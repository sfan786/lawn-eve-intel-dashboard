"""Mock traffic analytics for demo mode — synthetic, deterministic, no auth.

Live mode records real traffic (routes/analytics_routes.py) and gates the
summary behind write auth. Demo has neither traffic nor auth, so it fabricates
a plausible month of usage so the /analytics page can be exercised.
"""

import random
from datetime import UTC, datetime, timedelta

from flask import Blueprint, jsonify, request

mock_analytics_bp = Blueprint("mock_analytics", __name__)

_PAGES = [("/", 0.75), ("/entosis", 0.2), ("/analytics", 0.04), ("/other", 0.01)]
_API = [
    "/api/sovereignty", "/api/activity", "/api/campaigns", "/api/config",
    "/api/zkill/feed", "/api/history/adm", "/api/annotations", "/api/jumpbridges",
    "/api/entosis/nodes", "/api/timers",
]
_PILOTS = ["Kaelen Voss", "Mira Tenshun", "Bhaal Ruk", "Nyx Aldente", "Sable Quinn"]


@mock_analytics_bp.route("/api/analytics/auth")
def mock_analytics_auth():
    """Demo has no secrets to protect, so the page opens unlocked."""
    return jsonify({
        "configured": True,
        "authorized": True,
        "sso": False,
        "password": False,
        "character_name": None,
    })


@mock_analytics_bp.route("/api/analytics/summary")
def mock_analytics_summary():
    try:
        days = min(max(int(request.args.get("days", 30)), 1), 365)
    except ValueError:
        days = 30

    rng = random.Random(days)
    now = datetime.now(UTC)

    daily = []
    for i in range(days - 1, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        visitors = rng.randint(4, 18)
        page_views = visitors * rng.randint(2, 6)
        daily.append({
            "day": day,
            "visitors": visitors,
            "page_views": page_views,
            "api_calls": page_views * rng.randint(8, 20),
        })

    total_pages = sum(d["page_views"] for d in daily)
    # Prime time is EU/US evening; the curve is what an alliance tool looks like.
    weights = [max(0.2, 1 - abs(h - 19) / 9) for h in range(24)]
    wsum = sum(weights)

    return jsonify({
        "days": days,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totals": {
            "page_views": total_pages,
            "api_calls": sum(d["api_calls"] for d in daily),
            "unique_visitors": 34,
            "returning_visitors": 21,
            "active_days": len(daily),
            "bot_hits": rng.randint(200, 900),
            "peak_daily_visitors": max(d["visitors"] for d in daily),
        },
        "daily": daily,
        "hourly": [{"hour": h, "views": int(total_pages * weights[h] / wsum)} for h in range(24)],
        "top_pages": [{"path": p, "views": int(total_pages * share)} for p, share in _PAGES],
        "top_api": sorted(
            [{"path": p, "views": rng.randint(400, 9000)} for p in _API],
            key=lambda r: -r["views"],
        ),
        "visitor_frequency": [
            {"days_seen": 1, "visitors": 13},
            {"days_seen": 2, "visitors": 8},
            {"days_seen": 5, "visitors": 7},
            {"days_seen": 12, "visitors": 6},
        ],
        "pilots": [
            {"character_name": name, "days_seen": rng.randint(2, days),
             "last_seen": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
            for name in _PILOTS
        ],
    })
