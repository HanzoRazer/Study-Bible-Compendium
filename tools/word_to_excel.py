#!/usr/bin/env python3
"""
Convert PDF documents to Excel spreadsheets.

Extracts text content and tables from PDF files and writes to .xlsx format.
Optimized for large documents with batch processing and progress tracking.
"""

import sys
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
    from openpyxl import Workbook
except ImportError:
    print("[error] Required packages not installed")
    print("Install with: pip install pdfplumber openpyxl")
    sys.exit(1)


def convert_pdf_to_excel(
    pdf_path: str,
    excel_path: Optional[str] = None,
    mode: str = "text",
    batch_size: int = 50,
    save_every: int = 500
) -> None:
    """
    Convert PDF document to Excel spreadsheet.
    
    Args:
        pdf_path: Path to input .pdf file
        excel_path: Path to output .xlsx file (defaults to same name)
        mode: Extraction mode - "text" (text by page/line) or "tables" (extract tables)
        batch_size: Number of pages to process before progress update
        save_every: Save workbook every N pages to prevent memory issues
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"[error] File not found: {pdf_path}")
        sys.exit(1)
    
    if not pdf_file.suffix.lower() == ".pdf":
        print(f"[error] File must be .pdf format: {pdf_path}")
        sys.exit(1)
    
    # Default output path
    if excel_path is None:
        excel_path = pdf_file.with_suffix(".xlsx")
    else:
        excel_path = Path(excel_path)
    
    # Show file size
    file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
    print(f"[info] Reading PDF document: {pdf_file.name} ({file_size_mb:.2f} MB)")
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            print(f"[info] Document contains {total_pages} pages")
            
            if mode == "text":
                # Extract text line by line
                ws.title = "Text Content"
                ws.append(["Page", "Line", "Text"])
                row_count = 0
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line_num, line in enumerate(lines, start=1):
                            line = line.strip()
                            if line:  # Skip empty lines
                                ws.append([page_num, line_num, line])
                                row_count += 1
                    
                    # Progress update
                    if page_num % batch_size == 0:
                        progress = (page_num / total_pages) * 100
                        print(f"[info] Processing... Page {page_num}/{total_pages} ({progress:.1f}%) - {row_count:,} lines extracted")
                    
                    # Periodic save to prevent memory issues with large files
                    if page_num % save_every == 0:
                        print(f"[info] Auto-saving at page {page_num}...")
                        wb.save(excel_path)
                
                print(f"[ok] Extracted {row_count:,} lines from {total_pages} pages")
            
            elif mode == "tables":
                # Extract tables from all pages
                ws.title = "Tables"
                table_count = 0
                total_rows = 0
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    tables = page.extract_tables()
                    
                    if tables:
                        for table_idx, table in enumerate(tables):
                            table_count += 1
                            
                            # Add separator between tables
                            if table_count > 1:
                                ws.append([])  # Empty row
                            
                            # Add table header with page/table info
                            ws.append([f"Page {page_num} - Table {table_idx + 1}"])
                            
                            # Add table data
                            for row in table:
                                if row:  # Skip None rows
                                    # Clean cells (handle None values)
                                    cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                                    ws.append(cleaned_row)
                                    total_rows += 1
                        
                        print(f"[info] Page {page_num}: Found {len(tables)} table(s)")
                    
                    # Progress update
                    if page_num % batch_size == 0:
                        progress = (page_num / total_pages) * 100
                        print(f"[info] Processing... Page {page_num}/{total_pages} ({progress:.1f}%)")
                
                if table_count == 0:
                    print("[warn] No tables found in document")
                    ws.append(["No tables found"])
                else:
                    print(f"[ok] Extracted {table_count} tables with {total_rows:,} total rows")
            
            else:
                print(f"[error] Unknown mode: {mode}. Use 'text' or 'tables'")
                sys.exit(1)
    
    except Exception as e:
        print(f"[error] Failed to process PDF: {e}")
        sys.exit(1)
    
    # Save Excel file
    print(f"[info] Saving Excel file...")
    wb.save(excel_path)
    output_size_mb = excel_path.stat().st_size / (1024 * 1024)
    print(f"[ok] Saved Excel file: {excel_path} ({output_size_mb:.2f} MB)")


def main(argv: list[str]) -> None:
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert PDF documents to Excel spreadsheets (.xlsx)",
        epilog="Example: python word_to_excel.py document.pdf -o output.xlsx -m text"
    )
    parser.add_argument(
        "pdf_file",
        help="Path to input PDF document (.pdf)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Path to output Excel file (default: same name as input with .xlsx extension)"
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["text", "tables"],
        default="text",
        help="Extraction mode: 'text' (extract text line by line) or 'tables' (extract tables)"
    )
    parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=50,
        help="Progress update frequency in pages (default: 50 pages)"
    )
    parser.add_argument(
        "-s", "--save-every",
        type=int,
        default=500,
        help="Auto-save every N pages to manage memory (default: 500 pages)"
    )
    
    args = parser.parse_args(argv)
    
    convert_pdf_to_excel(
        pdf_path=args.pdf_file,
        excel_path=args.output,
        mode=args.mode,
        batch_size=args.batch_size,
        save_every=args.save_every
    )


if __name__ == "__main__":
    main(sys.argv[1:])
