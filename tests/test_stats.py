import contextlib
from datetime import date, datetime, timezone, timedelta
import io
import json
import os
import unittest
from unittest.mock import Mock, patch

import valorant_tracker as cli
from valorant_stats import calendar_date, daily_summary, performance_summary


def game(match_id, started="2026-10-24T08:00:00Z", won=True, rounds=(13, 6), stats=None):
    return {
        "metadata": {"match_id": match_id, "started_at": started, "is_completed": True,
                     "map": {"name": "Ascent"}},
        "players": [{"puuid": "me", "team_id": "opaque-id", "agent": {"name": "Clove"},
                     "stats": stats or {"kills": 20, "deaths": 10, "assists": 5, "headshots": 1, "bodyshots": 9}}],
        "teams": [{"team_id": "other", "won": not won, "rounds": {"won": rounds[1], "lost": rounds[0]}},
                  {"team_id": "opaque-id", "won": won, "rounds": {"won": rounds[0], "lost": rounds[1]}}],
    }


def update(match_id, change, started="2026-10-24T08:00:00Z"):
    return {"match_id": match_id, "date": started, "last_change": change, "map": {"name": "Ascent"}}


class DailyTests(unittest.TestCase):
    def test_net_rr_and_results_join_by_id(self):
        history = [update("loss", -14), update("win", 30), update("win", 30), update("old", 25, "2026-10-23T23:00:00Z")]
        result = daily_summary(history, [game("win"), game("loss", won=False, rounds=(12, 14))], "me", date(2026, 10, 24), True)
        self.assertEqual((result["matches"], result["wins"], result["losses"]), (2, 1, 1))
        self.assertEqual((result["rr_gained"], result["rr_lost"], result["net_rr"]), (30, -14, 16))

    def test_zero_rr_is_not_a_draw_and_draw_can_gain_rr(self):
        result = daily_summary([update("loss", 0), update("draw", 3)],
                               [game("loss", won=False, rounds=(8, 13)), game("draw", won=False, rounds=(14, 14))],
                               "me", date(2026, 10, 24), True)
        self.assertEqual((result["losses"], result["draws"], result["net_rr"]), (1, 1, 3))

    def test_missing_rr_and_missing_result_are_explicit(self):
        result = daily_summary([update("missing-game", 22)], [game("missing-rr")], "me", date(2026, 10, 24), True)
        self.assertEqual(result["missing_rr"], 1)
        self.assertEqual(result["unknown_results"], 1)
        self.assertEqual(result["net_rr"], 22)

    def test_midnight_uses_timezone_conversion(self):
        self.assertEqual(calendar_date("2026-10-24T00:15:00+05:30", True), date(2026, 10, 23))
        self.assertEqual(calendar_date("2026-10-24T06:00:00Z"), datetime(2026, 10, 24, 6, tzinfo=timezone.utc).astimezone().date())
        local = Mock()
        local.astimezone.return_value = datetime(2026, 10, 25, 0, 15, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        with patch("valorant_stats.timestamp", return_value=local):
            self.assertEqual(calendar_date("2026-10-24T18:45:00Z"), date(2026, 10, 25))

    def test_empty_day(self):
        result = daily_summary([], [], "me", date(2026, 10, 24), True)
        self.assertEqual((result["matches"], result["net_rr"], result["missing_rr"]), (0, 0, 0))

    def test_stats_uses_total_hits_and_excludes_unfinished(self):
        first = game("1")
        second = game("2", won=False, rounds=(4, 13), stats={"kills": 10, "deaths": 20, "headshots": 9, "bodyshots": 81})
        incomplete = game("3")
        incomplete["metadata"]["is_completed"] = False
        result = performance_summary([first, second, incomplete], "me")
        self.assertEqual(result["matches"], 2)
        self.assertEqual(result["headshot_pct"], 10)
        self.assertEqual(result["kd"], 1)
        self.assertEqual(result["win_rate"], 50)

    def test_history_pagination_crosses_ten_matches(self):
        fake = Mock()
        today = datetime.now(timezone.utc).date()
        started = today.isoformat() + "T01:00:00Z"
        older = (today - timedelta(days=1)).isoformat() + "T01:00:00Z"
        histories = [update(str(i), 10, started) for i in range(11)] + [update("old", 10, older)]
        fake.get.side_effect = [{"history": histories}, [game(str(i), started) for i in range(10)], [game("10", started), game("old", older)]]
        result = cli.fetch_today(fake, "ap", "pc", "me", True)
        self.assertEqual(result["today"]["net_rr"], 110)
        self.assertEqual(result["today"]["matches"], 11)
        self.assertEqual(fake.get.call_args.kwargs["start"], 10)

    def test_recent_only_history_warns(self):
        started = datetime.now(timezone.utc).date().isoformat() + "T01:00:00Z"
        fake = Mock()
        fake.get.side_effect = [{"history": [update("1", 10, started)]}, [game("1", started)]]
        result = cli.fetch_today(fake, "ap", "pc", "me", True)
        self.assertTrue(any("earlier games may be missing" in n for n in result["notes"]))

    def test_new_command_json_outputs(self):
        account = {"name": "Test", "tag": "TAG", "puuid": "me", "region": "ap"}
        for command, response, expected_key in [("!rr", {"history": [update("1", 30)]}, "history"),
                                                ("!stats", [game("1")], "stats"), ("!last", [game("1")], "matches")]:
            with self.subTest(command=command), patch.dict(os.environ, {"HENRIK_API_KEY": "test"}), patch.object(cli.Client, "get", side_effect=[account, response]):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(cli.main([command, "Test#TAG", "--json"]), 0)
                self.assertIn(expected_key, json.loads(output.getvalue()))


if __name__ == "__main__":
    unittest.main()
