"""Tests for traffic analytics: request classification, rollup writes, gating.

The recorder is an after_app_request hook, so these register the blueprint onto
a bare Flask app with a couple of stand-in routes and drive it with the test
client — no ESI, no real SPA build.
"""

import pytest
from flask import Flask

import config
import db
from routes.analytics_routes import analytics_bp
from routes.analytics_routes import flush as analytics_flush
from routes.limiter import limiter

AUTH = {"X-Analytics-Auth": "analytics-password"}
FLEET_AUTH = {"X-Timer-Auth": "fleet-password"}


@pytest.fixture
def app(tmp_db, monkeypatch):
    # The fleet-wide write credential is set here precisely so the tests can
    # prove it does NOT open the analytics endpoints.
    monkeypatch.setattr(config, "TIMER_PASSWORD", "fleet-password")
    monkeypatch.setattr(config, "ANALYTICS_PASSWORD", "analytics-password")
    monkeypatch.setattr(config, "ANALYTICS_ALLOWED_CHARACTER_IDS", {90000001})
    monkeypatch.setattr(config, "ANALYTICS_AUTH_CONFIGURED", True)

    # Module-level buffers persist across tests; start each one empty and with
    # the flush interval elapsed so an explicit flush always writes.
    import routes.analytics_routes as analytics_routes
    monkeypatch.setattr(analytics_routes, "_hourly", {})
    monkeypatch.setattr(analytics_routes, "_visitors", {})
    monkeypatch.setattr(analytics_routes, "_last_flush", 0.0)
    monkeypatch.setattr(analytics_routes, "ANALYTICS_ENABLED", True)

    flask_app = Flask(__name__)
    flask_app.secret_key = "test-secret"
    flask_app.config.update(TESTING=True, RATELIMIT_ENABLED=False)
    limiter.init_app(flask_app)
    flask_app.register_blueprint(analytics_bp)

    @flask_app.route("/")
    def index():
        return "spa"

    @flask_app.route("/entosis")
    def entosis():
        return "spa"

    @flask_app.route("/wp-login.php")
    def junk():
        return "spa"

    @flask_app.route("/api/zkill/<int:system_id>")
    def zkill(system_id):
        return {"system_id": system_id}

    @flask_app.route("/assets/app.js")
    def asset():
        return "js"

    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def summary(client, days=30):
    return client.get(f"/api/analytics/summary?days={days}", headers=AUTH).get_json()


