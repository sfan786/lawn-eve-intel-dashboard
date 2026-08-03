"""
SQLite persistence for historical data.
Stores ADM snapshots, activity, timers, annotations, and jump bridges.

Rows are scoped by deployment_id so a single intel.db can survive moves
between deployments without mixing data. Reads filter by the active
deployment from config; writes always tag rows with the active deployment.
Existing pre-migration rows are tagged 'lawn-kalevala' so they remain
visible if you ever switch back.
"""

import logging
import os
import sqlite3
import time
from datetime import UTC, datetime, timedelta

from config import DEPLOYMENT_ID

log = logging.getLogger(__name__)

DB_PATH = os.environ.get("INTEL_DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "intel.db")

LEGACY_DEPLOYMENT_ID = "lawn-kalevala"

# Track last snapshot time per system to deduplicate
_last_adm_snapshot = {}
_last_activity_snapshot = {}
SNAPSHOT_INTERVAL = 3600  # At most one snapshot per system per hour


def _iso_cutoff(hours):
    """ISO-8601 UTC timestamp N hours ago, matching the stored timestamp format."""
    return (datetime.now(UTC) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_connection():
    """Get a SQLite connection with WAL mode for concurrent reads."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init():
    """Initialize database schema and run migrations.

    Three-step ordering: (1) ensure tables exist, (2) ALTER any pre-migration
    tables to add deployment_id, (3) rebuild tables for updated constraints, (4) create indexes.
    """
    conn = get_connection()

    # 1. Create tables with CURRENT schema (for fresh installs)
    conn.executescript(f"""
        CREATE TABLE IF NOT EXISTS adm_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
            system_id INTEGER NOT NULL,
            system_name TEXT NOT NULL,
            adm REAL NOT NULL,
            alliance_name TEXT,
            timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS activity_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
            system_id INTEGER NOT NULL,
            ship_kills INTEGER DEFAULT 0,
            pod_kills INTEGER DEFAULT 0,
            npc_kills INTEGER DEFAULT 0,
            jumps INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS custom_timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
            system_name TEXT NOT NULL,
            structure_type TEXT NOT NULL,
            owner TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS system_annotations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
            system_name TEXT NOT NULL,
            note        TEXT NOT NULL,
            updated_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            UNIQUE(deployment_id, system_name)
        );

        CREATE TABLE IF NOT EXISTS jump_bridges (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
            system_a   TEXT NOT NULL,
            system_b   TEXT NOT NULL,
            label      TEXT,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            UNIQUE(deployment_id, system_a, system_b)
        );

        CREATE TABLE IF NOT EXISTS sov_state (
            deployment_id TEXT NOT NULL,
            system_id     INTEGER NOT NULL,
            alliance_id   INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (deployment_id, system_id)
        );

        CREATE TABLE IF NOT EXISTS sov_changes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL,
            system_id     INTEGER NOT NULL,
            system_name   TEXT NOT NULL,
            old_alliance  INTEGER,
            new_alliance  INTEGER,
            detected_at   REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS traffic_hourly (
            deployment_id TEXT NOT NULL,
            hour          TEXT NOT NULL,
            kind          TEXT NOT NULL,
            path          TEXT NOT NULL,
            views         INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (deployment_id, hour, kind, path)
        );

        CREATE TABLE IF NOT EXISTS traffic_visitors (
            deployment_id  TEXT NOT NULL,
            day            TEXT NOT NULL,
            visitor_hash   TEXT NOT NULL,
            character_name TEXT,
            page_views     INTEGER NOT NULL DEFAULT 0,
            api_calls      INTEGER NOT NULL DEFAULT 0,
            first_seen     TEXT NOT NULL,
            last_seen      TEXT NOT NULL,
            PRIMARY KEY (deployment_id, day, visitor_hash)
        );

        CREATE TABLE IF NOT EXISTS entosis_nodes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
            system_name  TEXT NOT NULL,
            label        TEXT,
            status       TEXT NOT NULL DEFAULT 'unclaimed',
            claimed_by   TEXT,
            campaign_id  INTEGER,
            created_at   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );
    """)

    # 2. Add deployment_id column to existing tables if missing (for legacy updates)
    for table in ["adm_snapshots", "activity_snapshots", "custom_timers", "system_annotations", "jump_bridges"]:
        cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if "deployment_id" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}'")

    # 2b. Add campaign_id to entosis_nodes if missing (links nodes to ESI sov campaigns)
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(entosis_nodes)")}
    if "campaign_id" not in cols:
        conn.execute("ALTER TABLE entosis_nodes ADD COLUMN campaign_id INTEGER")

    # 3. Migrate system_annotations to composite unique constraint
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='system_annotations'").fetchone()
    if row and "UNIQUE(deployment_id, system_name)" not in row["sql"].replace(" ", "").replace("\n", ""):
        conn.executescript(f"""
            DROP TABLE IF EXISTS system_annotations_new;
            CREATE TABLE system_annotations_new (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
                system_name TEXT NOT NULL,
                note        TEXT NOT NULL,
                updated_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE(deployment_id, system_name)
            );
            INSERT INTO system_annotations_new (id, deployment_id, system_name, note, updated_at)
            SELECT id, deployment_id, system_name, note, updated_at FROM system_annotations;
            DROP TABLE system_annotations;
            ALTER TABLE system_annotations_new RENAME TO system_annotations;
        """)

    # 4. Migrate jump_bridges to composite unique constraint
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='jump_bridges'").fetchone()
    if row and "UNIQUE(deployment_id, system_a, system_b)" not in row["sql"].replace(" ", "").replace("\n", ""):
        conn.executescript(f"""
            DROP TABLE IF EXISTS jump_bridges_new;
            CREATE TABLE jump_bridges_new (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
                system_a   TEXT NOT NULL,
                system_b   TEXT NOT NULL,
                label      TEXT,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE(deployment_id, system_a, system_b)
            );
            INSERT INTO jump_bridges_new (id, deployment_id, system_a, system_b, label, created_at)
            SELECT id, deployment_id, system_a, system_b, label, created_at FROM jump_bridges;
            DROP TABLE jump_bridges;
            ALTER TABLE jump_bridges_new RENAME TO jump_bridges;
        """)

    # 5. Create indexes
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_adm_system_time ON adm_snapshots(system_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_activity_system_time ON activity_snapshots(system_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_timer_time ON custom_timers(timestamp);
        CREATE INDEX IF NOT EXISTS idx_annotation_system ON system_annotations(system_name);

        CREATE INDEX IF NOT EXISTS idx_adm_deployment_time ON adm_snapshots(deployment_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_adm_deploy_system_time ON adm_snapshots(deployment_id, system_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_activity_deployment_time ON activity_snapshots(deployment_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_activity_deploy_system_time ON activity_snapshots(deployment_id, system_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_timer_deployment_time ON custom_timers(deployment_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_entosis_deployment ON entosis_nodes(deployment_id);
        CREATE INDEX IF NOT EXISTS idx_traffic_hourly_deploy_hour ON traffic_hourly(deployment_id, hour);
        CREATE INDEX IF NOT EXISTS idx_traffic_visitors_deploy_day ON traffic_visitors(deployment_id, day);
    """)

    conn.commit()
    conn.close()
    log.info("Database initialized: %s (deployment=%s)", DB_PATH, DEPLOYMENT_ID)


