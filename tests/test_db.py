"""
Tests for db.py — SQLite persistence layer.

Uses the `tmp_db` fixture from conftest.py which:
  - Points DB_PATH at a fresh temp file
  - Sets DEPLOYMENT_ID to 'test_deploy'
  - Clears in-memory dedup caches
  - Calls db.init()
"""

import sqlite3
import time
from datetime import datetime, timezone, timedelta

import pytest
import db


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _conn(tmp_db):
    """Raw connection to the test DB for assertion queries."""
    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    return conn


def _count(tmp_db, table, where="1=1"):
    with _conn(tmp_db) as c:
        return c.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]


def _future_ts(days=1):
    """ISO timestamp N days in the future (so active-timer queries include it)."""
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _old_ts(hours=2):
    """ISO timestamp N hours in the past."""
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchema:
    def test_all_tables_exist(self, tmp_db):
        expected = {
            "adm_snapshots", "activity_snapshots", "custom_timers",
            "system_annotations", "jump_bridges", "sov_state",
            "sov_changes", "entosis_nodes",
        }
        with _conn(tmp_db) as c:
            tables = {r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        assert expected.issubset(tables)

    def test_init_is_idempotent(self, tmp_db):
        # Calling init() a second time must not raise or duplicate tables
        db.init()
        with _conn(tmp_db) as c:
            n = c.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='adm_snapshots'"
            ).fetchone()[0]
        assert n == 1


# ---------------------------------------------------------------------------
# ADM snapshot deduplication
# ---------------------------------------------------------------------------

class TestAdmSnapshot:
    def test_first_call_inserts(self, tmp_db):
        db.snapshot_adm_batch([(1, "Sys1", 5.0, "LAWN")])
        assert _count(tmp_db, "adm_snapshots") == 1

    def test_same_adm_within_hour_deduplicates(self, tmp_db):
        db.snapshot_adm_batch([(1, "Sys1", 5.0, "LAWN")])
        db.snapshot_adm_batch([(1, "Sys1", 5.0, "LAWN")])
        assert _count(tmp_db, "adm_snapshots") == 1

    def test_different_adm_inserts_new_row(self, tmp_db):
        db.snapshot_adm_batch([(1, "Sys1", 5.0, "LAWN")])
        db.snapshot_adm_batch([(1, "Sys1", 4.0, "LAWN")])
        assert _count(tmp_db, "adm_snapshots") == 2

    def test_zero_adm_skipped(self, tmp_db):
        db.snapshot_adm_batch([(1, "Sys1", 0.0, "LAWN")])
        assert _count(tmp_db, "adm_snapshots") == 0

    def test_old_record_allows_new_insert(self, tmp_db, monkeypatch):
        # Insert a row with a timestamp older than the 1-hour dedup window
        old_ts = _old_ts(hours=2)
        with _conn(tmp_db) as c:
            c.execute(
                "INSERT INTO adm_snapshots (deployment_id, system_id, system_name, adm, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                ("test_deploy", 1, "Sys1", 5.0, old_ts),
            )
            c.commit()

        # Clear in-memory cache so the DB path is used
        monkeypatch.setattr(db, "_last_adm_snapshot", {})
        db.snapshot_adm_batch([(1, "Sys1", 5.0, "LAWN")])
        assert _count(tmp_db, "adm_snapshots") == 2

    def test_multiple_systems_batched(self, tmp_db):
        db.snapshot_adm_batch([
            (1, "Sys1", 5.0, "LAWN"),
            (2, "Sys2", 3.0, "LAWN"),
            (3, "Sys3", 1.5, "LAWN"),
        ])
        assert _count(tmp_db, "adm_snapshots") == 3


# ---------------------------------------------------------------------------
# Activity snapshot deduplication
# ---------------------------------------------------------------------------

class TestActivitySnapshot:
    def test_first_call_inserts(self, tmp_db):
        db.snapshot_activity_batch([(1, 5, 2, 100, 30)])
        assert _count(tmp_db, "activity_snapshots") == 1

    def test_same_system_within_hour_deduplicates(self, tmp_db):
        db.snapshot_activity_batch([(1, 5, 2, 100, 30)])
        db.snapshot_activity_batch([(1, 0, 0, 0, 0)])  # different values — still deduped
        assert _count(tmp_db, "activity_snapshots") == 1

    def test_old_record_allows_new_insert(self, tmp_db, monkeypatch):
        old_ts = _old_ts(hours=2)
        with _conn(tmp_db) as c:
            c.execute(
                "INSERT INTO activity_snapshots "
                "(deployment_id, system_id, ship_kills, pod_kills, npc_kills, jumps, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("test_deploy", 1, 5, 2, 100, 30, old_ts),
            )
            c.commit()

        monkeypatch.setattr(db, "_last_activity_snapshot", {})
        db.snapshot_activity_batch([(1, 10, 3, 200, 50)])
        assert _count(tmp_db, "activity_snapshots") == 2


# ---------------------------------------------------------------------------
# ADM history window
# ---------------------------------------------------------------------------

