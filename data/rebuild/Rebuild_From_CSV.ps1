param(
  [string]$Manifest = ".\Project_Rebuild_Manifest.csv",
  [switch]$DryRun = $false
)
if (!(Test-Path $Manifest)) { throw "Manifest not found: $Manifest" }
$rows = Import-Csv $Manifest
Write-Host ("Loaded {0} manifest rows" -f $rows.Count)

foreach ($r in $rows) {
  $path = $r.path
  $cmd = $r.command_to_recreate
  $action = $r.action
  $proj = $r.project
  $phase = $r.phase
  if ([string]::IsNullOrWhiteSpace($cmd) -or $cmd -like "(local file*") {
    continue
  }
  Write-Host "[$proj/$phase] $action -> $path"
  if ($DryRun) {
    Write-Host "  DRYRUN: $cmd"
  } else {
    # naive execution: try powershell first, then python, else shell
    if ($cmd -match "^\s*powershell\b") {
      Invoke-Expression $cmd
    } elseif ($cmd -match "^\s*python\b") {
      & python -c "import os; print('PY OK')" 2>$null | Out-Null
      # run the full command via cmd /c to preserve args
      cmd /c $cmd
    } else {
      cmd /c $cmd
    }
  }
}
Write-Host "Rebuild manifest complete."
