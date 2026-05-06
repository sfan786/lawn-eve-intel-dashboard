"""
SQLite persistence for historical data.
Stores ADM snapshots, activity, timers, annotations, and jump bridges.

Rows are scoped by deployment_id so a single intel.db can survive moves
between deployments without mixing data. Reads filter by the active
deployment from config; writes always tag rows with the active deployment.
Existing pre-migration rows are tagged 'lawn-kalevala' so they remain
visible if you ever switch back.
"""

import sqlite3
import os
import time
from datetime import datetime, timedelta

from config import DEPLOYMENT_ID

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intel.db")

LEGACY_DEPLOYMENT_ID = "lawn-kalevala"

# Track last snapshot time per system to deduplicate
_last_adm_snapshot = {}
_last_activity_snapshot = {}
SNAPSHOT_INTERVAL = 3600  # At most one snapshot per system per hour


def get_connection():
    """Get a SQLite connection with WAL mode for concurrent reads."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_deployment_column(conn, table):
    """Add deployment_id column to a pre-existing table, tagging old rows as legacy."""
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if "deployment_id" not in cols:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN deployment_id TEXT NOT NULL "
            f"DEFAULT '{LEGACY_DEPLOYMENT_ID}'"
        )


def init():
    """Initialize database schema and run migrations.

    Three-step ordering: (1) ensure tables exist, (2) ALTER any pre-migration
    tables to add deployment_id, (3) create indexes that reference deployment_id.
    Step 3 has to run last because indexes on a column that was just ALTERed
    in cannot be created in the same executescript block as the CREATE TABLE.
    """
    conn = get_connection()

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

        CREATE INDEX IF NOT EXISTS idx_adm_system_time
            ON adm_snapshots(system_id, timestamp);

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

        CREATE INDEX IF NOT EXISTS idx_activity_system_time
            ON activity_snapshots(system_id, timestamp);

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

        CREATE INDEX IF NOT EXISTS idx_timer_time
            ON custom_timers(timestamp);

        CREATE TABLE IF NOT EXISTS system_annotations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
            system_name TEXT NOT NULL UNIQUE,
            note        TEXT NOT NULL,
            updated_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_annotation_system
            ON system_annotations(system_name);

        CREATE TABLE IF NOT EXISTS jump_bridges (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
        CREATE TABLE IF NOT EXISTS jump_bridges (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}',
            system_a   TEXT NOT NULL,
            system_b   TEXT NOT NULL,
            label      TEXT,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            UNIQUE(deployment_id, system_a, system_b)
        );
            system_a   TEXT NOT NULL,
            system_b   TEXT NOT NULL,
            label      TEXT,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            UNIQUE(system_a, system_b)
        );
    """)

    for table in ("adm_snapshots", "activity_snapshots", "custom_timers",
                  "system_annotations", "jump_bridges"):
        _ensure_deployment_column(conn, table)

    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_adm_deployment_time
            ON adm_snapshots(deployment_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_activity_deployment_time
            ON activity_snapshots(deployment_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_timer_deployment_time
            ON custom_timers(deployment_id, timestamp);
    """)

    conn.commit()
    conn.close()
    print(f"[*] Database initialized: {DB_PATH} (deployment={DEPLOYMENT_ID})")


def snapshot_adm_batch(systems):
    """Record ADM readings for multiple systems.
    systems: list of (system_id, system_name, adm, alliance_name) tuples.
    Deduplicates: skips if same ADM was recorded within the last hour.
    """
    now = time.time()
    to_insert = []

    for system_id, system_name, adm, alliance_name in systems:
        if adm <= 0:
            continue
        last = _last_adm_snapshot.get(system_id)
        if last and last["adm"] == adm and (now - last["time"]) < SNAPSHOT_INTERVAL:
            continue
        to_insert.append((DEPLOYMENT_ID, system_id, system_name, adm, alliance_name))
        _last_adm_snapshot[system_id] = {"adm": adm, "time": now}

    if not to_insert:
        return

    conn = get_connection()
    conn.executemany(
        "INSERT INTO adm_snapshots (deployment_id, system_id, system_name, adm, alliance_name) "
        "VALUES (?, ?, ?, ?, ?)",
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

    for system_id, ship_kills, pod_kills, npc_kills, jumps in systems:
        last = _last_activity_snapshot.get(system_id)
        if last and (now - last["time"]) < SNAPSHOT_INTERVAL:
            continue
        to_insert.append((DEPLOYMENT_ID, system_id, ship_kills, pod_kills, npc_kills, jumps))
        _last_activity_snapshot[system_id] = {"time": now}

    if not to_insert:
        return

    conn = get_connection()
    conn.executemany(
        "INSERT INTO activity_snapshots (deployment_id, system_id, ship_kills, pod_kills, npc_kills, jumps) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        to_insert,
    )
    conn.commit()
    conn.close()


def get_adm_history(system_id=None, hours=168):
    """Get ADM history for the last N hours.
    Returns dict keyed by system_id: {system_name, history: [{adm, timestamp}]}
    """
    conn = get_connection()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

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
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

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
    cutoff = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        "ON CONFLICT(system_name) DO UPDATE SET "
        "ON CONFLICT(deployment_id, system_name) DO UPDATE SET "
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
    cur = conn.execute(
        "INSERT OR IGNORE INTO jump_bridges (deployment_id, system_a, system_b, label) VALUES (?, ?, ?, ?)",
        (DEPLOYMENT_ID, a, b, label.strip() if label else None),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


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
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

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
