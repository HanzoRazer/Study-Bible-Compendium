# Study Bible Compendium - Quick Reference

## Unified CLI (`compendium.py`)

### Setup Commands

```bash
# Initialize hermeneutical policy (immutable, trigger-locked)
python compendium.py init-policy

# Initialize verse schema (create verses_normalized table)
python compendium.py init-schema
```

### Data Import

```bash
# Import a Bible translation from CSV
python compendium.py import-bible <file.csv> <CODE>

# Example: Import KJV
python compendium.py import-bible data/kjv.csv KJV

# Overwrite existing translation
python compendium.py import-bible data/kjv_updated.csv KJV --overwrite
```

**CSV Format Expected**:
```csv
book,chapter,verse,text
Genesis,1,1,In the beginning God created the heaven and the earth.
John,3,16,For God so loved the world...
```

### Search & Query

```bash
# Search all translations (case-insensitive)
python compendium.py search "faith"

# Limit results
python compendium.py search "Barnabas" --limit 5

# List loaded translations
python compendium.py list-translations
```

### Reports (Stub)

```bash
# Generate basic report
python compendium.py pdf-report output.txt
```

---

## Legacy CLI Tools

### Main Bible Engine (`cli/study_bible_compendium.py`)

```bash
# Import Bible (legacy hierarchical schema)
python cli/study_bible_compendium.py import-bible-csv \
  --version-code KJV \
  --version-name "King James Version" \
  --language en \
  --file kjv.csv

# Import Strong's lexicon
python cli/study_bible_compendium.py import-strongs \
  --language el \
  --file strongs_greek.csv

# Search verses (legacy schema)
python cli/study_bible_compendium.py search \
  --query "faith" \
  --version-code KJV \
  --limit 50

# Export chapter to PDF
python cli/study_bible_compendium.py export-pdf \
  --version-code KJV \
  --book John \
  --chapter 3 \
  --outfile john3.pdf
```

### Berean Bible Tools

```bash
# Import Berean Bible interlinear data
python cli/import_berean.py \
  --db compendium.sqlite \
  --berean-dir "sources/excel/Berean Bible"

# Query by Strong's number
python cli/query_berean.py \
  --db compendium.sqlite \
  --strongs 3056    # G3056 = λόγος (logos)

# Generate cross-references for a verse
python cli/xref_berean.py \
  --db compendium.sqlite \
  --verse "John 3:16" \
  --min-shared 2    # Minimum shared Strong's numbers
```

---

## Database Architecture

### Three Schema Systems

1. **Normalized Schema** (NEW - `verses_normalized`)
   - Flat table with normalized refs (GEN.1.1)
   - Used by: `compendium.py`
   - Status: 3 verses (TEST translation)

2. **Legacy Schema** (OLD - hierarchical)
   - Tables: `bible_versions` → `books` → `chapters` → `verses`
   - Used by: `cli/study_bible_compendium.py`
   - Status: 317,529 verses across 14 translations

3. **Berean Schema** (interlinear)
   - Tables: `berean_verses`, `berean_words`, `berean_strongs`
   - Used by: `cli/query_berean.py`, `cli/xref_berean.py`
   - Status: 138,993 Greek words, 5,349 Strong's definitions

### Key Directories

```
Study_Bible_Compendium/
├── compendium.py              # Unified CLI ✅
├── compendium.sqlite          # Single database (3 schemas)
├── sbc/                       # Python package (new CLI backend)
├── cli/                       # Legacy CLI tools
├── schema/                    # SQL schema definitions
├── data/                      # Canon, policy, sample data
├── sources/                   # Original PDFs and Excel files
├── tools/                     # PDF conversion utilities
└── docs/                      # Documentation
```

---

## Common Workflows

### 1. First-Time Setup

```bash
# 1. Initialize policy
python compendium.py init-policy

# 2. Initialize verse schema
python compendium.py init-schema

# 3. Import a Bible
python compendium.py import-bible data/kjv.csv KJV

# 4. Verify import
python compendium.py list-translations

# 5. Test search
python compendium.py search "faith"
```

### 2. Import Multiple Translations

```bash
python compendium.py import-bible sources/kjv.csv KJV
python compendium.py import-bible sources/bsb.csv BSB
python compendium.py import-bible sources/asv.csv ASV

python compendium.py list-translations
# Expected output:
#   - ASV
#   - BSB
#   - KJV
```

### 3. Greek Word Study (Berean)

