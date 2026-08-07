#!/usr/bin/env python3
"""
Seed a war ledger with history from zKillboard.

The background poller only reaches back as far as its rolling window, so a war
that started months ago needs its past fetched once. zKill caps every response
at 200 kills regardless of the time filters, so `pastSeconds` cannot reach back
far — the way to walk history is year/month plus pages, which is what this
does.

Idempotent: rows are keyed on killmail_id, so re-running tops up after an
outage instead of duplicating. Safe to interrupt and resume.

    python tools/backfill_war.py --war dronelands --dry-run
    python tools/backfill_war.py --war dronelands --since 2026-03-01
    python tools/backfill_war.py --war dronelands --regions 10000066 --since 2026-07-01
"""

import argparse
import logging
import os
import sys
import time
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402
import esi_client  # noqa: E402
import wars  # noqa: E402
from war_ingest import (  # noqa: E402
    ZKILL_PAGE_SIZE,
    ZKILL_REQUEST_SPACING,
    resolve_pending_names,
    store_kills,
)

log = logging.getLogger("backfill_war")


def month_range(since, until=None):
    """(year, month) pairs from `until` back to `since`, newest first."""
    until = until or datetime.now(UTC)
    months = []
    y, m = until.year, until.month
    while (y, m) >= (since.year, since.month):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return months


def walk_region_month(spec, region_id, year, month, since_iso, max_pages, dry_run, spacing,
                      start_page=1):
    """Fetch one region-month page by page. Returns (fetched, stored, pages).

    Pages run newest-first within the month, so hitting `max_pages` truncates
    the *oldest* end. `start_page` exists to resume such a walk without
    re-fetching everything above it — a busy month in a contested region can
    run well past a sane default cap.
    """
    fetched = stored = 0
    page = start_page
    for page in range(start_page, max_pages + 1):
        if page > start_page or fetched:
            time.sleep(spacing)
        try:
            batch = esi_client.get_zkill_region_kills(
                region_id, year=year, month=month, page=page
            )
        except Exception as e:
            log.warning("  region %s %04d-%02d page %d failed: %s", region_id, year, month, page, e)
            break

        if not batch:
            break
        fetched += len(batch)

        # Trim anything older than the requested start before storing, so
        # --since is honoured exactly rather than to the nearest month.
        keep = [k for k in batch if (k.get("killmail_time") or "") >= since_iso]
        if not dry_run and keep:
            stored += store_kills(spec, region_id, keep)

        oldest = min((k.get("killmail_time") or "" for k in batch), default="")
        if len(batch) < ZKILL_PAGE_SIZE or (oldest and oldest < since_iso):
            break
    else:
        log.warning(
            "  region %s %04d-%02d hit the %d-page cap — raise --max-pages to go deeper",
            region_id, year, month, max_pages,
        )
    return fetched, stored, page


def main():
    ap = argparse.ArgumentParser(description="Backfill a war ledger from zKillboard history.")
    ap.add_argument("--war", required=True, help="WAR_ID of a loaded war module")
    ap.add_argument("--since", help="ISO date to walk back to (default: the war's START_DATE)")
    ap.add_argument("--regions", nargs="*", type=int, help="Limit to these region IDs")
    ap.add_argument("--max-pages", type=int, default=40,
                    help="Page cap per region-month (200 kills each, default 40)")
    ap.add_argument("--start-page", type=int, default=1,
                    help="Resume a capped walk from this page instead of re-fetching from 1")
    ap.add_argument("--spacing", type=float, default=ZKILL_REQUEST_SPACING,
                    help="Seconds between zKill requests (default 1.0)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Fetch and report volume without writing anything")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    spec = wars.get(args.war)
    if not spec:
        available = ", ".join(wars.WARS) or "(none)"
        ap.error(f"war '{args.war}' not found. Loaded wars: {available}")

    since_str = args.since or spec.start_date
    since = datetime.strptime(since_str[:10], "%Y-%m-%d").replace(tzinfo=UTC)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    region_ids = args.regions or spec.region_ids

    if not args.dry_run:
        db.init()

    months = month_range(since)
    log.info(
        "%s: %d region(s) x %d month(s) back to %s%s",
        spec.name, len(region_ids), len(months), since_str,
        "  [DRY RUN — nothing will be written]" if args.dry_run else "",
    )

    started = time.time()
    total_fetched = total_stored = total_pages = 0
    for region_id in region_ids:
        name = spec.region_names.get(region_id, str(region_id))
        r_fetched = r_stored = r_pages = 0
        for year, month in months:
            fetched, stored, pages = walk_region_month(
                spec, region_id, year, month, since_iso,
                args.max_pages, args.dry_run, args.spacing, args.start_page,
            )
            r_fetched += fetched
            r_stored += stored
            r_pages += pages
            if fetched:
                log.info("  %-22s %04d-%02d  %4d kills  %2d pages  +%d stored",
                         name, year, month, fetched, pages, stored)
        log.info("%-24s %5d kills fetched, %5d stored, %3d requests",
                 name, r_fetched, r_stored, r_pages)
        total_fetched += r_fetched
        total_stored += r_stored
        total_pages += r_pages

    elapsed = time.time() - started
    log.info("")
    log.info("Total: %d kills seen, %d stored, %d requests in %.0fs",
             total_fetched, total_stored, total_pages, elapsed)

    if args.dry_run:
        log.info("Dry run — re-run without --dry-run to write these to the ledger.")
        return

    # Ingest never blocks on name resolution, so anything that failed mid-walk
    # is sitting there with IDs only. Repair it now rather than leaving the
    # ledger half-named until the poller's next cycle.
    repaired = 0
    while True:
        batch = resolve_pending_names(spec)
        if not batch:
            break
        repaired += batch
    if repaired:
        log.info("Resolved names for %d rows", repaired)

    # Big batch inserts leave a large WAL behind; fold it back into the db.
    conn = db.get_connection()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()

    summary = db.get_war_summary(spec.key, days=0)
    log.info("Ledger now holds %d kills (%s → %s)",
             summary["coverage"]["rows"],
             summary["coverage"]["first_kill"], summary["coverage"]["last_kill"])
    log.info("  %s: %d kills / %.1fB ISK destroyed",
             spec.sides["a"]["label"], summary["totals"]["a_kills"],
             summary["totals"]["a_isk"] / 1e9)
    log.info("  %s: %d kills / %.1fB ISK destroyed",
             spec.sides["b"]["label"], summary["totals"]["b_kills"],
             summary["totals"]["b_isk"] / 1e9)


if __name__ == "__main__":
    main()
