"""Tests for the security hardening: password lockout, SSO re-verification,
the entosis claim gate, browser security headers, and the compose port binding.

Like test_routes.py, blueprints go onto a bare Flask app so nothing touches ESI.
Unlike it, the rate limiter is ENABLED here — the lockout is the thing under test.
"""

import re
import time
from pathlib import Path

import pytest
from flask import Flask

import config
from routes.auth_sso import auth_sso_bp
from routes.entosis_routes import entosis_bp
from routes.limiter import limiter
from routes.security_headers import apply_security_headers
from routes.static_routes import static_bp
from routes.timer_routes import timer_bp

PASSWORD = "test-password"
ALLIANCE = 99000001
OTHER_ALLIANCE = 99000002
CHARACTER = 2112000001

TIMER = {
    "system_name": "9BGY-6", "structure_type": "IHUB", "owner": "X",
    "event_type": "armor", "timestamp": "2030-01-01T00:00:00Z",
}


@pytest.fixture
def app(tmp_db, monkeypatch):
    monkeypatch.setattr(config, "TIMER_PASSWORD", PASSWORD)
    monkeypatch.setattr(config, "AUTH_ALLOWED_ALLIANCE_IDS", {ALLIANCE})
    monkeypatch.setattr(config, "AUTH_ALLOWED_CHARACTER_IDS", set())
    monkeypatch.setattr(config, "AUTH_RECHECK_SECONDS", 3600)
    monkeypatch.setattr(config, "SSO_ENABLED", False)

    flask_app = Flask(__name__)
    flask_app.secret_key = "test-secret"
    flask_app.config.update(TESTING=True, RATELIMIT_ENABLED=True)
    limiter.init_app(flask_app)
    apply_security_headers(flask_app)
    for bp in (timer_bp, entosis_bp, auth_sso_bp, static_bp):
        flask_app.register_blueprint(bp)
    with flask_app.app_context():
        limiter.reset()
    yield flask_app
    with flask_app.app_context():
        limiter.reset()


@pytest.fixture
def client(app):
    return app.test_client()


def _check(client, password):
    return client.post("/api/auth/check", json={"password": password})


# ---------------------------------------------------------------------------
# TIMER_PASSWORD guessing
# ---------------------------------------------------------------------------

class TestPasswordLockout:
    def test_locks_out_after_ten_failures(self, client):
        for _ in range(10):
            assert _check(client, "wrong").status_code == 401
        assert _check(client, "wrong").status_code == 429

    def test_lockout_refuses_the_correct_password_too(self, client):
        # Otherwise the attacker learns which guess was right from the status.
        for _ in range(10):
            _check(client, "wrong")
        assert _check(client, PASSWORD).status_code == 429
        assert client.post("/api/timers", json=TIMER, headers={"X-Timer-Auth": PASSWORD}).status_code == 429

    def test_failures_are_shared_across_endpoints(self, client):
        # Spreading guesses between the check endpoint and write endpoints
        # must not multiply the allowance.
        for _ in range(5):
            _check(client, "wrong")
        for _ in range(5):
            client.post("/api/timers", json=TIMER, headers={"X-Timer-Auth": "wrong"})
        assert _check(client, PASSWORD).status_code == 429

    def test_correct_password_is_never_counted(self, client):
        for _ in range(30):
            assert _check(client, PASSWORD).status_code == 200

    def test_missing_header_is_not_a_guess(self, client):
        # The frontend sends no/empty header before a password is entered.
        for _ in range(30):
            assert client.post("/api/timers", json=TIMER, headers={"X-Timer-Auth": ""}).status_code == 401
        assert _check(client, PASSWORD).status_code == 200

    def test_lockout_is_per_ip(self, client):
        for _ in range(10):
            _check(client, "wrong")
        other = client.post("/api/auth/check", json={"password": PASSWORD},
                            environ_base={"REMOTE_ADDR": "10.9.9.9"})
        assert other.status_code == 200

    def test_non_ascii_header_is_rejected_not_500(self, client):
        resp = client.post("/api/timers", json=TIMER, headers={"X-Timer-Auth": "pässwörd"})
        assert resp.status_code == 401

    def test_non_string_password_rejected(self, client):
        assert _check(client, ["a"]).status_code == 401
        assert client.post("/api/auth/check", json=["x"]).status_code == 401


# ---------------------------------------------------------------------------
# SSO session re-verification
# ---------------------------------------------------------------------------

def _login(client, *, checked_at, character_id=CHARACTER, alliance_id=ALLIANCE):
    with client.session_transaction() as s:
        s["character_id"] = character_id
        s["character_name"] = "Test Pilot"
        s["alliance_id"] = alliance_id
        s["authorized"] = True
        if checked_at is not None:
            s["auth_checked_at"] = checked_at


