# ROADMAP — EVE Alliance Intel Dashboard

**Current situation (May 2026):** LAWN has relocated to **Perrigen Falls** (constellations 9BGY-6 and WXB-RY). The dashboard codebase is now alliance/region agnostic — see `deployments/` and `tools/bootstrap_deployment.py`.

## Completed

- [x] **Alliance/region-agnostic deployment system** — `deployments/` modules + `tools/bootstrap_deployment.py` bootstrap; `DEPLOYMENT` env var picks active deployment; per-deployment scoping in `intel.db` via `deployment_id`
- [x] **Perrigen Falls migration** — LAWN relocated from Kalevala to Perrigen Falls; mock data, frontend, and CLAUDE.md all updated; old Kalevala history preserved but inert
- [x] **SQLite persistence** — hourly ADM + activity snapshots with deduplication, scoped per deployment
- [x] **ADM trend sparklines** — 7-day history per system with 24h change indicators
- [x] **Constellation map** — full region with subway/traditional modes, grinding indicators; map data served from `/api/config`
- [x] **Sov campaign tracking** — reinforced/nodes phases, countdown timers, progress bars
- [x] **Kill feed** — zKillboard integration with primary-space/regional tagging
- [x] **Vulnerability windows** — ADM-based vuln duration calculation per system
- [x] **Alliance activity summary** — LAWN-wide kills/NPC/jumps totals (always visible regardless of tab selection)
- [x] **Enhanced data timestamp** — full date/time display for ESI data freshness indicator
- [x] **Neighbor threat profiling** — zKillboard-sourced ship doctrine analysis (what they FLY, not what they kill), TZ heatmaps with peak window, ISK destroyed, capital role badges (DREAD/FAX/etc.), "NEAR LAWN" region activity, composite threat scoring; auto-detects active entities from kills in neighbor systems alongside manually pinned NEIGHBOR_ENTITIES; 15-min endpoint cache
- [x] **Activity heatmap** — per-system hourly activity grid (systems × hours UTC) from SQLite snapshots
- [x] **Timerboard** — password-protected custom structure timers with add/delete and countdown display
- [x] **Sov upgrade tracking** — manual iHub upgrade display (military/industry/strategic) per LAWN system
- [x] **Vite + React build system** — frontend split into `frontend/src/` with proper component files, utils, and CSS modules; Vite dev proxy for local development; legacy `static/index.html` kept as fallback
- [x] **Flask Blueprint refactor** — `app.py` and `demo.py` reduced to thin entry points; live routes in `routes/` package, mock routes in `mock/` package; `SystemState` singleton for shared startup state
- [x] **Multi-stage Docker build** — Node 20 stage builds Vite frontend, Python 3.11 stage runs gunicorn; `intel.db` persisted via host volume mount
- [x] **Friendly entity expansion** — BorderZone [BOZON] and Gnomes Rising HoA [GNOME] added as friendly alliances; all 12 LAWN member corps added to `FRIENDLY_CORPORATIONS`
- [x] **ADM grinding planner** — priority cards (top 6 systems) ranked by 5-tier tactical scoring (border > cross-constellation > hub > interior > dead-end), with grinding rate (+X.X/day from history), and collapsible full-system table for all 15 LAWN systems; `computeGrindingRate` and `compute24hChange` added to `admHelpers.js`
- [x] **UI space efficiency pass** — map mode toggle lifted into panel header; controls policy documented in CLAUDE.md (controls in headers, compact empty states, metadata as badges)
- [x] **Localized time display** — status bar clock shows EVE (UTC) and Local time simultaneously
- [x] **DScan parser** — paste EVE directional scan output for instant ship breakdown by class (SUPER/CAPITAL/BATTLESHIP/etc.), threat tier banner (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL), and structures/deployables section; pure frontend, no server round-trip (`DscanParser.jsx`)
- [x] **Local chat scanner** — paste pilot names from local chat; resolves via ESI `POST /universe/ids/` + `POST /characters/affiliation/` and classifies each pilot as LAWN / FRIENDLY / UNKNOWN / UNRESOLVED with corp+alliance display and zKillboard links (`LocalScanner.jsx`, `POST /api/local/scan`)
- [x] **Ally expansion** — The Skeleton Crew [MEAN] (99008788) and Weapons Of Mass Production [WOMP] (99010468) added as friendly alliances in `config.py`; classified as FRIENDLY in local scanner and sov display
- [x] **Map system annotations** — right-click any system to add/edit/delete sticky notes (SQLite-backed); amber dot indicator on map, note in tooltip, Note column in system table; no auth required
- [x] **Jump bridge overlay** — manual JB config panel (timer auth gated) renders dashed violet lines on the constellation map in both modes; `JumpBridgeManager.jsx` + `routes/jb_routes.py`
- [x] **DScan copy** — COPY button in DScan parser header copies formatted threat summary (tier + ship class counts + objects) to clipboard
- [x] **PLH-style pilot risk ratings** — `POST /api/chars/analyze` fetches zKillboard stats per character; `_compute_risk_tier()` classifies VERY DANGEROUS / DANGEROUS / MODERATE / SNUGGLY / NEWBIE / NO DATA based on kills, danger ratio, and ISK efficiency; displayed in Local Scanner RISK column and Intel Channel Parser char rows
- [x] **Capital/dropper/covert role detection** — `_detect_roles()` reads the zkill stats `groups` dict (ship groups from losses) to detect TITAN, SUPER, DREAD, CARRIER, FAX, BLOPS, RECON, BOMBER, T3C, COVOPS; role badges rendered next to risk tier in both scanner panels; `THREAT_SHIP_GROUPS` map in `eve_constants.py`
- [x] **Intel Channel Parser enhancements** — per-row × deletion; `onBoardChange` prop propagates board state to `ConstellationMap` which renders a pulsing orange ring (distinct from amber reffed ring) on systems with active hostile intel; browser `Notification` API fires on primary/border system reports (permission requested on first hostile paste)
- [x] **Hostile sov indicators** — primary systems taken by enemy alliances are visually distinguished from friendly-held systems: red node + pulsing red dashed ring + `✕` icon on the map (both subway and traditional modes); `☠ HOSTILE` badge in the system table Status column; tooltip shows system name and holder in red with `☠ HOSTILE SOV — RECONQUEST NEEDED` banner; "Hostile Sov" count in the Situation Overview header
- [x] **Entosis command node board** — dedicated `/entosis` SPA page (`EntosisPage.jsx`); pilots enter a callsign, claim nodes, and advance status through unclaimed → running → contested → captured/lost; password-gated add/delete; 5s auto-poll; `routes/entosis_routes.py` + SQLite `entosis_nodes` table
- [x] **RMC coalition standings** — ~50 RMC alliance IDs + 8 standalone +5 corps added to `lawn_perrigen.py`; new `FRIENDLY_STANDING_CORPORATIONS` deployment key for standalone corps; `FRIENDLY_STANDING_CORP_IDS`/`_NAMES` sets consumed by intel, local-scan, and hostile-feed routes
- [x] **Performance & security pass** — parallel killmail prefetch via `ThreadPoolExecutor` in kill feed + hostile feed; bulk `POST /universe/names/` primes the ESI cache before the enrichment loop; compound DB indexes on `(deployment_id, system_id, timestamp)` for faster history queries; thread-safe ESI cache (`_cache_lock`, per-entry `expires_at`); HMAC-based timer password check
- [x] **SQLite-backed sov change tracking** — `sov_state` + `sov_changes` tables replace in-memory dict; `db.record_sov_changes()` persists neighbor sov events across restarts; changes exposed via `/api/intel/sov_changes`
- [x] **EVE SSO auth (identity-only)** — "Log in with EVE" OAuth2 flow gates write actions (timers, entosis claims, annotations, jump bridges, AI summaries) by alliance membership / character allowlist; access-token JWT verified against EVE JWKS + issuer + `aud`/`azp`; `TIMER_PASSWORD`/`X-Timer-Auth` retained as fallback via the shared `require_write_auth` decorator; `routes/auth_sso.py`, `useAuth` hook, `EveLoginButton.jsx`. No ESI scopes yet
- [x] **AI threat summaries** — "AI SUMMARY" button in the D-scan and Local scanner panels sends parsed intel to the Gemini API (`gemini-2.5-flash`) for a concise tactical read-out; `routes/ai_routes.py` (`POST /api/ai/threat_summary`) gated by `require_write_auth`, bounded by `max_output_tokens` + client timeout, with a prompt-injection guard on pasted data; shared `useAiSummary` hook + `common/AiSummary.jsx`; requires `GEMINI_API_KEY` (endpoint returns 501 / button hidden when unset)
- [x] **Fleet composition analyzer (live fleet paste)** — paste a fleet/pilot list → `POST /api/fleet/analyze` (`routes/intel_routes.py`) resolves each pilot's standing (lawn/friendly/unknown/unresolved), risk tier, and capital + fleet role badges (reusing `_compute_risk_tier`/`_detect_roles`/`_detect_fleet_roles`), plus an aggregate summary (risk distribution, role/fleet-role counts, capital count, avg danger/kills, top hostile alliances); `FleetCompAnalyzer.jsx`. (The doctrine-profile / blue-vs-red comparison from the Priority 3 item is still open.)

