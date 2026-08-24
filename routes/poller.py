"""
Background ESI poller — keeps the historical record advancing without traffic.

ADM sparklines, the grinding-rate estimate, the activity heatmap, and the 7-day
baselines behind regional spike detection are all computed from the
`adm_snapshots` and `activity_snapshots` tables. Those writes used to happen as
a side effect of serving GET /api/sovereignty and GET /api/activity, so the
record only advanced while somebody had a browser open — leaving holes
overnight and skewing every baseline built on top of them.

This thread writes them on a fixed interval instead, so the history is a
function of wall-clock time rather than of who happened to be looking.

Concurrency: db's snapshot helpers dedupe on (deployment, system, ADM, hour)
with a NOT EXISTS guard, so running a poller in every gunicorn worker is safe —
it costs a redundant ESI fetch, not a duplicate row. Note that threads do not
survive fork, so under `preload_app` this must be started from gunicorn's
post_fork hook (see gunicorn.conf.py), never at import time.
"""

import logging
import os
import threading
import time

import db
import esi_client
from config import HAS_AO, HOLDS_SOV, POSTURE
from eve_constants import SOV_HUB_TYPE_IDS
from routes import analytics_routes
from routes.system_state import state

log = logging.getLogger(__name__)

# How often to sample. db.SNAPSHOT_INTERVAL (1h) is what actually decides
# whether a sample is kept, so polling more often than that just means a
# missed window costs less — it does not inflate the table.
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "900"))

_thread = None
_thread_lock = threading.Lock()


def snapshot_sovereignty():
    """Record current ADM for every monitored system. Returns rows written."""
    sov_map = esi_client.get_sovereignty_map()

    adm_by_system = {}
    try:
        for struct in esi_client.get_sovereignty_structures():
            if struct.get("structure_type_id") in SOV_HUB_TYPE_IDS:
                adm_by_system[struct.get("solar_system_id")] = struct.get(
                    "vulnerability_occupancy_level", 0
                )
    except Exception as e:
        log.warning("Sov structures unavailable, ADM will be 0 this cycle: %s", e)

    batch = []
    for entry in sov_map:
        sys_id = entry.get("system_id")
        if sys_id not in state.all_monitored_ids:
            continue
        alliance_name = None
        alliance_id = entry.get("alliance_id")
        if alliance_id:
            try:
                alliance_name = esi_client.get_alliance_info(alliance_id).get("name")
            except Exception:
                pass
        batch.append(
            (sys_id, state.lookup_system_name(sys_id), adm_by_system.get(sys_id, 0), alliance_name)
        )

    db.snapshot_adm_batch(batch)
    return len(batch)


def snapshot_activity():
    """Record kills/jumps for every monitored system. Returns rows written."""
    kills_by_system = {e["system_id"]: e for e in esi_client.get_system_kills()}
    jumps_by_system = {e["system_id"]: e for e in esi_client.get_system_jumps()}

    batch = [
        (
            sys_id,
            kills_by_system.get(sys_id, {}).get("ship_kills", 0),
            kills_by_system.get(sys_id, {}).get("pod_kills", 0),
            kills_by_system.get(sys_id, {}).get("npc_kills", 0),
            jumps_by_system.get(sys_id, {}).get("ship_jumps", 0),
        )
        for sys_id in state.all_monitored_ids
    ]

    db.snapshot_activity_batch(batch)
    return len(batch)


def poll_once():
    """Run one full sampling cycle. Never raises — a bad cycle is skipped."""
    # The two snapshots answer to different postures.
    #
    # ADM is ownership-specific: snapshot_sovereignty records whatever ESI
    # reports for every monitored system and db only drops rows where ADM is 0,
    # so without sov of our own this files the *current holder's* ADM under our
    # deployment_id and AdmTrends/GrindingPlan sparkline someone else's sov as
    # if it were ours.
    #
    # Activity (kills/jumps) is ownership-neutral and a guest still needs it —
    # the heatmap and the 7-day baselines behind regional spike detection are
    # both built on activity_snapshots, and both render under a guest posture.
    jobs = []
    if HOLDS_SOV:
        jobs.append(("sovereignty", snapshot_sovereignty))
    if HAS_AO:
        jobs.append(("activity", snapshot_activity))
    if not jobs:
        log.debug("Poller: posture is %s, nothing to snapshot", POSTURE)
        return

    for name, fn in jobs:
        try:
            count = fn()
            log.info("Poller: %s snapshot covered %d systems", name, count)
        except Exception:
            log.exception("Poller: %s snapshot failed, will retry next cycle", name)


def _loop():
    # Stagger the first run so a fleet of workers restarting together does not
    # hit ESI simultaneously, and so startup is not blocked behind a poll.
    time.sleep(5)
    while True:
        poll_once()
        # Buffered traffic counts are otherwise only written when the next
        # request comes in — flush here so a quiet night still persists the
        # visits that happened before it went quiet.
        try:
            analytics_routes.flush(force=True)
        except Exception:
            log.exception("Poller: traffic analytics flush failed")
        # Lapsed parser shares. Cheap enough (indexed DELETE over at most a few
        # days of rows) to run every cycle without an interval guard, and this
        # loop keeps ticking under every posture — poll_once no-ops for
        # rootless, but expired shares still have to go.
        try:
            dropped = db.prune_shared_reports()
            if dropped:
                log.info("Poller: pruned %d expired shared report(s)", dropped)
        except Exception:
            log.exception("Poller: shared-report prune failed")
        time.sleep(POLL_INTERVAL_SECONDS)


def start_poller():
    """Start the poller once per process. Idempotent."""
    global _thread
    with _thread_lock:
        if _thread is not None and _thread.is_alive():
            return _thread
        _thread = threading.Thread(target=_loop, name="esi-poller", daemon=True)
        _thread.start()
        log.info("Background ESI poller started (interval=%ss)", POLL_INTERVAL_SECONDS)
        return _thread
