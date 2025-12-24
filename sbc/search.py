"""
Search and passage extraction for the Study Bible Compendium.

This module now provides:

- search_verses(query, limit, translation_code=None)
    Real SQL search against verses_normalized.text

- get_passage(ref, translation_code)
    Extracts a passage like "John 3:16-18" or "Gen 1:1"

- print_search_results(rows)
    Pretty-print results to the console
"""

from __future__ import annotations

from typing import List, Tuple, Optional, Dict, Any
import sqlite3

from .db import get_conn
from .util import info, warn
from .loader import load_canon


# (translation_code, book_num, book_code, chapter, verse, text)
VerseRow = Tuple[str, int, str, int, int, str]


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


def search_verses(
    query: str,
    limit: int = 20,
    translation_code: Optional[str] = None,
) -> List[VerseRow]:
    """
    Perform a basic text search across verses.

    Parameters
    ----------
    query:
        Text to search for (simple LIKE '%query%').
    limit:
        Max number of verses to return.
    translation_code:
        Optional translation filter (e.g., 'KJV'). If None, searches all.

    Returns
    -------
    List of VerseRow tuples:
        (translation_code, book_num, book_code, chapter, verse, text)
    """
    query = query.strip()
    if not query:
        warn("Empty search query; returning no results.")
        return []

    info(f"=== SEARCH === query={query!r}, limit={limit}, translation={translation_code!r}")

    try:
        with get_conn(readonly=True) as conn:
            if translation_code:
                translation_code = translation_code.upper()
                cur = conn.execute(
                    """
                    SELECT translation_code,
                           book_num,
                           book_code,
                           chapter,
                           verse,
                           text
                    FROM verses_normalized
                    WHERE translation_code = ?
                      AND text LIKE ?
                    ORDER BY translation_code, book_num, chapter, verse
                    LIMIT ?;
                    """,
                    (translation_code, f"%{query}%", limit),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT translation_code,
                           book_num,
                           book_code,
                           chapter,
                           verse,
                           text
                    FROM verses_normalized
                    WHERE text LIKE ?
                    ORDER BY translation_code, book_num, chapter, verse
                    LIMIT ?;
                    """,
                    (f"%{query}%", limit),
                )
            rows = cur.fetchall()
    except sqlite3.Error as e:
        warn(f"Database error during search: {e}")
        return []

    info(f"Search returned {len(rows)} row(s).")
    return [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]


def _parse_reference(ref: str) -> Optional[tuple[str, int, int, int]]:
    """
    Parse a reference string like 'John 3:16-18' or 'Gen 1:1'.

    Returns
    -------
    (book_str, chapter, verse_start, verse_end) or None on failure.
    """
    s = ref.strip()
    if not s:
        warn("Empty reference string.")
        return None

    try:
        space_idx = s.rindex(" ")
    except ValueError:
        warn(f"Could not split book and chapter/verse from reference: {ref!r}")
        return None

    book_str = s[:space_idx].strip()
    cv_str = s[space_idx + 1 :].strip()

    if ":" not in cv_str:
        warn(f"Reference missing ':' in chapter:verse part: {ref!r}")
        return None

    chap_str, verse_part = cv_str.split(":", 1)
    try:
        chapter = int(chap_str)
    except ValueError:
        warn(f"Non-integer chapter in reference: {ref!r}")
        return None

    verse_part = verse_part.strip()
    if "-" in verse_part:
        start_str, end_str = verse_part.split("-", 1)
        try:
            v_start = int(start_str.strip())
            v_end = int(end_str.strip())
        except ValueError:
            warn(f"Invalid verse range in reference: {ref!r}")
            return None
    else:
        try:
            v_start = v_end = int(verse_part)
        except ValueError:
            warn(f"Invalid verse number in reference: {ref!r}")
            return None

    return book_str, chapter, v_start, v_end


def get_passage(ref: str, translation_code: str) -> List[VerseRow]:
    """
    Fetch a passage like 'John 3:16-18' or 'Gen 1:1' from the `verses_normalized` table.

    Parameters
    ----------
    ref:
        Reference string, e.g. 'John 3:16-18', 'Gen 1:1'.
    translation_code:
        Translation code (e.g., 'KJV').

    Returns
    -------
    List[VerseRow]:
        (translation_code, book_num, book_code, chapter, verse, text)
    """
    translation_code = translation_code.upper()
    info(f"=== PASSAGE === ref={ref!r}, translation={translation_code!r}")

    parsed = _parse_reference(ref)
    if parsed is None:
        return []

    book_str, chapter, v_start, v_end = parsed

    canon = load_canon()
    if not canon:
        warn("Canon mapping is empty; cannot resolve book in reference.")
        return []

    book_lookup = _build_book_lookup(canon)

    num = None
    for key in (book_str, book_str.lower()):
        if key in book_lookup:
            num = book_lookup[key]
            break

    if num is None:
        warn(f"Could not resolve book name {book_str!r} using canon.json.")
        return []

    book_meta = canon[num]
    book_code = book_meta["code"]

    try:
        with get_conn(readonly=True) as conn:
            cur = conn.execute(
                """
                SELECT translation_code,
                       book_num,
                       book_code,
                       chapter,
                       verse,
                       text
                FROM verses_normalized
                WHERE translation_code = ?
                  AND book_num = ?
                  AND chapter = ?
                  AND verse BETWEEN ? AND ?
                ORDER BY verse;
                """,
                (translation_code, num, chapter, v_start, v_end),
            )
            rows = cur.fetchall()
    except sqlite3.Error as e:
        warn(f"Database error during passage retrieval: {e}")
        return []

    info(f"Passage query returned {len(rows)} row(s).")
    return [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]


def print_search_results(rows: List[VerseRow]) -> None:
    """
    Pretty-print search or passage results to the console.
    """
    if not rows:
        info("No results.")
        return

    canon = load_canon()
    if not canon:
        warn("Canon mapping missing; printing without book names.")
        for code, book_num, book_code, chapter, verse, text in rows:
            print(f"[{code}] {book_code} {chapter}:{verse}")
            print(f"    {text}")
            print()
        return

    for code, book_num, book_code, chapter, verse, text in rows:
        meta = canon.get(book_num, {})
        book_name = meta.get("name", book_code)
        print(f"[{code}] {book_name} {chapter}:{verse}")
        print(f"    {text}")
        print()
