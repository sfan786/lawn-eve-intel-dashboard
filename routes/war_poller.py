"""
Background war-ledger ingest.

A separate thread from routes/poller.py rather than another job inside it: the
intervals differ, and a war cycle that has to paginate through a big fight must
not delay the ADM/activity snapshots behind it.

Three things here differ from the ADM poller and are worth stating, because
copying that module's reasoning wholesale would be wrong:

  * **The work is leased, not merely deduplicated.** The ADM poller runs in
    every gunicorn worker because a duplicate cycle costs one small ESI call.
    A duplicate war cycle costs megabytes of zKillboard traffic, so exactly one
    worker holds the lease and the rest sleep.

  * **The fetch window comes from a stored cursor.** zKill's plain region URL
    is CDN-cached for an hour, so polling it repeatedly re-downloads an
    identical body. Deriving `pastSeconds` from the last kill we stored makes
    every request a distinct URL, and therefore actually fresh.

  * **The cursor only advances on a confirmed success.** esi_client's ordinary
    zKill helper flattens an outage to "no kills"; this path uses the raising
    variant so a timeout leaves the window to be re-covered next cycle instead
    of being skipped forever.

Posture-independent: a war is fought wherever it is fought, so this runs the
same for a sovereign, guest or rootless deployment.
"""

import logging
import os
import socket
import threading
import time
from datetime import UTC, datetime

import db
import wars
from war_ingest import fetch_pages, resolve_pending_names, store_kills

log = logging.getLogger(__name__)

WAR_POLL_INTERVAL_SECONDS = int(os.environ.get("WAR_POLL_INTERVAL_SECONDS", "600"))
# 6 pages = 1200 kills per region per cycle. Past that we record a gap rather
# than let one busy region monopolise the cycle.
WAR_MAX_PAGES_PER_CYCLE = int(os.environ.get("WAR_MAX_PAGES_PER_CYCLE", "6"))
# Re-ask for a little before the cursor, so a kill landing on zKill late is not
# missed by an exact-boundary window.
WAR_WINDOW_OVERLAP_SECONDS = int(os.environ.get("WAR_WINDOW_OVERLAP_SECONDS", "900"))
WAR_PRUNE_INTERVAL_SECONDS = 86400

_MIN_WINDOW = 600
_MAX_WINDOW = 604800  # zKill's ceiling for pastSeconds

_thread = None
_thread_lock = threading.Lock()
_last_prune = 0.0


def _owner():
    return f"{socket.gethostname()}:{os.getpid()}"


def _now_iso():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _window_seconds(last_kill_time):
    """How far back to ask, from the newest kill already stored."""
    if not last_kill_time:
        return _MAX_WINDOW
    try:
        last = datetime.strptime(last_kill_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return _MAX_WINDOW
    elapsed = (datetime.now(UTC) - last).total_seconds() + WAR_WINDOW_OVERLAP_SECONDS
    return int(max(_MIN_WINDOW, min(_MAX_WINDOW, elapsed)))


def poll_region(spec, region_id, state_by_region):
    """One region, one cycle. Returns rows stored; never raises."""
    cursor = (state_by_region.get(region_id) or {}).get("last_kill_time")
    if not cursor:
        # A backfill stores kills without ever writing an ingest cursor, so on
        # the first cycle after one the ledger knows more than the state table
        # does. Ask the ledger, or we re-walk a week that is already stored.
        cursor = db.get_war_latest_kill_time(spec.key, region_id)
    db.upsert_war_ingest_state(spec.key, region_id, last_poll_at=_now_iso())

    try:
        kills, saturated = fetch_pages(
            region_id,
            max_pages=WAR_MAX_PAGES_PER_CYCLE,
            past_seconds=_window_seconds(cursor),
            stop_before=cursor,
        )
    except Exception as e:
        # Leave last_kill_time alone: the next cycle widens its window to cover
        # whatever happened while zKill was unreachable.
        log.warning("War ingest: region %s fetch failed: %s", region_id, e)
        db.upsert_war_ingest_state(spec.key, region_id, last_error=str(e)[:200])
        return 0

    stored = store_kills(spec, region_id, kills)
    newest = max((k.get("killmail_time") or "" for k in kills), default="")
    db.upsert_war_ingest_state(
        spec.key, region_id,
        last_success_at=_now_iso(),
        last_kill_time=newest or cursor,
        new_kills=stored,
        saturated=1 if saturated else 0,
        last_error=None,
    )
    if saturated:
        log.warning(
            "War ingest: region %s hit the %d-page cap — kills may have been missed",
            region_id, WAR_MAX_PAGES_PER_CYCLE,
        )
    return stored


def poll_war(spec):
    """One war, one cycle. Returns rows stored across all its regions."""
    if not db.acquire_war_poll_lease(spec.key, _owner(), WAR_POLL_INTERVAL_SECONDS * 2):
        log.debug("War ingest: another worker holds the lease for %s", spec.key)
        return 0

    # Roster edits made from the page have to reach ingest, or newly assigned
    # alliances would keep classifying as unaligned on every incoming kill.
    spec.apply_overrides(db.get_war_roster_overrides(spec.key))

    state_by_region = {s["region_id"]: s for s in db.get_war_ingest_state(spec.key)}
    total = 0
    for region_id in spec.region_ids:
        try:
            total += poll_region(spec, region_id, state_by_region)
        except Exception:
            log.exception("War ingest: region %s failed, continuing", region_id)

    try:
        repaired = resolve_pending_names(spec)
        if repaired:
            log.info("War ingest: resolved names for %d rows", repaired)
    except Exception:
        log.exception("War ingest: name repair failed")

    return total


def poll_once():
    """Run one cycle for every loaded war. Never raises."""
    global _last_prune
    if not wars.WARS:
        log.debug("War ingest: no wars configured")
        return

    for spec in wars.WARS.values():
        try:
            stored = poll_war(spec)
            if stored:
                log.info("War ingest: %s stored %d new kills", spec.key, stored)
        except Exception:
            log.exception("War ingest: cycle failed for %s, will retry", spec.key)

    if time.time() - _last_prune > WAR_PRUNE_INTERVAL_SECONDS:
        _last_prune = time.time()
        for spec in wars.WARS.values():
            try:
                removed = db.prune_war_kills(spec.key)
                if removed:
                    log.info("War ingest: pruned %d rows from %s", removed, spec.key)
            except Exception:
                log.exception("War ingest: prune failed for %s", spec.key)


def _loop():
    # Stagger startup so a fleet of workers restarting together does not hit
    # zKill at once, and so boot is not blocked behind a poll.
    time.sleep(20)
    while True:
        poll_once()
        time.sleep(WAR_POLL_INTERVAL_SECONDS)


def start_war_poller():
    """Start the war poller once per process. Idempotent."""
    global _thread
    if not wars.WARS:
        log.info("War poller not started: no war modules loaded")
        return None
    with _thread_lock:
        if _thread is not None and _thread.is_alive():
            return _thread
        _thread = threading.Thread(target=_loop, name="war-poller", daemon=True)
        _thread.start()
        log.info(
            "War poller started (interval=%ss, wars=%s)",
            WAR_POLL_INTERVAL_SECONDS, ", ".join(wars.WARS),
        )
        return _thread
