"""A dependency-free CLI for the HenrikDev VALORANT API."""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from valorant_stats import agent_hours, calendar_date, daily_summary, performance_summary, timestamp

BASE_URL = "https://api.henrikdev.xyz"
COLORS = {"green": "\x1b[92m", "red": "\x1b[91m", "yellow": "\x1b[93m"}
RESET_COLOR = "\x1b[0m"


class TrackerError(Exception):
    pass


def riot_id(value):
    name, sep, tag = value.strip().rpartition("#")
    if not sep or not name.strip() or not tag.strip() or "#" in name:
        raise argparse.ArgumentTypeError('Use a quoted Riot ID: "Player#TAG"')
    return name.strip(), tag.strip()


def match_count(value):
    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Count must be an integer from 1 to 10")
    if not 1 <= count <= 10:
        raise argparse.ArgumentTypeError("Count must be between 1 and 10")
    return count


class Client:
    def __init__(self, key, opener=None):
        if not key or not key.strip():
            raise TrackerError("Set HENRIK_API_KEY first. Get a key at https://api.henrikdev.xyz/dashboard/")
        self.key = key.strip()
        self.opener = opener or urllib.request.urlopen

    def get(self, *segments, **query):
        path = "/".join(urllib.parse.quote(str(s), safe="") for s in segments)
        url = f"{BASE_URL}/{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers={
            "Authorization": self.key, "Accept": "application/json",
            "User-Agent": "valorant-tracker-cli/0.6.0",
        })
        try:
            with self.opener(request, timeout=20) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            messages = {
                400: "Invalid request. Check the Riot ID, region, and platform.",
                401: "API key rejected. Check HENRIK_API_KEY.",
                403: "Access denied. Check your API key permissions and player access.",
                404: "Player or data not found. Check the Riot ID and region.",
                429: "Rate limit reached. Wait before trying again.",
            }
            message = messages.get(exc.code, f"API unavailable (HTTP {exc.code}). Try again later.")
            retry = exc.headers.get("Retry-After") if exc.headers else None
            if exc.code == 429 and retry:
                message += f" Retry-After: {retry}."
            exc.close()
            raise TrackerError(message) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise TrackerError("Could not reach the API. Check your connection and try again.") from None
        except (ValueError, UnicodeError):
            raise TrackerError("The API returned invalid JSON. Try again later.") from None
        if not isinstance(payload, dict) or "data" not in payload or payload.get("errors"):
            raise TrackerError("The API returned an unexpected response.")
        return payload["data"]


def clean(value):
    # Remote player names must not be able to inject terminal control sequences.
    return "".join(c for c in str(value) if c.isprintable())


def terminal_supports_color():
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb" or not sys.stdout.isatty():
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError):
        return False


def color_value(value, color):
    return COLORS[color] + value + RESET_COLOR


def color_rr(value):
    amount = int(value)
    return color_value(value, "green" if amount > 0 else "red" if amount < 0 else "yellow")


