from flask import Blueprint, jsonify
from mock.mock_data import build_enriched_sovereignty, get_mock_campaigns

mock_sov_bp = Blueprint("mock_sov", __name__)


@mock_sov_bp.route("/api/sovereignty")
def api_sovereignty():
    return jsonify(build_enriched_sovereignty())


@mock_sov_bp.route("/api/campaigns")
def api_campaigns():
    return jsonify(get_mock_campaigns())
