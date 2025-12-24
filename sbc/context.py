"""
Context engine for the Study Bible Compendium.

Provides 4-verse (or configurable) windows around a reference like "John 3:16",
so you can see verses before and after a given location.

Public API:

- get_verse_window(ref, translation_code, before=2, after=2) -> List[VerseRow]

Where VerseRow is:
    (translation_code, book_num, book_code, chapter, verse, text)
"""

from __future__ import annotations

from typing import List, Tuple, Optional, Dict, Any
import sqlite3

from .db import get_conn
from .util import info, warn
from .loader import load_canon


# Same row shape as sbc.search.VerseRow
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


def _parse_reference(ref: str) -> Optional[tuple[str, int, int]]:
    """
    Parse a reference string like 'John 3:16' into:

        (book_str, chapter, verse)

    This is intentionally simpler than the passage parser: we only
    need a single verse as the center-point of the context window.
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

    chap_str, verse_str = cv_str.split(":", 1)

    try:
        chapter = int(chap_str.strip())
        verse = int(verse_str.strip())
    except ValueError:
        warn(f"Invalid chapter/verse in reference: {ref!r}")
        return None

    return book_str, chapter, verse


def get_verse_window(
    ref: str,
    translation_code: str,
    before: int = 2,
    after: int = 2,
) -> List[VerseRow]:
    """
    Fetch a window of verses around a reference.

    Example:
        get_verse_window("John 3:16", "KJV", before=2, after=2)

    Returns
    -------
    List[VerseRow]:
        (translation_code, book_num, book_code, chapter, verse, text)
    """
    translation_code = translation_code.upper()
    info(
        f"=== CONTEXT WINDOW === ref={ref!r}, translation={translation_code!r}, "
        f"before={before}, after={after}"
    )

    parsed = _parse_reference(ref)
    if parsed is None:
        return []

    book_str, chapter, center_verse = parsed

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

    v_start = max(1, center_verse - before)
    v_end = center_verse + after

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
        warn(f"Database error during context retrieval: {e}")
        return []

    info(f"Context query returned {len(rows)} row(s).")
    return [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]
