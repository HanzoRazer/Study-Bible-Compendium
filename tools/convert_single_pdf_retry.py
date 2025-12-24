#!/usr/bin/env python3
"""
Convert a single PDF with per-page error handling and fallbacks.

Usage:
  python convert_single_pdf_retry.py "C:\path\to\bib.pdf" "C:\path\to\output.xlsx"

Behavior:
- Tries page.extract_text(); on exception, retries with adjusted tolerances.
- If text extraction still fails, falls back to extracting words and joins them.
- Logs any pages that could not be extracted to a log file for manual inspection.
"""
import sys
from pathlib import Path
import time

try:
    import pdfplumber
    from openpyxl import Workbook
except ImportError:
    print("[error] Required packages not installed. Run: pip install pdfplumber openpyxl")
    sys.exit(1)


def extract_text_with_fallback(page):
    """Attempt multiple extraction strategies for a pdfplumber page.
    Returns text (string) or None if nothing could be extracted.
    """
    # 1) Default
    try:
        text = page.extract_text()
        if text:
            return text
    except Exception:
        pass

    # 2) Tolerance tweaks
    try:
        text = page.extract_text(x_tolerance=1.0, y_tolerance=1.0)
        if text:
            return text
    except Exception:
        pass

    # 3) Use higher tolerance
    try:
        text = page.extract_text(x_tolerance=2.0, y_tolerance=2.0)
        if text:
            return text
    except Exception:
        pass

    # 4) Fallback to words
    try:
        words = page.extract_words()
        if words:
            # Sort by top/left then join
            words_sorted = sorted(words, key=lambda w: (float(w.get('top', 0)), float(w.get('x0', 0))))
            joined = ' '.join(w.get('text', '') for w in words_sorted)
            if joined.strip():
                return joined
    except Exception:
        pass

    return None


def convert(pdf_path: Path, excel_path: Path, batch_size: int = 50, save_every: int = 500):
    start = time.time()
    log_file = excel_path.with_suffix('.retry.log')
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        wb = Workbook()
        ws = wb.active
        ws.title = 'Text Content'
        ws.append(['Page', 'Line', 'Text'])
        row_count = 0
        failed_pages = []

        for page_num, page in enumerate(pdf.pages, start=1):
            try:
                text = extract_text_with_fallback(page)
                if text:
                    lines = text.split('\n')
                    for line_num, line in enumerate(lines, start=1):
                        line = line.strip()
                        if line:
                            ws.append([page_num, line_num, line])
                            row_count += 1
                else:
                    failed_pages.append(page_num)

            except KeyboardInterrupt:
                print('[warn] Interrupted by user')
                break
            except Exception as e:
                print(f"[warn] Unexpected exception on page {page_num}: {e}")
                failed_pages.append(page_num)

            if page_num % batch_size == 0:
                progress = (page_num / total_pages) * 100
                print(f"[info] Progress: Page {page_num}/{total_pages} ({progress:.1f}%) - {row_count:,} lines")

            if page_num % save_every == 0:
                print(f"[info] Auto-saving at page {page_num}...")
                wb.save(excel_path)

        # Final save
        print('[info] Saving final file...')
        wb.save(excel_path)

        elapsed = time.time() - start
        print(f"[ok] Saved: {excel_path.name} ({row_count:,} lines) in {elapsed:.1f}s")

        if failed_pages:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('Failed pages (could not extract text):\n')
                for p in failed_pages:
                    f.write(f"{p}\n")
            print(f"[warn] {len(failed_pages)} pages failed; list written to {log_file}")
        else:
            # Remove log file if exists
            if log_file.exists():
                try:
                    log_file.unlink()
                except Exception:
                    pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python convert_single_pdf_retry.py <input.pdf> [output.xlsx]')
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        excel_path = Path(sys.argv[2])
    else:
        excel_path = pdf_path.with_suffix('.xlsx')

    if not pdf_path.exists():
        print(f"[error] PDF not found: {pdf_path}")
        sys.exit(1)

    convert(pdf_path, excel_path)
