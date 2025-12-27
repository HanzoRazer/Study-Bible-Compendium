#!/usr/bin/env python3
"""
Core Passages installer for Study Bible Compendium.

Manages high-value theological passages with attached verse notes and Greek margins.
Supports both hardcoded Python data and JSON-based loading from STUDIES/ directory.

Usage:
    # Initialize schema
    python -m sbc.core_passages --db compendium.sqlite init-schema
    
    # Install from JSON (recommended)
    python -m sbc.core_passages --db compendium.sqlite add-from-json \\
        --greek-margins STUDIES/greek-margins/romans_8.json \\
        --verse-notes STUDIES/verse-notes/romans_8.json \\
        --core-passage STUDIES/core-passages/sanctification.json
    
    # Install hardcoded data (legacy)
    python -m sbc.core_passages --db compendium.sqlite add-romans8-sanctification-core
"""

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


# ========== Data Models ==========

@dataclass
class VerseNoteRow:
    """Single verse note (midrash, summary, etc.)."""
    ref: str
    note_kind: str
    unit_id: str
    title: Optional[str]
    note_md: str
    tags: str
    sort_order: int


@dataclass
class GreekMarginRow:
    """Single Greek margin annotation (word/phrase study)."""
    ref: str
    unit_id: str
    lemma_greek: str
    translit: str
    morph: str
    gloss: str
    note_md: str
    sort_order: int


@dataclass
class CorePassageUnit:
    """Complete core passage unit with metadata and annotations."""
    unit_id: str
    category: str
    title: str
    range_ref: str
    summary_md: str
    tags: str
    verse_notes: List[VerseNoteRow]
    greek_margins: List[GreekMarginRow]


# ========== Database Utilities ==========

def resolve_db_path(db_arg: Optional[str]) -> Path:
    """Resolve database path from CLI arg or environment variable."""
    if db_arg:
        return Path(db_arg)
    env = os.getenv("SBC_DB", "")
    if env:
        return Path(env)
    raise RuntimeError("No --db argument or SBC_DB environment variable set.")


