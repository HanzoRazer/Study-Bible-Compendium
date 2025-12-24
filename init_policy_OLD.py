#!/usr/bin/env python3
"""
init_policy.py

Initialize the Study Bible Compendium Hermeneutical Rule Policy
in a locked SQLite table so that it cannot be modified later.

This module can be used in two ways:
    1. As a library: import and call run_init_policy(db_path)
    2. As a standalone CLI: python init_policy.py --db <path>
"""

import argparse
import datetime as _dt
import hashlib
import sqlite3
import sys
from textwrap import dedent

# =========================
# 1. TEXT CONTENT
# =========================

PREFACE_TEXT = dedent("""
    📘 Doctrinal Preface
    Study Bible Compendium – Hermeneutical Foundation

    This Study Bible Compendium is built on the conviction that Holy Scripture is the inspired,
    sufficient, and authoritative Word of God, breathed out by the Spirit and preserved for the
    people of God in history. Because Scripture is God's Word, it interprets itself, governs all
    doctrine, and stands above every tradition, denomination, commentary, and human teacher.

    We affirm the unity of the Old and New Testaments and confess that the entire canon,
    from Genesis to Revelation, bears faithful witness to the person and work of the Messiah.
    The Law, the Prophets, the Writings, the Gospels, and the Apostolic writings form a single,
    coherent revelation in which Christ is the central figure and interpretive key—without
    cancelling the plain sense, historical setting, or linguistic reality of any passage.

    For this reason, our method refuses to bend the text to fit systems, trends, or personalities.
    Instead, it submits every interpretation to the original languages—Hebrew, the Septuagint
    Greek (LXX), and New Testament Greek—together with careful attention to context, grammar,
    typology, and inspired cross-references. Where hard choices must be made, the language of
    the text rules over tradition, opinion, or consensus.

    This Hermeneutical Rule Policy is therefore not an optional appendix, but the binding
    interpretive standard for all commentary, notes, word studies, and doctrinal conclusions
    within this Compendium. Every study, cross-reference, and theological conclusion is
    expected to conform to these rules, so that God's Word may be handled with reverence,
    accuracy, and integrity, and so that Christ may be seen clearly in the very words by
    which the Spirit chose to reveal Him.
""").strip()

