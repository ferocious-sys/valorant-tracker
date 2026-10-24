from pathlib import Path
import tempfile
import unittest

from valorant_lock import lock_current_agent
from valorant_tracker import TrackerError

SUBJECT = "11111111-1111-4111-8111-111111111111"
AGENT = "22222222-2222-4222-8222-222222222222"
MATCH = "33333333-3333-4333-8333-333333333333"


class LockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        lockfile = root / "Riot Games/Riot Client/Config/lockfile"
        lockfile.parent.mkdir(parents=True)
        lockfile.write_text("Riot:123:12345:mock-password:https")
        log = root / "VALORANT/Saved/Logs/ShooterGame.log"
        log.parent.mkdir(parents=True)
        log.write_text("connected https://glz-ap-1.ap.a.pvp.net/pregame")
        self.calls = []
        self.player = {"Subject": SUBJECT, "CharacterID": "", "CharacterSelectionState": ""}
        self.lobby = {"PregameState": "character_select_active", "AllyTeam": {"Players": [self.player]}}

    def request(self, url, headers=None, method="GET", local=False):
        self.calls.append((url, method))
        if "/entitlements/" in url:
            self.assertTrue(local)
            return {"subject": SUBJECT, "accessToken": "mock-token", "token": "mock-entitlement"}
        if "/external-sessions" in url:
            return {"session": {"productId": "valorant", "version": "mock-version"}}
        if "valorant-api.com" in url:
            self.assertIsNone(headers)
            return {"data": [{"displayName": "Clove", "uuid": AGENT}]}
        self.assertTrue(url.startswith("https://glz-ap-1.ap.a.pvp.net/"))
        if "/players/" in url:
            return {"MatchID": MATCH}
        if "/lock/" in url:
            self.player.update(CharacterID=AGENT, CharacterSelectionState="locked")
        return self.lobby

    def test_one_shot_lock_is_confirmed(self):
        result = lock_current_agent("clove", request=self.request, local_root=self.temp.name)
        self.assertEqual(result["status"], "locked")
        writes = [url for url, method in self.calls if method == "POST"]
        self.assertEqual(len(writes), 2)
        self.assertIn("/select/", writes[0])
        self.assertIn("/lock/", writes[1])

    def test_dry_run_never_writes(self):
        result = lock_current_agent("Clove", dry_run=True, request=self.request, local_root=self.temp.name)
        self.assertTrue(result["dry_run"])
        self.assertFalse(any(method == "POST" for _, method in self.calls))

    def test_teammate_lock_prevents_writes(self):
        self.lobby["AllyTeam"]["Players"].append({"Subject": "other", "CharacterID": AGENT, "CharacterSelectionState": "locked"})
        with self.assertRaisesRegex(TrackerError, "teammate"):
            lock_current_agent("Clove", request=self.request, local_root=self.temp.name)
        self.assertFalse(any(method == "POST" for _, method in self.calls))

    def test_finished_lobby_prevents_writes(self):
        self.lobby["PregameState"] = "provisioned"
        with self.assertRaisesRegex(TrackerError, "no longer active"):
            lock_current_agent("Clove", request=self.request, local_root=self.temp.name)
        self.assertFalse(any(method == "POST" for _, method in self.calls))

    def test_existing_lock_is_not_changed(self):
        self.player.update(CharacterID=AGENT, CharacterSelectionState="locked")
        result = lock_current_agent("Clove", request=self.request, local_root=self.temp.name)
        self.assertEqual(result["status"], "already locked")
        self.assertFalse(any(method == "POST" for _, method in self.calls))

    def test_unknown_agent_prevents_writes(self):
        with self.assertRaisesRegex(TrackerError, "Unknown agent"):
            lock_current_agent("not-an-agent", request=self.request, local_root=self.temp.name)
        self.assertFalse(any(method == "POST" for _, method in self.calls))