---

## Priority 1 — Immediate Tactical Value

### zKillboard Feed Enhancements
**Why:** Current feed is basic — need better filtering and analysis for fleet intel.
- [x] Filter by: LAWN space only / all regional, PVP only / include NPC
- [x] Attacker corp/alliance aggregation — "who's roaming our space?"
- [x] Loss summary — "LAWN lost X ISK today" vs "LAWN killed X ISK today"
- [x] ISK threshold filter
- [x] Ship class breakdown — subcaps vs caps vs supers in region
- [x] Repeat offender tracking — flag pilots/corps seen multiple times
- [x] Expandable kill details (fitted ship value, attacker list)
- **Data sources:** zKillboard API + websocket for real-time



### Mobile Responsive Layout
**Why:** Need to be able to check the dashboard on mobile.
- [x] Mobile tab nav (Map / Systems / Kills / Intel / Timers / Industry) with bottom nav bar
- [x] Tab-based content switching — each tab shows only its relevant panels
- [x] Responsive header — compact clock/status bar on small screens
- [x] Tablet layout — `.panel-pair` wrapper puts CampaignAlerts+Timers and AdmTrends+Upgrades side-by-side at 700px+
- [ ] Large screen optimisation — side-by-side map + table (attempted; map too small at 3fr/2fr split — needs different approach)
- **Data sources:** N/A
---