def colorize(command, output):
    """Apply color only after untrusted text has been cleaned and columns aligned."""
    lines = output.split("\n")
    for index in range(1, len(lines)):
        line = lines[index]
        if command == "today":
            if " matches | " in line:
                line = re.sub(r"\b\d+[WLD]\b", lambda m: color_value(
                    m.group(), {"W": "green", "L": "red", "D": "yellow"}[m.group()[-1]]), line)
            elif line.startswith("RR gained:"):
                line = re.sub(r"(RR gained: |RR lost: |Net RR: )([+-]?\d+)",
                              lambda m: m.group(1) + color_rr(m.group(2)), line)
            elif re.match(r"^\d{4}-\d{2}-\d{2} ", line):
                line = re.sub(r"\b(WIN|LOSS|DRAW)\b", lambda m: color_value(
                    m.group(), {"WIN": "green", "LOSS": "red", "DRAW": "yellow"}[m.group()]), line)
                line = re.sub(r"(?<!\S)[+-]\d+(?!\S)", lambda m: color_rr(m.group()), line)
        elif command in ("matches", "last"):
            line = re.sub(r"\b(WIN|LOSS|DRAW)\b", lambda m: color_value(
                m.group(), {"WIN": "green", "LOSS": "red", "DRAW": "yellow"}[m.group()]), line)
        elif command == "rr":
            line = re.sub(r"(?<!\S)[+-]\d+(?!\S)", lambda m: color_rr(m.group()), line)
        elif command == "rank" and line.startswith("Last RR change"):
            line = re.sub(r"([+-]?\d+)\s*$", lambda m: color_rr(m.group(1)), line)
        elif command == "stats" and line.startswith("Record"):
            line = re.sub(r"\b\d+[WLD]\b", lambda m: color_value(
                m.group(), {"W": "green", "L": "red", "D": "yellow"}[m.group()[-1]]), line)
        lines[index] = line
    return "\n".join(lines)


def table(headers, rows):
    rows = [[clean(v) for v in row] for row in [headers, *rows]]
    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    return "\n".join("  ".join(v.ljust(widths[i]) for i, v in enumerate(row)).rstrip() for row in rows)


def match_rows(matches, puuid):
    rows = []
    for match in matches:
        meta = match.get("metadata") or {}
        player = next((p for p in match.get("players", []) if p.get("puuid") == puuid), None)
        if player is None:
            continue
        stats = player.get("stats") or {}
        team = next((t for t in match.get("teams", []) if t.get("team_id") == player.get("team_id")), {})
        rounds = team.get("rounds") or {}
        won, lost = rounds.get("won"), rounds.get("lost")
        result = "--"
        if meta.get("is_completed") and team:
            if won is not None and won == lost:
                result = "DRAW"
            elif team.get("won") is True:
                result = "WIN"
            elif team.get("won") is False:
                result = "LOSS"
        shots = sum(stats.get(k, 0) or 0 for k in ("headshots", "bodyshots", "legshots"))
        hs = f"{100 * (stats.get('headshots', 0) or 0) / shots:.1f}%" if shots else "--"
        rows.append([
            meta.get("started_at", "--"), (meta.get("map") or {}).get("name", "--"),
            (player.get("agent") or {}).get("name", "--"), result,
            f"{won}-{lost}" if won is not None and lost is not None else "--",
            "/".join(str(stats.get(k, "--")) for k in ("kills", "deaths", "assists")), hs,
        ])
    return rows


