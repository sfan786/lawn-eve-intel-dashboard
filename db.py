"""
SQLite persistence for historical data.
Stores ADM snapshots, activity, timers, annotations, and jump bridges.

Rows are scoped by deployment_id so a single intel.db can survive moves
between deployments without mixing data. Reads filter by the active
deployment from config; writes always tag rows with the active deployment.
Existing pre-migration rows are tagged 'lawn-kalevala' so they remain
visible if you ever switch back.
"""

import json
import logging
import math
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

        -- War ledger. NOTE: scoped by war_id and deliberately NOT by
        -- deployment_id, the only table here that is. A war belongs to New
        -- Eden, not to wherever we happen to live: the record has to survive
        -- the alliance moving home, and two deployments watching the same war
        -- must see one ledger rather than two partial ones. Do not "fix" this
        -- to match the other tables.
        CREATE TABLE IF NOT EXISTS war_kills (
            war_id          TEXT    NOT NULL,
            killmail_id     INTEGER NOT NULL,
            killmail_time   TEXT    NOT NULL,
            hour_bucket     TEXT    NOT NULL,
            region_id       INTEGER NOT NULL DEFAULT 0,
            system_id       INTEGER NOT NULL DEFAULT 0,
            system_name     TEXT    NOT NULL DEFAULT '',
            victim_side     TEXT,
            killer_side     TEXT,
            victim_alliance_id   INTEGER,
            victim_alliance_name TEXT NOT NULL DEFAULT '',
            victim_corp_id       INTEGER,
            victim_corp_name     TEXT NOT NULL DEFAULT '',
            victim_char_id       INTEGER,
            victim_char_name     TEXT NOT NULL DEFAULT '',
            ship_type_id    INTEGER,
            ship_name       TEXT    NOT NULL DEFAULT '',
            ship_class      TEXT    NOT NULL DEFAULT 'subcap',
            isk_value       REAL    NOT NULL DEFAULT 0,
            isk_destroyed   REAL    NOT NULL DEFAULT 0,
            attacker_count  INTEGER NOT NULL DEFAULT 0,
            pilot_count     INTEGER NOT NULL DEFAULT 0,
            is_npc          INTEGER NOT NULL DEFAULT 0,
            is_awox         INTEGER NOT NULL DEFAULT 0,
            final_blow_alliance_id INTEGER,
            -- JSON array of distinct attacker alliances. Without it a killer
            -- leaderboard is impossible, and so is reclassifying a stored
            -- ledger after a side's roster changes mid-war.
            attacker_alliance_ids  TEXT NOT NULL DEFAULT '[]',
            -- Pilots per attacking alliance on the same kill, as a JSON
            -- object. Lets a roster change re-run the ingest-time majority
            -- rule exactly, rather than approximating it from which
            -- alliances were merely present.
            attacker_alliance_counts TEXT NOT NULL DEFAULT '{{}}',
            names_resolved  INTEGER NOT NULL DEFAULT 0,
            ingested_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            PRIMARY KEY (war_id, killmail_id)
        );

        -- Per-region ingest cursor. last_kill_time is what bounds the next
        -- fetch window, so it may only advance on a confirmed success.
        CREATE TABLE IF NOT EXISTS war_ingest_state (
            war_id          TEXT    NOT NULL,
            region_id       INTEGER NOT NULL,
            last_poll_at    TEXT,
            last_success_at TEXT,
            last_kill_time  TEXT,
            new_kills       INTEGER NOT NULL DEFAULT 0,
            saturated       INTEGER NOT NULL DEFAULT 0,
            last_error      TEXT,
            PRIMARY KEY (war_id, region_id)
        );

        -- Roster edits made from the /war page, layered over the war module's
        -- own lists. They live here rather than in the module because
        -- private/ is mounted read-only in production (docker-compose.yml) —
        -- the app cannot write its own config, and should not: the module
        -- stays the reviewable base roster, this table is the running
        -- correction on top of it.
        --
        -- A row with side NULL is an explicit "not a belligerent", which is
        -- what stops the suggestion panel offering it again. That is why the
        -- absence of a row and a NULL side mean different things.
        CREATE TABLE IF NOT EXISTS war_roster_overrides (
            war_id      TEXT    NOT NULL,
            entity_type TEXT    NOT NULL,
            entity_id   INTEGER NOT NULL,
            side        TEXT,
            name        TEXT    NOT NULL DEFAULT '',
            added_by    TEXT    NOT NULL DEFAULT '',
            added_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            PRIMARY KEY (war_id, entity_type, entity_id)
        );

        -- One poller per war across all gunicorn workers. Unlike the ADM
        -- poller, a duplicate war cycle costs megabytes of zKill traffic
        -- rather than one small ESI call, so the work is leased rather than
        -- merely deduplicated at the insert.
        CREATE TABLE IF NOT EXISTS war_poll_lease (
            war_id      TEXT PRIMARY KEY,
            owner       TEXT NOT NULL,
            acquired_at TEXT NOT NULL,
            expires_at  TEXT NOT NULL
        );
    """)

    # 2. Add deployment_id column to existing tables if missing (for legacy updates)
    for table in ["adm_snapshots", "activity_snapshots", "custom_timers", "system_annotations", "jump_bridges"]:
        cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if "deployment_id" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN deployment_id TEXT NOT NULL DEFAULT '{LEGACY_DEPLOYMENT_ID}'")

    # 2a. Add attacker_alliance_counts to war_kills if missing. Rows written
    # before it stay '{}' — reclassification falls back to the approximate
    # rule for those, and says so, rather than silently mixing the two.
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(war_kills)")}
    if cols and "attacker_alliance_counts" not in cols:
        conn.execute(
            "ALTER TABLE war_kills ADD COLUMN attacker_alliance_counts TEXT NOT NULL DEFAULT '{}'"
        )

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

        CREATE INDEX IF NOT EXISTS idx_war_kills_time ON war_kills(war_id, killmail_time);
        CREATE INDEX IF NOT EXISTS idx_war_kills_sys_time ON war_kills(war_id, system_id, killmail_time);
        CREATE INDEX IF NOT EXISTS idx_war_kills_vside_time ON war_kills(war_id, victim_side, killmail_time);
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


# --- War ledger ---
#
# Every read here is scoped by war_id, never by DEPLOYMENT_ID. See the comment
# on the war_kills table in init() for why that is deliberate.
#
# Aggregates follow get_traffic_summary's shape: a few small GROUP BYs, with
# assembly done in Python. Each one states its own filters rather than
# inheriting a default, because "a kill in the war" and "a kill between the
# belligerents" are genuinely different questions and mixing them silently is
# how a scoreboard ends up wrong.

WAR_RETENTION_DAYS = int(os.environ.get("WAR_RETENTION_DAYS", "0"))
WAR_THIRD_PARTY_DAYS = int(os.environ.get("WAR_THIRD_PARTY_DAYS", "180"))

_WAR_INSERT_COLUMNS = (
    "killmail_id", "killmail_time", "hour_bucket", "region_id", "system_id", "system_name",
    "victim_side", "killer_side", "victim_alliance_id", "victim_alliance_name",
    "victim_corp_id", "victim_corp_name", "victim_char_id", "victim_char_name",
    "ship_type_id", "ship_name", "ship_class", "isk_value", "isk_destroyed",
    "attacker_count", "pilot_count", "is_npc", "is_awox", "final_blow_alliance_id",
    "attacker_alliance_ids", "attacker_alliance_counts", "names_resolved",
)

# Kills counted in the headline scoreboard: real fights between the two sides.
_BELLIGERENT_PAIR = (
    "is_npc = 0 AND victim_side IS NOT NULL AND killer_side IS NOT NULL "
    "AND victim_side != killer_side"
)


def _now_iso():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_days_ago(days):
    return (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _war_cutoff(days):
    """Window start. days=None or 0 means the whole ledger."""
    if not days:
        return "0000-01-01T00:00:00Z"
    return _iso_days_ago(days)


def _region_clause(region_ids, alias=""):
    """SQL fragment + params restricting a query to a war's current regions.

    `alias` prefixes the column for queries that alias the table (e.g. "k.").

    The war module's REGIONS list is the single statement of where a war is
    fought, so it has to govern reads as well as ingest. Dropping a region that
    turned out not to matter would otherwise leave its kills in every total —
    the config would say one thing and the page show another.

    Filtering rather than deleting keeps this reversible: a region put back on
    the list brings its stored history with it instead of needing a re-walk.
    """
    ids = [int(r) for r in region_ids] if region_ids else []
    if not ids:
        return "", []
    return f" AND {alias}region_id IN ({','.join('?' * len(ids))})", ids


def record_war_kills(war_id, rows):
    """Insert classified kills, ignoring any already stored. Returns new rows.

    ON CONFLICT DO NOTHING rather than INSERT OR IGNORE: the latter also
    swallows NOT NULL violations, which is exactly the kind of bug that should
    surface in a test instead of silently dropping rows.
    """
    if not rows:
        return 0
    payload = []
    for r in rows:
        ids = r.get("attacker_alliance_ids") or []
        counts = r.get("attacker_alliance_counts") or {}
        encoded = {"attacker_alliance_ids": json.dumps(ids),
                   "attacker_alliance_counts": json.dumps(counts)}
        payload.append(tuple(
            encoded.get(col, r.get(col)) for col in _WAR_INSERT_COLUMNS
        ))

    placeholders = ",".join("?" * (len(_WAR_INSERT_COLUMNS) + 1))
    conn = get_connection()
    try:
        before = conn.total_changes
        conn.executemany(
            f"INSERT INTO war_kills (war_id, {', '.join(_WAR_INSERT_COLUMNS)}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(war_id, killmail_id) DO NOTHING",
            [(war_id, *row) for row in payload],
        )
        inserted = conn.total_changes - before
        conn.commit()
        return inserted
    finally:
        conn.close()


def get_known_war_kill_ids(war_id, killmail_ids):
    """Which of these killmail IDs are already stored.

    Chunked well under SQLITE_MAX_VARIABLE_NUMBER (999 on older builds). Served
    by the primary key, which is why it is ordered (war_id, killmail_id).
    """
    ids = [int(i) for i in killmail_ids if i]
    if not ids:
        return set()
    found = set()
    conn = get_connection()
    try:
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            rows = conn.execute(
                f"SELECT killmail_id FROM war_kills WHERE war_id = ? "
                f"AND killmail_id IN ({','.join('?' * len(chunk))})",
                (war_id, *chunk),
            ).fetchall()
            found.update(r["killmail_id"] for r in rows)
    finally:
        conn.close()
    return found


def _bucket_expr(bucket):
    """SQL expression grouping killmail_time into day/week/month buckets."""
    if bucket == "month":
        return "substr(killmail_time, 1, 7)"
    if bucket == "week":
        # ISO-ish week start (Monday), so a months-long war stays readable.
        return "date(substr(killmail_time, 1, 10), 'weekday 0', '-6 days')"
    return "substr(killmail_time, 1, 10)"


def get_war_series(war_id, days=7, bucket="day", region_ids=None):
    """Kills and ISK destroyed per side over time."""
    region_sql, region_params = _region_clause(region_ids)
    conn = get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_bucket_expr(bucket)} AS period, "
            "  SUM(CASE WHEN killer_side='a' THEN 1 ELSE 0 END) AS a_kills, "
            "  SUM(CASE WHEN killer_side='a' THEN isk_destroyed ELSE 0 END) AS a_isk, "
            "  SUM(CASE WHEN killer_side='b' THEN 1 ELSE 0 END) AS b_kills, "
            "  SUM(CASE WHEN killer_side='b' THEN isk_destroyed ELSE 0 END) AS b_isk "
            f"FROM war_kills WHERE war_id = ? AND killmail_time >= ? AND {_BELLIGERENT_PAIR}"
            f"{region_sql} "
            "GROUP BY period ORDER BY period ASC",
            (war_id, _war_cutoff(days), *region_params),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "period": r["period"],
            "a_kills": r["a_kills"] or 0,
            "a_isk": r["a_isk"] or 0,
            "b_kills": r["b_kills"] or 0,
            "b_isk": r["b_isk"] or 0,
        }
        for r in rows
    ]


def get_war_summary(war_id, days=7, bucket="day", region_ids=None):
    """Headline scoreboard, time series, contested systems and hull losses."""
    cutoff = _war_cutoff(days)
    region_sql, region_params = _region_clause(region_ids)
    conn = get_connection()
    try:
        totals = conn.execute(
            "SELECT "
            "  SUM(CASE WHEN killer_side='a' THEN 1 ELSE 0 END) AS a_kills, "
            "  SUM(CASE WHEN killer_side='a' THEN isk_destroyed ELSE 0 END) AS a_isk, "
            "  SUM(CASE WHEN killer_side='b' THEN 1 ELSE 0 END) AS b_kills, "
            "  SUM(CASE WHEN killer_side='b' THEN isk_destroyed ELSE 0 END) AS b_isk "
            f"FROM war_kills WHERE war_id = ? AND killmail_time >= ? AND {_BELLIGERENT_PAIR}"
            f"{region_sql}",
            (war_id, cutoff, *region_params),
        ).fetchone()

        coverage = conn.execute(
            "SELECT COUNT(*) AS rows, MIN(killmail_time) AS first_kill, "
            "       MAX(killmail_time) AS last_kill "
            f"FROM war_kills WHERE war_id = ?{region_sql}",
            (war_id, *region_params),
        ).fetchone()

        # Contested systems count ALL violence in the system, third parties
        # included: a system does not stop being fought over because a neutral
        # died in it.
        #
        # But the *shortlist* is taken by belligerent involvement, not by ISK.
        # A war's regions include busy space where most kills have nothing to
        # do with it (measured: two Drone regions run under 30% war-related),
        # so picking the top systems by raw ISK would let unrelated ratting
        # losses crowd genuinely contested systems out of the list before the
        # contest ranking below ever sees them.
        systems = conn.execute(
            "SELECT system_id, system_name, region_id, COUNT(*) AS kills, "
            "  SUM(isk_destroyed) AS isk, MAX(killmail_time) AS last_kill, "
            "  SUM(CASE WHEN victim_side='a' THEN 1 ELSE 0 END) AS a_losses, "
            "  SUM(CASE WHEN victim_side='b' THEN 1 ELSE 0 END) AS b_losses, "
            "  SUM(CASE WHEN victim_side IS NULL THEN 1 ELSE 0 END) AS other_losses, "
            "  SUM(CASE WHEN victim_side IS NOT NULL OR killer_side IS NOT NULL "
            "           THEN 1 ELSE 0 END) AS war_kills "
            "FROM war_kills WHERE war_id = ? AND killmail_time >= ? AND is_npc = 0"
            f"{region_sql} "
            "GROUP BY system_id HAVING war_kills > 0 "
            "ORDER BY war_kills DESC, isk DESC LIMIT 40",
            (war_id, cutoff, *region_params),
        ).fetchall()

        hulls = conn.execute(
            "SELECT victim_side, ship_class, COUNT(*) AS n, SUM(isk_destroyed) AS isk "
            "FROM war_kills WHERE war_id = ? AND killmail_time >= ? AND is_npc = 0 "
            "  AND victim_side IS NOT NULL"
            f"{region_sql} "
            "GROUP BY victim_side, ship_class",
            (war_id, cutoff, *region_params),
        ).fetchall()

        biggest = conn.execute(
            "SELECT killmail_id, killmail_time, system_name, victim_side, "
            "       victim_alliance_name, ship_name, ship_class, isk_destroyed "
            f"FROM war_kills WHERE war_id = ? AND killmail_time >= ? AND {_BELLIGERENT_PAIR}"
            f"{region_sql} "
            "ORDER BY isk_destroyed DESC LIMIT 10",
            (war_id, cutoff, *region_params),
        ).fetchall()
    finally:
        conn.close()

    ship_classes = {"a": {}, "b": {}}
    for r in hulls:
        ship_classes[r["victim_side"]][r["ship_class"]] = {
            "count": r["n"],
            "isk": r["isk"] or 0,
        }

    contested = []
    for r in systems:
        a, b = r["a_losses"] or 0, r["b_losses"] or 0
        # Balance stops a one-sided gank corridor outranking a real fight:
        # 40-0 scores 0 however many kills it holds.
        balance = min(a, b) / max(a, b, 1)
        contested.append({
            "system_id": r["system_id"],
            "system_name": r["system_name"],
            "region_id": r["region_id"],
            "kills": r["kills"],
            "isk": r["isk"] or 0,
            "last_kill": r["last_kill"],
            "a_losses": a,
            "b_losses": b,
            "other_losses": r["other_losses"] or 0,
            "war_kills": r["war_kills"] or 0,
            # Scored on war kills, not total kills: a system with 200 unrelated
            # losses and two belligerent ones is not a contested system.
            "contest_score": round(balance * math.log1p(r["war_kills"] or 0), 3),
        })
    # SQL selects the top systems by ISK (cheap, index-friendly); the ranking
    # the panel actually shows is by how contested they are, which needs both
    # sides' loss counts and so can only be computed here.
    contested.sort(key=lambda s: (s["contest_score"], s["isk"]), reverse=True)

    a_kills = totals["a_kills"] or 0
    b_kills = totals["b_kills"] or 0
    a_isk = totals["a_isk"] or 0
    b_isk = totals["b_isk"] or 0
    return {
        "war_id": war_id,
        "days": days,
        "bucket": bucket,
        "generated_at": _now_iso(),
        "totals": {
            "a_kills": a_kills,
            "b_kills": b_kills,
            "a_isk": a_isk,
            "b_isk": b_isk,
            # Efficiency reads as "share of destruction I inflicted".
            "a_efficiency": round(100 * a_isk / (a_isk + b_isk), 1) if (a_isk + b_isk) else 0,
            "b_efficiency": round(100 * b_isk / (a_isk + b_isk), 1) if (a_isk + b_isk) else 0,
        },
        "coverage": {
            "rows": coverage["rows"] or 0,
            "first_kill": coverage["first_kill"],
            "last_kill": coverage["last_kill"],
        },
        "series": get_war_series(war_id, days, bucket, region_ids=region_ids),
        "contested_systems": contested,
        "ship_classes": ship_classes,
        "biggest_kills": [dict(r) for r in biggest],
    }


def get_war_leaderboards(war_id, days=7, limit=15, region_ids=None):
    """Who is bleeding, and who is on the killmails.

    The killer board credits every alliance present on a kill, so its ISK
    column sums to more than the ISK actually destroyed. That is how
    zKillboard counts too, which is why the API and UI call it "involved"
    rather than "destroyed".
    """
    cutoff = _war_cutoff(days)
    region_sql, region_params = _region_clause(region_ids)
    k_region_sql, _ = _region_clause(region_ids, alias="k.")
    conn = get_connection()
    try:
        bleeders = conn.execute(
            "SELECT victim_side, victim_alliance_id AS alliance_id, "
            "  MAX(victim_alliance_name) AS name, COUNT(*) AS losses, "
            "  SUM(isk_destroyed) AS isk_lost "
            "FROM war_kills WHERE war_id = ? AND killmail_time >= ? AND is_npc = 0 "
            "  AND victim_side IS NOT NULL AND victim_alliance_id IS NOT NULL"
            f"{region_sql} "
            "GROUP BY victim_alliance_id ORDER BY isk_lost DESC LIMIT ?",
            (war_id, cutoff, *region_params, limit),
        ).fetchall()

        killers = conn.execute(
            "SELECT je.value AS alliance_id, COUNT(*) AS involved_kills, "
            "  SUM(k.isk_destroyed) AS isk_involved "
            "FROM war_kills k, json_each(k.attacker_alliance_ids) je "
            "WHERE k.war_id = ? AND k.killmail_time >= ? AND k.is_npc = 0 "
            "  AND k.victim_side IS NOT NULL"
            f"{k_region_sql} "
            "GROUP BY je.value ORDER BY isk_involved DESC LIMIT ?",
            (war_id, cutoff, *region_params, limit),
        ).fetchall()
    finally:
        conn.close()

    return {
        "bleeders": [dict(r) for r in bleeders],
        "killers": [dict(r) for r in killers],
    }


def get_war_participant(war_id, alliance_ids, days=7, region_ids=None):
    """One alliance's (or coalition's) own war record."""
    ids = [int(a) for a in alliance_ids or [] if a]
    if not ids:
        return None
    cutoff = _war_cutoff(days)
    marks = ",".join("?" * len(ids))
    region_sql, region_params = _region_clause(region_ids)
    k_region_sql, _ = _region_clause(region_ids, alias="k.")
    conn = get_connection()
    try:
        losses = conn.execute(
            f"SELECT COUNT(*) AS n, SUM(isk_destroyed) AS isk FROM war_kills "
            f"WHERE war_id = ? AND killmail_time >= ? AND is_npc = 0 "
            f"AND victim_alliance_id IN ({marks}){region_sql}",
            (war_id, cutoff, *ids, *region_params),
        ).fetchone()

        kills = conn.execute(
            f"SELECT COUNT(*) AS n, SUM(k.isk_destroyed) AS isk FROM war_kills k "
            f"WHERE k.war_id = ? AND k.killmail_time >= ? AND k.is_npc = 0 "
            f"AND k.victim_alliance_id NOT IN ({marks}) "
            f"AND EXISTS (SELECT 1 FROM json_each(k.attacker_alliance_ids) je "
            f"            WHERE je.value IN ({marks})){k_region_sql}",
            (war_id, cutoff, *ids, *ids, *region_params),
        ).fetchone()

        systems = conn.execute(
            f"SELECT system_name, COUNT(*) AS n FROM war_kills k "
            f"WHERE k.war_id = ? AND k.killmail_time >= ? AND k.is_npc = 0 "
            f"AND (k.victim_alliance_id IN ({marks}) "
            f"     OR EXISTS (SELECT 1 FROM json_each(k.attacker_alliance_ids) je "
            f"                WHERE je.value IN ({marks}))){k_region_sql} "
            f"GROUP BY system_id ORDER BY n DESC LIMIT 8",
            (war_id, cutoff, *ids, *ids, *region_params),
        ).fetchall()
    finally:
        conn.close()

    isk_killed = kills["isk"] or 0
    isk_lost = losses["isk"] or 0
    return {
        "kills": kills["n"] or 0,
        "losses": losses["n"] or 0,
        "isk_killed": isk_killed,
        "isk_lost": isk_lost,
        "efficiency": round(100 * isk_killed / (isk_killed + isk_lost), 1) if (isk_killed + isk_lost) else 0,
        "top_systems": [dict(r) for r in systems],
    }


def get_war_unclassified(war_id, days=7, limit=20, region_ids=None, known_alliance_ids=None):
    """Alliances fighting in the war zone that are on neither roster.

    Feeds the roster-suggestion panel: a war's membership drifts, and the
    killmails are the only source that notices.

    `known_alliance_ids` must be passed, or the panel suggests entities that
    are already rostered. `killer_side` is NULL whenever no side won a majority
    of a kill's attackers — a rostered alliance that turns up as a minority
    participant on such a kill would otherwise be reported as unaligned.
    """
    cutoff = _war_cutoff(days)
    region_sql, region_params = _region_clause(region_ids)
    k_region_sql, _ = _region_clause(region_ids, alias="k.")
    known = [int(a) for a in known_alliance_ids or [] if a]
    known_sql = f" AND je.value NOT IN ({','.join('?' * len(known))})" if known else ""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT je.value AS alliance_id, COUNT(*) AS involved_kills, "
            "  SUM(k.isk_destroyed) AS isk_involved, MAX(k.killmail_time) AS last_seen, "
            "  SUM(CASE WHEN k.victim_side='a' THEN 1 ELSE 0 END) AS vs_a, "
            "  SUM(CASE WHEN k.victim_side='b' THEN 1 ELSE 0 END) AS vs_b "
            "FROM war_kills k, json_each(k.attacker_alliance_ids) je "
            "WHERE k.war_id = ? AND k.killmail_time >= ? AND k.is_npc = 0 "
            "  AND k.killer_side IS NULL"
            f"{k_region_sql}{known_sql} "
            "GROUP BY je.value HAVING involved_kills >= 3 "
            "ORDER BY involved_kills DESC LIMIT ?",
            (war_id, cutoff, *region_params, *known, limit),
        ).fetchall()

        names = conn.execute(
            "SELECT victim_alliance_id AS id, MAX(victim_alliance_name) AS name "
            "FROM war_kills WHERE war_id = ? AND victim_alliance_name != ''"
            f"{region_sql} "
            "GROUP BY victim_alliance_id",
            (war_id, *region_params),
        ).fetchall()
    finally:
        conn.close()

    known = {r["id"]: r["name"] for r in names}
    out = []
    for r in rows:
        vs_a, vs_b = r["vs_a"] or 0, r["vs_b"] or 0
        out.append({
            "alliance_id": r["alliance_id"],
            "name": known.get(r["alliance_id"], ""),
            "involved_kills": r["involved_kills"],
            "isk_involved": r["isk_involved"] or 0,
            "last_seen": r["last_seen"],
            "kills_vs_a": vs_a,
            "kills_vs_b": vs_b,
            # Whoever they shoot more is the side they are probably not on.
            "suggested_side": "b" if vs_a > vs_b else ("a" if vs_b > vs_a else None),
        })
    return out


def get_war_kill_feed(war_id, limit=50, before=None, side=None, ship_class=None,
                      system_id=None, min_isk=None, include_npc=False, region_ids=None):
    """Recent classified kills, newest first.

    Ordered by (killmail_time, killmail_id) because a fight puts many kills in
    the same second — ordering by time alone makes `before` paging skip and
    repeat rows.
    """
    where = ["war_id = ?"]
    params = [war_id]
    ids = [int(r) for r in region_ids] if region_ids else []
    if ids:
        where.append(f"region_id IN ({','.join('?' * len(ids))})")
        params += ids
    if not include_npc:
        where.append("is_npc = 0")
    if side in ("a", "b"):
        where.append("(victim_side = ? OR killer_side = ?)")
        params += [side, side]
    if ship_class:
        where.append("ship_class = ?")
        params.append(ship_class)
    if system_id:
        where.append("system_id = ?")
        params.append(int(system_id))
    if min_isk:
        where.append("isk_destroyed >= ?")
        params.append(float(min_isk))
    if before:
        before_time, _, before_id = str(before).partition("|")
        if before_time and before_id:
            where.append("(killmail_time < ? OR (killmail_time = ? AND killmail_id < ?))")
            params += [before_time, before_time, int(before_id)]

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT killmail_id, killmail_time, system_id, system_name, region_id, "
            "  victim_side, killer_side, victim_alliance_name, victim_corp_name, "
            "  victim_char_name, ship_name, ship_class, isk_destroyed, isk_value, "
            "  attacker_count, pilot_count, is_npc "
            f"FROM war_kills WHERE {' AND '.join(where)} "
            "ORDER BY killmail_time DESC, killmail_id DESC LIMIT ?",
            (*params, int(limit)),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_war_battles(war_id, days=7, gap_seconds=1800, min_kills=3, limit=25, region_ids=None):
    """Cluster kills into engagements.

    Sessionized on a gap in time within a system, not by clock hour: a fight
    running 19:55 to 20:20 is one battle, and two unrelated ganks at 19:05 and
    19:50 are not. Hour bucketing gets both of those wrong. Done in Python over
    one ordered scan — the row counts are small and the loop is far easier to
    test than a window-function query.
    """
    cutoff = _war_cutoff(days)
    region_sql, region_params = _region_clause(region_ids)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT system_id, system_name, region_id, killmail_id, killmail_time, "
            "  hour_bucket, isk_destroyed, victim_side, ship_class, attacker_count "
            "FROM war_kills WHERE war_id = ? AND killmail_time >= ? AND is_npc = 0 "
            "  AND (victim_side IS NOT NULL OR killer_side IS NOT NULL)"
            f"{region_sql} "
            "ORDER BY system_id ASC, killmail_time ASC, killmail_id ASC",
            (war_id, cutoff, *region_params),
        ).fetchall()
    finally:
        conn.close()

    battles = []
    current = None
    last_ts = None

    def _epoch(ts):
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()

    def _flush(battle):
        if not battle or battle["kills"] < min_kills:
            return
        # Anchor the zKill related link on the busiest hour: a fight starting
        # at 19:58 belongs on the 20:00 page, not the 19:00 one.
        peak_hour = max(battle["_hours"], key=battle["_hours"].get)
        battle["related_url"] = (
            f"https://zkillboard.com/related/{battle['system_id']}/"
            f"{peak_hour.replace('-', '').replace('T', '')}00/"
        )
        battle.pop("_hours", None)
        a, b = battle["a_losses"], battle["b_losses"]
        battle["winner"] = "b" if a > b else ("a" if b > a else None)
        battles.append(battle)

    for r in rows:
        ts = _epoch(r["killmail_time"])
        if current is None or r["system_id"] != current["system_id"] or ts - last_ts > gap_seconds:
            _flush(current)
            current = {
                "system_id": r["system_id"],
                "system_name": r["system_name"],
                "region_id": r["region_id"],
                "start_time": r["killmail_time"],
                "end_time": r["killmail_time"],
                "kills": 0,
                "isk": 0.0,
                "a_losses": 0,
                "b_losses": 0,
                "cap_losses": 0,
                "structure_losses": 0,
                "peak_attackers": 0,
                "_hours": {},
            }
        current["kills"] += 1
        current["isk"] += r["isk_destroyed"] or 0
        current["end_time"] = r["killmail_time"]
        current["peak_attackers"] = max(current["peak_attackers"], r["attacker_count"] or 0)
        if r["victim_side"] == "a":
            current["a_losses"] += 1
        elif r["victim_side"] == "b":
            current["b_losses"] += 1
        if r["ship_class"] in ("capital", "super"):
            current["cap_losses"] += 1
        if r["ship_class"] == "structure":
            current["structure_losses"] += 1
        current["_hours"][r["hour_bucket"]] = current["_hours"].get(r["hour_bucket"], 0) + 1
        last_ts = ts
    _flush(current)

    for b in battles:
        b["duration_minutes"] = round(
            (_epoch(b["end_time"]) - _epoch(b["start_time"])) / 60, 1
        )
    battles.sort(key=lambda x: x["isk"], reverse=True)
    return battles[:limit]


def get_war_roster_overrides(war_id):
    """Roster edits made from the page, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT entity_type, entity_id, side, name, added_by, added_at "
            "FROM war_roster_overrides WHERE war_id = ? ORDER BY added_at DESC",
            (war_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def set_war_roster_override(war_id, entity_type, entity_id, side, name="", added_by=""):
    """Assign an entity to a side, or to no side when `side` is None."""
    if entity_type not in ("alliance", "corporation"):
        raise ValueError("entity_type must be 'alliance' or 'corporation'")
    if side not in ("a", "b", None):
        raise ValueError("side must be 'a', 'b' or None")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO war_roster_overrides "
            "(war_id, entity_type, entity_id, side, name, added_by) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(war_id, entity_type, entity_id) DO UPDATE SET "
            "  side = excluded.side, name = excluded.name, added_by = excluded.added_by, "
            "  added_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')",
            (war_id, entity_type, int(entity_id), side, name or "", added_by or ""),
        )
        conn.commit()
    finally:
        conn.close()


