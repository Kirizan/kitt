"""Quick test REST API endpoints."""

import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from kitt.web.auth import require_auth
from kitt.web.services.event_bus import event_bus

bp = Blueprint("api_quicktest", __name__, url_prefix="/api/v1/quicktest")


@bp.route("/models", methods=["GET"])
def models():
    """List available models from Devon manifest."""
    from kitt.web.app import get_services

    local_model_service = get_services()["local_model_service"]
    return jsonify(local_model_service.read_manifest())


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

    # Create quick test record with command_id for heartbeat dispatch
    test_id = uuid.uuid4().hex[:16]
    command_id = uuid.uuid4().hex[:16]
    now = datetime.now().isoformat()

    conn = services["db_conn"]
    conn.execute(
        """INSERT INTO quick_tests
           (id, agent_id, model_path, engine_name, benchmark_name, suite_name,
            status, command_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?)""",
        (
            test_id,
            data["agent_id"],
            data["model_path"],
            data["engine_name"],
            data.get("benchmark_name", "throughput"),
            data.get("suite_name", "quick"),
            command_id,
            now,
        ),
    )
    conn.commit()

    # Publish queued event for SSE subscribers
    event_bus.publish(
        "status",
        test_id,
        {"status": "queued", "test_id": test_id, "command_id": command_id},
    )

    return jsonify({"id": test_id, "status": "queued", "command_id": command_id}), 202


@bp.route("/<test_id>", methods=["GET"])
def status(test_id):
    """Get quick test status."""
    from kitt.web.app import get_services

    conn = get_services()["db_conn"]
    row = conn.execute("SELECT * FROM quick_tests WHERE id = ?", (test_id,)).fetchone()

    if row is None:
        return jsonify({"error": "Quick test not found"}), 404

    return jsonify(dict(row))


@bp.route("/<test_id>/logs", methods=["POST"])
@require_auth
def post_log(test_id):
    """Agent POSTs log lines here during test execution."""
    from kitt.web.app import get_services

    conn = get_services()["db_conn"]
    row = conn.execute("SELECT id FROM quick_tests WHERE id = ?", (test_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Quick test not found"}), 404

    data = request.get_json(silent=True)
    if not data or "line" not in data:
        return jsonify({"error": "'line' is required"}), 400

    # Publish log line to SSE subscribers
    event_bus.publish(
        "log",
        test_id,
        {"line": data["line"], "test_id": test_id},
    )

    return jsonify({"ok": True})


@bp.route("/<test_id>/status", methods=["POST"])
@require_auth
def update_status(test_id):
    """Agent updates test status (running, completed, failed)."""
    from kitt.web.app import get_services

    conn = get_services()["db_conn"]
    row = conn.execute("SELECT id FROM quick_tests WHERE id = ?", (test_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Quick test not found"}), 404

    data = request.get_json(silent=True)
    if not data or "status" not in data:
        return jsonify({"error": "'status' is required"}), 400

    new_status = data["status"]
    allowed = {"running", "completed", "failed"}
    if new_status not in allowed:
        return jsonify({"error": f"Status must be one of: {allowed}"}), 400

    now = datetime.now().isoformat()

    if new_status == "running":
        conn.execute(
            "UPDATE quick_tests SET status = ?, started_at = ? WHERE id = ?",
            (new_status, now, test_id),
        )
    elif new_status in ("completed", "failed"):
        error = data.get("error", "")
        conn.execute(
            "UPDATE quick_tests SET status = ?, completed_at = ?, error = ? WHERE id = ?",
            (new_status, now, error, test_id),
        )
    conn.commit()

    # Publish status event for SSE subscribers
    event_bus.publish(
        "status",
        test_id,
        {"status": new_status, "test_id": test_id},
    )

    return jsonify({"ok": True, "status": new_status})
