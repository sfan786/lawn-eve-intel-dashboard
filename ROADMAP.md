# ROADMAP — LAWN Eve Intel Dashboard

Prioritized by tactical value for LAWN's current situation: brand new sov in Kalevala Expanse, ADMs still grinding up, surrounded by collapsed SL0W remnant space and fresh T.RD claims.

## Completed

- [x] **SQLite persistence** — hourly ADM + activity snapshots with deduplication
- [x] **ADM trend sparklines** — 7-day history per system with 24h change indicators
- [x] **Constellation map** — full TKE region with subway/traditional modes, grinding indicators
- [x] **Sov campaign tracking** — reinforced/nodes phases, countdown timers, progress bars
- [x] **Kill feed** — zKillboard integration with LAWN/regional tagging
- [x] **Vulnerability windows** — ADM-based vuln duration calculation per system
- [x] **Alliance activity summary** — LAWN-wide kills/NPC/jumps totals (always visible regardless of tab selection)
- [x] **Enhanced data timestamp** — full date/time display for ESI data freshness indicator

---

## Priority 1 — Immediate Tactical Value

### Neighbor Threat Profiling
**Why:** SL0W space is collapsing around us. Need to know who's moving in before they're on our doorstep.
- Pull alliance/corp activity from zKillboard for border-adjacent holders (SL0W remnants, T.RD, BIGAB, FRIES)
- Ship doctrine analysis — what do they fly? (top 10 ship types by kills)
- Timezone activity — when are they active? (kill timestamps binned by hour)
- Threat score per neighbor — composite of activity level, fleet size indicators, proximity
- Display as a dedicated panel with per-neighbor cards
- **Data sources:** zKillboard API (public, no auth), ESI sovereignty map

### Time-Zone Activity Heatmaps
**Why:** LAWN needs to know when systems are safe to grind and when to expect hostiles.
- Heatmap grid: systems × hours (24h UTC), colored by activity level
- Separate views for NPC kills (friendly grinding activity) and PVP kills (hostile activity)
- Highlight vulnerability windows overlaid on the heatmap
- Use historical activity_snapshots from SQLite for the data
- Shows "safe grinding hours" vs "danger hours" at a glance
- **Data sources:** SQLite activity_snapshots table, ESI hourly data

### zKillboard Feed Enhancements
**Why:** Current feed is basic — need better filtering and analysis for fleet intel.
- Filter by: LAWN space only / all regional, PVP only / include NPC, ISK threshold
- Ship class breakdown — subcaps vs caps vs supers in region
- Attacker corp/alliance aggregation — "who's roaming our space?"
- Repeat offender tracking — flag pilots/corps seen multiple times
- Loss summary — "LAWN lost X ISK today" vs "LAWN killed X ISK today"
- Expandable kill details (fitted ship value, attacker list)
- **Data sources:** zKillboard API + websocket for real-time

### ADM Grinding Planner
**Why:** With 15 systems all below ADM 4, need to prioritize grinding efficiently.
- Ranked system list by grinding urgency (ADM level × strategic importance)
- Strategic importance weighting: border systems (UDVW-O, N-JK02) > cross-constellation (F48K-D, FB5U-I) > hubs > dead-ends
- Estimated time to next ADM level based on current grinding rate (from sparkline slope)
- Suggested daily grinding targets — "grind these 3 systems today"
- ADM goal tracker — set target ADMs per system, show progress
- **Data sources:** SQLite adm_snapshots (trend analysis), config.py (system metadata)

---

## Priority 2 — Operational Quality of Life

### Browser Push Notifications
**Why:** Need instant alerts without requiring Discord setup.
- PVP activity in LAWN space (configurable threshold)
- New sov campaigns (structure reffed)
- ADM drops below threshold
- Uses browser Notification API — works in background tabs
- Configurable per-system and per-alert-type
- **Data sources:** Existing API endpoints, polled client-side

### Structure Tracking
**Why:** Once citadels and engineering complexes go up, need to track timers and fuel.
- List all known structures in LAWN space (citadels, refineries, ECs)
- Fuel status and depletion estimates (requires SSO)
- Reinforcement timers if attacked
- Vulnerability schedule display
- **Data sources:** ESI structure endpoints (requires SSO auth)

### Regional Intel Aggregation
**Why:** Need early warning from neighboring regions before hostiles reach LAWN.
- Monitor Vale of the Silent (north gate — UDVW-O), Geminate (northwest), Etherium Reach (south), Malpais (east)
- Track large fleet movements via jump spikes
- Flag new sovereignty changes in adjacent constellations
- "Threat corridor" view — show activity along the 2 entry routes into LAWN space
- **Data sources:** ESI sovereignty/jumps/kills (public), zKillboard regional feeds

### Jump Bridge Route Overlay
**Why:** Once JBs are online, need to show route options on the constellation map.
- Manual JB configuration (system pairs)
- Draw JB connections on map as distinct line type
- Route calculation — shortest path between any two LAWN systems
- Gate-only vs JB-optimized route comparison
- **Data sources:** Manual config (JB endpoints entered by user)

---

## Priority 3 — Long-Term / Requires Auth

### Discord Webhook Alerts
**Why:** Most of LAWN lives in Discord. Push critical alerts there.
- Configurable webhook URL(s) per alert type
- Alert types: ADM drop below threshold, new sov campaign, high PVP spike, structure timer
- Rich embeds with system info, map snippet, and action links
- Rate limiting to avoid spam
- **Data sources:** Existing backend data, outbound webhooks

### EVE SSO Auth
**Why:** Unlocks character-specific and corp-level data.
- OAuth2 flow with EVE's SSO
- Character-specific: location, ship, skill queue
- Corp-level: structure list, fuel levels, moon extractions, wallet
- Fleet tracking — who's in fleet, what they're flying
- **Prerequisite for:** Structure tracking, fleet comp analysis, PI tracking

### Fleet Composition Analyzer
**Why:** Know what LAWN can field vs what neighbors bring.
- Analyze zKillboard data to build doctrine profiles per alliance
- LAWN vs neighbors: ship class comparison, average fleet size
- "Can we fight this?" quick assessment based on recent fleet comps
- **Data sources:** zKillboard API (public for kills), ESI (SSO for corp members)

### Moon Mining Tracker
**Why:** Moons are a key income source in nullsec.
- Track moon extraction timers
- Ore composition and estimated value per moon
- Extraction schedule calendar view
- **Prerequisite:** EVE SSO auth
- **Data sources:** ESI moon extraction endpoints (SSO)

---

## Ideas / Backlog

- **Mobile-responsive layout** — dashboard works on phone for quick checks during ops
- **Multi-alliance view** — if LAWN blues other groups, show their space too
- **Wormhole connection tracker** — integration with Pathfinder/Tripwire APIs
- **PI (Planetary Interaction) tracker** — colony status and extraction timers (SSO)
- **Market dashboard** — regional market activity, price comparisons to Jita
- **Fuel logistics planner** — calculate fuel needs for structures, plan hauling runs
- **Historical battle reports** — aggregate kills into fleet fight summaries
- **Map annotations** — user-placed notes on systems ("cloaky camper here", "safe to rat")
- **SRP (Ship Replacement) integration** — track losses eligible for reimbursement
- **Localized time display** — show timers in user's local TZ alongside EVE time
