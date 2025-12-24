$outputDir = "C:\Users\thepr\Downloads\Study_Bible _Compendium\excel_output"
$logFile = "C:\Users\thepr\Downloads\Study_Bible _Compendium\excel_output\conversion_status.log"

# Ensure output dir exists
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

while ($true) {
    $timestamp = (Get-Date).ToString('u')
    $files = Get-ChildItem -Path $outputDir -Filter "*.xlsx" -File -ErrorAction SilentlyContinue
    $count = if ($files) { $files.Count } else { 0 }
    $latest = if ($files) { $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { $_.Name + " (`" + $_.LastWriteTime.ToString('u') + "`)" } } else { "N/A" }
    $line = "[$timestamp] Converted files: $count ; Latest: $latest"
    Add-Content -Path $logFile -Value $line
    Start-Sleep -Seconds 1800
}
