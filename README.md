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

---

## Project Structure

```
lawn-eve-intel-dashboard/
├── app.py                   # Live entry point — registers ESI-backed blueprints
├── demo.py                  # Demo entry point — registers mock blueprints
├── config.py                # Alliance IDs, constellation IDs, upgrade data
├── db.py                    # SQLite persistence (ADM + activity snapshots)
├── esi_client.py            # ESI API wrapper with TTL caching
│
├── routes/                  # Live Flask blueprints
│   ├── system_state.py      # Shared SystemState singleton (populated at startup)
│   ├── config_routes.py     # /api/config, /api/status
│   ├── sov_routes.py        # /api/sovereignty, /api/campaigns
│   ├── activity_routes.py   # /api/activity
│   ├── zkill_routes.py      # /api/zkill/feed, /api/zkill/<id>
│   ├── history_routes.py    # /api/history/adm, /api/history/activity/heatmap
│   ├── intel_routes.py      # /api/intel/neighbors
│   ├── timer_routes.py      # /api/timers, /api/auth/check
│   └── static_routes.py     # / (serves Vite build or legacy fallback)
│
├── mock/                    # Demo mock blueprints (no ESI calls)
│   ├── mock_data.py         # All mock constants and builder functions
│   └── mock_*_routes.py     # One file per route group
│
├── frontend/                # Vite + React project
│   ├── package.json
│   ├── vite.config.js       # Proxy /api → Flask, build → static/dist/
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx          # Root component — state, fetching, tab nav
│       ├── styles/global.css
│       ├── data/mapData.js  # MAP_LAYOUT, MAP_LAYOUT_SUBWAY, MAP_CONNECTIONS
│       ├── utils/           # admHelpers, campaignHelpers, formatters, upgradeHelpers
│       └── components/      # 11 feature components + 3 common components
│
├── static/
│   ├── index.html           # Legacy CDN-React fallback (no build step required)
│   ├── map_data.js          # Source of truth for map layout data
│   └── dist/                # Vite build output (gitignored, served by Flask in prod)
│
├── tools/
│   └── esi_lookup.py        # CLI: resolve system/alliance/corp names to IDs
│
├── Dockerfile               # Multi-stage: Node (Vite build) → Python (gunicorn)
├── docker-compose.yml       # Production container config
├── nginx.conf               # Nginx reverse proxy config
├── deploy-oracle.sh         # First-time server setup script
├── update.sh                # Full rebuild deploy (no cache)
├── quick-update.sh          # Fast deploy (uses Docker layer cache)
├── setup.fish               # Local first-time setup (venv + npm install)
├── run_dev.fish             # Local dev launcher (Flask + Vite together)
└── requirements.txt
```

---

## Local Development

### First-Time Setup

```fish
git clone git@github.com:sfan786/lawn-eve-intel-dashboard.git
cd lawn-eve-intel-dashboard
./setup.fish
```

Creates the Python venv, installs pip deps, and runs `npm install` in `frontend/`.

### Running Locally

**Demo mode** — mock data, no ESI connection needed:
```fish
./run_dev.fish demo
# Flask mock API: http://localhost:5001
# Vite dev server: http://localhost:3000  ← open this
```

**Live mode** — real ESI data:
```fish
./run_dev.fish
# Flask:          http://localhost:5000
# Vite dev server: http://localhost:3000  ← open this
```

Or run each manually:
```fish
# Terminal 1
FLASK_PORT=5001 python demo.py    # or: python app.py

# Terminal 2
cd frontend && npm run dev:demo   # or: npm run dev
```

### npm Scripts

All run from `frontend/`:

| Script | What it does |
|--------|-------------|
| `npm run dev` | Vite dev server on :3000, proxies `/api` → Flask :5000 |
| `npm run dev:demo` | Vite dev server on :3000, proxies `/api` → Flask :5001 (demo) |
| `npm run build` | Build to `../static/dist/` |
| `npm run preview` | Serve the last build locally for inspection |
| `npm run build:serve` | Build then start `python app.py` |

---

## Production Deployment (Hetzner / Docker)

The production setup is:
- **Docker** — multi-stage build (Node builds Vite → Python runs gunicorn)
- **Gunicorn** — 2 workers serving Flask on port 5000 inside the container
- **Nginx** — reverse proxy on port 80/443, forwards to gunicorn
- **SQLite** — persisted to `./intel.db` on the host via Docker volume

### How the Docker build works

`docker-compose build` runs a two-stage Dockerfile:
1. **Node stage** — runs `npm ci && npm run build` inside `frontend/`, outputting to `static/dist/`
2. **Python stage** — installs pip deps, copies app code, overlays the Vite build output

