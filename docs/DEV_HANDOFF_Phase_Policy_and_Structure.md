# Developer Handoff – Study Bible Compendium
## Phase: Policy Insert & Repo Restructure (2025-11-29)

### 1. Overview

This phase establishes the **structural foundation** of the Study Bible Compendium project:

1. Introduce a clean, predictable folder layout.
2. Lock in the **Hermeneutical Rule Policy** as an immutable record in the SQLite database.
3. Prepare the codebase for the upcoming **Unified Loader** (Excel → SQLite) and Strong's / cross-reference importers.

No Bible content schemas are finalized in this step. The focus is on **doctrinal integrity** and **project hygiene**.

---

### 2. Goals of This Phase

- Enforce a **single authoritative hermeneutical policy** at the database level.
- Ensure the policy cannot be changed silently (triggers prevent update/delete/additional inserts).
- Organize existing scripts and data files into a structure that will scale to:
  - 30+ Bible translations
  - Interlinear / Strong's data
  - PDF report generation
  - CLI-based search and study tools

---

### 3. Target Folder Layout

Project root (simplified):

```text
Study_Bible_Compendium/
├─ compendium.sqlite
├─ cli/
│  ├─ init_policy.py
│  ├─ import_berean.py
│  ├─ query_berean.py
│  ├─ xref_berean.py
│  ├─ study_bible_compendium.py
│  └─ study_bible_cli.py
├─ schema/
│  └─ hermeneutical_policy.sql
├─ data/
│  ├─ policy_preface.txt
│  ├─ policy_body.txt
│  ├─ Strongs_Concordance.xlsx
│  ├─ strongs_sample.xlsx
│  ├─ kjv_sample.xlsx
│  └─ Study_Bible_Compendium_Hermeneutical_Rule_Policy.txt
├─ sources/
│  ├─ pdf/
│  └─ excel/
│     ├─ excel_output/
│     ├─ Study Bibles/
│     ├─ Bibles/
│     └─ Berean Bibles/
├─ tools/
│  ├─ convert_single_pdf_retry.py
│  ├─ batch_pdf_to_excel.py
│  ├─ word_to_excel.py
│  └─ poll_conversion_status.ps1
├─ docs/
│  ├─ DEV_HANDOFF_Phase_Policy_and_Structure.md (this file)
│  └─ What_is_a_SaaS_app.txt
├─ .github/
└─ workspace.code-workspace
```

---

### 4. Key Components

#### 4.1 schema/hermeneutical_policy.sql

Defines:
- `hermeneutical_policy` table (single-row, id = 1)
- Triggers:
  - `hermeneutical_policy_no_extra_inserts`
  - `hermeneutical_policy_no_updates`
  - `hermeneutical_policy_no_deletes`

Purpose: make the policy effectively immutable once set.

#### 4.2 data/policy_preface.txt and data/policy_body.txt

- `policy_preface.txt`: Doctrinal preface for the Study Bible Compendium
- `policy_body.txt`: Full Hermeneutical Rule Policy (prime rule, text-over-tradition, linguistic priority, typology, cross-reference rules, etc.)

These are human-editable source files; their contents are injected into the DB one time and checksum-verified.

#### 4.3 cli/init_policy.py

Responsibilities:
- Open `compendium.sqlite`
- Apply `schema/hermeneutical_policy.sql` (table + triggers)
- Read `data/policy_preface.txt` and `data/policy_body.txt`
- Compute a SHA-256 checksum of (preface + body) with a fixed separator
- Insert a single row into `hermeneutical_policy` with:
  - `id = 1`
  - `title = "Study Bible Compendium – Hermeneutical Rule Policy"`
  - `version` (default 1.0.0)
  - `effective_utc` (current UTC timestamp, ISO8601)
  - `checksum`
- If the table already contains a row, the script prints the existing version and exits without modification

This ensures reproducible behavior and prevents accidental overwrites.

---

### 5. How to Run This Phase

From the project root:

1. **Ensure folder structure matches Section 3**
2. **Confirm `compendium.sqlite` exists** (create a blank SQLite DB if needed)
3. **Run:**
   ```bash
   python cli\init_policy.py --db compendium.sqlite
   ```
4. **Verify:**
   ```sql
   SELECT id, title, version, effective_utc, checksum
   FROM hermeneutical_policy;
   ```
   Expected:
   - One row, `id = 1`
   - A non-empty checksum
   - Triggers present in `sqlite_master`

---

### 6. What Comes Next (for Future Devs)

#### 6.1 Unified Loader (Excel → SQLite)
- Create `cli/load_bible.py` to normalize all 30+ Bible Excel files into a shared schema
- Ensure all loaders run under the hermeneutical policy already locked in the DB

#### 6.2 Strong's & Cross-Reference Importers
- Build `cli/load_strongs.py` and `cli/load_crossrefs.py` using `data/Strongs_Concordance.xlsx` and existing Berean xref tools

#### 6.3 PDF Output Pipeline
- Implement PDF generators for:
  - Passage extraction
  - Interlinear views
  - Midrash of the Messiah study
  - Concordance slices

#### 6.4 CLI Unification
- Introduce a single top-level entrypoint (`compendium.py`) that routes commands:
  - `init-policy`
  - `import-bible`
  - `search`
  - `passage`
  - `midrash`
  - etc.

---

### 7. Risks & Notes

**Policy Mutability:**  
Changing the hermeneutical policy in future versions will require:
- New DB versioning strategy, or
- New DB file with a higher `policy.version`

For now, treat this policy as frozen for v1.

**Path Assumptions:**  
`init_policy.py` assumes relative paths from project root:
- `schema/hermeneutical_policy.sql`
- `data/policy_preface.txt`
- `data/policy_body.txt`

