"""
Shared system state for all route blueprints.
SystemState is populated once at startup by resolve_all_systems() and then
shared (read-only) across all request handlers.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from config import PRIMARY_CONSTELLATION_IDS, REGION, REGION_ID, NEIGHBOR_SYSTEM_NAMES
import esi_client


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

    region_label = REGION.get("name", str(REGION_ID))
    print(f"[*] Loading region {REGION_ID} ({region_label})...")
    try:
        region_info = esi_client.get_region_info(REGION_ID)
        region_constellation_ids = region_info.get("constellations", [])
        print(f"  [+] Region has {len(region_constellation_ids)} constellations")
    except Exception as e:
        print(f"  [!] Failed to load region info: {e}")
        print(f"  [*] Falling back to primary constellations only")
        region_constellation_ids = PRIMARY_CONSTELLATION_IDS

    print(f"[*] Resolving {len(region_constellation_ids)} {region_label} constellations...")
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
                print(f"  [!] Error loading constellation {cid}: {e}")

    all_system_ids = []
    for cid, info in constellation_infos.items():
        for sys_id in info.get("systems", []):
            all_system_ids.append((cid, sys_id))

    print(f"[*] Resolving {len(all_system_ids)} {region_label} systems...")
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
                print(f"  [!] Error loading system {sys_id}: {e}")

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
        print(f"  [+] {info.get('name')} (ID: {cid}) -> {len(systems)} systems [{tag}]")

    for cid, cdata in s.constellation_data.items():
        if cdata.get("is_primary"):
            s.primary_system_ids.update(cdata["systems"].keys())

    print(f"[*] Resolving {len(NEIGHBOR_SYSTEM_NAMES)} neighbor systems...")
    if NEIGHBOR_SYSTEM_NAMES:
        try:
            id_result = esi_client.post_universe_ids(NEIGHBOR_SYSTEM_NAMES)
            resolved_systems = id_result.get("systems", [])
            print(f"  [+] Resolved {len(resolved_systems)} / {len(NEIGHBOR_SYSTEM_NAMES)} names")

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
                        print(f"  [!] Error loading neighbor {neighbor_entries[sid]}: {e}")

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
            print(f"  [!] Failed to resolve neighbor names: {e}")

    for cdata in s.constellation_data.values():
        s.all_monitored_ids.update(cdata["systems"].keys())
    s.all_monitored_ids.update(s.neighbor_systems.keys())

    region_count = sum(len(c["systems"]) for c in s.constellation_data.values())
    primary_count = len(s.primary_system_ids)
    neighbor_count = len(s.neighbor_systems)
    elapsed = _time.monotonic() - t_start
    print(f"[*] Total: {len(s.constellation_data)} constellations, "
          f"{primary_count} primary + {region_count - primary_count} region + {neighbor_count} neighbor "
          f"= {len(s.all_monitored_ids)} systems ({elapsed:.1f}s)")
