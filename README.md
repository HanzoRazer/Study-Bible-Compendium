# Study Bible Compendium

A unified, offline-friendly system for collecting Study Bibles, lexicons, grammars, and study aids into one searchable source—so users can draw from many commentaries and cross references in one place.

## Two Sections (by design)

### 1) CANON (Founding Philosophy)
`/CANON/` contains the repository's canonical hermeneutical framework.
These files are protected and checksum-locked.

### 2) STUDIES (Scriptural Studies)
`/STUDIES/` contains verse-by-verse notes, word studies, typology studies, and teaching guides.
Studies are governed by the CANON policy but are expected to grow continuously.

## Repository Structure

```
Study-Bible-Compendium/
├── CANON/                    # Locked hermeneutical policy
│   ├── HERMENEUTICAL_RULE_POLICY.md
│   ├── CANON_CHANGELOG.md
│   └── CANON_LOCK.md
├── STUDIES/                  # Scriptural studies (governed by CANON)
│   ├── word-studies/
│   └── typology/
├── TOOLS/                    # Utility scripts
│   └── scripts/
├── cli/                      # CLI tools
├── sbc/                      # Core library modules
├── schema/                   # Database schemas
├── data/                     # Data files and imports
└── docs/                     # Documentation
```

## Canon Integrity

The hermeneutical policy is checksum-locked to prevent silent drift.

Run locally:
```bash
python TOOLS/scripts/canon_lock.py
```

CI verifies the canon lock on every push and PR.

## Database

The compendium uses SQLite with:
- **berean_verses** — NT Greek + English translations (7,957 verses)
- **verse_notes** — Midrash commentary linked to verses
- **greek_margins** — Word/phrase-level Greek parsing
- **core_passages** — High-value passage registry

## Quick Start

```bash
# Check system status
python compendium.py status

# Search verses
python compendium.py search "love"

# Get passage
python compendium.py passage "John 3:16"

# Compare translations
python compendium.py compare "Romans 8:28" BSB BLB
```

## Hermeneutical Policy (Summary)

> "Follow the original language when you have issues.
> The language will bear out 90% of the interpretation in most cases."

See `/CANON/HERMENEUTICAL_RULE_POLICY.md` for the full policy.
