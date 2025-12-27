# Study Bible Compendium - AI Agent Instructions

## Project Purpose

A **Study Bible Compendium** system managing biblical texts, lexicons, cross-references, and interpretive materials in a single **SQLite database** (`compendium.sqlite`). Core principle: hermeneutical rules must be immutable once set to ensure interpretive consistency.

## Architecture Overview

### Unified Database Architecture

The system uses a **single SQLite database** (`compendium.sqlite`) with **three coexisting schemas**:

**1. Immutable Policy System**
- Table: `hermeneutical_policy` (single row, trigger-locked)
- Entry point: `cli/init_policy.py` or `compendium.py init-policy`
- Policy source: `CANON/HERMENEUTICAL_RULE_POLICY.md` (SHA-256 locked)
- Database backup: `data/policy_preface.txt` + `data/policy_body.txt`
- Integrity: Three SQLite triggers prevent updates/deletes/extra inserts

**2. Normalized Verse Schema** (NEW - Production System)
- Table: `verses_normalized` (flat structure, multi-translation)
- Entry point: `compendium.py` (unified CLI using `sbc/` package)
- Format: `translation_code | book_num | chapter | verse | normalized_ref | text`
- Canon: 66-book Protestant canon via `data/canon.json`
- Features: Fast lookups, deduplication, canonical verse spine (`canonical_verses`)

**3. Legacy & Berean Schemas** (Compatibility Layer)
- Legacy: `bible_versions → books → chapters → verses` (317K verses, 14 translations)
- Berean: `berean_verses`, `berean_words`, `berean_strongs` (NT Greek interlinear)
- Entry points: `cli/study_bible_compendium.py`, `cli/import_berean.py`
- Status: Read-only, coexists with normalized schema

### Unified CLI Entry Point

**Primary interface**: `compendium.py` (NEW - use this for all operations)

```bash
# Policy and schema initialization
python compendium.py init-policy   # Lock hermeneutical policy
python compendium.py init-schema   # Create verses_normalized table
python compendium.py build-spine   # Build canonical verse spine

# Bible data operations (NEW unified API)
python compendium.py import-bible data/kjv.csv KJV
python compendium.py list-translations
python compendium.py search "faith" --translation KJV --limit 50
python compendium.py passage "John 3:16" --translations KJV BSB
python compendium.py context "Romans 8:28" --before 2 --after 2
python compendium.py parallel "Genesis 1:1" --translations KJV BSB ASV

# PDF report generation
python compendium.py pdf-report output.txt "Title" --body "Content..."
python compendium.py pdf-passage "John 3" output.pdf --translations KJV BSB
python compendium.py pdf-parallel "Genesis 1:1" output.pdf --translations KJV BSB

# System status
python compendium.py status        # Database health check

# Legacy CLI tools (compatibility only)
python cli\study_bible_compendium.py import-bible-csv --version-code BSB --file berean.csv
python cli\import_berean.py --db compendium.sqlite --berean-dir "sources\excel\Berean Bible"
python cli\query_berean.py --db compendium.sqlite --strongs 3056
python cli\xref_berean.py --db compendium.sqlite --verse "John 3:16"

# Utility tools
python tools\batch_pdf_to_excel.py --input sources\pdf\ --output sources\excel\
```

### Core Package Structure: `sbc/`

The unified CLI uses a modular package architecture:

```python
sbc/
├── config.py       # Project version and constants
├── paths.py        # Path management (PROJECT_ROOT, DB_PATH, SCHEMA_DIR)
├── db.py           # Database connection management
├── util.py         # Console output ([ok], [info], [warn], [error])
├── model.py        # Data models (Verse, Book classes)
├── loader.py       # Bible import from Excel/CSV
├── search.py       # Full-text verse search
├── context.py      # Verse context windows
├── parallel.py     # Multi-translation parallel views
├── spine.py        # Canonical verse spine builder
├── pdfgen.py       # PDF report generation
└── status.py       # System health checks
```

**Import pattern**:
```python
from sbc.paths import PROJECT_ROOT, DB_PATH
from sbc.loader import import_bible_from_excel
from sbc.search import search_verses
from sbc.db import get_conn
```

