"""
app.py — Zero-dependency Python HTTP server for Wumpus World Logic Agent
Uses only the standard library (http.server, json, pathlib).
No Flask, no pip install needed.
"""

import http.server
import json
import os
from pathlib import Path
from wumpus.world import World
from wumpus.kb import KnowledgeBase
from wumpus.agent import Agent

PORT = 5050
ROOT = Path(__file__).resolve().parent

# ── In-Memory Game State ─────────────────────────────────────────────────
_world: World | None = None
_kb: KnowledgeBase | None = None
_agent: Agent | None = None


def _snapshot() -> dict:
    if _world is None or _kb is None or _agent is None:
        return {"error": "No game in progress"}
    return {
        "world": {
            "rows": _world.rows,
            "cols": _world.cols,
            "grid": _world.grid,
        },
        "agent": _agent.to_dict(),
        "kb": {
            "inference_steps": _kb.inference_steps,
            "clauses": _kb.get_clause_strings(20),
            "known_pit": list(_kb.known_pit),
            "known_wumpus": list(_kb.known_wumpus),
        },
    }


# ── Handlers ──────────────────────────────────────────────────────────────

class WumpusHandler(http.server.SimpleHTTPRequestHandler):
    """Routes API calls and serves static files / templates."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    # ── Routing ──────────────────────────────────────────────────────────

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_template()
        elif self.path == "/api/state":
            self._json_response(_snapshot())
        elif self.path.startswith("/static/"):
            # Serve static files from static/ folder
            rel = self.path[len("/static/"):]
            file_path = ROOT / "static" / rel
            self._serve_file(file_path)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/new_game":
            self._handle_new_game()
        elif self.path == "/api/step":
            self._handle_step()
        else:
            self.send_error(404)

    # ── API logic ────────────────────────────────────────────────────────

    def _handle_new_game(self):
        global _world, _kb, _agent
        data = self._read_json()
        rows = max(2, min(10, int(data.get("rows", 4))))
        cols = max(2, min(10, int(data.get("cols", 4))))
        num_pits = max(1, min(rows * cols - 4, int(data.get("pits", 2))))

        _kb = KnowledgeBase()
        _world = World(rows, cols, num_pits)
        _agent = Agent(_world, _kb)
        _agent.cell_state["0_0"] = "safe"

        self._json_response({"status": "ok", "snapshot": _snapshot()})

    def _handle_step(self):
        global _agent
        if _agent is None:
            self._json_response({"error": "No game"}, 400)
            return
        can_continue = _agent.step()
        self._json_response({"can_continue": can_continue, "snapshot": _snapshot()})

    # ── Template serving (simple string replace for static URLs) ──────

    def _serve_template(self):
        tpl_path = ROOT / "templates" / "index.html"
        if not tpl_path.exists():
            self.send_error(404, "Template not found")
            return
        html = tpl_path.read_text(encoding="utf-8")
        # Replace Jinja2 url_for calls with plain paths
        html = html.replace("{{ url_for('static', filename='style.css') }}", "/static/style.css")
        html = html.replace("{{ url_for('static', filename='js/ui.js') }}", "/static/js/ui.js")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    # ── Helpers ──────────────────────────────────────────────────────────

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    def _json_response(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        ext = path.suffix.lower()
        ct_map = {
            ".html": "text/html",
            ".css":  "text/css",
            ".js":   "application/javascript",
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".svg":  "image/svg+xml",
            ".ico":  "image/x-icon",
            ".json": "application/json",
            ".webp": "image/webp",
        }
        content_type = ct_map.get(ext, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # Quieter logging
        pass


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = http.server.HTTPServer(("", PORT), WumpusHandler)
    print(f"🧠 Wumpus Logic Agent running at http://localhost:{PORT}")
    print(f"   Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
