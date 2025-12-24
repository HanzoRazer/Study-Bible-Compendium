"""
Spine builder for the Study Bible Compendium.

This module:

- Ensures the canonical_verses and notes schemas exist.
- Ensures the verses table has a verse_id column.
- Builds a canonical verse spine by deduplicating verses.normalized_ref.
- Attaches verse_id to verses by matching normalized_ref.

Design:
- We *derive* the spine from whatever verses are currently imported.
- One canonical row per normalized_ref, regardless of translation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Tuple

import sqlite3
from datetime import datetime, timezone

from .paths import SCHEMA_DIR
from .db import get_conn
from .util import info, warn


def _apply_schema(path: Path) -> None:
    if not path.exists():
        warn(f"Schema file not found: {path}")
        return
    sql = path.read_text(encoding="utf-8")
    info(f"Applying schema from: {path}")
    with get_conn() as conn:
        conn.executescript(sql)
        conn.commit()


def ensure_canonical_schema() -> None:
    """
    Ensure canonical_verses table exists.
    """
    _apply_schema(SCHEMA_DIR / "canonical_verses.sql")


def ensure_notes_schema() -> None:
    """
    Ensure notes table exists.
    """
    _apply_schema(SCHEMA_DIR / "notes.sql")


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (name,),
    )
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table});")
    for row in cur.fetchall():
        # row = cid, name, type, notnull, dflt_value, pk
        if row[1] == column:
            return True
    return False


def ensure_verses_has_verse_id() -> None:
    """
    Ensure the verses table has a verse_id column.

    This is safe to run repeatedly. If the column already exists,
    nothing happens.
    """
    with get_conn() as conn:
        if not _table_exists(conn, "verses_normalized"):
            warn("verses_normalized table does not exist yet; run init-schema and import-bible first.")
            return

        if _column_exists(conn, "verses_normalized", "verse_id"):
            info("verses_normalized.verse_id column already present.")
            return

        info("Adding verse_id column to verses_normalized table...")
        conn.execute("ALTER TABLE verses_normalized ADD COLUMN verse_id INTEGER;")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verses_normalized_verse_id ON verses_normalized (verse_id);"
        )
        conn.commit()
        info("verse_id column added to verses_normalized.")


def _build_canonical_from_verses() -> None:
    """
    Populate canonical_verses from distinct normalized_ref values in verses.

    One canonical row per normalized_ref, using MIN(book_num) and a representative
    book_code/chapter/verse.
    """
    ensure_canonical_schema()
    ensure_verses_has_verse_id()

    with get_conn() as conn:
        if not _table_exists(conn, "verses_normalized"):
            warn("verses_normalized table does not exist; cannot build canonical spine.")
            return

        info("Populating canonical_verses from verses_normalized.normalized_ref...")

        # This INSERT is idempotent due to UNIQUE on normalized_ref.
        conn.execute(
            """
            INSERT OR IGNORE INTO canonical_verses (
                book_num,
                book_code,
                chapter,
                verse,
                normalized_ref
            )
            SELECT
                MIN(book_num)      AS book_num,
                book_code          AS book_code,
                chapter            AS chapter,
                verse              AS verse,
                normalized_ref     AS normalized_ref
            FROM verses_normalized
            GROUP BY book_code, chapter, verse, normalized_ref;
            """
        )
        conn.commit()

        cur = conn.execute("SELECT COUNT(*) FROM canonical_verses;")
        (count,) = cur.fetchone()
        info(f"canonical_verses now has {count} row(s).")


def _attach_verse_ids_to_verses() -> None:
    """
    Fill verses.verse_id by joining on canonical_verses.normalized_ref.

    Only updates rows where verse_id IS NULL, so it's safe to run repeatedly.
    """
    with get_conn() as conn:
        if not _table_exists(conn, "verses_normalized"):
            warn("verses_normalized table does not exist; cannot attach verse_id.")
            return
        if not _table_exists(conn, "canonical_verses"):
            warn("canonical_verses table does not exist; cannot attach verse_id.")
            return

        info("Attaching verse_id to verses_normalized (joining on normalized_ref)...")
        conn.execute(
            """
            UPDATE verses_normalized
            SET verse_id = (
                SELECT id
                FROM canonical_verses cv
                WHERE cv.normalized_ref = verses_normalized.normalized_ref
            )
            WHERE verse_id IS NULL;
            """
        )
        conn.commit()

        cur = conn.execute("SELECT COUNT(*) FROM verses_normalized WHERE verse_id IS NOT NULL;")
        (attached,) = cur.fetchone()
        cur = conn.execute("SELECT COUNT(*) FROM verses_normalized;")
        (total,) = cur.fetchone()
        info(f"verses_normalized with verse_id: {attached}/{total}")

        cur = conn.execute("SELECT COUNT(*) FROM verses_normalized WHERE verse_id IS NULL;")
        (missing,) = cur.fetchone()
        if missing > 0:
            warn(f"{missing} verse row(s) still missing verse_id (no matching spine row).")


def build_spine() -> None:
    """
    Public entry point: build the canonical verse spine and attach verse_ids.

    Steps:
    - Ensure canonical_verses + notes schemas exist.
    - Ensure verses has verse_id column.
    - Populate canonical_verses from verses.
    - Attach verse_id to verses.
    """
    info("=== BUILD SPINE ===")
    ensure_canonical_schema()
    ensure_notes_schema()
    ensure_verses_has_verse_id()
    _build_canonical_from_verses()
    _attach_verse_ids_to_verses()
    info("Spine build complete.")
