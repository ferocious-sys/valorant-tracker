"""One-shot agent lock for the locally signed-in Windows VALORANT client."""
import base64
import json
import os
from pathlib import Path
import re
import ssl
import urllib.error
import urllib.request
from uuid import UUID

from valorant_tracker import TrackerError


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request_json(url, headers=None, method="GET", local=False):
    handlers = [NoRedirect(), urllib.request.ProxyHandler({})]
    if local:
        # Riot's loopback client uses a self-signed certificate. Never apply to remote hosts.
        if not re.fullmatch(r"https://127\.0\.0\.1:\d+/[a-z0-9/.-]+", url):
            raise TrackerError("Invalid local Riot client endpoint.")
        handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(url, headers=headers or {}, method=method,
                                     data=b"" if method == "POST" else None)
    try:
        with opener.open(request, timeout=10) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        if code == 404:
            raise TrackerError("No active agent-selection lobby found. Enter agent select and try again.") from None
        raise TrackerError(f"Riot/catalog request failed (HTTP {code}). The lobby may have changed or the agent may be unavailable.") from None
    except (OSError, ValueError):
        raise TrackerError("Could not read the Riot client or agent catalog. Check that VALORANT is running and try again.") from None


def player_state(match, subject):
    players = (match.get("AllyTeam") or {}).get("Players", [])
    if not players:
        players = [p for t in match.get("Teams", []) for p in t.get("Players", [])]
    player = next((p for p in players if p.get("Subject") == subject), None)
    if not player:
        raise TrackerError("Your player is not present in this selection lobby.")
    return player, players


def lock_current_agent(agent, dry_run=False, request=request_json, local_root=None):
    if local_root is None and os.name != "nt":
        raise TrackerError("In-game agent locking requires the Windows VALORANT client.")
    root_value = local_root or os.environ.get("LOCALAPPDATA")
    if not root_value:
        raise TrackerError("Could not locate the local Riot client.")
    root = Path(root_value)
    try:
        fields = (root / "Riot Games/Riot Client/Config/lockfile").read_text().strip().split(":")
        if len(fields) != 5 or fields[4] != "https" or not 1 <= int(fields[2]) <= 65535:
            raise ValueError()
        port, password = fields[2], fields[3]
    except (OSError, ValueError):
        raise TrackerError("Riot client lockfile unavailable. Start VALORANT and sign in first.") from None
    local_headers = {"Authorization": "Basic " + base64.b64encode(("riot:" + password).encode()).decode()}
    base = f"https://127.0.0.1:{port}"
    tokens = request(base + "/entitlements/v1/token", local_headers, local=True)
    sessions = request(base + "/product-session/v1/external-sessions", local_headers, local=True)
    session = next((s for s in sessions.values() if s.get("productId") == "valorant" and s.get("version")), None)
    if session is None:
        raise TrackerError("No running VALORANT session found.")
    try:
        log = (root / "VALORANT/Saved/Logs/ShooterGame.log").read_text(encoding="utf-8", errors="replace")
    except OSError:
        raise TrackerError("Could not read VALORANT's log to detect the game region.") from None
    hosts = re.findall(r"https://glz-(na|latam|br|eu|ap|kr)-1\.(na|pbe|eu|ap|kr)\.a\.pvp\.net(?=[/:\s]|$)", log)
    if not hosts:
        raise TrackerError("Game region not found. Wait for VALORANT to connect and try again.")
    region, shard = hosts[-1]
    remote = f"https://glz-{region}-1.{shard}.a.pvp.net"
    subject = str(UUID(tokens["subject"]))
    platform = base64.b64encode(json.dumps({"platformType": "PC", "platformOS": "Windows",
                                           "platformOSVersion": "10.0.19042.1.256.64bit", "platformChipset": "Unknown"}).encode()).decode()
    headers = {"Authorization": "Bearer " + tokens["accessToken"], "X-Riot-Entitlements-JWT": tokens["token"],
               "X-Riot-ClientPlatform": platform, "X-Riot-ClientVersion": session["version"]}
    catalog = request("https://valorant-api.com/v1/agents?isPlayableCharacter=true")
    normalize = lambda text: re.sub(r"[^a-z0-9]", "", text.casefold())
    selected = next((a for a in catalog["data"] if normalize(a["displayName"]) == normalize(agent)), None)
    if not selected:
        raise TrackerError("Unknown agent. Use the agent's full name, e.g. Clove, Jett, or KAY/O.")
    agent_id = str(UUID(selected["uuid"]))
    match_id = str(UUID(request(remote + f"/pregame/v1/players/{subject}", headers)["MatchID"]))
    path = remote + f"/pregame/v1/matches/{match_id}"
    match = request(path, headers)
    if match.get("PregameState") != "character_select_active":
        raise TrackerError("Agent selection is no longer active.")
    player, players = player_state(match, subject)
    if player.get("CharacterSelectionState") == "locked":
        if player.get("CharacterID") == agent_id:
            return {"agent": selected["displayName"], "status": "already locked", "dry_run": dry_run}
        raise TrackerError("You have already locked a different agent.")
    if any(p.get("Subject") != subject and p.get("CharacterID") == agent_id and p.get("CharacterSelectionState") == "locked" for p in players):
        raise TrackerError("A teammate has already locked this agent.")
    if dry_run:
        return {"agent": selected["displayName"], "status": "lobby ready; no selection changed", "dry_run": True}
    request(path + f"/select/{agent_id}", headers, method="POST")
    locked = request(path + f"/lock/{agent_id}", headers, method="POST")
    player, _ = player_state(locked, subject)
    if player.get("CharacterID") != agent_id or player.get("CharacterSelectionState") != "locked":
        raise TrackerError("Lock was not confirmed. Check the game; the agent may only be selected.")
    return {"agent": selected["displayName"], "status": "locked", "dry_run": False}
