"""A dependency-free CLI for the HenrikDev VALORANT API."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from valorant_stats import calendar_date, daily_summary, performance_summary, timestamp

BASE_URL = "https://api.henrikdev.xyz"


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
            "User-Agent": "valorant-tracker-cli/0.2.0",
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


def parser():
    p = argparse.ArgumentParser(description="VALORANT player tracker powered by HenrikDev. Use for yourself or consenting players.")
    p.add_argument("--version", action="version", version="%(prog)s 0.2.0")
    commands = p.add_subparsers(dest="command", required=True)
    for command, description in [("profile", "Account details"), ("rank", "Current rank and peak"),
                                 ("matches", "Recent matches and personal performance"),
                                 ("today", "Today's wins, losses, and net RR"), ("rr", "Recent RR changes"),
                                 ("stats", "Recent competitive performance summary"), ("last", "Your latest match")]:
        aliases = {"profile": ["!profile"], "rank": ["!rank"], "matches": ["recent", "!recent"],
                   "today": ["!today"], "rr": ["!rr"], "stats": ["!stats"], "last": ["!last"]}
        sub = commands.add_parser(command, aliases=aliases[command], help=description)
        sub.set_defaults(command=command)
        sub.add_argument("player", type=riot_id, help='Riot ID, e.g. "Player#TAG"')
        sub.add_argument("--json", action="store_true", help="Output structured JSON")
        if command != "profile":
            sub.add_argument("--region", choices=["eu", "na", "ap", "kr", "br", "latam"], help="Defaults to account region")
            sub.add_argument("--platform", choices=["pc", "console"], default="pc")
        if command in ("matches", "rr", "stats"):
            sub.add_argument("--count", type=match_count, default=10 if command == "stats" else 5)
        if command in ("matches", "last"):
            sub.add_argument("--mode", default="competitive", help="Queue filter (default: competitive); use all for all queues")
        if command in ("today", "rr"):
            sub.add_argument("--utc", action="store_true", help="Use UTC instead of your computer's local time")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        client = Client(os.environ.get("HENRIK_API_KEY"))
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
            else:
                query = {"size": 1 if args.command == "last" else args.count}
                mode = getattr(args, "mode", "competitive")
                if mode != "all":
                    query["mode"] = mode
                data["matches"] = client.get("valorant", "v4", "by-puuid", "matches", region, args.platform, account["puuid"], **query)
                if not isinstance(data["matches"], list):
                    raise TrackerError("No match data available.")
                if args.command == "stats":
                    data["stats"] = performance_summary(data["matches"], account["puuid"])
        print(json.dumps(data, indent=2, ensure_ascii=True) if args.json else clean_lines(render(args.command, data)))
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
    sys.exit(main())