def render(command, data):
    account = data["account"]
    heading = f"{account['name']}#{account['tag']}"
    if command == "hours":
        h = data["hours"]
        lines = [heading, f"{h['agent']}: {h['hours']:.2f} hours ({h['minutes']:.0f} minutes)",
                 f"{h['agent_matches']} agent matches in {h['scanned_matches']} available recent matches.", h["scope"]]
        if h["oldest_match"]:
            lines.append(f"Sample: {h['oldest_match']} to {h['newest_match']}")
        if h["missing_duration"]:
            lines.append(f"Duration missing for {h['missing_duration']} matches; hours are partial.")
        if not h["agent_matches"]:
            lines.append("No matches with this agent in the sample. Check the spelling or increase --pages.")
        return "\n".join(lines)
    if command in ("kd", "hs"):
        s = data["stats"]
        if command == "kd":
            value = f"{s['kd']:.2f}" if s["kd"] is not None else "-- (zero deaths)"
            line = f"K/D: {value} | {s['kills']} kills / {s['deaths']} deaths / {s['assists']} assists"
        else:
            value = f"{s['headshot_pct']:.1f}%" if s["headshot_pct"] is not None else "-- (no hits)"
            line = f"HS: {value} | Head {s['headshots']} / Body {s['bodyshots']} / Legs {s['legshots']}"
        return f"{heading}\n{line}\nSample: {s['matches']} recent completed competitive matches."
    if command == "today":
        summary = data["today"]
        lines = [heading, f"Today: {summary['date']} ({summary['timezone']})",
                 f"{summary['matches']} matches | {summary['wins']}W / {summary['losses']}L / {summary['draws']}D | {summary['unknown_results']} unknown",
                 f"RR gained: +{summary['rr_gained']} | RR lost: {summary['rr_lost']} | Net RR: {summary['net_rr']:+}"]
        if summary["missing_rr"]:
            lines.append(f"RR unavailable for {summary['missing_rr']} matches; net RR is partial.")
        if summary["games"]:
            lines.append(table(["STARTED", "MAP", "RESULT", "RR"], [
                [local_time(g["date"], data["utc"]), g["map"], g["result"],
                 f"{g['rr_change']:+}" if g["rr_change"] is not None else "--"] for g in summary["games"]]))
        else:
            lines.append("No competitive matches found today.")
        lines.extend("Note: " + note for note in data.get("notes", []))
        return "\n".join(lines)
    if command == "rr":
        rows = [[local_time(h["date"], data["utc"]), (h.get("map") or {}).get("name", "--"),
                 f"{h['last_change']:+}", (h.get("tier") or {}).get("name", "--"), h.get("rr", "--")]
                for h in data["history"]]
        return heading + "\nRR history (" + ("UTC" if data["utc"] else "local time") + ")\n" + (
            table(["STARTED", "MAP", "CHANGE", "RANK AFTER", "RR AFTER"], rows) if rows else "No RR history available.")
    if command == "stats":
        s = data["stats"]
        return heading + "\nRecent competitive performance\n" + table(["FIELD", "VALUE"], [
            ["Matches", s["matches"]], ["Record", f"{s['wins']}W / {s['losses']}L / {s['draws']}D"],
            ["Unknown results", s["unknown_results"]],
            ["Win rate", f"{s['win_rate']:.1f}%" if s["win_rate"] is not None else "--"],
            ["Total K/D/A", f"{s['kills']}/{s['deaths']}/{s['assists']}"],
            ["K/D", f"{s['kd']:.2f}" if s["kd"] is not None else "--"],
            ["HS%", f"{s['headshot_pct']:.1f}%" if s["headshot_pct"] is not None else "--"],
            ["Agents", ", ".join(f"{name} ({count})" for name, count in s["agents"].items()) or "--"],
        ])
    if command == "profile":
        return heading + "\n" + table(["FIELD", "VALUE"], [
            ["Level", account.get("account_level", "--")],
            ["Region", account.get("region", "--")],
            ["Platforms", ", ".join(account.get("platforms", []))],
            ["PUUID", account["puuid"]], ["Updated", account.get("updated_at", "--")],
        ])
    if command == "rank":
        rank = data["rank"]
        current = rank.get("current") or {}
        peak = rank.get("peak") or {}
        return heading + "\n" + table(["FIELD", "VALUE"], [
            ["Rank", (current.get("tier") or {}).get("name", "Unrated")],
            ["RR", current.get("rr", "--")], ["Last RR change", current.get("last_change", "--")],
            ["Peak", (peak.get("tier") or {}).get("name", "--")],
        ])
    rows = match_rows(data["matches"], account["puuid"])
    return heading + "\n" + (table(["STARTED (UTC)", "MAP", "AGENT", "RESULT", "ROUNDS", "K/D/A", "HS%"], rows) if rows else "No matches found for this player and filter.")


def local_time(value, utc=False):
    dt = timestamp(value)
    dt = dt.astimezone(timezone.utc) if utc else dt.astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")


