# EVE Alliance Intel Dashboard

Real-time sovereignty and intel monitoring for EVE Online nullsec space. Currently configured for **Get Off My Lawn [LAWN]** in **Perrigen Falls**, but the codebase is alliance/region agnostic — bootstrap a new deployment for any alliance in any region with `tools/bootstrap_deployment.py`.

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
- **DScan parser** — Paste EVE directional scan output for instant ship class breakdown and threat tier assessment (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL)
- **Local chat scanner** — Paste pilot names from local; resolves corp/alliance via ESI and classifies each as LAWN / FRIENDLY / UNKNOWN / UNRESOLVED with zKillboard links, risk ratings, and capital/covert role badges
- **Regional intel** — Neighbor region threat overview with per-system kill/jump spikes vs 7-day baseline and sov change history
- **Entosis command node board** — Dedicated `/entosis` page for live coordination during sov fights; pilots claim nodes with a callsign and advance status (unclaimed → running → contested → captured/lost)
- **Auto-refresh** — Live ESI data updates with thread-safe in-memory caching
- **Demo mode** — Full UI testing with mock data, no ESI access required

---

## Project Structure

```
lawn-eve-intel-dashboard/
├── app.py                   # Live entry point — registers ESI-backed blueprints
├── demo.py                  # Demo entry point — registers mock blueprints
├── config.py                # Thin re-export of the active deployment + game-wide constants
├── eve_constants.py         # Game-wide constants (ESI URLs, TTLs, upgrade catalog, planet types)
├── deployments/             # One module per (alliance, region) pair
│   ├── __init__.py          # Loader: picks ACTIVE from DEPLOYMENT env var
│   ├── lawn_perrigen.py     # Active deployment (LAWN in Perrigen Falls)
│   └── example.py           # Commented template for new deployments
├── db.py                    # SQLite persistence (deployment-scoped via deployment_id)
├── esi_client.py            # ESI API wrapper with TTL caching
│
├── routes/                  # Live Flask blueprints
│   ├── system_state.py      # Shared SystemState singleton (populated at startup)
│   ├── config_routes.py     # /api/config, /api/status
│   ├── sov_routes.py        # /api/sovereignty, /api/campaigns
│   ├── activity_routes.py   # /api/activity
│   ├── zkill_routes.py      # /api/zkill/feed, /api/zkill/<id>
│   ├── history_routes.py    # /api/history/adm, /api/history/activity/heatmap
│   ├── intel_routes.py      # /api/intel/neighbors, /api/intel/regional, /api/intel/sov_changes, /api/local/scan, /api/chars/analyze, /api/fleet/analyze
│   ├── entosis_routes.py    # /api/entosis/nodes (command node board)
│   ├── timer_routes.py      # /api/timers, /api/auth/check
│   └── static_routes.py     # / and /entosis (serves Vite SPA)
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
│       ├── pages/           # Full-page routes (EntosisPage.jsx — /entosis)
│       ├── styles/global.css
│       ├── utils/           # admHelpers, campaignHelpers, formatters, upgradeHelpers, mapHelpers
│       └── components/      # 14 feature components + 3 common components
│   (map layout is served by `/api/config` — no static map module)
│
├── static/
│   ├── index.html           # Legacy CDN-React fallback (no build step required)
│   ├── map_data.js          # Source of truth for map layout data
│   └── dist/                # Vite build output (gitignored, served by Flask in prod)
│
├── tools/
│   ├── esi_lookup.py        # CLI: resolve system/alliance/corp names to IDs
│   └── bootstrap_deployment.py  # CLI: scaffold a new deployment from ESI
│
├── Dockerfile               # Multi-stage: Node (Vite build) → Python (gunicorn)
├── docker-compose.yml       # Production container config
├── nginx.conf               # Nginx reverse proxy config
├── .env.example             # Config template — copy to .env on server
├── update.sh                # Manual full rebuild deploy (no cache)
├── quick-update.sh          # Manual fast deploy (uses Docker layer cache)
├── scripts/
│   └── server-setup.sh      # One-time setup for a fresh Debian/Ubuntu VPS
├── .github/workflows/
│   └── deploy.yml           # CD: auto-deploy to server on push to main
├── setup.sh / setup.fish    # Local first-time setup (venv + npm install)
├── run_dev.sh / run_dev.fish # Local dev launcher (Flask + Vite together)
├── requirements.txt
├── requirements-dev.txt     # Dev-only: pytest, pytest-flask, pytest-mock
├── pytest.ini               # pytest config (testpaths = tests/)
└── tests/                   # Python test suite (pytest)
```

