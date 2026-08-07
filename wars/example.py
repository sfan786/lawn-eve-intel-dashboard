"""
Template for a war module. Copy to private/wars/<name>.py and edit.

A war is two coalitions fighting over a set of regions. It is tracked
separately from the deployment, so the ledger survives the alliance moving
home — and so a war can be watched without being fought in.

WHERE THIS FILE BELONGS
-----------------------
In `private/wars/`, not here. A live war module lists both coalitions' current
alliance rosters; for the side you are on, that is your standings list, which
this repo is public and must not carry. `private/` is already gitignored,
dockerignored, and mounted read-only into the container, so dropping a module
there needs no extra plumbing — see "Deployment Data Is Not Public" in
CLAUDE.md. Only this template and wars that have become history belong in the
committed directory.

Nothing here is auto-generated: there is no geography to walk, so there is no
bootstrap. Resolve the IDs with:

    python tools/esi_lookup.py --json alliance "Some Alliance"

Once the ledger has data, the /war page's "unaligned in the zone" panel ranks
alliances fighting in these regions that are on neither roster, and hands you
the config line to paste back here. That is the intended way to grow a roster:
start with the entities you are sure of and let the killmails find the rest.
"""

# Stable key. It scopes every stored kill, so changing it after ingest starts
# hides the existing ledger. Lowercase slug.
WAR_ID = "example-war"

NAME = "Example War"
SHORT_NAME = "EXAMPLE"

# When the fighting started. The page's full-war range reaches back to this
# date, and tools/backfill_war.py defaults its walk to it.
START_DATE = "2026-03-01"

DESCRIPTION = "One-line summary shown under the page title."

# Regions the war is fought in. The poller walks exactly these, so keep the
# list to where fighting actually happens — each entry is a zKillboard request
# per cycle. IDs are validated against ESI's region catalogue at load.
REGIONS = [
    {"id": 10000066, "name": "Perrigen Falls"},
]

# The two coalitions.
#
# Corporation entries beat alliance entries when both match, so a corp that
# has left its alliance's side can be listed explicitly without splitting the
# alliance roster.
#
# `color` drives every chart and feed row for that side. The defaults are
# hostile-red for A and friendly-green for B, matching the rest of the
# dashboard; override when neither side is "ours".
SIDES = {
    "a": {
        "label": "Attacker Coalition",
        "short": "ATK",
        "color": "#ff3355",
        "alliance_ids": [
            # 99000001,   # Some Alliance <TICK>
        ],
        "corporation_ids": [],
    },
    "b": {
        "label": "Defender Coalition",
        "short": "DEF",
        "color": "#00ff88",
        "alliance_ids": [],
        "corporation_ids": [],
    },
}

# Optional. Alliances *you* are in, if you are a belligerent. Drives the
# "our war record" panel — kills, losses and busiest systems for these
# entities alone. Leave empty when watching someone else's war.
HOME_ALLIANCE_IDS = []


# ---------------------------------------------------------------------------
# Deriving a roster from the active deployment
# ---------------------------------------------------------------------------
# When one side is "us and our blues", do not paste the standings list here —
# it will drift the moment standings change, and then the ledger quietly
# misattributes kills. Import it instead, so a standings edit flows straight
# into the war:
#
#     from deployments import ACTIVE as _D
#
#     SIDES["b"]["alliance_ids"] = [_D.ALLIANCE["id"], *_D.FRIENDLY_ALLIANCE_IDS]
#     SIDES["b"]["corporation_ids"] = [
#         c["id"] for c in getattr(_D, "FRIENDLY_STANDING_CORPORATIONS", [])
#     ]
#     HOME_ALLIANCE_IDS = [_D.ALLIANCE["id"]]
#
# The trade-off is that the war then only classifies correctly while that
# deployment is active. That is usually right for a war you are fighting, and
# wrong for one you are only watching — in which case list the IDs explicitly.
#
# Either way, stored kills keep the ids of everyone involved, so
# tools/reclassify_war.py can recompute sides after a roster change without
# re-fetching anything.