def delete_war_roster_override(war_id, entity_type, entity_id):
    """Drop an override, reverting to whatever the war module says."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM war_roster_overrides "
            "WHERE war_id = ? AND entity_type = ? AND entity_id = ?",
            (war_id, entity_type, int(entity_id)),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def reclassify_war_kills(war_id, spec, region_ids=None, entity_id=None):
    """Recompute stored sides after a roster change. Returns rows updated.

    Runs off the IDs already on each row, so a roster correction applies to the
    war's whole history without re-fetching anything from zKillboard.

    Two things keep this from corrupting the ledger, both learned the hard way
    from a change that did not round-trip:

    * **Scoped to the entity that changed** (`entity_id`). Rows that entity was
      never on keep their ingest-time classification untouched. Rewriting every
      row on every edit meant an assignment and its undo did not cancel out.
    * **Exact where the data allows.** Rows carrying `attacker_alliance_counts`
      reproduce the ingest majority rule precisely. Rows written before that
      column existed fall back to "the only side present, else the final blow",
      which can differ on genuinely mixed fights — the fallback is why the
      scoping matters.
    """
    region_sql, region_params = _region_clause(region_ids)
    where = f"war_id = ?{region_sql}"
    params = [war_id, *region_params]
    if entity_id:
        # Only kills this entity took part in can change side because of it.
        where += (" AND (victim_alliance_id = ? OR victim_corp_id = ? "
                  "OR EXISTS (SELECT 1 FROM json_each(war_kills.attacker_alliance_ids) je "
                  "           WHERE je.value = ?))")
        params += [entity_id, entity_id, entity_id]

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT killmail_id, victim_side, killer_side, victim_alliance_id, "
            "  victim_corp_id, final_blow_alliance_id, attacker_alliance_ids, "
            "  attacker_alliance_counts "
            f"FROM war_kills WHERE {where}",
            params,
        ).fetchall()

        updates = []
        for r in rows:
            victim_side = (
                spec.side_by_corp.get(r["victim_corp_id"])
                or spec.side_by_alliance.get(r["victim_alliance_id"])
            )
            killer_side = _recompute_killer_side(r, spec)
            if victim_side != r["victim_side"] or killer_side != r["killer_side"]:
                updates.append((victim_side, killer_side, war_id, r["killmail_id"]))

        if updates:
            conn.executemany(
                "UPDATE war_kills SET victim_side = ?, killer_side = ? "
                "WHERE war_id = ? AND killmail_id = ?",
                updates,
            )
            conn.commit()
        return len(updates)
    finally:
        conn.close()


def _recompute_killer_side(row, spec):
    """Which side scored a stored kill, under the current roster."""
    try:
        counts = json.loads(row["attacker_alliance_counts"] or "{}")
    except (TypeError, ValueError):
        counts = {}

    if counts:
        # Exact: the same majority-of-pilots rule ingest applies.
        per_side = {}
        for alliance_id, n in counts.items():
            side = spec.side_by_alliance.get(int(alliance_id))
            if side:
                per_side[side] = per_side.get(side, 0) + int(n or 0)
        per_side = {s: n for s, n in per_side.items() if n}
        if not per_side:
            return None
        best = max(per_side.values())
        leaders = [s for s, n in per_side.items() if n == best]
        if len(leaders) == 1:
            return leaders[0]
        fb = spec.side_by_alliance.get(row["final_blow_alliance_id"])
        return fb if fb in leaders else sorted(leaders)[0]

    # Rows written before the counts column. Only the cases that do not need
    # pilot numbers are recomputed; anything genuinely ambiguous keeps what
    # ingest decided at the time.
    #
    # Guessing here (an earlier version used the final blow) is what made a
    # roster edit lossy: it rewrote kills whose majority it could not know, so
    # undoing the edit did not restore them. A stale-but-original answer beats
    # a confidently wrong one.
    try:
        attackers = json.loads(row["attacker_alliance_ids"] or "[]")
    except (TypeError, ValueError):
        attackers = []
    sides = {spec.side_by_alliance.get(a) for a in attackers}
    sides.discard(None)
    if len(sides) == 1:
        # One side present, so it holds the majority however many pilots each
        # brought — the same answer ingest reached.
        return next(iter(sides))
    if not sides:
        return None
    return row["killer_side"]


def get_war_latest_kill_time(war_id, region_id):
    """Newest stored kill for a region, or None.

    Lets the poller pick up where a backfill left off. The two write the same
    rows but not the same cursor: `tools/backfill_war.py` walks history and
    never touches `war_ingest_state`, so without this a freshly backfilled
    region looks uningested and the first poll cycle re-walks a full week that
    is already stored.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT MAX(killmail_time) AS t FROM war_kills WHERE war_id = ? AND region_id = ?",
            (war_id, region_id),
        ).fetchone()
    finally:
        conn.close()
    return row["t"] if row else None


