"""
Shared system state for all route blueprints.
SystemState is populated once at startup by resolve_all_systems() and then
shared (read-only) across all request handlers.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import esi_client
from config import (
    HAS_AO,
    NEIGHBOR_SYSTEM_NAMES,
    POSTURE,
    PRIMARY_CONSTELLATION_IDS,
    REGION,
    REGION_ID,
)

log = logging.getLogger(__name__)


class SystemState:
    def __init__(self):
        self.constellation_data = {}     # cid -> {name, region_id, systems, is_primary}
        self.neighbor_systems = {}       # sys_id -> {name, system_id, security_status, region_name}
        self.primary_constellation_ids_set = set()
        self.primary_system_ids = set()
        self.all_monitored_ids = set()   # All region + neighbor system IDs

    def lookup_system_name(self, sys_id):
        """Look up system name from constellation_data or neighbor_systems."""
        for cdata in self.constellation_data.values():
            if sys_id in cdata["systems"]:
                return cdata["systems"][sys_id]["name"]
        if sys_id in self.neighbor_systems:
            return self.neighbor_systems[sys_id]["name"]
        return ""


# Module-level singleton imported by all blueprints
state = SystemState()


def resolve_all_systems(s: SystemState):
    """Load all region constellations + neighbor systems from ESI, populating s.*."""
    import time as _time

    t_start = _time.monotonic()
    s.primary_constellation_ids_set = set(PRIMARY_CONSTELLATION_IDS)

    # A rootless deployment has no home region to resolve. Walking one anyway
    # would cost a full constellation+system fan-out at every startup to
    # populate state that nothing reads: the sov, activity, map and ADM
    # surfaces are all stood down, and the kill feed resolves system names
    # on demand. Leave every collection empty and return.
    #
    # Keyed on HAS_AO, not HOLDS_SOV: a guest doesn't own its space but very
    # much has a home region to render, defend and watch neighbours of.
    if not HAS_AO and not PRIMARY_CONSTELLATION_IDS:
        log.info("Posture is %s with no primary constellations — skipping region resolution", POSTURE)
        return

    region_label = REGION.get("name", str(REGION_ID))
    log.info("Loading region %s (%s)...", REGION_ID, region_label)
    try:
        region_info = esi_client.get_region_info(REGION_ID)
        region_constellation_ids = region_info.get("constellations", [])
        log.info("  Region has %d constellations", len(region_constellation_ids))
    except Exception as e:
        log.warning("  Failed to load region info: %s", e)
        log.warning("  Falling back to primary constellations only")
        region_constellation_ids = PRIMARY_CONSTELLATION_IDS

    log.info("Resolving %d %s constellations...", len(region_constellation_ids), region_label)
    constellation_infos = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        future_to_cid = {
            pool.submit(esi_client.get_constellation_info, cid): cid
            for cid in region_constellation_ids
        }
        for future in as_completed(future_to_cid):
            cid = future_to_cid[future]
            try:
                constellation_infos[cid] = future.result()
            except Exception as e:
                log.warning("  Error loading constellation %s: %s", cid, e)

    all_system_ids = []
    for cid, info in constellation_infos.items():
        for sys_id in info.get("systems", []):
            all_system_ids.append((cid, sys_id))

    log.info("Resolving %d %s systems...", len(all_system_ids), region_label)
    system_infos = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        future_to_sid = {
            pool.submit(esi_client.get_system_info, sys_id): sys_id
            for _, sys_id in all_system_ids
        }
        for future in as_completed(future_to_sid):
            sys_id = future_to_sid[future]
            try:
                system_infos[sys_id] = future.result()
            except Exception as e:
                log.warning("  Error loading system %s: %s", sys_id, e)

    for cid, info in constellation_infos.items():
        systems = {}
        for sys_id in info.get("systems", []):
            if sys_id in system_infos:
                si = system_infos[sys_id]
                systems[sys_id] = {
                    "name": si.get("name", str(sys_id)),
                    "security_status": round(si.get("security_status", 0), 2),
                    "system_id": sys_id,
                }

        is_primary = cid in s.primary_constellation_ids_set
        s.constellation_data[cid] = {
            "constellation_id": cid,
            "name": info.get("name", str(cid)),
            "region_id": info.get("region_id"),
            "systems": systems,
            "is_primary": is_primary,
            "is_lawn": is_primary,  # backwards-compat for any frontend still reading is_lawn
        }
        tag = "PRIMARY" if is_primary else "REGION"
        log.info("  %s (ID: %s) -> %d systems [%s]", info.get("name"), cid, len(systems), tag)

    for cdata in s.constellation_data.values():
        if cdata.get("is_primary"):
            s.primary_system_ids.update(cdata["systems"].keys())

    log.info("Resolving %d neighbor systems...", len(NEIGHBOR_SYSTEM_NAMES))
    if NEIGHBOR_SYSTEM_NAMES:
        try:
            id_result = esi_client.post_universe_ids(NEIGHBOR_SYSTEM_NAMES)
            resolved_systems = id_result.get("systems", [])
            log.info("  Resolved %d / %d names", len(resolved_systems), len(NEIGHBOR_SYSTEM_NAMES))

            neighbor_entries = {entry["id"]: entry["name"] for entry in resolved_systems}
            neighbor_sys_infos = {}
            with ThreadPoolExecutor(max_workers=10) as pool:
                future_to_sid = {
                    pool.submit(esi_client.get_system_info, sid): sid
                    for sid in neighbor_entries
                }
                for future in as_completed(future_to_sid):
                    sid = future_to_sid[future]
                    try:
                        neighbor_sys_infos[sid] = future.result()
                    except Exception as e:
                        log.warning("  Error loading neighbor %s: %s", neighbor_entries[sid], e)

            neighbor_const_ids = set()
            for si in neighbor_sys_infos.values():
                cid = si.get("constellation_id")
                if cid:
                    neighbor_const_ids.add(cid)

            neighbor_const_infos = {}
            with ThreadPoolExecutor(max_workers=10) as pool:
                future_to_cid = {
                    pool.submit(esi_client.get_constellation_info, cid): cid
                    for cid in neighbor_const_ids
                }
                for future in as_completed(future_to_cid):
                    cid = future_to_cid[future]
                    try:
                        neighbor_const_infos[cid] = future.result()
                    except Exception:
                        pass

            neighbor_region_ids = set()
            for ci in neighbor_const_infos.values():
                rid = ci.get("region_id")
                if rid:
                    neighbor_region_ids.add(rid)

            neighbor_region_infos = {}
            with ThreadPoolExecutor(max_workers=10) as pool:
                future_to_rid = {
                    pool.submit(esi_client.get_region_info, rid): rid
                    for rid in neighbor_region_ids
                }
                for future in as_completed(future_to_rid):
                    rid = future_to_rid[future]
                    try:
                        neighbor_region_infos[rid] = future.result()
                    except Exception:
                        pass

            for sys_id, sys_name in neighbor_entries.items():
                si = neighbor_sys_infos.get(sys_id)
                if not si:
                    continue
                region_name = "Unknown"
                const_id = si.get("constellation_id")
                if const_id and const_id in neighbor_const_infos:
                    rid = neighbor_const_infos[const_id].get("region_id")
                    if rid and rid in neighbor_region_infos:
                        region_name = neighbor_region_infos[rid].get("name", "Unknown")

                s.neighbor_systems[sys_id] = {
                    "name": sys_name,
                    "system_id": sys_id,
                    "security_status": round(si.get("security_status", 0), 2),
                    "region_name": region_name,
                }
        except Exception as e:
            log.warning("  Failed to resolve neighbor names: %s", e)

    for cdata in s.constellation_data.values():
        s.all_monitored_ids.update(cdata["systems"].keys())
    s.all_monitored_ids.update(s.neighbor_systems.keys())

    region_count = sum(len(c["systems"]) for c in s.constellation_data.values())
    primary_count = len(s.primary_system_ids)
    neighbor_count = len(s.neighbor_systems)
    elapsed = _time.monotonic() - t_start
    log.info(
        "Total: %d constellations, %d primary + %d region + %d neighbor = %d systems (%.1fs)",
        len(s.constellation_data), primary_count, region_count - primary_count,
        neighbor_count, len(s.all_monitored_ids), elapsed,
    )
