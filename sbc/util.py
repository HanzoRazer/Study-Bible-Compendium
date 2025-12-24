"""
Utility functions for console output and common operations.
"""


def info(msg: str) -> None:
    """Print an info message."""
    print(f"[info] {msg}")


def warn(msg: str) -> None:
    """Print a warning message."""
    print(f"[warn] {msg}")


def ok(msg: str) -> None:
    """Print a success message."""
    print(f"[ok] {msg}")
