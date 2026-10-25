import argparse
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import valorant_tracker as v
from valorant_overlay import rank_entry


class TrackerTests(unittest.TestCase):
    def test_overlay_rank_uses_entered_account(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            def get(self, *path, **query):
                self.calls.append(path)
                if path[:3] == ("valorant", "v2", "account"):
                    return {"name": "Test", "tag": "TAG", "puuid": "player-id", "region": "ap"}
                return {"current": {"tier": {"name": "Gold 3"}, "rr": 42}}

        client = FakeClient()
        self.assertEqual(rank_entry(("Test", "TAG"), client),
                         {"name": "Test#TAG", "rank": "Gold 3", "rr": 42})
        self.assertEqual(client.calls[1], ("valorant", "v3", "by-puuid", "mmr", "ap", "pc", "player-id"))
        self.assertEqual(v.parser().parse_args(["!overlay", "Test#TAG"]).players, [("Test", "TAG")])

    def test_short_command_aliases(self):
        for alias, expected in [("!rank", "rank"), ("!recent", "matches"), ("recent", "matches")]:
            args = v.parser().parse_args([alias, "Test#TAG"])
            self.assertEqual(args.command, expected)

    def test_riot_id(self):
        self.assertEqual(v.riot_id(" My Name#ABC "), ("My Name", "ABC"))
        for value in ("abc", "#ABC", "abc#", "a#b#c"):
            with self.assertRaises(argparse.ArgumentTypeError):
                v.riot_id(value)

    def test_request_encoding_and_auth(self):
        seen = []
        def opener(request, timeout):
            seen.append(request)
            self.assertEqual(timeout, 20)
            return io.StringIO('{"data": {"name": "test"}}')
        self.assertEqual(v.Client("secret", opener).get("account", "A/B ?", "TAG"), {"name": "test"})
        self.assertEqual(seen[0].full_url, v.BASE_URL + "/account/A%2FB%20%3F/TAG")
        self.assertEqual(seen[0].get_header("Authorization"), "secret")

    def test_errors(self):
        for status in (401, 403, 404, 429, 500):
            def opener(request, timeout):
                raise HTTPError(request.full_url, status, "error", {"Retry-After": "60"}, None)
            with self.assertRaises(v.TrackerError) as caught:
                v.Client("secret", opener).get("test")
            self.assertNotIn("secret", str(caught.exception))
        with self.assertRaises(v.TrackerError):
            v.Client(" ")
        with self.assertRaises(v.TrackerError):
            v.Client("key", lambda *a, **k: io.StringIO("oops")).get("test")
        with self.assertRaises(v.TrackerError):
            v.Client("key", lambda *a, **k: io.StringIO('{"errors": []}')).get("test")

    def test_team_join_draw_and_zero_shots(self):
        match = {
            "metadata": {"is_completed": True, "map": {"name": "Ascent"}},
            "players": [{"puuid": "me", "team_id": "blue", "agent": {"name": "Jett"},
                         "stats": {"kills": 20, "deaths": 0, "assists": 4, "headshots": 2, "bodyshots": 6, "legshots": 0}}],
            "teams": [{"team_id": "red", "won": False, "rounds": {"won": 8, "lost": 13}},
                      {"team_id": "blue", "won": True, "rounds": {"won": 13, "lost": 8}}],
        }
        self.assertEqual(v.match_rows([match], "me")[0][3:], ["WIN", "13-8", "20/0/4", "25.0%"])
        match["teams"][1].update(won=False, rounds={"won": 14, "lost": 14})
        match["players"][0]["stats"] = {}
        self.assertEqual(v.match_rows([match], "me")[0][3], "DRAW")
        self.assertEqual(v.match_rows([match], "me")[0][-1], "--")
        self.assertEqual(v.match_rows([match], "someone-else"), [])

    def test_cli_json_and_region_detection(self):
        account = {"name": "Test", "tag": "TAG", "puuid": "id", "region": "ap"}
        with patch.dict(os.environ, {"HENRIK_API_KEY": "secret"}), patch.object(v.Client, "get", side_effect=[account, []]) as get:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = v.main(["matches", "Test#TAG", "--mode", "all", "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue()), {"account": account, "matches": []})
            self.assertEqual(get.call_args.args, ("valorant", "v4", "by-puuid", "matches", "ap", "pc", "id"))
            self.assertEqual(get.call_args.kwargs, {"size": 5})

    def test_missing_key_exit_and_terminal_controls(self):
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(v.main(["profile", "Test#TAG"]), 1)
        self.assertIn("HENRIK_API_KEY", err.getvalue())
        self.assertNotIn("\x1b", v.clean("evil\x1b[31m"))

    def test_outcome_and_rr_colors_are_applied_after_sanitizing(self):
        plain = v.clean_lines("Test#TAG\n2 matches | 1W / 1L / 0D | 0 unknown\n"
                              "RR gained: +18 | RR lost: -14 | Net RR: +4\n"
                              "STARTED  MAP  RESULT  RR\n"
                              "2026-10-25  Ascent  WIN  +18\n"
                              "2026-10-25  Haven  LOSS  -14\n"
                              "2026-10-25  Lotus  DRAW  +0")
        colored = v.colorize("today", plain)
        self.assertIn("\x1b[92mWIN\x1b[0m", colored)
        self.assertIn("\x1b[91m-14\x1b[0m", colored)
        self.assertIn("\x1b[93m+0\x1b[0m", colored)
        self.assertIn("\x1b[92m1W\x1b[0m", colored)
        for color in ("\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"):
            colored = colored.replace(color, "")
        self.assertEqual(colored, plain)
        self.assertNotIn("\x1b", v.clean_lines("evil\x1b[31m"))

    def test_terminal_color_respects_redirects_and_no_color(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(v.terminal_supports_color())
        with patch.dict(os.environ, {"NO_COLOR": ""}):
            self.assertFalse(v.terminal_supports_color())


if __name__ == "__main__":
    unittest.main()
