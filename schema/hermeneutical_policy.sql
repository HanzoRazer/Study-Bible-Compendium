-- schema/hermeneutical_policy.sql
-- Immutable hermeneutical policy table with locking triggers

CREATE TABLE IF NOT EXISTS hermeneutical_policy (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    title           TEXT NOT NULL,
    preface         TEXT NOT NULL,
    body            TEXT NOT NULL,
    version         TEXT NOT NULL,
    effective_utc   TEXT NOT NULL,
    checksum        TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS hermeneutical_policy_no_extra_inserts
BEFORE INSERT ON hermeneutical_policy
WHEN (SELECT COUNT(*) FROM hermeneutical_policy) >= 1
BEGIN
    SELECT RAISE(ABORT, 'hermeneutical_policy is locked; no further inserts allowed');
END;

CREATE TRIGGER IF NOT EXISTS hermeneutical_policy_no_updates
BEFORE UPDATE ON hermeneutical_policy
BEGIN
    SELECT RAISE(ABORT, 'hermeneutical_policy is locked; updates are not allowed');
END;

CREATE TRIGGER IF NOT EXISTS hermeneutical_policy_no_deletes
BEFORE DELETE ON hermeneutical_policy
BEGIN
    SELECT RAISE(ABORT, 'hermeneutical_policy is locked; deletes are not allowed');
END;