def fetch_today(client, region, platform, puuid, utc=False):
    now = datetime.now(timezone.utc) if utc else datetime.now().astimezone()
    day = now.date()
    history = fetch_history(client, region, platform, puuid)
    matches, seen, notes = [], set(), []
    # At most 10 pages to keep a single invocation within normal API limits.
    for page_number in range(10):
        page = client.get("valorant", "v4", "by-puuid", "matches", region, platform, puuid,
                          mode="competitive", size=10, start=page_number * 10)
        if not isinstance(page, list):
            raise TrackerError("The API returned invalid match history.")
        new = [m for m in page if m["metadata"]["match_id"] not in seen]
        matches.extend(new)
        seen.update(m["metadata"]["match_id"] for m in new)
        if len(page) < 10 or any(calendar_date(m["metadata"]["started_at"], utc) < day for m in page):
            break
        if not new:
            notes.append("Match pagination repeated; results may be incomplete.")
            break
    else:
        notes.append("Stopped after 100 recent matches; results may be incomplete.")
    if history and not any(calendar_date(h["date"], utc) < day for h in history):
        notes.append("Available RR history does not extend before today; earlier games may be missing.")
    notes.append("Uses available API history and match start dates; recently finished games may take time to appear.")
    return {"today": daily_summary(history, matches, puuid, day, utc), "utc": utc, "notes": notes}


def fetch_history(client, region, platform, puuid):
    data = client.get("valorant", "v2", "by-puuid", "mmr-history", region, platform, puuid)
    if not isinstance(data, dict) or not isinstance(data.get("history"), list):
        raise TrackerError("The API returned invalid RR history.")
    # Deduplicate updates before totals or display.
    unique = {h["match_id"]: h for h in data["history"]}
    return sorted(unique.values(), key=lambda h: timestamp(h["date"]), reverse=True)


def fetch_recent_pages(client, region, platform, puuid, pages):
    matches, seen = [], set()
    for index in range(pages):
        page = client.get("valorant", "v4", "by-puuid", "matches", region, platform, puuid, size=10, start=index * 10)
        if not isinstance(page, list):
            raise TrackerError("The API returned invalid match history.")
        new = [m for m in page if m["metadata"]["match_id"] not in seen]
        matches.extend(new)
        seen.update(m["metadata"]["match_id"] for m in new)
        if len(page) < 10 or not new:
            break
    return matches


def port_number(value):
    try:
        port = int(value)
        if 1 <= port <= 65535:
            return port
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("Port must be between 1 and 65535")


def parser():
    p = argparse.ArgumentParser(description="VALORANT player tracker powered by HenrikDev. Use for yourself or consenting players.")
    p.add_argument("--version", action="version", version="%(prog)s 0.6.0")
    commands = p.add_subparsers(dest="command", required=True)
    for command, description in [("profile", "Account details"), ("rank", "Current rank and peak"),
                                 ("matches", "Recent matches and personal performance"),
                                 ("today", "Today's wins, losses, and net RR"), ("rr", "Recent RR changes"),
                                 ("stats", "Recent competitive performance summary"), ("last", "Your latest match"),
                                 ("kd", "Recent kill/death ratio"), ("hs", "Recent headshot percentage"),
                                 ("hours", "Recent playtime on an agent (not lifetime)")]:
        aliases = {"profile": ["!profile"], "rank": ["!rank"], "matches": ["recent", "!recent", "career", "!career"],
                   "today": ["!today"], "rr": ["!rr"], "stats": ["!stats"], "last": ["!last"],
                   "kd": ["!kd"], "hs": ["!hs"], "hours": ["!hours"]}
        sub = commands.add_parser(command, aliases=aliases[command], help=description)
        sub.set_defaults(command=command)
        sub.add_argument("player", type=riot_id, help='Riot ID, e.g. "Player#TAG"')
        sub.add_argument("--json", action="store_true", help="Output structured JSON")
        if command != "profile":
            sub.add_argument("--region", choices=["eu", "na", "ap", "kr", "br", "latam"], help="Defaults to account region")
            sub.add_argument("--platform", choices=["pc", "console"], default="pc")
        if command in ("matches", "rr", "stats", "kd", "hs"):
            sub.add_argument("--count", type=match_count, default=10 if command in ("stats", "kd", "hs") else 5)
        if command == "hours":
            sub.add_argument("agent", help='Agent name, e.g. Clove or "KAY/O"')
            sub.add_argument("--pages", type=match_count, default=3, help="Scan 1-10 pages of 10 matches (default: 3)")
        if command in ("matches", "last"):
            sub.add_argument("--mode", default="competitive", help="Queue filter (default: competitive); use all for all queues")
        if command in ("today", "rr"):
            sub.add_argument("--utc", action="store_true", help="Use UTC instead of your computer's local time")
    web = commands.add_parser("web", aliases=["!web", "serve", "!serve"], help="Serve the local web client")
    web.set_defaults(command="web")
    web.add_argument("--port", type=port_number, default=8765)
    web.add_argument("--no-browser", action="store_true", help="Start without opening a browser")
    overlay = commands.add_parser("overlay", aliases=["!overlay"], help="Show entered player ranks in a desktop overlay (F8 toggles)")
    overlay.set_defaults(command="overlay")
    overlay.add_argument("players", type=riot_id, nargs="+", metavar="Player#TAG",
                         help="Your Riot ID and any other players who opted in (up to 5)")
    return p


