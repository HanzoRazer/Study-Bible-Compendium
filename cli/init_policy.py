#!/usr/bin/env python3
"""
init_policy.py

Initialize the Study Bible Compendium Hermeneutical Rule Policy
in a locked SQLite table so that it cannot be modified later.

This module reads policy content from external files and applies
the schema from an SQL file, making maintenance easier.

Usage:
    python cli/init_policy.py --db compendium.sqlite

Directory structure expected:
    schema/hermeneutical_policy.sql  (table + triggers)
    data/policy_preface.txt          (preface content)
    data/policy_body.txt             (policy body content)
"""

import argparse
import datetime as _dt
import hashlib
import sqlite3
import sys
from pathlib import Path


POLICY_TITLE = "Study Bible Compendium – Hermeneutical Rule Policy"
POLICY_VERSION = "1.0.0"

# Default file paths (relative to project root)
DEFAULT_SCHEMA_PATH = "schema/hermeneutical_policy.sql"
DEFAULT_PREFACE_PATH = "data/policy_preface.txt"
DEFAULT_BODY_PATH = "data/policy_body.txt"


# =========================
# HELPER FUNCTIONS
# =========================

def compute_checksum(preface: str, body: str) -> str:
    """
    Compute a SHA-256 checksum from the concatenation of preface + body.
    """
    combined = (preface + "\n\n" + body).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def read_text_file(file_path: Path) -> str:
    """
    Read a text file and return its contents.
    Handles common line ending variations.
    """
    if not file_path.exists():
        print(f"[error] File not found: {file_path}")
        sys.exit(1)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    return content.strip()


def apply_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    """
    Apply the SQL schema from file (creates table and triggers).
    """
    if not schema_path.exists():
        print(f"[error] Schema file not found: {schema_path}")
        sys.exit(1)
    
    print(f"[info] Applying schema from: {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print("[ok] Schema applied successfully")
    except sqlite3.Error as e:
        print(f"[error] Failed to apply schema: {e}")
        sys.exit(1)


def policy_exists(conn: sqlite3.Connection) -> bool:
    """
    Return True if a policy row already exists, False otherwise.
    """
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM hermeneutical_policy;")
    (count,) = cur.fetchone()
    return count >= 1


def insert_policy(
    conn: sqlite3.Connection,
    preface: str,
    body: str
) -> None:
    """
    Insert the hermeneutical policy if it does not already exist.
    Respects the locking triggers; will not modify an existing row.
    """
    if policy_exists(conn):
        print("[info] hermeneutical_policy row already present; no changes made (locked).")
        return

    checksum = compute_checksum(preface, body)
    effective_utc = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    print(f"[info] Computed checksum: {checksum}")
    print(f"[info] Effective UTC: {effective_utc}")

    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO hermeneutical_policy (
                id,
                title,
                preface,
                body,
                version,
                effective_utc,
                checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                1,
                POLICY_TITLE,
                preface,
                body,
                POLICY_VERSION,
                effective_utc,
                checksum,
            ),
        )
        conn.commit()
        print("[ok] hermeneutical_policy initialized and locked.")
        print(f"[ok] version: {POLICY_VERSION}")
        print(f"[ok] checksum: {checksum}")
    except sqlite3.IntegrityError as e:
        msg = str(e)
        print(f"[warn] IntegrityError while inserting policy: {msg}")
        print("[warn] Policy may already be locked or constrained. No changes were made.")
    except sqlite3.Error as e:
        print(f"[error] SQLite error while inserting policy: {e}")
        sys.exit(1)


# =========================
# PUBLIC API
# =========================

def run_init_policy(
    db_path: str,
    schema_path: str = DEFAULT_SCHEMA_PATH,
    preface_path: str = DEFAULT_PREFACE_PATH,
    body_path: str = DEFAULT_BODY_PATH,
    project_root: Path = None
) -> None:
    """
    Public entry point to be used by the Study Bible Compendium CLI.

    Opens the database, applies schema/triggers from SQL file,
    reads policy content from text files, and inserts if not already present.

    Args:
        db_path: Path to the SQLite database file
        schema_path: Path to SQL schema file (relative to project root)
        preface_path: Path to preface text file (relative to project root)
        body_path: Path to body text file (relative to project root)
        project_root: Project root directory (defaults to parent of cli/)
    """
    # Determine project root
    if project_root is None:
        # Assume this script is in cli/ and project root is parent
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
    
    # Convert all paths to absolute
    db_path = Path(db_path)
    schema_path = project_root / schema_path
    preface_path = project_root / preface_path
    body_path = project_root / body_path
    
    print(f"[info] Project root: {project_root}")
    print(f"[info] Database: {db_path}")
    
    # Ensure database parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error as e:
        print(f"[error] Failed to open database '{db_path}': {e}")
        sys.exit(1)

    try:
        # Apply schema
        apply_schema(conn, schema_path)
        
        # Read policy content
        print(f"[info] Reading preface from: {preface_path}")
        preface = read_text_file(preface_path)
        
        print(f"[info] Reading body from: {body_path}")
        body = read_text_file(body_path)
        
        # Insert policy
        insert_policy(conn, preface, body)
        
    finally:
        conn.close()


def main(argv=None) -> None:
    """
    Standalone CLI entrypoint for when this module is run directly:
        python cli/init_policy.py --db compendium.sqlite
    """
    parser = argparse.ArgumentParser(
        description="Initialize the Study Bible Compendium Hermeneutical Rule Policy in a locked SQLite table."
    )
    parser.add_argument(
        "--db",
        "--database",
        dest="db_path",
        default="compendium.sqlite",
        help="Path to the SQLite database file (default: compendium.sqlite)",
    )
    parser.add_argument(
        "--schema",
        dest="schema_path",
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to schema SQL file (default: {DEFAULT_SCHEMA_PATH})",
    )
    parser.add_argument(
        "--preface",
        dest="preface_path",
        default=DEFAULT_PREFACE_PATH,
        help=f"Path to preface text file (default: {DEFAULT_PREFACE_PATH})",
    )
    parser.add_argument(
        "--body",
        dest="body_path",
        default=DEFAULT_BODY_PATH,
        help=f"Path to body text file (default: {DEFAULT_BODY_PATH})",
    )
    
    args = parser.parse_args(argv)
    
    run_init_policy(
        db_path=args.db_path,
        schema_path=args.schema_path,
        preface_path=args.preface_path,
        body_path=args.body_path
    )


if __name__ == "__main__":
    main()
