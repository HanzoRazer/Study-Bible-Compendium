#!/usr/bin/env python3
"""
import_annotations.py - Convert JSON annotation files to SQL inserts

Usage:
    python cli/import_annotations.py --type greek-margins --input STUDIES/greek-margins/romans_8.json
    python cli/import_annotations.py --type core-passages --input STUDIES/core-passages/sanctification.json
    python cli/import_annotations.py --type verse-notes --input STUDIES/verse-notes/romans_8.json
    
    # Batch import all files of a type
    python cli/import_annotations.py --type greek-margins --all
    
    # Apply directly to database
    python cli/import_annotations.py --type greek-margins --input file.json --apply
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from sbc.paths import PROJECT_ROOT, DB_PATH
from sbc.util import info, warn, ok


def validate_greek_margins(data: Dict[str, Any]) -> List[str]:
    """Validate greek-margins JSON structure."""
    errors = []
    
    required_top = ["unit_id", "passage", "annotations"]
    for field in required_top:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    if "annotations" in data:
        for idx, ann in enumerate(data["annotations"]):
            required_ann = ["verse_ref", "sort_order", "lemma_greek", "translit", "morph", "gloss"]
            for field in required_ann:
                if field not in ann:
                    errors.append(f"Annotation {idx}: missing field '{field}'")
            
            # Check for duplicate sort orders
            sort_orders = [a.get("sort_order") for a in data["annotations"]]
            if len(sort_orders) != len(set(sort_orders)):
                errors.append("Duplicate sort_order values detected")
                break
    
    return errors


def validate_core_passages(data: Dict[str, Any]) -> List[str]:
    """Validate core-passages JSON structure."""
    errors = []
    
    if "passages" not in data:
        errors.append("Missing required field: passages")
        return errors
    
    for idx, passage in enumerate(data["passages"]):
        required = ["unit_id", "category", "title", "range_ref", "summary_md"]
        for field in required:
            if field not in passage:
                errors.append(f"Passage {idx}: missing field '{field}'")
    
    return errors


def validate_verse_notes(data: Dict[str, Any]) -> List[str]:
    """Validate verse-notes JSON structure."""
    errors = []
    
    required_top = ["unit_id", "passage", "notes"]
    for field in required_top:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    if "notes" in data:
        for idx, note in enumerate(data["notes"]):
            required_note = ["verse_ref", "note_kind", "note_md", "sort_order"]
            for field in required_note:
                if field not in note:
                    errors.append(f"Note {idx}: missing field '{field}'")
    
    return errors


def generate_greek_margins_sql(data: Dict[str, Any]) -> str:
    """Generate SQL INSERT statements for greek_margins table."""
    unit_id = data["unit_id"]
    passage = data["passage"]
    
    sql_parts = [
        f"-- Greek margin annotations for {passage}",
        f"-- Unit: {unit_id}",
        ""
    ]
    
    for ann in data["annotations"]:
        verse_ref = ann["verse_ref"]
        sort_order = ann["sort_order"]
        lemma = ann["lemma_greek"]
        translit = ann["translit"]
        morph = ann["morph"]
        gloss = ann["gloss"]
        note_md = ann.get("note_md", "")
        
        # Escape single quotes for SQL
        lemma_esc = lemma.replace("'", "''")
        translit_esc = translit.replace("'", "''")
        morph_esc = morph.replace("'", "''")
        gloss_esc = gloss.replace("'", "''")
        note_esc = note_md.replace("'", "''")
        
        sql = f"""-- {verse_ref} ({translit})
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
SELECT id, '{unit_id}',
'{lemma_esc}', '{translit_esc}', '{morph_esc}', '{gloss_esc}',
'{note_esc}',
{sort_order}
FROM berean_verses WHERE verse_ref IN ('{verse_ref}', '{verse_ref.replace(' ', '|')}');
"""
        sql_parts.append(sql)
    
    return "\n".join(sql_parts)


def generate_core_passages_sql(data: Dict[str, Any]) -> str:
    """Generate SQL INSERT statements for core_passages table."""
    sql_parts = [
        "-- Core passages registry",
        ""
    ]
    
    for passage in data["passages"]:
        unit_id = passage["unit_id"]
        category = passage["category"]
        title = passage["title"]
        range_ref = passage["range_ref"]
        summary_md = passage["summary_md"]
        tags = passage.get("tags", "")
        
        # Escape single quotes
        title_esc = title.replace("'", "''")
        summary_esc = summary_md.replace("'", "''")
        tags_esc = tags.replace("'", "''")
        
        sql = f"""INSERT OR IGNORE INTO core_passages (unit_id, category, title, range_ref, summary_md, tags)
