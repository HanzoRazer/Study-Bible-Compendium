#!/usr/bin/env python3
"""
Generate cross-references between verses using Strong's numbers.

Creates cross-reference reports showing:
- Verses that share specific Strong's numbers
- Thematic connections via common Greek words
- Parallel passages using key theological terms
"""

import sys
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Set
from collections import defaultdict


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


def find_xrefs_for_verse(conn: sqlite3.Connection, verse_ref: str, min_shared: int = 2, limit: Optional[int] = None) -> None:
    """
    Find cross-references for a specific verse based on shared Strong's numbers.
    
    Args:
        verse_ref: Verse to find cross-references for (e.g., "Matthew 1:1")
        min_shared: Minimum number of shared Strong's numbers to report
        limit: Maximum number of cross-references to return
    """
    cursor = conn.cursor()
    
    # Get the verse text
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
    
    # Get Strong's numbers in this verse (verse_ref is already in space format)
    cursor.execute("""
        SELECT DISTINCT strongs_number, greek_word
        FROM berean_words
        WHERE verse_ref = ? AND strongs_number IS NOT NULL
    """, (verse_ref,))
    
    strongs_in_verse = cursor.fetchall()
    if not strongs_in_verse:
        print("[warn] No Strong's numbers found in this verse")
        return
    
    strongs_numbers = [row['strongs_number'] for row in strongs_in_verse]
    strongs_map = {row['strongs_number']: row['greek_word'] for row in strongs_in_verse}
    
    print(f"Key Greek words (Strong's numbers): {', '.join([f'{strongs_map[s]} (G{s})' for s in strongs_numbers[:5]])}")
    if len(strongs_numbers) > 5:
        print(f"  ... and {len(strongs_numbers) - 5} more\n")
    else:
        print()
    
    # Find other verses with shared Strong's numbers
    placeholders = ','.join('?' * len(strongs_numbers))
    sql = f"""
        SELECT 
            w.verse_ref,
            v.bsb_text,
            COUNT(DISTINCT w.strongs_number) as shared_count,
            GROUP_CONCAT(DISTINCT w.strongs_number) as shared_strongs
        FROM berean_words w
        JOIN berean_verses v ON w.verse_ref = v.verse_ref
        WHERE w.strongs_number IN ({placeholders})
          AND w.verse_ref != ?
        GROUP BY w.verse_ref
        HAVING shared_count >= ?
        ORDER BY shared_count DESC, v.book, v.chapter, v.verse
    """
    
    if limit:
        sql += f" LIMIT {limit}"
    
    cursor.execute(sql, strongs_numbers + [verse_ref, min_shared])
    xrefs = cursor.fetchall()
    
    if not xrefs:
        print(f"[info] No cross-references found with at least {min_shared} shared Strong's numbers")
        return
    
    print(f"Found {len(xrefs)} cross-references (minimum {min_shared} shared Strong's numbers):\n")
    
    for xref in xrefs:
        xref_verse = xref['verse_ref'].replace('|', ' ')
        shared_count = xref['shared_count']
        shared_strongs = [int(s) for s in xref['shared_strongs'].split(',')]
        shared_words = [f"G{s}" for s in shared_strongs]
        
        print(f"{xref_verse} ({shared_count} shared)")
        print(f"  Shared: {', '.join(shared_words)}")
        print(f"  Text: {xref['bsb_text']}")
        print()


def find_xrefs_by_strongs(conn: sqlite3.Connection, strongs_nums: List[int], limit: Optional[int] = None) -> None:
    """
    Find verses that contain ALL specified Strong's numbers.
    
    Args:
        strongs_nums: List of Strong's numbers to search for
        limit: Maximum number of results
    """
    if not strongs_nums:
        print("[warn] No Strong's numbers provided")
        return
    
    cursor = conn.cursor()
    
    # Get definitions
    print("\nSearching for verses containing ALL of these Strong's numbers:\n")
    for strongs_num in strongs_nums:
        cursor.execute("SELECT definition FROM berean_strongs WHERE strongs_number = ?", (strongs_num,))
        row = cursor.fetchone()
        definition = row['definition'] if row else "Definition not found"
        print(f"  G{strongs_num}: {definition}")
    print()
    
    # Find verses containing ALL specified Strong's numbers
    placeholders = ','.join('?' * len(strongs_nums))
    sql = f"""
        SELECT 
            w.verse_ref,
            v.bsb_text,
            COUNT(DISTINCT w.strongs_number) as match_count
        FROM berean_words w
        JOIN berean_verses v ON w.verse_ref = v.verse_ref
        WHERE w.strongs_number IN ({placeholders})
        GROUP BY w.verse_ref
        HAVING match_count = ?
        ORDER BY v.book, v.chapter, v.verse
    """
    
    if limit:
        sql += f" LIMIT {limit}"
    
    cursor.execute(sql, strongs_nums + [len(strongs_nums)])
    verses = cursor.fetchall()
    
    if not verses:
        print(f"[info] No verses found containing all {len(strongs_nums)} Strong's numbers")
        return
    
    print(f"Found {len(verses)} verses containing all specified Strong's numbers:\n")
    
    for verse in verses:
        verse_ref = verse['verse_ref'].replace('|', ' ')
        print(f"{verse_ref}")
        print(f"  Text: {verse['bsb_text']}")
        print()


