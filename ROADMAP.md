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
- [x] **Automated test suite** — pytest 8.3.5 + Vitest 2; 107 Python tests (`tests/test_db.py`, `tests/test_esi_client.py`, `tests/test_routes.py`) covering SQLite CRUD, deduplication, deployment isolation, ESI cache/eviction/threading/chunking, session + error-limit backoff, and route-level auth gating / payload validation; 122 JS tests across 4 utility modules and 3 React components; both suites plus ruff and eslint run in CI via `smoke-test.yml`
- [x] **Fleet composition analyzer (live fleet paste)** — paste a fleet/pilot list → `POST /api/fleet/analyze` (`routes/intel_routes.py`) resolves each pilot's standing (lawn/friendly/unknown/unresolved), risk tier, and capital + fleet role badges (reusing `_compute_risk_tier`/`_detect_roles`/`_detect_fleet_roles`), plus an aggregate summary (risk distribution, role/fleet-role counts, capital count, avg danger/kills, top hostile alliances); `FleetCompAnalyzer.jsx`. (The doctrine-profile / blue-vs-red comparison from the Priority 3 item is still open.)
- [x] **Entosis ops redesign (event board)** — `/entosis` reorganized around ESI-detected sov campaigns instead of a blank node list: one event panel per campaign (active-first ordering, attacker/defender score bar, node-spawn countdown, vuln window, IHUB/TCU + DEFENSE/RECONQUEST badges); command nodes link to campaigns via nullable `entosis_nodes.campaign_id` (nodes spawn constellation-wide, so the per-event add dropdown lists the campaign's whole constellation); UNLINKED NODES section for manual/legacy nodes (stale-campaign nodes flagged EVENT ENDED); focused OP MAP shows only constellations with active/upcoming events (`utils/entosisHelpers.js` filters the map config, `ConstellationMap` reused unchanged); collapsible side column with D-Scan Parser, Local Scanner, OP KILL FEED (regional zkill feed filtered to campaign-constellation systems), Fleet Comp Analyzer, and Timerboard; ALERTS bell with browser push for new campaigns, nodes-spawned (new reinforced→nodes transition alert in `useNotifications`, also fires on the main dashboard), and ADM drops; demo mode seeds linked nodes
- [x] **UX polish: system filter + clipboard copy** — SystemTable live name-filter input (with count badge + ✕ clear); LocalScanner COPY button (formats pilots as `NAME (Corp/Alliance) [STANDING] RISK [ROLES]`); FleetCompAnalyzer COPY button (exports fleet summary); all follow the existing DscanParser COPY pattern
- [x] **CampaignAlerts COPY button** — panel-header COPY button on the Sovereignty Campaigns panel formats every active/reinforced campaign as a fleet-ping-ready line (`SYSTEM — TYPE — LABEL — NODES ACTIVE (X% vs Y%)` or `... Reinforced, nodes spawn in Xh Ym (date EVE)`) for pasting into Discord/fleet chat; `buildCampaignCopyText` in `campaignHelpers.js`
- [x] **Reliability & operations pass** — history collection decoupled from page views: `routes/poller.py` samples ESI on a fixed interval (`POLL_INTERVAL_SECONDS`) instead of snapshotting as a side effect of `GET /api/sovereignty` and `GET /api/activity`, so ADM sparklines, grinding rates, the heatmap, and the 7-day spike baselines no longer have holes whenever nobody has the dashboard open. All ESI/zKill HTTP moved onto one pooled `requests.Session` with retry/backoff, plus cooperative backoff on ESI's `X-Esi-Error-Limit-Remain` budget (exhausting it gets the IP temp-banned by CCP). `gunicorn.conf.py` adds `preload_app` so the startup region walk happens once in the master and workers inherit the warm cache via fork, with the poller started from `post_fork` (threads don't survive fork). Per-IP rate limits (`flask-limiter`) on the unauthenticated zKill-fanout endpoints and the Gemini endpoint; 20k-char input cap on AI summaries. `print()` replaced with the `logging` module throughout the backend. Legacy CDN-React `static/index.html` fallback removed — a missing Vite build now fails loudly instead of silently serving a stale UI. ruff + eslint added and wired into CI (eslint caught a real conditional-`useMemo` rules-of-hooks bug in `UpgradesOverview.jsx`). Route-level test suite added
- [x] **Traffic analytics** — answers "is this still worth running?": `routes/analytics_routes.py` registers an app-wide `after_app_request` hook that counts every request into two rollup tables (`traffic_hourly` keyed on hour/kind/path, `traffic_visitors` one row per visitor per day) — no per-request rows, so a busy day costs a few hundred rows regardless of poll volume. Counts buffer in memory and flush on an interval (and once per poller cycle) so SQLite writes stay off the request path. Privacy-preserving: no IPs or user agents stored, a visitor is a truncated HMAC of IP + user agent keyed on `ANALYTICS_SALT` (defaults to `FLASK_SECRET_KEY`); logged-in SSO sessions stamp the character name. Bot user agents counted separately and never as visitors; parameterised API paths collapse to their `url_rule`; unknown page paths bucket to `/other`. Reading the stats is operator-only and closed by default — `require_analytics_auth` takes an explicit character allowlist (`ANALYTICS_ALLOWED_CHARACTER_IDS`) or a dedicated `ANALYTICS_PASSWORD` (`X-Analytics-Auth` header), never the fleet-wide write credential, since `TIMER_PASSWORD` is handed out for timers and SSO write access covers the whole alliance; constant-time comparison plus a `RATELIMIT_ANALYTICS` cap (10/min) makes guessing impractical, and the header USAGE link only appears on a browser that has already unlocked the page. `GET /api/analytics/summary?days=N` (1–365) serves unique/returning visitors, "regulars" (5+ days), daily series, hour-of-day distribution, top pages/endpoints, and known pilots; rendered by the `/analytics` page (`AnalyticsPage.jsx`, linked as USAGE in the header). Rollups pruned after `ANALYTICS_RETENTION_DAYS` (default 180); recording disabled with `ANALYTICS_ENABLED=false`

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
- [x] Kill age display ("Xm ago" / "Xh ago") on each feed entry
- **Data sources:** zKillboard API + websocket for real-time



