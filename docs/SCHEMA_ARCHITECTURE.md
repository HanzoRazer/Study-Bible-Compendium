# Database Schema Architecture

## Dual Verse Storage Systems

The `compendium.sqlite` database contains **two parallel verse storage schemas**:

### 1. Legacy Schema (Hierarchical)
**Tables**: `bible_versions` → `books` → `chapters` → `verses`

- Created by: `cli/study_bible_compendium.py`
- Structure: Relational hierarchy with foreign keys
- Status: **317,529 verses** from 14 translations (AKJV, ASV, BLB, BSB, CPDV, DBT, DRB, ERV, JPS, KJV, SLT, WBT, WEB, YLT)
- Use case: Legacy imports, compatibility with older tooling

**Legacy verses table schema**:
```sql
CREATE TABLE verses (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER,
    verse_number INTEGER,
    text TEXT
);
```

### 2. Normalized Schema (Flat)
**Table**: `verses_normalized`

- Created by: `compendium.py init-schema` (via `schema/verse_schema.sql`)
- Structure: Flat table with normalized references
- Status: **Empty** - ready for new imports
- Use case: New unified CLI imports, fast lookups, multi-translation queries

**Normalized schema**:
```sql
CREATE TABLE verses_normalized (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_code TEXT NOT NULL,    -- 'KJV', 'BSB', etc.
    book_num INTEGER NOT NULL,         -- 1-66 (Protestant canon)
    book_code TEXT NOT NULL,           -- 'GEN', 'EXO', etc.
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    normalized_ref TEXT NOT NULL,      -- 'GEN.1.1'
    text TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    created_utc TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (translation_code, book_num, chapter, verse)
);
```

### 3. Berean Bible Schema (Interlinear)
**Tables**: `berean_verses`, `berean_words`, `berean_strongs`

- Created by: `cli/import_berean.py`
- Structure: Multi-translation text + Greek interlinear tokens
- Status: **7,957 NT verses**, **138,993 Greek words**, **5,349 Strong's definitions**
- Use case: Original language study, cross-references via Strong's numbers

**Key tables**:
```sql
CREATE TABLE berean_verses (
    verse_ref TEXT PRIMARY KEY,  -- 'Matthew 1:1'
    bgb TEXT,                     -- Berean Greek Bible
    bib TEXT,                     -- Berean Interlinear Bible
    blb TEXT,                     -- Berean Literal Bible
    bsb TEXT                      -- Berean Study Bible
);

CREATE TABLE berean_words (
    verse_ref TEXT,
    word_index INTEGER,
    greek TEXT,                   -- Greek surface form
    translit TEXT,                -- Transliteration
    strongs TEXT,                 -- Strong's number (G1234)
    english TEXT                  -- English gloss
);
```

## Schema Usage Guide

### For New Imports
Use the **normalized schema** (`verses_normalized`) via:
```bash
python compendium.py import-bible data/kjv.xlsx KJV
```

### For Legacy Data Access
Query the **legacy schema** (`verses` + hierarchy) via:
```bash
python cli/study_bible_compendium.py search --query "faith" --version-code KJV
```

### For Greek Interlinear
Query the **Berean schema** (`berean_words`) via:
```bash
python cli/query_berean.py --strongs 3056  # G3056 = λόγος (logos)
```

## Migration Strategy

**Current state**: Both schemas coexist peacefully.

**Future options**:
1. **Keep both**: Legacy for compatibility, normalized for new features
2. **Migrate legacy → normalized**: Requires mapping old verse IDs to normalized refs
3. **Deprecate legacy**: After all tools updated to use normalized schema

**Recommendation**: Keep both for now. The 317K verses in legacy tables are stable and don't need migration unless specific features require unified schema.

## Table Inventory

### Complete table list in `compendium.sqlite`:
- `verses_normalized` - **NEW** unified verse storage (empty)
- `verses` - Legacy verse text (317,529 rows)
- `chapters` - Legacy chapter metadata
- `books` - Legacy book metadata  
- `bible_versions` - Legacy translation metadata
- `verse_strongs` - Strong's number mappings (legacy)
- `strongs_lexicon` - Hebrew/Greek lexicon entries (legacy)
- `interlinear_tokens` - Word-level original language tokens (legacy)
- `berean_verses` - Berean Bible 4 translations (7,957 NT verses)
- `berean_words` - Greek interlinear tokens (138,993 words)
- `berean_strongs` - Strong's definitions for Berean (5,349 entries)
- `hermeneutical_policy` - Immutable hermeneutical rules (1 row, trigger-locked)
- `policy` - Alternative policy storage
- `crossrefs` - Cross-reference links
- `midrash_sources` - Study note sources
- `midrash_notes` - Study notes content
- `user_notes` - User annotations

## Schema Versioning

**Legacy schema**: No version tracking, created incrementally by imports  
**Normalized schema**: Version 1.0, defined in `schema/verse_schema.sql`  
**Berean schema**: No version tracking, stable after import

---

**Last updated**: Phase Verse Schema deployment (2025)
