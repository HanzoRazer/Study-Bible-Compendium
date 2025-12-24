"""
sbc - Study Bible Compendium core package

This package contains the core functionality for the Study Bible Compendium:
- config: Project configuration and versioning
- paths: Path management and directory setup
- util: Utility functions for console output
- loader: Bible text import functionality
- search: Verse search functionality
- pdfgen: PDF report generation
"""

from . import config
from .paths import PROJECT_ROOT, DB_PATH, ensure_basic_dirs
from .util import info, warn, ok
from .loader import import_bible_from_excel
from .search import search_verses, print_search_results
from .pdfgen import generate_basic_report

__version__ = config.__version__
__all__ = [
    "config",
    "PROJECT_ROOT",
    "DB_PATH",
    "ensure_basic_dirs",
    "info",
    "warn",
    "ok",
    "import_bible_from_excel",
    "search_verses",
    "print_search_results",
    "generate_basic_report",
]
