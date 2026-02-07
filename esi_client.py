"""
EVE ESI API Client with in-memory caching.
Handles all data fetching from ESI and zKillboard.
"""

import time
import requests
from typing import Optional
from config import ESI_BASE, ESI_DATASOURCE, CACHE_TTL, ZKILL_BASE, ZKILL_RECENT_HOURS

# Simple in-memory cache
_cache = {}


def _get_cached(key: str, ttl_category: str) -> Optional[dict]:
    """Return cached data if still valid, else None."""
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < CACHE_TTL.get(ttl_category, 300):
            return entry["data"]
    return None


def _set_cache(key: str, data):
    """Store data in cache."""
    _cache[key] = {"data": data, "timestamp": time.time()}


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
    cached = _get_cached(cache_key, "constellation_info")
    if cached:
        return cached
    
    data = esi_get("/universe/constellations/")
    _set_cache(cache_key, data)
    return data


def get_constellation_info(constellation_id: int) -> dict:
    """Get constellation details: name, region, systems."""
    cache_key = f"constellation_{constellation_id}"
    cached = _get_cached(cache_key, "constellation_info")
    if cached:
        return cached
    
    data = esi_get(f"/universe/constellations/{constellation_id}/")
    _set_cache(cache_key, data)
    return data


def get_system_info(system_id: int) -> dict:
    """Get system details: name, security status, etc."""
    cache_key = f"system_{system_id}"
    cached = _get_cached(cache_key, "system_info")
    if cached:
        return cached
    
    data = esi_get(f"/universe/systems/{system_id}/")
    _set_cache(cache_key, data)
    return data


def resolve_constellation_name(name: str) -> Optional[int]:
    """Find a constellation ID by name using ESI search."""
    cache_key = f"constellation_resolve_{name}"
    cached = _get_cached(cache_key, "constellation_info")
    if cached:
        return cached
    
    # Use the search endpoint
    try:
        data = esi_get("/search/", params={
            "categories": "constellation",
            "search": name,
            "strict": "true"
        })
        if "constellation" in data and len(data["constellation"]) > 0:
            result = data["constellation"][0]
            _set_cache(cache_key, result)
            return result
    except Exception as e:
        print(f"Failed to resolve constellation '{name}': {e}")
    
    return None


# ============ Sovereignty ============

def get_sovereignty_map() -> list:
    """Get sovereignty data for all nullsec systems."""
    cache_key = "sovereignty_map"
    cached = _get_cached(cache_key, "sovereignty")
    if cached:
        return cached
    
    data = esi_get("/sovereignty/map/")
    _set_cache(cache_key, data)
    return data


def get_sovereignty_campaigns() -> list:
    """Get active sovereignty campaigns (entosis timers)."""
    cache_key = "sovereignty_campaigns"
    cached = _get_cached(cache_key, "sovereignty")
    if cached:
        return cached
    
    data = esi_get("/sovereignty/campaigns/")
    _set_cache(cache_key, data)
    return data


# ============ Activity Stats ============

def get_system_kills() -> list:
    """Get kill stats per system (ship, pod, NPC kills)."""
    cache_key = "system_kills"
    cached = _get_cached(cache_key, "system_kills")
    if cached:
        return cached
    
    data = esi_get("/universe/system_kills/")
    _set_cache(cache_key, data)
    return data


def get_system_jumps() -> list:
    """Get jump counts per system."""
    cache_key = "system_jumps"
    cached = _get_cached(cache_key, "system_jumps")
    if cached:
        return cached
    
    data = esi_get("/universe/system_jumps/")
    _set_cache(cache_key, data)
    return data


# ============ Alliance/Corp Resolution ============

def get_alliance_info(alliance_id: int) -> dict:
    """Get alliance name and details."""
    cache_key = f"alliance_{alliance_id}"
    cached = _get_cached(cache_key, "constellation_info")  # slow-changing
    if cached:
        return cached
    
    data = esi_get(f"/alliances/{alliance_id}/")
    _set_cache(cache_key, data)
    return data


def get_corporation_info(corp_id: int) -> dict:
    """Get corporation name and details."""
    cache_key = f"corporation_{corp_id}"
    cached = _get_cached(cache_key, "constellation_info")
    if cached:
        return cached
    
    data = esi_get(f"/corporations/{corp_id}/")
    _set_cache(cache_key, data)
    return data


# ============ zKillboard ============

def get_zkill_system(system_id: int) -> list:
    """Get recent kills in a system from zKillboard."""
    cache_key = f"zkill_system_{system_id}"
    cached = _get_cached(cache_key, "zkill")
    if cached:
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
        _set_cache(cache_key, data)
        return data
    except Exception as e:
        print(f"zKill error for system {system_id}: {e}")
        return []


def get_zkill_region(region_id: int) -> list:
    """Get recent kills in a region from zKillboard."""
    cache_key = f"zkill_region_{region_id}"
    cached = _get_cached(cache_key, "zkill")
    if cached:
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
        _set_cache(cache_key, data)
        return data
    except Exception as e:
        print(f"zKill error for region {region_id}: {e}")
        return []