def get_war_ingest_state(war_id):
    """Per-region ingest health, for the coverage line on the page."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT region_id, last_poll_at, last_success_at, last_kill_time, "
            "       new_kills, saturated, last_error "
            "FROM war_ingest_state WHERE war_id = ? ORDER BY region_id",
            (war_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def upsert_war_ingest_state(war_id, region_id, **fields):
    """Merge cursor/health fields for one region. Unset fields are untouched."""
    allowed = ("last_poll_at", "last_success_at", "last_kill_time",
               "new_kills", "saturated", "last_error")
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    cols = list(updates)
    conn = get_connection()
    try:
        conn.execute(
            f"INSERT INTO war_ingest_state (war_id, region_id, {', '.join(cols)}) "
            f"VALUES (?, ?, {', '.join('?' * len(cols))}) "
            f"ON CONFLICT(war_id, region_id) DO UPDATE SET "
            + ", ".join(f"{c} = excluded.{c}" for c in cols),
            (war_id, region_id, *(updates[c] for c in cols)),
        )
        conn.commit()
    finally:
        conn.close()


def acquire_war_poll_lease(war_id, owner, ttl_seconds):
    """Claim the right to poll this war for ttl_seconds. True if we hold it.

    BEGIN IMMEDIATE serializes the check-and-take across workers and processes.
    An expired lease is takeable, so a crashed holder costs one TTL of delay
    rather than needing any supervision.
    """
    now = _now_iso()
    expires = (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = get_connection()
    conn.isolation_level = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO war_poll_lease (war_id, owner, acquired_at, expires_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(war_id) DO UPDATE SET "
            "  owner = excluded.owner, acquired_at = excluded.acquired_at, "
            "  expires_at = excluded.expires_at "
            "WHERE war_poll_lease.expires_at < ? OR war_poll_lease.owner = ?",
            (war_id, owner, now, expires, now, owner),
        )
        held = conn.execute(
            "SELECT owner FROM war_poll_lease WHERE war_id = ?", (war_id,)
        ).fetchone()
        conn.commit()
        return bool(held) and held["owner"] == owner
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def resolve_war_kill_names(war_id, names, limit=900):
    """Backfill display names onto rows stored with IDs only.

    Ingest never blocks on name resolution — IDs are the source of truth and a
    name is presentation — so this repairs the gap afterwards.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT killmail_id, victim_alliance_id, victim_corp_id, victim_char_id, ship_type_id "
            "FROM war_kills WHERE war_id = ? AND names_resolved = 0 LIMIT ?",
            (war_id, limit),
        ).fetchall()
        if not rows:
            return 0
        updates = []
        for r in rows:
            updates.append((
                names.get(r["victim_alliance_id"], "") or "",
                names.get(r["victim_corp_id"], "") or "",
                names.get(r["victim_char_id"], "") or "",
                names.get(r["ship_type_id"], "") or "",
                war_id,
                r["killmail_id"],
            ))
        conn.executemany(
            "UPDATE war_kills SET victim_alliance_name = ?, victim_corp_name = ?, "
            "  victim_char_name = ?, ship_name = ?, names_resolved = 1 "
            "WHERE war_id = ? AND killmail_id = ?",
            updates,
        )
        conn.commit()
        return len(updates)
    finally:
        conn.close()


