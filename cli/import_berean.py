#!/usr/bin/env python3
"""
Import Berean Bible data into Study Bible Compendium database.

Imports from CSV files:
- berean_text.csv: Verse text in multiple translations (BGB, BIB, BLB, BSB)
- berean_tables.csv: Interlinear Greek with Strong's numbers and parsing

Creates tables:
- berean_verses: Complete verse text
- berean_words: Individual Greek words with Strong's numbers
- berean_strongs: Strong's number definitions
"""

import sys
import csv
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


def utc_now_iso() -> str:
    """RFC-3339-like UTC timestamp, second precision."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_berean_schema(conn: sqlite3.Connection) -> None:
    """Create tables for Berean Bible data."""
    print("[info] Creating Berean Bible schema...")
    
    conn.executescript("""
        -- Verse text table
        CREATE TABLE IF NOT EXISTS berean_verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verse_ref TEXT NOT NULL UNIQUE,  -- e.g., "Matthew 1:1"
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            bgb_text TEXT,  -- Berean Greek Bible (pure Greek)
            bib_text TEXT,  -- Berean Interlinear Bible (Greek with glosses)
            blb_text TEXT,  -- Berean Literal Bible (English literal)
            bsb_text TEXT,  -- Berean Study Bible (English readable)
            created_utc TEXT NOT NULL,
            UNIQUE(book, chapter, verse)
        );
        
        -- Greek word tokens with Strong's numbers
        CREATE TABLE IF NOT EXISTS berean_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verse_ref TEXT NOT NULL,  -- e.g., "Matthew|1:1"
            word_order INTEGER NOT NULL,  -- Position in verse
            greek_word TEXT NOT NULL,  -- Original Greek: Βίβλος
            transliteration TEXT,  -- Romanized: Biblos
            strongs_number INTEGER,  -- e.g., 976
            parsing TEXT,  -- Grammar: "N-NFS" (Noun - Nominative Feminine Singular)
            parsing_full TEXT,  -- Full description
            english_gloss TEXT,  -- "[The] book"
            created_utc TEXT NOT NULL,
            FOREIGN KEY (verse_ref) REFERENCES berean_verses(verse_ref)
        );
        
        -- Strong's number definitions (unique)
        CREATE TABLE IF NOT EXISTS berean_strongs (
            strongs_number INTEGER PRIMARY KEY,
            definition TEXT NOT NULL,
            created_utc TEXT NOT NULL
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_berean_verses_ref ON berean_verses(verse_ref);
        CREATE INDEX IF NOT EXISTS idx_berean_verses_book ON berean_verses(book, chapter, verse);
        CREATE INDEX IF NOT EXISTS idx_berean_words_verse ON berean_words(verse_ref);
        CREATE INDEX IF NOT EXISTS idx_berean_words_strongs ON berean_words(strongs_number);
    """)
    
    conn.commit()
    print("[ok] Schema created")


def parse_verse_ref(ref: str) -> tuple[str, int, int]:
    """
    Parse verse reference into (book, chapter, verse).
    
    Handles both formats:
        "Matthew 1:1" -> ("Matthew", 1, 1)  # Space format
        "Matthew|1:1" -> ("Matthew", 1, 1)  # Pipe format
    """
    # Normalize pipe format to space format
    ref = ref.replace('|', ' ')
    
    parts = ref.rsplit(' ', 1)  # Split from right: "Matthew 1:1" -> ["Matthew", "1:1"]
    book = parts[0]
    chap_verse = parts[1].split(':')
    chapter = int(chap_verse[0])
    verse = int(chap_verse[1])
    return book, chapter, verse


def import_berean_text(conn: sqlite3.Connection, csv_path: Path) -> int:
    """Import berean_text.csv into berean_verses table."""
    print(f"[info] Importing verse text from {csv_path.name}...")
    
    if not csv_path.exists():
        print(f"[error] File not found: {csv_path}")
        return 0
    
    cursor = conn.cursor()
    timestamp = utc_now_iso()
    row_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip copyright lines manually before creating DictReader
        lines = f.readlines()
        # Find the header row (contains "Verse")
        header_idx = next(i for i, line in enumerate(lines) if 'Verse' in line and 'BGB' in line)
        
        # Create reader starting from header
        from io import StringIO
        csv_content = ''.join(lines[header_idx:])
        reader = csv.DictReader(StringIO(csv_content))
        
        for row in reader:
            verse_ref = row.get('Verse', '').strip()
            if not verse_ref or not ' ' in verse_ref:
                continue  # Skip invalid rows
            
            try:
                book, chapter, verse = parse_verse_ref(verse_ref)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO berean_verses 
                    (verse_ref, book, chapter, verse, bgb_text, bib_text, blb_text, bsb_text, created_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    verse_ref,
                    book,
                    chapter,
                    verse,
                    row.get('BGB - Berean Greek Bible', '').strip(),
                    row.get('BIB - Berean Interlinear Bible', '').strip(),
                    row.get('BLB - Berean Literal Bible', '').strip(),
                    row.get('BSB - Berean Study Bible', '').strip(),
                    timestamp
                ))
                
                row_count += 1
                
                if row_count % 500 == 0:
                    print(f"[info] Imported {row_count} verses...")
                    conn.commit()
                    
            except Exception as e:
                print(f"[warn] Failed to import verse '{verse_ref}': {e}")
                continue
    
    conn.commit()
    print(f"[ok] Imported {row_count} verses")
    return row_count


def import_berean_tables(conn: sqlite3.Connection, csv_path: Path) -> tuple[int, int]:
    """Import berean_tables.csv into berean_words and berean_strongs tables."""
    print(f"[info] Importing interlinear data from {csv_path.name}...")
    
    if not csv_path.exists():
        print(f"[error] File not found: {csv_path}")
        return 0, 0
    
    cursor = conn.cursor()
    timestamp = utc_now_iso()
    word_count = 0
    strongs_set = {}  # Track unique Strong's numbers
    
    # berean_tables.csv has NO header row - row 1 is copyright, row 2+ are data
    # Column positions (0-indexed):
    # [7] = Verse ref (Matthew|1:1)
    # [12] = Greek word (Βίβλος)
    # [13] = Transliteration (Biblos)
    # [14-16] = English glosses (BIB, BLB, BSB)
    # [17] = Parsing code (N-NFS)
    # [18] = Parsing full (Noun - Nominative Feminine Singular)
    # [19] = Strong's number (976)
    # [20] = Lexical definition
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)  # Skip copyright row
        
        current_verse = None
        word_order = 0
        
        for row in reader:
            # Skip empty rows or rows with insufficient columns
            if len(row) < 20:
                continue
                
            verse_ref = row[7].strip() if len(row) > 7 else ''
            
            # Skip rows without verse references
            if not verse_ref or '|' not in verse_ref:
                continue
            
            # Normalize verse_ref to space format (Matthew|1:1 -> Matthew 1:1)
            verse_ref = verse_ref.replace('|', ' ')
            
            # Reset word order for new verse
            if verse_ref != current_verse:
                current_verse = verse_ref
                word_order = 0
            
            word_order += 1
            
            # Extract data using positional indices
            greek_word = row[12].strip() if len(row) > 12 else ''
            if not greek_word:
                continue  # Skip empty words
            
            transliteration = row[13].strip() if len(row) > 13 else ''
            
            # English glosses from columns 14-16 (BIB, BLB, BSB)
            english_gloss = ''
            for idx in [14, 15, 16]:
                if len(row) > idx and row[idx].strip():
                    english_gloss = row[idx].strip()
                    break
            
            parsing = row[17].strip() if len(row) > 17 else ''
            parsing_full = row[18].strip() if len(row) > 18 else ''
            strongs_str = row[19].strip() if len(row) > 19 else ''
            definition = row[20].strip() if len(row) > 20 else ''
            
            # Parse Strong's number
            strongs_number = None
            if strongs_str and strongs_str.isdigit():
                strongs_number = int(strongs_str)
                
                # Store Strong's definition
                if strongs_number and definition and strongs_number not in strongs_set:
                    strongs_set[strongs_number] = definition
            
            try:
                cursor.execute("""
                    INSERT INTO berean_words 
                    (verse_ref, word_order, greek_word, transliteration, strongs_number, 
                     parsing, parsing_full, english_gloss, created_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    verse_ref,
                    word_order,
                    greek_word,
                    transliteration,
                    strongs_number,
                    parsing,
                    parsing_full,
                    english_gloss,
                    timestamp
                ))
                
                word_count += 1
                
                if word_count % 1000 == 0:
                    print(f"[info] Imported {word_count} words...")
                    conn.commit()
                    
            except Exception as e:
                print(f"[warn] Failed to import word from '{verse_ref}': {e}")
                continue
    
    # Insert Strong's definitions
    print(f"[info] Importing {len(strongs_set)} Strong's definitions...")
    for strongs_num, definition in strongs_set.items():
        cursor.execute("""
            INSERT OR REPLACE INTO berean_strongs 
            (strongs_number, definition, created_utc)
            VALUES (?, ?, ?)
        """, (strongs_num, definition, timestamp))
    
    conn.commit()
    print(f"[ok] Imported {word_count} words and {len(strongs_set)} Strong's definitions")
    return word_count, len(strongs_set)