If the structure changes, update the default arguments accordingly.

---

### 8. Completed Migration Summary

**Status:** ✅ Complete (2025-11-29)

#### Directory Structure Created

#### Directory Structure Created

All project files successfully organized into clean folder hierarchy:
- ✅ `cli/` - All CLI scripts (6 files)
- ✅ `schema/` - SQL schema files (1 file)
- ✅ `data/` - Policy text & reference data (6 files)
- ✅ `sources/` - Original PDFs and Excel files
- ✅ `tools/` - Conversion utilities (4 files)
- ✅ `docs/` - Documentation (2 files)

#### Policy System Initialized

- ✅ Policy inserted with checksum: `38acc82a078be735a6ac27250b3e3e1dd1c85fe8a960c4079c471dd34eb2efd6`
- ✅ Version: `1.0.0`
- ✅ Effective UTC: `2025-11-29T22:33:56Z`
- ✅ Database triggers active and verified
- ✅ Subsequent runs correctly report policy is locked

#### Files Migrated

**Created:**
- `schema/hermeneutical_policy.sql` - Schema with locking triggers
- `cli/init_policy.py` - File-based policy loader (rewritten)
- `docs/DEV_HANDOFF_Phase_Policy_and_Structure.md` - This document

**Moved:**
- All CLI scripts → `cli/`
- Policy text files → `data/` (renamed: `preface.txt` → `policy_preface.txt`)
- Sample data → `data/`
- Conversion tools → `tools/`
- Source materials → `sources/pdf/` and `sources/excel/`
- Documentation → `docs/`

**Backed Up:**
- `init_policy_OLD.py` - Original implementation preserved

**Deleted:**
- None (all files preserved)

#### PDF Conversion Status

**Overall:** 35 of 38 files successfully converted (92% success rate)

**Failed Conversions (3 files - only headers, no content):**
1. `32518882-The-Septuagint-Bible-1879.xlsx` (76.12 MB PDF)
2. `381183384-The-Scofield-Reference-Bible-pdf.xlsx` (108.32 MB PDF)
3. `Thompson-Chain-Reference-Bible-1908-Edition.xlsx` (106.03 MB PDF)

**Successfully Converted (35 files):**
- All 12 Bible translations (akjv, asv, kjv, web, ylt, etc.)
- Most Study Bibles (Nelson's NKJV, Oxford Commentary, Dakes, etc.)
- Specialized resources (Greek Lexicon, Aramaic Bible, Exhaustive Concordance)
- Berean Bible files (bgb, bib, blb, bsb)
- THE MIDRASH OF THE MESSIAH ✅

**Note:** The 3 failed conversions were likely due to large file sizes (76-108 MB) causing memory issues during system crash. These can be retried with `--save-every 100` flag if needed.

---

### 9. Testing Performed

#### ✅ Policy Initialization
```bash
python cli\init_policy.py --db compendium.sqlite
# Result: SUCCESS - Policy initialized and locked
```

#### ✅ Idempotency Check
```bash
python cli\init_policy.py --db compendium.sqlite
# Result: SUCCESS - "hermeneutical_policy row already present; no changes made (locked)."
```

#### ✅ File Structure Validation
All files confirmed in correct locations:
- 6 CLI scripts in `cli/`
- 6 data files in `data/`
- 1 schema file in `schema/`
- 4 tool scripts in `tools/`
- 38 Excel outputs in `sources/excel/excel_output/`
- 30 PDFs in `sources/excel/Study Bibles/` and `sources/excel/Bibles/`

---

### 10. Breaking Changes & Migration Notes

#### For CLI Users

**Old:**
```bash
python init_policy.py --db study_bible_compendium.db
python study_bible_compendium.py search --query "faith"
```

**New:**
```bash
python cli\init_policy.py --db compendium.sqlite
python cli\study_bible_compendium.py search --query "faith"
```

All CLI scripts now in `cli/` directory. Update any automation scripts accordingly.

#### For Library Users

The public API remains compatible:

```python
from cli.init_policy import run_init_policy

# Still works
run_init_policy("compendium.sqlite")
```

---

### 11. Next Steps

#### Immediate (Ready to Use)
1. ✅ Policy system is operational
2. ✅ All CLI scripts accessible via `cli/` directory
3. ✅ Clean project structure ready for development
4. ✅ 35 Bible/Study resources converted and ready

#### Recommended Follow-ups
1. **Retry failed PDF conversions** (3 files) with memory-optimized settings
2. **Test other CLI scripts** from new locations:
   - `python cli\import_berean.py --db compendium.sqlite --berean-dir "sources\excel\Berean Bible"`
   - `python cli\query_berean.py --db compendium.sqlite --strongs 3056`
   - `python cli\xref_berean.py --db compendium.sqlite --verse "John 3:16"`
3. **Update AI instructions** in `.github/copilot-instructions.md` (already done)
4. **Consider creating** `compendium.py` unified entrypoint at project root

---

### 12. Rollback Procedure (If Needed)

If you need to revert to the old structure:

```powershell
# Restore old init_policy.py
Copy-Item init_policy_OLD.py init_policy.py

# Move files back to root
Move-Item cli\* .
Move-Item data\policy_preface.txt preface.txt
Move-Item data\policy_body.txt .
# ... etc
```

**Note:** Database changes (policy initialization) cannot be rolled back due to triggers. Delete `compendium.sqlite` and recreate if needed.

---

**End of Handoff – Phase: Policy Insert & Repo Restructure**

**Checksum for verification:**  
Policy content checksum: `38acc82a078be735a6ac27250b3e3e1dd1c85fe8a960c4079c471dd34eb2efd6`

**Migration completed successfully!** 🎉
