-- schema/notes.sql
--
-- General notes / midrash anchored to the canonical verse spine.

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id    INTEGER NOT NULL,       -- references canonical_verses.id
    note_type   TEXT    NOT NULL,       -- e.g. 'midrash', 'study', 'crossref'
    source      TEXT    NOT NULL,       -- e.g. 'Midrash of the Messiah'
    body        TEXT    NOT NULL,
    created_utc TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notes_verse_id
    ON notes (verse_id);

CREATE INDEX IF NOT EXISTS idx_notes_type_source
    ON notes (note_type, source);