### ISK War Ledger
**Why:** Both kill-feed routes already parse full killmails with `zkb.totalValue`, then throw the aggregate away every request. Persisting it answers "how did the week go?" at a glance.
- [ ] `kill_ledger` table (deployment-scoped): killmail_id, timestamp, system_id, isk_value, our_loss vs our_kill
- [ ] Populate from the background poller so it accrues without page views
- [ ] Daily kills-vs-losses sparkline panel; 7/30-day ISK efficiency
- [ ] Per-corp breakdown — who is bleeding ships
- **Data sources:** zKillboard regional feed + ESI killmails (already fetched), SQLite
- **Depends on:** background poller (done)

### Battle Report Aggregation
**Why:** The kill feed shows individual kills; fights are what actually matter for AARs and for knowing what the enemy committed.
- [ ] Cluster kills by system + 20-minute window into "engagements"
- [ ] Per-engagement: participant counts per side, ISK destroyed/lost, ship classes committed, duration
- [ ] Link out to a zKillboard related-kills URL for the full BR
- [ ] Surface recent engagements on the dashboard and on `/entosis` for the active op
- **Data sources:** pure post-processing over data the kill feed already fetches
- **Depends on:** ISK war ledger (shared table)

### ADM Forecast
**Why:** `computeGrindingRate` already derives +X.X/day per system; projecting it forward answers the question the Grinding Plan panel exists to answer.
- [ ] "Days to ADM 5" projection per system from the observed rate
- [ ] Alliance-wide ETA to all-systems-safe, and which systems are trending *down*
- [ ] Flag systems whose rate is too low to reach target before the next vuln window
- **Data sources:** SQLite `adm_snapshots` (already collected)
- **Notes:** small addition to `GrindingPlan.jsx` + `admHelpers.js`

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

### PWA / Service Worker Alerts
**Why:** Browser notifications currently only fire while a tab is open. For a tool people check on a phone mid-fight, that is the difference between the alert working and not.
- [ ] Service worker + web app manifest (installable on mobile home screen)
- [ ] Move alert evaluation into the worker so campaigns/nodes/ADM alerts fire with the app closed
- [ ] Offline shell — last-known map and system table render without a connection
- **Data sources:** existing `/api/campaigns`, `/api/sovereignty`, `/api/activity`
- **Notes:** highest-leverage follow-up to the background poller — server-side truth plus client-side delivery

### Hostile Pilot Watchlist
**Why:** BLOPS/RECON/COVOPS role detection already exists, but only runs on demand when someone pastes Local. Known droppers should be flagged automatically.
- [ ] `hostile_watchlist` table — pilots flagged from scans, with detected roles and last-seen
- [ ] Auto-flag watchlisted pilots when they appear in the kill feed or a Local scan
- [ ] Manual add/remove (write-auth gated), with a note field
- [ ] "Seen in our space in the last 24h" panel
- **Data sources:** existing `_detect_roles()` output + zKill feed
- **Depends on:** background poller for passive detection

### zKillboard RedisQ Stream
**Why:** The feed currently polls with a 120s cache. RedisQ (long-poll) gives near-real-time kills and removes the polling entirely.
- [ ] Background RedisQ consumer feeding the same enrichment path as the current feed
- [ ] Push new kills to the browser (SSE or WebSocket) instead of 5-minute refreshes
- [ ] Drives PVP notifications directly, cutting alert latency from minutes to seconds
- **Data sources:** zKillboard RedisQ
- **Depends on:** background poller (same lifecycle/threading model)

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

### Sov Campaign History
**Why:** `sov_changes` already records neighbor sov flips, but nothing records how our own campaigns resolved — so there is no defense record to look back on.
- [ ] Persist each ESI campaign we see through to its outcome (held / lost / undefended)
- [ ] Per-system defense record and win rate; which TZs we keep losing in
- [ ] Correlate outcomes with fleet participation from the battle reports
- **Data sources:** `/sovereignty/campaigns/` polled by the background poller, SQLite
- **Depends on:** background poller, battle report aggregation

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
