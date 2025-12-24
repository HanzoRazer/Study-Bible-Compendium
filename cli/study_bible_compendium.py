#!/usr/bin/env python3
"""
Study Bible Compendium – Desktop Engine v2
Now includes:
- Proper schema for KJV/BSB/ASV/Greek/Hebrew (multi-version)
- Strong's lexicon + verse mapping
- Interlinear tokens for original language text
- Midrash of the Messiah note storage
- CLI importers for:
    * Plaintext Bible (bootstrap)
    * Normalized CSV Bible verses
    * Strong's CSV
    * Interlinear CSV
    * Midrash CSV
- PDF exporters:
    * Simple chapter verse-per-line
    * Midrash study report (chapter, with 4-verse context window)
"""

import argparse
import sqlite3
from sqlite3 import Connection, Row
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Tuple
import sys
import csv

# ReportLab for PDFs (optional but recommended)
try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
except ImportError:
    reportlab_available = False
else:
    reportlab_available = True


# ---------------------------------------------------------------------------
# Time helper
# ---------------------------------------------------------------------------

def utc_now_iso() -> str:
    """RFC-3339-like UTC timestamp, second precision."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# DB connection + schema
# ---------------------------------------------------------------------------

def get_connection(db_path: Path) -> Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = Row
    return conn


SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS policy (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    preface     TEXT NOT NULL,
    body        TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    locked      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bible_versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    language    TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS books (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id   INTEGER NOT NULL,
    code         TEXT NOT NULL,
    name         TEXT NOT NULL,
    order_index  INTEGER NOT NULL,
    FOREIGN KEY (version_id) REFERENCES bible_versions(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_books_version_code
    ON books(version_id, code);
CREATE UNIQUE INDEX IF NOT EXISTS idx_books_version_name
    ON books(version_id, name);

CREATE TABLE IF NOT EXISTS chapters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL,
    chapter_number  INTEGER NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_chapters_book_ch
    ON chapters(book_id, chapter_number);

CREATE TABLE IF NOT EXISTS verses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id      INTEGER NOT NULL,
    verse_number    INTEGER NOT NULL,
    text            TEXT NOT NULL,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_verses_ch_verse
    ON verses(chapter_id, verse_number);
CREATE INDEX IF NOT EXISTS idx_verses_text
    ON verses(text);

CREATE TABLE IF NOT EXISTS strongs_lexicon (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strongs_number  TEXT NOT NULL UNIQUE,
    language        TEXT NOT NULL,
    lemma           TEXT NOT NULL,
    gloss           TEXT,
    extra           TEXT
);

CREATE TABLE IF NOT EXISTS verse_strongs (
    verse_id    INTEGER NOT NULL,
    strongs_id  INTEGER NOT NULL,
    PRIMARY KEY (verse_id, strongs_id),
    FOREIGN KEY (verse_id) REFERENCES verses(id),
    FOREIGN KEY (strongs_id) REFERENCES strongs_lexicon(id)
);

CREATE TABLE IF NOT EXISTS interlinear_tokens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id        INTEGER NOT NULL,
    word_index      INTEGER NOT NULL,
    language        TEXT NOT NULL,
    surface         TEXT NOT NULL,
    lemma           TEXT,
    strongs_number  TEXT,
    morph           TEXT,
    FOREIGN KEY (verse_id) REFERENCES verses(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_interlinear_unique
    ON interlinear_tokens(verse_id, word_index);

CREATE TABLE IF NOT EXISTS crossrefs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    from_verse_id  INTEGER NOT NULL,
    to_verse_id    INTEGER NOT NULL,
    kind           TEXT,
    FOREIGN KEY (from_verse_id) REFERENCES verses(id),
    FOREIGN KEY (to_verse_id) REFERENCES verses(id)
);

CREATE TABLE IF NOT EXISTS user_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id  INTEGER,
    book_id     INTEGER,
    chapter     INTEGER,
    verse       INTEGER,
    note_text   TEXT NOT NULL,
    tags        TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY (version_id) REFERENCES bible_versions(id),
    FOREIGN KEY (book_id) REFERENCES books(id)
);

CREATE TABLE IF NOT EXISTS midrash_sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    short_code  TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS midrash_notes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id      INTEGER NOT NULL,
    version_id     INTEGER,
    book_id        INTEGER,
    chapter        INTEGER,
    verse_start    INTEGER NOT NULL,
    verse_end      INTEGER,
    note_text      TEXT NOT NULL,
    category       TEXT,
    color_tag      TEXT,
    created_at     TEXT NOT NULL,
    metadata_json  TEXT,
    FOREIGN KEY (source_id) REFERENCES midrash_sources(id),
    FOREIGN KEY (version_id) REFERENCES bible_versions(id),
    FOREIGN KEY (book_id) REFERENCES books(id)
);
"""


