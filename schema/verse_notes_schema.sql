-- Study Bible Compendium: verse_notes, greek_margins, core_passages schema
-- Linked to berean_verses table for NT content
-- Created: 2024-12-24

PRAGMA foreign_keys=ON;

-- =============================================================================
-- VERSE NOTES: Midrash entries, doctrinal tags, unit grouping
-- =============================================================================
CREATE TABLE IF NOT EXISTS verse_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id INTEGER NOT NULL,                    -- FK to berean_verses.id
    note_kind TEXT NOT NULL DEFAULT 'midrash',    -- midrash, summary, doctrine, application
    unit_id TEXT,                                 -- e.g., SANCT_CORE_ROM_008_018_030
    title TEXT,                                   -- optional header for grouped notes
    note_md TEXT NOT NULL,                        -- markdown content
    tags TEXT,                                    -- comma-separated tags
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (verse_id) REFERENCES berean_verses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_verse_notes_verse_id ON verse_notes(verse_id);
CREATE INDEX IF NOT EXISTS idx_verse_notes_unit_id ON verse_notes(unit_id);
CREATE INDEX IF NOT EXISTS idx_verse_notes_kind ON verse_notes(note_kind);

-- =============================================================================
-- GREEK MARGINS: Word/phrase-level parsing entries
-- =============================================================================
CREATE TABLE IF NOT EXISTS greek_margins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id INTEGER NOT NULL,                    -- FK to berean_verses.id
    unit_id TEXT,                                 -- group with passage unit
    lemma_greek TEXT NOT NULL,                    -- e.g., logizomai or phrase
    translit TEXT,                                -- transliteration
    morph TEXT NOT NULL,                          -- morphological tag
    gloss TEXT,                                   -- short meaning
    note_md TEXT,                                 -- parsing note / theological force
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (verse_id) REFERENCES berean_verses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_greek_margins_verse_id ON greek_margins(verse_id);
CREATE INDEX IF NOT EXISTS idx_greek_margins_unit_id ON greek_margins(unit_id);

-- =============================================================================
-- CORE PASSAGES: High-value passage registry for navigation/search
-- =============================================================================
CREATE TABLE IF NOT EXISTS core_passages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id TEXT NOT NULL UNIQUE,                 -- SANCT_CORE_ROM_008_018_030
    category TEXT NOT NULL,                       -- sanctification, trinity, prayer, etc.
    title TEXT NOT NULL,
    range_ref TEXT NOT NULL,                      -- "Romans 8:18-30"
    summary_md TEXT NOT NULL,
    tags TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_core_passages_category ON core_passages(category);
