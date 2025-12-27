"""
Patch for sbc/core_passages.py - Add JSON loading support

Changes:
1. Make verse table configurable (berean_verses vs verses)
2. Add load_unit_from_json() to read STUDIES/ JSON files
3. Keep Python dataclass validation
4. Deprecate hardcoded romans8_sanctification_core_unit()
"""

# Add to imports section (after existing imports):
import json
from pathlib import Path

# Add after connect() function:

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


# Replace require_verses_ref() with:

def require_verses_ref(conn: sqlite3.Connection) -> None:
    """Legacy function - now auto-detects table."""
    table_name = get_verse_table_name(conn)
    require_verse_table_with_ref(conn, table_name)


# Replace get_verse_ids_by_ref() with:

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


# Add new function to load from JSON:

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


# Add new CLI command:

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
    
    print(f"OK: installed core passage unit {unit.unit_id}")
    print(f"  - verse_notes added:   {notes_added}")
    print(f"  - greek_margins added: {margins_added}")
    print("  - core_passages upserted: 1")
    return 0


# Update build_parser() - add new subcommand:

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbc.core_passages", description="Core passage installer for Study Bible Compendium")
    p.add_argument("--db", help="Path to SQLite DB (or set SBC_DB).", default=None)

    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("init-schema", help="Create/ensure core_passages, verse_notes, greek_margins tables + indexes.")
    s1.set_defaults(func=cmd_init_schema)

    s2 = sub.add_parser("add-romans8-sanctification-core", help="Install Romans 8:18–30 as the sanctification core passage (hardcoded).")
    s2.set_defaults(func=cmd_add_romans8)
    
    # NEW: JSON loader command
    s3 = sub.add_parser("add-from-json", help="Install core passage from JSON files (recommended).")
    s3.add_argument("--greek-margins", required=True, help="Path to greek-margins JSON file")
    s3.add_argument("--verse-notes", required=True, help="Path to verse-notes JSON file")
    s3.add_argument("--core-passage", required=True, help="Path to core-passages JSON file")
    s3.set_defaults(func=cmd_add_from_json)

    return p
