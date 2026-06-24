import pytest
import db


@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    """Isolated SQLite DB for each test.

    Patches DB_PATH to a temp file, resets the active DEPLOYMENT_ID to a
    test-only string, and clears the in-memory dedup caches so tests don't
    bleed into each other.
    """
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(db, "DB_PATH", db_file)
    monkeypatch.setattr(db, "DEPLOYMENT_ID", "test_deploy")
    # Reset in-memory dedup trackers; these are module-level dicts that persist
    # across function calls, so tests that call snapshot_* functions would
    # otherwise interfere with each other.
    monkeypatch.setattr(db, "_last_adm_snapshot", {})
    monkeypatch.setattr(db, "_last_activity_snapshot", {})
    db.init()
    yield db_file
