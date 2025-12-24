# Developer Handoff – Study Bible Compendium
## Phase: Core Verse Schema & Canon (2025-11-30)

### 1. Overview

This phase introduces the first *real* data structure for the Study Bible Compendium:

- The **`verses`** table (shared by all translations).
- A 66-book **canon definition** in `data/canon.json`.
- CLI command `init-schema` to apply the verse schema.
- Loader scaffolding that now knows:
  - How to ensure the schema exists.
  - How to find the canon definition.

No actual verse content is imported in this phase; the loader still behaves as a stub. The goal is to lay a stable foundation for the upcoming Excel → SQLite import work.

---

### 2. Files Introduced / Updated

#### 2.1 `schema/verse_schema.sql`

Defines the `verses` table with:

- `id` (PK, autoincrement)
- `translation_code` (e.g. `KJV`, `BSB`)
- `book_num` (1–66, Protestant canon)
- `book_code` (3-letter code, e.g. `GEN`)
- `chapter`, `verse`
- `normalized_ref` (`GEN.1.1`, etc.)
- `text`
- `word_count`
- `created_utc`

Also defines indexes:

- `idx_verses_normref`
- `idx_verses_translation_ref`
- `idx_verses_text`

#### 2.2 `data/canon.json`

Contains a 66-entry list of objects describing each book:

- `book_num` (1–66)
- `code` (3-letter code, canonical)
- `name` (full English name)
- `testament` (`OT` or `NT`)

This file will be used during import to:

- Resolve book names or codes from Excel.
- Generate `book_num` and `book_code`.
- Build `normalized_ref` strings.

#### 2.3 `sbc/model.py`

Introduces basic data models:

- `VerseRef(book_num, chapter, verse)` and `to_normalized(book_code)` helper.
- `Verse` representing a row in the `verses` table, with `from_db_row` constructor.

These classes are intentionally simple, to be used by loader, search, and PDF components.

#### 2.4 `sbc/loader.py`

Enhancements:

- `ensure_verse_schema()` – executes `schema/verse_schema.sql` against the DB.
- `load_canon()` – loads `data/canon.json` into a Python dict keyed by `book_num`.
- `import_bible_from_excel()` – still a stub, but now:
  - Ensures verse schema exists.
  - Loads canon.
  - Prints diagnostic info.

This prepares the way for the next phase where actual Excel parsing and INSERTs will be implemented.

#### 2.5 `compendium.py`

New command:

```bash
python compendium.py init-schema
```

Behavior:

- Reads `schema/verse_schema.sql`.
- Applies it to `compendium.sqlite` via `sbc.db.get_conn`.
- Prints confirmation.

Existing commands (`init-policy`, `import-bible`, `search`, `pdf-report`) are preserved.

---

### 3. How to Run This Phase

From the project root:

1. Ensure the folder structure and new files are in place.

2. Run the schema initializer:

```bash
python compendium.py init-schema
```

3. Verify the table exists:

```bash
sqlite3 compendium.sqlite
.schema verses
```

You should see the `verses` table and its indexes.

4. (Optional) Run the stub loader to see diagnostics:

```bash
python compendium.py import-bible sources/excel/kjv_sample.xlsx KJV
```

Expected behavior:

- Reports Excel path & translation code.
- Applies verse schema (idempotent).
- Loads canon and reports `Loaded canon for 66 books`.
- Prints that no rows were actually written yet.

---

### 4. Future Work (Next Phases)

#### Excel Parsing & Real Inserts

- Implement concrete import logic in `sbc.loader.import_bible_from_excel`.
- Map Excel columns → (book, chapter, verse, text).
- Use `canon.json` to determine `book_num` and `book_code`.
- Compute `normalized_ref` via `VerseRef`.
- Populate `word_count` from text.

#### Translation Registry

- Add a `translations` table to track:
  - Code (KJV, BSB, etc.)
  - Name
  - Language
  - Copyright / source notes

#### Search Implementation

- Implement real SELECT queries in `sbc.search.search_verses` against `verses.text`.
- Later, optionally migrate to FTS for more advanced search.

#### Cross-Reference & Strong's Glue

- Design tables that point back to `verses.id` or `(translation_code, book_num, chapter, verse)`.
- Import data from Strong's Excel and existing cross-ref materials.

#### PDF Extraction

- Have `pdfgen` pull verses from `verses` based on:
  - A list of `VerseRefs`
  - A passage range
  - Search results

---

### 5. Risks / Notes

- The verse schema is intentionally simple, but changes later (e.g., adding FTS tables) may require migrations.
- `canon.json` must remain consistent for all imports; if you change `book_num` or codes, be prepared to re-import Bibles.
- Current loader behavior is intentionally non-destructive (no inserts yet), so it is safe for testing.

---

**End of Handoff – Phase: Core Verse Schema & Canon**
