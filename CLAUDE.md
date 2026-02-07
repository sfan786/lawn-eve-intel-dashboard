# CLAUDE.md — Eve Intel Dashboard

## What This Is
Real-time intel dashboard for **Astrum Mechanica**, a corporation in the **Get Off My Lawn (LAWN)** alliance (EVE Online). LAWN was removed from the Imperium coalition after 14 years and relocated to the Dronelands, claiming 2 constellations in **The Kalevala Expanse** region.

The dashboard monitors sovereignty, kill activity, jump traffic, and active sov campaigns across LAWN's territory and the neighboring border systems.

## Current Game Situation (Feb 2026)
- LAWN holds **all** sovereignty in constellations **6-CBBM** (7 systems) and **2Q-8WA** (8 systems)
- **Sov levels are 0** across the board — brand new claims, ADMs need grinding up
- **SL0W CHILDREN AT PLAY** collapsed and retreated to highsec. Their remnant sov (ADM 4) surrounds LAWN on the south and east — this is vulnerable space that other groups could contest
- **T.RD (The Rejected)** holds systems to the south/southwest, mostly at ADM 0-1 — also freshly claimed or abandoned
- **BIGAB** holds a pocket in the far south (SG-3HY, QZX-L9, AU2V-J, SY-0AM area)
- **FRIES** holds C3J0-O and B3ZU-H in the southeast
- Regional connections: **Vale of the Silent** (north), **Geminate** (northwest), **Etherium Reach** (south), **Malpais** (east)

## LAWN's Systems

### 6-CBBM Constellation (7 systems)
| System | Notes |
|--------|-------|
| UDVW-O | Northern border — gate to LS-JEP (Vale of the Silent) |
| UJXC-B | Northern border — gate to A3-RQ3 (Vale of the Silent) |
| F48K-D | **Cross-constellation gate** to FB5U-I (2Q-8WA) |
| 1-KCSA | Interior hub |
| XTJ-5Q | **Southern border** — gate to LE-67X (SL0W remnant). Hot zone. |
| JT2I-7 | Dead-end off XTJ-5Q |
| N-JK02 | **Southern border** — gates to L-GY1B (SL0W) and AID-9T (Etherium Reach). Hot zone. |

### 2Q-8WA Constellation (8 systems)
| System | Notes |
|--------|-------|
| FB5U-I | Cross-constellation gate to F48K-D |
| BZ-BCK | Hub — connects to J-OAH2 and O5-YNW |
| J-OAH2 | Dead-end off BZ-BCK |
| O5-YNW | Hub — connects to 86L-9F and 5-VFC6 |
| 86L-9F | Connects to IUU3-L |
| 5-VFC6 | Dead-end off O5-YNW |
| IUU3-L | Connects to S-LHPJ |
| S-LHPJ | **Eastern border** — gate to 6V-D0E (SL0W remnant). Hot zone. |

### Threat Entry Points (border systems)
- **XTJ-5Q** → LE-67X (SL0W remnant, ADM 4)
- **N-JK02** → L-GY1B (SL0W, ADM 4) + AID-9T (Etherium Reach regional)
- **S-LHPJ** → 6V-D0E (SL0W, ADM 4)
- **UDVW-O** → LS-JEP (Vale of the Silent regional)
- **UJXC-B** → A3-RQ3 (Vale of the Silent regional)

## Tech Stack
- **Backend:** Python 3 + Flask
- **Frontend:** React 18 (CDN via Babel) in a single HTML file
- **Data source:** EVE ESI public endpoints (esi.evetech.net) — no auth needed
- **No build step** — CDN React + Babel in-browser transpilation
- User's OS is **CachyOS (Arch Linux)** with **fish shell**

## Project Structure
```
eve-intel-dashboard/
├── app.py              # Flask backend — live ESI data
├── demo.py             # Demo mode — mock data for testing UI
├── config.py           # Constellation IDs, friendly alliance definitions
├── esi_client.py       # ESI API wrapper with in-memory TTL caching
├── requirements.txt    # flask, requests
├── static/
│   └── index.html      # React SPA with SVG constellation map
├── .gitignore
├── CLAUDE.md           # This file
└── README.md
```

## Key Technical Decisions
1. **static/index.html not templates/** — Must be served via `send_from_directory`, NOT `render_template`, because Jinja2's `{{ }}` conflicts with React JSX expressions
2. **Map layout is manual** — System positions in `MAP_LAYOUT` (inside index.html) are manually placed to match the Dotlan sovereignty map layout. Gate connections are in `MAP_CONNECTIONS` array with types: `internal`, `cross`, `border`, `regional`
3. **Demo mode** — `demo.py` serves identical API routes as `app.py` but returns hardcoded mock data (no ESI calls). Always test UI changes against demo mode first
4. **In-memory caching** — `esi_client.py` caches responses in a dict with per-category TTLs. No persistence yet

## Development

### Setup
```bash
python -m venv .venv
source .venv/bin/activate.fish   # fish shell
pip install -r requirements.txt
```

### Run
```bash
python demo.py      # Mock data (for UI work)
python app.py       # Live ESI data
# → http://localhost:5000
```

### Important ESI Endpoints (all public, no auth)
- `GET /sovereignty/map/` — who holds what
- `GET /sovereignty/campaigns/` — active sov timers
- `GET /universe/system_kills/` — kills per system (hourly)
- `GET /universe/system_jumps/` — jump traffic (hourly)
- `GET /universe/constellations/{id}/` — system list for a constellation
- `GET /universe/systems/{id}/` — system details (name, security)
- `GET /search/?categories=constellation&search={name}` — name → ID resolution

### Dashboard API Routes
- `GET /api/config` — constellation + system metadata
- `GET /api/sovereignty` — sov holder per system with friendly/hostile flag
- `GET /api/activity` — kills + jumps per system
- `GET /api/campaigns` — active sov contests
- `GET /api/status` — health check

## Roadmap
- [ ] Discord webhook alerts (ADM drops, hostile activity spikes, new sov campaigns)
- [ ] SQLite persistence for historical trends
- [ ] zKillboard feed panel (recent kills with ship types, ISK values)
- [ ] Neighbor threat profiling (who lives nearby, what they fly, TZ activity)
- [ ] ADM tracking with threshold alerts
- [ ] EVE SSO auth for character-specific data
- [ ] Jump bridge route overlay on map
- [ ] Time-zone activity heatmaps

## Visual Design
Dark sci-fi HUD aesthetic matching EVE's Neocom interface:
- Background: `#060a0f`, panels: `#0a1018`
- Accent: cyan `#00d4ff`, friendly: green `#00ff88`, hostile: red `#ff3355`, caution: amber `#ffaa00`
- Fonts: Orbitron (headings), Share Tech Mono (data), Rajdhani (body)
- Scanline overlay, corner brackets on panels, pulsing status indicators
