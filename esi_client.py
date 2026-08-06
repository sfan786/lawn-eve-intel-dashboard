"""
EVE ESI API Client with in-memory caching.
Handles all data fetching from ESI and zKillboard.

All HTTP goes through a single pooled Session (`_session`) so the parallel
killmail prefetches reuse connections instead of paying a TLS handshake each,
and through `_pause_if_error_limited()` so every thread cooperatively backs off
when ESI's rolling error budget runs low.
"""

import logging
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from eve_constants import (
    CACHE_TTL,
    ESI_BASE,
    ESI_DATASOURCE,
    ESI_ERROR_LIMIT_FLOOR,
    HTTP_MAX_RETRIES,
    HTTP_POOL_SIZE,
    HTTP_RETRY_STATUSES,
    USER_AGENT,
    ZKILL_BASE,
)

log = logging.getLogger(__name__)

# Simple in-memory cache. Routes fetch killmails from ThreadPoolExecutor
# workers, so all _cache access must hold _cache_lock.
_cache = {}
_cache_lock = threading.Lock()
MAX_CACHE_SIZE = 1000  # Maximum number of items in cache


def _build_session() -> requests.Session:
    """Pooled session with transparent retry on transient upstream failures.

    raise_on_status=False leaves the final response for the caller to inspect —
    we still want to read the error-limit headers off a failed response before
    raise_for_status() fires.
    """
    session = requests.Session()
    retry = Retry(
        total=HTTP_MAX_RETRIES,
        backoff_factor=0.5,
        status_forcelist=HTTP_RETRY_STATUSES,
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(
        pool_connections=HTTP_POOL_SIZE,
        pool_maxsize=HTTP_POOL_SIZE,
        max_retries=retry,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"Accept": "application/json", "User-Agent": USER_AGENT})
    return session


_session = _build_session()

# Cooperative error-limit backoff shared by every thread.
_error_limit_lock = threading.Lock()
_error_limit_until = 0.0


def _pause_if_error_limited():
    """Block while an ESI error-limit backoff is armed."""
    while True:
        with _error_limit_lock:
            wait = _error_limit_until - time.time()
        if wait <= 0:
            return
        time.sleep(min(wait, 5))


def _note_error_limit(resp):
    """Arm a backoff when ESI reports the error budget is nearly spent.

    A 420 means we already blew through it; a low remaining count means we are
    about to. Either way every thread pauses until the window resets.
    """
    global _error_limit_until
    try:
        remain = int(resp.headers.get("X-Esi-Error-Limit-Remain"))
        reset = int(resp.headers.get("X-Esi-Error-Limit-Reset") or 60)
    except (TypeError, ValueError):
        return  # header absent or non-numeric (also covers mocked responses)

    if resp.status_code == 420 or remain <= ESI_ERROR_LIMIT_FLOOR:
        with _error_limit_lock:
            until = time.time() + max(reset, 1)
            if until > _error_limit_until:
                _error_limit_until = until
                log.warning(
                    "ESI error budget low (remain=%s, status=%s) — pausing all requests for %ss",
                    remain, resp.status_code, reset,
                )


def _get_cached(key: str) -> dict | None:
    """Return cached data if still valid, else None."""
    with _cache_lock:
        if key in _cache:
            entry = _cache[key]
            if time.time() < entry["expires_at"]:
                return entry["data"]
            else:
                del _cache[key]  # Clean up expired item on access
        return None


def _set_cache(key: str, data, ttl_category: str):
    """Store data in cache with its exact expiry, managing size."""
    current_time = time.time()

    with _cache_lock:
        # Prune entries if cache is full
        if len(_cache) >= MAX_CACHE_SIZE:
            # 1. Remove expired items
            expired_keys = [
                k for k, v in _cache.items()
                if current_time >= v["expires_at"]
            ]
            for k in expired_keys:
                del _cache[k]

            # 2. If still full, remove the 20% closest to expiry
            if len(_cache) >= MAX_CACHE_SIZE:
                sorted_by_expiry = sorted(_cache.items(), key=lambda item: item[1]["expires_at"])
                to_remove = int(MAX_CACHE_SIZE * 0.2)
                for k, _ in sorted_by_expiry[:to_remove]:
                    del _cache[k]

        _cache[key] = {"data": data, "expires_at": current_time + CACHE_TTL.get(ttl_category, 300)}


