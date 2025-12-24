"""
Bible/loading logic for the Study Bible Compendium.

This module now:
- Ensures the verse schema exists.
- Loads the canon.json mapping.
- Reads Excel rows via sbc.excel_import.
- Inserts real rows into the `verses_normalized` table (unless dry-run is enabled).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone

import json

from .db import get_conn
from .util import info, warn
from .paths import SCHEMA_DIR, DATA_DIR
from .model import VerseRef
from .excel_import import iter_verses_from_excel, ExcelVerseRow


def _apply_schema(path: Path) -> None:
    if not path.exists():
        warn(f"Schema file not found: {path}")
        return
    sql = path.read_text(encoding="utf-8")
    info(f"Applying schema from: {path}")
    with get_conn() as conn:
        conn.executescript(sql)
        conn.commit()


def ensure_verse_schema() -> None:
    """
    Apply the verse schema SQL file to the database (idempotent).
    """
    _apply_schema(SCHEMA_DIR / "verse_schema.sql")


def ensure_translations_schema() -> None:
    """
    Apply the translations schema SQL file to the database (idempotent).
    """
    _apply_schema(SCHEMA_DIR / "translations.sql")


def load_canon() -> Dict[int, Dict[str, Any]]:
    """
    Load the 66-book canon definition from data/canon.json.

    Returns
    -------
    dict:
        Map of book_num -> { "code": str, "name": str, "testament": str }
    """
    canon_path = DATA_DIR / "canon.json"
    if not canon_path.exists():
        warn(f"canon.json not found at: {canon_path}")
        return {}

    data = json.loads(canon_path.read_text(encoding="utf-8"))

    result: Dict[int, Dict[str, Any]] = {}
    for entry in data:
        num = int(entry["book_num"])
        result[num] = {
            "code": entry["code"],
            "name": entry["name"],
            "testament": entry.get("testament", "unknown"),
        }
    return result


def _build_book_lookup(canon: Dict[int, Dict[str, Any]]) -> Dict[str, int]:
    """
    Build a mapping from various book strings to book_num.

    Keys include:
    - 3-letter code (GEN)
    - full name (Genesis)
    - lowercase variants
    """
    lookup: Dict[str, int] = {}
    for num, meta in canon.items():
        code = meta["code"]
        name = meta["name"]

        for key in {code, code.lower(), name, name.lower()}:
            lookup[key] = num

    return lookup


def _resolve_book(book_str: str, book_lookup: Dict[str, int]) -> Optional[Tuple[int, str]]:
    """
    Resolve an incoming book string to (book_num, book_code).

    book_str may be:
    - 3-letter code (GEN)
    - full name (Genesis)
    - case variations thereof.
    """
    key_exact = book_str
    key_lower = book_str.lower()

    if key_exact in book_lookup:
        num = book_lookup[key_exact]
    elif key_lower in book_lookup:
        num = book_lookup[key_lower]
    else:
        return None

    return num, None  # book_code will be looked up from canon by num


def register_translation(
    code: str,
    name: Optional[str],
    language: str,
    source_notes: str,
) -> None:
    """
    Insert or update a translation row in the `translations` table.

    If name is None, we fall back to using the code as the name.
    """
    ensure_translations_schema()

    code = code.upper()
    if not name:
        name = code

    imported_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    info(f"Registering translation {code!r} in translations table.")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO translations (code, name, language, source_notes, imported_utc)
            VALUES (:code, :name, :language, :source_notes, :imported_utc)
            ON CONFLICT(code) DO UPDATE SET
                name         = excluded.name,
                language     = excluded.language,
                source_notes = excluded.source_notes,
                imported_utc = excluded.imported_utc;
            """,
            {
                "code": code,
                "name": name,
                "language": language,
                "source_notes": source_notes,
                "imported_utc": imported_utc,
            },
        )
        conn.commit()