POLICY_BODY = dedent("""
    📘 HERMENEUTICAL RULE POLICY
    Study Bible Compendium – Governing Interpretive Standard

    1. THE PRIME RULE OF INTERPRETATION

    "Follow the original language when you have issues.
    The language will bear out 90% of the interpretation in most cases."

    When a passage is unclear, debated, or misinterpreted, the authority is:

    • Hebrew (Old Testament)
    • Septuagint Greek (LXX)
    • New Testament Greek

    This policy rejects:
    • tradition as final authority
    • commentary as final authority
    • denominational doctrine as final authority
    • consensus interpretation as final authority
    • theological systems overriding the text

    The inspired text rules.
    Everything else is secondary.


    2. RULE OF TEXTUAL HONESTY

    "If the Septuagint says angels (angelos) and not sons of God… go with angels —
    regardless of what famous scholars say."

    This rule guards against:
    • traditional override of the text
    • theological pressure applied to words
    • academic bias shaping meaning
    • forced doctrinal models imposed on passages

    Summary:
    • Text over tradition
    • Language over scholars
    • Original meaning over reconstruction


    3. LINGUISTIC PRIORITY ORDER

    Interpretation must follow this hierarchy:

    1) Original Hebrew
       Use root forms, stems, idioms, parallel usages, and context.

    2) Septuagint Greek (LXX)
       Often preserves older Hebrew traditions, clarifies idioms, reveals ancient
       Jewish understanding, and aligns with New Testament apostolic usage.

    3) New Testament Greek
       Apostolic citation and interpretation of the Old Testament is final.

    4) Plain-Sense Meaning
       Interpret the text in its natural, plain sense, unless the context clearly
       demands metaphor, parable, typology, or symbolic usage.


    4. WHAT THIS POLICY REJECTS

    ❌ Bending Scripture to fit denominational tradition
    ❌ Speculative reconstructions not grounded in language or context
    ❌ Mystical reinterpretations detached from the text
    ❌ Theological systems overriding clear wording
    ❌ Forcing doctrines into words that do not carry them
    ❌ Consensus-driven meanings that contradict linguistic facts
    ❌ Proof-texting without context

    The text governs theology.
    Theology does not govern the text.


    5. REQUIRED METHODS OF EXEGESIS

    A. Seek Typology

       Interpret typology where the structure, pattern, or usage is explicit or implied
       within Scripture itself:

       • shadow → substance
       • type → antitype
       • Old Testament prophecy → New Testament fulfillment
       • narrative parallels that the Bible itself recognizes or echoes

       Typology is treated as God's architectural signature, not human imagination.


    B. Seek Direct OT ↔ NT Cross-References

       Scripture must interpret Scripture.

       • If Jesus cites it → His interpretation is final.
       • If Paul cites it → that apostolic explanation is authoritative.
       • If Hebrews expounds it → that interpretation is authoritative.
       • If the Gospels or Epistles apply an Old Testament text typologically →
         that application is binding for how we understand the passage.

       Required question: "Where is this used or echoed in the New Testament?"


    C. Comparison and Contrast

       Biblical truth is clarified by comparison and contrast:

       • covenants (old vs. new)
       • Adam vs. Christ
       • Joseph vs. Christ
       • law vs. grace
       • flesh vs. spirit
       • shadow vs. reality
       • earthly pattern vs. heavenly reality

       This is a core Hebrew teaching method and is central to this policy.


    D. Line-by-Line Exegesis

       Interpretation is performed:
       • word by word
       • phrase by phrase
       • clause by clause
       • in continuous context

       Never:
       • skip context to reach a desired doctrinal conclusion
       • impose a system onto a verse
       • build doctrine from isolated fragments
       • ignore grammar, syntax, or discourse flow

       A verse means what it means in its textual location, in its book,
       and within the whole canon.


    6. OPTIONAL TOOL: HEBREW PICTOGRAM FRAMEWORK

    Hebrew pictographs may be used to support:

    • lexical meaning
    • conceptual depth
    • natural imagery behind roots
    • teaching clarity
    • typological connections

    But:

    • Pictographs support meaning; they never override lexical definition.
    • Pictographs are a secondary teaching aid, not the primary determinant
      of doctrine.

    Order of priority:
    • Lexical meaning first.
    • Pictograph and visual associations second.


    7. SUMMARY STATEMENT

    This Hermeneutical Rule Policy establishes:

    • Text over tradition
    • Language over commentary
    • Old–New Testament unity over denominational division
    • Typology over speculation
    • Exegesis over imagination
    • Context over proof-texting
    • Hebrew thought-forms over abstract philosophical systems
    • Spirit-led insight anchored in linguistic and textual truth

    As a result, this policy ensures that:

    • Scripture interprets itself.
    • Theology flows from the inspired text.
    • Christ is revealed in both Testaments without distortion.
    • Believers are protected from false doctrine birthed from poor exegesis.
    • Teaching remains mature, accurate, and Spirit-filled.

    This policy is binding for all commentary, notes, word studies, cross-references,
    and doctrinal conclusions within the Study Bible Compendium.
""").strip()

POLICY_TITLE = "Study Bible Compendium – Hermeneutical Rule Policy"
POLICY_VERSION = "1.0.0"