## Priority 2 — Operational Quality of Life

### Browser Push Notifications
**Why:** Need instant alerts without requiring Discord setup.
- [x] PVP activity in LAWN space (configurable threshold, default 3 kills)
- [x] New sov campaigns (structure reffed)
- [x] ADM drops below 2.0 (critical threshold)
- [x] Uses browser Notification API — works in background tabs
- [x] Configurable per-type toggles + PVP threshold; settings persisted in localStorage
- [x] ALERTS button in header status bar — pulsing amber dot when active
- **Data sources:** Existing API endpoints, polled client-side

### Regional Intel Aggregation *(complete)*
**Why:** Need early warning from neighboring regions before hostiles reach LAWN.
- [x] `/api/intel/regional` endpoint — neighbor system kills/jumps grouped by region, threat level per system and region
- [x] `RegionalIntel.jsx` component — per-region cards with per-system rows, color-coded threat tiers
- [x] Spike detection vs historical baseline — `db.get_activity_baseline()` computes 7-day avg per neighbor system; `/api/intel/regional` adds `spike_kills`/`spike_jumps` ratios; RegionalIntel shows `↑Xх` badge (amber ≥2×, red ≥5×); requires 3+ snapshots before flagging
- [x] Sov change tracking in adjacent constellations — `/api/intel/sov_changes` endpoint tracks ESI sov changes for neighbor systems in-memory; changes shown in RegionalIntel panel with alliance IDs and zkillboard links
- **Data sources:** ESI system_kills + system_jumps (already fetched for neighbor systems); activity_snapshots table (neighbor systems already included via all_monitored_ids)