The built frontend is served directly by Flask from `static/dist/`. No separate Node process runs in production.

---

### First-Time Server Setup

For a fresh Hetzner (or Oracle) server, see the full guide: **[DEPLOY-HETZNER.md](DEPLOY-HETZNER.md)**

**Quick version** — on the server as a non-root user:

```bash
# 1. Clone the repo
git clone git@github.com:sfan786/lawn-eve-intel-dashboard.git
cd lawn-eve-intel-dashboard

# 2. Run the deploy script (installs Docker, nginx, starts the app)
chmod +x deploy-oracle.sh
./deploy-oracle.sh

# 3. Set firewall rules
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Then access via `http://YOUR_SERVER_IP`.

---

### Setting the Timer Password in Production

The timer password defaults to `REDACTED`. Set it via environment variable before building:

```bash
# Option 1: export before running docker-compose
export TIMER_PASSWORD="your-secret-password"
docker-compose up -d --build

# Option 2: create a .env file in the project root (gitignored)
echo "TIMER_PASSWORD=your-secret-password" > .env
docker-compose up -d --build
```

`docker-compose.yml` reads `${TIMER_PASSWORD:-REDACTED}` — if the variable isn't set it falls back to the default.

---

### Deploying Updates

**After pushing code changes to GitHub, on the server:**

```bash
cd ~/lawn-eve-intel-dashboard

# Fast update — uses Docker layer cache, rebuilds only changed layers
./quick-update.sh

# OR: full clean rebuild (use after changing requirements.txt or package.json)
./update.sh
```

Both scripts:
1. `git pull origin main`
2. `docker-compose down`
3. Rebuild the Docker image (Node Vite build + Python)
4. `docker-compose up -d`
5. Poll the API health check until it responds

`quick-update.sh` uses Docker's layer cache — if you only changed Python/JSX files, the `npm ci` and `pip install` layers are skipped, making it fast. Use `update.sh` (no-cache) when you add/change dependencies.

---

### Server Management

```bash
cd ~/lawn-eve-intel-dashboard

# View live logs
docker-compose logs -f

# Restart without rebuild
docker-compose restart

# Stop
docker-compose down

# Check container status
docker-compose ps

# Check API health
curl http://localhost:5000/api/status
```

---

### SSL / Domain Setup

1. **Point DNS** — create an A record pointing `lawn.yourdomain.com` → your server IP

2. **Update nginx config** on the server:
   ```bash
   sudo nano /etc/nginx/sites-available/lawn-intel
   # Change: server_name _;
   # To:     server_name lawn.yourdomain.com;
   sudo nginx -t && sudo systemctl reload nginx
   ```

3. **Install SSL certificate**:
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d lawn.yourdomain.com
   # Choose "Redirect HTTP to HTTPS" when prompted
   ```

Certbot auto-renews via a systemd timer — no manual action needed after setup.

---

## Configuration

### Monitored systems (`config.py`)

```python
LAWN_CONSTELLATION_IDS = [
    20000414,  # 6-CBBM
    20000423,  # 2Q-8WA
]
FRIENDLY_ALLIANCES = ["Get Off My Lawn"]
FRIENDLY_CORPORATIONS = ["Astrum Mechanica", "LAWN Logistics"]
```

### Sovereignty upgrades (`config.py`)

`SYSTEM_UPGRADES` maps system names to installed iHub upgrades. Update manually when upgrades change in-game — ESI doesn't expose iHub fittings without SSO auth.

```python
SYSTEM_UPGRADES = {
    "1-KCSA": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 3}],
    ...
}
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_DEBUG` | `false` | Enable Flask debug/reloader (never true in production) |
| `FLASK_PORT` | `5000` | Port Flask listens on (overridden to 5001 for demo alongside live) |
| `TIMER_PASSWORD` | `REDACTED` | Password for timerboard add/delete |

---

## Entity Lookup Tool

Resolve names to numeric IDs for `config.py`:

```fish
source .venv/bin/activate.fish
python tools/esi_lookup.py alliance  "Get Off My Lawn"
python tools/esi_lookup.py system    "UDVW-O"
python tools/esi_lookup.py zkill     "Deepwater Hooligans"
```

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11, Flask, Flask Blueprints |
| Frontend | React 18, Vite 5 |
| Persistence | SQLite (WAL mode) |
| Production server | Gunicorn (2 workers) behind Nginx |
| Containerisation | Docker multi-stage build, Docker Compose |
| Data source | EVE ESI public API — no auth required |

---

## Logo

Drop your alliance logo at `static/logo.png` — the header picks it up automatically. Recommended: 40–48px height, transparent PNG.

---

## License

MIT