def import_bible_from_excel(
    excel_path: Path,
    translation_code: str,
    overwrite: bool = False,
    sheet_name: Optional[str] = None,
    dry_run: bool = False,
    max_rows: Optional[int] = None,
) -> None:
    """
    Import a single Bible translation from an Excel file into the database.

    Parameters
    ----------
    excel_path:
        Path to the Excel file to import.
    translation_code:
        Short code for the translation (e.g. 'KJV', 'BSB', 'ASV').
    overwrite:
        If True, existing verses for this translation will be deleted first.
    sheet_name:
        Optional worksheet name. If None, the active sheet is used.
    dry_run:
        If True, do not write anything to the database. Just print diagnostics.
    max_rows:
        Optional limit on number of data rows to process (for testing).
    """
    excel_path = excel_path.resolve()
    if not excel_path.exists():
        warn(f"Excel file not found: {excel_path}")
        return

    translation_code = translation_code.upper()

    info("=== IMPORT BIBLE ===")
    info(f"Excel file       : {excel_path}")
    info(f"Translation code : {translation_code}")
    info(f"Overwrite        : {overwrite}")
    info(f"Sheet name       : {sheet_name or '(active sheet)'}")
    info(f"Dry run          : {dry_run}")
    info(f"Max rows         : {max_rows if max_rows is not None else '(no limit)'}")

    # Ensure schemas are in place
    ensure_verse_schema()
    ensure_translations_schema()

    # Load canon mapping
    canon = load_canon()
    if not canon:
        warn("Canon mapping is empty; cannot normalize references. Aborting.")
        return

    book_lookup = _build_book_lookup(canon)

    # Gather rows from Excel
    rows: List[ExcelVerseRow] = list(
        iter_verses_from_excel(excel_path, sheet_name=sheet_name, max_rows=max_rows)
    )
    if not rows:
        warn("No usable verse rows found in Excel file.")
        return

    info(f"Parsed {len(rows)} verse rows from Excel.")

    # Normalize rows into DB-ready tuples
    db_rows: List[Tuple[str, int, str, int, int, str, str, int]] = []
    skipped = 0

    for r in rows:
        resolved = _resolve_book(r.book, book_lookup)
        if resolved is None:
            warn(f"Row {r.raw_row_index}: could not resolve book {r.book!r}; skipping.")
            skipped += 1
            continue

        book_num, _ = resolved
        book_meta = canon[book_num]
        book_code = book_meta["code"]

        vref = VerseRef(book_num=book_num, chapter=r.chapter, verse=r.verse)
        norm_ref = vref.to_normalized(book_code)

        text = r.text.strip()
        word_count = len(text.split()) if text else 0

        db_rows.append(
            (
                translation_code,
                book_num,
                book_code,
                r.chapter,
                r.verse,
                norm_ref,
                text,
                word_count,
            )
        )

    info(f"Prepared {len(db_rows)} rows for insertion; skipped {skipped} rows.")

    if dry_run:
        info("Dry run enabled – no rows will be written to the database.")
        return

    if not db_rows:
        warn("No rows to insert after normalization. Nothing written.")
        return

    # Insert into DB
    with get_conn() as conn:
        cur = conn.cursor()

        if overwrite:
            info(f"Deleting existing verses for translation {translation_code!r}...")
            cur.execute(
                "DELETE FROM verses_normalized WHERE translation_code = ?;",
                (translation_code,),
            )

        info("Inserting verse rows into `verses_normalized` table...")
        cur.executemany(
            """
            INSERT INTO verses_normalized (
                translation_code,
                book_num,
                book_code,
                chapter,
                verse,
                normalized_ref,
                text,
                word_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            db_rows,
        )
        conn.commit()

    info(f"Import complete. Inserted {len(db_rows)} verses for {translation_code!r}.")
    if skipped:
        info(f"Skipped {skipped} rows due to book/structure issues.")

    # Register translation (basic guess for name/language/source)
    # You can refine these later (e.g., config or CLI flags)
    source_notes = f"Imported from Excel file {excel_path.name}"
    register_translation(
        code=translation_code,
        name=None,          # fallback to code
        language="en",      # default assumption
        source_notes=source_notes,
    )


def list_loaded_translations() -> None:
    """
    List which translations are already in the database (from verses_normalized table).
    """
    from .db import ping

    if not ping():
        warn("Database is not reachable yet. Ensure compendium.sqlite exists.")
        return

    with get_conn(readonly=True) as conn:
        cur = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'verses_normalized';
            """
        )
        if not cur.fetchone():
            warn("`verses_normalized` table does not exist yet. Run init-schema first.")
            return

        cur = conn.execute(
            "SELECT DISTINCT translation_code FROM verses_normalized ORDER BY translation_code;"
        )
        rows = cur.fetchall()

    if not rows:
        info("No translations loaded into `verses_normalized` yet.")
        return

    info("Loaded translations (from verses_normalized table):")
    for (code,) in rows:
        print(f"  - {code}")
