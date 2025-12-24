#!/usr/bin/env python3
"""
Batch import all converted CSV Bibles into compendium.sqlite.

This script imports multiple Bible translations by calling study_bible_compendium.py
import-bible-csv for each CSV file with appropriate version codes and names.

Usage:
    python cli/batch_import_bibles.py --db compendium.sqlite --csv-dir data/converted/
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Mapping of CSV filenames to (version_code, version_name, language)
BIBLE_VERSIONS = {
    "kjv.csv": ("KJV", "King James Version", "en"),
    "akjv.csv": ("AKJV", "Authorized King James Version", "en"),
    "asv.csv": ("ASV", "American Standard Version", "en"),
    "web.csv": ("WEB", "World English Bible", "en"),
    "ylt.csv": ("YLT", "Young's Literal Translation", "en"),
    "drb.csv": ("DRB", "Douay-Rheims Bible", "en"),
    "erv.csv": ("ERV", "English Revised Version", "en"),
    "dbt.csv": ("DBT", "Darby Translation", "en"),
    "wbt.csv": ("WBT", "Webster's Bible Translation", "en"),
    "slt.csv": ("SLT", "Smith's Literal Translation", "en"),
    "cpdv.csv": ("CPDV", "Catholic Public Domain Version", "en"),
    "jps.csv": ("JPS", "Jewish Publication Society OT", "en"),
    "bsb.csv": ("BSB", "Berean Study Bible", "en"),
    "blb.csv": ("BLB", "Berean Literal Bible", "en"),
    "bsb-book-9.5.csv": ("BSB-B", "Berean Study Bible (Book Format)", "en"),
    "504052744-The-Exhaustive-Concordance-of-the-Bible.csv": ("STRONGS", "Strong's Concordance", "en"),
    "exhaustiveconcor0000jame.csv": ("STRONGS2", "Strong's Concordance (alt)", "en"),
    "434906249-The-Chronological-Study-Bible-New-King-James-Version-PDFDrive-com.csv": ("NKJV-CHRONO", "Chronological Study Bible NKJV", "en"),
    "514304690-Nelson-s-NKJV-Study-Bible-Second-Edition-PDFDrive.csv": ("NKJV-NELSON", "Nelson's NKJV Study Bible", "en"),
}


def import_bible(
    db_path: Path,
    csv_path: Path,
    version_code: str,
    version_name: str,
    language: str,
    verbose: bool = False
) -> bool:
    """
    Import a single Bible CSV using study_bible_compendium.py.
    Returns True on success, False on failure.
    """
    cmd = [
        sys.executable,
        "cli/study_bible_compendium.py",
        "--db", str(db_path),
        "import-bible-csv",
        "--version-code", version_code,
        "--version-name", version_name,
        "--language", language,
        "--file", str(csv_path)
    ]
    
    if verbose:
        print(f"[info] Importing {version_code}: {csv_path.name}")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        if verbose:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[error] Failed to import {version_code}: {e.stderr}")
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Batch import all CSV Bible translations into database"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("compendium.sqlite"),
        help="Database path (default: compendium.sqlite)"
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path("data/converted"),
        help="Directory containing CSV files (default: data/converted/)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args(argv)
    
    if not args.csv_dir.exists():
        print(f"[error] Directory not found: {args.csv_dir}")
        sys.exit(1)
    
    success_count = 0
    fail_count = 0
    
    for csv_file, (code, name, lang) in BIBLE_VERSIONS.items():
        csv_path = args.csv_dir / csv_file
        
        if not csv_path.exists():
            if args.verbose:
                print(f"[warn] Skipping missing file: {csv_file}")
            continue
        
        if import_bible(args.db, csv_path, code, name, lang, args.verbose):
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n[ok] Import complete: {success_count} successful, {fail_count} failed")


if __name__ == "__main__":
    main()
