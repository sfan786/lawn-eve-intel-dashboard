import logging
import os

from flask import Blueprint, send_from_directory

log = logging.getLogger(__name__)

static_bp = Blueprint("static_files", __name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIST_DIR = os.path.join(_ROOT, "static", "dist")

_BUILD_MISSING_HTML = """<!doctype html>
<title>Frontend build missing</title>
<body style="background:#060a0f;color:#ff3355;font:14px monospace;padding:2rem">
<h1>Frontend build missing</h1>
<p>No Vite build found at <code>static/dist/index.html</code>.</p>
<p>Build it with:</p>
<pre style="color:#00d4ff">cd frontend &amp;&amp; npm install &amp;&amp; npm run build</pre>
</body>"""


def _serve_spa():
    """Serve the Vite SPA, or a loud error if it was never built.

    There used to be a fallback to a legacy CDN-React static/index.html here.
    It meant a failed or skipped frontend build silently served a stale UI
    instead of surfacing the problem, so the fallback is gone.
    """
    if os.path.exists(os.path.join(_DIST_DIR, "index.html")):
        return send_from_directory(_DIST_DIR, "index.html")
    log.error("No frontend build at %s — run `npm run build` in frontend/", _DIST_DIR)
    return _BUILD_MISSING_HTML, 503


@static_bp.route("/")
def index():
    """Serve the React SPA from the Vite build (static/dist/)."""
    return _serve_spa()


@static_bp.route("/assets/<path:filename>")
def assets(filename):
    """Serve Vite's hashed JS/CSS chunks from static/dist/assets/."""
    return send_from_directory(os.path.join(_DIST_DIR, "assets"), filename)


@static_bp.route("/<path:path>")
def spa_fallback(path):
    """Catch-all: serve the SPA for client-side routes (e.g. /entosis). Returns 404 for unknown API paths."""
    if path.startswith("api/"):
        return {"error": "Not Found"}, 404
    return _serve_spa()
