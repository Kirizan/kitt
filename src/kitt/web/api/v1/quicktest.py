"""Quick test REST API endpoints."""

import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from kitt.web.auth import require_auth

bp = Blueprint("api_quicktest", __name__, url_prefix="/api/v1/quicktest")


@bp.route("/", methods=["POST"])
@require_auth
def launch():
    """Launch a quick test."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    required = ["agent_id", "model_path", "engine_name"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"'{field}' is required"}), 400

    from kitt.web.app import get_services

    services = get_services()
    agent_mgr = services["agent_manager"]

    agent = agent_mgr.get_agent(data["agent_id"])
    if agent is None:
        return jsonify({"error": "Agent not found"}), 404

    # Create quick test record
    test_id = uuid.uuid4().hex[:16]
    now = datetime.now().isoformat()

    conn = services["db_conn"]
    conn.execute(
        """INSERT INTO quick_tests
           (id, agent_id, model_path, engine_name, benchmark_name, suite_name,
            status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'queued', ?)""",
        (
            test_id,
            data["agent_id"],
            data["model_path"],
            data["engine_name"],
            data.get("benchmark_name", "throughput"),
            data.get("suite_name", "quick"),
            now,
        ),
    )
    conn.commit()

    return jsonify({"id": test_id, "status": "queued"}), 202


@bp.route("/<test_id>", methods=["GET"])
def status(test_id):
    """Get quick test status."""
    from kitt.web.app import get_services

    conn = get_services()["db_conn"]
    row = conn.execute("SELECT * FROM quick_tests WHERE id = ?", (test_id,)).fetchone()

    if row is None:
        return jsonify({"error": "Quick test not found"}), 404

    return jsonify(dict(row))
