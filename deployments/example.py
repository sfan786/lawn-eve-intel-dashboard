"""
Template deployment — copy this as a starting point if you cannot use the
bootstrap tool, or to understand what fields are required. The bootstrap
(tools/bootstrap_deployment.py) is the recommended path: it resolves IDs from
ESI, walks the gate graph, and fills in everything except FRIENDLY_*/upgrades.

Activate a deployment by setting the DEPLOYMENT env var to the module name
(e.g. DEPLOYMENT=lawn_perrigen). The default is lawn_perrigen.

NOTE: this repository is public. A deployment module describes current
standings and where the alliance actually lives, so live ones belong in
`deployments/local_<name>.py`, which is gitignored. Commit only reference or
historical deployments.
"""

# Stable identifier used to scope DB rows (ADM/activity history, timers,
# annotations, jump bridges) to this deployment. Changing it after rows
# have been written will hide that history.
DEPLOYMENT_ID = "example-deployment"

# Numeric IDs from ESI plus display strings used throughout the UI.
# Look these up with `python tools/esi_lookup.py alliance "..."`.
ALLIANCE = {
    "id": 0,
    "name": "Example Alliance",
    "ticker": "EXAM",
    "short_name": "EXAM",          # used in notification text
    "display_name": "EXAMPLE ALLIANCE",  # used in dashboard header
}

# Region this deployment monitors. Used to scope zKillboard region feeds and
# to discover constellations/systems via /universe/regions/<id>.
REGION = {
    "id": 0,
    "name": "Example Region",
}

# What this alliance's relationship to the monitored space actually is.
#   "sovereign" — holds sov in PRIMARY_CONSTELLATION_IDS. The default, and the
#                 only posture where the map, ADM trends, grinding planner,
#                 upgrades and PI panels mean anything.
#   "guest"     — we live in a host alliance's sov. Map, campaigns, activity,
#                 neighbour intel and the upgrade panel stay live; the ADM
#                 trends and grinding planner stand down, because that index
#                 isn't ours to raise. Set HOST_ALLIANCE_IDS below.
#   "rootless"  — no home, no sov. Those panels stand down and the dashboard
#                 reduces to the intel tooling that needs only standings
#                 (D-scan, local scan, fleet comp, kill feed, timers).
# Optional: omit it and you get "sovereign".
POSTURE = "sovereign"

# Required for POSTURE = "guest", ignored otherwise. The alliance(s) whose sov
# we live under. Their systems render as HOST (blue) instead of hostile, and a
# campaign defending their sov in our constellation reads as DEFENSE. Hosts are
# NOT implicitly friendly — add them to FRIENDLY_ALLIANCE_IDS as well if
# standings say so.
HOST_ALLIANCE_IDS = []

# Optional header subtitle, shown in place of the region name. Useful for a
# deployment whose situation is in flux; purely display text.
POSTURE_LABEL = ""

# Optional. Regions the kill feed and hostile tracker may be pointed at. A
# sovereign deployment can omit this (it defaults to [REGION]); a rootless one
# lists everywhere worth watching and the UI shows a picker. The backend
# rejects any region_id not on this list, so these endpoints can't be driven
# as an open zKillboard proxy.
#   WATCHED_REGIONS = [{"id": 10000066, "name": "Perrigen Falls"}, ...]

# Constellations this alliance operates in — and, under a "sovereign" posture,
# owns. SystemState marks systems in these constellations as `is_primary` so
# the UI highlights them. Other constellations in the region are still loaded
# for context but rendered dimly. Leave empty for a rootless deployment: that
# is what tells SystemState to skip the region walk entirely.
PRIMARY_CONSTELLATION_IDS = []
PRIMARY_CONSTELLATION_NAMES = []

# IDs and names of allied alliances/corps. Used by sov_routes and intel_routes
# to classify holders as friendly vs hostile.
FRIENDLY_ALLIANCE_IDS = []
FRIENDLY_ALLIANCES = []          # display names (parallel list; both shown in UI)
FRIENDLY_CORPORATIONS = []
# Standalone corporations (no alliance) with positive standings — list of
# {"name": ..., "id": ...} dicts. Classified "friendly", not "lawn".
FRIENDLY_STANDING_CORPORATIONS = []

# Threat alliances tracked by the Neighbor Threat Profiling panel.
NEIGHBOR_ENTITIES = [
    # {"name": "Some Hostile Alliance", "id": 99000000, "type": "alliance"},
]

# Systems just outside the primary region that share a gate with one of our
# systems. Resolved at startup so the early-warning panel can include them.
NEIGHBOR_SYSTEM_NAMES = []

# Convenience lists of system names. PRIMARY_SYSTEMS is the space this alliance
# operates in (its sov space under a "sovereign" posture); BORDER_SYSTEMS is
# primary-region systems with at least one gate leading outside the primary
# constellations (entry points).
PRIMARY_SYSTEMS = []
BORDER_SYSTEMS = []

# Per-system iHub upgrades. Manually maintained — ESI does not expose iHub
# fittings without SSO. Keys must match system names from PRIMARY_SYSTEMS.
# Upgrade type abbreviations come from eve_constants.UPGRADE_TYPES.
SYSTEM_UPGRADES = {
    # "EXAM-1": [{"type": "MTD", "level": 3}, {"type": "PA_Trit", "level": 1}],
}

# Map layout — each entry: {x, y, constellation, lawn?, security?, note?}.
# `lawn: True` marks primary-constellation systems for emphasis. `note` is the
# region name for neighbor systems (shown in tooltips).
MAP_LAYOUT = {
    # "EXAM-1": {"x": 500, "y": 250, "constellation": "EXAM-A", "lawn": True},
}

# Subway-style abstract layout. Often identical to MAP_LAYOUT initially; tune
# separately for the alternate map mode.
MAP_LAYOUT_SUBWAY = {}

# Gate connections. Type is one of:
#   internal — same constellation
#   cross    — different constellations, same region
#   regional — primary region <-> neighbor region
#   neighbor — between two neighbor-region systems
MAP_CONNECTIONS = [
    # ["EXAM-1", "EXAM-2", "internal"],
]

# Planetary interaction data per primary system. Auto-generated by bootstrap.
# Each planet: {planet_id, name, type_id, type}.
PI_DATA = {
    # "EXAM-1": [{"planet_id": 40000000, "name": "EXAM-1 I", "type_id": 11, "type": "Planet (Temperate)"}],
}
