# CLAUDE.md — LAWN Eve Intel Dashboard

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
| UDVW-O | **Northern border** — ONLY gate to Vale of the Silent (→ LS-JEP). Hot zone. |
| UJXC-B | Northern interior — no external gates |
| F48K-D | **Cross-constellation gate** to FB5U-I (2Q-8WA) |
| 1-KCSA | Interior hub |
| XTJ-5Q | **Southern interior** — dead-end off 1-KCSA via N-JK02 |
| JT2I-7 | Dead-end off XTJ-5Q |
| N-JK02 | **Southern border** — ONLY gate from LAWN to rest of TKE (→ L-GY1B). Hot zone. |

### 2Q-8WA Constellation (8 systems)
| System | Notes |
|--------|-------|
| FB5U-I | Cross-constellation gate to F48K-D |
| BZ-BCK | Hub — connects to J-OAH2, O5-YNW, and 5-VFC6 |
| J-OAH2 | Dead-end off BZ-BCK |
| O5-YNW | Hub — connects to 86L-9F and IUU3-L |
| 86L-9F | Dead-end off O5-YNW |
| 5-VFC6 | Dead-end off BZ-BCK |
| IUU3-L | Hub — connects to O5-YNW and S-LHPJ |
| S-LHPJ | **Eastern interior** — dead-end off IUU3-L |

### Threat Entry Points (border systems)
LAWN has **only 2 exits** from sov space:
- **N-JK02** → L-GY1B (rest of TKE, S4S-SD constellation)
- **UDVW-O** → LS-JEP (Vale of the Silent regional)

All other border systems (XTJ-5Q, S-LHPJ) are interior dead-ends with no external gates.

## Tech Stack
- **Backend:** Python 3 + Flask
- **Frontend:** React 18 (CDN via Babel) in a single HTML file
- **Data source:** EVE ESI public endpoints (esi.evetech.net) — no auth needed
- **No build step** — CDN React + Babel in-browser transpilation
- User's OS is **CachyOS (Arch Linux)** with **fish shell**

## Project Structure
```
lawn-eve-intel-dashboard/
├── app.py              # Flask backend — live ESI data
├── demo.py             # Demo mode — mock data for testing UI
├── config.py           # Constellation IDs, friendly alliance definitions
├── db.py               # SQLite persistence — ADM/activity snapshots + history queries
├── esi_client.py       # ESI API wrapper with in-memory TTL caching
├── intel.db            # SQLite database (auto-created, gitignored)
├── requirements.txt    # flask, requests
├── static/
│   └── index.html      # React SPA with SVG constellation map + ADM sparklines
├── .gitignore
├── CLAUDE.md           # This file
└── README.md
```

