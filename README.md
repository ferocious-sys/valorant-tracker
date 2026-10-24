# VALORANT Tracker CLI

Check your rank, recent games, and today's RR from your terminal.

```powershell
!rank "Player#TAG"
!recent "Player#TAG"
!today "Player#TAG"
```

Built with Python and the community [HenrikDev API](https://github.com/Henrik-3/unofficial-valorant-api). No Python runtime dependencies. Use it for your own account or players who have consented.

## Getting started on Windows

You need **Python 3.10 or newer**, PowerShell, and a HenrikDev API key. Git is needed only if you clone instead of downloading the repository ZIP.

### 1. Download the tracker

```powershell
git clone https://github.com/ferocious-sys/valorant-tracker.git
cd valorant-tracker
python --version
```

Alternatively, choose **Code > Download ZIP** on GitHub, extract it, and open PowerShell in the extracted folder.

### 2. Add your own API key

Create a key at the [HenrikDev dashboard](https://api.henrikdev.xyz/dashboard/). Follow the dashboard's account and application steps, then enter the key locally:

```powershell
$secret = Read-Host 'HenrikDev API key' -AsSecureString
$env:HENRIK_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
```

This sets the key for the current window. To let the shortcuts reuse it in future windows:

```powershell
[Environment]::SetEnvironmentVariable('HENRIK_API_KEY', $env:HENRIK_API_KEY, 'User')
```

The persistent key is stored in your Windows user environment, not an encrypted vault. Do not share it, put it in your source files, or commit it to GitHub. The tracker never prints it.

### 3. Enable the short commands

Run from the project folder:

```powershell
.\install-shortcuts.ps1
. .\shortcuts.ps1
```

You can now use the shortcuts from any folder. The installer adds a line to your PowerShell profile so future windows load them automatically. Keep the project in the same folder. If you move it, remove the old profile line and rerun the installer. To uninstall, remove the line ending in `# valorant-tracker shortcuts` from your profile (`notepad $PROFILE`).

If PowerShell blocks scripts, use the Python commands below; changing your execution policy is not required.

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
| `!instalock Clove` | Select and lock an agent in your current Windows agent-selection lobby |

### In-game agent locking

```powershell
# Check the lobby without changing your selection:
!instalock Clove --dry-run
# Select and lock once, in the current lobby:
!instalock Clove
```

Start VALORANT, sign in, and enter agent select first. This command acts on the currently signed-in account; it does not take a Riot ID. It checks that selection is active and the agent is not already locked by a teammate, then sends one select request and one lock request. It verifies the returned lock state. It does not wait for future games or keep running. If a request fails after selection, check the game before retrying.

This is an **unofficial client integration**, separate from HenrikDev. The [community endpoint documentation](https://valapidocs.techchrism.me/endpoint/lock-character) warns that instalocking may lead to account or API restrictions. Use at your own discretion. Live locking has not been tested against an actual game lobby; automated tests mock the requests.

It reads the running Riot client's local lockfile and game log, uses session tokens only in memory, and sends them only to the detected Riot game host. Tokens are not stored, printed, or sent to HenrikDev or the agent catalog. Only the local Riot client connection accepts its self-signed certificate; remote HTTPS remains verified. It needs Windows and a running game, but no HenrikDev key. Agent names come from [Valorant-API](https://valorant-api.com/). Agent locking is available only from the CLI, not the web client.

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
| Missing API key | Follow step 2. For direct Python use, set the key in the current process. |
| Key rejected / access denied | Verify the key and permissions in HenrikDev's dashboard. |
| Player not found | Check the full Riot ID, including tag, region, and platform. |
| No matches / outdated stats | Wait for the API to update; check your queue filter and platform. |
| Rate limit reached | Wait and retry. The CLI does not continuously poll or automatically retry. |
| Network error | Check connectivity. Requests time out after 20 seconds. |

To remove your saved key:

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
