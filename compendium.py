#!/usr/bin/env python
"""
compendium.py – unified CLI for the Study Bible Compendium

Commands:

  python compendium.py init-policy
      Initialize and lock the hermeneutical policy in compendium.sqlite

  python compendium.py init-schema
      Create/ensure the core verse schema (verses table + indexes)

  python compendium.py import-bible path/to/file.xlsx KJV
      Stub loader: prints what it would import (with schema + canon ready)

  python compendium.py search "Barnabas" --limit 10
      Stub search: prints a placeholder summary

  python compendium.py pdf-report output_name "Title" --body "Body text..."
      Stub PDF: writes a .txt report as a proof-of-pipeline
"""

import argparse
import sys
import subprocess
from pathlib import Path

from sbc.paths import PROJECT_ROOT, DB_PATH, SCHEMA_DIR, ensure_basic_dirs
from sbc.util import info, warn
from sbc import config
from sbc.loader import import_bible_from_excel, list_loaded_translations, ensure_translations_schema
from sbc.search import search_verses, print_search_results, get_passage
from sbc.pdfgen import (
    generate_basic_report,
    generate_passage_report,
    generate_parallel_report,
)
from sbc.db import get_conn
from sbc.status import print_status, get_policy_status
from sbc.context import get_verse_window
from sbc.parallel import get_parallel_verses, print_parallel
from sbc.spine import build_spine


# ---------- Command handlers ----------


def cmd_init_policy(args: argparse.Namespace) -> None:
    """
    Run cli/init_policy.py as a subprocess.

    This lets that script keep its own argparse logic without conflicting
    with this top-level CLI.
    """
    script_path = PROJECT_ROOT / "cli" / "init_policy.py"
    if not script_path.exists():
        warn(f"init_policy.py not found at: {script_path}")
        return

    db_path = Path(args.db) if args.db else DB_PATH

    info(f"Running init_policy.py on DB: {db_path}")
    cmd = [sys.executable, str(script_path), "--db", str(db_path)]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        warn(f"init_policy.py exited with non-zero status: {e.returncode}")


def cmd_init_schema(args: argparse.Namespace) -> None:
    """
    Apply the verse schema SQL to the database (idempotent).
    """
    schema_path = SCHEMA_DIR / "verse_schema.sql"
    if not schema_path.exists():
        warn(f"verse_schema.sql not found at: {schema_path}")
        return

    sql = schema_path.read_text(encoding="utf-8")
    info(f"Applying verse schema from: {schema_path}")
    with get_conn() as conn:
        conn.executescript(sql)
        conn.commit()
    info("Verse schema initialized / verified.")


def cmd_import_bible(args: argparse.Namespace) -> None:
    """
    Wire through to sbc.loader.import_bible_from_excel with full options.
    """
    excel_path = Path(args.excel)
    translation_code = args.code.upper()
    overwrite = args.overwrite
    sheet_name = args.sheet
    dry_run = args.dry_run
    max_rows = args.max_rows

    import_bible_from_excel(
        excel_path,
        translation_code,
        overwrite=overwrite,
        sheet_name=sheet_name,
        dry_run=dry_run,
        max_rows=max_rows,
    )


def cmd_search(args: argparse.Namespace) -> None:
    """
    Wire through to sbc.search.search_verses, then pretty-print results.
    """
    query = args.query
    limit = args.limit
    translation = args.code
    rows = search_verses(query, limit=limit, translation_code=translation)
    print_search_results(rows)


def cmd_list_translations(args: argparse.Namespace) -> None:
    """
    List all translations loaded in verses_normalized table.
    """
    list_loaded_translations()


def cmd_passage(args: argparse.Namespace) -> None:
    """
    Extract a passage by reference.
    """
    ref = args.ref
    translation = args.code
    rows = get_passage(ref, translation)
    print_search_results(rows)


def cmd_context(args: argparse.Namespace) -> None:
    """
    Fetch a window of verses around a central reference.
    """
    ref = args.ref
    translation = args.code
    before = args.before
    after = args.after
    rows = get_verse_window(ref, translation, before=before, after=after)
    print_search_results(rows)


def cmd_pdf_report(args: argparse.Namespace) -> None:
    """
    Wire through to sbc.pdfgen.generate_basic_report (currently writes .txt).
    """
    output_path = Path(args.output)
    title = args.title

    if args.body_file:
        body_path = Path(args.body_file)
        if not body_path.exists():
            warn(f"Body file not found: {body_path}")
            return
        body = body_path.read_text(encoding="utf-8")
    elif args.body:
        body = args.body
    else:
        body = f"Placeholder report body for '{title}'."

    generate_basic_report(output_path, title, body)