## Key Technical Decisions
1. **static/index.html not templates/** — Must be served via `send_from_directory`, NOT `render_template`, because Jinja2's `{{ }}` conflicts with React JSX expressions
2. **Map layout is manual** — Two layout modes: `MAP_LAYOUT` (traditional Dotlan-style) and `MAP_LAYOUT_SUBWAY` (abstract metro-style). Gate connections are in `MAP_CONNECTIONS` array with types: `internal` (same constellation), `cross` (different TKE constellations), `regional` (to other regions), `neighbor` (neighbor region systems). Subway mode prioritizes readability over geometric accuracy — LAWN at top, TKE spread below, neighbor systems positioned to avoid overlapping TKE connection lines
3. **Demo mode** — `demo.py` serves identical API routes as `app.py` but returns hardcoded mock data (no ESI calls). Always test UI changes against demo mode first
4. **In-memory caching** — `esi_client.py` caches responses in a dict with per-category TTLs
5. **SQLite persistence** — `db.py` snapshots ADM and activity data hourly (deduplicated). WAL mode for concurrent reads. History API serves sparkline data to frontend

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
- `GET /api/history/adm?hours=168` — ADM history for sparklines (default 7 days, max 30)
- `GET /api/status` — health check

### Map Implementation Details

**Key Functions** (in `static/index.html`):
- `isReffed(name)` — checks if system has active sov campaign
- `needsCriticalGrinding(name)` — checks if ADM < 2 (red treatment)
- `needsCautionGrinding(name)` — checks if ADM 2-4 (amber treatment)
- `getAdmColor(adm)` — returns color for ADM value display
- `getColor(name)` — returns base stroke color for system nodes

**Visual Rendering Order** (SVG z-order in node rendering):
1. Reffed ring (rendered first, outermost)
2. NPC ring (activity indicator)
3. PVP glow (combat indicator)
4. Selection ring (UI state)
5. Main node circle (with grinding stroke if needed)
6. "!" icon (critical systems only)
7. System name and ADM labels

**CSS Animations**:
- `pulse-dot` — status indicator (2s cycle)
- `pulse-reffed` — reffed system ring (2s cycle, opacity 0.3→0.8)

**SVG Filters**:
- `glow-r` — red glow (stdDeviation 4) for PVP and critical systems
- `glow-c` — cyan glow (stdDeviation 3) for selection
- `glow-amber` — amber glow (stdDeviation 3) for reffed and caution systems

## Map Visualization & Visual Indicators

The constellation map shows The Kalevala Expanse with multiple visual indicators that stack to show system status at a glance:

### Visual Priority Hierarchy (outermost to innermost)
1. **Reffed Ring** (r=16, amber dashed) - Pulsing amber warning ring for systems with active sov campaigns
2. **NPC Ring** (r=18-24, cyan) - Ratting activity indicator (>200 NPC kills/hour)
3. **PVP Glow** (r=8-14, red) - Combat activity indicator (≥1 ship kill/hour)
4. **Node Circle** (r=6) - System base with color-coded stroke for grinding status
5. **"!" Icon** - Red exclamation mark for critical ADM systems (< 2.0)
6. **System Name** (above node, fontSize 10) - 25% larger than previous version
7. **ADM Value** (below node, fontSize 9) - 29% larger, color-coded by level

### ADM Differentiation & Grinding Priority

The dashboard emphasizes **critical systems (ADM < 2.0)** much more strongly than caution systems:

**Critical Systems (ADM < 2.0)**:
- **Map**: Thick red stroke (3px) with red glow + bold "!" icon (fontSize 11)
- **Table**: "⚠ CRITICAL" badge in bright red with higher opacity background
- **Tooltip**: "⚠ CRITICAL - PRIORITY GRINDING TARGET" banner in red
- **Summary Card**: "Critical ADM" count shows systems needing immediate attention

**Caution Systems (ADM 2.0-4.0)**:
- **Map**: Amber stroke (2px) with amber glow (no icon)
- **Table**: "⚠ GRIND" badge in amber
- **Tooltip**: "⚠ GRIND RECOMMENDED" banner in amber

**Safe Systems (ADM 4.0+)**:
- Normal display with cyan/green ADM values
- No grinding indicators

### Sov Campaign Alerts

Campaign alerts show **system names** instead of numeric IDs (e.g., "1-KCSA" instead of "System 30002826"):
- Campaign type: TCU, IHUB, or STATION
- Attack vs defense percentages
- Systems with active campaigns display pulsing amber ring on map

### Reffed System Indicators

Systems under attack (reinforced structures) are clearly marked:
- **Map**: Pulsing amber dashed ring (r=16) - 2s animation cycle
- **Tooltip**: "⚠ ACTIVE SOV CAMPAIGN" banner in amber
- Visible at a glance even when zoomed out

### Map Legend

Updated legend shows all indicators:
- Reffed (active timer) - amber dashed ring
- Critical (ADM < 2) - thick red border
- Caution (ADM 2-4) - amber border
- LAWN Sov - green dot
- NPC ratting - cyan ring
- PVP danger - red dot
- Neighbor region - dimmed
- Internal/cross/regional gates - various line styles

### Enhanced Tooltips

Hovering over systems shows detailed status with priority warnings:
- ADM level with color coding
- ADM status warnings for systems below safe threshold
- Active campaign status (if reffed)
- Grinding priority (critical or caution)
- Activity metrics (PVP, NPC, jumps)
- Sov holder and corporation

**Note**: ESI API does not provide separate Military/Industrial/Strategic indexes. Only the combined ADM (vulnerability_occupancy_level) is available.

## Roadmap
See [ROADMAP.md](ROADMAP.md) for full details and backlog.

**Done:**
- [x] SQLite persistence for historical trends
- [x] ADM tracking with trend sparklines and 24h change indicators

**Priority 1 — Immediate tactical value:**
- [ ] Neighbor threat profiling (who lives nearby, what they fly, TZ activity)
- [ ] Time-zone activity heatmaps
- [ ] zKillboard feed panel enhancements (filtering, ship class breakdowns)
- [ ] ADM grinding planner (priority ranking, rate estimation, daily targets)

**Priority 2 — Operational:**
- [ ] Browser push notifications (PVP alerts, sov campaigns, ADM drops)
- [ ] Structure tracking (requires SSO)
- [ ] Regional intel aggregation (neighboring region early warning)
- [ ] Jump bridge route overlay on map

**Priority 3 — Long-term:**
- [ ] Discord webhook alerts (ADM drops, hostile activity spikes, new sov campaigns)
- [ ] EVE SSO auth for character-specific data
- [ ] Fleet composition analyzer
- [ ] Moon mining tracker

## Visual Design

Dark sci-fi HUD aesthetic matching EVE's Neocom interface:
- **Background**: `#060a0f`, panels: `#0a1018`
- **Color Palette**:
  - Accent: cyan `#00d4ff`
  - Friendly: green `#00ff88`
  - Critical/Hostile: red `#ff3355`
  - Caution/Warning: amber `#ffaa00`
  - Muted text: `#6a8090`, `#8a9aa0`
- **Fonts**:
  - Orbitron (headings, warnings) - bold, uppercase, letter-spaced
  - Share Tech Mono (data, system names) - monospace, technical
  - Rajdhani (body text)
- **Visual Effects**:
  - Scanline overlay for CRT aesthetic
  - Corner brackets on panels
  - Pulsing status indicators (dot, reffed ring)
  - SVG glow filters (red, cyan, amber)
  - Smooth transitions on hover
- **Map Font Sizes** (increased Feb 2026):
  - LAWN system names: 10px (was 8px)
  - Neighbor system names: 8px (was 7px)
  - ADM values: 9px (was 7px)
  - Warning icons: 11px bold
