# Dot-source this file to enable the VALORANT commands in PowerShell.
$script:ValorantTrackerPath = Join-Path $PSScriptRoot 'valorant_tracker.py'

function global:Invoke-ValorantTracker {
    & (Join-Path (Split-Path -Parent $script:ValorantTrackerPath) 'launch.ps1') @args
}

function global:!rank { Invoke-ValorantTracker rank @args }
function global:!recent { Invoke-ValorantTracker recent @args }

function global:!today { Invoke-ValorantTracker today @args }
function global:!rr { Invoke-ValorantTracker rr @args }
function global:!stats { Invoke-ValorantTracker stats @args }
function global:!last { Invoke-ValorantTracker last @args }
function global:!profile { Invoke-ValorantTracker profile @args }
function global:!help { Invoke-ValorantTracker --help }
function global:!kd { Invoke-ValorantTracker kd @args }
function global:!hs { Invoke-ValorantTracker hs @args }
function global:!hours { Invoke-ValorantTracker hours @args }
function global:!career { Invoke-ValorantTracker career @args }
function global:!web { Invoke-ValorantTracker web @args }
function global:!serve { Invoke-ValorantTracker serve @args }
function global:!overlay { Invoke-ValorantTracker overlay @args }