def connect(db_path: Path) -> sqlite3.Connection:
    """Open database connection with Row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def table_has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    """Check if table has specified column."""
    pragma = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == col for r in pragma)


def get_verse_table_name(conn: sqlite3.Connection) -> str:
    """
    Auto-detect which verse table to use.
    Priority: berean_verses > verses_normalized > verses
    """
    for table in ["berean_verses", "verses_normalized", "verses"]:
        if conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table,)
        ).fetchone():
            return table
    raise RuntimeError("No verse table found (expected: berean_verses, verses_normalized, or verses)")


def require_verse_table_with_ref(conn: sqlite3.Connection, table_name: str) -> None:
    """Validate verse table has required columns."""
    if not conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,)
    ).fetchone():
        raise RuntimeError(f"Missing required table: {table_name}")
    
    # For berean_verses, check 'verse_ref' column
    # For verses/verses_normalized, check 'ref' column
    ref_col = "verse_ref" if table_name == "berean_verses" else "ref"
    
    if not table_has_column(conn, table_name, ref_col):
        raise RuntimeError(f"{table_name} table must contain a '{ref_col}' column.")
    
    if not table_has_column(conn, table_name, "id"):
        raise RuntimeError(f"{table_name} table must contain an 'id' primary key column.")


def require_verses_ref(conn: sqlite3.Connection) -> None:
    """Legacy function - now auto-detects table."""
    table_name = get_verse_table_name(conn)
    require_verse_table_with_ref(conn, table_name)


def get_verse_ids_by_ref(conn: sqlite3.Connection, refs: Iterable[str]) -> Dict[str, int]:
    """Get verse IDs from refs, supporting multiple table formats."""
    refs = list(refs)
    if not refs:
        return {}
    
    table_name = get_verse_table_name(conn)
    ref_col = "verse_ref" if table_name == "berean_verses" else "ref"
    
    # For berean_verses, try both "Romans 8:26" and "Romans|8:26" formats
    if table_name == "berean_verses":
        expanded_refs = []
        ref_map = {}  # maps expanded ref -> original ref
        for r in refs:
            expanded_refs.append(r)
            ref_map[r] = r
            # Add alternate format
            alt = r.replace(" ", "|") if " " in r else r.replace("|", " ")
            expanded_refs.append(alt)
            ref_map[alt] = r
        
        placeholders = ",".join("?" for _ in expanded_refs)
        rows = conn.execute(
            f"SELECT id, {ref_col} FROM {table_name} WHERE {ref_col} IN ({placeholders})",
            expanded_refs,
        ).fetchall()
        
        found = {}
        for row in rows:
            original_ref = ref_map[row[ref_col]]
            found[original_ref] = int(row["id"])
    else:
        placeholders = ",".join("?" for _ in refs)
        rows = conn.execute(
            f"SELECT id, {ref_col} FROM {table_name} WHERE {ref_col} IN ({placeholders})",
            refs,
        ).fetchall()
        found = {r[ref_col]: int(r["id"]) for r in rows}
    
    missing = [r for r in refs if r not in found]
    if missing:
        raise RuntimeError(
            f"Cannot install core passage unit. Missing {table_name}.{ref_col} values:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + f"\n\nFix: ensure your {table_name} table contains these verse references."
        )
    return found


# ========== Schema Management ==========

def cmd_init_schema(args: argparse.Namespace) -> int:
    """Create or verify schema for core passages system."""
    db_path = resolve_db_path(args.db)
    
    with connect(db_path) as conn:
        # Create core_passages table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS core_passages (
                unit_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                range_ref TEXT NOT NULL,
                summary_md TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT ''
            );
        """)
        
        # Create verse_notes table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verse_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verse_id INTEGER NOT NULL,
                note_kind TEXT NOT NULL DEFAULT 'midrash',
                unit_id TEXT,
                title TEXT,
                note_md TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (unit_id) REFERENCES core_passages(unit_id)
            );
        """)
        
        # Create greek_margins table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS greek_margins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verse_id INTEGER NOT NULL,
                unit_id TEXT,
                lemma_greek TEXT NOT NULL,
                translit TEXT NOT NULL,
                morph TEXT NOT NULL,
                gloss TEXT NOT NULL,
                note_md TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (unit_id) REFERENCES core_passages(unit_id)
            );
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verse_notes_verse_id ON verse_notes(verse_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verse_notes_unit_id ON verse_notes(unit_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_greek_margins_verse_id ON greek_margins(verse_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_greek_margins_unit_id ON greek_margins(unit_id);")
        
        conn.commit()
    
    print("[ok] Schema initialized: core_passages, verse_notes, greek_margins")
    return 0


# ========== Data Installation ==========

def install_unit(conn: sqlite3.Connection, unit: CorePassageUnit) -> tuple[int, int]:
    """
    Install a complete core passage unit.
    
    Returns:
        (notes_added, margins_added)
    """
    require_verses_ref(conn)
    
    # Collect all verse refs
    all_refs = set()
    for note in unit.verse_notes:
        all_refs.add(note.ref)
    for margin in unit.greek_margins:
        all_refs.add(margin.ref)
    
    # Get verse IDs
    verse_id_map = get_verse_ids_by_ref(conn, all_refs)
    
    # Insert core passage metadata (upsert)
    conn.execute("""
        INSERT INTO core_passages (unit_id, category, title, range_ref, summary_md, tags)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(unit_id) DO UPDATE SET
            category = excluded.category,
            title = excluded.title,
            range_ref = excluded.range_ref,
            summary_md = excluded.summary_md,
            tags = excluded.tags
    """, (unit.unit_id, unit.category, unit.title, unit.range_ref, unit.summary_md, unit.tags))
    
    # Insert verse notes
    notes_added = 0
    for note in unit.verse_notes:
        verse_id = verse_id_map[note.ref]
        conn.execute("""
            INSERT OR IGNORE INTO verse_notes (verse_id, note_kind, unit_id, title, note_md, tags, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (verse_id, note.note_kind, note.unit_id, note.title, note.note_md, note.tags, note.sort_order))
        notes_added += conn.execute("SELECT changes()").fetchone()[0]
    
    # Insert greek margins
    margins_added = 0
    for margin in unit.greek_margins:
        verse_id = verse_id_map[margin.ref]
        conn.execute("""
            INSERT OR IGNORE INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (verse_id, margin.unit_id, margin.lemma_greek, margin.translit, margin.morph, margin.gloss, margin.note_md, margin.sort_order))
        margins_added += conn.execute("SELECT changes()").fetchone()[0]
    
    return notes_added, margins_added


# ========== JSON Loader ==========

def load_unit_from_json_files(
    greek_margins_json: Path,
    verse_notes_json: Path,
    core_passage_json: Path
) -> CorePassageUnit:
    """
    Load a CorePassageUnit from STUDIES/ JSON files.
    
    Args:
        greek_margins_json: Path to STUDIES/greek-margins/passage.json
        verse_notes_json: Path to STUDIES/verse-notes/passage.json
        core_passage_json: Path to STUDIES/core-passages/category.json
    
    Returns:
        CorePassageUnit with data from JSON files
    """
    # Load greek margins
    with open(greek_margins_json, "r", encoding="utf-8") as f:
        gm_data = json.load(f)
    
    greek_margins = [
        GreekMarginRow(
            ref=ann["verse_ref"],
            unit_id=gm_data["unit_id"],
            lemma_greek=ann["lemma_greek"],
            translit=ann["translit"],
            morph=ann["morph"],
            gloss=ann["gloss"],
            note_md=ann.get("note_md", ""),
            sort_order=ann["sort_order"]
        )
        for ann in gm_data["annotations"]
    ]
    
    # Load verse notes
    with open(verse_notes_json, "r", encoding="utf-8") as f:
        vn_data = json.load(f)
    
    verse_notes = [
        VerseNoteRow(
            ref=note["verse_ref"],
            note_kind=note.get("note_kind", "midrash"),
            unit_id=vn_data["unit_id"],
            title=note.get("title"),
            note_md=note["note_md"],
            tags=note.get("tags", ""),
            sort_order=note["sort_order"]
        )
        for note in vn_data["notes"]
    ]
    
    # Load core passage metadata
    with open(core_passage_json, "r", encoding="utf-8") as f:
        cp_data = json.load(f)
    
    # Find matching passage by unit_id
    passage = None
    for p in cp_data["passages"]:
        if p["unit_id"] == gm_data["unit_id"]:
            passage = p
            break
    
    if not passage:
        raise ValueError(
            f"No passage with unit_id={gm_data['unit_id']} found in {core_passage_json}"
        )
    
    return CorePassageUnit(
        unit_id=passage["unit_id"],
        category=passage["category"],
        title=passage["title"],
        range_ref=passage["range_ref"],
        summary_md=passage["summary_md"],
        tags=passage.get("tags", ""),
        verse_notes=verse_notes,
        greek_margins=greek_margins
    )


# ========== Hardcoded Data (Legacy) ==========

def romans8_sanctification_core_unit() -> CorePassageUnit:
    """
    DEPRECATED: Hardcoded Romans 8:18-30 data.
    Use JSON files in STUDIES/ directory instead.
    """
    verse_notes = [
        VerseNoteRow("Romans 8:18", "midrash", "SANCT_CORE_ROM_008_018_030", None,
                     "The *sufferings of the present time* (τὰ παθήματα τοῦ νῦν καιροῦ) create a context of eschatological hope.", "", 10),
        VerseNoteRow("Romans 8:19", "midrash", "SANCT_CORE_ROM_008_018_030", None,
                     "All creation awaits the *revelation of the sons of God* (ἀποκάλυψιν τῶν υἱῶν τοῦ θεοῦ).", "", 20),
        # ... Add remaining 13 notes as needed
    ]
    
    greek_margins = [
        GreekMarginRow("Romans 8:18", "SANCT_CORE_ROM_008_018_030", "παθήματα", "pathēmata", "N-NPN",
                       "sufferings", "Suffering as birth pangs leading to glory", 10),
        GreekMarginRow("Romans 8:19", "SANCT_CORE_ROM_008_018_030", "ἀποκάλυψις", "apokalupsis", "N-ASF",
                       "revelation", "Unveiling of believers' glorified state", 20),
        # ... Add remaining 18 annotations as needed
    ]
    
    return CorePassageUnit(
        unit_id="SANCT_CORE_ROM_008_018_030",
        category="sanctification",
        title="Romans 8:18–30 — Sanctification Through Groaning, Help, and Conformity",
        range_ref="Romans 8:18-30",
        summary_md="Paul presents sanctification as a cosmic process: creation groans, believers groan in hope, and the Spirit intercedes with groans too deep for words.",
        tags="sanctification,suffering,hope,predestination",
        verse_notes=verse_notes,
        greek_margins=greek_margins
    )


# ========== CLI Commands ==========

def cmd_add_romans8(args: argparse.Namespace) -> int:
    """Install hardcoded Romans 8:18-30 core passage (DEPRECATED)."""
    print("[warn] This command uses hardcoded data. Consider using 'add-from-json' with STUDIES/ JSON files.")
    
    db_path = resolve_db_path(args.db)
    unit = romans8_sanctification_core_unit()
    
    with connect(db_path) as conn:
        try:
            notes_added, margins_added = install_unit(conn, unit)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    print(f"[ok] Installed core passage unit {unit.unit_id}")
    print(f"  - verse_notes added:   {notes_added}")
    print(f"  - greek_margins added: {margins_added}")
    print("  - core_passages upserted: 1")
    return 0


def cmd_add_from_json(args: argparse.Namespace) -> int:
    """Install core passage from JSON files."""
    db_path = resolve_db_path(args.db)
    
    unit = load_unit_from_json_files(
        Path(args.greek_margins),
        Path(args.verse_notes),
        Path(args.core_passage)
    )
    
    with connect(db_path) as conn:
        try:
            notes_added, margins_added = install_unit(conn, unit)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    print(f"[ok] Installed core passage unit {unit.unit_id}")
    print(f"  - verse_notes added:   {notes_added}")
    print(f"  - greek_margins added: {margins_added}")
    print("  - core_passages upserted: 1")
    return 0


# ========== CLI Entry Point ==========

def build_parser() -> argparse.ArgumentParser:
    """Build argument parser with subcommands."""
    p = argparse.ArgumentParser(
        prog="sbc.core_passages",
        description="Core passage installer for Study Bible Compendium"
    )
    p.add_argument("--db", help="Path to SQLite DB (or set SBC_DB).", default=None)

    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("init-schema", help="Create/ensure core_passages, verse_notes, greek_margins tables + indexes.")
    s1.set_defaults(func=cmd_init_schema)

    s2 = sub.add_parser("add-romans8-sanctification-core", help="Install Romans 8:18–30 as sanctification core passage (hardcoded - DEPRECATED).")
    s2.set_defaults(func=cmd_add_romans8)
    
    s3 = sub.add_parser("add-from-json", help="Install core passage from JSON files (recommended).")
    s3.add_argument("--greek-margins", required=True, help="Path to greek-margins JSON file")
    s3.add_argument("--verse-notes", required=True, help="Path to verse-notes JSON file")
    s3.add_argument("--core-passage", required=True, help="Path to core-passages JSON file")
    s3.set_defaults(func=cmd_add_from_json)

    return p


def main(argv=None):
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    
    try:
        return args.func(args)
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