# =========================
# 2. DB SCHEMA + TRIGGERS
# =========================

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hermeneutical_policy (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    title           TEXT NOT NULL,
    preface         TEXT NOT NULL,
    body            TEXT NOT NULL,
    version         TEXT NOT NULL,
    effective_utc   TEXT NOT NULL,
    checksum        TEXT NOT NULL
);
"""

TRIGGERS_SQL = [
    """
    CREATE TRIGGER IF NOT EXISTS hermeneutical_policy_no_extra_inserts
    BEFORE INSERT ON hermeneutical_policy
    WHEN (SELECT COUNT(*) FROM hermeneutical_policy) >= 1
    BEGIN
        SELECT RAISE(ABORT, 'hermeneutical_policy is locked; no further inserts allowed');
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS hermeneutical_policy_no_updates
    BEFORE UPDATE ON hermeneutical_policy
    BEGIN
        SELECT RAISE(ABORT, 'hermeneutical_policy is locked; updates are not allowed');
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS hermeneutical_policy_no_deletes
    BEFORE DELETE ON hermeneutical_policy
    BEGIN
        SELECT RAISE(ABORT, 'hermeneutical_policy is locked; deletes are not allowed');
    END;
    """
]


# =========================
# 3. HELPER FUNCTIONS
# =========================

def compute_checksum(preface: str, body: str) -> str:
    """
    Compute a SHA-256 checksum from the concatenation of preface + body.
    """
    combined = (preface + "\n\n" + body).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Create the hermeneutical_policy table and its locking triggers if they do not exist.
    """
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    for trig_sql in TRIGGERS_SQL:
        cur.execute(trig_sql)
    conn.commit()


def policy_exists(conn: sqlite3.Connection) -> bool:
    """
    Return True if a policy row already exists, False otherwise.
    """
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM hermeneutical_policy;")
    (count,) = cur.fetchone()
    return count >= 1


def insert_policy(conn: sqlite3.Connection) -> None:
    """
    Insert the hermeneutical policy if it does not already exist.
    Respects the locking triggers; will not modify an existing row.
    """
    if policy_exists(conn):
        print("[info] hermeneutical_policy row already present; no changes made (locked).")
        return

    checksum = compute_checksum(PREFACE_TEXT, POLICY_BODY)
    effective_utc = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO hermeneutical_policy (
                id,
                title,
                preface,
                body,
                version,
                effective_utc,
                checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                1,
                POLICY_TITLE,
                PREFACE_TEXT,
                POLICY_BODY,
                POLICY_VERSION,
                effective_utc,
                checksum,
            ),
        )
        conn.commit()
        print("[ok] hermeneutical_policy initialized and locked.")
        print(f"[ok] version: {POLICY_VERSION}")
        print(f"[ok] effective_utc: {effective_utc}")
        print(f"[ok] checksum: {checksum}")
    except sqlite3.IntegrityError as e:
        msg = str(e)
        print(f"[warn] IntegrityError while inserting policy: {msg}")
        print("[warn] Policy may already be locked or constrained. No changes were made.")
    except sqlite3.Error as e:
        print(f"[error] SQLite error while inserting policy: {e}")
        sys.exit(1)


# =========================
# 4. PUBLIC API
# =========================

def run_init_policy(db_path: str) -> None:
    """
    Public entry point to be used by the Study Bible Compendium CLI.

    Opens the database, ensures schema/triggers, and inserts the policy
    if not already present.

    Args:
        db_path: Path to the SQLite database file
    """
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        print(f"[error] Failed to open database '{db_path}': {e}")
        sys.exit(1)

    try:
        ensure_schema(conn)
        insert_policy(conn)
    finally:
        conn.close()


def main(argv=None) -> None:
    """
    Standalone CLI entrypoint for when this module is run directly:
        python init_policy.py --db study_bible_compendium.db
    """
    parser = argparse.ArgumentParser(
        description="Initialize the Study Bible Compendium Hermeneutical Rule Policy in a locked SQLite table."
    )
    parser.add_argument(
        "--db",
        "--database",
        dest="db_path",
        default="study_bible_compendium.db",
        help="Path to the SQLite database file (default: study_bible_compendium.db)",
    )
    args = parser.parse_args(argv)
    run_init_policy(args.db_path)


if __name__ == "__main__":
    main()
