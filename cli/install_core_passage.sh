#!/bin/bash
# Install a complete core passage unit from STUDIES/ JSON files
#
# Usage:
#   ./cli/install_core_passage.sh <unit> <category> [database]
#
# Arguments:
#   unit      - Base name of passage (e.g., "romans_8", "john_3")
#   category  - Theological category (e.g., "sanctification", "justification")
#   database  - Path to SQLite database (default: compendium.sqlite)
#
# Examples:
#   ./cli/install_core_passage.sh romans_8 sanctification
#   ./cli/install_core_passage.sh john_3 atonement test.db

set -euo pipefail

# Parse arguments
if [ $# -lt 2 ]; then
    echo "[error] Usage: $0 <unit> <category> [database]"
    echo ""
    echo "Examples:"
    echo "  $0 romans_8 sanctification"
    echo "  $0 john_3 atonement test.db"
    exit 1
fi

UNIT="$1"
CATEGORY="$2"
DATABASE="${3:-compendium.sqlite}"

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATABASE_PATH="$PROJECT_ROOT/$DATABASE"

GREEK_MARGINS_PATH="$PROJECT_ROOT/STUDIES/greek-margins/$UNIT.json"
VERSE_NOTES_PATH="$PROJECT_ROOT/STUDIES/verse-notes/$UNIT.json"
CORE_PASSAGE_PATH="$PROJECT_ROOT/STUDIES/core-passages/$CATEGORY.json"

# Validate JSON files exist
echo "[info] Validating JSON files..."

if [ ! -f "$GREEK_MARGINS_PATH" ]; then
    echo "[error] Greek margins file not found: $GREEK_MARGINS_PATH"
    exit 1
fi

if [ ! -f "$VERSE_NOTES_PATH" ]; then
    echo "[error] Verse notes file not found: $VERSE_NOTES_PATH"
    exit 1
fi

if [ ! -f "$CORE_PASSAGE_PATH" ]; then
    echo "[error] Core passage file not found: $CORE_PASSAGE_PATH"
    exit 1
fi

echo "[ok] Found all JSON files"
echo "  - Greek margins: $GREEK_MARGINS_PATH"
echo "  - Verse notes:   $VERSE_NOTES_PATH"
echo "  - Core passage:  $CORE_PASSAGE_PATH"
echo ""

# Validate database exists
if [ ! -f "$DATABASE_PATH" ]; then
    echo "[error] Database not found: $DATABASE_PATH"
    echo "[info] Create it first with: python compendium.py init-schema"
    exit 1
fi

# Run installation
echo "[info] Installing core passage unit: $UNIT ($CATEGORY)"
echo ""

cd "$PROJECT_ROOT"

python -m sbc.core_passages \
    --db "$DATABASE" \
    add-from-json \
    --greek-margins "STUDIES/greek-margins/$UNIT.json" \
    --verse-notes "STUDIES/verse-notes/$UNIT.json" \
    --core-passage "STUDIES/core-passages/$CATEGORY.json"

if [ $? -eq 0 ]; then
    echo ""
    echo "[ok] Core passage installed successfully!"
else
    echo ""
    echo "[error] Installation failed"
    exit 1
fi
