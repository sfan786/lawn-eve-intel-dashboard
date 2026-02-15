# LAWN Eve Intel Dashboard

Real-time sovereignty and intel monitoring for EVE Online nullsec space. Built for **Get Off My Lawn [LAWN]** alliance in The Kalevala Expanse.

## Features

- **Sovereignty map** — Interactive SVG constellation map (traditional + subway modes) with gate connections, neighbor systems, and visual indicators for PVP danger, ratting activity, and grinding priority
- **ADM trend tracking** — SQLite-backed historical ADM data with sparkline charts and 24h change indicators
- **System status table** — All monitored systems with kill stats, jump traffic, sovereignty holder, upgrade badges, and activity bars
- **Campaign alerts** — Pulsing warnings for active sovereignty contests with countdown timers and progress bars
- **Kill feed** — Regional zKillboard integration with LAWN space highlighting and attacker details
- **Neighbor threat profiling** — Ship doctrine analysis, timezone heatmaps, and threat scoring for border-adjacent alliances
- **Activity heatmap** — Per-system hourly activity grid showing safe grinding hours vs danger hours
- **Timerboard** — Manual structure timer tracking with password-protected add/delete
- **Sov upgrade tracking** — Manual iHub upgrade display (military/industry/strategic) per LAWN system
- **Auto-refresh** — Live ESI data updates with in-memory caching
- **Demo mode** — Full UI testing with mock data, no ESI access required

## Quick Start

```bash
git clone git@github.com:sfan786/lawn-eve-intel-dashboard.git
cd lawn-eve-intel-dashboard
python -m venv .venv
source .venv/bin/activate      # or activate.fish for fish shell
pip install -r requirements.txt

# Demo mode (mock data)
python demo.py

# Live mode (ESI)
python app.py
```

Open http://localhost:5000

## Configuration

Edit `config.py` to set your monitored constellations and friendly alliances:

```python
MONITORED_CONSTELLATION_IDS = [
    20000414,  # 6-CBBM
    20000423,  # 2Q-8WA
]
FRIENDLY_ALLIANCES = ["Get Off My Lawn"]
FRIENDLY_CORPORATIONS = ["Astrum Mechanica", "LAWN Logistics"]
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_DEBUG` | `false` | Enable Flask debug mode (set to `true` for development) |
| `TIMER_PASSWORD` | `REDACTED` | Password for timerboard add/delete operations |

## Logo

Drop your alliance logo at `static/logo.png` — the header will pick it up automatically. Recommended size: 40-48px height, transparent background PNG.

## Tech Stack

- Python 3 / Flask (backend)
- SQLite with WAL mode (persistence)
- React 18 via CDN (frontend — no build step)
- EVE ESI public API (no auth required)

## License

MIT
