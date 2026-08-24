"""
EVE Intel Dashboard - Flask Backend

Active deployment is selected by the DEPLOYMENT env var (default: lawn_perrigen).
See deployments/ for the available deployment modules.

Usage:
    ./run_dev.fish
    OR
    source .venv/bin/activate.fish
    python app.py
    Open http://localhost:5000
"""

import logging
import os

from flask import Flask

import config
import db
from config import ALLIANCE, FLASK_DEBUG, FLASK_HOST, FLASK_PORT, REGION
from routes.activity_routes import activity_bp
from routes.ai_routes import ai_bp
from routes.analytics_routes import analytics_bp
from routes.annotation_routes import annotation_bp
from routes.auth_sso import auth_sso_bp
from routes.config_routes import config_bp
from routes.entosis_routes import entosis_bp
from routes.history_routes import history_bp
from routes.hostile_routes import hostile_bp
from routes.intel_routes import intel_bp
from routes.jb_routes import jb_bp
from routes.limiter import limiter
from routes.proxy import apply_proxy_fix, warn_on_untrusted_proxy
from routes.share_routes import share_bp
from routes.sov_routes import sov_bp
from routes.static_routes import static_bp
from routes.system_state import resolve_all_systems, state
from routes.timer_routes import timer_bp
from routes.war_routes import war_bp
from routes.zkill_routes import zkill_bp


def configure_logging():
    """Send app logs to stdout with levels and timestamps.

    Under gunicorn this is inherited by the workers; the gunicorn access/error
    logs are configured separately in gunicorn.conf.py.
    """
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def create_app():
    app = Flask(__name__)
    app.secret_key = config.FLASK_SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=not FLASK_DEBUG,
    )
    # Must wrap wsgi_app before the limiter reads remote_addr per request.
    apply_proxy_fix(app)
    warn_on_untrusted_proxy(app)
    limiter.init_app(app)
    for bp in [config_bp, sov_bp, activity_bp, zkill_bp, war_bp, history_bp, intel_bp, hostile_bp, timer_bp, annotation_bp, jb_bp, entosis_bp, auth_sso_bp, static_bp, ai_bp, analytics_bp, share_bp]:
        app.register_blueprint(bp)
    return app


configure_logging()

# Load all systems at module import time (works with gunicorn and Flask dev server).
# In debug mode, Werkzeug's reloader will cause this to run twice — but with
# parallel fetches the second load hits the ESI cache and is near-instant.
# Under gunicorn this runs once in the master (preload_app) and the warm ESI
# cache is inherited by every worker through fork.
resolve_all_systems(state)
db.init()
app = create_app()

if __name__ == "__main__":
    # Threads don't survive fork, so under gunicorn the poller starts from the
    # post_fork hook instead (gunicorn.conf.py). Here we own the process.
    from routes.poller import start_poller
    from routes.war_poller import start_war_poller

    log = logging.getLogger(__name__)
    primary_names = [c["name"] for c in state.constellation_data.values() if c.get("is_primary")]
    log.info("Dashboard starting at http://localhost:%s", FLASK_PORT)
    log.info("%s Intel Dashboard - %s", ALLIANCE["display_name"], REGION["name"])
    log.info("Primary constellations: %s", ", ".join(primary_names))
    log.info("Monitoring %d systems total", len(state.all_monitored_ids))

    # Werkzeug's reloader runs this module twice; only the child holds the server.
    if not FLASK_DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_poller()
        # No-op unless a war module is configured.
        start_war_poller()

    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