## Critical Implementation Patterns

### CANON Integrity System (NEW)

The hermeneutical policy uses **dual integrity locks**:

**1. Git-Level Lock** (`CANON/CANON_LOCK.md`)
- Tracks SHA-256 of `CANON/HERMENEUTICAL_RULE_POLICY.md`
- Generated via: `python TOOLS/scripts/canon_lock.py`
- CI verifies checksum on every push/PR
- Changes require PR + review + changelog entry

**2. Database-Level Lock** (`hermeneutical_policy` table)
- Three SQLite triggers prevent mutations:
  - `hermeneutical_policy_no_extra_inserts` - Blocks additional rows
  - `hermeneutical_policy_no_updates` - Blocks modifications  
  - `hermeneutical_policy_no_deletes` - Blocks deletions
- Content checksum stored in database
- Why: Biblical interpretation rules must remain consistent; changes invalidate derived scholarship

**Workflow for policy changes**:
```bash
# 1. Edit CANON/HERMENEUTICAL_RULE_POLICY.md
# 2. Update CANON/CANON_CHANGELOG.md
# 3. Regenerate lock
python TOOLS/scripts/canon_lock.py
# 4. Re-initialize database
python compendium.py init-policy --force
```

### Canonical Verse Spine Architecture

The `canonical_verses` table provides a **deduplication layer** for multi-translation verse storage:

```sql
-- Spine: One row per unique verse across all translations
CREATE TABLE canonical_verses (
    verse_id INTEGER PRIMARY KEY,
    normalized_ref TEXT UNIQUE,  -- e.g., 'GEN.1.1'
    book_num INTEGER,
    book_code TEXT,
    chapter INTEGER,
    verse INTEGER
);

-- Verses link to spine via verse_id
ALTER TABLE verses_normalized ADD COLUMN verse_id INTEGER;
```

**Why**: Allows notes, cross-references, and metadata to be translation-agnostic—attach to `verse_id` instead of duplicating per translation.

**Usage**:
```bash
# Build spine from imported verses
python compendium.py build-spine

# Notes can now reference verse_id instead of translation-specific rows
INSERT INTO notes (verse_id, content) VALUES (12345, 'Genesis 1:1 note');
```

### Berean Bible Schema Architecture
Separate schema in `compendium.sqlite` created by `import_berean.py`:
- `berean_verses`: Multi-translation text (BGB, BIB, BLB, BSB)
- `berean_words`: Interlinear Greek tokens with Strong's numbers
- `berean_strongs`: Strong's number definitions (unique lookup)

Tables use `verse_ref` format: `"Matthew|1:1"` or `"Matthew 1:1"` (both patterns exist).

### Cross-Reference Generation Strategy
`xref_berean.py` generates cross-references by finding verses sharing Strong's numbers:
```python
# Find verses sharing 2+ Strong's numbers with target verse
find_xrefs_for_verse(conn, "John 3:16", min_shared=2)

# Find all verses containing specific Strong's numbers
find_xrefs_by_strongs(conn, [3056, 2316])  # logos + theos
```

## Domain-Specific Knowledge

### Hermeneutical Priority Order
Biblical text interpretation follows strict linguistic hierarchy:
1. Original Hebrew (Old Testament)
2. Septuagint Greek (LXX) 
3. New Testament Greek
4. Plain-sense meaning

**Never override text with tradition, commentary, or theological systems.**

### Exegetical Methods Required
- **Typology**: Old Testament patterns → New Testament fulfillment
- **OT ↔ NT Cross-References**: Scripture interprets Scripture
- **Line-by-Line Exegesis**: Context-sensitive, never proof-texting
- **Hebrew Pictograms**: Optional teaching aid, never primary source

## Development Workflows

### Database Initialization Sequence

**Policy database** (first time setup):
```bash
# NEW: Automatically reads from schema/ and data/ directories
python compendium.py init-policy

# Or force re-initialization
python compendium.py init-policy --force
```

