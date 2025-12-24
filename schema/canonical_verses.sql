-- schema/canonical_verses.sql
--
-- Canonical verse spine: one row per verse of Scripture,
-- shared across all translations.

CREATE TABLE IF NOT EXISTS canonical_verses (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    book_num       INTEGER NOT NULL,
    book_code      TEXT    NOT NULL,
    chapter        INTEGER NOT NULL,
    verse          INTEGER NOT NULL,
    normalized_ref TEXT    NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_canonical_verses_book_ch_verse
    ON canonical_verses (book_num, chapter, verse);
