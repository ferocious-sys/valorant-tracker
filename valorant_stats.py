"""Pure calculations for daily RR and recent competitive performance."""
from datetime import datetime, timezone


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("API timestamp has no time zone")
    return parsed


def calendar_date(value, utc=False):
    dt = timestamp(value)
    return (dt.astimezone(timezone.utc) if utc else dt.astimezone()).date()


def player_in(match, puuid):
    return next((p for p in match.get("players", []) if p.get("puuid") == puuid), None)


def outcome(match, puuid):
    player = player_in(match, puuid)
    if not player or not match.get("metadata", {}).get("is_completed"):
        return "UNKNOWN"
    team = next((t for t in match.get("teams", []) if t.get("team_id") == player.get("team_id")), None)
    if team is None:
        return "UNKNOWN"
    rounds = team.get("rounds") or {}
    if rounds.get("won") is not None and rounds.get("won") == rounds.get("lost"):
        return "DRAW"
    if team.get("won") is True:
        return "WIN"
    if team.get("won") is False:
        return "LOSS"
    return "UNKNOWN"


def daily_summary(history, matches, puuid, day, utc=False):
    # Join by match ID, never by list position or the sign of an RR change.
    updates = {h["match_id"]: h for h in history
               if h.get("queue_id") in (None, "competitive") and calendar_date(h["date"], utc) == day}
    games = {m["metadata"]["match_id"]: m for m in matches
             if m["metadata"].get("is_completed") and calendar_date(m["metadata"]["started_at"], utc) == day}
    counts = {"WIN": 0, "LOSS": 0, "DRAW": 0, "UNKNOWN": 0}
    rows = []
    for match_id in games.keys() | updates.keys():
        update, match = updates.get(match_id), games.get(match_id)
        result = outcome(match, puuid) if match else "UNKNOWN"
        counts[result] += 1
        meta = match["metadata"] if match else {}
        rows.append({
            "match_id": match_id,
            "date": update["date"] if update else meta["started_at"],
            "map": ((update or meta).get("map") or {}).get("name", "--"),
            "result": result,
            "rr_change": update.get("last_change") if update else None,
        })
    changes = [r["rr_change"] for r in rows if isinstance(r["rr_change"], (int, float))]
    return {
        "date": day.isoformat(), "timezone": "UTC" if utc else "system local time",
        "matches": len(rows), "wins": counts["WIN"], "losses": counts["LOSS"],
        "draws": counts["DRAW"], "unknown_results": counts["UNKNOWN"],
        "rr_gained": sum(c for c in changes if c > 0),
        "rr_lost": sum(c for c in changes if c < 0), "net_rr": sum(changes),
        "missing_rr": len(rows) - len(changes),
        "games": sorted(rows, key=lambda r: timestamp(r["date"]), reverse=True),
    }


def performance_summary(matches, puuid):
    games = [m for m in matches if m.get("metadata", {}).get("is_completed") and player_in(m, puuid)]
    counts = {"WIN": 0, "LOSS": 0, "DRAW": 0, "UNKNOWN": 0}
    totals = dict.fromkeys(("kills", "deaths", "assists", "headshots", "bodyshots", "legshots"), 0)
    agents = {}
    for match in games:
        counts[outcome(match, puuid)] += 1
        player = player_in(match, puuid)
        stats = player.get("stats") or {}
        for key in totals:
            totals[key] += stats.get(key, 0) or 0
        agent = (player.get("agent") or {}).get("name", "Unknown")
        agents[agent] = agents.get(agent, 0) + 1
    shots = totals["headshots"] + totals["bodyshots"] + totals["legshots"]
    known_results = counts["WIN"] + counts["LOSS"] + counts["DRAW"]
    return {
        "matches": len(games), "wins": counts["WIN"], "losses": counts["LOSS"],
        "draws": counts["DRAW"], "unknown_results": counts["UNKNOWN"],
        "win_rate": 100 * counts["WIN"] / known_results if known_results else None,
        "kills": totals["kills"], "deaths": totals["deaths"], "assists": totals["assists"],
        "kd": totals["kills"] / totals["deaths"] if totals["deaths"] else None,
        "headshot_pct": 100 * totals["headshots"] / shots if shots else None,
        "agents": dict(sorted(agents.items(), key=lambda item: (-item[1], item[0]))),
    }
