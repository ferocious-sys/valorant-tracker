param([Parameter(ValueFromRemainingArguments = $true)][string[]]$TrackerArguments)
$ErrorActionPreference = 'Stop'
$trackerPython = 'python'
$trackerCredentialPath = $null
$trackerConfigPath = Join-Path $PSScriptRoot 'runtime-config.json'
if (Test-Path -LiteralPath $trackerConfigPath) {
    $trackerConfig = Get-Content -LiteralPath $trackerConfigPath -Raw | ConvertFrom-Json
    $trackerPython = $trackerConfig.python
    $trackerCredentialPath = $trackerConfig.credentialPath
}
$trackerPreviousKey = $env:HENRIK_API_KEY
try {
    if (-not $env:HENRIK_API_KEY -and $trackerCredentialPath -and (Test-Path -LiteralPath $trackerCredentialPath)) {
        $trackerSecret = Import-Clixml -LiteralPath $trackerCredentialPath
        $env:HENRIK_API_KEY = [System.Net.NetworkCredential]::new('', $trackerSecret).Password
    }
    if (-not $env:HENRIK_API_KEY) {
        $env:HENRIK_API_KEY = [Environment]::GetEnvironmentVariable('HENRIK_API_KEY', 'User')
    }
    if (-not $TrackerArguments) { $TrackerArguments = @('web') }
    & $trackerPython (Join-Path $PSScriptRoot 'valorant_tracker.py') @TrackerArguments
} finally {
    $env:HENRIK_API_KEY = $trackerPreviousKey
    Remove-Variable trackerSecret -ErrorAction SilentlyContinue
}
