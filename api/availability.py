"""
api/availability.py
--------------------
Vercel serverless function — GET /api/availability?court_id=1&outdoor=true

Returns simulated time-slot availability for a given court and today's date.

Simulation logic (honest — no live booking data exists publicly for NYC courts):
  - Slots run 7 am – 9 pm in 1-hour increments
  - Booking probability varies by day of week and time of day
  - Results are deterministic: same court + date + hour always returns the same status
    (so refreshing the page doesn't flip slots randomly)
  - Past slots are marked "past"
  - Outdoor courts are marked "closed" before 7 am and after 9 pm
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import hashlib
import json


# ── Simulation constants ───────────────────────────────────────────────────────

SLOT_START = 7   # 7 am
SLOT_END   = 22  # up to but not including 10 pm (last slot = 9 pm)

# Baseline booking probability by weekday (0=Mon … 6=Sun)
BASE_PROB = {0: 0.40, 1: 0.38, 2: 0.42, 3: 0.45, 4: 0.55, 5: 0.75, 6: 0.70}

# Peak-hour adjustment added on top of BASE_PROB
def _peak_adjustment(hour: int) -> float:
    if 7 <= hour <= 9:    return +0.10   # morning rush
    if 17 <= hour <= 20:  return +0.20   # after-work peak
    if 12 <= hour <= 13:  return +0.05   # lunch
    if hour >= 21:        return -0.30   # late evening quiet
    return 0.0


def _slot_status(court_id: str, date_str: str, hour: int, is_outdoor: bool, current_hour: int) -> str:
    if hour < current_hour:
        return "past"

    # Outdoor courts don't have lights after 9 pm (simplified)
    if is_outdoor and hour >= 21:
        return "closed"

    date = datetime.strptime(date_str, "%Y-%m-%d")
    prob = BASE_PROB.get(date.weekday(), 0.50) + _peak_adjustment(hour)
    prob = max(0.05, min(0.95, prob))

    # Deterministic seed: same inputs → same output every time
    seed_str = f"{court_id}-{date_str}-{hour}"
    seed_int = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    val = (seed_int % 10_000) / 10_000  # value in [0, 1)

    return "booked" if val < prob else "available"


# ── Vercel handler ─────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params    = parse_qs(urlparse(self.path).query)
        court_id  = params.get("court_id",  ["1"])[0]
        is_outdoor = params.get("outdoor", ["true"])[0].lower() != "false"

        now          = datetime.now()
        today        = now.strftime("%Y-%m-%d")
        current_hour = now.hour

        slots = []
        for hour in range(SLOT_START, SLOT_END):
            status = _slot_status(court_id, today, hour, is_outdoor, current_hour)
            label  = f"{hour if hour <= 12 else hour - 12}{'am' if hour < 12 else 'pm'}"
            slots.append({"hour": hour, "label": label, "status": status})

        available_count = sum(1 for s in slots if s["status"] == "available")

        body = json.dumps({
            "court_id":       court_id,
            "date":           today,
            "slots":          slots,
            "available_count": available_count,
            "generated_at":   now.isoformat(),
            "disclaimer":     "Simulated — live court booking data is not yet publicly available for NYC courts"
        }).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def log_message(self, format, *args):
        pass
