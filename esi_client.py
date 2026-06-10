"""
EVE ESI API Client with in-memory caching.
Handles all data fetching from ESI and zKillboard.
"""

import threading
import time
import requests
from typing import Optional
from eve_constants import ESI_BASE, ESI_DATASOURCE, CACHE_TTL, ZKILL_BASE

# Simple in-memory cache. Routes fetch killmails from ThreadPoolExecutor
# workers, so all _cache access must hold _cache_lock.
_cache = {}
_cache_lock = threading.Lock()
MAX_CACHE_SIZE = 1000  # Maximum number of items in cache


def _get_cached(key: str) -> Optional[dict]:
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
    url = f"{ESI_BASE}{path}"
    if params is None:
        params = {}
    params["datasource"] = ESI_DATASOURCE
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "AstrumMechanica-IntelDash/1.0 (contact: in-game)"
    }
    
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


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

    url = f"{ESI_BASE}/universe/ids/"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "AstrumMechanica-IntelDash/1.0 (contact: in-game)"
    }
    params = {"datasource": ESI_DATASOURCE}
    resp = requests.post(url, json=names, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
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


def resolve_constellation_name(name: str) -> Optional[int]:
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
        print(f"Failed to resolve constellation '{name}': {e}")

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

    url = f"{ESI_BASE}/characters/affiliation/"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "AstrumMechanica-IntelDash/1.0 (contact: in-game)"
    }
    params = {"datasource": ESI_DATASOURCE}
    resp = requests.post(url, json=character_ids, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
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
    cache_key = f"zkill_system_{system_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    try:
        headers = {
            "Accept": "application/json",
            "User-Agent": "AstrumMechanica-IntelDash/1.0"
        }
        url = f"{ZKILL_BASE}/kills/systemID/{system_id}/"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _set_cache(cache_key, data, "zkill")
        return data
    except Exception as e:
        print(f"zKill error for system {system_id}: {e}")
        return []


def get_zkill_region(region_id: int) -> list:
    """Get recent kills in a region from zKillboard."""
    cache_key = f"zkill_region_{region_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    try:
        headers = {
            "Accept": "application/json",
            "User-Agent": "AstrumMechanica-IntelDash/1.0"
        }
        url = f"{ZKILL_BASE}/kills/regionID/{region_id}/"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _set_cache(cache_key, data, "zkill")
        return data
    except Exception as e:
        print(f"zKill error for region {region_id}: {e}")
        return []


def get_zkill_alliance(alliance_id: int) -> list:
    """Get recent kills for an alliance from zKillboard."""
    cache_key = f"zkill_alliance_{alliance_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    try:
        headers = {
            "Accept": "application/json",
            "User-Agent": "AstrumMechanica-IntelDash/1.0"
        }
        # Fetching kills where alliance is attacker or victim? Usually "kills/allianceID/..." gets both
        # To get intel on what they fly, we mostly care about their kills (attackers)
        url = f"{ZKILL_BASE}/kills/allianceID/{alliance_id}/"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        _set_cache(cache_key, data, "zkill")
        return data
    except Exception as e:
        print(f"zKill error for alliance {alliance_id}: {e}")
        return []


def get_zkill_corporation(corp_id: int) -> list:
    """Get recent kills for a corporation from zKillboard."""
    cache_key = f"zkill_corporation_{corp_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    try:
        headers = {
            "Accept": "application/json",
            "User-Agent": "AstrumMechanica-IntelDash/1.0"
        }
        url = f"{ZKILL_BASE}/kills/corporationID/{corp_id}/"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        _set_cache(cache_key, data, "zkill")
        return data
    except Exception as e:
        print(f"zKill error for corporation {corp_id}: {e}")
        return []


def get_zkill_char_stats(char_id: int) -> dict:
    """Get lifetime kill stats for a character from zKillboard stats API."""
    cache_key = f"zkill_stats_{char_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    try:
        headers = {"Accept": "application/json", "User-Agent": "AstrumMechanica-IntelDash/1.0"}
        url = f"{ZKILL_BASE}/stats/characterID/{char_id}/"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json() or {}
        _set_cache(cache_key, data, "zkill_stats")
        return data
    except Exception as e:
        print(f"zKill stats error for char {char_id}: {e}")
        return {}


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
        print(f"ESI error for killmail {killmail_id}: {e}")
        return {}
