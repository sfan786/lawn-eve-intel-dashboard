"""
War loader. A war is a named conflict between two coalitions over a set of
regions, tracked independently of whichever deployment happens to be active.

Two locations are searched, private first — the same split, and for the same
reason, as `deployments/`:

  private/wars/<name>.py — live wars. A war module names both coalitions'
                           current alliance rosters, which is exactly the kind
                           of standings information this public repo must not
                           carry. `private/` is already gitignored,
                           dockerignored, and mounted read-only on the server,
                           so a module dropped in there needs no new plumbing.

  wars/<name>.py         — the commented template, and any war old enough that
                           publishing its rosters costs nothing.

Override the private directory with WAR_DIR.

Deliberately unlike `deployments/`, a missing or broken war module is NOT
fatal. A deployment must fail loudly, because booting with the wrong one
silently serves another alliance's map. A war is additive: with none loaded,
/api/wars returns [], the page hides itself, and every other feature is
unaffected. Killing the app over an optional feature would be the worse bug.
"""

import importlib.util
import logging
import os
import re
import sys

log = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAR_DIR = (os.environ.get("WAR_DIR") or "").strip() or os.path.join(_REPO_ROOT, "private", "wars")

_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_SIDES = ("a", "b")

# Fallback palette: side A reads hostile-red and side B friendly-green, which
# matches how the rest of the dashboard colours "them" and "us". A module can
# override per side.
_DEFAULT_COLORS = {"a": "#ff3355", "b": "#00ff88"}


class WarSpec:
    """A validated war definition with membership flattened for lookup.

    The `side_by_*` maps are what the classifier actually reads: a war module
    states rosters in whatever shape is convenient to maintain (and side B
    here is usually derived from the active deployment's standings), but
    classification happens per killmail and must be a dict hit, not a scan.
    """

    def __init__(self, module):
        self.key = module.WAR_ID
        self.name = module.NAME
        self.short_name = getattr(module, "SHORT_NAME", "") or module.NAME
        self.start_date = module.START_DATE
        self.description = getattr(module, "DESCRIPTION", "")
        self.regions = list(module.REGIONS)
        self.region_ids = [r["id"] for r in self.regions]
        self.region_names = {r["id"]: r.get("name", str(r["id"])) for r in self.regions}

        self.sides = {}
        self.side_by_alliance = {}
        self.side_by_corp = {}
        for key in _SIDES:
            raw = module.SIDES[key]
            alliance_ids = [int(i) for i in raw.get("alliance_ids", [])]
            corp_ids = [int(i) for i in raw.get("corporation_ids", [])]
            self.sides[key] = {
                "key": key,
                "label": raw.get("label", key.upper()),
                "short": raw.get("short", raw.get("label", key.upper())),
                "color": raw.get("color") or _DEFAULT_COLORS[key],
                "alliance_count": len(alliance_ids),
                "corporation_count": len(corp_ids),
            }
            for aid in alliance_ids:
                self.side_by_alliance[aid] = key
            for cid in corp_ids:
                self.side_by_corp[cid] = key

        # Alliances the viewer belongs to, used to render a "we" panel. Not a
        # side: a war can be watched by someone who is not in it.
        self.home_alliance_ids = [int(i) for i in getattr(module, "HOME_ALLIANCE_IDS", []) or []]

        # The module's own lists, kept so apply_overrides() can rebuild from a
        # clean base rather than accumulating edits on top of edits.
        self._base_by_alliance = dict(self.side_by_alliance)
        self._base_by_corp = dict(self.side_by_corp)
        self.override_count = 0
        self.decided_alliance_ids = set(self.side_by_alliance)

    def apply_overrides(self, overrides):
        """Layer roster edits made from the page over the module's lists.

        The module stays the reviewable base roster — it is version-controlled
        and someone has to read it — while these are the running corrections a
        war accumulates as membership drifts. Applied to a *copy* of the base
        maps, so removing an override reverts cleanly instead of leaving the
        process with a roster nobody wrote down.
        """
        self.side_by_alliance = dict(self._base_by_alliance)
        self.side_by_corp = dict(self._base_by_corp)
        self.override_count = 0

        for row in overrides or []:
            entity_id = row.get("entity_id")
            if not entity_id:
                continue
            target = (
                self.side_by_corp if row.get("entity_type") == "corporation"
                else self.side_by_alliance
            )
            side = row.get("side")
            if side in ("a", "b"):
                target[entity_id] = side
            else:
                # An explicit "not a belligerent" — drop any inherited side so
                # the page stops counting them, and record the decision so the
                # suggestion panel stops offering them.
                target.pop(entity_id, None)
            self.override_count += 1

        # Entities with an explicit decision, whichever way it went. The
        # suggestion panel needs this: an alliance ruled neutral must not keep
        # coming back, even though it is on no side.
        self.decided_alliance_ids = set(self.side_by_alliance) | {
            r["entity_id"] for r in overrides or []
            if r.get("entity_type") != "corporation" and r.get("entity_id")
        }
        return self

    def side_label(self, key):
        return self.sides[key]["label"] if key in self.sides else "Unaligned"

    def to_json(self):
        return {
            "key": self.key,
            "name": self.name,
            "short_name": self.short_name,
            "start_date": self.start_date,
            "description": self.description,
            "regions": self.regions,
            "sides": self.sides,
            "home_alliance_ids": self.home_alliance_ids,
        }


