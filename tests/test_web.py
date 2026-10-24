import http.client
import json
import threading
import unittest
from unittest.mock import Mock

from valorant_stats import agent_hours
from valorant_tracker import parser, fetch_recent_pages, TrackerError
from valorant_web import TrackerServer, query_args
from test_stats import game


class NewCommandTests(unittest.TestCase):
    def test_aliases(self):
        for command in ("career", "!career", "recent"):
            self.assertEqual(parser().parse_args([command, "Test#TAG"]).command, "matches")
        for command in ("web", "!web", "serve", "!serve"):
            self.assertEqual(parser().parse_args([command, "--no-browser"]).command, "web")

    def test_hours_filters_agent_deduplicates_and_reports_unknown_duration(self):
        first, second, third = game("1"), game("2"), game("3")
        first["metadata"]["game_length_in_ms"] = 3_600_000
        third["players"][0]["agent"]["name"] = "Jett"
        result = agent_hours([first, first, second, third], "me", "cLoVe")
        self.assertEqual((result["hours"], result["agent_matches"], result["scanned_matches"], result["missing_duration"]), (1, 2, 3, 1))
        self.assertEqual(agent_hours([first], "me", "Jett")["hours"], 0)

    def test_hours_pagination_stops_on_repeated_page(self):
        page = [game(str(i)) for i in range(10)]
        client = Mock()
        client.get.side_effect = [page, page]
        result = fetch_recent_pages(client, "ap", "pc", "me", 10)
        self.assertEqual(len(result), 10)
        self.assertEqual(client.get.call_count, 2)

    def test_web_input_validation(self):
        for body in ({"command": "web"}, {"command": []}, {"player": "Test#TAG", "count": True},
                     {"player": "Test#TAG", "pages": 100}, {"player": "Test#TAG", "command": "hours"},
                     {"player": "Test#TAG", "region": "invalid"}):
            with self.assertRaises(ValueError):
                query_args(body)
        self.assertEqual(query_args({"command": "career", "player": "Test#TAG"}).command, "matches")


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lookup = Mock(return_value={"account": {"name": "Test", "tag": "TAG", "puuid": "me", "region": "ap"}})
        cls.server = TrackerServer(("127.0.0.1", 0), cls.lookup)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method="GET", path="/", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_assets_and_no_file_access(self):
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertIn(b"VALORANT Tracker", body)
        self.assertIn("Content-Security-Policy", headers)
        for path in ("/valorant_tracker.py", "/../README.md", "/.env"):
            self.assertEqual(self.request(path=path)[0], 404)
        self.assertEqual(self.request(path="/app.js")[0], 200)

    def test_rejects_cross_origin_and_missing_header(self):
        body = json.dumps({"command": "profile", "player": "Test#TAG"})
        headers = {"Content-Type": "application/json", "X-Tracker-Request": "1", "Origin": "https://example.com"}
        self.assertEqual(self.request("POST", "/api/query", body, headers)[0], 403)
        self.assertEqual(self.request("POST", "/api/query", body, {"Content-Type": "application/json"})[0], 403)
        self.assertEqual(self.request(headers={"Host": "attacker.example"})[0], 403)

    def test_lookup_response_and_error_redaction(self):
        body = json.dumps({"command": "profile", "player": "Test#TAG"})
        headers = {"Content-Type": "application/json", "X-Tracker-Request": "1"}
        status, _, payload = self.request("POST", "/api/query", body, headers)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["data"]["account"]["name"], "Test")
        self.lookup.side_effect = RuntimeError("secret-should-not-leak")
        try:
            status, _, payload = self.request("POST", "/api/query", body, headers)
            self.assertEqual(status, 502)
            self.assertNotIn(b"secret-should-not-leak", payload)
        finally:
            self.lookup.side_effect = None


if __name__ == "__main__":
    unittest.main()