def snapshot_adm_batch(systems):
    """Record ADM readings for multiple systems.
    systems: list of (system_id, system_name, adm, alliance_name) tuples.
    Deduplicates: skips if same ADM was recorded within the last hour.
    """
    now = time.time()
    to_insert = []

    dedup_cutoff = _iso_cutoff(SNAPSHOT_INTERVAL / 3600)
    for system_id, system_name, adm, alliance_name in systems:
        if adm <= 0:
            continue
        last = _last_adm_snapshot.get(system_id)
        if last and last["adm"] == adm and (now - last["time"]) < SNAPSHOT_INTERVAL:
            continue
        to_insert.append((DEPLOYMENT_ID, system_id, system_name, adm, alliance_name,
                          DEPLOYMENT_ID, system_id, adm, dedup_cutoff))
        _last_adm_snapshot[system_id] = {"adm": adm, "time": now}

    if not to_insert:
        return

    conn = get_connection()
    # NOT EXISTS guard makes dedup correct across gunicorn workers — the
    # in-memory check above is only a fast path for the single-process case.
    conn.executemany(
        "INSERT INTO adm_snapshots (deployment_id, system_id, system_name, adm, alliance_name) "
        "SELECT ?, ?, ?, ?, ? "
        "WHERE NOT EXISTS (SELECT 1 FROM adm_snapshots "
        "WHERE deployment_id = ? AND system_id = ? AND adm = ? AND timestamp >= ?)",
        to_insert,
    )
    conn.commit()
    conn.close()


