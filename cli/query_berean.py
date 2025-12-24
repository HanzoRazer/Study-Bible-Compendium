#!/usr/bin/env python3
"""
Query Berean Bible data by Strong's numbers or Greek words.

Search capabilities:
- Find all verses containing a specific Strong's number
- Search for Greek words (exact or partial match)
- List all uses of a word with context
- Show word definitions and parsing information
"""

import sys
import sqlite3
from pathlib import Path
from typing import Optional, List


def connect_db(db_path: Path) -> sqlite3.Connection:
    """Connect to database and verify Berean tables exist."""
    if not db_path.exists():
        print(f"[error] Database not found: {db_path}")
        print("[info] Run: python import_berean.py --db compendium.sqlite")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Check if tables exist
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('berean_verses', 'berean_words', 'berean_strongs')
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    if len(tables) < 3:
        print("[error] Berean tables not found in database")
        print("[info] Run: python import_berean.py --db compendium.sqlite")
        sys.exit(1)
    
    return conn


def search_by_strongs(conn: sqlite3.Connection, strongs_num: int, limit: Optional[int] = None) -> None:
    """Find all verses containing a specific Strong's number."""
    cursor = conn.cursor()
    
    # Get Strong's definition
    cursor.execute("SELECT definition FROM berean_strongs WHERE strongs_number = ?", (strongs_num,))
    row = cursor.fetchone()
    
    if not row:
        print(f"[warn] Strong's number {strongs_num} not found")
        return
    
    definition = row['definition']
    print(f"\n[ok] Strong's G{strongs_num}: {definition}\n")
    
    # Find all words with this Strong's number
    sql = """
        SELECT DISTINCT w.verse_ref, w.greek_word, w.transliteration, w.english_gloss,
               v.bsb_text
        FROM berean_words w
        JOIN berean_verses v ON w.verse_ref = v.verse_ref
        WHERE w.strongs_number = ?
        ORDER BY v.book, v.chapter, v.verse
    """
    
    if limit:
        sql += f" LIMIT {limit}"
    
    cursor.execute(sql, (strongs_num,))
    rows = cursor.fetchall()
    
    if not rows:
        print(f"[warn] No verses found with Strong's G{strongs_num}")
        return
    
    print(f"Found {len(rows)} occurrences:\n")
    
    for row in rows:
        verse_ref = row['verse_ref'].replace('|', ' ')  # "Matthew|1:1" -> "Matthew 1:1"
        greek = row['greek_word']
        trans = row['transliteration'] or ''
        gloss = row['english_gloss'] or ''
        text = row['bsb_text']
        
        print(f"{verse_ref}")
        print(f"  Greek: {greek} ({trans}) - {gloss}")
        print(f"  Text: {text}")
        print()


def search_by_greek(conn: sqlite3.Connection, greek_word: str, exact: bool = True, limit: Optional[int] = None) -> None:
    """Search for Greek words (exact or partial match)."""
    cursor = conn.cursor()
    
    if exact:
        sql = """
            SELECT DISTINCT w.verse_ref, w.greek_word, w.transliteration, w.strongs_number,
                   w.english_gloss, s.definition, v.bsb_text
            FROM berean_words w
            LEFT JOIN berean_strongs s ON w.strongs_number = s.strongs_number
            JOIN berean_verses v ON w.verse_ref = v.verse_ref
            WHERE w.greek_word = ?
            ORDER BY v.book, v.chapter, v.verse
        """
        params = (greek_word,)
    else:
        sql = """
            SELECT DISTINCT w.verse_ref, w.greek_word, w.transliteration, w.strongs_number,
                   w.english_gloss, s.definition, v.bsb_text
            FROM berean_words w
            LEFT JOIN berean_strongs s ON w.strongs_number = s.strongs_number
            JOIN berean_verses v ON w.verse_ref = v.verse_ref
            WHERE w.greek_word LIKE ?
            ORDER BY v.book, v.chapter, v.verse
        """
        params = (f"%{greek_word}%",)
    
    if limit:
        sql += f" LIMIT {limit}"
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    if not rows:
        match_type = "exact match for" if exact else "matches for"
        print(f"[warn] No {match_type} Greek word '{greek_word}'")
        return
    
    match_type = "exact match" if exact else "matches"
    print(f"\n[ok] Found {len(rows)} {match_type} for '{greek_word}':\n")
    
    for row in rows:
        verse_ref = row['verse_ref'].replace('|', ' ')
        greek = row['greek_word']
        trans = row['transliteration'] or ''
        strongs = f"G{row['strongs_number']}" if row['strongs_number'] else "N/A"
        gloss = row['english_gloss'] or ''
        definition = row['definition'] or ''
        text = row['bsb_text']
        
        print(f"{verse_ref} - {strongs}")
        print(f"  Greek: {greek} ({trans})")
        print(f"  Gloss: {gloss}")
        if definition:
            print(f"  Definition: {definition}")
        print(f"  Text: {text}")
        print()


