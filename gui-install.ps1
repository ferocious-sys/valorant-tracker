param([string]$SourceDirectory)

if ($env:OS -ne 'Windows_NT') { throw 'The GUI installer requires Windows.' }
if ([Threading.Thread]::CurrentThread.ApartmentState -ne 'STA') {
    throw 'Run with powershell.exe -STA -File gui-install.ps1.'
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

function Quote-PS([string]$Value) { "'" + $Value.Replace("'", "''") + "'" }

$script:installProcess = $null
$script:tempRoot = $null
$script:logPath = $null
$script:lastLog = ''
$script:finished = $false

function Clear-SetupTemp {
    if ($script:tempRoot -and (Test-Path -LiteralPath $script:tempRoot)) {
        $resolved = [IO.Path]::GetFullPath($script:tempRoot)
        $parent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
        if ($resolved.StartsWith($parent, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolved) -match '^valorant-gui-[a-f0-9]{32}$') {
            Remove-Item -LiteralPath $resolved -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    $script:tempRoot = $null
    $script:logPath = $null
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'VALORANT Tracker Setup'
$form.Size = New-Object Drawing.Size(640, 590)
$form.MinimumSize = New-Object Drawing.Size(640, 590)
$form.StartPosition = 'CenterScreen'
$form.BackColor = [Drawing.Color]::FromArgb(17, 21, 34)
$form.ForeColor = [Drawing.Color]::FromArgb(237, 242, 255)
$form.Font = New-Object Drawing.Font('Segoe UI', 10)

function Add-Label([string]$Text, [int]$X, [int]$Y, [int]$Width, [int]$Height, [int]$Size = 10) {
    $label = New-Object System.Windows.Forms.Label
    $label.Text = $Text
    $label.Location = New-Object Drawing.Point($X, $Y)
    $label.Size = New-Object Drawing.Size($Width, $Height)
    $label.Font = New-Object Drawing.Font('Segoe UI', $Size)
    $form.Controls.Add($label)
    return $label
}

function Style-Button($Button, [Drawing.Color]$Background) {
    $Button.FlatStyle = 'Flat'
    $Button.FlatAppearance.BorderSize = 0
    $Button.BackColor = $Background
    $Button.ForeColor = [Drawing.Color]::White
    $Button.Cursor = 'Hand'
}

$title = Add-Label 'VALORANT TRACKER' 24 20 580 38 20
$title.Font = New-Object Drawing.Font('Segoe UI Semibold', 20)
$subtitle = Add-Label 'Install the local tracker and launch its web client.' 26 64 570 28 10
$subtitle.ForeColor = [Drawing.Color]::FromArgb(165, 178, 205)

Add-Label 'Installation folder' 26 112 250 24 | Out-Null
$pathBox = New-Object System.Windows.Forms.TextBox
$pathBox.Location = New-Object Drawing.Point(26, 141)
$pathBox.Size = New-Object Drawing.Size(482, 29)
$pathBox.Text = Join-Path $env:LOCALAPPDATA 'ValorantTracker'
$form.Controls.Add($pathBox)
$browse = New-Object System.Windows.Forms.Button
$browse.Text = 'Browse'
$browse.Location = New-Object Drawing.Point(518, 139)
$browse.Size = New-Object Drawing.Size(90, 33)
Style-Button $browse ([Drawing.Color]::FromArgb(57, 67, 92))
$form.Controls.Add($browse)
$browse.Add_Click({
    $picker = New-Object System.Windows.Forms.FolderBrowserDialog
    $picker.Description = 'Choose a folder for VALORANT Tracker'
    if (Test-Path -LiteralPath $pathBox.Text) { $picker.SelectedPath = $pathBox.Text }
    if ($picker.ShowDialog($form) -eq 'OK') { $pathBox.Text = $picker.SelectedPath }
    $picker.Dispose()
})

Add-Label 'HenrikDev API key' 26 190 250 24 | Out-Null
$keyBox = New-Object System.Windows.Forms.TextBox
$keyBox.Location = New-Object Drawing.Point(26, 219)
$keyBox.Size = New-Object Drawing.Size(482, 29)
$keyBox.UseSystemPasswordChar = $true
$form.Controls.Add($keyBox)
$dashboard = New-Object System.Windows.Forms.Button
$dashboard.Text = 'Get key'
$dashboard.Location = New-Object Drawing.Point(518, 217)
$dashboard.Size = New-Object Drawing.Size(90, 33)
Style-Button $dashboard ([Drawing.Color]::FromArgb(57, 67, 92))
$form.Controls.Add($dashboard)
$dashboard.Add_Click({ Start-Process 'https://api.henrikdev.xyz/dashboard/' })
$hint = Add-Label 'Leave blank to reuse a saved key. Sign in on HenrikDev to create a new key.' 26 256 580 38 9
$hint.ForeColor = [Drawing.Color]::FromArgb(165, 178, 205)

$shortcuts = New-Object System.Windows.Forms.CheckBox
$shortcuts.Text = 'Add !rank, !today, !web, and other PowerShell shortcuts'
$shortcuts.Location = New-Object Drawing.Point(26, 307)
$shortcuts.Size = New-Object Drawing.Size(570, 27)
$shortcuts.Checked = $true
$form.Controls.Add($shortcuts)
$startWeb = New-Object System.Windows.Forms.CheckBox
$startWeb.Text = 'Start the web client after installation'
$startWeb.Location = New-Object Drawing.Point(26, 339)
$startWeb.Size = New-Object Drawing.Size(570, 27)
$startWeb.Checked = $true
$form.Controls.Add($startWeb)

$install = New-Object System.Windows.Forms.Button
$install.Text = 'Install tracker'
$install.Location = New-Object Drawing.Point(26, 385)
$install.Size = New-Object Drawing.Size(160, 42)
Style-Button $install ([Drawing.Color]::FromArgb(84, 104, 222))
$form.Controls.Add($install)
$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object Drawing.Point(201, 396)
$progress.Size = New-Object Drawing.Size(407, 19)
$progress.Style = 'Marquee'
$progress.Visible = $false
$form.Controls.Add($progress)

$status = Add-Label 'Ready. No Riot password is required.' 26 440 580 28 10
$status.ForeColor = [Drawing.Color]::FromArgb(142, 218, 213)
$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Location = New-Object Drawing.Point(26, 473)
$logBox.Size = New-Object Drawing.Size(582, 65)
$logBox.Multiline = $true
$logBox.ReadOnly = $true
$logBox.ScrollBars = 'Vertical'
$logBox.BackColor = [Drawing.Color]::FromArgb(27, 34, 52)
$logBox.ForeColor = [Drawing.Color]::FromArgb(209, 220, 242)
$form.Controls.Add($logBox)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 350
$timer.Add_Tick({
    if ($script:logPath -and (Test-Path -LiteralPath $script:logPath)) {
        try {
            $content = Get-Content -LiteralPath $script:logPath -Raw -ErrorAction Stop
            if ($content -ne $script:lastLog) {
                $script:lastLog = $content
                $logBox.Text = $content
                $logBox.SelectionStart = $logBox.TextLength
                $logBox.ScrollToCaret()
            }
        } catch { }
    }
    if (-not $script:installProcess -or $script:finished -or -not $script:installProcess.HasExited) { return }
    $script:finished = $true
    $timer.Stop()
    $progress.Visible = $false
    $install.Enabled = $true
    $pathBox.Enabled = $true
    $browse.Enabled = $true
    $keyBox.Enabled = $true
    $shortcuts.Enabled = $true
    if ($script:installProcess.ExitCode -eq 0) {
        $status.Text = 'Installed successfully.'
        $status.ForeColor = [Drawing.Color]::FromArgb(142, 218, 213)
        $keyBox.Clear()
        if ($startWeb.Checked) {
            try {
                $launcher = Join-Path ([IO.Path]::GetFullPath($pathBox.Text.Trim())) 'start.ps1'
                $webProcess = New-Object System.Diagnostics.ProcessStartInfo
                $webProcess.FileName = 'powershell.exe'
                $webProcess.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $launcher + '" web'
                $webProcess.UseShellExecute = $true
                [void][System.Diagnostics.Process]::Start($webProcess)
                $status.Text = 'Installed. The web client is starting in a PowerShell window.'
            } catch {
                $status.Text = 'Installed, but the web client could not start. Run !web.'
            }
        }
    } else {
        $status.Text = 'Installation failed. Review the details below and try again.'
        $status.ForeColor = [Drawing.Color]::FromArgb(255, 166, 166)
    }
    $script:installProcess.Dispose()
    $script:installProcess = $null
    Clear-SetupTemp
})

$install.Add_Click({
    try {
        $target = $pathBox.Text.Trim()
        if (-not $target) { throw 'Choose an installation folder.' }
        $target = [IO.Path]::GetFullPath($target)
        $script:tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('valorant-gui-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $script:tempRoot -Force | Out-Null
        $script:logPath = Join-Path $script:tempRoot 'setup.log'
        $script:lastLog = ''
        $localInstaller = if ($PSScriptRoot) { Join-Path $PSScriptRoot 'install.ps1' } else { $null }
        if ($localInstaller -and (Test-Path -LiteralPath $localInstaller)) {
            $installerPath = $localInstaller
            if (-not $SourceDirectory) { $source = $PSScriptRoot } else { $source = $SourceDirectory }
        } else {
            $installerPath = Join-Path $script:tempRoot 'install.ps1'
            Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/ferocious-sys/valorant-tracker/main/install.ps1' -OutFile $installerPath -TimeoutSec 30
            $source = $SourceDirectory
        }
        $command = '& ' + (Quote-PS $installerPath) + ' -InstallDirectory ' + (Quote-PS $target) + ' -NonInteractive -AutoInstallPython -NoStart'
        if ($source) { $command += ' -SourceDirectory ' + (Quote-PS ([IO.Path]::GetFullPath($source))) }
        if (-not $shortcuts.Checked) { $command += ' -SkipProfile' }
        $command = '$ErrorActionPreference = ''Stop''; try { ' + $command + ' *> ' + (Quote-PS $script:logPath) + '; exit 0 } catch { $_ | Out-String | Add-Content -LiteralPath ' + (Quote-PS $script:logPath) + '; exit 1 }'
        $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
        $info = New-Object System.Diagnostics.ProcessStartInfo
        $info.FileName = 'powershell.exe'
        $info.Arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand ' + $encoded
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        if ($keyBox.Text.Trim()) { $info.EnvironmentVariables['HENRIK_API_KEY'] = $keyBox.Text.Trim() }
        $script:installProcess = [System.Diagnostics.Process]::Start($info)
        $script:finished = $false
        $install.Enabled = $false
        $pathBox.Enabled = $false
        $browse.Enabled = $false
        $keyBox.Enabled = $false
        $shortcuts.Enabled = $false
        $progress.Visible = $true
        $status.Text = 'Installing... This can take a few minutes if Python is needed.'
        $timer.Start()
    } catch {
        $status.Text = 'Could not start installation: ' + $_.Exception.Message
        $status.ForeColor = [Drawing.Color]::FromArgb(255, 166, 166)
        Clear-SetupTemp
    }
})

$form.Add_FormClosing({
    if ($script:installProcess -and -not $script:installProcess.HasExited) {
        $answer = [System.Windows.Forms.MessageBox]::Show('Stop the installation and close setup?', 'VALORANT Tracker Setup', 'YesNo', 'Question')
        if ($answer -ne 'Yes') { $_.Cancel = $true; return }
        $script:installProcess.Kill()
        $script:installProcess.WaitForExit()
    }
    $timer.Stop()
    if ($script:installProcess) { $script:installProcess.Dispose() }
    Clear-SetupTemp
})

[void]$form.ShowDialog()
$form.Dispose()