def snapshot_activity_batch(systems):
    """Record activity data for multiple systems.
    systems: list of (system_id, ship_kills, pod_kills, npc_kills, jumps) tuples.
    """
    now = time.time()
    to_insert = []

    dedup_cutoff = _iso_cutoff(SNAPSHOT_INTERVAL / 3600)
    for system_id, ship_kills, pod_kills, npc_kills, jumps in systems:
        last = _last_activity_snapshot.get(system_id)
        if last and (now - last["time"]) < SNAPSHOT_INTERVAL:
            continue
        to_insert.append((DEPLOYMENT_ID, system_id, ship_kills, pod_kills, npc_kills, jumps,
                          DEPLOYMENT_ID, system_id, dedup_cutoff))
        _last_activity_snapshot[system_id] = {"time": now}

    if not to_insert:
        return

    conn = get_connection()
    conn.executemany(
        "INSERT INTO activity_snapshots (deployment_id, system_id, ship_kills, pod_kills, npc_kills, jumps) "
        "SELECT ?, ?, ?, ?, ?, ? "
        "WHERE NOT EXISTS (SELECT 1 FROM activity_snapshots "
        "WHERE deployment_id = ? AND system_id = ? AND timestamp >= ?)",
        to_insert,
    )
    conn.commit()
    conn.close()


def get_adm_history(system_id=None, hours=168):
    """Get ADM history for the last N hours.
    Returns dict keyed by system_id: {system_name, history: [{adm, timestamp}]}
    """
    conn = get_connection()
    cutoff = _iso_cutoff(hours)

    if system_id:
        rows = conn.execute(
            "SELECT system_id, system_name, adm, timestamp FROM adm_snapshots "
            "WHERE deployment_id = ? AND system_id = ? AND timestamp >= ? "
            "ORDER BY timestamp ASC",
            (DEPLOYMENT_ID, system_id, cutoff),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT system_id, system_name, adm, timestamp FROM adm_snapshots "
            "WHERE deployment_id = ? AND timestamp >= ? "
            "ORDER BY system_id, timestamp ASC",
            (DEPLOYMENT_ID, cutoff),
        ).fetchall()

    conn.close()

    result = {}
    for row in rows:
        sid = row["system_id"]
        if sid not in result:
            result[sid] = {"system_name": row["system_name"], "history": []}
        result[sid]["history"].append({
            "adm": row["adm"],
            "timestamp": row["timestamp"],
        })

    return result


def get_activity_history(system_id=None, hours=168):
    """Get activity history for the last N hours."""
    conn = get_connection()
    cutoff = _iso_cutoff(hours)

    if system_id:
        rows = conn.execute(
            "SELECT system_id, ship_kills, pod_kills, npc_kills, jumps, timestamp "
            "FROM activity_snapshots WHERE deployment_id = ? AND system_id = ? "
            "AND timestamp >= ? ORDER BY timestamp ASC",
            (DEPLOYMENT_ID, system_id, cutoff),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT system_id, ship_kills, pod_kills, npc_kills, jumps, timestamp "
            "FROM activity_snapshots WHERE deployment_id = ? AND timestamp >= ? "
            "ORDER BY system_id, timestamp ASC",
            (DEPLOYMENT_ID, cutoff),
        ).fetchall()

    conn.close()

    result = {}
    for row in rows:
        sid = row["system_id"]
        if sid not in result:
            result[sid] = []
        result[sid].append({
            "ship_kills": row["ship_kills"],
            "pod_kills": row["pod_kills"],
            "npc_kills": row["npc_kills"],
            "jumps": row["jumps"],
            "timestamp": row["timestamp"],
        })

    return result


