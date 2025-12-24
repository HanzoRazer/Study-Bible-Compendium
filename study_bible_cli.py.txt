#!/usr/bin/env python3
"""
study_bible_cli.py

Main CLI for the Study Bible Compendium.
"""

import argparse
import sys
from pathlib import Path

from init_policy import run_init_policy  # <-- import the function we just exposed


DEFAULT_DB_PATH = "study_bible_compendium.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Study Bible Compendium CLI"
    )

    parser.add_argument(
        "--db",
        "--database",
        dest="db_path",
        default=DEFAULT_DB_PATH,
        help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH})",
    )

    # === New: --init-policy subcommand-style flag ===
    parser.add_argument(
        "--init-policy",
        dest="init_policy",
        action="store_true",
        help="Initialize and lock the Hermeneutical Rule Policy in the database, then exit.",
    )

    # You can also add other subcommands or flags here
    # e.g. parser.add_argument("--generate-report", ...)

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    db_path = args.db_path

    # Handle the policy initialization "subcommand"
    if args.init_policy:
        # Ensure the folder exists if you are pointing at a nested path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        run_init_policy(db_path)
        # Exit after initialization so this behaves like a dedicated subcommand
        sys.exit(0)

    # --- Normal CLI flow continues here ---
    # e.g.
    # if args.generate_report:
    #     ...
    # else:
    #     parser.print_help()
    #     sys.exit(1)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
