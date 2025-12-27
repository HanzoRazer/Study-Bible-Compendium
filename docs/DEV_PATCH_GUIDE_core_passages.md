# Core Passages System - Developer Patch Guide

## Problem Summary

Two competing annotation systems with schema mismatches:

1. **Python Module** (`sbc/core_passages.py`): Hardcoded dataclasses, expects `verses.ref`
2. **JSON System** (`cli/import_annotations.py`): Editable JSON files, expects `berean_verses.verse_ref`

## Recommended Solution

**Unify both approaches** by making `core_passages.py` consume JSON files while keeping validation logic.

---

## Patch Implementation

### Option A: Quick Fix (5 minutes)

**Update `sbc/core_passages.py` to use `berean_verses`:**

Replace line ~79-80:
```python
# OLD
if not conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='verses';"
).fetchone():
    raise RuntimeError("Missing required table: verses")
```

With:
```python
# NEW
table_name = "berean_verses"  # or "verses_normalized" for new schema
if not conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
    (table_name,)
).fetchone():
    raise RuntimeError(f"Missing required table: {table_name}")
```

Update line ~90:
```python
# OLD
if not table_has_column(conn, "verses", "ref"):
    raise RuntimeError("verses table must contain a 'ref' column...")

# NEW
ref_col = "verse_ref" if table_name == "berean_verses" else "ref"
if not table_has_column(conn, table_name, ref_col):
    raise RuntimeError(f"{table_name} table must contain a '{ref_col}' column...")
```

Update `get_verse_ids_by_ref()` at line ~95:
```python
# OLD
rows = conn.execute(
    f"SELECT id, ref FROM verses WHERE ref IN ({placeholders})",
    refs,
).fetchall()

# NEW
ref_col = "verse_ref"  # for berean_verses
rows = conn.execute(
    f"SELECT id, {ref_col} FROM berean_verses WHERE {ref_col} IN ({placeholders})",
    refs,
).fetchall()
```

**Also handle both formats** (`Romans 8:26` and `Romans|8:26`):
```python
# Expand refs to include both formats
expanded_refs = []
for r in refs:
    expanded_refs.append(r)
    expanded_refs.append(r.replace(" ", "|"))
```

---

### Option B: Full Refactor (30 minutes)

**Apply the complete patch** from `docs/PATCH_core_passages_json_support.py`:

1. **Auto-detect verse table** (supports `berean_verses`, `verses_normalized`, `verses`)
2. **Add JSON loader** function: `load_unit_from_json_files()`
3. **New CLI command**: `add-from-json`
4. **Keep Python validation** but use JSON as data source

**Usage after patch:**
```bash
# Old way (hardcoded Python data)
python -m sbc.core_passages --db compendium.sqlite add-romans8-sanctification-core

# New way (JSON source, recommended)
python -m sbc.core_passages --db compendium.sqlite add-from-json \
  --greek-margins STUDIES/greek-margins/romans_8.json \
  --verse-notes STUDIES/verse-notes/romans_8.json \
  --core-passage STUDIES/core-passages/sanctification.json
```

---

### Option C: Deprecate Python Module (Simplest)

**Use `cli/import_annotations.py` exclusively:**

1. Delete or archive `sbc/core_passages.py`
2. Update workflows to use JSON import script
3. Add convenience wrapper if needed:

```bash
# Create simple install script
cat > cli/install_core_passage.sh << 'EOF'
#!/bin/bash
# Install complete core passage unit from STUDIES/ JSON files

UNIT=$1  # e.g., "romans_8"
CATEGORY=$2  # e.g., "sanctification"

python cli/import_annotations.py --type greek-margins --input STUDIES/greek-margins/${UNIT}.json --apply
python cli/import_annotations.py --type verse-notes --input STUDIES/verse-notes/${UNIT}.json --apply
python cli/import_annotations.py --type core-passages --input STUDIES/core-passages/${CATEGORY}.json --apply

echo "Installed core passage: ${UNIT}"
EOF

chmod +x cli/install_core_passage.sh

# Usage:
./cli/install_core_passage.sh romans_8 sanctification
```

---

## Recommendation

**Go with Option B** (Full Refactor):

✅ **Benefits:**
- Best of both worlds: Python validation + JSON maintainability
- Auto-detects verse table (works with any schema)
- Scholars can edit JSON, devs get type safety
- Backward compatible (keeps hardcoded option)

**Implementation:**
1. Apply patch from `docs/PATCH_core_passages_json_support.py`
2. Test with Romans 8 JSON files (already created)
3. Deprecate hardcoded `add-romans8-sanctification-core` in docs
4. Document JSON workflow as primary method

---

## Migration Path

**Immediate (today):**
- Apply Option A quick fix to unblock current work
- Use `cli/import_annotations.py` for Romans 8 data

**Short-term (this week):**
- Apply Option B full refactor
- Update `.github/copilot-instructions.md` to document JSON workflow
- Create `cli/install_core_passage.sh` wrapper

**Long-term (next month):**
- Remove hardcoded `romans8_sanctification_core_unit()` function
- Move all passage data to `STUDIES/` JSON files
- Keep `sbc/core_passages.py` as validation/installation engine only

---

## Testing After Patch

```bash
# 1. Test schema creation
python -m sbc.core_passages --db test.db init-schema

# 2. Test JSON loading (after Option B patch)
python -m sbc.core_passages --db test.db add-from-json \
  --greek-margins STUDIES/greek-margins/romans_8.json \
  --verse-notes STUDIES/verse-notes/romans_8.json \
  --core-passage STUDIES/core-passages/sanctification.json

# 3. Verify data
sqlite3 test.db "SELECT COUNT(*) FROM verse_notes WHERE unit_id='SANCT_CORE_ROM_008_018_030';"
# Expected: 15

sqlite3 test.db "SELECT COUNT(*) FROM greek_margins WHERE unit_id='SANCT_CORE_ROM_008_018_030';"
# Expected: 20

sqlite3 test.db "SELECT title FROM core_passages WHERE unit_id='SANCT_CORE_ROM_008_018_030';"
# Expected: Romans 8:18–30 — Sanctification Through Groaning, Help, and Conformity
```

---

## Files to Update

- [x] `docs/PATCH_core_passages_json_support.py` - Patch code (created)
- [ ] `sbc/core_passages.py` - Apply patch
- [ ] `.github/copilot-instructions.md` - Document JSON workflow
- [ ] `STUDIES/README.md` - Add `add-from-json` usage example
- [ ] `cli/install_core_passage.sh` - Create convenience wrapper (optional)

---

**Decision needed:** Which option do you want to implement?
