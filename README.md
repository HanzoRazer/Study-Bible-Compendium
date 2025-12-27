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
│   ├── typology/
│   ├── greek-margins/        # Greek word/phrase annotations (JSON)
│   ├── verse-notes/          # Midrash commentary (JSON)
│   └── core-passages/        # High-value passage registry (JSON)
├── TOOLS/                    # Utility scripts
│   └── scripts/
├── cli/                      # CLI tools
│   ├── install_core_passage.ps1  # Convenience installer (PowerShell)
│   └── install_core_passage.sh   # Convenience installer (Bash)
├── sbc/                      # Core library modules
│   ├── core_passages.py      # Core passage installer
│   ├── loader.py             # Bible data loader
│   ├── search.py             # Verse search
│   └── ...                   # Other modules
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

The compendium uses SQLite (`compendium.sqlite`) with:
- **berean_verses** — NT Greek + English translations (7,957 verses)
- **verses_normalized** — Multi-translation flat schema (66-book Protestant canon)
- **canonical_verses** — Canonical verse spine (deduplication layer)
- **verse_notes** — Midrash commentary linked to verses
- **greek_margins** — Word/phrase-level Greek parsing
- **core_passages** — High-value passage registry
- **hermeneutical_policy** — Immutable policy (trigger-locked)
### Basic Bible Operations

```bash
# Check system status
python compendium.py status

# Search verses
python compendium.py search "faith" --translation KJV --limit 50

# Get passage with multiple translations
python compendium.py passage "John 3:16" --translations KJV BSB

# View passage with context
python compendium.py context "Romans 8:28" --before 2 --after 2

# Compare translations side-by-side
python compendium.py parallel "Genesis 1:1" --translations KJV BSB ASV
```

### Core Passages (Annotations System)

The STUDIES/ directory contains JSON-based annotations for high-value passages:

```bash
# Install a core passage unit (PowerShell)
.\cli\install_core_passage.ps1 romans_8 sanctification

# Install a core passage unit (Bash)
./cli/install_core_passage.sh romans_8 sanctification

# Install using Python module directly
python -m sbc.core_passages --db compendium.sqlite add-from-json \
  --greek-margins STUDIES/greek-margins/romans_8.json \
  --verse-notes STUDIES/verse-notes/romans_8.json \
  --core-passage STUDIES/core-passages/sanctification.json

# Initialize core passages schema
python -m sbc.core_passages --db compendium.sqlite init-schema
```

### Creating New Annotations

Annotations are stored as JSON in `STUDIES/` subdirectories:

1. **Greek Margins** (`STUDIES/greek-margins/{passage}.json`) - Word/phrase-level Greek parsing
2. **Verse Notes** (`STUDIES/verse-notes/{passage}.json`) - Midrash commentary
3. **Core Passages** (`STUDIES/core-passages/{category}.json`) - Passage metadata

See `STUDIES/README.md` for JSON schemas and examples.
# Compare translations
python compendium.py compare "Romans 8:28" BSB BLB
```

## Hermeneutical Policy (Summary)

> "Follow the original language when you have issues.
> The language will bear out 90% of the interpretation in most cases."

See `/CANON/HERMENEUTICAL_RULE_POLICY.md` for the full policy.