def init_schema(conn: Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


# ---------------------------------------------------------------------------
# Policy handling
# ---------------------------------------------------------------------------

def compute_policy_checksum(preface: str, body: str) -> str:
    import hashlib
    h = hashlib.sha256()
    normalized = (
        preface.replace("\r\n", "\n").replace("\r", "\n") + "\n\n" +
        body.replace("\r\n", "\n").replace("\r", "\n")
    )
    h.update(normalized.encode("utf-8"))
    return h.hexdigest()


def is_policy_locked(conn: Connection) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT locked FROM policy WHERE id = 1;")
    row = cur.fetchone()
    if row is None:
        return False
    return bool(row["locked"])


def init_policy(
    conn: Connection,
    preface_text: str,
    body_text: str,
    force: bool = False,
) -> None:
    init_schema(conn)

    locked = is_policy_locked(conn)
    cur = conn.cursor()

    checksum = compute_policy_checksum(preface_text, body_text)
    now = utc_now_iso()

    if locked and not force:
        cur.execute("SELECT checksum FROM policy WHERE id = 1;")
        row = cur.fetchone()
        existing_checksum = row["checksum"] if row else "UNKNOWN"
        print(
            "Policy table is already locked.\n"
            f"Existing checksum={existing_checksum}\n"
            "No changes made. Use --force ONLY if you really intend to overwrite.",
            file=sys.stderr,
        )
        return

    cur.execute(
        """
        REPLACE INTO policy (id, preface, body, checksum, locked, created_at)
        VALUES (1, ?, ?, ?, 1, ?);
        """,
        (preface_text, body_text, checksum, now),
    )
    conn.commit()

    if locked and force:
        print("Existing locked policy was OVERWRITTEN (force=True).")
    else:
        print("Policy inserted and locked successfully.")
    print(f"Checksum: {checksum}")


# ---------------------------------------------------------------------------
# Core lookup helpers (versions / books / chapters / verses)
# ---------------------------------------------------------------------------

BOOK_ORDER = {
    # Seed – extend as you go
    "Genesis": 1,
    "Exodus": 2,
    "Leviticus": 3,
    "Numbers": 4,
    "Deuteronomy": 5,
}


def get_or_create_version(
    conn: Connection,
    code: str,
    name: str,
    language: str,
) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM bible_versions WHERE code = ?;", (code,))
    row = cur.fetchone()
    if row:
        return row["id"]
    now = utc_now_iso()
    cur.execute(
        """
        INSERT INTO bible_versions (code, name, language, created_at)
        VALUES (?, ?, ?, ?);
        """,
        (code, name, language, now),
    )
    conn.commit()
    return cur.lastrowid


def get_or_create_book(
    conn: Connection,
    version_id: int,
    book_name: str,
    book_code: Optional[str] = None,
) -> int:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM books WHERE version_id = ? AND name = ?;",
        (version_id, book_name),
    )
    row = cur.fetchone()
    if row:
        return row["id"]

    # Also check by code to handle interrupted imports
    code = book_code or book_name[:3].upper()
    cur.execute(
        "SELECT id FROM books WHERE version_id = ? AND code = ?;",
        (version_id, code),
    )
    row = cur.fetchone()
    if row:
        return row["id"]

    order_idx = BOOK_ORDER.get(book_name, 999)
    cur.execute(
        """
        INSERT INTO books (version_id, code, name, order_index)
        VALUES (?, ?, ?, ?);
        """,
        (version_id, code, book_name, order_idx),
    )
    conn.commit()
    return cur.lastrowid


def get_or_create_chapter(
    conn: Connection,
    book_id: int,
    chapter_number: int,
) -> int:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM chapters WHERE book_id = ? AND chapter_number = ?;",
        (book_id, chapter_number),
    )
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute(
        "INSERT INTO chapters (book_id, chapter_number) VALUES (?, ?);",
        (book_id, chapter_number),
    )
    conn.commit()
    return cur.lastrowid


