#!/usr/bin/env python3
"""
Test the complete import workflow by creating a minimal sample Bible.
"""
import sys
from pathlib import Path

# Create a minimal 3-verse test Bible in CSV format
test_data = """book,chapter,verse,text
Genesis,1,1,In the beginning God created the heaven and the earth.
Genesis,1,2,And the earth was without form and void; and darkness was upon the face of the deep.
John,3,16,For God so loved the world that he gave his only begotten Son.
"""

# Write to file
test_file = Path("test_sample.csv")
test_file.write_text(test_data, encoding="utf-8")
print(f"[ok] Created test sample: {test_file}")
print(f"     Contains 3 verses: Genesis 1:1-2, John 3:16")