def generate_xref_network(conn: sqlite3.Connection, strongs_num: int, max_verses: int = 10) -> None:
    """
    Generate a cross-reference network showing how verses connect via a Strong's number.
    
    Args:
        strongs_num: Strong's number to build network around
        max_verses: Maximum verses to include in network
    """
    cursor = conn.cursor()
    
    # Get Strong's definition
    cursor.execute("SELECT definition FROM berean_strongs WHERE strongs_number = ?", (strongs_num,))
    row = cursor.fetchone()
    
    if not row:
        print(f"[warn] Strong's number G{strongs_num} not found")
        return
    
    definition = row['definition']
    print(f"\n[ok] Cross-reference network for G{strongs_num}: {definition}\n")
    
    # Get verses containing this Strong's number
    cursor.execute("""
        SELECT DISTINCT w.verse_ref, v.book, v.chapter, v.verse, v.bsb_text
        FROM berean_words w
        JOIN berean_verses v ON w.verse_ref = v.verse_ref
        WHERE w.strongs_number = ?
        ORDER BY v.book, v.chapter, v.verse
        LIMIT ?
    """, (strongs_num, max_verses))
    
    verses = cursor.fetchall()
    
    if not verses:
        print(f"[warn] No verses found with Strong's G{strongs_num}")
        return
    
    print(f"Key verses using this word (showing {len(verses)} of all occurrences):\n")
    
    # Build network
    verse_refs = []
    for verse in verses:
        verse_ref = verse['verse_ref'].replace('|', ' ')
        verse_refs.append(verse['verse_ref'])
        print(f"{verse_ref}")
        print(f"  {verse['bsb_text']}")
        print()
    
    # Find common co-occurring Strong's numbers
    if len(verse_refs) > 1:
        placeholders = ','.join('?' * len(verse_refs))
        cursor.execute(f"""
            SELECT w.strongs_number, s.definition, COUNT(*) as occurrence_count
            FROM berean_words w
            LEFT JOIN berean_strongs s ON w.strongs_number = s.strongs_number
            WHERE w.verse_ref IN ({placeholders})
              AND w.strongs_number != ?
              AND w.strongs_number IS NOT NULL
            GROUP BY w.strongs_number
            HAVING occurrence_count >= 2
            ORDER BY occurrence_count DESC
            LIMIT 10
        """, verse_refs + [strongs_num])
        
        co_occurring = cursor.fetchall()
        
        if co_occurring:
            print(f"Strong's numbers frequently appearing with G{strongs_num}:\n")
            for co in co_occurring:
                print(f"  G{co['strongs_number']} ({co['occurrence_count']} times): {co['definition']}")


def main(argv: list[str]) -> None:
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate cross-references using Strong's numbers",
        epilog="""Examples:
  python xref_berean.py --verse "John 3:16"  # Find cross-refs for a verse
  python xref_berean.py --strongs 2424 5547  # Find verses with both G2424 and G5547
  python xref_berean.py --network 26         # Show cross-ref network for G26 (love)
        """
    )
    
    parser.add_argument("--db", default="compendium.sqlite", help="Path to database")
    parser.add_argument("--verse", help="Find cross-references for a verse (e.g., 'John 3:16')")
    parser.add_argument("--strongs", type=int, nargs='+', help="Find verses containing ALL these Strong's numbers")
    parser.add_argument("--network", type=int, help="Generate cross-reference network for a Strong's number")
    parser.add_argument("--min-shared", type=int, default=2, help="Minimum shared Strong's for verse xrefs (default: 2)")
    parser.add_argument("--limit", type=int, default=20, help="Limit number of results (default: 20)")
    
    args = parser.parse_args(argv)
    
    # Require at least one search parameter
    if not any([args.verse, args.strongs, args.network]):
        parser.print_help()
        sys.exit(1)
    
    db_path = Path(args.db)
    conn = connect_db(db_path)
    
    try:
        if args.verse:
            find_xrefs_for_verse(conn, args.verse, args.min_shared, args.limit)
        
        if args.strongs:
            find_xrefs_by_strongs(conn, args.strongs, args.limit)
        
        if args.network:
            generate_xref_network(conn, args.network, args.limit)
    
    finally:
        conn.close()


if __name__ == "__main__":
    main(sys.argv[1:])