def cmd_pdf_passage(args: argparse.Namespace) -> None:
    """
    Generate a passage-focused report tied to the hermeneutical policy.
    """
    ref = args.ref
    translation = args.code
    output_path = Path(args.output)
    include_context = args.include_context
    before = args.before
    after = args.after

    # Get passage verses
    passage_rows = get_passage(ref, translation)
    if not passage_rows:
        warn("No verses found for the requested passage; no report generated.")
        return

    # Get optional context window (around the first verse in the reference)
    context_rows = None
    if include_context:
        context_rows = get_verse_window(ref, translation, before=before, after=after)

    # Get policy info
    policy = get_policy_status()
    if policy is None:
        policy_version = None
        policy_checksum = None
    else:
        policy_version, policy_checksum = policy

    generate_passage_report(
        output_path=output_path,
        ref=ref,
        translation_code=translation,
        passage_rows=passage_rows,
        context_rows=context_rows,
        policy_version=policy_version,
        policy_checksum=policy_checksum,
    )


def cmd_init_translations(args: argparse.Namespace) -> None:
    """
    Ensure the translations table exists (idempotent).
    """
    ensure_translations_schema()
    info("Translations schema initialized / verified.")


def cmd_compare(args: argparse.Namespace) -> None:
    """
    Console-side parallel comparison of translations for a reference.
    """
    ref = args.ref
    codes = [c.upper() for c in args.codes]
    rows = get_parallel_verses(ref, codes)
    print_parallel(ref, codes, rows)


def cmd_pdf_parallel(args: argparse.Namespace) -> None:
    """
    Generate a parallel translation report tied to the hermeneutical policy.
    """
    ref = args.ref
    codes = [c.upper() for c in args.codes]
    output_path = Path(args.output)

    rows = get_parallel_verses(ref, codes)
    if not rows:
        warn("No parallel verses found; no report generated.")
        return

    policy = get_policy_status()
    if policy is None:
        policy_version = None
        policy_checksum = None
    else:
        policy_version, policy_checksum = policy

    generate_parallel_report(
        output_path=output_path,
        ref=ref,
        translation_codes=codes,
        rows=rows,
        policy_version=policy_version,
        policy_checksum=policy_checksum,
    )


def cmd_build_spine(args: argparse.Namespace) -> None:
    """
    Build the canonical verse spine and attach verse_id to verses.
    """
    build_spine()


def cmd_status(args: argparse.Namespace) -> None:
    """
    Print a quick system status report.
    """
    print_status()