class TestGating:
    def test_summary_requires_auth(self, client):
        assert client.get("/api/analytics/summary").status_code == 401

    def test_summary_accepts_analytics_password(self, client):
        assert client.get("/api/analytics/summary", headers=AUTH).status_code == 200

    def test_fleet_write_password_is_not_enough(self, client):
        """TIMER_PASSWORD is shared with the whole fleet — it must not unlock stats."""
        assert client.get("/api/analytics/summary", headers=FLEET_AUTH).status_code == 401

    def test_wrong_analytics_password_rejected(self, client):
        resp = client.get("/api/analytics/summary", headers={"X-Analytics-Auth": "guess"})
        assert resp.status_code == 401

    def test_allowlisted_character_is_admitted(self, client):
        with client.session_transaction() as sess:
            sess["character_id"] = 90000001
            sess["character_name"] = "Ops Officer"
        assert client.get("/api/analytics/summary").status_code == 200

    def test_sso_session_alone_is_not_enough(self, client):
        """An ordinary alliance member with write access still can't read stats."""
        with client.session_transaction() as sess:
            sess["character_id"] = 90000002
            sess["character_name"] = "Line Member"
            sess["authorized"] = True
        assert client.get("/api/analytics/summary").status_code == 401

    def test_unconfigured_denies_everyone(self, client, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_AUTH_CONFIGURED", False)
        resp = client.get("/api/analytics/summary", headers=AUTH)
        assert resp.status_code == 503
        assert "detail" in resp.get_json()

    def test_auth_endpoint_reports_state_without_leaking_data(self, client):
        body = client.get("/api/analytics/auth").get_json()
        assert body == {
            "configured": True, "authorized": False,
            "sso": False, "password": True, "character_name": None,
        }

    def test_auth_endpoint_confirms_a_valid_credential(self, client):
        body = client.get("/api/analytics/auth", headers=AUTH).get_json()
        assert body["authorized"] is True


class TestRecording:
    def test_page_load_counts_as_visitor(self, client):
        client.get("/")
        data = summary(client)
        assert data["totals"]["unique_visitors"] == 1
        assert data["totals"]["page_views"] == 1
        assert {"path": "/", "views": 1} in data["top_pages"]

    def test_api_calls_are_separated_from_page_loads(self, client):
        client.get("/")
        client.get("/api/zkill/30002826")
        data = summary(client)
        assert data["totals"]["page_views"] == 1
        # The summary request itself is an API call, so only check the parameterised route.
        assert data["totals"]["api_calls"] >= 1
        assert any(r["path"] == "/api/zkill/<int:system_id>" for r in data["top_api"])

    def test_parameterised_api_paths_collapse_to_one_row(self, client):
        for sid in (30002826, 30002827, 30002828):
            client.get(f"/api/zkill/{sid}")
        rows = [r for r in summary(client)["top_api"] if r["path"] == "/api/zkill/<int:system_id>"]
        assert len(rows) == 1 and rows[0]["views"] == 3

    def test_unknown_paths_bucket_into_other(self, client):
        client.get("/wp-login.php")
        paths = {r["path"] for r in summary(client)["top_pages"]}
        assert paths == {"/other"}

    def test_missing_paths_are_not_counted(self, client):
        client.get("/no/such/route")
        data = summary(client)
        assert data["totals"]["page_views"] == 0
        assert data["top_pages"] == []

    def test_assets_are_not_counted(self, client):
        client.get("/assets/app.js")
        assert summary(client)["totals"]["page_views"] == 0

    def test_bots_are_counted_but_are_not_visitors(self, client):
        client.get("/", headers={"User-Agent": "Googlebot/2.1"})
        data = summary(client)
        assert data["totals"]["bot_hits"] == 1
        assert data["totals"]["unique_visitors"] == 0
        assert data["totals"]["page_views"] == 0

    def test_distinct_clients_count_separately(self, client):
        client.get("/", headers={"X-Forwarded-For": "10.0.0.1", "User-Agent": "Firefox"})
        client.get("/", headers={"X-Forwarded-For": "10.0.0.2", "User-Agent": "Firefox"})
        # Same client twice — still one visitor.
        client.get("/", headers={"X-Forwarded-For": "10.0.0.1", "User-Agent": "Firefox"})
        assert summary(client)["totals"]["unique_visitors"] == 2

    def test_forwarded_clients_are_distinguished_without_proxy_trust(self, client, monkeypatch):
        """Untrusted mode reads X-Forwarded-For so visitors don't all collapse to nginx."""
        monkeypatch.setattr(config, "TRUSTED_PROXY_HOPS", 0)
        client.get("/", headers={"X-Forwarded-For": "203.0.113.7", "User-Agent": "Firefox"})
        client.get("/", headers={"X-Forwarded-For": "203.0.113.8", "User-Agent": "Firefox"})
        assert summary(client)["totals"]["unique_visitors"] == 2

    def test_proxy_trust_makes_remote_addr_authoritative(self, client, monkeypatch):
        """With hops trusted, ProxyFix owns remote_addr and a spoofed header can't split identity."""
        monkeypatch.setattr(config, "TRUSTED_PROXY_HOPS", 1)
        # No ProxyFix on this bare test app, so remote_addr stays constant —
        # which is exactly what proves the forwarded header is being ignored.
        client.get("/", headers={"X-Forwarded-For": "203.0.113.7", "User-Agent": "Firefox"})
        client.get("/", headers={"X-Forwarded-For": "203.0.113.8", "User-Agent": "Firefox"})
        assert summary(client)["totals"]["unique_visitors"] == 1

    def test_logged_in_character_is_attributed(self, client):
        with client.session_transaction() as sess:
            sess["character_name"] = "Kaelen Voss"
        client.get("/")
        pilots = summary(client)["pilots"]
        assert [p["character_name"] for p in pilots] == ["Kaelen Voss"]

    def test_disabled_flag_records_nothing(self, client, monkeypatch):
        import routes.analytics_routes as analytics_routes
        monkeypatch.setattr(analytics_routes, "ANALYTICS_ENABLED", False)
        client.get("/")
        assert summary(client)["totals"]["page_views"] == 0

    def test_recording_failure_does_not_break_the_request(self, client, monkeypatch):
        import routes.analytics_routes as analytics_routes
        monkeypatch.setattr(analytics_routes, "_buffer",
                            lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        assert client.get("/").status_code == 200


class TestRollups:
    def test_counts_accumulate_across_flushes(self, tmp_db):
        db.record_traffic(
            {("2026-08-01T12", "page", "/"): 3},
            {("2026-08-01", "abc"): {"page_views": 3, "api_calls": 0,
                                     "first_seen": "2026-08-01T12:00:00Z",
                                     "last_seen": "2026-08-01T12:05:00Z"}},
        )
        db.record_traffic(
            {("2026-08-01T12", "page", "/"): 2},
            {("2026-08-01", "abc"): {"page_views": 2, "api_calls": 7,
                                     "character_name": "Mira Tenshun",
                                     "first_seen": "2026-08-01T12:10:00Z",
                                     "last_seen": "2026-08-01T12:20:00Z"}},
        )
        conn = db.get_connection()
        views = conn.execute("SELECT views FROM traffic_hourly").fetchone()["views"]
        row = conn.execute("SELECT * FROM traffic_visitors").fetchone()
        conn.close()
        assert views == 5
        assert (row["page_views"], row["api_calls"]) == (5, 7)
        assert row["character_name"] == "Mira Tenshun"
        assert row["last_seen"] == "2026-08-01T12:20:00Z"

    def test_character_name_is_not_cleared_by_a_later_anonymous_hit(self, tmp_db):
        base = {"page_views": 1, "api_calls": 0,
                "first_seen": "2026-08-01T12:00:00Z", "last_seen": "2026-08-01T12:00:00Z"}
        db.record_traffic({}, {("2026-08-01", "abc"): {**base, "character_name": "Bhaal Ruk"}})
        db.record_traffic({}, {("2026-08-01", "abc"): dict(base)})
        conn = db.get_connection()
        name = conn.execute("SELECT character_name FROM traffic_visitors").fetchone()[0]
        conn.close()
        assert name == "Bhaal Ruk"

    def test_prune_drops_old_rows_only(self, tmp_db):
        db.record_traffic(
            {("2020-01-01T00", "page", "/"): 1},
            {("2020-01-01", "old"): {"page_views": 1, "api_calls": 0,
                                     "first_seen": "2020-01-01T00:00:00Z",
                                     "last_seen": "2020-01-01T00:00:00Z"}},
        )
        from datetime import UTC, datetime
        today = datetime.now(UTC)
        db.record_traffic(
            {(today.strftime("%Y-%m-%dT%H"), "page", "/"): 1},
            {(today.strftime("%Y-%m-%d"), "new"): {"page_views": 1, "api_calls": 0,
                                                   "first_seen": "x", "last_seen": "x"}},
        )
        db.prune_traffic(days=30)
        conn = db.get_connection()
        hashes = {r[0] for r in conn.execute("SELECT visitor_hash FROM traffic_visitors")}
        hours = {r[0] for r in conn.execute("SELECT hour FROM traffic_hourly")}
        conn.close()
        assert hashes == {"new"}
        assert all(not h.startswith("2020") for h in hours)


class TestSummaryShape:
    def test_hourly_covers_every_hour(self, client):
        client.get("/")
        hourly = summary(client)["hourly"]
        assert [h["hour"] for h in hourly] == list(range(24))
        assert sum(h["views"] for h in hourly) == 1

    def test_returning_visitors_counts_multi_day_hashes(self, tmp_db):
        base = {"page_views": 1, "api_calls": 0, "first_seen": "x", "last_seen": "x"}
        from datetime import UTC, datetime, timedelta
        now = datetime.now(UTC)
        for i in range(3):
            day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            db.record_traffic({}, {(day, "regular"): dict(base)})
        db.record_traffic({}, {(now.strftime("%Y-%m-%d"), "oneoff"): dict(base)})

        data = db.get_traffic_summary(days=30)
        assert data["totals"]["unique_visitors"] == 2
        assert data["totals"]["returning_visitors"] == 1
        assert {"days_seen": 3, "visitors": 1} in data["visitor_frequency"]

    def test_days_window_is_clamped(self, client):
        assert client.get("/api/analytics/summary?days=99999", headers=AUTH).get_json()["days"] == 365
        assert client.get("/api/analytics/summary?days=0", headers=AUTH).get_json()["days"] == 1
        assert client.get("/api/analytics/summary?days=abc", headers=AUTH).get_json()["days"] == 30


def test_flush_is_a_noop_when_nothing_buffered(app):
    """Called from the poller every cycle — must not touch the DB when idle."""
    with app.test_request_context("/"):
        analytics_flush(force=True)
