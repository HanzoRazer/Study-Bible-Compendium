"""
Path configuration for the Study Bible Compendium project.
"""

from pathlib import Path

# Project root is one level up from sbc/
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "compendium.sqlite"
SCHEMA_DIR = PROJECT_ROOT / "schema"
DATA_DIR = PROJECT_ROOT / "data"


def ensure_basic_dirs() -> None:
    """
    Ensure essential directories exist:
    - data/
    - reports/
    - logs/ (future)
    - schema/
    """
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)
    (PROJECT_ROOT / "reports").mkdir(exist_ok=True)
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    (PROJECT_ROOT / "schema").mkdir(exist_ok=True)
