import os
from flask import Blueprint, send_from_directory

static_bp = Blueprint("static_files", __name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIST_DIR = os.path.join(_ROOT, "static", "dist")
_STATIC_DIR = os.path.join(_ROOT, "static")


@static_bp.route("/")
def index():
    """Serve the React SPA — Vite build (static/dist/) if present, else legacy."""
    dist_index = os.path.join(_DIST_DIR, "index.html")
    if os.path.exists(dist_index):
        return send_from_directory(_DIST_DIR, "index.html")
    return send_from_directory(_STATIC_DIR, "index.html")


@static_bp.route("/assets/<path:filename>")
def assets(filename):
    """Serve Vite's hashed JS/CSS chunks from static/dist/assets/."""
    return send_from_directory(os.path.join(_DIST_DIR, "assets"), filename)
