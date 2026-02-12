"""Agent REST API endpoints."""

import logging

from flask import Blueprint, jsonify, request

from kitt.web.models.agent import AgentHeartbeat, AgentRegistration

logger = logging.getLogger(__name__)

bp = Blueprint("api_agents", __name__, url_prefix="/api/v1/agents")


def _get_agent_manager():
    from kitt.web.app import get_services

    return get_services()["agent_manager"]


def _check_auth():
    """Validate bearer token from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth[7:]


@bp.route("/register", methods=["POST"])
def register():
    """Register a new agent."""
    token = _check_auth()
    if not token:
        return jsonify({"error": "Missing or invalid authorization"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        reg = AgentRegistration(**data)
    except Exception as e:
        return jsonify({"error": f"Invalid registration data: {e}"}), 400

    mgr = _get_agent_manager()
    result = mgr.register(reg, token)
    return jsonify(result), 201


@bp.route("/<agent_id>/heartbeat", methods=["POST"])
def heartbeat(agent_id):
    """Process agent heartbeat."""
    token = _check_auth()
    if not token:
        return jsonify({"error": "Missing or invalid authorization"}), 401

    mgr = _get_agent_manager()
    if not mgr.verify_token(agent_id, token):
        return jsonify({"error": "Invalid token for this agent"}), 403

    data = request.get_json(silent=True) or {}
    hb = AgentHeartbeat(**data)
    result = mgr.heartbeat(agent_id, hb)
    return jsonify(result)


@bp.route("/", methods=["GET"])
def list_agents():
    """List all agents."""
    mgr = _get_agent_manager()
    agents = mgr.list_agents()
    return jsonify(agents)


@bp.route("/<agent_id>", methods=["GET"])
def get_agent(agent_id):
    """Get agent details."""
    mgr = _get_agent_manager()
    agent = mgr.get_agent(agent_id)
    if agent is None:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify(agent)


@bp.route("/<agent_id>", methods=["DELETE"])
def delete_agent(agent_id):
    """Remove an agent."""
    mgr = _get_agent_manager()
    if mgr.delete_agent(agent_id):
        return jsonify({"deleted": True})
    return jsonify({"error": "Agent not found"}), 404


@bp.route("/<agent_id>", methods=["PATCH"])
def update_agent(agent_id):
    """Update agent fields."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    mgr = _get_agent_manager()
    if mgr.update_agent(agent_id, data):
        return jsonify({"updated": True})
    return jsonify({"error": "No valid fields to update"}), 400


@bp.route("/<agent_id>/results", methods=["POST"])
def report_result(agent_id):
    """Agent reports benchmark result."""
    token = _check_auth()
    if not token:
        return jsonify({"error": "Missing or invalid authorization"}), 401

    mgr = _get_agent_manager()
    if not mgr.verify_token(agent_id, token):
        return jsonify({"error": "Invalid token for this agent"}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    # Store the result if result_data is provided
    from kitt.web.app import get_services

    result_svc = get_services()["result_service"]
    result_data = data.get("result_data")
    if result_data:
        result_svc._store.save_result(result_data)

    return jsonify({"accepted": True}), 202