class TestSessionRecheck:
    def test_fresh_session_skips_esi(self, client, mocker):
        esi = mocker.patch("routes.auth_sso.esi_get")
        _login(client, checked_at=time.time())
        assert client.post("/api/timers", json=TIMER).status_code == 200
        esi.assert_not_called()

    def test_stale_session_revoked_when_pilot_left_alliance(self, client, mocker):
        mocker.patch("routes.auth_sso.esi_get", return_value={"alliance_id": OTHER_ALLIANCE})
        _login(client, checked_at=time.time() - 7200)
        assert client.post("/api/timers", json=TIMER).status_code == 401
        assert client.get("/api/auth/me").get_json()["authorized"] is False
        with client.session_transaction() as s:
            assert s["authorized"] is False

    def test_stale_session_kept_when_still_a_member(self, client, mocker):
        esi = mocker.patch("routes.auth_sso.esi_get", return_value={"alliance_id": ALLIANCE})
        _login(client, checked_at=time.time() - 7200)
        assert client.post("/api/timers", json=TIMER).status_code == 200
        # Re-stamped, so the next request doesn't hit ESI again.
        assert client.post("/api/timers", json=TIMER).status_code == 200
        assert esi.call_count == 1

    def test_pre_upgrade_session_is_rechecked(self, client, mocker):
        # Cookies issued before this change have no auth_checked_at.
        mocker.patch("routes.auth_sso.esi_get", return_value={"alliance_id": None})
        _login(client, checked_at=None)
        assert client.post("/api/timers", json=TIMER).status_code == 401

    def test_esi_outage_keeps_access_and_retries_soon(self, client, mocker):
        esi = mocker.patch("routes.auth_sso.esi_get", side_effect=RuntimeError("ESI down"))
        _login(client, checked_at=time.time() - 7200)
        assert client.post("/api/timers", json=TIMER).status_code == 200
        with client.session_transaction() as s:
            # Due again well before a full recheck interval.
            assert time.time() - s["auth_checked_at"] > config.AUTH_RECHECK_SECONDS - 600
        esi.side_effect = None
        esi.return_value = {"alliance_id": OTHER_ALLIANCE}
        with client.session_transaction() as s:
            s["auth_checked_at"] = time.time() - 7200
        assert client.post("/api/timers", json=TIMER).status_code == 401

    def test_character_allowlist_needs_no_esi(self, client, mocker, monkeypatch):
        monkeypatch.setattr(config, "AUTH_ALLOWED_CHARACTER_IDS", {CHARACTER})
        esi = mocker.patch("routes.auth_sso.esi_get")
        _login(client, checked_at=time.time() - 7200, alliance_id=None)
        assert client.post("/api/timers", json=TIMER).status_code == 200
        esi.assert_not_called()


# ---------------------------------------------------------------------------
# Entosis claim gate
# ---------------------------------------------------------------------------

def _add_node(client):
    client.post("/api/entosis/nodes", json={"system_name": "9BGY-6"}, headers={"X-Timer-Auth": PASSWORD})


class TestEntosisPatch:
    def test_open_without_sso(self, client):
        _add_node(client)
        assert client.patch("/api/entosis/nodes/1", json={"claimed_by": "Pilot"}).status_code == 200

    def test_anonymous_rejected_with_sso(self, client, monkeypatch):
        _add_node(client)
        monkeypatch.setattr(config, "SSO_ENABLED", True)
        assert client.patch("/api/entosis/nodes/1", json={"status": "running"}).status_code == 401

    def test_any_logged_in_character_may_claim(self, client, monkeypatch):
        # Not just members — blues fly entosis too.
        _add_node(client)
        monkeypatch.setattr(config, "SSO_ENABLED", True)
        with client.session_transaction() as s:
            s["character_id"] = CHARACTER
            s["character_name"] = "Blue Pilot"
            s["authorized"] = False
        assert client.patch("/api/entosis/nodes/1", json={"claimed_by": "x"}).status_code == 200

    def test_rate_limited(self, client):
        _add_node(client)
        codes = [client.patch("/api/entosis/nodes/1", json={"status": "running"}).status_code
                 for _ in range(31)]
        assert codes[:30] == [200] * 30
        assert codes[30] == 429


# ---------------------------------------------------------------------------
# Browser security headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    @pytest.mark.parametrize("path", ["/", "/api/timers", "/api/nope"])
    def test_headers_on_every_response(self, client, path):
        h = client.get(path).headers
        assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
        assert "script-src 'self'" in h["Content-Security-Policy"]
        assert h["X-Frame-Options"] == "DENY"
        assert h["X-Content-Type-Options"] == "nosniff"
        assert h["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_csp_allows_only_what_the_frontend_loads(self, client):
        csp = client.get("/").headers["Content-Security-Policy"]
        assert "unsafe-eval" not in csp
        assert re.search(r"script-src 'self'(;|$)", csp)
        assert "https://fonts.googleapis.com" in csp
        assert "https://fonts.gstatic.com" in csp
        assert "https://images.evetech.net" in csp

    def test_hsts_only_over_https(self, client):
        assert "Strict-Transport-Security" not in client.get("/").headers
        assert "max-age=" in client.get("/", base_url="https://localhost").headers["Strict-Transport-Security"]


# ---------------------------------------------------------------------------
# Deployment config
# ---------------------------------------------------------------------------

def test_compose_publishes_app_port_on_loopback_only():
    # Docker bypasses ufw; a port published on 0.0.0.0 lets clients skip nginx
    # and forge X-Forwarded-For past every per-IP limit.
    compose = (Path(__file__).resolve().parent.parent / "docker-compose.yml").read_text()
    ports = re.findall(r'^\s*-\s*"([^"]*:\d+)"\s*$', compose, re.MULTILINE)
    assert ports, "no port mappings found in docker-compose.yml"
    for mapping in ports:
        assert mapping.startswith("127.0.0.1:"), mapping
