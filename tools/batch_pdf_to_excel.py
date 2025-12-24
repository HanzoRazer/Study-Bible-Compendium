#!/usr/bin/env python3
"""
Batch convert multiple PDF files to Excel spreadsheets.

Processes all PDFs in a directory or from a list of files.
Handles large files with progress tracking and error recovery.
"""

import sys
from pathlib import Path
from typing import Optional, List
import time

try:
    import pdfplumber
    from openpyxl import Workbook
except ImportError:
    print("[error] Required packages not installed")
    print("Install with: pip install pdfplumber openpyxl")
    sys.exit(1)


def convert_single_pdf(
    pdf_path: Path,
    excel_path: Optional[Path] = None,
    mode: str = "text",
    batch_size: int = 50,
    save_every: int = 500
) -> bool:
    """
    Convert a single PDF to Excel.
    Returns True if successful, False if failed.
    """
    if excel_path is None:
        excel_path = pdf_path.with_suffix(".xlsx")
    
    # Skip if Excel file already exists
    if excel_path.exists():
        print(f"[info] Skipping {pdf_path.name} - Excel file already exists")
        return True
    
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"\n[info] Converting: {pdf_path.name} ({file_size_mb:.2f} MB)")
    
    start_time = time.time()
    
    try:
        wb = Workbook()
        ws = wb.active
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"[info] Pages: {total_pages}")
            
            if mode == "text":
                ws.title = "Text Content"
                ws.append(["Page", "Line", "Text"])
                row_count = 0
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line_num, line in enumerate(lines, start=1):
                            line = line.strip()
                            if line:
                                ws.append([page_num, line_num, line])
                                row_count += 1
                    
                    if page_num % batch_size == 0:
                        progress = (page_num / total_pages) * 100
                        print(f"[info] Progress: Page {page_num}/{total_pages} ({progress:.1f}%) - {row_count:,} lines")
                    
                    if page_num % save_every == 0:
                        print(f"[info] Auto-saving at page {page_num}...")
                        wb.save(excel_path)
                
                print(f"[info] Extracted {row_count:,} lines")
            
            elif mode == "tables":
                ws.title = "Tables"
                table_count = 0
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    tables = page.extract_tables()
                    
                    if tables:
                        for table_idx, table in enumerate(tables):
                            table_count += 1
                            if table_count > 1:
                                ws.append([])
                            ws.append([f"Page {page_num} - Table {table_idx + 1}"])
                            
                            for row in table:
                                if row:
                                    cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                                    ws.append(cleaned_row)
                    
                    if page_num % batch_size == 0:
                        progress = (page_num / total_pages) * 100
                        print(f"[info] Progress: Page {page_num}/{total_pages} ({progress:.1f}%)")
                
                if table_count == 0:
                    print("[warn] No tables found")
                else:
                    print(f"[info] Extracted {table_count} tables")
        
        print(f"[info] Saving final file...")
        wb.save(excel_path)
        
        output_size_mb = excel_path.stat().st_size / (1024 * 1024)
        elapsed = time.time() - start_time
        print(f"[ok] Saved: {excel_path.name} ({output_size_mb:.2f} MB) in {elapsed:.1f}s")
        
        return True
    
    except Exception as e:
        print(f"[error] Failed to convert {pdf_path.name}: {e}")
        return False


def batch_convert_pdfs(
    pdf_paths: List[Path],
    output_dir: Optional[Path] = None,
    mode: str = "text",
    batch_size: int = 50,
    save_every: int = 500
) -> tuple[int, int]:
    """
    Convert multiple PDFs to Excel.
    Returns (success_count, failure_count).
    """
    total = len(pdf_paths)
    success_count = 0
    failure_count = 0
    
    print(f"[info] Starting batch conversion of {total} PDF files")
    print(f"[info] Mode: {mode}")
    if output_dir:
        print(f"[info] Output directory: {output_dir}")
    print()
    
    for idx, pdf_path in enumerate(pdf_paths, start=1):
        print(f"═══ File {idx}/{total} ═══")
        
        if output_dir:
            excel_path = output_dir / pdf_path.with_suffix(".xlsx").name
        else:
            excel_path = None
        
        if convert_single_pdf(pdf_path, excel_path, mode, batch_size, save_every):
            success_count += 1
        else:
            failure_count += 1
    
    return success_count, failure_count


def find_pdfs_in_directory(directory: Path, recursive: bool = False) -> List[Path]:
    """Find all PDF files in a directory."""
    if recursive:
        pdfs = sorted(directory.rglob("*.pdf"))
    else:
        pdfs = sorted(directory.glob("*.pdf"))
    
    return pdfs


def main(argv: list[str]) -> None:
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Batch convert multiple PDF files to Excel spreadsheets",
        epilog="""Examples:
  # Convert all PDFs in current directory
  python batch_pdf_to_excel.py --dir .
  
  # Convert all PDFs in a folder (including subfolders)
  python batch_pdf_to_excel.py --dir "C:\\PDFs" --recursive
  
  # Convert specific files
  python batch_pdf_to_excel.py --files file1.pdf file2.pdf file3.pdf
  
  # Save all to a specific output directory
  python batch_pdf_to_excel.py --dir . --output "C:\\Excel Output"
        """
    )
    
    parser.add_argument(
        "--dir",
        help="Directory containing PDF files to convert"
    )
    parser.add_argument(
        "--files",
        nargs='+',
        help="Specific PDF files to convert"
    )
    parser.add_argument(
        "--output",
        help="Output directory for Excel files (default: same as PDF location)"
    )
    parser.add_argument(
        "--recursive",
        action='store_true',
        help="Search for PDFs in subdirectories"
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["text", "tables"],
        default="text",
        help="Extraction mode (default: text)"
    )
    parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=50,
        help="Progress update frequency in pages (default: 50)"
    )
    parser.add_argument(
        "-s", "--save-every",
        type=int,
        default=500,
        help="Auto-save every N pages (default: 500)"
    )
    
    args = parser.parse_args(argv)
    
    # Validate inputs
    if not args.dir and not args.files:
        parser.print_help()
        print("\n[error] Must specify either --dir or --files")
        sys.exit(1)
    
    # Collect PDF files
    pdf_paths = []
    
    if args.dir:
        directory = Path(args.dir)
        if not directory.exists():
            print(f"[error] Directory not found: {directory}")
            sys.exit(1)
        
        pdf_paths = find_pdfs_in_directory(directory, args.recursive)
        
        if not pdf_paths:
            print(f"[warn] No PDF files found in {directory}")
            sys.exit(0)
    
    if args.files:
        for file_path in args.files:
            path = Path(file_path)
            if not path.exists():
                print(f"[warn] File not found: {file_path}")
                continue
            if path.suffix.lower() != '.pdf':
                print(f"[warn] Not a PDF file: {file_path}")
                continue
            pdf_paths.append(path)
    
    if not pdf_paths:
        print("[error] No valid PDF files to convert")
        sys.exit(1)
    
    # Setup output directory
    output_dir = None
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"[info] Created output directory: {output_dir}")
    
    # Run batch conversion
    start_time = time.time()
    success_count, failure_count = batch_convert_pdfs(
        pdf_paths,
        output_dir,
        args.mode,
        args.batch_size,
        args.save_every
    )
    
    total_time = time.time() - start_time
    
    # Summary
    print("\n" + "═" * 50)
    print(f"[ok] Batch conversion complete!")
    print(f"  Total files: {len(pdf_paths)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failure_count}")
    print(f"  Total time: {total_time / 60:.1f} minutes")
    print("═" * 50)


if __name__ == "__main__":
    main(sys.argv[1:])
