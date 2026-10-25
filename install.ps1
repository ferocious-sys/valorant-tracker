param(
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'ValorantTracker'),
    [string]$SourceDirectory,
    [switch]$NoStart,
    [switch]$NonInteractive,
    [switch]$AutoInstallPython,
    [switch]$SkipProfile
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Find-TrackerPython {
    $candidates = @()
    foreach ($commandName in @('python', 'python3', 'py')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    $pythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
    if (Test-Path -LiteralPath $pythonRoot) {
        $candidates += Get-ChildItem -LiteralPath $pythonRoot -Filter 'Python*' -Directory | ForEach-Object { Join-Path $_.FullName 'python.exe' }
    }
    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        try {
            $resolvedPython = & $candidate -c 'import sys; print(sys.executable) if sys.version_info >= (3,10) else sys.exit(1)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $resolvedPython -and (Test-Path -LiteralPath ([string]$resolvedPython))) { return [string]$resolvedPython }
        } catch { }
    }
    return $null
}

function Test-TrackerKey([string]$Key) {
    if ([string]::IsNullOrWhiteSpace($Key)) { return $false }
    try {
        $result = Invoke-RestMethod -Uri 'https://api.henrikdev.xyz/valorant/v1/version/ap' -Headers @{Authorization=$Key.Trim()} -TimeoutSec 20
        return $result.status -eq 200
    } catch {
        $status = 0
        if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
        if ($status -in @(401,403)) { return $false }
        throw 'API validation unavailable. Check your connection or wait for the rate limit to reset, then rerun the installer.'
    }
}

function Set-TrackerProfile([string]$ProfilePath, [string]$ShortcutPath) {
    $parent = Split-Path -Parent $ProfilePath
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $lines = @()
    if (Test-Path -LiteralPath $ProfilePath) { $lines = @(Get-Content -LiteralPath $ProfilePath) }
    $managedLine = ". '" + $ShortcutPath.Replace("'", "''") + "' # valorant-tracker shortcuts"
    $lines = @($lines | Where-Object { $_ -notmatch '^\. .* # valorant-tracker shortcuts$' })
    @($lines + $managedLine) | Set-Content -LiteralPath $ProfilePath -Encoding UTF8
}

Write-Host 'VALORANT Tracker setup' -ForegroundColor Cyan
Write-Host 'Installing for your Windows user. No Riot password is requested.'
$trackerPython = Find-TrackerPython
if (-not $trackerPython) {
    if ($NonInteractive -and -not $AutoInstallPython) { throw 'Python 3.10+ was not found. Install Python and retry.' }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Install Python 3.10+ from python.org, then rerun this command. Windows Package Manager is unavailable.' }
    Write-Host 'Installing Python with Windows Package Manager...'
    & winget install --id Python.Python.3.13 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw 'Python installation failed. Install Python from python.org and rerun setup.' }
    $trackerPython = Find-TrackerPython
    if (-not $trackerPython) { throw 'Python was installed but could not be located. Reopen PowerShell and rerun setup.' }
}

