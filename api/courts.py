"""
api/courts.py
-------------
Vercel serverless function — GET /api/courts
Returns the full courts dataset from courts_data.json.
Falls back to a minimal response if the file is missing.
"""

from http.server import BaseHTTPRequestHandler
import json
import os

# Load courts data once at module level (cached across warm invocations)
_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'courts_data.json')

def _load_courts():
    try:
        with open(_DATA_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {"courts": [], "meta": {"error": "courts_data.json not found", "source": "api"}}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = _load_courts()
        # Tag the response so the frontend knows it came from the API
        if "meta" in data:
            data["meta"]["served_by"] = "vercel-api"

        body = json.dumps(data).encode()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress default Vercel noise