def get_verse_id(
    conn: Connection,
    version_code: str,
    book_name: str,
    chapter_number: int,
    verse_number: int,
) -> Optional[int]:
    """
    Resolve a verse to its internal ID, or None if missing.
    """
    cur = conn.cursor()
    cur.execute("SELECT id FROM bible_versions WHERE code = ?;", (version_code,))
    ver = cur.fetchone()
    if not ver:
        return None
    version_id = ver["id"]

    cur.execute(
        "SELECT id FROM books WHERE version_id = ? AND name = ?;",
        (version_id, book_name),
    )
    b = cur.fetchone()
    if not b:
        return None
    book_id = b["id"]

    cur.execute(
        "SELECT id FROM chapters WHERE book_id = ? AND chapter_number = ?;",
        (book_id, chapter_number),
    )
    ch = cur.fetchone()
    if not ch:
        return None
    chapter_id = ch["id"]

    cur.execute(
        "SELECT id FROM verses WHERE chapter_id = ? AND verse_number = ?;",
        (chapter_id, verse_number),
    )
    v = cur.fetchone()
    if not v:
        return None
    return v["id"]


# ---------------------------------------------------------------------------
# Bible importers
# ---------------------------------------------------------------------------

def import_plaintext_bible(
    conn: Connection,
    version_code: str,
    version_name: str,
    language: str,
    file_path: Path,
) -> None:
    """
    Very simple bootstrap importer.
    Format per line:
      Book Chapter:Verse Text...
    Example:
      Genesis 1:1 In the beginning God created the heaven and the earth.
    """
    init_schema(conn)
    version_id = get_or_create_version(conn, version_code, version_name, language)
    cur = conn.cursor()
    inserted = 0

    with file_path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue

            parts = line.split(maxsplit=2)
            if len(parts) < 3:
                print(f"Skipping line {line_no}: cannot parse -> {line}")
                continue

            book_name = parts[0]
            ch_verse = parts[1]
            text = parts[2]

            if ":" not in ch_verse:
                print(f"Skipping line {line_no}: missing ':' -> {line}")
                continue

            try:
                chapter_str, verse_str = ch_verse.split(":", 1)
                chapter_num = int(chapter_str)
                verse_num = int(verse_str)
            except ValueError:
                print(f"Skipping line {line_no}: bad chapter/verse -> {line}")
                continue

            book_id = get_or_create_book(conn, version_id, book_name)
            chap_id = get_or_create_chapter(conn, book_id, chapter_num)

            cur.execute(
                """
                INSERT INTO verses (chapter_id, verse_number, text)
                VALUES (?, ?, ?)
                ON CONFLICT(chapter_id, verse_number) DO UPDATE SET text=excluded.text;
                """,
                (chap_id, verse_num, text),
            )
            inserted += 1

    conn.commit()
    print(f"Imported/updated {inserted} verses into version {version_code} from plaintext.")


def import_bible_csv(
    conn: Connection,
    version_code: str,
    version_name: str,
    language: str,
    csv_path: Path,
) -> None:
    """
    Normalized CSV importer for real KJV/BSB/ASV/Greek/Hebrew sources.

    Expected CSV columns (header row required):
        book, chapter, verse, text
    Optionally:
        book_code

    This decouples your real source format (OSIS, Zefania, etc.)
    from this importer: you can pre-normalize each source into
    this simple CSV, then call this.
    """
    init_schema(conn)
    version_id = get_or_create_version(conn, version_code, version_name, language)
    cur = conn.cursor()
    inserted = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required_cols = {"book", "chapter", "verse", "text"}
        if not required_cols.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must have columns: {', '.join(sorted(required_cols))}")

        for row in reader:
            book = row["book"].strip()
            book_code = row.get("book_code") or None
            try:
                chapter = int(row["chapter"])
                verse = int(row["verse"])
            except ValueError:
                print(f"Skipping bad reference {row}", file=sys.stderr)
                continue
            text = row["text"]

            book_id = get_or_create_book(conn, version_id, book, book_code)
            chap_id = get_or_create_chapter(conn, book_id, chapter)

            cur.execute(
                """
                INSERT INTO verses (chapter_id, verse_number, text)
                VALUES (?, ?, ?)
                ON CONFLICT(chapter_id, verse_number) DO UPDATE SET text=excluded.text;
                """,
                (chap_id, verse, text),
            )
            inserted += 1

    conn.commit()
    print(f"Imported/updated {inserted} verses into {version_code} from CSV.")


# ---------------------------------------------------------------------------
# Strong's + Interlinear importers
# ---------------------------------------------------------------------------

