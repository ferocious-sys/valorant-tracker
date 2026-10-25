# VALORANT Tracker CLI

Check your rank, recent games, and today's RR from your terminal.

```powershell
!rank "Player#TAG"
!recent "Player#TAG"
!today "Player#TAG"
```

Built with Python and the community [HenrikDev API](https://github.com/Henrik-3/unofficial-valorant-api). No Python runtime dependencies. Use it for your own account or players who have consented.

## One-command Windows installation

Paste this into PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/ferocious-sys/valorant-tracker/main/install.ps1 | iex"
```

This downloads and runs the installer from this repository. You can [review the script](install.ps1) first. Execution-policy bypass applies only to this installer process; it does not change your saved policy.

Setup will:

1. Find Python 3.10+ or install Python 3.13 for your Windows user through Windows Package Manager.
2. Open the HenrikDev dashboard if no valid key is available. Sign in there, create a Basic API key, and paste it into the installer's hidden prompt.
3. Validate the key and save it encrypted with Windows DPAPI for your user account.
4. Download the tracker into `%LOCALAPPDATA%\ValorantTracker`, install PowerShell shortcuts, and open the local web client automatically.

**Key creation is not automatic:** HenrikDev documents a dashboard-based key flow, not an API for third-party key provisioning. Setup never asks for your Riot or Discord password. Existing valid keys are reused. The dashboard may require joining HenrikDev's Discord and entering application details; setup displays suggested details.

Keep the terminal open while using the web client. Press **Ctrl+C** to stop. Later, open PowerShell and run `!web` to start again. Run the same installation command to update; your saved key is reused and older installed versions are retained.

The key is saved at `%LOCALAPPDATA%\ValorantTracker\api-key.xml`. Only the same Windows user on the same computer can decrypt it. The API key is passed to the Python child process in memory. An explicitly set `HENRIK_API_KEY` environment variable takes priority during normal launches.

If Python installation is unavailable, install [Python](https://www.python.org/downloads/windows/) manually and rerun the command. If organizational policy blocks scripts, follow your organization's policy; the installer does not change persistent execution-policy settings.

### Manual installation

```powershell
git clone https://github.com/ferocious-sys/valorant-tracker.git
cd valorant-tracker
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -SourceDirectory .
```

Already have Python and a key? You can also run the source directly:

```powershell
$secret = Read-Host 'HenrikDev API key' -AsSecureString
$env:HENRIK_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
python valorant_tracker.py web
```

For source-checkout shortcuts, run `.\install-shortcuts.ps1` and `. .\shortcuts.ps1`. Keep the checkout in the same folder. Remove the line ending in `# valorant-tracker shortcuts` from your PowerShell profile to uninstall the shortcuts.

### Installer options

```powershell
# Install and authenticate, but do not start the web server
.\install.ps1 -NoStart

# Install from a local checkout (no GitHub download)
.\install.ps1 -SourceDirectory . -NoStart
```

`-NonInteractive` fails instead of prompting when Python or a valid key is missing. `-SkipProfile` avoids modifying shell profiles. `-InstallDirectory` selects an alternative installation folder. A stable launcher is available at `<installation folder>\start.ps1`.

## Commands

Replace `Player#TAG` with your Riot ID. Use quotation marks when your name has spaces.

| Command | What it shows |
| --- | --- |
| `!rank "Player#TAG"` | Current rank, RR, last RR change, and peak rank |
| `!recent "Player#TAG"` | Last 5 competitive matches, map, agent, result, score, K/D/A, and HS% |
| `!today "Player#TAG"` | Today's wins, losses, draws, RR gained, RR lost, net RR, and individual games |
| `!last "Player#TAG"` | Your most recent competitive match |
| `!rr "Player#TAG"` | Last 5 RR changes and rank after each game |
| `!stats "Player#TAG"` | Up to 10 recent competitive games: win rate, K/D, HS%, and agents |
| `!profile "Player#TAG"` | Account level, region, platforms, and account ID |
| `!help` | List of available commands |
| `!career "Player#TAG"` | Alias for `!recent`, with the same options |
| `!kd "Player#TAG"` | K/D ratio and total kills, deaths, assists over up to 10 recent competitive matches |
| `!hs "Player#TAG"` | Headshot percentage and head/body/leg hit totals over up to 10 recent competitive matches |
| `!hours "Player#TAG" Clove` | Time on an agent within available recent matches across all queues |
| `!web` or `!serve` | Start the local browser client |

### Web client

```powershell
!web
# Equivalent command:
!serve
# Choose another port or skip opening a browser:
!web --port 9000 --no-browser
```

Open **http://127.0.0.1:8765** (or your chosen port). Keep the PowerShell window running; press **Ctrl+C** to stop the server. The web client supports rank, today, career, stats, K/D, headshots, agent hours, RR history, last match, and profile. Choose a view, enter your Riot ID, then click **Look up player**. No automatic polling occurs.

The server listens only on your own computer. It reads the same `HENRIK_API_KEY` used by the CLI; the key is never sent to the browser. This is a local personal client, not a public hosting server. Without PowerShell shortcuts, use `python valorant_tracker.py web` after setting the key in your environment.

### Agent hours and focused stats

```powershell
!kd "Player#TAG" --count 5
!hs "Player#TAG" --count 10
!hours "Player#TAG" Clove
!hours "Player#TAG" "KAY/O" --pages 10
!career "Player#TAG" --count 10 --mode all
```

`!hours` scans up to 30 recent matches by default (3 pages). `--pages` accepts 1 to 10, for a maximum of 100 available games. It sums completed match durations for the named agent, ignoring case. Each full page costs one API request. It shows the number of agent matches, the number of games scanned, and the date range. Missing durations are reported as partial data.

This measures match time in the available sample, **not lifetime hours**, time spent in menus, or precise active playtime during disconnects. An agent absent from the sample returns no matching games; check the spelling or expand the sample. `!kd` and `!hs` use competitive games, with `--count` from 1 to 10.

### Useful options

```powershell
# Show more recent matches (1 to 10)
!recent "Player#TAG" --count 10

# Include non-competitive queues
!recent "Player#TAG" --mode all
!last "Player#TAG" --mode all

# Use UTC instead of your computer's local date
!today "Player#TAG" --utc

# Review RR changes or a smaller performance sample
!rr "Player#TAG" --count 10
!stats "Player#TAG" --count 5

# Console account / explicit region
!rank "Player#TAG" --platform console --region na

# Export structured data
!today "Player#TAG" --json | Out-File today.json -Encoding utf8

# Help for one command
!today --help
```

Region is detected automatically. `--region` accepts `ap`, `eu`, `na`, `kr`, `br`, or `latam`. Platform defaults to `pc`. Profile does not need platform or region options.

## How today's RR is calculated

`!today` uses your computer's **local calendar date** and each game's **start time**. On a computer using India time, today runs from midnight to midnight IST. A game starting before midnight belongs to the previous day even if it finishes after midnight. Use `--utc` to group by UTC instead.

- **RR gained:** sum of positive `last_change` values in competitive RR history.
- **RR lost:** sum of negative changes, displayed as a negative number.
- **Net RR:** gained + lost. For example, `+30` and `-14` produce **+16 RR**.
- **Wins, losses, and draws:** taken from match results, joined to RR history by match ID. A zero-RR game is not automatically a draw.

RR changes come directly from the API; the tracker does not subtract current rank bars, which can reset when you promote. It does not add refund or bonus fields separately, avoiding double-counting. This summarizes reported match RR changes, not every possible account adjustment.

The API may return limited history or delay new games. The tracker fetches match-history pages until it reaches a previous day, with a safety limit of 100 matches. Missing RR stays unknown rather than being treated as zero, and partial totals are labelled. If RR history does not extend before today, it warns that earlier games may be missing. No activity means no games were found in available history, not a guarantee that the upstream service has updated.

## Understanding your stats

- **K/D/A:** kills / deaths / assists.
- **K/D:** total kills divided by total deaths; `--` when deaths are zero.
- **HS%:** head hits divided by head + body + leg hits, not the percentage of kills.
- **Win rate:** wins divided by games with known results, including draws in the denominator.
- `!stats` uses a recent sample, not lifetime statistics. HS% is calculated from total hits, not an average of each game's percentage.
- Missing values display `--`. Unavailable results are reported as unknown.

## Python commands and other shells

The `!` shortcuts are PowerShell functions. The Python CLI works on Windows, macOS, and Linux once `HENRIK_API_KEY` is set in your environment:

```sh
python valorant_tracker.py rank "Player#TAG"
python valorant_tracker.py recent "Player#TAG"
python valorant_tracker.py today "Player#TAG"
python valorant_tracker.py rr "Player#TAG"
python valorant_tracker.py stats "Player#TAG"
python valorant_tracker.py last "Player#TAG"
python valorant_tracker.py profile "Player#TAG"
```

`matches` and `recent` are equivalent. Optional virtual-environment installation adds the `valo` command:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\valo today "Player#TAG"
```

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `!today` is not recognized | Open a new PowerShell window, or run `. .\shortcuts.ps1` from the project folder. |
| Python is not recognized | Install Python 3.10+ and add it to PATH, then reopen PowerShell. |
| Missing API key | Rerun the installer, or set the key in the current process for direct Python use. |
| Key rejected / access denied | Verify the key and permissions in HenrikDev's dashboard. |
| Player not found | Check the full Riot ID, including tag, region, and platform. |
| No matches / outdated stats | Wait for the API to update; check your queue filter and platform. |
| Rate limit reached | Wait and retry. The CLI does not continuously poll or automatically retry. |
| Network error | Check connectivity. Requests time out after 20 seconds. |

To remove the installer-saved key, delete `%LOCALAPPDATA%\ValorantTracker\api-key.xml`. For a key previously saved as a user environment variable:

```powershell
[Environment]::SetEnvironmentVariable('HENRIK_API_KEY', $null, 'User')
Remove-Item Env:HENRIK_API_KEY -ErrorAction SilentlyContinue
```

## Development

```powershell
python -m unittest discover -s tests -v
```

Tests use mocked HTTP and sample match data. API schema: [HenrikDev OpenAPI](https://api.henrikdev.xyz/openapi.json).

Not affiliated with or endorsed by Riot Games. VALORANT and Riot Games are trademarks of Riot Games, Inc.

## Version 0.5.0 — Liquid glass

The web client now features frosted panels, soft violet and teal lighting, rounded controls, smooth hover and result transitions, and a loading indicator. Small screens use a horizontal view picker and stacked result cards. Animations respect your system reduced-motion preference.

To update an installed copy, rerun the one-command installer above. For a Git checkout, run `git pull`. Stop the old web server with Ctrl+C, run `!web` again, and refresh your browser.