---

## Local Development

### First-Time Setup

```bash
git clone git@github.com:sfan786/lawn-eve-intel-dashboard.git
cd lawn-eve-intel-dashboard
./setup.sh
```

Creates the Python venv, installs pip deps, and runs `npm install` in `frontend/`.

> fish users can run the `./setup.fish` / `./run_dev.fish` equivalents instead — the `.sh`
> scripts are the default for bash-based systems (most VPS hosts).

### Running Locally

**Demo mode** — mock data, no ESI connection needed:
```bash
./run_dev.sh demo
# Flask mock API: http://localhost:5001
# Vite dev server: http://localhost:3000  ← open this
```

**Live mode** — real ESI data:
```bash
./run_dev.sh
# Flask:          http://localhost:5000
# Vite dev server: http://localhost:3000  ← open this
```

Or run each manually:
```bash
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

## Production Deployment

The production setup is:
- **Docker** — multi-stage build (Node builds Vite → Python runs gunicorn)
- **Gunicorn** — 2 workers serving Flask on port 5000 inside the container
- **Nginx** — reverse proxy on port 80/443, forwards to gunicorn
- **SQLite** — persisted to `./intel.db` on the host via Docker volume

`docker-compose build` runs a two-stage Dockerfile:
1. **Node stage** — `npm ci && npm run build` inside `frontend/`, output to `static/dist/`
2. **Python stage** — installs pip deps, copies app code, overlays the Vite build

---

### Automated Deploys (GitHub Actions)

Every push to `main` automatically deploys to the server. One-time setup:

1. Add these 4 secrets to your repo under **Settings → Secrets → Actions**:

   | Secret | Value |
   |--------|-------|
   | `DEPLOY_HOST` | Server IP address |
   | `DEPLOY_USER` | SSH username (e.g. `root`) |
   | `DEPLOY_SSH_KEY` | Private key content (`cat ~/.ssh/id_ed25519`) |
   | `DEPLOY_PATH` | Repo path on server (e.g. `/root/lawn-eve-intel-dashboard`) |

2. On the server, make sure the repo is cloned (not a tarball extract):
   ```bash
   git remote -v   # should show origin → github
   git pull        # get latest scripts
   ```

After that, `git push` = deployed.

---

### Manual Updates

SSH into the server and run one of:

```bash
cd ~/lawn-eve-intel-dashboard

# Fast — uses Docker layer cache (use for code-only changes)
./quick-update.sh

# Full clean rebuild (use after changing requirements.txt or package.json)
./update.sh
```

Both scripts pull latest code, rebuild the image, restart the container, and poll the health check.

---

### First-Time Server Setup (new server)

For a fresh Debian/Ubuntu VPS (Hetzner, Oracle, etc.):

```bash
# Edit REPO_URL at the top of the script first, then:
bash scripts/server-setup.sh
```

This installs Docker, nginx, clones the repo, creates `.env` from the template, and starts the app.

---

### Configuration

Copy `.env.example` to `.env` on the server and edit it:

```bash
cp .env.example .env
nano .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOYMENT` | `lawn_perrigen` | Active deployment module under `deployments/` |
| `TIMER_PASSWORD` | _(unset)_ | Fallback password for write actions (timerboard, entosis, annotations, JBs) when EVE SSO is off. See [EVE SSO setup](#eve-sso-setup) and the env table below. |
| `FLASK_PORT` | `5000` | Port Flask listens on |
| `FLASK_DEBUG` | `false` | Never enable in production |

---

### Server Management

```bash
cd ~/lawn-eve-intel-dashboard

docker compose logs -f        # tail logs
docker compose restart        # restart without rebuild
docker compose down           # stop
docker compose ps             # container status
curl http://localhost:5000/api/status  # health check
```

---

### SSL / Domain Setup

1. **Point DNS** — create an A record: `lawn.yourdomain.com` → server IP

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
   ```

Certbot auto-renews via a systemd timer — no manual action needed after setup.

---

## Configuration

### Switching deployments

The dashboard ships with one deployment configured (`deployments/lawn_perrigen.py`). To run a different one:

```fish
DEPLOYMENT=other_deployment python app.py
```

To create a new deployment for any alliance/region, run the bootstrap tool:

