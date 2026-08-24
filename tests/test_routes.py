"""Route-level tests for the live blueprints.

These exercise request validation, auth gating, and the SPA catch-all without
touching the network: the blueprints are registered onto a bare Flask app here
rather than importing app.py, which would call resolve_all_systems() and walk
the whole region via ESI at import time.
"""

from datetime import UTC, datetime, timedelta

import pytest
from flask import Flask

import config
from routes.ai_routes import ai_bp
from routes.annotation_routes import annotation_bp
from routes.entosis_routes import entosis_bp
from routes.jb_routes import jb_bp
from routes.limiter import limiter
from routes.share_routes import MAX_PAYLOAD_BYTES, share_bp
from routes.static_routes import static_bp
from routes.timer_routes import timer_bp

AUTH = {"X-Timer-Auth": "test-password"}


def _future_ts(hours=6):
    """ISO timestamp N hours ahead — get_active_timers() drops anything older than now-24h."""
    return (datetime.now(UTC) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def app(tmp_db, monkeypatch):
    """Flask app with the write-gated blueprints, backed by an isolated DB."""
    monkeypatch.setattr(config, "TIMER_PASSWORD", "test-password")
    # timer_routes imports TIMER_PASSWORD by value at module load.
    import routes.timer_routes as timer_routes
    monkeypatch.setattr(timer_routes, "TIMER_PASSWORD", "test-password")

    flask_app = Flask(__name__)
    flask_app.secret_key = "test-secret"
    flask_app.config.update(TESTING=True, RATELIMIT_ENABLED=False)
    limiter.init_app(flask_app)
    for bp in (timer_bp, annotation_bp, jb_bp, entosis_bp, ai_bp, static_bp, share_bp):
        flask_app.register_blueprint(bp)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Write auth gating
# ---------------------------------------------------------------------------

class TestWriteAuth:
    @pytest.mark.parametrize(
        "method,path,payload",
        [
            ("post", "/api/timers", {}),
            ("delete", "/api/timers/1", None),
            ("post", "/api/annotations", {}),
            ("post", "/api/jumpbridges", {}),
            ("delete", "/api/jumpbridges/1", None),
            ("post", "/api/entosis/nodes", {}),
            ("delete", "/api/entosis/nodes/1", None),
            ("delete", "/api/entosis/nodes", None),
            ("post", "/api/share", {"kind": "dscan", "payload": {}}),
        ],
    )
    def test_write_endpoints_reject_anonymous(self, client, method, path, payload):
        resp = getattr(client, method)(path, json=payload)
        assert resp.status_code == 401, f"{method.upper()} {path} was not gated"

    def test_bad_password_rejected(self, client):
        resp = client.post("/api/timers", json={}, headers={"X-Timer-Auth": "wrong"})
        assert resp.status_code == 401

    def test_auth_check_accepts_correct_password(self, client):
        assert client.post("/api/auth/check", json={"password": "test-password"}).status_code == 200

    def test_auth_check_rejects_wrong_password(self, client):
        assert client.post("/api/auth/check", json={"password": "nope"}).status_code == 401

    def test_reads_are_open(self, client):
        for path in ("/api/timers", "/api/annotations", "/api/jumpbridges", "/api/entosis/nodes"):
            assert client.get(path).status_code == 200, path


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------

class TestTimerValidation:
    def test_missing_fields_rejected(self, client):
        assert client.post("/api/timers", json={"system_name": "9BGY-6"}, headers=AUTH).status_code == 400

    def test_complete_timer_accepted(self, client):
        resp = client.post("/api/timers", json={
            "system_name": "9BGY-6", "structure_type": "IHUB", "owner": "LAWN",
            "event_type": "armor", "timestamp": _future_ts(),
        }, headers=AUTH)
        assert resp.status_code == 200
        assert len(client.get("/api/timers").get_json()) == 1

    def test_non_string_notes_rejected(self, client):
        resp = client.post("/api/timers", json={
            "system_name": "X", "structure_type": "IHUB", "owner": "L",
            "event_type": "armor", "timestamp": _future_ts(), "notes": 42,
        }, headers=AUTH)
        assert resp.status_code == 400


class TestEntosisValidation:
    def test_empty_system_name_rejected(self, client):
        assert client.post("/api/entosis/nodes", json={"system_name": "  "}, headers=AUTH).status_code == 400

    def test_invalid_status_rejected(self, client):
        client.post("/api/entosis/nodes", json={"system_name": "9BGY-6"}, headers=AUTH)
        assert client.patch("/api/entosis/nodes/1", json={"status": "bogus"}).status_code == 400

    def test_valid_status_accepted(self, client):
        client.post("/api/entosis/nodes", json={"system_name": "9BGY-6"}, headers=AUTH)
        assert client.patch("/api/entosis/nodes/1", json={"status": "running"}).status_code == 200

    def test_bool_campaign_id_rejected(self, client):
        """bool is an int subclass — the route must reject it explicitly."""
        resp = client.post("/api/entosis/nodes",
                           json={"system_name": "9BGY-6", "campaign_id": True}, headers=AUTH)
        assert resp.status_code == 400

    def test_claim_is_open_to_fleet_members(self, client):
        """PATCH is deliberately unauthenticated so any pilot can claim a node."""
        client.post("/api/entosis/nodes", json={"system_name": "9BGY-6"}, headers=AUTH)
        assert client.patch("/api/entosis/nodes/1", json={"claimed_by": "Pilot"}).status_code == 200


class TestJumpBridgeValidation:
    def test_identical_endpoints_rejected(self, client):
        resp = client.post("/api/jumpbridges", json={"system_a": "A", "system_b": "A"}, headers=AUTH)
        assert resp.status_code == 400

    def test_missing_endpoint_rejected(self, client):
        assert client.post("/api/jumpbridges", json={"system_a": "A"}, headers=AUTH).status_code == 400

    def test_valid_pair_accepted(self, client):
        resp = client.post("/api/jumpbridges", json={"system_a": "9BGY-6", "system_b": "LW-YEW"}, headers=AUTH)
        assert resp.status_code == 200
        assert len(client.get("/api/jumpbridges").get_json()) == 1


class TestAnnotationValidation:
    def test_missing_system_name_rejected(self, client):
        assert client.post("/api/annotations", json={"note": "hi"}, headers=AUTH).status_code == 400

    def test_non_string_note_rejected(self, client):
        resp = client.post("/api/annotations", json={"system_name": "X", "note": {"a": 1}}, headers=AUTH)
        assert resp.status_code == 400

    def test_note_roundtrips(self, client):
        client.post("/api/annotations", json={"system_name": "9BGY-6", "note": "cloaky camper"}, headers=AUTH)
        assert client.get("/api/annotations").get_json()["9BGY-6"]["note"] == "cloaky camper"


# ---------------------------------------------------------------------------
# AI endpoint
# ---------------------------------------------------------------------------

class TestAiRoute:
    def test_unconfigured_returns_501(self, client, mocker):
        mocker.patch("routes.ai_routes.get_client", return_value=None)
        resp = client.post("/api/ai/threat_summary", json={"type": "dscan", "data": "x"}, headers=AUTH)
        assert resp.status_code == 501

    def test_requires_auth(self, client):
        assert client.post("/api/ai/threat_summary", json={"type": "dscan", "data": "x"}).status_code == 401

    def test_unknown_scan_type_rejected(self, client, mocker):
        mocker.patch("routes.ai_routes.get_client", return_value=object())
        resp = client.post("/api/ai/threat_summary", json={"type": "bogus", "data": "x"}, headers=AUTH)
        assert resp.status_code == 400

    def test_non_string_data_rejected(self, client, mocker):
        mocker.patch("routes.ai_routes.get_client", return_value=object())
        resp = client.post("/api/ai/threat_summary", json={"type": "dscan", "data": {"a": 1}}, headers=AUTH)
        assert resp.status_code == 400

    def test_oversized_input_is_truncated_not_rejected(self, client, mocker):
        """A huge paste should still work — bounded, not refused."""
        import routes.ai_routes as ai_routes

        captured = {}

        class _FakeModels:
            def generate_content(self, model, contents, config):
                captured["prompt"] = contents
                return type("R", (), {"text": "summary"})()

        mocker.patch.object(ai_routes, "get_client",
                            return_value=type("C", (), {"models": _FakeModels()})())
        resp = client.post("/api/ai/threat_summary",
                           json={"type": "dscan", "data": "A" * 50000}, headers=AUTH)
        assert resp.status_code == 200
        # Count the pasted run itself rather than every "A" in the prompt — the
        # template's own prose contains some.
        limit = ai_routes._MAX_INPUT_CHARS
        assert "A" * limit in captured["prompt"]
        assert "A" * (limit + 1) not in captured["prompt"]


# ---------------------------------------------------------------------------
# SPA catch-all
# ---------------------------------------------------------------------------

class TestStaticRoutes:
    def test_unknown_api_path_404s(self, client):
        """The catch-all must not swallow unmatched /api/ paths into the SPA."""
        resp = client.get("/api/does-not-exist")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "Not Found"

    def test_missing_build_reports_503(self, client, mocker):
        """No Vite build must fail loudly, not silently serve something stale."""
        mocker.patch("routes.static_routes.os.path.exists", return_value=False)
        resp = client.get("/")
        assert resp.status_code == 503
        assert b"Frontend build missing" in resp.data


# ---------------------------------------------------------------------------
# Shared parser snapshots
# ---------------------------------------------------------------------------

def _make_share(client, **overrides):
    body = {"kind": "dscan", "payload": {"result": {"ships": 4}}}
    body.update(overrides)
    return client.post("/api/share", json=body, headers=AUTH)


class TestShareRoutes:
    def test_create_returns_token_and_url(self, client):
        resp = _make_share(client)
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["url"] == f"/s/{body['token']}"
        assert body["expires_at"]

    def test_round_trip(self, client):
        token = _make_share(client, title="Gate camp").get_json()["token"]
        resp = client.get(f"/api/share/{token}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["kind"] == "dscan"
        assert body["title"] == "Gate camp"
        # payload comes back as an object, not the stored JSON string
        assert body["payload"]["result"]["ships"] == 4

    def test_unknown_token_404s(self, client):
        assert client.get("/api/share/not-a-real-token").status_code == 404

    def test_unknown_kind_rejected(self, client):
        assert _make_share(client, kind="intel").status_code == 400

    def test_unknown_visibility_rejected(self, client):
        assert _make_share(client, visibility="everyone").status_code == 400

    def test_non_object_payload_rejected(self, client):
        assert _make_share(client, payload=["not", "a", "dict"]).status_code == 400
        assert _make_share(client, payload="a string").status_code == 400

    def test_oversized_payload_rejected_not_truncated(self, client):
        # Deliberately the opposite of the AI route, which truncates: half a
        # JSON document is not a smaller report, it is a corrupt one.
        huge = {"result": {"blob": "A" * (MAX_PAYLOAD_BYTES + 1)}}
        assert _make_share(client, payload=huge).status_code == 413

    def test_title_is_truncated(self, client):
        token = _make_share(client, title="T" * 500).get_json()["token"]
        assert len(client.get(f"/api/share/{token}").get_json()["title"]) == 120

    def test_alliance_only_share_is_gated_on_read(self, client):
        token = _make_share(client, visibility="alliance").get_json()["token"]
        resp = client.get(f"/api/share/{token}")
        assert resp.status_code == 403
        # Distinguishable from "not found" so the page can offer a login prompt.
        assert resp.get_json()["error"] == "alliance only"

    def test_alliance_only_share_readable_when_authorized(self, client):
        token = _make_share(client, visibility="alliance").get_json()["token"]
        assert client.get(f"/api/share/{token}", headers=AUTH).status_code == 200

    def test_link_share_is_public(self, client):
        token = _make_share(client).get_json()["token"]
        assert client.get(f"/api/share/{token}").status_code == 200


class TestRobotsTxt:
    def test_disallows_share_paths(self, client):
        resp = client.get("/robots.txt")
        assert resp.status_code == 200
        assert "Disallow: /s/" in resp.get_data(as_text=True)


class TestSharePathBucketing:
    """A share token must never be written into traffic_hourly.path.

    It is the secret that guards the snapshot, and one row per share would give
    the path column the unbounded cardinality the "/other" bucket exists to
    prevent.
    """

    def test_share_pages_collapse_to_slash_s(self, app):
        from routes.analytics_routes import classify_request
        with app.test_request_context("/s/aVeryLongOpaqueShareToken"):
            assert classify_request() == ("page", "/s")

    def test_api_share_reads_collapse_to_the_url_rule(self, app):
        from routes.analytics_routes import classify_request
        with app.test_request_context("/api/share/aVeryLongOpaqueShareToken"):
            kind, path = classify_request()
        assert kind == "api"
        assert "aVeryLongOpaqueShareToken" not in path

    def test_other_unknown_pages_still_bucket_to_other(self, app):
        from routes.analytics_routes import classify_request
        with app.test_request_context("/wp-login.php"):
            assert classify_request() == ("page", "/other")
