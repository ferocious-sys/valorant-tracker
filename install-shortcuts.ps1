$ErrorActionPreference = 'Stop'
$shortcutPath = Join-Path $PSScriptRoot 'shortcuts.ps1'
$profileDirectory = Split-Path -Parent $PROFILE
New-Item -ItemType Directory -Path $profileDirectory -Force | Out-Null
$line = ". '" + $shortcutPath.Replace("'", "''") + "' # valorant-tracker shortcuts"
if (-not (Test-Path -LiteralPath $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE | Out-Null
}
$content = Get-Content -LiteralPath $PROFILE -Raw
if (-not $content -or -not $content.Contains($line)) {
    Add-Content -LiteralPath $PROFILE -Value ("`r`n" + $line) -Encoding UTF8
}
. $shortcutPath
Write-Output 'Installed VALORANT shortcuts. Open a new PowerShell window, or dot-source shortcuts.ps1 in this window. Run !help to see commands.'