class TestAdmHistory:
    def test_returns_rows_within_window(self, tmp_db):
        db.snapshot_adm_batch([(1, "Sys1", 5.0, "LAWN")])
        result = db.get_adm_history(system_id=1, hours=24)
        assert 1 in result
        assert len(result[1]["history"]) == 1

    def test_excludes_rows_outside_window(self, tmp_db):
        old_ts = _old_ts(hours=50)
        with _conn(tmp_db) as c:
            c.execute(
                "INSERT INTO adm_snapshots (deployment_id, system_id, system_name, adm, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                ("test_deploy", 1, "Sys1", 4.0, old_ts),
            )
            c.commit()
        result = db.get_adm_history(system_id=1, hours=24)
        # 50h-old row should not appear in a 24h window
        assert result.get(1) is None or len(result.get(1, {}).get("history", [])) == 0


# ---------------------------------------------------------------------------
# Deployment isolation
# ---------------------------------------------------------------------------

class TestDeploymentIsolation:
    def test_timers_scoped_by_deployment(self, tmp_db, monkeypatch):
        # Write under 'test_deploy'
        db.add_timer("Sys1", "Citadel", "LAWN", "armor", _future_ts())
        assert len(db.get_active_timers()) == 1

        # Switch to a different deployment — should see nothing
        monkeypatch.setattr(db, "DEPLOYMENT_ID", "other_deploy")
        assert db.get_active_timers() == []

    def test_annotations_scoped_by_deployment(self, tmp_db, monkeypatch):
        db.upsert_annotation("Sys1", "hello")
        assert "Sys1" in db.get_all_annotations()

        monkeypatch.setattr(db, "DEPLOYMENT_ID", "other_deploy")
        assert db.get_all_annotations() == {}

    def test_adm_history_scoped_by_deployment(self, tmp_db, monkeypatch):
        db.snapshot_adm_batch([(1, "Sys1", 5.0, "LAWN")])
        assert db.get_adm_history(system_id=1, hours=24) != {}

        monkeypatch.setattr(db, "DEPLOYMENT_ID", "other_deploy")
        assert db.get_adm_history(system_id=1, hours=24) == {}

    def test_annotations_unique_constraint_per_deployment(self, tmp_db, monkeypatch):
        db.upsert_annotation("Sys1", "Note A")
        monkeypatch.setattr(db, "DEPLOYMENT_ID", "other_deploy")
        db.upsert_annotation("Sys1", "Note B")
        assert db.get_all_annotations()["Sys1"]["note"] == "Note B"
        monkeypatch.setattr(db, "DEPLOYMENT_ID", "test_deploy")
        assert db.get_all_annotations()["Sys1"]["note"] == "Note A"


# ---------------------------------------------------------------------------
# Timer CRUD
# ---------------------------------------------------------------------------

class TestTimerCrud:
    def test_add_and_retrieve(self, tmp_db):
        db.add_timer("Sys1", "Citadel", "Hostiles", "armor", _future_ts(), notes="watch out")
        timers = db.get_active_timers()
        assert len(timers) == 1
        assert timers[0]["system_name"] == "Sys1"
        assert timers[0]["notes"] == "watch out"

    def test_delete_removes_timer(self, tmp_db):
        db.add_timer("Sys1", "Citadel", "Hostiles", "armor", _future_ts())
        timers = db.get_active_timers()
        timer_id = timers[0]["id"]

        db.delete_timer(timer_id)
        assert db.get_active_timers() == []

    def test_delete_nonexistent_does_not_raise(self, tmp_db):
        db.delete_timer(99999)  # should not raise

    def test_multiple_timers_ordered_by_time(self, tmp_db):
        t1 = _future_ts(days=1)
        t2 = _future_ts(days=2)
        db.add_timer("Sys2", "iHub", "Hostiles", "hull", t2)
        db.add_timer("Sys1", "Citadel", "Hostiles", "armor", t1)
        timers = db.get_active_timers()
        assert timers[0]["system_name"] == "Sys1"  # earlier timer first


# ---------------------------------------------------------------------------
# Annotation CRUD
# ---------------------------------------------------------------------------

class TestAnnotationCrud:
    def test_upsert_inserts(self, tmp_db):
        db.upsert_annotation("Sys1", "First note")
        ann = db.get_all_annotations()
        assert ann["Sys1"]["note"] == "First note"

    def test_upsert_updates_existing(self, tmp_db):
        db.upsert_annotation("Sys1", "First note")
        db.upsert_annotation("Sys1", "Updated note")
        ann = db.get_all_annotations()
        assert ann["Sys1"]["note"] == "Updated note"
        assert _count(tmp_db, "system_annotations") == 1

    def test_empty_note_deletes(self, tmp_db):
        db.upsert_annotation("Sys1", "Some note")
        db.upsert_annotation("Sys1", "")
        assert "Sys1" not in db.get_all_annotations()

    def test_delete_annotation(self, tmp_db):
        db.upsert_annotation("Sys1", "note")
        db.delete_annotation("Sys1")
        assert db.get_all_annotations() == {}


