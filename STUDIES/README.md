# Studies

All studies in this folder follow the canonical hermeneutical policy in `/CANON/`.

## Directory Structure

### `greek-margins/`
Word/phrase-level Greek parsing annotations. Links to `greek_margins` table via `unit_id`.

**Format**: JSON files with lemma, transliteration, morphology, gloss, and theological notes.

### `verse-notes/`
Verse-level midrash commentary, doctrinal tags, and study notes. Links to `verse_notes` table.

**Format**: JSON files with markdown content, tags, and unit grouping.

### `core-passages/`
High-value passage registry for navigation and categorization. Links to `core_passages` table.

**Format**: JSON files with category, title, summary, and tags.

### `word-studies/`
Lexical studies on specific Hebrew/Greek terms across Scripture.

### `typology/`
Type/antitype patterns across Scripture.

## JSON Annotation Workflow

1. **Create JSON** in appropriate subdirectory (e.g., `greek-margins/romans_8.json`)
2. **Validate & Generate SQL**:
   ```bash
   python cli/import_annotations.py --type greek-margins --input STUDIES/greek-margins/romans_8.json
   ```
3. **Review SQL output** in `data/` directory
4. **Apply to database**:
   ```bash
   python cli/import_annotations.py --type greek-margins --input STUDIES/greek-margins/romans_8.json --apply
   ```

## JSON Schemas

### Greek Margins (`greek-margins/*.json`)
```json
{
  "unit_id": "SANCT_CORE_ROM_008_018_030",
  "passage": "Romans 8:18-30",
  "testament": "NT",
  "annotations": [
    {
      "verse_ref": "Romans 8:26",
      "sort_order": 10,
      "lemma_greek": "Ὡσαύτως δὲ καὶ",
      "translit": "hōsautōs de kai",
      "morph": "Adv + Conj + Conj",
      "gloss": "likewise / now / also",
      "note_md": "Markdown explanation..."
    }
  ]
}
```

### Core Passages (`core-passages/*.json`)
```json
{
  "passages": [
    {
      "unit_id": "SANCT_CORE_ROM_008_018_030",
      "category": "sanctification",
      "title": "Romans 8:18–30 — Title",
      "range_ref": "Romans 8:18–30",
      "summary_md": "Summary...",
      "tags": "tag1,tag2,tag3"
    }
  ]
}
```

### Verse Notes (`verse-notes/*.json`)
```json
{
  "unit_id": "SANCT_CORE_ROM_008_018_030",
  "passage": "Romans 8:18-30",
  "notes": [
    {
      "verse_ref": "Romans 8:26",
      "note_kind": "midrash",
      "title": "Optional title",
      "note_md": "Markdown content...",
      "tags": "tag1,tag2",
      "sort_order": 10
    }
  ]
}
```

## Recommended study template

- **Passage / Topic**
- **Thesis**
- **Original language notes** (Hebrew/LXX/NT Greek)
- **Cross references** (OT → NT)
- **Comparison & contrast**
- **Teaching points**
- **Application**

## Folder structure

- `word-studies/` — Lexical studies on specific Hebrew/Greek terms
- `typology/` — Type/antitype patterns across Scripture
