"""
Parallel translation engine for the Study Bible Compendium.

Given a reference like "John 3:16" (or "John 3:16-18"), this module can
return the same verse(s) across multiple translations in one structure.

Public API:

- get_parallel_verses(ref, translation_codes) -> List[ParallelRow]
- print_parallel(ref, translation_codes, rows)

ParallelRow shape:
    (book_code, chapter, verse, { "KJV": text, "BSB": text, ... })
"""

from __future__ import annotations

from typing import List, Dict, Tuple, Optional, Any
import sqlite3

from .db import get_conn
from .util import info, warn
from .loader import load_canon


ParallelRow = Tuple[str, int, int, Dict[str, str]]  # book_code, chapter, verse, texts_by_translation


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


def _parse_reference_range(ref: str) -> Optional[Tuple[str, int, int, int]]:
    """
    Parse a reference like 'John 3:16-18' or 'Gen 1:1' into:

        (book_str, chapter, verse_start, verse_end)
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
        chapter = int(chap_str.strip())
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


def get_parallel_verses(ref: str, translation_codes: List[str]) -> List[ParallelRow]:
    """
    Fetch verses for a reference across multiple translations.

    Parameters
    ----------
    ref:
        Reference string like 'John 3:16' or 'John 3:16-18'.
    translation_codes:
        List of translation codes, e.g. ['KJV', 'BSB', 'ASV'].

    Returns
    -------
    List[ParallelRow]:
        (book_code, chapter, verse, { code: text, ... })
    """
    translation_codes = [c.upper() for c in translation_codes]
    info(f"=== PARALLEL === ref={ref!r}, codes={translation_codes!r}")

    if not translation_codes:
        warn("No translation codes provided; nothing to do.")
        return []

    parsed = _parse_reference_range(ref)
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

    # Prepare query
    placeholders = ", ".join("?" for _ in translation_codes)
    sql = f"""
        SELECT translation_code,
               book_code,
               chapter,
               verse,
               text
        FROM verses_normalized
        WHERE translation_code IN ({placeholders})
          AND book_num = ?
          AND chapter = ?
          AND verse BETWEEN ? AND ?
        ORDER BY verse, translation_code;
    """

    try:
        with get_conn(readonly=True) as conn:
            cur = conn.execute(
                sql,
                (*translation_codes, num, chapter, v_start, v_end),
            )
            rows = cur.fetchall()
    except sqlite3.Error as e:
        warn(f"Database error during parallel retrieval: {e}")
        return []

    if not rows:
        warn("No verses found for the requested reference in the given translations.")
        return []

    # Build map: verse -> { code: text }
    verse_map = {}
    for t_code, b_code, chap, verse, text in rows:
        if chap != chapter:
            continue
        mapping = verse_map.setdefault(verse, {})
        mapping[t_code] = text

    # Convert to ordered list of ParallelRow
    parallel_rows: List[ParallelRow] = []
    for verse in range(v_start, v_end + 1):
        texts = verse_map.get(verse, {})
        parallel_rows.append((book_code, chapter, verse, texts))

    return parallel_rows


def print_parallel(ref: str, translation_codes: List[str], rows: List[ParallelRow]) -> None:
    """
    Pretty-print parallel rows to the console.

    Output format:

        John 3:16
          [KJV] For God so loved...
          [BSB] For God so loved...
          ...

    One block per verse.
    """
    if not rows:
        warn("No parallel rows to display.")
        return

    translation_codes = [c.upper() for c in translation_codes]

    # Try to get a nice book name for the header line
    canon = load_canon()
    book_code = rows[0][0]
    book_name = book_code
    if canon:
        for meta in canon.values():
            if meta.get("code") == book_code:
                book_name = meta.get("name", book_code)
                break

    for book_code, chapter, verse, texts in rows:
        print(f"{book_name} {chapter}:{verse}")
        for code in translation_codes:
            text = texts.get(code, "(missing in this translation)")
            print(f"  [{code}] {text}")
        print()