def _validate(module, source):
    """Return a WarSpec, or None with a warning explaining what was wrong."""
    def bad(msg):
        log.warning("Ignoring war module %s: %s", source, msg)
        return None

    war_id = getattr(module, "WAR_ID", None)
    if not war_id or not isinstance(war_id, str) or not _SLUG.match(war_id):
        return bad("WAR_ID must be a lowercase slug (letters, digits, - and _)")
    if not getattr(module, "NAME", None):
        return bad("NAME is required")

    start = getattr(module, "START_DATE", None)
    if not isinstance(start, str) or not re.match(r"^\d{4}-\d{2}-\d{2}", start):
        return bad("START_DATE must be an ISO date string (YYYY-MM-DD)")

    regions = getattr(module, "REGIONS", None)
    if not regions or not all(isinstance(r, dict) and r.get("id") for r in regions):
        return bad("REGIONS must be a non-empty list of {'id': ..., 'name': ...}")

    sides = getattr(module, "SIDES", None)
    if not isinstance(sides, dict) or set(sides) != set(_SIDES):
        return bad("SIDES must be a dict with exactly the keys 'a' and 'b'")
    for key in _SIDES:
        raw = sides[key]
        if not isinstance(raw, dict):
            return bad(f"SIDES['{key}'] must be a dict")
        if not raw.get("alliance_ids") and not raw.get("corporation_ids"):
            return bad(f"SIDES['{key}'] lists no alliance_ids or corporation_ids")

    try:
        return WarSpec(module)
    except Exception as e:
        return bad(f"could not be read ({e})")


def _load_file(path):
    name = os.path.basename(path).removesuffix(".py")
    mod_name = f"_war_{name}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    # Register before exec so a re-import returns the same object instead of
    # running the module twice.
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def load_all():
    """Every valid war, private first. Never raises."""
    wars = {}
    for directory in (WAR_DIR, os.path.dirname(os.path.abspath(__file__))):
        if not os.path.isdir(directory):
            continue
        for filename in sorted(os.listdir(directory)):
            if not filename.endswith(".py") or filename.startswith("_") or filename == "example.py":
                continue
            path = os.path.join(directory, filename)
            try:
                module = _load_file(path)
            except Exception as e:
                log.warning("Ignoring war module %s: import failed (%s)", path, e)
                continue
            war = _validate(module, path)
            # First definition wins, so a private module shadows a committed
            # one of the same name rather than being overwritten by it.
            if war and war.key not in wars:
                wars[war.key] = war
    return wars


WARS = load_all()


def get(war_id):
    return WARS.get(war_id)


def reload_wars():
    """Re-scan both directories. Used by tests and the backfill tool."""
    global WARS
    WARS = load_all()
    return WARS