def run_import(db_path: Path, berean_dir: Path) -> None:
    """Run the complete Berean Bible import process."""
    print(f"[info] Starting Berean Bible import")
    print(f"[info] Database: {db_path}")
    print(f"[info] Source directory: {berean_dir}")
    
    # Connect to database
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Create schema
        create_berean_schema(conn)
        
        # Import verse text
        text_csv = berean_dir / "berean_text.csv"
        verse_count = import_berean_text(conn, text_csv)
        
        # Import interlinear data
        tables_csv = berean_dir / "berean_tables.csv"
        word_count, strongs_count = import_berean_tables(conn, tables_csv)
        
        print("\n[ok] Import complete!")
        print(f"  - {verse_count:,} verses")
        print(f"  - {word_count:,} Greek words")
        print(f"  - {strongs_count:,} Strong's definitions")
        
    except Exception as e:
        print(f"[error] Import failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


def main(argv: list[str]) -> None:
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Import Berean Bible CSV data into Study Bible Compendium database",
        epilog="Example: python import_berean.py --db compendium.sqlite --berean-dir 'Berean Bible'"
    )
    parser.add_argument(
        "--db",
        default="compendium.sqlite",
        help="Path to SQLite database (default: compendium.sqlite)"
    )
    parser.add_argument(
        "--berean-dir",
        default="Berean Bible",
        help="Directory containing berean_text.csv and berean_tables.csv (default: 'Berean Bible')"
    )
    
    args = parser.parse_args(argv)
    
    db_path = Path(args.db)
    berean_dir = Path(args.berean_dir)
    
    if not berean_dir.exists():
        print(f"[error] Berean directory not found: {berean_dir}")
        sys.exit(1)
    
    run_import(db_path, berean_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
