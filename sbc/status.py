"""
Status and health-report helpers for the Study Bible Compendium.
"""

from __future__ import annotations

from typing import List, Tuple, Optional

import sqlite3

from .db import get_conn
from .paths import DB_PATH
from .util import info, warn


def get_policy_status() -> Optional[Tuple[str, str]]:
    """
    Return (version, checksum) for the hermeneutical policy, or None if missing.
    """
    try:
        with get_conn(readonly=True) as conn:
            cur = conn.execute(
                """
                SELECT version, checksum
                FROM hermeneutical_policy
                WHERE id = 1;
                """
            )
            row = cur.fetchone()
    except sqlite3.Error:
        return None

    if not row:
        return None
    return row[0], row[1]


def get_translation_stats() -> List[Tuple[str, int]]:
    """
    Return a list of (translation_code, verse_count) from the verses_normalized table.
    """
    try:
        with get_conn(readonly=True) as conn:
            cur = conn.execute(
                """
                SELECT translation_code, COUNT(*)
                FROM verses_normalized
                GROUP BY translation_code
                ORDER BY translation_code;
                """
            )
            rows = cur.fetchall()
    except sqlite3.Error:
        return []
    return [(r[0], int(r[1])) for r in rows]


def get_translations() -> List[Tuple[str, str, str]]:
    """
    Return a list of (code, name, language) from translations table.

    If the table does not exist, returns [].
    """
    try:
        with get_conn(readonly=True) as conn:
            cur = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                  AND name='translations';
                """
            )
            if not cur.fetchone():
                return []

            cur = conn.execute(
                """
                SELECT code, name, language
                FROM translations
                ORDER BY code;
                """
            )
            rows = cur.fetchall()
    except sqlite3.Error:
        return []

    return [(r[0], r[1], r[2]) for r in rows]


def print_status() -> None:
    """
    Print a human-readable status report:

    - DB path
    - Policy version/checksum (if present)
    - Translations loaded + verse counts
    """
    info(f"Database: {DB_PATH}")

    # Policy
    policy = get_policy_status()
    if policy is None:
        warn("Policy: hermeneutical_policy table or row not found.")
    else:
        version, checksum = policy
        info(f"Policy: version={version}, checksum={checksum[:12]}...")

    # Translation stats from verses_normalized
    stats = get_translation_stats()
    if not stats:
        warn("No verse data found in `verses_normalized` table (or table missing).")
    else:
        info("Verse counts per translation (from verses_normalized table):")
        for code, count in stats:
            print(f"  - {code}: {count} verse(s)")

    # Translations registry
    registry = get_translations()
    if not registry:
        warn("No translations recorded in `translations` table (or table missing).")
    else:
        info("Translations registry:")
        for code, name, lang in registry:
            print(f"  - {code} [{lang}]: {name}")
