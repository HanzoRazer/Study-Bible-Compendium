"""
PDF generation scaffolding.

Currently this module writes plain-text files with `.txt` extension
as a stand-in for real PDF generation. Once a PDF library is chosen
(e.g., ReportLab), the functions here can be upgraded without changing
the surrounding code.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Optional, Dict

from .util import info

# Keep this type in sync with sbc.search.VerseRow / sbc.context.VerseRow
VerseRow = Tuple[str, int, str, int, int, str]

# ParallelRow: book_code, chapter, verse, { code: text }
ParallelRow = Tuple[str, int, int, Dict[str, str]]


def generate_basic_report(output_path: Path, title: str, body: str) -> None:
    """
    Placeholder function for generating a minimal report.

    CURRENT STATUS:
    ---------------
    Writes a plain-text file with `.txt` extension.
    """
    output_path = output_path.with_suffix(".txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    info(f"Writing BASIC REPORT (stub) to: {output_path}")
    content = f"{title}\n{'=' * len(title)}\n\n{body}\n"
    output_path.write_text(content, encoding="utf-8")


def _format_verse_rows(rows: List[VerseRow]) -> str:
    """
    Format a list of verses into a human-readable block of text.

    Each line looks like:
        BookCode 3:16  {text}
    """
    lines: List[str] = []
    for code, book_num, book_code, chapter, verse, text in rows:
        # We don't have book names here (only book_code), which is fine for now.
        lines.append(f"{book_code} {chapter}:{verse}  {text}")
    return "\n".join(lines)


def generate_passage_report(
    output_path: Path,
    ref: str,
    translation_code: str,
    passage_rows: List[VerseRow],
    context_rows: Optional[List[VerseRow]],
    policy_version: Optional[str],
    policy_checksum: Optional[str],
) -> None:
    """
    Generate a passage-focused report with optional context and
    hermeneutical policy information in the header.

    CURRENT STATUS:
    ---------------
    Writes a `.txt` file as a stand-in for a real PDF.

    Parameters
    ----------
    output_path:
        Base path for the output file (will be forced to `.txt`).
    ref:
        Reference string used for the passage (e.g. 'John 3:16-18').
    translation_code:
        Translation code (e.g. 'KJV').
    passage_rows:
        Verses that belong directly to the requested passage range.
    context_rows:
        Optional verses providing context around the passage.
    policy_version:
        Version string from the hermeneutical policy (or None if missing).
    policy_checksum:
        Full checksum from the hermeneutical policy (or None if missing).
    """
    translation_code = translation_code.upper()
    output_path = output_path.with_suffix(".txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Header ---
    title = f"Passage Report – {ref} ({translation_code})"

    header_lines: List[str] = []
    header_lines.append(title)
    header_lines.append("=" * len(title))
    header_lines.append("")
    header_lines.append(f"Reference : {ref}")
    header_lines.append(f"Translation: {translation_code}")

    if policy_version and policy_checksum:
        header_lines.append(
            f"Hermeneutical Policy: v{policy_version} "
            f"(checksum {policy_checksum[:12]}...)"
        )
    else:
        header_lines.append("Hermeneutical Policy: NOT INITIALIZED")

    header_lines.append("")

    # --- Passage section ---
    body_lines: List[str] = []
    body_lines.append("[Passage]")
    if passage_rows:
        body_lines.append(_format_verse_rows(passage_rows))
    else:
        body_lines.append("(No verses found for this passage.)")

    # --- Optional context section ---
    if context_rows is not None:
        body_lines.append("")
        body_lines.append("[Context Window]")
        if context_rows:
            body_lines.append(_format_verse_rows(context_rows))
        else:
            body_lines.append("(No context verses found.)")

    content = "\n".join(header_lines + [""] + body_lines) + "\n"

    info(f"Writing PASSAGE REPORT (stub) to: {output_path}")
    output_path.write_text(content, encoding="utf-8")


def generate_parallel_report(
    output_path: Path,
    ref: str,
    translation_codes: List[str],
    rows: List[ParallelRow],
    policy_version: Optional[str],
    policy_checksum: Optional[str],
) -> None:
    """
    Generate a parallel translation report for a reference.

    CURRENT STATUS:
    ---------------
    Writes a `.txt` file; easy to upgrade to real PDF later.
    """
    translation_codes = [c.upper() for c in translation_codes]
    output_path = output_path.with_suffix(".txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    title = f"Parallel Translation Report – {ref}"

    header_lines: List[str] = []
    header_lines.append(title)
    header_lines.append("=" * len(title))
    header_lines.append("")
    header_lines.append(f"Reference : {ref}")
    header_lines.append("Translations: " + ", ".join(translation_codes))

    if policy_version and policy_checksum:
        header_lines.append(
            f"Hermeneutical Policy: v{policy_version} "
            f"(checksum {policy_checksum[:12]}...)"
        )
    else:
        header_lines.append("Hermeneutical Policy: NOT INITIALIZED")

    header_lines.append("")

    body_lines: List[str] = []

    for book_code, chapter, verse, texts in rows:
        body_lines.append(f"{book_code} {chapter}:{verse}")
        for code in translation_codes:
            text = texts.get(code, "(missing in this translation)")
            body_lines.append(f"  [{code}] {text}")
        body_lines.append("")

    content = "\n".join(header_lines + [""] + body_lines) + "\n"

    info(f"Writing PARALLEL REPORT (stub) to: {output_path}")
    output_path.write_text(content, encoding="utf-8")