**Verse schema** (NEW unified system):
```bash
# 1. Create verses_normalized table
python compendium.py init-schema

# 2. Import Bible translations (Excel/CSV with columns: book,chapter,verse,text)
python compendium.py import-bible data/kjv.xlsx KJV
python compendium.py import-bible data/bsb.csv BSB --overwrite

# 3. Build canonical verse spine (deduplication layer)
python compendium.py build-spine

# 4. Query and export
python compendium.py search "faith" --translation KJV --limit 50
python compendium.py passage "John 3:16" --translations KJV BSB
python compendium.py pdf-passage "John 3" output.pdf --translations KJV BSB
```

### Berean Bible Import Workflow

Berean Bible uses different CSV structure (`berean_text.csv`, `berean_tables.csv`) and creates its own schema:
```bash
# Import from "Berean Bible" directory containing CSV files
python cli\import_berean.py --db compendium.sqlite --berean-dir "sources\excel\Berean Bible"

# Query by Strong's number (G3056 = logos)
python cli\query_berean.py --db compendium.sqlite --strongs 3056 --limit 20

# Generate cross-references for a verse
python cli\xref_berean.py --db compendium.sqlite --verse "John 1:1" --min-shared 2
```

### PDF Processing Utilities

Convert reference PDFs to Excel for data extraction:
```bash
# Single file conversion
python tools\word_to_excel.py --input sources\pdf\concordance.pdf --output concordance.xlsx --mode text

# Batch conversion
python tools\batch_pdf_to_excel.py \
  --input "sources\excel\Study Bibles" \
  --output "sources\excel\excel_output" \
  --mode text \
  --save-every 500  # Auto-save every 500 pages for large files
```

Modes: `text` (line-by-line extraction) or `tables` (extract tabular data).

### Testing Database Immutability

```bash
# Initialize policy
python cli\init_policy.py --db test.db

# Verify triggers work (should fail with ABORT error)
sqlite3 test.db "UPDATE hermeneutical_policy SET title='test';"
# Expected: Error: hermeneutical_policy is locked; updates are not allowed

# Check policy integrity
sqlite3 test.db "SELECT checksum, version FROM hermeneutical_policy WHERE id=1;"
```

## Key File Locations

### Policy System (`compendium.sqlite`)
- **Schema**: `schema/hermeneutical_policy.sql` - Table definition + 3 locking triggers
- **Policy source**: `CANON/HERMENEUTICAL_RULE_POLICY.md` - Canonical policy (SHA-256 locked)
- **Policy lock**: `CANON/CANON_LOCK.md` - Git-level checksum verification
- **Policy changelog**: `CANON/CANON_CHANGELOG.md` - Version history
- **Database backup**: `data/policy_preface.txt` + `data/policy_body.txt`
- **Loader**: `cli/init_policy.py` - Policy initialization tool

### Verse Schema (NEW - `verses_normalized`)
- **Main CLI**: `compendium.py` - Unified entry point (uses `sbc/` package)
- **Schema**: `schema/verse_schema.sql` - Flat verses_normalized table
- **Spine schema**: `schema/canonical_verses.sql` - Deduplication layer
- **Notes schema**: `schema/notes.sql` - Verse annotations
- **Canon definition**: `data/canon.json` - 66-book Protestant canon (book_num, code, name)
- **Package modules**: `sbc/*.py` - Core functionality (loader, search, parallel, pdfgen, etc.)

### Legacy & Berean Bible Tools
- **Legacy engine**: `cli/study_bible_compendium.py` - Hierarchical schema (317K verses)
- **Berean importer**: `cli/import_berean.py` - NT Greek interlinear
- **Berean query**: `cli/query_berean.py` - Strong's number search
- **Cross-references**: `cli/xref_berean.py` - Shared Strong's number finder

### Utility Scripts
- **PDF conversion**: `tools/batch_pdf_to_excel.py`, `tools/word_to_excel.py`
- **Excel conversion**: `tools/convert_excel_to_csv.py`
- **Sample data**: `data/kjv_sample.csv`, `data/test_sample.csv`
- **Source materials**: `sources/pdf/` (reference PDFs), `sources/excel/` (Bible CSVs)