### Jump Bridge Route Overlay *(on hold — see Priority 4)*
**Why:** On hold pending new sov stabilization. Moving to new space resets JB infrastructure. With 1-2 constellations likely at destination, mechanics probably allow at most 1 JB total (Ansiblex requires iHub + sov upgrades per constellation). No guarantee of a viable ally link either. Config UI and map rendering are already built — revisit when sov is established.
- [x] Manual JB config panel + map rendering (shipped, functional)
- [ ] Route calculation and gate vs JB comparison (deferred)
- **Blocked on:** New sov settlement and JB feasibility assessment

---

## Priority 3 — Long-Term / Requires Auth

### EVE SSO Auth
**Why:** Unlocks character-specific and corp-level data.
- [x] **OAuth2 flow with EVE's SSO** — "Log in with EVE" gates write actions
  (timers, entosis claims, annotations, jump bridges) by alliance membership /
  character allowlist; entosis claims stamped with the real character;
  `TIMER_PASSWORD` retained as a fallback. `routes/auth_sso.py`,
  `frontend/src/utils/useAuth.js`, `EveLoginButton.jsx`. (No ESI scopes yet —
  identity only.)
- Character-specific: location, ship, skill queue (needs scopes)
- Corp-level: structure list, fuel levels, moon extractions, wallet (needs scopes)
- Fleet tracking — who's in fleet, what they're flying (needs scopes)
- **Prerequisite for:** Structure tracking, fleet comp analysis, PI tracking

### Fleet Composition Analyzer *(partially done)*
**Why:** Know what LAWN can field vs what neighbors bring.
- [x] Live fleet paste — `POST /api/fleet/analyze` + `FleetCompAnalyzer.jsx`: per-pilot standing/risk/role classification with an aggregate composition summary (see Completed)
- [ ] Analyze zKillboard data to build doctrine profiles per alliance
- [ ] LAWN vs neighbors: ship class comparison, average fleet size
- [ ] "Can we fight this?" quick assessment based on recent fleet comps
- **Data sources:** zKillboard API (public for kills), ESI (SSO for corp members)

---

## Priority 4 -- Low Priority   

### ADM Grinding Planner *(partially done)*
**Why:** With 15 systems all below ADM 4, need to prioritize grinding efficiently.
- [x] Ranked system list by grinding urgency (ADM level × 5-tier tactical scoring)
- [x] Strategic importance weighting: border > cross-constellation > hub > interior > dead-end
- [x] Rate display — actual grinding speed (+X.X/day) from ADM history on each priority card
- [x] Full system table (all 15 systems) with ADM, rate, and tier — behind collapsible toggle in panel header
- [x] ADM goal tracker — set target ADMs per system, show progress bars
- **Data sources:** SQLite adm_snapshots (trend analysis), config.py (system metadata)


---

## Ideas / Backlog

- **Wormhole connection tracker** — integration with Pathfinder/Tripwire APIs
- **PI (Planetary Interaction) tracker** — colony status and extraction timers (SSO)
- **Market dashboard** — regional market activity, price comparisons to Jita
- **Fuel logistics planner** — calculate fuel needs for structures, plan hauling runs
- **Historical battle reports** — aggregate kills into fleet fight summaries
- **Map annotations** — user-placed notes on systems ("cloaky camper here", "safe to rat")
- **SRP (Ship Replacement) integration** — track losses eligible for reimbursement
- **Multi-alliance view** — if LAWN blues other groups, show their space too *(partially addressed via friendly IDs)*
- **Wormhole connection tracker** — integration with Pathfinder/Tripwire APIs
- **Discord webhook alerts** — ADM drops, sov campaigns, PVP spikes pushed to Discord (no current plans)