def get_war_rows_needing_names(war_id, limit=900):
    """Entity IDs still missing a name, for one bulk resolve."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT victim_alliance_id, victim_corp_id, victim_char_id, ship_type_id "
            "FROM war_kills WHERE war_id = ? AND names_resolved = 0 LIMIT ?",
            (war_id, limit),
        ).fetchall()
    finally:
        conn.close()
    ids = set()
    for r in rows:
        for key in ("victim_alliance_id", "victim_corp_id", "victim_char_id", "ship_type_id"):
            if r[key]:
                ids.add(r[key])
    return sorted(ids)


def prune_war_kills(war_id, days=None, third_party_days=None):
    """Trim the ledger. Returns rows deleted.

    Belligerent kills are the record the page exists to show, so they are kept
    indefinitely by default (WAR_RETENTION_DAYS=0). Third-party rows are stored
    only to keep the already-seen filter honest, so they expire sooner.
    """
    days = WAR_RETENTION_DAYS if days is None else days
    third_party_days = WAR_THIRD_PARTY_DAYS if third_party_days is None else third_party_days
    conn = get_connection()
    try:
        before = conn.total_changes
        if days:
            conn.execute(
                "DELETE FROM war_kills WHERE war_id = ? AND killmail_time < ?",
                (war_id, _iso_days_ago(days)),
            )
        if third_party_days:
            conn.execute(
                "DELETE FROM war_kills WHERE war_id = ? AND killmail_time < ? "
                "AND victim_side IS NULL AND killer_side IS NULL",
                (war_id, _iso_days_ago(third_party_days)),
            )
        deleted = conn.total_changes - before
        conn.commit()
        return deleted
    finally:
        conn.close()