### Code Organization Pattern

All modules follow this structure:
1. **Module docstring** - Purpose and usage examples
2. **Imports** - Standard library only (no external dependencies except PDF tools)
3. **Helper functions** - Internal operations (database, parsing, formatting)
4. **Core functionality** - Primary business logic
5. **Public API** - `run_*()` functions for library use
6. **CLI entrypoint** - `main(argv=None)` with argparse
7. **Guard**: `if __name__ == "__main__": main()`

## Testing & Validation

### Manual Testing Workflow
```bash
# Initialize policy
python study_bible_cli.py --init-policy --db test.db

# Verify policy locked (should fail with trigger error)
sqlite3 test.db "UPDATE hermeneutical_policy SET title='test';"
```

### Checksum Validation
```python
# Read policy and verify integrity
cur.execute("SELECT preface, body, checksum FROM hermeneutical_policy WHERE id=1")
preface, body, stored_checksum = cur.fetchone()
computed = compute_checksum(preface, body)
assert computed == stored_checksum, "Policy corruption detected"
```

### Testing PDF Conversion
```bash
# Test single file
python word_to_excel.py --input test.pdf --output test.xlsx --mode text

# Test batch with auto-save for large files
python batch_pdf_to_excel.py --input pdfs/ --output excel/ --save-every 500
```

## Common Pitfalls

1. **Never attempt UPDATE/DELETE on policy table** - Database triggers will abort transaction
2. **Policy must be inserted exactly once** - Additional inserts blocked by trigger
3. **Always use `run_init_policy()` not direct SQL** - Ensures schema/triggers exist first
4. **Path.parent.mkdir()** - CLI creates DB directory if needed; don't assume it exists
5. **Timestamp format** - Always use `datetime.utcnow().replace(microsecond=0).isoformat() + "Z"` for `effective_utc` field

## Technical Conventions

### Import Style
- Standard library only (no external dependencies)
- Imports: `argparse`, `sqlite3`, `hashlib`, `datetime`, `pathlib`, `textwrap`, `sys`
- Alias datetime: `import datetime as _dt` (underscore prefix convention)

### Console Output Format
Use standardized prefixes for all console messages:
- `[ok]` - Successful operations
- `[info]` - Informational messages
- `[warn]` - Warnings that don't halt execution
- `[error]` - Fatal errors before `sys.exit(1)`

### String Formatting
- Policy text uses `textwrap.dedent()` with `.strip()` to maintain clean multi-line constants
- SQL uses triple-quoted strings for readability
- Database paths default to `study_bible_compendium.db` in working directory

## Extending the System

When adding new CLI commands:
1. Add argparse flag in `build_parser()` in `study_bible_cli.py`
2. Handle flag in `main()` before `parser.print_help()`
3. Follow exit pattern: `sys.exit(0)` on success for subcommands
4. Always respect `--db` flag for database path consistency

### Future Extension Points
The codebase structure suggests planned features:
- Word studies and lexical analysis tools
- Cross-reference generation system
- Commentary and doctrinal note generation
- Biblical typology mapping tools

**When implementing**: All generated content must conform to the hermeneutical policy (verify via checksum, respect linguistic priority order).

## Project Directory Structure