def get_activity_baseline(system_ids, days=7):
    """Return historical avg ship_kills and jumps per system over the last N days.
    Requires at least 3 snapshots before returning data (avoids false spike alerts).
    Returns {system_id: {"avg_kills": float, "avg_jumps": float, "sample_count": int}}
    """
    if not system_ids:
        return {}
    cutoff = _iso_cutoff(days * 24)
    placeholders = ','.join('?' * len(system_ids))
    conn = get_connection()
    rows = conn.execute(
        f"SELECT system_id, AVG(ship_kills) as avg_kills, AVG(jumps) as avg_jumps, COUNT(*) as n "
        f"FROM activity_snapshots "
        f"WHERE deployment_id=? AND system_id IN ({placeholders}) AND timestamp > ? "
        f"GROUP BY system_id",
        [DEPLOYMENT_ID] + list(system_ids) + [cutoff],
    ).fetchall()
    conn.close()
    return {
        r["system_id"]: {
            "avg_kills": round(r["avg_kills"], 2),
            "avg_jumps": round(r["avg_jumps"], 2),
            "sample_count": r["n"],
        }
        for r in rows
    }


def add_timer(system_name, structure_type, owner, event_type, timestamp, notes=None):
    """Add a custom timer."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO custom_timers (deployment_id, system_name, structure_type, owner, event_type, timestamp, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (DEPLOYMENT_ID, system_name, structure_type, owner, event_type, timestamp, notes),
    )
    conn.commit()
    conn.close()


def get_active_timers():
    """Get all future timers + timers from the last 24h."""
    conn = get_connection()
    cutoff = _iso_cutoff(24)
    rows = conn.execute(
        "SELECT id, system_name, structure_type, owner, event_type, timestamp, notes "
        "FROM custom_timers WHERE deployment_id = ? AND timestamp >= ? ORDER BY timestamp ASC",
        (DEPLOYMENT_ID, cutoff),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_timer(timer_id):
    """Delete a custom timer (scoped to active deployment)."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM custom_timers WHERE id = ? AND deployment_id = ?",
        (timer_id, DEPLOYMENT_ID),
    )
    conn.commit()
    conn.close()


def get_all_annotations():
    """Return dict keyed by system_name: {note, updated_at} for the active deployment."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT system_name, note, updated_at FROM system_annotations "
        "WHERE deployment_id = ? ORDER BY system_name",
        (DEPLOYMENT_ID,),
    ).fetchall()
    conn.close()
    return {row["system_name"]: {"note": row["note"], "updated_at": row["updated_at"]} for row in rows}


def upsert_annotation(system_name, note):
    """Insert or replace annotation. Empty note removes it."""
    if not note or not note.strip():
        delete_annotation(system_name)
        return
    conn = get_connection()
    conn.execute(
        "INSERT INTO system_annotations (deployment_id, system_name, note, updated_at) "
        "VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) "
        "ON CONFLICT(deployment_id, system_name) DO UPDATE SET "
        "note=excluded.note, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ', 'now')",
        (DEPLOYMENT_ID, system_name, note.strip()),
    )
    conn.commit()
    conn.close()


def delete_annotation(system_name):
    """Remove annotation for a system in the active deployment."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM system_annotations WHERE system_name = ? AND deployment_id = ?",
        (system_name, DEPLOYMENT_ID),
    )
    conn.commit()
    conn.close()


def get_jump_bridges():
    """Return list of {id, system_a, system_b, label, created_at} dicts for active deployment."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, system_a, system_b, label, created_at FROM jump_bridges "
        "WHERE deployment_id = ? ORDER BY created_at ASC",
        (DEPLOYMENT_ID,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_jump_bridge(system_a, system_b, label=None):
    """Add a JB pair (alphabetically normalized). Returns new id."""
    a, b = sorted([system_a.strip(), system_b.strip()])
    conn = get_connection()
    conn.execute(
        "INSERT INTO jump_bridges (deployment_id, system_a, system_b, label) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(deployment_id, system_a, system_b) DO UPDATE SET label=excluded.label",
        (DEPLOYMENT_ID, a, b, label.strip() if label else None),
    )
    # lastrowid is unreliable when ON CONFLICT updates an existing row — look the id up
    row = conn.execute(
        "SELECT id FROM jump_bridges WHERE deployment_id = ? AND system_a = ? AND system_b = ?",
        (DEPLOYMENT_ID, a, b),
    ).fetchone()
    conn.commit()
    conn.close()
    return row["id"] if row else None


def delete_jump_bridge(bridge_id):
    """Delete a jump bridge by id (scoped to active deployment)."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM jump_bridges WHERE id = ? AND deployment_id = ?",
        (bridge_id, DEPLOYMENT_ID),
    )
    conn.commit()
    conn.close()