# ---------------------------------------------------------------------------
# Jump bridge CRUD
# ---------------------------------------------------------------------------

class TestJumpBridgeCrud:
    def test_add_and_retrieve(self, tmp_db):
        bridge_id = db.add_jump_bridge("Sys1", "Sys2", label="My JB")
        bridges = db.get_jump_bridges()
        assert len(bridges) == 1
        assert bridges[0]["label"] == "My JB"
        assert bridge_id == bridges[0]["id"]

    def test_alphabetically_normalized(self, tmp_db):
        # "Zeta" comes after "Alpha" → stored as Alpha/Zeta
        db.add_jump_bridge("Zeta", "Alpha")
        bridges = db.get_jump_bridges()
        assert bridges[0]["system_a"] == "Alpha"
        assert bridges[0]["system_b"] == "Zeta"

    def test_duplicate_upserts_label(self, tmp_db):
        db.add_jump_bridge("Sys1", "Sys2", label="old")
        db.add_jump_bridge("Sys1", "Sys2", label="new")
        bridges = db.get_jump_bridges()
        assert len(bridges) == 1
        assert bridges[0]["label"] == "new"

    def test_delete_removes_bridge(self, tmp_db):
        bridge_id = db.add_jump_bridge("Sys1", "Sys2")
        db.delete_jump_bridge(bridge_id)
        assert db.get_jump_bridges() == []


# ---------------------------------------------------------------------------
# Entosis node state machine
# ---------------------------------------------------------------------------

class TestEntosisNodes:
    def test_add_creates_unclaimed_node(self, tmp_db):
        node_id = db.add_entosis_node("Sys1", label="Node A")
        nodes = db.get_entosis_nodes()
        assert len(nodes) == 1
        assert nodes[0]["status"] == "unclaimed"
        assert nodes[0]["label"] == "Node A"
        assert node_id == nodes[0]["id"]

    def test_update_status_and_claimed_by(self, tmp_db):
        node_id = db.add_entosis_node("Sys1")
        db.update_entosis_node(node_id, status="running", claimed_by="Pilot X")
        nodes = db.get_entosis_nodes()
        assert nodes[0]["status"] == "running"
        assert nodes[0]["claimed_by"] == "Pilot X"

    def test_unclaim_clears_claimed_by(self, tmp_db):
        node_id = db.add_entosis_node("Sys1")
        db.update_entosis_node(node_id, claimed_by="Pilot X")
        db.update_entosis_node(node_id, claimed_by="")  # empty string = unclaim
        nodes = db.get_entosis_nodes()
        assert nodes[0]["claimed_by"] is None

    def test_delete_single_node(self, tmp_db):
        node_id = db.add_entosis_node("Sys1")
        db.add_entosis_node("Sys2")
        db.delete_entosis_node(node_id)
        nodes = db.get_entosis_nodes()
        assert len(nodes) == 1
        assert nodes[0]["system_name"] == "Sys2"

    def test_clear_all_nodes(self, tmp_db):
        db.add_entosis_node("Sys1")
        db.add_entosis_node("Sys2")
        db.add_entosis_node("Sys3")
        db.clear_entosis_nodes()
        assert db.get_entosis_nodes() == []


# ---------------------------------------------------------------------------
# Sov change tracking
# ---------------------------------------------------------------------------

class TestSovChanges:
    def test_first_sighting_seeds_state_without_event(self, tmp_db):
        db.record_sov_changes({101: 99001}, {101: "Sys1"})
        # First sighting only seeds sov_state; no change event logged
        changes = db.get_recent_sov_changes()
        assert changes == []

    def test_change_from_seeded_state_logs_event(self, tmp_db):
        db.record_sov_changes({101: 99001}, {101: "Sys1"})
        db.record_sov_changes({101: 99002}, {101: "Sys1"})
        changes = db.get_recent_sov_changes()
        assert len(changes) == 1
        assert changes[0]["old_alliance"] == 99001
        assert changes[0]["new_alliance"] == 99002

    def test_no_change_no_event(self, tmp_db):
        db.record_sov_changes({101: 99001}, {101: "Sys1"})
        db.record_sov_changes({101: 99001}, {101: "Sys1"})  # same alliance
        assert db.get_recent_sov_changes() == []

    def test_get_recent_respects_limit(self, tmp_db):
        # Seed state first
        db.record_sov_changes({101: 0}, {101: "Sys1"})
        # Generate 10 change events by alternating alliances
        for i in range(10):
            db.record_sov_changes({101: (i + 1) * 1000}, {101: "Sys1"})
        changes = db.get_recent_sov_changes(limit=5)
        assert len(changes) == 5

    def test_results_ordered_newest_first(self, tmp_db):
        db.record_sov_changes({101: 0}, {101: "Sys1"})
        db.record_sov_changes({101: 111}, {101: "Sys1"})
        db.record_sov_changes({101: 222}, {101: "Sys1"})
        changes = db.get_recent_sov_changes()
        # Newest event should have new_alliance=222
        assert changes[0]["new_alliance"] == 222