```
Study_Bible_Compendium/
├─ compendium.sqlite           # Single database (policy + Bible data)
├─ compendium.py               # NEW unified CLI entry point
├─ cli/                        # All executable scripts
│  ├─ init_policy.py           # Policy initialization (file-based)
│  ├─ study_bible_cli.py       # Legacy CLI wrapper
│  ├─ study_bible_compendium.py # Legacy Bible data engine
│  ├─ import_berean.py         # Berean Bible importer
│  ├─ query_berean.py          # Strong's number search
│  └─ xref_berean.py           # Cross-reference generator
├─ sbc/                        # NEW core package (Python library)
│  ├─ config.py                # Version constants
│  ├─ paths.py                 # Path management
│  ├─ db.py                    # Database connections
│  ├─ util.py                  # Console output helpers
│  ├─ model.py                 # Data models (Verse, Book)
│  ├─ loader.py                # Bible import engine
│  ├─ search.py                # Verse search
│  ├─ context.py               # Context windows
│  ├─ parallel.py              # Multi-translation views
│  ├─ spine.py                 # Canonical verse spine
│  ├─ pdfgen.py                # PDF report generation
│  └─ status.py                # System health checks
├─ schema/                     # SQL schema definitions
│  ├─ hermeneutical_policy.sql # Policy table + triggers
│  ├─ verse_schema.sql         # verses_normalized table
│  ├─ canonical_verses.sql     # Deduplication spine
│  ├─ notes.sql                # Verse annotations
│  └─ translations.sql         # Translation metadata
├─ CANON/                      # NEW hermeneutical policy (locked)
│  ├─ HERMENEUTICAL_RULE_POLICY.md  # Canonical policy
│  ├─ CANON_LOCK.md            # SHA-256 checksum
│  └─ CANON_CHANGELOG.md       # Version history
├─ data/                       # Policy text & reference data
│  ├─ policy_preface.txt       # Editable preface
│  ├─ policy_body.txt          # Editable policy rules
│  ├─ canon.json               # 66-book Protestant canon
│  ├─ kjv_sample.csv           # Sample Bible data
│  └─ converted/               # Batch-converted CSVs
├─ sources/                    # Original source materials
│  ├─ pdf/                     # Reference PDFs
│  └─ excel/                   # Bible CSV sources
│     ├─ Berean Bible/
│     ├─ Study Bibles/
│     └─ Bibles/
├─ tools/                      # Conversion utilities
│  ├─ batch_pdf_to_excel.py
│  ├─ word_to_excel.py
│  └─ convert_excel_to_csv.py
├─ TOOLS/                      # NEW scripts for maintenance
│  └─ scripts/
│     └─ canon_lock.py         # Regenerate CANON_LOCK.md
├─ docs/                       # Documentation
│  ├─ SCHEMA_ARCHITECTURE.md   # Database schema design
│  ├─ DEV_HANDOFF_Phase_Policy_and_Structure.md
│  └─ PHASE_COMPLETE_Verse_Schema.md
├─ STUDIES/                    # Scriptural studies (governed by CANON)
│  ├─ word-studies/
│  └─ typology/
├─ .github/
│  └─ copilot-instructions.md  # This file
└─ workspace.code-workspace
```

## Data Flow Architecture

```
Policy Storage (compendium.sqlite)
├── hermeneutical_policy (immutable, trigger-locked)
│   ├── Loaded from: schema/hermeneutical_policy.sql
│   └── Content from: data/policy_preface.txt + data/policy_body.txt

Bible Data DB (compendium.sqlite)
├── Main Schema (study_bible_compendium.py)
│   ├── bible_versions → books → chapters → verses
│   ├── strongs_lexicon ↔ verse_strongs (many-to-many)
│   ├── interlinear_tokens (word-level original language)
│   ├── midrash_sources → midrash_notes
│   └── user_notes, crossrefs
│
├── Normalized Schema (NEW - compendium.py via sbc/)
│   ├── verses_normalized (flat, multi-translation)
│   ├── canonical_verses (spine: one row per verse across translations)
│   ├── notes (attached to verse_id from spine)
│   └── translations (metadata for loaded Bibles)
│
└── Berean Schema (import_berean.py)
    ├── berean_verses (multi-translation: BGB, BIB, BLB, BSB)
    ├── berean_words (Greek tokens with Strong's numbers)
    └── berean_strongs (definitions)
```

Cross-references discovered by:
1. Shared Strong's numbers between verses (`xref_berean.py`)
2. Manual typology mapping (future)
3. NT citations of OT (manual annotation, future)

## Environment Notes

- **Operating System**: Windows (file paths use backslashes, e.g., `c:\Users\...`)
- **Default Shell**: PowerShell (`pwsh.exe`)
- **File path spaces**: Project directory contains space: `Study_Bible _Compendium` - quote paths when needed
- **Python version**: Python 3.x (uses `#!/usr/bin/env python3`, f-strings, type hints in signatures)
