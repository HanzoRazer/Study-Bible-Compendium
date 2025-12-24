-- schema/translations.sql
--
-- Registry of Bible translations that exist in the database.

CREATE TABLE IF NOT EXISTS translations (
    code         TEXT PRIMARY KEY,  -- e.g. 'KJV', 'BSB'
    name         TEXT NOT NULL,     -- e.g. 'King James Version'
    language     TEXT NOT NULL,     -- e.g. 'en'
    source_notes TEXT NOT NULL,     -- free-form: Excel source, PDF, etc.
    imported_utc TEXT NOT NULL      -- ISO8601 timestamp of last import
);

CREATE INDEX IF NOT EXISTS idx_translations_language
    ON translations(language);