def search_by_transliteration(conn: sqlite3.Connection, trans_word: str, limit: Optional[int] = None) -> None:
    """Search for transliterated Greek words (case-insensitive partial match)."""
    cursor = conn.cursor()
    
    sql = """
        SELECT DISTINCT w.verse_ref, w.greek_word, w.transliteration, w.strongs_number,
               w.english_gloss, s.definition, v.bsb_text
        FROM berean_words w
        LEFT JOIN berean_strongs s ON w.strongs_number = s.strongs_number
        JOIN berean_verses v ON w.verse_ref = v.verse_ref
        WHERE w.transliteration LIKE ?
        ORDER BY v.book, v.chapter, v.verse
    """
    
    if limit:
        sql += f" LIMIT {limit}"
    
    cursor.execute(sql, (f"%{trans_word}%",))
    rows = cursor.fetchall()
    
    if not rows:
        print(f"[warn] No matches for transliteration '{trans_word}'")
        return
    
    print(f"\n[ok] Found {len(rows)} matches for transliteration '{trans_word}':\n")
    
    for row in rows:
        verse_ref = row['verse_ref'].replace('|', ' ')
        greek = row['greek_word']
        trans = row['transliteration'] or ''
        strongs = f"G{row['strongs_number']}" if row['strongs_number'] else "N/A"
        gloss = row['english_gloss'] or ''
        definition = row['definition'] or ''
        text = row['bsb_text']
        
        print(f"{verse_ref} - {strongs}")
        print(f"  Greek: {greek} ({trans})")
        print(f"  Gloss: {gloss}")
        if definition:
            print(f"  Definition: {definition}")
        print(f"  Text: {text}")
        print()


def list_strongs_in_verse(conn: sqlite3.Connection, verse_ref: str) -> None:
    """List all Strong's numbers and words in a specific verse."""
    cursor = conn.cursor()
    
    # Get verse text
    cursor.execute("""
        SELECT book, chapter, verse, bsb_text, bgb_text
        FROM berean_verses
        WHERE verse_ref = ?
    """, (verse_ref,))
    
    verse_row = cursor.fetchone()
    if not verse_row:
        print(f"[warn] Verse not found: {verse_ref}")
        return
    
    print(f"\n{verse_ref}")
    print(f"Greek: {verse_row['bgb_text']}")
    print(f"English: {verse_row['bsb_text']}\n")
    
    # Get all words in verse
    cursor.execute("""
        SELECT w.word_order, w.greek_word, w.transliteration, w.strongs_number,
               w.parsing, w.english_gloss, s.definition
        FROM berean_words w
        LEFT JOIN berean_strongs s ON w.strongs_number = s.strongs_number
        WHERE w.verse_ref = ?
        ORDER BY w.word_order
    """, (verse_ref.replace(' ', '|'),))  # Convert "Matthew 1:1" to "Matthew|1:1"
    
    words = cursor.fetchall()
    
    if not words:
        print("[warn] No word data found for this verse")
        return
    
    print("Word-by-word breakdown:\n")
    
    for word in words:
        strongs = f"G{word['strongs_number']}" if word['strongs_number'] else "N/A"
        parsing = word['parsing'] or ''
        
        print(f"{word['word_order']}. {word['greek_word']} ({word['transliteration']}) - {strongs} {parsing}")
        print(f"   Gloss: {word['english_gloss']}")
        if word['definition']:
            print(f"   Definition: {word['definition']}")
        print()


def main(argv: list[str]) -> None:
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Query Berean Bible by Strong's numbers or Greek words",
        epilog="""Examples:
  python query_berean.py --strongs 2424  # Search for Strong's G2424 (Jesus)
  python query_berean.py --greek Ἰησοῦ   # Search for Greek word
  python query_berean.py --trans Iesou   # Search by transliteration
  python query_berean.py --verse "Matthew 1:1"  # Show all words in verse
        """
    )
    
    parser.add_argument("--db", default="compendium.sqlite", help="Path to database")
    parser.add_argument("--strongs", type=int, help="Search by Strong's number (e.g., 2424)")
    parser.add_argument("--greek", help="Search by Greek word (exact match)")
    parser.add_argument("--greek-partial", help="Search by Greek word (partial match)")
    parser.add_argument("--trans", help="Search by transliteration (partial match)")
    parser.add_argument("--verse", help="List all words in a verse (e.g., 'Matthew 1:1')")
    parser.add_argument("--limit", type=int, help="Limit number of results")
    
    args = parser.parse_args(argv)
    
    # Require at least one search parameter
    if not any([args.strongs, args.greek, args.greek_partial, args.trans, args.verse]):
        parser.print_help()
        sys.exit(1)
    
    db_path = Path(args.db)
    conn = connect_db(db_path)
    
    try:
        if args.strongs:
            search_by_strongs(conn, args.strongs, args.limit)
        
        if args.greek:
            search_by_greek(conn, args.greek, exact=True, limit=args.limit)
        
        if args.greek_partial:
            search_by_greek(conn, args.greek_partial, exact=False, limit=args.limit)
        
        if args.trans:
            search_by_transliteration(conn, args.trans, args.limit)
        
        if args.verse:
            list_strongs_in_verse(conn, args.verse)
    
    finally:
        conn.close()


if __name__ == "__main__":
    main(sys.argv[1:])
