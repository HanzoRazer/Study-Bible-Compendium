#!/usr/bin/env python3
"""
Canon Lock Generator

Generates a checksum lock file for the canonical hermeneutical policy.
This ensures any changes to CANON/ files are tracked and intentional.

Usage:
    python TOOLS/scripts/canon_lock.py
"""

import hashlib
from pathlib import Path
from datetime import datetime, timezone

CANON_FILE = Path("CANON/HERMENEUTICAL_RULE_POLICY.md")
LOCK_FILE = Path("CANON/CANON_LOCK.md")


def sha256(p: Path) -> str:
    """Compute SHA256 hash of a file."""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    """Generate the canon lock file."""
    if not CANON_FILE.exists():
        raise SystemExit(f"Missing {CANON_FILE}")

    digest = sha256(CANON_FILE)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    content = f"""# Canon Lock

**Canonical file:** `{CANON_FILE.as_posix()}`
**SHA256:** `{digest}`
**Generated (UTC):** `{ts}`

## Change rules
- Canon changes require PR + review
- Update `CANON/CANON_CHANGELOG.md`
- Regenerate this lock file via:
  - `python TOOLS/scripts/canon_lock.py`

## Notes
This lock exists to prevent silent drift of foundational hermeneutics.
"""
    LOCK_FILE.write_text(content, encoding="utf-8")
    print(f"[ok] Wrote {LOCK_FILE}")
    print(f"     SHA256: {digest}")


if __name__ == "__main__":
    main()
