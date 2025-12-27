#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Install a complete core passage unit from STUDIES/ JSON files.

.DESCRIPTION
    Convenience wrapper for sbc.core_passages that installs greek-margins,
    verse-notes, and core-passage metadata in a single command.

.PARAMETER Unit
    The base name of the passage (e.g., "romans_8", "john_3")
    Must match the JSON filenames in STUDIES/ subdirectories.

.PARAMETER Category
    The theological category (e.g., "sanctification", "justification")
    Must match the core-passages JSON filename.

.PARAMETER Database
    Path to SQLite database. Defaults to "compendium.sqlite" in project root.

.EXAMPLE
    .\cli\install_core_passage.ps1 -Unit romans_8 -Category sanctification

.EXAMPLE
    .\cli\install_core_passage.ps1 romans_8 sanctification -Database test.db
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Unit,
    
    [Parameter(Mandatory=$true, Position=1)]
    [string]$Category,
    
    [Parameter(Mandatory=$false)]
    [string]$Database = "compendium.sqlite"
)

$ErrorActionPreference = "Stop"

# Resolve paths
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DatabasePath = Join-Path $ProjectRoot $Database

$GreekMarginsPath = Join-Path $ProjectRoot "STUDIES\greek-margins\$Unit.json"
$VerseNotesPath = Join-Path $ProjectRoot "STUDIES\verse-notes\$Unit.json"
$CorePassagePath = Join-Path $ProjectRoot "STUDIES\core-passages\$Category.json"

# Validate JSON files exist
Write-Host "[info] Validating JSON files..." -ForegroundColor Cyan

if (-not (Test-Path $GreekMarginsPath)) {
    Write-Host "[error] Greek margins file not found: $GreekMarginsPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $VerseNotesPath)) {
    Write-Host "[error] Verse notes file not found: $VerseNotesPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $CorePassagePath)) {
    Write-Host "[error] Core passage file not found: $CorePassagePath" -ForegroundColor Red
    exit 1
}

Write-Host "[ok] Found all JSON files" -ForegroundColor Green
Write-Host "  - Greek margins: $GreekMarginsPath"
Write-Host "  - Verse notes:   $VerseNotesPath"
Write-Host "  - Core passage:  $CorePassagePath"
Write-Host ""

# Validate database exists
if (-not (Test-Path $DatabasePath)) {
    Write-Host "[error] Database not found: $DatabasePath" -ForegroundColor Red
    Write-Host "[info] Create it first with: python compendium.py init-schema" -ForegroundColor Yellow
    exit 1
}

# Run installation
Write-Host "[info] Installing core passage unit: $Unit ($Category)" -ForegroundColor Cyan
Write-Host ""

Push-Location $ProjectRoot
try {
    python -m sbc.core_passages `
        --db $Database `
        add-from-json `
        --greek-margins "STUDIES\greek-margins\$Unit.json" `
        --verse-notes "STUDIES\verse-notes\$Unit.json" `
        --core-passage "STUDIES\core-passages\$Category.json"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[ok] Core passage installed successfully!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[error] Installation failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
