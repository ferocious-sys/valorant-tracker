"""Loopback-only web client. API credentials never leave the Python server."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import webbrowser

from valorant_tracker import TrackerError, lookup, render, riot_id
from valorant_ui import HTML, CSS, JS

COMMANDS = {"rank", "matches", "today", "rr", "stats", "last", "profile", "kd", "hs", "hours"}


def query_args(body):
    if not isinstance(body, dict):
        raise ValueError("Expected a JSON object.")
    command = body.get("command", "rank")
    if not isinstance(command, str):
        raise ValueError("Invalid command.")
    command = {"career": "matches", "recent": "matches"}.get(command, command)
    if command not in COMMANDS:
        raise ValueError("Unknown tracker command.")
    player = body.get("player", "")
    if not isinstance(player, str) or len(player) > 120:
        raise ValueError("Enter a valid Riot ID.")
    try:
        player = riot_id(player)
    except argparse.ArgumentTypeError as exc:
        raise ValueError(str(exc)) from None
    region = body.get("region") or None
    platform = body.get("platform", "pc")
    if region not in (None, "ap", "na", "eu", "br", "latam", "kr") or platform not in ("pc", "console"):
        raise ValueError("Invalid region or platform.")
    count, pages = body.get("count", 10), body.get("pages", 3)
    if type(count) is not int or not 1 <= count <= 10 or type(pages) is not int or not 1 <= pages <= 10:
        raise ValueError("Count and pages must be integers from 1 to 10.")
    agent = body.get("agent", "")
    if not isinstance(agent, str) or len(agent) > 60 or (command == "hours" and not agent.strip()):
        raise ValueError("Enter an agent name for playtime.")
    utc = body.get("utc", False)
    if type(utc) is not bool:
        raise ValueError("UTC must be true or false.")
    return argparse.Namespace(command=command, player=player, region=region, platform=platform,
                              count=count, pages=pages, agent=agent, utc=utc, mode="competitive")


class TrackerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, lookup_fn=lookup):
        super().__init__(address, Handler)
        self.lookup_fn = lookup_fn
        self.query_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not write player data or request bodies to logs.

    def allowed(self):
        port = self.server.server_address[1]
        allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host") not in allowed_hosts:
            return False
        origin = self.headers.get("Origin")
        return not origin or origin in {f"http://{host}" for host in allowed_hosts}

    def send(self, status, payload, content_type="application/json; charset=utf-8"):
        raw = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self.allowed():
            return self.send(403, {"error": "Local access only."})
        assets = {"/": (HTML, "text/html; charset=utf-8"), "/style.css": (CSS, "text/css; charset=utf-8"),
                  "/app.js": (JS, "text/javascript; charset=utf-8")}
        if self.path not in assets:
            return self.send(404, {"error": "Not found."})
        content, mime = assets[self.path]
        self.send(200, content, mime)

    def do_OPTIONS(self):
        self.send(403, {"error": "Cross-origin requests are not supported."})

    def do_POST(self):
        if not self.allowed() or self.headers.get("X-Tracker-Request") != "1":
            return self.send(403, {"error": "Local application requests only."})
        if self.path != "/api/query":
            return self.send(404, {"error": "Not found."})
        if self.headers.get_content_type() != "application/json":
            return self.send(415, {"error": "Send JSON."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 4096:
                return self.send(413, {"error": "Request too large or empty."})
            self.connection.settimeout(10)
            body = json.loads(self.rfile.read(size))
            args = query_args(body)
        except (ValueError, TypeError, OSError):
            return self.send(400, {"error": "Invalid input. Check your Riot ID, agent, and options."})
        if not self.server.query_lock.acquire(blocking=False):
            return self.send(429, {"error": "Another lookup is running. Please wait."})
        try:
            data = self.server.lookup_fn(args)
            self.send(200, {"command": args.command, "data": data, "text": render(args.command, data)})
        except TrackerError as exc:
            self.send(502, {"error": str(exc)})
        except Exception:
            self.send(502, {"error": "Unable to read player data. Try again later."})
        finally:
            self.server.query_lock.release()


def serve(port=8765, open_browser=True):
    try:
        server = TrackerServer(("127.0.0.1", port))
    except OSError:
        raise TrackerError(f"Could not start on port {port}. Try --port {port + 1 if port < 65535 else 8765}.") from None
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"VALORANT Tracker: {url}\nLocal access only. Press Ctrl+C to stop.", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
    return 0
