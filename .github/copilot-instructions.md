# Study Bible Compendium - AI Agent Instructions

## Project Purpose

A **Study Bible Compendium** system managing biblical texts, lexicons, cross-references, and interpretive materials using multiple **SQLite databases** with different schemas. Core principle: hermeneutical rules must be immutable once set to ensure interpretive consistency.

## Architecture Overview

### Two Parallel Database Systems

**1. Hermeneutical Policy Database** (`compendium.sqlite`)
- Entry point: `cli/init_policy.py` (NEW: file-based loader)
- Reads schema from `schema/hermeneutical_policy.sql`
- Reads policy text from `data/policy_preface.txt` and `data/policy_body.txt`
- Single-record immutable policy table with SHA-256 checksum
- Enforced via SQLite triggers (no updates/deletes/additional inserts)

**2. Bible Data Database** (`compendium.sqlite`)
- Entry points: `study_bible_compendium.py` (main engine) and specialized importers
- Multi-version Bible text storage (KJV, BSB, ASV, Greek, Hebrew)
- Strong's lexicon with verse mappings
- Interlinear tokens for original language analysis
- Cross-reference generation via shared Strong's numbers

### Key Entry Points

```bash
# Policy initialization (NEW: file-based, reads from data/ and schema/)
python cli\init_policy.py --db compendium.sqlite
python cli\study_bible_cli.py --init-policy --db compendium.sqlite

# Bible data operations (main engine with subcommands)
python cli\study_bible_compendium.py import-bible-csv --version-code BSB --file berean.csv
python cli\study_bible_compendium.py import-strongs --language el --file strongs.csv
python cli\study_bible_compendium.py search --query "faith" --version-code KJV

# Berean Bible-specific tools (separate schema in compendium.sqlite)
python cli\import_berean.py --db compendium.sqlite --berean-dir "sources\excel\Berean Bible"
python cli\query_berean.py --db compendium.sqlite --strongs 3056  # Search by Strong's number
python cli\xref_berean.py --db compendium.sqlite --verse "John 3:16"  # Cross-references

# Utility tools
python tools\batch_pdf_to_excel.py --input sources\pdf\ --output sources\excel\excel_output\
```

## Critical Implementation Patterns

### Immutable Policy Pattern (Policy DB)
The hermeneutical policy uses **three database triggers** to prevent changes:
1. `hermeneutical_policy_no_extra_inserts` - Blocks additional rows
2. `hermeneutical_policy_no_updates` - Blocks modifications  
3. `hermeneutical_policy_no_deletes` - Blocks deletions

**Why**: Biblical interpretation rules must remain consistent; changes would invalidate derived scholarship.

### Checksum Verification
Policy content integrity protected via SHA-256:
```python
checksum = hashlib.sha256((preface + "\n\n" + body).encode("utf-8")).hexdigest()
```

### Dual-Interface Module Pattern
Both CLI tools expose two interfaces:
```python
# Library interface (for integration)
run_init_policy(db_path: str) -> None

# Standalone CLI (underscore-prefixed private function)
def main(argv=None) -> None
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
python cli\init_policy.py --db compendium.sqlite

# Or via main CLI
python cli\study_bible_cli.py --init-policy --db compendium.sqlite
```

**Bible data database** (multi-step import):
```bash
# 1. Import Bible text (CSV format: book,chapter,verse,text)
python cli\study_bible_compendium.py import-bible-csv \
  --version-code BSB \
  --version-name "Berean Study Bible" \
  --language en \
  --file berean.csv

# 2. Import Strong's lexicon (strongs_number,language,lemma,gloss,extra)
python cli\study_bible_compendium.py import-strongs \
  --language el \
  --file data\strongs_greek.csv

# 3. Import interlinear tokens (verse_ref,word_index,language,surface,lemma,strongs_number,morph)
python cli\study_bible_compendium.py import-interlinear --file interlinear.csv

# 4. Query and export
python cli\study_bible_compendium.py search --query "faith" --version-code BSB --limit 50
python cli\study_bible_compendium.py export-pdf \
  --version-code BSB \
  --book John \
  --chapter 3 \
  --outfile john3.pdf
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
- **Policy text**: `data/policy_preface.txt` and `data/policy_body.txt` - Editable policy content
- **Loader**: `cli/init_policy.py` - File-based policy initialization
- **CLI integration**: `cli/study_bible_cli.py` - argparse setup and subcommand handling
- **Reference**: `data/Study_Bible_Compendium_Hermeneutical_Rule_Policy.txt` - Human-readable full policy

### Bible Data Engine (`compendium.sqlite`)
- **Main engine**: `cli/study_bible_compendium.py` - comprehensive schema with subcommands:
  - `import-bible-csv` → multi-version text
  - `import-strongs` → lexicon data
  - `import-interlinear` → original language tokens
  - `import-midrash` → study notes
  - `search` → full-text verse search
  - `export-pdf` → chapter PDF generation
  - `export-midrash-pdf` → study report PDFs

### Berean Bible Tools (separate schema in `compendium.sqlite`)
- **Importer**: `cli/import_berean.py` - creates `berean_verses`, `berean_words`, `berean_strongs` tables
- **Query tool**: `cli/query_berean.py` - search by Strong's numbers or Greek words
- **Cross-reference generator**: `cli/xref_berean.py` - find thematic connections via shared Strong's numbers

### Utility Scripts
- **PDF conversion**: `tools/batch_pdf_to_excel.py`, `tools/word_to_excel.py` - extract text/tables from PDFs
- **Sample data**: `data/kjv_sample.xlsx`, `data/strongs_sample.xlsx` - CSV format examples
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
├─ cli/                        # All executable scripts
│  ├─ init_policy.py           # Policy initialization (file-based)
│  ├─ study_bible_cli.py       # Main CLI wrapper
│  ├─ study_bible_compendium.py # Bible data engine
│  ├─ import_berean.py         # Berean Bible importer
│  ├─ query_berean.py          # Strong's number search
│  └─ xref_berean.py           # Cross-reference generator
├─ schema/                     # SQL schema definitions
│  └─ hermeneutical_policy.sql # Policy table + triggers
├─ data/                       # Policy text & reference data
│  ├─ policy_preface.txt       # Editable preface
│  ├─ policy_body.txt          # Editable policy rules
│  ├─ kjv_sample.xlsx          # Sample Bible CSV
│  └─ strongs_sample.xlsx      # Sample lexicon CSV
├─ sources/                    # Original source materials
│  ├─ pdf/                     # Reference PDFs
│  └─ excel/                   # Bible CSV sources
│     ├─ Berean Bible/
│     ├─ Study Bibles/
│     └─ Bibles/
├─ tools/                      # Conversion utilities
│  ├─ batch_pdf_to_excel.py
│  ├─ word_to_excel.py
│  └─ convert_single_pdf_retry.py
├─ docs/                       # Documentation
│  └─ DEV_HANDOFF_Phase_Policy_and_Structure.md
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