def lookup(args, client=None):
    client = client or Client(os.environ.get("HENRIK_API_KEY"))
    name, tag = args.player
    account = client.get("valorant", "v2", "account", name, tag)
    if not isinstance(account, dict) or not all(account.get(k) for k in ("name", "tag", "puuid", "region")):
        raise TrackerError("The API returned incomplete account data.")
    data = {"account": account}
    if args.command != "profile":
        region = args.region or account["region"]
        if args.command == "rank":
            data["rank"] = client.get("valorant", "v3", "by-puuid", "mmr", region, args.platform, account["puuid"])
            if not isinstance(data["rank"], dict):
                raise TrackerError("No ranked data available.")
        elif args.command == "today":
            data.update(fetch_today(client, region, args.platform, account["puuid"], args.utc))
        elif args.command == "rr":
            data.update(history=fetch_history(client, region, args.platform, account["puuid"])[:args.count], utc=args.utc)
        elif args.command == "hours":
            games = fetch_recent_pages(client, region, args.platform, account["puuid"], args.pages)
            data["hours"] = agent_hours(games, account["puuid"], args.agent)
        else:
            query = {"size": 1 if args.command == "last" else args.count}
            mode = getattr(args, "mode", "competitive")
            if mode != "all":
                query["mode"] = mode
            data["matches"] = client.get("valorant", "v4", "by-puuid", "matches", region, args.platform, account["puuid"], **query)
            if not isinstance(data["matches"], list):
                raise TrackerError("No match data available.")
            if args.command in ("stats", "kd", "hs"):
                data["stats"] = performance_summary(data["matches"], account["puuid"])
    return data


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "web":
            from valorant_web import serve
            return serve(args.port, not args.no_browser)
        if args.command == "overlay":
            if len(args.players) > 5:
                raise TrackerError("The overlay supports up to 5 entered players.")
            from valorant_overlay import run
            return run(args.players)
        data = lookup(args)
        if args.json:
            output = json.dumps(data, indent=2, ensure_ascii=True)
        else:
            output = clean_lines(render(args.command, data))
            if terminal_supports_color():
                output = colorize(args.command, output)
        print(output)
        return 0
    except TrackerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (KeyError, TypeError, ValueError, AttributeError):
        print("Error: The API returned incomplete or malformed player data. Try again later.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 0


def clean_lines(text):
    return "\n".join(clean(line) for line in text.split("\n"))


if __name__ == "__main__":
    # Use the canonical module so the web server shares the same exception types.
    from valorant_tracker import main as entrypoint
    sys.exit(entrypoint())
