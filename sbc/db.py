"""
Database connection management for the Study Bible Compendium.
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator

from .paths import DB_PATH


@contextmanager
def get_conn(readonly: bool = False) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    
    Args:
        readonly: If True, open in read-only mode
        
    Yields:
        sqlite3.Connection with row_factory set to Row
    """
    uri = f"file:{DB_PATH}?mode=ro" if readonly else str(DB_PATH)
    conn = sqlite3.connect(uri, uri=readonly)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def ping() -> bool:
    """
    Check if the database is reachable.
    
    Returns:
        True if database exists and can be connected to
    """
    if not DB_PATH.exists():
        return False
    
    try:
        with get_conn(readonly=True) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