def esi_get(path: str, params: dict = None) -> dict:
    """Make a GET request to ESI."""
    params = dict(params or {})
    params["datasource"] = ESI_DATASOURCE

    _pause_if_error_limited()
    resp = _session.get(f"{ESI_BASE}{path}", params=params, timeout=15)
    _note_error_limit(resp)
    resp.raise_for_status()
    return resp.json()


def esi_post(path: str, payload) -> dict:
    """Make a POST request to ESI (bulk resolution endpoints)."""
    _pause_if_error_limited()
    resp = _session.post(
        f"{ESI_BASE}{path}",
        json=payload,
        params={"datasource": ESI_DATASOURCE},
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    _note_error_limit(resp)
    resp.raise_for_status()
    return resp.json()


def _zkill_get(path: str, cache_key: str, ttl_category: str = "zkill", timeout: int = 10):
    """Fetch a zKillboard endpoint, returning the cached value when fresh.

    zKill is a best-effort source — every caller treats an outage as "no kills"
    rather than an error, so failures are logged and flattened to a default.
    """
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        resp = _session.get(f"{ZKILL_BASE}{path}", timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning("zKill error for %s: %s", path, e)
        return {} if ttl_category == "zkill_stats" else []

    if ttl_category == "zkill_stats":
        data = data or {}
    _set_cache(cache_key, data, ttl_category)
    return data


# ============ Universe / Static Data ============

def get_all_constellation_ids() -> list:
    """Get all constellation IDs in the game."""
    cache_key = "all_constellation_ids"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get("/universe/constellations/")
    _set_cache(cache_key, data, "constellation_info")
    return data


def get_constellation_info(constellation_id: int) -> dict:
    """Get constellation details: name, region, systems."""
    cache_key = f"constellation_{constellation_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get(f"/universe/constellations/{constellation_id}/")
    _set_cache(cache_key, data, "constellation_info")
    return data


def get_region_info(region_id: int) -> dict:
    """Get region details: name, constellation IDs."""
    cache_key = f"region_{region_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get(f"/universe/regions/{region_id}/")
    _set_cache(cache_key, data, "region_info")
    return data


def get_all_regions() -> list:
    """Every known-space region as [{"id", "name"}], sorted by name.

    Two calls (region list + bulk names) cached for a day, because regions are
    as static as EVE data gets. Wormhole (11000000+) and Abyssal (12000000+)
    regions are excluded: their names are procedural noise like "A-R00001",
    there is nothing to watch in a picker, and they'd triple the list length.
    Pochven (10000070) sits in the known-space range and is kept.
    """
    cache_key = "all_regions"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    region_ids = [rid for rid in esi_get("/universe/regions/") if rid < 11000000]
    regions = []
    for chunk_start in range(0, len(region_ids), 1000):
        chunk = region_ids[chunk_start:chunk_start + 1000]
        for item in esi_post("/universe/names/", chunk):
            regions.append({"id": item["id"], "name": item["name"]})

    regions.sort(key=lambda r: r["name"])
    _set_cache(cache_key, regions, "region_info")
    return regions


def post_universe_ids(names: list) -> dict:
    """Bulk-resolve names to IDs via POST /universe/ids/.
    Returns dict with 'systems', 'constellations', etc. lists.
    """
    if not names:
        return {}
    cache_key = f"universe_ids_{','.join(sorted(names))}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_post("/universe/ids/", names)
    _set_cache(cache_key, data, "region_info")
    return data


def get_system_info(system_id: int) -> dict:
    """Get system details: name, security status, etc."""
    cache_key = f"system_{system_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get(f"/universe/systems/{system_id}/")
    _set_cache(cache_key, data, "system_info")
    return data


def resolve_constellation_name(name: str) -> int | None:
    """Find a constellation ID by name using POST /universe/ids/."""
    cache_key = f"constellation_resolve_{name}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        data = post_universe_ids([name])
        constellations = data.get("constellations", [])
        if constellations:
            result = constellations[0]["id"]
            _set_cache(cache_key, result, "constellation_info")
            return result
    except Exception as e:
        log.warning("Failed to resolve constellation '%s': %s", name, e)

    return None


# ============ Sovereignty ============

def get_sovereignty_map() -> list:
    """Get sovereignty data for all nullsec systems."""
    cache_key = "sovereignty_map"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get("/sovereignty/map/")
    _set_cache(cache_key, data, "sovereignty")
    return data


def get_sovereignty_structures() -> list:
    """Get sovereignty structures (TCU/iHub) with ADM levels.
    Returns list with alliance_id, solar_system_id,
    structure_type_id (TCU=32226, iHub=32458),
    vulnerability_occupancy_level (= ADM, 1.0-6.0).
    """
    cache_key = "sovereignty_structures"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get("/sovereignty/structures/")
    _set_cache(cache_key, data, "sovereignty_structures")
    return data


def get_sovereignty_campaigns() -> list:
    """Get active sovereignty campaigns (entosis timers)."""
    cache_key = "sovereignty_campaigns"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get("/sovereignty/campaigns/")
    _set_cache(cache_key, data, "sovereignty")
    return data


# ============ Activity Stats ============

def get_system_kills() -> list:
    """Get kill stats per system (ship, pod, NPC kills)."""
    cache_key = "system_kills"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get("/universe/system_kills/")
    _set_cache(cache_key, data, "system_kills")
    return data


def get_system_jumps() -> list:
    """Get jump counts per system."""
    cache_key = "system_jumps"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get("/universe/system_jumps/")
    _set_cache(cache_key, data, "system_jumps")
    return data


# ============ Alliance/Corp Resolution ============

def get_alliance_info(alliance_id: int) -> dict:
    """Get alliance name and details."""
    cache_key = f"alliance_{alliance_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get(f"/alliances/{alliance_id}/")
    _set_cache(cache_key, data, "entity_info")
    return data


def get_corporation_info(corp_id: int) -> dict:
    """Get corporation name and details."""
    cache_key = f"corporation_{corp_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = esi_get(f"/corporations/{corp_id}/")
    _set_cache(cache_key, data, "entity_info")
    return data


# ============ Killmail Enrichment ============

def get_type_name(type_id: int) -> str:
    """Get the name of a type (ship, item, etc.) by ID."""
    cache_key = f"type_{type_id}"
    cached = _get_cached(cache_key)  # static data, long cache
    if cached is not None:
        return cached

    try:
        data = esi_get(f"/universe/types/{type_id}/")
        name = data.get("name", f"Type {type_id}")
        group_id = data.get("group_id", 0)
        _set_cache(cache_key, name, "system_info")
        _set_cache(f"type_group_{type_id}", group_id, "system_info")
        return name
    except Exception:
        return f"Type {type_id}"


def get_type_group_id(type_id: int) -> int:
    """Get the group_id of a type (ship class, etc.) by ID."""
    if not type_id:
        return 0
    cache_key = f"type_group_{type_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        data = esi_get(f"/universe/types/{type_id}/")
        group_id = data.get("group_id", 0)
        _set_cache(cache_key, group_id, "system_info")
        return group_id
    except Exception:
        return 0


def bulk_resolve_names(ids: list) -> None:
    """POST /universe/names/ — pre-populate character/corp/alliance/type caches in one call.
    Eliminates N sequential ESI requests during killmail enrichment; call before the loop.
    Already-cached IDs are filtered out to avoid redundant network requests.
    """
    if not ids:
        return
    unique_ids = {int(i) for i in ids if i}
    if not unique_ids:
        return

    current_time = time.time()
    uncached = []
    # Single lock acquisition to check all IDs — avoids repeated lock/unlock per ID.
    with _cache_lock:
        for i in unique_ids:
            cached = False
            for prefix in ("character_", "corporation_", "alliance_", "type_"):
                entry = _cache.get(f"{prefix}{i}")
                if entry:
                    if current_time < entry["expires_at"]:
                        cached = True
                        break
                    else:
                        del _cache[f"{prefix}{i}"]
            if not cached:
                uncached.append(i)

    if not uncached:
        return
    try:
        for chunk_start in range(0, len(uncached), 1000):
            chunk = uncached[chunk_start:chunk_start + 1000]
            for item in esi_post("/universe/names/", chunk):
                eid = item["id"]
                name = item["name"]
                category = item.get("category", "")
                if category == "character":
                    _set_cache(f"character_{eid}", name, "entity_info")
                elif category == "corporation":
                    # Cache as {"name": ...} to match get_corporation_info() return shape
                    _set_cache(f"corporation_{eid}", {"name": name}, "entity_info")
                elif category == "alliance":
                    _set_cache(f"alliance_{eid}", {"name": name}, "entity_info")
                elif category == "inventory_type":
                    _set_cache(f"type_{eid}", name, "system_info")
    except Exception as e:
        log.warning("bulk_resolve_names error: %s", e)


def bulk_character_affiliations(character_ids: list) -> list:
    """POST /characters/affiliation/ — bulk corp/alliance lookup for up to 1000 IDs.
    Returns [{character_id, corporation_id, alliance_id?}, ...]
    """
    if not character_ids:
        return []
    # Cache key based on sorted IDs (order-independent)
    cache_key = f"affiliations_{','.join(str(i) for i in sorted(character_ids))}"
    cached = _get_cached(cache_key)  # short TTL — affiliations can change
    if cached is not None:
        return cached

    data = esi_post("/characters/affiliation/", character_ids)
    _set_cache(cache_key, data, "sovereignty")
    return data


def get_character_name(character_id: int) -> str:
    """Get character name by ID."""
    cache_key = f"character_{character_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        data = esi_get(f"/characters/{character_id}/")
        name = data.get("name", f"Pilot {character_id}")
        _set_cache(cache_key, name, "entity_info")
        return name
    except Exception:
        return f"Pilot {character_id}"


# ============ zKillboard ============

def get_zkill_system(system_id: int) -> list:
    """Get recent kills in a system from zKillboard."""
    return _zkill_get(f"/kills/systemID/{system_id}/", f"zkill_system_{system_id}")


def get_zkill_region(region_id: int) -> list:
    """Get recent kills in a region from zKillboard."""
    return _zkill_get(f"/kills/regionID/{region_id}/", f"zkill_region_{region_id}")


def get_zkill_alliance(alliance_id: int) -> list:
    """Get recent kills for an alliance from zKillboard.

    Returns kills where the alliance appears on either side; doctrine analysis
    filters to the attacker side to see what they actually fly.
    """
    return _zkill_get(f"/kills/allianceID/{alliance_id}/", f"zkill_alliance_{alliance_id}", timeout=15)


def get_zkill_corporation(corp_id: int) -> list:
    """Get recent kills for a corporation from zKillboard."""
    return _zkill_get(f"/kills/corporationID/{corp_id}/", f"zkill_corporation_{corp_id}", timeout=15)


def get_zkill_char_stats(char_id: int) -> dict:
    """Get lifetime kill stats for a character from zKillboard stats API."""
    return _zkill_get(f"/stats/characterID/{char_id}/", f"zkill_stats_{char_id}", ttl_category="zkill_stats")


def get_killmail(killmail_id: int, killmail_hash: str) -> dict:
    """Get full killmail details from ESI."""
    cache_key = f"killmail_{killmail_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        # ESI endpoint: /killmails/{killmail_id}/{killmail_hash}/
        data = esi_get(f"/killmails/{killmail_id}/{killmail_hash}/")
        # Killmails are immutable, so we can cache them for a long time (usage 'killmail' TTL or default)
        _set_cache(cache_key, data, "killmail")
        return data
    except Exception as e:
        log.warning("ESI error for killmail %s: %s", killmail_id, e)
        return {}
