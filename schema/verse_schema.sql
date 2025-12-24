-- schema/verse_schema.sql
--
-- Core verse table for all translations.
-- Every Bible you import will land here.

CREATE TABLE IF NOT EXISTS verses_normalized (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_code TEXT    NOT NULL,  -- e.g. 'KJV', 'BSB'
    book_num         INTEGER NOT NULL,  -- 1–66 (Protestant canon)
    book_code        TEXT    NOT NULL,  -- e.g. 'GEN', 'EXO'
    chapter          INTEGER NOT NULL,
    verse            INTEGER NOT NULL,
    normalized_ref   TEXT    NOT NULL,  -- e.g. 'GEN.1.1'
    text             TEXT    NOT NULL,
    word_count       INTEGER NOT NULL DEFAULT 0,
    verse_id         INTEGER,           -- canonical_verses.id (filled by spine builder)
    created_utc      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    CONSTRAINT verses_unique_per_translation
        UNIQUE (translation_code, book_num, chapter, verse)
);

-- Indexes for lookup and search

-- Fast lookup by normalized reference
CREATE INDEX IF NOT EXISTS idx_verses_normref
    ON verses_normalized(normalized_ref);

-- Combined translation + reference lookup
CREATE INDEX IF NOT EXISTS idx_verses_translation_ref
    ON verses_normalized(translation_code, book_num, chapter, verse);

-- Basic text search index (for LIKE-based search)
CREATE INDEX IF NOT EXISTS idx_verses_text
    ON verses_normalized(text);

-- Spine linkage index
CREATE INDEX IF NOT EXISTS idx_verses_normalized_verse_id
    ON verses_normalized(verse_id);