def import_strongs_csv(
    conn: Connection,
    csv_path: Path,
    default_language: Optional[str] = None,
) -> None:
    """
    Import Strong's lexicon from CSV.

    Expected columns:
        strongs_number, lemma
    Optional:
        language, gloss, extra

    If 'language' is missing, default_language is used (e.g. 'he' or 'el').
    """
    init_schema(conn)
    cur = conn.cursor()
    inserted = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "strongs_number" not in reader.fieldnames or "lemma" not in reader.fieldnames:
            raise ValueError("CSV must have at least 'strongs_number' and 'lemma' columns")

        for row in reader:
            num = row["strongs_number"].strip()
            lemma = row["lemma"].strip()
            language = (row.get("language") or default_language or "").strip()
            gloss = (row.get("gloss") or "").strip() or None
            extra = (row.get("extra") or "").strip() or None

            if not num or not lemma or not language:
                print(f"Skipping incomplete Strong's row: {row}", file=sys.stderr)
                continue

            cur.execute(
                """
                INSERT INTO strongs_lexicon (strongs_number, language, lemma, gloss, extra)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(strongs_number) DO UPDATE SET
                    language=excluded.language,
                    lemma=excluded.lemma,
                    gloss=excluded.gloss,
                    extra=excluded.extra;
                """,
                (num, language, lemma, gloss, extra),
            )
            inserted += 1

    conn.commit()
    print(f"Imported/updated {inserted} Strong's lexicon entries.")


def import_interlinear_csv(
    conn: Connection,
    csv_path: Path,
) -> None:
    """
    Import interlinear tokens for Greek/Hebrew.

    Expected columns:
        version_code, book, chapter, verse,
        word_index, language, surface
    Optional:
        lemma, strongs_number, morph

    Assumes the target Bible text has already been imported
    for the given version_code.
    """
    init_schema(conn)
    cur = conn.cursor()
    inserted = 0
    skipped = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"version_code", "book", "chapter", "verse", "word_index", "language", "surface"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must have columns: {', '.join(sorted(required))}")

        for row in reader:
            version_code = row["version_code"].strip()
            book = row["book"].strip()
            try:
                chapter = int(row["chapter"])
                verse = int(row["verse"])
                word_index = int(row["word_index"])
            except ValueError:
                print(f"Skipping bad reference index: {row}", file=sys.stderr)
                skipped += 1
                continue
            language = row["language"].strip()
            surface = row["surface"].strip()
            lemma = (row.get("lemma") or "").strip() or None
            strongs_number = (row.get("strongs_number") or "").strip() or None
            morph = (row.get("morph") or "").strip() or None

            verse_id = get_verse_id(conn, version_code, book, chapter, verse)
            if verse_id is None:
                print(f"Warning: verse not found for token {row}", file=sys.stderr)
                skipped += 1
                continue

            cur.execute(
                """
                INSERT INTO interlinear_tokens
                    (verse_id, word_index, language, surface, lemma, strongs_number, morph)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(verse_id, word_index) DO UPDATE SET
                    language=excluded.language,
                    surface=excluded.surface,
                    lemma=excluded.lemma,
                    strongs_number=excluded.strongs_number,
                    morph=excluded.morph;
                """,
                (verse_id, word_index, language, surface, lemma, strongs_number, morph),
            )
            inserted += 1

    conn.commit()
    print(f"Imported/updated {inserted} interlinear tokens (skipped {skipped}).")


# ---------------------------------------------------------------------------
# Midrash (Midrash of the Messiah) import + reports
# ---------------------------------------------------------------------------

def get_or_create_midrash_source(
    conn: Connection,
    name: str,
    short_code: str,
) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM midrash_sources WHERE short_code = ?;", (short_code,))
    row = cur.fetchone()
    if row:
        return row["id"]
    now = utc_now_iso()
    cur.execute(
        """
        INSERT INTO midrash_sources (name, short_code, created_at)
        VALUES (?, ?, ?);
        """,
        (name, short_code, now),
    )
    conn.commit()
    return cur.lastrowid