```fish
python tools/bootstrap_deployment.py \
    --name some-alliance-region \
    --alliance "Some Alliance Name" \
    --region "Some Region" \
    --constellations "AAAA-A,BBBB-B" \
    --inherit-from deployments/lawn_perrigen.py    # copies friendlies / NEIGHBOR_ENTITIES
```

It resolves ESI IDs, walks the gate graph for the whole region, fetches PI data per primary system, generates an auto-layout for `MAP_LAYOUT` / `MAP_LAYOUT_SUBWAY`, and writes a complete deployment module to `deployments/<name>.py`. Hand-tune `MAP_LAYOUT` positions afterwards — auto-layout produces something usable but not pretty.

### Sovereignty upgrades

`SYSTEM_UPGRADES` in the active deployment module maps system names to installed iHub upgrades. Update manually when upgrades change in-game — ESI doesn't expose iHub fittings without SSO auth.

```python
# in deployments/lawn_perrigen.py
SYSTEM_UPGRADES = {
    "9BGY-6 I": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 3}],
    # ...
}
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOYMENT` | `lawn_perrigen` | Active deployment module under `deployments/` |
| `FLASK_DEBUG` | `false` | Enable Flask debug/reloader (never true in production) |
| `FLASK_PORT` | `5000` | Port Flask listens on (overridden to 5001 for demo alongside live) |
| `TIMER_PASSWORD` | _(unset)_ | Fallback password for write actions when SSO is off. If unset (and no SSO), writes are disabled (random per-process token). |
| `INTEL_DB_PATH` | `<repo>/intel.db` | Override SQLite database path |
| `EVE_CLIENT_ID` / `EVE_CLIENT_SECRET` / `EVE_CALLBACK_URL` | _(unset)_ | EVE SSO app credentials. All three enable "Log in with EVE" (see below). |
| `FLASK_SECRET_KEY` | _(random)_ | Signs the session cookie. **Set a persistent value in prod** or restarts log everyone out. |
| `AUTH_ALLOWED_ALLIANCE_IDS` | _(empty)_ | Extra alliance IDs allowed to write (primary alliance always allowed). Comma-separated. |
| `AUTH_ALLOWED_CHARACTER_IDS` | _(empty)_ | Specific character IDs allowed to write (FCs/guests outside the alliance). Comma-separated. |

### EVE SSO setup

When `EVE_CLIENT_ID`, `EVE_CLIENT_SECRET`, and `EVE_CALLBACK_URL` are all set,
write actions (timers, entosis claims, map annotations, jump bridges) are gated
by **"Log in with EVE"** instead of the shared password. A character may write if
its alliance is the deployment's primary alliance (or in `AUTH_ALLOWED_ALLIANCE_IDS`),
or its ID is in `AUTH_ALLOWED_CHARACTER_IDS`. Entosis claims are stamped with the
real logged-in character. `TIMER_PASSWORD` still works as a fallback.

1. Go to <https://developers.eveonline.com/applications> → **Create New Application**.
2. **Authentication Type:** Authentication Only (no scopes needed).
3. **Callback URL:** `https://<your-domain>/api/auth/sso/callback`.
   EVE allows only one callback per app — register a **separate app** for local
   dev with `http://localhost:5000/api/auth/sso/callback`.
4. Copy the **Client ID** and **Secret Key** into `.env`, set `EVE_CALLBACK_URL`
   to match, and set a persistent `FLASK_SECRET_KEY`
   (`python -c "import secrets; print(secrets.token_hex(32))"`).

---

## Entity Lookup Tool

Resolve names to numeric IDs for `config.py`:

```fish
source .venv/bin/activate.fish
python tools/esi_lookup.py alliance  "Get Off My Lawn"
python tools/esi_lookup.py system    "9BGY-6"
python tools/esi_lookup.py zkill     "Deepwater Hooligans"
```

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11, Flask, Flask Blueprints |
| Frontend | React 19, Vite 8 |
| Persistence | SQLite (WAL mode) |
| Production server | Gunicorn (2 workers) behind Nginx |
| Containerisation | Docker multi-stage build, Docker Compose |
| Data source | EVE ESI public API — no auth required |

---

## Logo

Drop your alliance logo at `static/logo.png` — the header picks it up automatically. Recommended: 40–48px height, transparent PNG.

---

## License

Licensed under the [GNU General Public License v3.0](LICENSE). You may use,
modify, and redistribute this software, but derivative works must also be
released under the GPL-3.0.
