from flask import Blueprint, jsonify
from mock.mock_data import MOCK_NEIGHBOR_INTEL

mock_intel_bp = Blueprint("mock_intel", __name__)


@mock_intel_bp.route("/api/intel/neighbors")
def api_neighbor_intel():
    return jsonify(MOCK_NEIGHBOR_INTEL)