$InstallDirectory = [IO.Path]::GetFullPath($InstallDirectory)
New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
$credentialPath = Join-Path $InstallDirectory 'api-key.xml'
$trackerKey = $env:HENRIK_API_KEY
if (-not $trackerKey -and (Test-Path -LiteralPath $credentialPath)) {
    try { $trackerKey = [System.Net.NetworkCredential]::new('', (Import-Clixml -LiteralPath $credentialPath)).Password } catch { }
}
if (-not $trackerKey) { $trackerKey = [Environment]::GetEnvironmentVariable('HENRIK_API_KEY','User') }
if (-not (Test-TrackerKey $trackerKey)) {
    if ($NonInteractive) { throw 'No valid API key found. Run setup interactively to authenticate.' }
    Write-Host 'Sign in and create a Basic key in the HenrikDev dashboard.'
    Write-Host 'Application: Personal VALORANT Tracker CLI'
    Write-Host 'Use case: View my own account rank, match history, and daily RR in a local tracker.'
    Write-Host 'HenrikDev does not document automatic key provisioning; copy the key after creating it.'
    Start-Process 'https://api.henrikdev.xyz/dashboard/'
    $valid = $false
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        $secret = Read-Host 'Paste your HenrikDev API key (hidden)' -AsSecureString
        $trackerKey = [System.Net.NetworkCredential]::new('', $secret).Password
        if (Test-TrackerKey $trackerKey) { $valid = $true; break }
        Write-Host 'Key rejected. Check the key and try again.' -ForegroundColor Yellow
    }
    if (-not $valid) { throw 'Setup stopped: no valid API key. Rerun when you have a valid key.' }
}
$trackerKey = $trackerKey.Trim()
ConvertTo-SecureString -String $trackerKey -AsPlainText -Force | Export-Clixml -LiteralPath $credentialPath
Write-Host 'API key verified and saved with Windows user encryption.'

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('valorant-setup-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot | Out-Null
try {
    if ($SourceDirectory) {
        $sourcePath = (Resolve-Path -LiteralPath $SourceDirectory).Path
        $version = 'local-' + [guid]::NewGuid().ToString('N')
    } else {
        Write-Host 'Downloading the latest tracker...'
        $commit = Invoke-RestMethod -Uri 'https://api.github.com/repos/ferocious-sys/valorant-tracker/commits/main' -Headers @{'User-Agent'='valorant-tracker-installer'} -TimeoutSec 30
        $version = [string]$commit.sha
        if ($version -notmatch '^[a-f0-9]{40}$') { throw 'Invalid GitHub version response.' }
        $archive = Join-Path $tempRoot 'tracker.zip'
        Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/ferocious-sys/valorant-tracker/zip/$version" -OutFile $archive -TimeoutSec 120
        Expand-Archive -LiteralPath $archive -DestinationPath $tempRoot
        $sourcePath = Join-Path $tempRoot "valorant-tracker-$version"
    }
    $versionPath = Join-Path $InstallDirectory "versions\$version"
    New-Item -ItemType Directory -Path $versionPath -Force | Out-Null
    $files = @('valorant_tracker.py','valorant_stats.py','valorant_web.py','valorant_ui.py','valorant_overlay.py','shortcuts.ps1','launch.ps1','README.md')
    foreach ($file in $files) {
        $sourceFile = Join-Path $sourcePath $file
        if (-not (Test-Path -LiteralPath $sourceFile)) { throw "Downloaded package is missing $file." }
        Copy-Item -LiteralPath $sourceFile -Destination (Join-Path $versionPath $file) -Force
    }
    @{python=$trackerPython; credentialPath=$credentialPath} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $versionPath 'runtime-config.json') -Encoding UTF8
    & $trackerPython (Join-Path $versionPath 'valorant_tracker.py') --version
    if ($LASTEXITCODE -ne 0) { throw 'Installed tracker failed its startup check.' }
    $shortcutPath = Join-Path $versionPath 'shortcuts.ps1'
    if (-not $SkipProfile) {
        $documents = [Environment]::GetFolderPath('MyDocuments')
        $profiles = @($PROFILE, (Join-Path $documents 'WindowsPowerShell\Microsoft.PowerShell_profile.ps1'), (Join-Path $documents 'PowerShell\Microsoft.PowerShell_profile.ps1'))
        foreach ($profilePath in $profiles | Select-Object -Unique) { Set-TrackerProfile $profilePath $shortcutPath }
        Write-Host 'Shortcuts installed for Windows PowerShell and PowerShell 7.'
    }
    # Stable launcher for users who do not load a PowerShell profile.
    $launcher = "& '" + (Join-Path $versionPath 'launch.ps1').Replace("'", "''") + "' @args"
    $launcher | Set-Content -LiteralPath (Join-Path $InstallDirectory 'start.ps1') -Encoding UTF8
    Write-Host 'Installed. Use !web, !rank Player#TAG, or !help in a new PowerShell window.' -ForegroundColor Green
    if (-not $NoStart) {
        Write-Host 'Starting the web client. Keep this window open; Ctrl+C stops it.'
        $previousKey = $env:HENRIK_API_KEY
        try {
            $env:HENRIK_API_KEY = $trackerKey
            & $trackerPython (Join-Path $versionPath 'valorant_tracker.py') web
        } finally { $env:HENRIK_API_KEY = $previousKey }
    }
} finally {
    Remove-Variable trackerKey,secret -ErrorAction SilentlyContinue
    $resolvedTemp = [IO.Path]::GetFullPath($tempRoot)
    $expectedParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($resolvedTemp.StartsWith($expectedParent,[StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolvedTemp) -match '^valorant-setup-[a-f0-9]{32}$') {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}