VALUES (
  '{unit_id}',
  '{category}',
  '{title_esc}',
  '{range_ref}',
  '{summary_esc}',
  '{tags_esc}'
);
"""
        sql_parts.append(sql)
    
    return "\n".join(sql_parts)


def generate_verse_notes_sql(data: Dict[str, Any]) -> str:
    """Generate SQL INSERT statements for verse_notes table."""
    unit_id = data["unit_id"]
    passage = data["passage"]
    
    sql_parts = [
        f"-- Verse notes for {passage}",
        f"-- Unit: {unit_id}",
        ""
    ]
    
    for note in data["notes"]:
        verse_ref = note["verse_ref"]
        note_kind = note.get("note_kind", "midrash")
        title = note.get("title", "")
        note_md = note["note_md"]
        tags = note.get("tags", "")
        sort_order = note["sort_order"]
        
        # Escape single quotes
        title_esc = title.replace("'", "''")
        note_esc = note_md.replace("'", "''")
        tags_esc = tags.replace("'", "''")
        
        sql = f"""INSERT INTO verse_notes (verse_id, note_kind, unit_id, title, note_md, tags, sort_order)
SELECT id, '{note_kind}', '{unit_id}', '{title_esc}', '{note_esc}', '{tags_esc}', {sort_order}
FROM berean_verses WHERE verse_ref IN ('{verse_ref}', '{verse_ref.replace(' ', '|')}');
"""
        sql_parts.append(sql)
    
    return "\n".join(sql_parts)


def process_file(filepath: Path, annotation_type: str, apply_to_db: bool = False) -> None:
    """Process a single JSON annotation file."""
    info(f"Processing: {filepath}")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        warn(f"Invalid JSON: {e}")
        return
    except Exception as e:
        warn(f"Error reading file: {e}")
        return
    
    # Validate
    if annotation_type == "greek-margins":
        errors = validate_greek_margins(data)
        sql = generate_greek_margins_sql(data) if not errors else ""
    elif annotation_type == "core-passages":
        errors = validate_core_passages(data)
        sql = generate_core_passages_sql(data) if not errors else ""
    elif annotation_type == "verse-notes":
        errors = validate_verse_notes(data)
        sql = generate_verse_notes_sql(data) if not errors else ""
    else:
        warn(f"Unknown annotation type: {annotation_type}")
        return
    
    if errors:
        warn(f"Validation errors in {filepath}:")
        for err in errors:
            print(f"  - {err}")
        return
    
    ok(f"Validation passed")
    
    # Output SQL
    if apply_to_db:
        info(f"Applying to database: {DB_PATH}")
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.executescript(sql)
            conn.commit()
            conn.close()
            ok("Applied to database")
        except Exception as e:
            warn(f"Database error: {e}")
    else:
        # Generate SQL file
        sql_output = filepath.parent.parent / "data" / f"{filepath.stem}.sql"
        sql_output.write_text(sql, encoding="utf-8")
        ok(f"Generated SQL: {sql_output}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import annotation JSON files")
    parser.add_argument("--type", required=True, 
                       choices=["greek-margins", "core-passages", "verse-notes"],
                       help="Type of annotation")
    parser.add_argument("--input", type=Path, help="Input JSON file")
    parser.add_argument("--all", action="store_true", 
                       help="Process all JSON files in STUDIES/<type>/")
    parser.add_argument("--apply", action="store_true", 
                       help="Apply SQL directly to database")
    
    args = parser.parse_args(argv)
    
    if args.all:
        studies_dir = PROJECT_ROOT / "STUDIES" / args.type
        if not studies_dir.exists():
            warn(f"Directory not found: {studies_dir}")
            sys.exit(1)
        
        json_files = list(studies_dir.glob("*.json"))
        if not json_files:
            warn(f"No JSON files found in {studies_dir}")
            sys.exit(1)
        
        info(f"Found {len(json_files)} JSON files")
        for filepath in json_files:
            process_file(filepath, args.type, args.apply)
    elif args.input:
        if not args.input.exists():
            warn(f"File not found: {args.input}")
            sys.exit(1)
        process_file(args.input, args.type, args.apply)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
