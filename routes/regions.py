"""
Which region a feed endpoint is pointed at.

A sovereign deployment has exactly one answer (its own region) and never needs
to ask. A rootless one has no home to anchor to, so the kill feed and hostile
tracker take a ?region_id= and the UI offers a picker over WATCHED_REGIONS.

The allowlist is the point. These endpoints fan out to zKillboard and then to
ESI for every killmail in the response, so an unvalidated region_id would turn
them into an open proxy that any caller could drive against arbitrary regions —
burning the shared ESI error budget that esi_client's backoff exists to
protect, and doing it from the deployment's IP.
"""

from config import REGION_ID, WATCHED_REGION_IDS


def resolve_region_id(args):
    """Resolve a request's ?region_id= against the watched allowlist.

    Returns (region_id, None) on success, or (None, error_dict) when the
    caller asked for a region this deployment does not watch.
    """
    raw = args.get("region_id")
    if raw is None or raw == "":
        return REGION_ID, None

    try:
        region_id = int(raw)
    except (TypeError, ValueError):
        return None, {"error": "region_id must be an integer"}

    if region_id not in WATCHED_REGION_IDS:
        return None, {
            "error": "region_id is not watched by this deployment",
            "watched_region_ids": sorted(WATCHED_REGION_IDS),
        }

    return region_id, None