# ---------- Parser setup ----------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compendium",
        description=f"{config.APP_NAME} CLI (v{config.__version__})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init-policy
    p_init = sub.add_parser(
        "init-policy",
        help="Initialize and lock the hermeneutical policy in the database",
    )
    p_init.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to SQLite DB (default: compendium.sqlite at project root)",
    )
    p_init.set_defaults(func=cmd_init_policy)

    # init-schema
    p_schema = sub.add_parser(
        "init-schema",
        help="Create/ensure the core verse schema (verses table + indexes)",
    )
    p_schema.set_defaults(func=cmd_init_schema)

    # init-translations
    p_tr = sub.add_parser(
        "init-translations",
        help="Create/ensure the translations registry table",
    )
    p_tr.set_defaults(func=cmd_init_translations)

    # import-bible
    p_import = sub.add_parser(
        "import-bible",
        help="Import a Bible from an Excel file into the `verses_normalized` table",
    )
    p_import.add_argument(
        "excel",
        type=str,
        help="Path to the Excel file to import",
    )
    p_import.add_argument(
        "code",
        type=str,
        help="Translation code (e.g., KJV, BSB, ASV)",
    )
    p_import.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete existing verses for this translation before import",
    )
    p_import.add_argument(
        "--sheet",
        type=str,
        default=None,
        help="Worksheet name (default: active sheet)",
    )
    p_import.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write to the DB; just parse and report",
    )
    p_import.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Maximum number of data rows to import (for testing)",
    )
    p_import.set_defaults(func=cmd_import_bible)

    # list-translations
    p_list = sub.add_parser(
        "list-translations",
        help="List all translations loaded in the database",
    )
    p_list.set_defaults(func=cmd_list_translations)

    # search
    p_search = sub.add_parser(
        "search",
        help="Search verses for a text phrase",
    )
    p_search.add_argument(
        "query",
        type=str,
        help="Search text",
    )
    p_search.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of verses to return (default: 20)",
    )
    p_search.add_argument(
        "--code",
        type=str,
        default=None,
        help="Optional translation code filter (e.g., KJV)",
    )
    p_search.set_defaults(func=cmd_search)

    # passage
    p_passage = sub.add_parser(
        "passage",
        help="Fetch a passage by reference (e.g. 'John 3:16-18')",
    )
    p_passage.add_argument(
        "ref",
        type=str,
        help="Reference string, e.g. 'John 3:16-18', 'Gen 1:1'",
    )
    p_passage.add_argument(
        "code",
        type=str,
        help="Translation code (e.g., KJV, BSB)",
    )
    p_passage.set_defaults(func=cmd_passage)

    # context
    p_context = sub.add_parser(
        "context",
        help="Fetch a window of verses around a reference (e.g. 'John 3:16')",
    )
    p_context.add_argument(
        "ref",
        type=str,
        help="Central reference, e.g. 'John 3:16'",
    )
    p_context.add_argument(
        "code",
        type=str,
        help="Translation code (e.g., KJV, BSB)",
    )
    p_context.add_argument(
        "--before",
        type=int,
        default=2,
        help="How many verses before the center to include (default: 2)",
    )
    p_context.add_argument(
        "--after",
        type=int,
        default=2,
        help="How many verses after the center to include (default: 2)",
    )
    p_context.set_defaults(func=cmd_context)

    # pdf-report
    p_pdf = sub.add_parser(
        "pdf-report",
        help="(scaffold) Generate a basic report (currently .txt) to test pipeline",
    )
    p_pdf.add_argument(
        "output",
        type=str,
        help="Output file name (extension will be changed to .txt for now)",
    )
    p_pdf.add_argument(
        "title",
        type=str,
        help="Report title",
    )
    p_pdf.add_argument(
        "--body",
        type=str,
        default=None,
        help="Inline body text for the report",
    )
    p_pdf.add_argument(
        "--body-file",
        type=str,
        default=None,
        help="Path to a text file whose contents become the report body",
    )
    p_pdf.set_defaults(func=cmd_pdf_report)

    # pdf-passage
    p_pdfp = sub.add_parser(
        "pdf-passage",
        help="Generate a passage report tied to the hermeneutical policy",
    )
    p_pdfp.add_argument(
        "ref",
        type=str,
        help="Reference string, e.g. 'John 3:16-18'",
    )
    p_pdfp.add_argument(
        "code",
        type=str,
        help="Translation code (e.g., KJV, BSB)",
    )
    p_pdfp.add_argument(
        "output",
        type=str,
        help="Base output file name (extension will become .txt for now)",
    )
    p_pdfp.add_argument(
        "--include-context",
        action="store_true",
        help="Include a context window around the first verse of the reference",
    )
    p_pdfp.add_argument(
        "--before",
        type=int,
        default=2,
        help="Context: verses before center (default: 2)",
    )
    p_pdfp.add_argument(
        "--after",
        type=int,
        default=2,
        help="Context: verses after center (default: 2)",
    )
    p_pdfp.set_defaults(func=cmd_pdf_passage)

    # compare
    p_cmp = sub.add_parser(
        "compare",
        help="Console-side parallel comparison across translations for a reference",
    )
    p_cmp.add_argument("ref", type=str, help="Reference string, e.g. 'John 3:16-18'")
    p_cmp.add_argument(
        "codes",
        nargs="+",
        type=str,
        help="One or more translation codes, e.g. KJV BSB ASV",
    )
    p_cmp.set_defaults(func=cmd_compare)

    # pdf-parallel
    p_pdfpl = sub.add_parser(
        "pdf-parallel",
        help="Generate a parallel translation report tied to the hermeneutical policy",
    )
    p_pdfpl.add_argument("ref", type=str, help="Reference string, e.g. 'John 3:16-18'")
    p_pdfpl.add_argument(
        "codes",
        nargs="+",
        type=str,
        help="One or more translation codes, e.g. KJV BSB ASV",
    )
    p_pdfpl.add_argument(
        "output", type=str, help="Base output file name (extension becomes .txt for now)"
    )
    p_pdfpl.set_defaults(func=cmd_pdf_parallel)

    # build-spine
    p_spine = sub.add_parser(
        "build-spine",
        help="Build canonical verse spine and attach verse_id to verses",
    )
    p_spine.set_defaults(func=cmd_build_spine)

    # status
    p_status = sub.add_parser(
        "status",
        help="Show DB, policy, and translation status summary",
    )
    p_status.set_defaults(func=cmd_status)

    return parser


# ---------- Main ----------


def main() -> None:
    ensure_basic_dirs()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