```bash
# 1. Search for Greek word "logos" (G3056)
python cli/query_berean.py --strongs 3056

# 2. Find cross-references for John 1:1
python cli/xref_berean.py --verse "John 1:1"

# Output: Verses sharing Strong's numbers with John 1:1
```

### 4. Convert PDFs to Excel

```bash
# Single file
python tools/word_to_excel.py \
  --input sources/pdf/concordance.pdf \
  --output concordance.xlsx \
  --mode text

# Batch conversion
python tools/batch_pdf_to_excel.py \
  --input "sources/pdf" \
  --output "sources/excel/excel_output" \
  --mode text
```

---

## Data Sources

### Expected CSV Format for Bible Import

**Columns**: `book`, `chapter`, `verse`, `text`

**Book names** (case-insensitive):
- Old Testament: Genesis, Exodus, Leviticus, Numbers, Deuteronomy, Joshua, Judges, Ruth, 1 Samuel, 2 Samuel, 1 Kings, 2 Kings, 1 Chronicles, 2 Chronicles, Ezra, Nehemiah, Esther, Job, Psalms, Proverbs, Ecclesiastes, Song of Solomon, Isaiah, Jeremiah, Lamentations, Ezekiel, Daniel, Hosea, Joel, Amos, Obadiah, Jonah, Micah, Nahum, Habakkuk, Zephaniah, Haggai, Zechariah, Malachi
- New Testament: Matthew, Mark, Luke, John, Acts, Romans, 1 Corinthians, 2 Corinthians, Galatians, Ephesians, Philippians, Colossians, 1 Thessalonians, 2 Thessalonians, 1 Timothy, 2 Timothy, Titus, Philemon, Hebrews, James, 1 Peter, 2 Peter, 1 John, 2 John, 3 John, Jude, Revelation

**Book codes** (3-letter):
GEN, EXO, LEV, NUM, DEU, JOS, JDG, RUT, 1SA, 2SA, 1KI, 2KI, 1CH, 2CH, EZR, NEH, EST, JOB, PSA, PRO, ECC, SNG, ISA, JER, LAM, EZK, DAN, HOS, JOL, AMO, OBA, JON, MIC, NAM, HAB, ZEP, HAG, ZEC, MAL, MAT, MRK, LUK, JHN, ACT, ROM, 1CO, 2CO, GAL, EPH, PHP, COL, 1TH, 2TH, 1TI, 2TI, TIT, PHM, HEB, JAS, 1PE, 2PE, 1JN, 2JN, 3JN, JUD, REV

---

## Troubleshooting

### Import fails with "Unknown book"
- Check book name spelling in CSV (must match canon names)
- Book names are case-insensitive but must be complete (e.g., "Genesis" not "Gen")
- See `data/canon.json` for official book names

### Search returns no results
- Check that translation is imported: `python compendium.py list-translations`
- Search is case-insensitive and uses LIKE (wildcards implicit)
- Try broader query (e.g., "love" instead of "God so loved")

### Database locked errors
- Only one write operation at a time
- Close other connections (e.g., SQLite browser, other Python scripts)
- Policy table is intentionally locked by triggers (cannot UPDATE/DELETE)

### Legacy vs. new schema confusion
- `compendium.py` uses **verses_normalized** (new flat schema)
- `cli/study_bible_compendium.py` uses **verses** (old hierarchical schema)
- Both systems coexist in same database (compendium.sqlite)
- See `docs/SCHEMA_ARCHITECTURE.md` for details

---

## Status Dashboard

### Database Contents (as of last check)

```
compendium.sqlite:
├── verses_normalized    3 verses (TEST)
├── verses             317,529 verses (14 translations - legacy)
├── berean_verses      7,957 NT verses (4 translations)
├── berean_words       138,993 Greek words
└── berean_strongs     5,349 Strong's definitions
```

### CLI Status

| Command | Status | Notes |
|---------|--------|-------|
| `init-policy` | ✅ Working | Policy table locked |
| `init-schema` | ✅ Working | Creates verses_normalized |
| `import-bible` | ✅ Working | CSV import functional |
| `search` | ✅ Working | LIKE-based text search |
| `list-translations` | ✅ Working | Lists distinct codes |
| `pdf-report` | ⚠️ Stub | Writes .txt placeholder |

### Next Priority Tasks

1. Import real Bible translations (KJV, BSB, ASV) into verses_normalized
2. Implement FTS5 full-text search for performance
3. Wire PDF generation to actual PDF library
4. Add translation metadata table
5. Build cross-reference links between normalized and Berean schemas

---

**Last Updated**: Phase Verse Schema Deployment  
**Documentation**: See `docs/` directory for detailed guides