def import_midrash_csv(
    conn: Connection,
    csv_path: Path,
    source_name: str = "Midrash of the Messiah",
    source_code: str = "MOTM",
    version_code: Optional[str] = None,
) -> None:
    """
    Import Midrash notes (e.g. Midrash of the Messiah) in normalized CSV form.

    Expected columns:
        book, chapter, verse_start, note_text
    Optional:
        verse_end, category, color_tag, metadata_json

    If version_code is provided, notes are bound to that version;
    otherwise version_id is NULL (applies to all versions).
    """
    init_schema(conn)
    cur = conn.cursor()
    source_id = get_or_create_midrash_source(conn, source_name, source_code)

    version_id = None
    if version_code:
        cur.execute("SELECT id FROM bible_versions WHERE code = ?;", (version_code,))
        vr = cur.fetchone()
        if not vr:
            raise ValueError(f"Version code for midrash binding not found: {version_code}")
        version_id = vr["id"]

    inserted = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"book", "chapter", "verse_start", "note_text"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Midrash CSV must have columns: {', '.join(sorted(required))}")

        for row in reader:
            book = row["book"].strip()
            try:
                chapter = int(row["chapter"])
                verse_start = int(row["verse_start"])
            except ValueError:
                print(f"Skipping bad midrash reference: {row}", file=sys.stderr)
                continue
            verse_end_raw = row.get("verse_end")
            verse_end = int(verse_end_raw) if verse_end_raw and verse_end_raw.strip() else None
            note_text = row["note_text"].strip()
            category = (row.get("category") or "").strip() or None
            color_tag = (row.get("color_tag") or "").strip() or None
            metadata_json = (row.get("metadata_json") or "").strip() or None

            # book_id is stored for the first version we find. If version_id is None,
            # we still need a version_id to resolve book_id; pick the first matching
            # version that has that book, or create for the first version in db.
            book_id = None
            if version_id is not None:
                cur.execute(
                    "SELECT id FROM books WHERE version_id = ? AND name = ?;",
                    (version_id, book),
                )
                b = cur.fetchone()
                if b:
                    book_id = b["id"]
            else:
                # Try any version
                cur.execute(
                    "SELECT id FROM books WHERE name = ? ORDER BY version_id LIMIT 1;",
                    (book,),
                )
                b = cur.fetchone()
                if b:
                    book_id = b["id"]

            now = utc_now_iso()
            cur.execute(
                """
                INSERT INTO midrash_notes
                    (source_id, version_id, book_id, chapter, verse_start, verse_end,
                     note_text, category, color_tag, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    source_id,
                    version_id,
                    book_id,
                    chapter,
                    verse_start,
                    verse_end,
                    note_text,
                    category,
                    color_tag,
                    now,
                    metadata_json,
                ),
            )
            inserted += 1

    conn.commit()
    print(f"Imported {inserted} midrash notes for source {source_code}.")


# ---------------------------------------------------------------------------
# Search + PDF exports
# ---------------------------------------------------------------------------

def search_verses(
    conn: Connection,
    query: str,
    version_code: Optional[str] = None,
    limit: int = 25,
) -> List[Row]:
    params: Tuple = ()
    sql = """
        SELECT v.id, bv.code AS version, b.name AS book,
               c.chapter_number, v.verse_number, v.text
        FROM verses v
        JOIN chapters c ON v.chapter_id = c.id
        JOIN books b    ON c.book_id = b.id
        JOIN bible_versions bv ON b.version_id = bv.id
        WHERE v.text LIKE ?
    """
    params += (f"%{query}%",)

    if version_code:
        sql += " AND bv.code = ?"
        params += (version_code,)

    sql += """
        ORDER BY b.order_index, c.chapter_number, v.verse_number
        LIMIT ?
    """
    params += (limit,)

    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()


def export_chapter_pdf(
    conn: Connection,
    version_code: str,
    book_name: str,
    chapter_number: int,
    outfile: Path,
) -> None:
    if not reportlab_available:
        print("ReportLab is not installed. Install with: pip install reportlab", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor()
    cur.execute("SELECT id FROM bible_versions WHERE code = ?;", (version_code,))
    ver = cur.fetchone()
    if not ver:
        print(f"Version not found: {version_code}", file=sys.stderr)
        sys.exit(1)
    version_id = ver["id"]

    cur.execute(
        "SELECT id, name FROM books WHERE version_id = ? AND name = ?;",
        (version_id, book_name),
    )
    b = cur.fetchone()
    if not b:
        print(f"Book not found for {version_code}: {book_name}", file=sys.stderr)
        sys.exit(1)
    book_id = b["id"]
    book_display = b["name"]

    cur.execute(
        "SELECT id FROM chapters WHERE book_id = ? AND chapter_number = ?;",
        (book_id, chapter_number),
    )
    ch = cur.fetchone()
    if not ch:
        print(f"Chapter not found: {book_name} {chapter_number}", file=sys.stderr)
        sys.exit(1)
    chapter_id = ch["id"]

    cur.execute(
        """
        SELECT verse_number, text
        FROM verses
        WHERE chapter_id = ?
        ORDER BY verse_number;
        """,
        (chapter_id,),
    )
    verses = cur.fetchall()
    if not verses:
        print("No verses found for that chapter.", file=sys.stderr)
        sys.exit(1)

    styles = getSampleStyleSheet()
    story = []

    title = f"{book_display} {chapter_number} ({version_code}) – Verse-per-line"
    story.append(Paragraph(title, styles["Heading1"]))
    story.append(Spacer(1, 12))

    for row in verses:
        line = f"<b>{row['verse_number']}</b> {row['text']}"
        story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 4))

    doc = SimpleDocTemplate(str(outfile), pagesize=LETTER)
    doc.build(story)
    print(f"PDF exported: {outfile}")


def export_midrash_chapter_pdf(
    conn: Connection,
    version_code: str,
    book_name: str,
    chapter_number: int,
    outfile: Path,
    source_code: str = "MOTM",
    context_back: int = 2,
    context_forward: int = 1,
) -> None:
    """
    Midrash Study Report for a single chapter.
    - Verse-per-line layout.
    - For verses with midrash notes, include:
        * Highlighted verse marker
        * Notes listed under the verse
    - Includes context_back verses before and context_forward after
      each noted verse (bounded within the chapter).
    """
    if not reportlab_available:
        print("ReportLab is not installed. Install with: pip install reportlab", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor()
    # Resolve version / book / chapter / verses
    cur.execute("SELECT id FROM bible_versions WHERE code = ?;", (version_code,))
    ver = cur.fetchone()
    if not ver:
        print(f"Version not found: {version_code}", file=sys.stderr)
        sys.exit(1)
    version_id = ver["id"]

    cur.execute(
        "SELECT id, name FROM books WHERE version_id = ? AND name = ?;",
        (version_id, book_name),
    )
    b = cur.fetchone()
    if not b:
        print(f"Book not found for {version_code}: {book_name}", file=sys.stderr)
        sys.exit(1)
    book_id = b["id"]
    book_display = b["name"]

    cur.execute(
        "SELECT id FROM chapters WHERE book_id = ? AND chapter_number = ?;",
        (book_id, chapter_number),
    )
    ch = cur.fetchone()
    if not ch:
        print(f"Chapter not found: {book_name} {chapter_number}", file=sys.stderr)
        sys.exit(1)
    chapter_id = ch["id"]

    # Fetch all verses in chapter
    cur.execute(
        "SELECT verse_number, text, id FROM verses WHERE chapter_id = ? ORDER BY verse_number;",
        (chapter_id,),
    )
    verses = cur.fetchall()
    if not verses:
        print("No verses found for that chapter.", file=sys.stderr)
        sys.exit(1)

    # Map verse_number -> verse_id
    verse_by_num = {v["verse_number"]: v for v in verses}

    # Get all midrash notes for this chapter and source
    cur.execute(
        """
        SELECT mn.*, ms.short_code
        FROM midrash_notes mn
        JOIN midrash_sources ms ON mn.source_id = ms.id
        WHERE ms.short_code = ?
          AND mn.chapter = ?
          AND (mn.book_id IS NULL OR mn.book_id = ?)
        ORDER BY mn.verse_start;
        """,
        (source_code, chapter_number, book_id),
    )
    midrash_rows = cur.fetchall()

    # Build verse -> list of notes mapping
    notes_by_verse = {}
    for r in midrash_rows:
        vs = r["verse_start"]
        ve = r["verse_end"] or vs
        for vnum in range(vs, ve + 1):
            notes_by_verse.setdefault(vnum, []).append(r)

    # Determine which verses to include (4-verse context window per verse with notes)
    include_flags = {v["verse_number"]: False for v in verses}
    for vnum in notes_by_verse:
        for cn in range(vnum - context_back, vnum + context_forward + 1):
            if cn in include_flags:
                include_flags[cn] = True

    styles = getSampleStyleSheet()
    story = []

    title = f"{book_display} {chapter_number} ({version_code}) – Midrash Study ({source_code})"
    story.append(Paragraph(title, styles["Heading1"]))
    story.append(Spacer(1, 12))

    for v in verses:
        vnum = v["verse_number"]
        if not include_flags[vnum]:
            continue

        base = f"<b>{vnum}</b> {v['text']}"
        if vnum in notes_by_verse:
            base = f"<b>[★ {vnum}]</b> {v['text']}"

        story.append(Paragraph(base, styles["Normal"]))
        story.append(Spacer(1, 2))

        if vnum in notes_by_verse:
            for note in notes_by_verse[vnum]:
                tag = note["category"] or "note"
                color = note["color_tag"] or ""
                label = f"{tag}"
                if color:
                    label += f" ({color})"
                line = f"<i>{label}:</i> {note['note_text']}"
                story.append(Paragraph(line, styles["Italic"]))
                story.append(Spacer(1, 2))

        story.append(Spacer(1, 4))

    doc = SimpleDocTemplate(str(outfile), pagesize=LETTER)
    doc.build(story)
    print(f"Midrash PDF exported: {outfile}")


# ---------------------------------------------------------------------------
# CLI command handlers
# ---------------------------------------------------------------------------

def cmd_init_db(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    init_schema(conn)
    print(f"Database initialized/verified at: {args.db}")


def cmd_init_policy(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    init_schema(conn)

    preface_path = Path(args.preface)
    policy_path = Path(args.policy)

    if not preface_path.is_file():
        print(f"Preface file not found: {preface_path}", file=sys.stderr)
        sys.exit(1)
    if not policy_path.is_file():
        print(f"Policy body file not found: {policy_path}", file=sys.stderr)
        sys.exit(1)

    preface_text = preface_path.read_text(encoding="utf-8")
    body_text = policy_path.read_text(encoding="utf-8")

    init_policy(conn, preface_text, body_text, force=args.force)


def cmd_list_versions(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    init_schema(conn)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, code, name, language, created_at FROM bible_versions ORDER BY code;"
    )
    rows = cur.fetchall()
    if not rows:
        print("No versions found.")
        return
    for r in rows:
        print(f"[{r['code']}] {r['name']} ({r['language']}) – created {r['created_at']}")


def cmd_import_plaintext(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    fp = Path(args.file)
    if not fp.is_file():
        print(f"File not found: {fp}", file=sys.stderr)
        sys.exit(1)

    import_plaintext_bible(
        conn,
        version_code=args.version_code,
        version_name=args.version_name,
        language=args.language,
        file_path=fp,
    )


def cmd_import_bible_csv(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    fp = Path(args.file)
    if not fp.is_file():
        print(f"File not found: {fp}", file=sys.stderr)
        sys.exit(1)

    import_bible_csv(
        conn,
        version_code=args.version_code,
        version_name=args.version_name,
        language=args.language,
        csv_path=fp,
    )


def cmd_import_strongs(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    fp = Path(args.file)
    if not fp.is_file():
        print(f"File not found: {fp}", file=sys.stderr)
        sys.exit(1)

    import_strongs_csv(conn, fp, default_language=args.language)


def cmd_import_interlinear(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    fp = Path(args.file)
    if not fp.is_file():
        print(f"File not found: {fp}", file=sys.stderr)
        sys.exit(1)

    import_interlinear_csv(conn, fp)


def cmd_import_midrash(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    fp = Path(args.file)
    if not fp.is_file():
        print(f"File not found: {fp}", file=sys.stderr)
        sys.exit(1)

    import_midrash_csv(
        conn,
        fp,
        source_name=args.source_name,
        source_code=args.source_code,
        version_code=args.version_code,
    )


def cmd_search(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    init_schema(conn)
    results = search_verses(conn, args.query, args.version_code, limit=args.limit)
    if not results:
        print("No matches found.")
        return
    for r in results:
        print(
            f"{r['version']} {r['book']} {r['chapter_number']}:{r['verse_number']} "
            f"- {r['text']}"
        )


def cmd_export_pdf(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    init_schema(conn)
    export_chapter_pdf(
        conn,
        version_code=args.version_code,
        book_name=args.book,
        chapter_number=args.chapter,
        outfile=Path(args.outfile),
    )


def cmd_export_midrash_pdf(args: argparse.Namespace) -> None:
    conn = get_connection(Path(args.db))
    init_schema(conn)
    export_midrash_chapter_pdf(
        conn,
        version_code=args.version_code,
        book_name=args.book,
        chapter_number=args.chapter,
        outfile=Path(args.outfile),
        source_code=args.source_code,
    )


# ---------------------------------------------------------------------------
# Argparse wiring
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Study Bible Compendium – Desktop Engine (SQLite + Strong's + Midrash)"
    )
    p.add_argument(
        "--db",
        default="compendium.sqlite",
        help="Path to SQLite database file (default: compendium.sqlite)",
    )

    subs = p.add_subparsers(dest="command", required=True)

    # init-db
    s = subs.add_parser("init-db", help="Initialize/verify database schema")
    s.set_defaults(func=cmd_init_db)

    # init-policy
    s = subs.add_parser("init-policy", help="Insert doctrinal preface + policy")
    s.add_argument("--preface", required=True, help="Preface text file")
    s.add_argument("--policy", required=True, help="Policy body text file")
    s.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing locked policy (use with extreme caution)",
    )
    s.set_defaults(func=cmd_init_policy)

    # list-versions
    s = subs.add_parser("list-versions", help="List Bible versions")
    s.set_defaults(func=cmd_list_versions)

    # import-plaintext
    s = subs.add_parser("import-plaintext", help="Import simple plaintext Bible")
    s.add_argument("--version-code", required=True, help="e.g. KJV, BSB")
    s.add_argument("--version-name", required=True, help="Full version name")
    s.add_argument("--language", required=True, help="Language code (e.g. en, el, he)")
    s.add_argument("--file", required=True, help="Path to plaintext file")
    s.set_defaults(func=cmd_import_plaintext)

    # import-bible-csv
    s = subs.add_parser("import-bible-csv", help="Import Bible from normalized CSV")
    s.add_argument("--version-code", required=True, help="e.g. KJV, BSB, ASV")
    s.add_argument("--version-name", required=True, help="Full version name")
    s.add_argument("--language", required=True, help="Language code")
    s.add_argument("--file", required=True, help="Path to CSV file (book, chapter, verse, text)")
    s.set_defaults(func=cmd_import_bible_csv)

    # import-strongs
    s = subs.add_parser("import-strongs", help="Import Strong's lexicon from CSV")
    s.add_argument("--language", required=True, help="Default language code for entries (he/el)")
    s.add_argument("--file", required=True, help="Path to Strong's CSV")
    s.set_defaults(func=cmd_import_strongs)

    # import-interlinear
    s = subs.add_parser("import-interlinear", help="Import interlinear tokens from CSV")
    s.add_argument("--file", required=True, help="Path to interlinear CSV")
    s.set_defaults(func=cmd_import_interlinear)

    # import-midrash
    s = subs.add_parser("import-midrash", help="Import Midrash notes (e.g. Midrash of the Messiah)")
    s.add_argument("--file", required=True, help="Path to Midrash CSV")
    s.add_argument(
        "--source-name",
        default="Midrash of the Messiah",
        help="Human-readable source name (default: Midrash of the Messiah)",
    )
    s.add_argument(
        "--source-code",
        default="MOTM",
        help="Short code for source (default: MOTM)",
    )
    s.add_argument(
        "--version-code",
        help="Bind notes to a specific version (e.g. BSB); if omitted, notes apply to all versions",
    )
    s.set_defaults(func=cmd_import_midrash)

    # search
    s = subs.add_parser("search", help="Search verses by phrase")
    s.add_argument("--query", required=True, help="Search phrase")
    s.add_argument("--version-code", help="Restrict to specific version")
    s.add_argument("--limit", type=int, default=25, help="Max hits (default 25)")
    s.set_defaults(func=cmd_search)

    # export-pdf
    s = subs.add_parser("export-pdf", help="Export verse-per-line chapter PDF")
    s.add_argument("--version-code", required=True, help="Version code (e.g. KJV)")
    s.add_argument("--book", required=True, help="Book name (e.g. Genesis)")
    s.add_argument("--chapter", required=True, type=int, help="Chapter number")
    s.add_argument("--outfile", required=True, help="Output PDF file path")
    s.set_defaults(func=cmd_export_pdf)

    # export-midrash-pdf
    s = subs.add_parser("export-midrash-pdf", help="Export Midrash Study chapter PDF")
    s.add_argument("--version-code", required=True, help="Version code (e.g. BSB)")
    s.add_argument("--book", required=True, help="Book name")
    s.add_argument("--chapter", required=True, type=int, help="Chapter number")
    s.add_argument(
        "--source-code",
        default="MOTM",
        help="Midrash source code (default: MOTM)",
    )
    s.add_argument("--outfile", required=True, help="Output PDF file path")
    s.set_defaults(func=cmd_export_midrash_pdf)

    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
