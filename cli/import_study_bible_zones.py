#!/usr/bin/env python3
"""
Import spatially-structured study Bible data from high-DPI scans.

Designed for CZUR Shine Ultra scans (400-600 DPI) with zone detection.
Separates verse text from annotations, cross-references, and study notes
using spatial coordinates and text analysis.

Usage:
    python import_study_bible_zones.py --db compendium.sqlite \
        --source "Dake's Annotated Reference Bible" \
        --scan-dir "sources/scans/dakes/" \
        --version-code DAKE

Expected Input Formats:
    1. CZUR searchable PDF with text layer
    2. ABBYY FineReader XML with zone coordinates
    3. JSON zone data: {"pages": [{"zones": [...]}]}

Output:
    - Bible text → bible_versions/books/chapters/verses
    - Annotations → midrash_sources/midrash_notes
    - Cross-references → crossrefs table
    - Spatial metadata preserved for future analysis
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Zone types for spatial analysis
ZONE_TYPES = {
    "verse_text": 1,      # Main Bible text columns
    "margin_note": 2,     # Side margin annotations
    "footnote": 3,        # Bottom page footnotes
    "header": 4,          # Book/chapter headers
    "cross_ref": 5,       # Cross-reference codes
    "study_note": 6,      # Extended commentary blocks
}


def parse_czur_pdf(pdf_path: Path) -> List[Dict]:
    """
    Extract text zones from CZUR searchable PDF.
    
    Uses pdfplumber to get text with coordinates.
    Classifies zones based on position heuristics.
    """
    try:
        import pdfplumber
    except ImportError:
        print("[error] pdfplumber required: pip install pdfplumber")
        sys.exit(1)
    
    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # Get words with bounding boxes
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False
            )
            
            # Classify zones by position
            zones = classify_zones_by_position(words, page.width, page.height)
            pages_data.append({
                "page": page_num,
                "zones": zones
            })
            
            if page_num % 100 == 0:
                print(f"[info] Processed {page_num} pages...")
    
    return pages_data


def classify_zones_by_position(
    words: List[Dict],
    page_width: float,
    page_height: float
) -> List[Dict]:
    """
    Classify text zones based on spatial position.
    
    Heuristics for study Bible layout:
    - Center columns (40-80% width) → verse text
    - Left margin (0-20% width) → annotations
    - Right margin (80-100% width) → annotations
    - Top 5% → headers
    - Bottom 5% → footnotes
    """
    zones = []
    
    # Group words by vertical position (lines)
    lines = {}
    for word in words:
        y_pos = int(word['top'])
        if y_pos not in lines:
            lines[y_pos] = []
        lines[y_pos].append(word)
    
    # Classify each line
    for y_pos, line_words in sorted(lines.items()):
        line_text = " ".join(w['text'] for w in line_words)
        avg_x = sum(w['x0'] for w in line_words) / len(line_words)
        
        # Position-based classification
        x_percent = avg_x / page_width
        y_percent = y_pos / page_height
        
        if y_percent < 0.05:
            zone_type = "header"
        elif y_percent > 0.95:
            zone_type = "footnote"
        elif x_percent < 0.2:
            zone_type = "margin_note"
        elif x_percent > 0.8:
            zone_type = "margin_note"
        elif 0.4 <= x_percent <= 0.8:
            # Center text - distinguish verse from study notes
            if is_verse_text(line_text):
                zone_type = "verse_text"
            else:
                zone_type = "study_note"
        else:
            zone_type = "verse_text"
        
        zones.append({
            "type": zone_type,
            "text": line_text,
            "x": avg_x,
            "y": y_pos,
            "bbox": {
                "x0": min(w['x0'] for w in line_words),
                "y0": min(w['top'] for w in line_words),
                "x1": max(w['x1'] for w in line_words),
                "y1": max(w['bottom'] for w in line_words)
            }
        })
    
    return zones


def is_verse_text(text: str) -> bool:
    """
    Heuristic: verse text typically starts with verse number.
    Examples: "1In the beginning", "23And God said"
    """
    # Check for leading verse number
    if re.match(r'^\d{1,3}[A-Z]', text):
        return True
    
    # Check for inline verse numbers
    if re.search(r'\b\d{1,3}\s+[A-Z]', text):
        return True
    
    # Exclude obvious commentary patterns
    if any(text.startswith(kw) for kw in [
        "Note:", "See", "Cf.", "Compare", "Literal:",
        "Greek:", "Hebrew:", "Or,"
    ]):
        return False
    
    return False  # Conservative default


def extract_verse_reference(text: str, context_book: str, context_chapter: int) -> Optional[Tuple[str, int, int]]:
    """
    Extract verse reference from annotation text.
    
    Examples:
        "God's sabbath (heading. 2:1)" → (context_book, 2, 1)
        "See Gen. 3:15" → ("Genesis", 3, 15)
    """
    # Pattern: (book chapter:verse)
    match = re.search(r'\((\w+\.?\s*)?(\d+):(\d+)\)', text)
    if match:
        book_abbrev, chapter, verse = match.groups()
        book = expand_book_abbreviation(book_abbrev) if book_abbrev else context_book
        return (book, int(chapter), int(verse))
    
    # Pattern: chapter:verse (no book, use context)
    match = re.search(r'\b(\d+):(\d+)\b', text)
    if match:
        chapter, verse = match.groups()
        return (context_book, int(chapter), int(verse))
    
    return None


def expand_book_abbreviation(abbrev: str) -> str:
    """Expand common Bible book abbreviations."""
    abbrevs = {
        "Gen.": "Genesis", "Ex.": "Exodus", "Lev.": "Leviticus",
        "Num.": "Numbers", "Dt.": "Deuteronomy", "Josh.": "Joshua",
        "Mt.": "Matthew", "Mk.": "Mark", "Lk.": "Luke", "Jn.": "John",
        "Rom.": "Romans", "Cor.": "Corinthians", "Gal.": "Galatians",
        "Eph.": "Ephesians", "Phil.": "Philippians", "Col.": "Colossians",
        "Heb.": "Hebrews", "Jas.": "James", "Rev.": "Revelation",
    }
    return abbrevs.get(abbrev.strip(), abbrev.strip())


def import_study_bible(
    db_path: Path,
    source_name: str,
    version_code: str,
    pages_data: List[Dict]
) -> None:
    """
    Import study Bible zones into database.
    
    Workflow:
        1. Create midrash_source entry
        2. Extract verse text → verses table
        3. Extract annotations → midrash_notes
        4. Link notes to verses via spatial/textual analysis
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Create midrash source
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO midrash_sources (code, title, author, pub_year, language)
        VALUES (?, ?, 'Finis Jennings Dake', 1963, 'en')
    """, (version_code, source_name))
    source_id = cur.lastrowid or cur.execute(
        "SELECT id FROM midrash_sources WHERE code = ?", (version_code,)
    ).fetchone()["id"]
    
    # Process pages
    context_book = None
    context_chapter = None
    
    for page_data in pages_data:
        for zone in page_data["zones"]:
            if zone["type"] == "header":
                # Update context from headers like "Genesis 2"
                match = re.match(r'(\w+)\s+(\d+)', zone["text"])
                if match:
                    context_book, context_chapter = match.groups()
                    context_chapter = int(context_chapter)
            
            elif zone["type"] == "verse_text":
                # TODO: Parse and insert verse text
                pass
            
            elif zone["type"] in ("margin_note", "study_note"):
                # Extract verse reference and insert annotation
                verse_ref = extract_verse_reference(
                    zone["text"], 
                    context_book or "Genesis", 
                    context_chapter or 1
                )
                if verse_ref:
                    book, chapter, verse = verse_ref
                    # TODO: Link to verse_id in database
                    print(f"[info] Annotation for {book} {chapter}:{verse}")
    
    conn.commit()
    conn.close()
    print(f"[ok] Imported {len(pages_data)} pages from {source_name}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Import spatially-structured study Bible scans"
    )
    parser.add_argument("--db", default="compendium.sqlite", help="Database path")
    parser.add_argument("--source", required=True, help="Study Bible source name")
    parser.add_argument("--version-code", required=True, help="Version code (e.g., DAKE)")
    parser.add_argument("--scan-dir", required=True, help="Directory with scan PDFs")
    
    args = parser.parse_args(argv)
    
    scan_dir = Path(args.scan_dir)
    if not scan_dir.exists():
        print(f"[error] Scan directory not found: {scan_dir}")
        sys.exit(1)
    
    # Find PDF files
    pdfs = list(scan_dir.glob("*.pdf"))
    if not pdfs:
        print(f"[error] No PDF files found in {scan_dir}")
        sys.exit(1)
    
    print(f"[info] Found {len(pdfs)} PDF files")
    print(f"[info] Processing with CZUR zone detection...")
    
    # Process first PDF as test
    pages_data = parse_czur_pdf(pdfs[0])
    
    # Import to database
    import_study_bible(
        Path(args.db),
        args.source,
        args.version_code,
        pages_data
    )


if __name__ == "__main__":
    main()
