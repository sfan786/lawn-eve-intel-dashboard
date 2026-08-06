"""
Which region a feed endpoint is pointed at.

A sovereign deployment has one obvious answer (its own region). A rootless one
has no home to anchor to and no reason to be fenced in either — an alliance
between homes, or a pilot roaming, wants to look wherever the fight is. So
`region_id` accepts **any known-space region**, and `WATCHED_REGIONS` is a
pinned shortlist surfaced first in the UI rather than a hard allowlist.

Validation still matters, just for a different reason than before. These
endpoints fan out to zKillboard and then to ESI for every killmail in the
response, all from the deployment's IP and shared ESI error budget. Two things
keep that bounded:

  * the id must be a real known-space region, so the endpoint can't be aimed at
    arbitrary numbers to generate cache-missing upstream requests, and
  * the callers are rate limited per IP (see routes/limiter.py).

Wormhole and Abyssal regions are excluded along with the catalogue in
esi_client.get_all_regions() — nothing in this dashboard reads them usefully.
"""

import logging

import esi_client
from config import REGION_ID, WATCHED_REGIONS

log = logging.getLogger(__name__)


def known_region_ids():
    """Valid region ids, or None if ESI is unreachable and we can't tell."""
    try:
        return {r["id"] for r in esi_client.get_all_regions()}
    except Exception as e:
        log.warning("Region catalogue unavailable, falling back to pinned regions: %s", e)
        return None


def pinned_regions():
    """The deployment's shortlist, shown first in the picker."""
    return [r for r in WATCHED_REGIONS if isinstance(r, dict) and r.get("id")]


def resolve_region_id(args):
    """Resolve a request's ?region_id= to a validated region.

    Returns (region_id, None) on success, or (None, error_dict) when the id is
    not a real region.
    """
    raw = args.get("region_id")
    if raw is None or raw == "":
        return REGION_ID, None

    try:
        region_id = int(raw)
    except (TypeError, ValueError):
        return None, {"error": "region_id must be an integer"}

    valid = known_region_ids()
    if valid is None:
        # ESI is down, so we can't confirm the id is real. Fall back to the
        # pinned list rather than either blocking every request or forwarding
        # an unvalidated id upstream while ESI is already struggling.
        valid = {r["id"] for r in pinned_regions()} | {REGION_ID}

    if region_id not in valid:
        return None, {"error": "not a known-space region id"}

    return region_id, None
