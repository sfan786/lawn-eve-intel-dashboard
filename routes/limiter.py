"""
Per-IP rate limiting for the expensive intel endpoints.

/api/local/scan, /api/chars/analyze and /api/fleet/analyze are unauthenticated
and each fans out to zKillboard — chars/analyze fires up to 25 parallel stats
requests per call. Without a cap, anyone who finds the URL can push the
deployment's IP into zKill's rate limits and take the intel panels down for
everyone.

Storage is in-process, so with N gunicorn workers the effective ceiling is N×
the configured limit. That is fine for the threat model here (accidental or
casual abuse); point `RATELIMIT_STORAGE_URI` at Redis if you ever need it exact.
"""

import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Applied per-endpoint via decorators — no global default, so ordinary
# dashboard polling is never throttled.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[],
    headers_enabled=True,
)

# Endpoints that fan out to zKillboard, one request per pilot.
INTEL_SCAN_LIMIT = os.environ.get("RATELIMIT_INTEL_SCAN", "20 per minute")
# The Gemini-backed summary endpoint — write-auth gated already, this bounds cost.
AI_LIMIT = os.environ.get("RATELIMIT_AI", "10 per minute")