def get_activity_heatmap_data(hours=168):
    """
    Aggregate activity data by hour of day for all systems in the active deployment.
    Returns: { system_id: { hour(0-23): { pvp, npc, jumps } } }
    """
    conn = get_connection()
    cutoff = _iso_cutoff(hours)

    query = """
        SELECT
            system_id,
            CAST(strftime('%H', timestamp) AS INTEGER) as hour,
            AVG(ship_kills + pod_kills) as avg_pvp,
            AVG(npc_kills) as avg_npc,
            AVG(jumps) as avg_jumps
        FROM activity_snapshots
        WHERE deployment_id = ? AND timestamp >= ?
        GROUP BY system_id, hour
        ORDER BY system_id, hour ASC
    """
    rows = conn.execute(query, (DEPLOYMENT_ID, cutoff)).fetchall()
    conn.close()

    result = {}
    for row in rows:
        sid = row["system_id"]
        if sid not in result:
            result[sid] = {}
        result[sid][row["hour"]] = {
            "pvp": round(row["avg_pvp"], 2),
            "npc": round(row["avg_npc"], 2),
            "jumps": round(row["avg_jumps"], 2)
        }

    return result


# --- Neighbor sov change tracking ---

SOV_CHANGES_MAX = 50


def record_sov_changes(current_sov, system_names):
    """Diff neighbor sov against persisted state, logging changes.
    current_sov: {system_id: alliance_id (0 = unclaimed)}.
    First sighting of a system seeds state without a change event.
    BEGIN IMMEDIATE serializes concurrent workers so a change is logged once.
    """
    if not current_sov:
        return
    conn = get_connection()
    # Autocommit mode: the manual BEGIN IMMEDIATE below owns the transaction,
    # without relying on sqlite3's implicit transaction management.
    conn.isolation_level = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            "SELECT system_id, alliance_id FROM sov_state WHERE deployment_id = ?",
            (DEPLOYMENT_ID,),
        ).fetchall()
        old_state = {r["system_id"]: r["alliance_id"] for r in rows}
        now = time.time()
        for sys_id, new_alliance in current_sov.items():
            old_alliance = old_state.get(sys_id)
            if old_alliance == new_alliance:
                continue
            if old_alliance is not None:
                conn.execute(
                    "INSERT INTO sov_changes (deployment_id, system_id, system_name, old_alliance, new_alliance, detected_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (DEPLOYMENT_ID, sys_id, system_names.get(sys_id, str(sys_id)), old_alliance, new_alliance, now),
                )
            conn.execute(
                "INSERT INTO sov_state (deployment_id, system_id, alliance_id) VALUES (?, ?, ?) "
                "ON CONFLICT(deployment_id, system_id) DO UPDATE SET alliance_id=excluded.alliance_id",
                (DEPLOYMENT_ID, sys_id, new_alliance),
            )
        conn.execute(
            "DELETE FROM sov_changes WHERE deployment_id = ? AND id NOT IN ("
            "SELECT id FROM sov_changes WHERE deployment_id = ? ORDER BY id DESC LIMIT ?)",
            (DEPLOYMENT_ID, DEPLOYMENT_ID, SOV_CHANGES_MAX),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_recent_sov_changes(limit=20):
    """Most recent neighbor sov changes, newest first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT system_id, system_name, old_alliance, new_alliance, detected_at "
        "FROM sov_changes WHERE deployment_id = ? ORDER BY id DESC LIMIT ?",
        (DEPLOYMENT_ID, limit),
    ).fetchall()
    conn.close()
    return [
        {
            "system_id": r["system_id"],
            "name": r["system_name"],
            "old_alliance": r["old_alliance"],
            "new_alliance": r["new_alliance"],
            "detected_at": r["detected_at"],
        }
        for r in rows
    ]


# --- Traffic analytics ---
#
# Two rollup tables, no per-request rows: `traffic_hourly` counts hits per
# (hour, kind, path) and `traffic_visitors` counts one row per (day, visitor).
# That keeps the table bounded — a busy day is a few hundred rows, not tens of
# thousands — while still answering the only question this feature exists for:
# is anybody actually using the dashboard?

TRAFFIC_RETENTION_DAYS = int(os.environ.get("ANALYTICS_RETENTION_DAYS", "180"))


def record_traffic(hourly, visitors):
    """Merge a batch of buffered counts into the rollup tables.

    hourly:   {(hour, kind, path): views}, hour as 'YYYY-MM-DDTHH'.
    visitors: {(day, visitor_hash): {character_name, page_views, api_calls,
              first_seen, last_seen}}, day as 'YYYY-MM-DD'.

    Counts are added to whatever is already stored, so callers may flush
    partial batches as often as they like and concurrent gunicorn workers
    accumulate into the same rows.
    """
    if not hourly and not visitors:
        return
    conn = get_connection()
    try:
        if hourly:
            conn.executemany(
                "INSERT INTO traffic_hourly (deployment_id, hour, kind, path, views) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(deployment_id, hour, kind, path) DO UPDATE SET views = views + excluded.views",
                [(DEPLOYMENT_ID, hour, kind, path, views) for (hour, kind, path), views in hourly.items()],
            )
        if visitors:
            conn.executemany(
                "INSERT INTO traffic_visitors "
                "(deployment_id, day, visitor_hash, character_name, page_views, api_calls, first_seen, last_seen) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(deployment_id, day, visitor_hash) DO UPDATE SET "
                "page_views = page_views + excluded.page_views, "
                "api_calls = api_calls + excluded.api_calls, "
                "last_seen = MAX(last_seen, excluded.last_seen), "
                # A visitor may browse anonymously before logging in; keep the
                # name once we learn it rather than reverting to NULL.
                "character_name = COALESCE(excluded.character_name, character_name)",
                [
                    (DEPLOYMENT_ID, day, vhash, v.get("character_name"),
                     v.get("page_views", 0), v.get("api_calls", 0),
                     v["first_seen"], v["last_seen"])
                    for (day, vhash), v in visitors.items()
                ],
            )
        conn.commit()
    finally:
        conn.close()


def prune_traffic(days=TRAFFIC_RETENTION_DAYS):
    """Drop traffic rollups older than N days (all deployments)."""
    cutoff_day = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_connection()
    conn.execute("DELETE FROM traffic_hourly WHERE hour < ?", (cutoff_day,))
    conn.execute("DELETE FROM traffic_visitors WHERE day < ?", (cutoff_day,))
    conn.commit()
    conn.close()


def get_traffic_summary(days=30):
    """Traffic rollup for the active deployment over the last N days.

    Returns daily page views / API calls / unique visitors, hour-of-day
    distribution (UTC = EVE time), the busiest paths, how many visitors came
    back on more than one day, and which logged-in pilots were seen.
    """
    now = datetime.now(UTC)
    cutoff_day = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_connection()

    day_rows = conn.execute(
        "SELECT day, "
        "SUM(page_views) AS page_views, SUM(api_calls) AS api_calls, "
        "COUNT(*) AS visitors "
        "FROM traffic_visitors WHERE deployment_id = ? AND day >= ? "
        "GROUP BY day ORDER BY day ASC",
        (DEPLOYMENT_ID, cutoff_day),
    ).fetchall()

    hour_rows = conn.execute(
        "SELECT CAST(substr(hour, 12, 2) AS INTEGER) AS hod, SUM(views) AS views "
        "FROM traffic_hourly WHERE deployment_id = ? AND hour >= ? AND kind = 'page' "
        "GROUP BY hod",
        (DEPLOYMENT_ID, cutoff_day),
    ).fetchall()

    path_rows = conn.execute(
        "SELECT kind, path, SUM(views) AS views FROM traffic_hourly "
        "WHERE deployment_id = ? AND hour >= ? GROUP BY kind, path ORDER BY views DESC",
        (DEPLOYMENT_ID, cutoff_day),
    ).fetchall()

    # How many distinct days each visitor showed up on — one-off visitors vs regulars.
    freq_rows = conn.execute(
        "SELECT days_seen, COUNT(*) AS visitors FROM ("
        "  SELECT visitor_hash, COUNT(DISTINCT day) AS days_seen FROM traffic_visitors "
        "  WHERE deployment_id = ? AND day >= ? GROUP BY visitor_hash"
        ") GROUP BY days_seen ORDER BY days_seen ASC",
        (DEPLOYMENT_ID, cutoff_day),
    ).fetchall()

    pilot_rows = conn.execute(
        "SELECT character_name, COUNT(DISTINCT day) AS days_seen, MAX(last_seen) AS last_seen "
        "FROM traffic_visitors WHERE deployment_id = ? AND day >= ? AND character_name IS NOT NULL "
        "GROUP BY character_name ORDER BY days_seen DESC, last_seen DESC",
        (DEPLOYMENT_ID, cutoff_day),
    ).fetchall()

    total_visitors = conn.execute(
        "SELECT COUNT(DISTINCT visitor_hash) FROM traffic_visitors "
        "WHERE deployment_id = ? AND day >= ?",
        (DEPLOYMENT_ID, cutoff_day),
    ).fetchone()[0]

    bot_hits = conn.execute(
        "SELECT COALESCE(SUM(views), 0) FROM traffic_hourly "
        "WHERE deployment_id = ? AND hour >= ? AND kind = 'bot'",
        (DEPLOYMENT_ID, cutoff_day),
    ).fetchone()[0]

    conn.close()

    daily = [
        {
            "day": r["day"],
            "page_views": r["page_views"] or 0,
            "api_calls": r["api_calls"] or 0,
            "visitors": r["visitors"] or 0,
        }
        for r in day_rows
    ]
    hourly = {r["hod"]: r["views"] for r in hour_rows}
    freq = {r["days_seen"]: r["visitors"] for r in freq_rows}

    return {
        "days": days,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totals": {
            "page_views": sum(d["page_views"] for d in daily),
            "api_calls": sum(d["api_calls"] for d in daily),
            "unique_visitors": total_visitors,
            "returning_visitors": sum(n for seen, n in freq.items() if seen > 1),
            "active_days": len(daily),
            "bot_hits": bot_hits,
            "peak_daily_visitors": max((d["visitors"] for d in daily), default=0),
        },
        "daily": daily,
        "hourly": [{"hour": h, "views": hourly.get(h, 0)} for h in range(24)],
        "top_pages": [
            {"path": r["path"], "views": r["views"]} for r in path_rows if r["kind"] == "page"
        ][:10],
        "top_api": [
            {"path": r["path"], "views": r["views"]} for r in path_rows if r["kind"] == "api"
        ][:15],
        "visitor_frequency": [
            {"days_seen": seen, "visitors": n} for seen, n in sorted(freq.items())
        ],
        "pilots": [
            {
                "character_name": r["character_name"],
                "days_seen": r["days_seen"],
                "last_seen": r["last_seen"],
            }
            for r in pilot_rows
        ],
    }


# --- Entosis node board ---

def get_entosis_nodes():
    """Return all nodes for the active deployment, ordered by creation time."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, system_name, label, status, claimed_by, campaign_id, created_at, updated_at "
        "FROM entosis_nodes WHERE deployment_id = ? ORDER BY created_at ASC",
        (DEPLOYMENT_ID,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_entosis_node(system_name, label=None, campaign_id=None):
    """Add a command node, optionally linked to an ESI sov campaign. Returns new id."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO entosis_nodes (deployment_id, system_name, label, campaign_id) VALUES (?, ?, ?, ?)",
        (DEPLOYMENT_ID, system_name.strip(), label.strip() if label else None, campaign_id),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_entosis_node(node_id, status=None, claimed_by=None):
    """Update status and/or claimed_by. Pass claimed_by='' to unclaim."""
    conn = get_connection()
    sets, params = [], []
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if claimed_by is not None:
        sets.append("claimed_by = ?")
        params.append(claimed_by or None)
    if sets:
        sets.append("updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')")
        params.extend([node_id, DEPLOYMENT_ID])
        conn.execute(
            f"UPDATE entosis_nodes SET {', '.join(sets)} WHERE id = ? AND deployment_id = ?",
            params,
        )
        conn.commit()
    conn.close()


def delete_entosis_node(node_id):
    """Delete a single node (scoped to active deployment)."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM entosis_nodes WHERE id = ? AND deployment_id = ?",
        (node_id, DEPLOYMENT_ID),
    )
    conn.commit()
    conn.close()


def clear_entosis_nodes():
    """Remove all nodes for the active deployment (end-of-op reset)."""
    conn = get_connection()
    conn.execute("DELETE FROM entosis_nodes WHERE deployment_id = ?", (DEPLOYMENT_ID,))
    conn.commit()
    conn.close()
