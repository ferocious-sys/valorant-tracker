# Dot-source this file to enable the VALORANT commands in PowerShell.
$script:ValorantTrackerPath = Join-Path $PSScriptRoot 'valorant_tracker.py'

function global:!rank {
    if (-not $env:HENRIK_API_KEY) {
        $env:HENRIK_API_KEY = [Environment]::GetEnvironmentVariable('HENRIK_API_KEY', 'User')
    }
    python $script:ValorantTrackerPath rank @args
}

function global:!recent {
    if (-not $env:HENRIK_API_KEY) {
        $env:HENRIK_API_KEY = [Environment]::GetEnvironmentVariable('HENRIK_API_KEY', 'User')
    }
    python $script:ValorantTrackerPath recent @args
}

function global:Invoke-ValorantTracker {
    if (-not $env:HENRIK_API_KEY) {
        $env:HENRIK_API_KEY = [Environment]::GetEnvironmentVariable('HENRIK_API_KEY', 'User')
    }
    python $script:ValorantTrackerPath @args
}

function global:!today { Invoke-ValorantTracker today @args }
function global:!rr { Invoke-ValorantTracker rr @args }
function global:!stats { Invoke-ValorantTracker stats @args }
function global:!last { Invoke-ValorantTracker last @args }
function global:!profile { Invoke-ValorantTracker profile @args }
function global:!help { Invoke-ValorantTracker --help }
