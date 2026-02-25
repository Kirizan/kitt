"""Agent REST API endpoints."""

import logging

from flask import Blueprint, jsonify, request

from kitt.web.auth import require_auth
from kitt.web.models.agent import AgentHeartbeat, AgentRegistration

logger = logging.getLogger(__name__)

bp = Blueprint("api_agents", __name__, url_prefix="/api/v1/agents")


def _get_agent_manager():
    from kitt.web.app import get_services

    return get_services()["agent_manager"]


def _extract_bearer_token() -> str:
    """Extract bearer token from Authorization header, or empty string."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return ""


@bp.route("/register", methods=["POST"])
def register():
    """Register a new agent.

    The agent must provide a Bearer token that matches its provisioned
    token hash.  If the agent has no token_hash stored (legacy or dev
    mode), registration succeeds without a token.
    """
    token = _extract_bearer_token()

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        reg = AgentRegistration(**data)
    except Exception as e:
        return jsonify({"error": f"Invalid registration data: {e}"}), 400

    mgr = _get_agent_manager()

    # Look up the agent to check if it has a provisioned token
    row = mgr._conn.execute(
        "SELECT id, token_hash, token FROM agents WHERE name = ?", (reg.name,)
    ).fetchone()

    if row:
        stored_hash = row["token_hash"] or ""
        stored_raw = row["token"] or ""
        # Agent has a token configured — verify it
        if stored_hash or stored_raw:
            if not token:
                return jsonify({"error": "Missing authorization"}), 401
            if not mgr.verify_token(row["id"], token):
                return jsonify({"error": "Invalid token for this agent"}), 403

    result = mgr.register(reg, token)
    return jsonify(result), 201


@bp.route("/<agent_id>/heartbeat", methods=["POST"])
def heartbeat(agent_id):
    """Process agent heartbeat.

    Verifies the agent's Bearer token against its stored hash.
    Agents with no token configured (empty hash) are allowed through.
    """
    token = _extract_bearer_token()

    mgr = _get_agent_manager()

    # Check if agent exists and has a token configured
    row = mgr._conn.execute(
        "SELECT token_hash, token FROM agents WHERE id = ?", (agent_id,)
    ).fetchone()

    if row is None:
        return jsonify({"error": "Agent not found"}), 404

    stored_hash = row["token_hash"] or ""
    stored_raw = row["token"] or ""

    # Agent has a token configured — verify it
    if stored_hash or stored_raw:
        if not token:
            return jsonify({"error": "Missing authorization"}), 401
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
@require_auth
def delete_agent(agent_id):
    """Remove an agent."""
    mgr = _get_agent_manager()
    if mgr.delete_agent(agent_id):
        return jsonify({"deleted": True})
    return jsonify({"error": "Agent not found"}), 404


@bp.route("/<agent_id>", methods=["PATCH"])
@require_auth
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
    """Agent reports benchmark result.

    Verifies the agent's Bearer token against its stored hash.
    Agents with no token configured (empty hash) are allowed through.
    """
    token = _extract_bearer_token()

    mgr = _get_agent_manager()

    row = mgr._conn.execute(
        "SELECT token_hash, token FROM agents WHERE id = ?", (agent_id,)
    ).fetchone()

    if row is None:
        return jsonify({"error": "Agent not found"}), 404

    stored_hash = row["token_hash"] or ""
    stored_raw = row["token"] or ""

    if stored_hash or stored_raw:
        if not token:
            return jsonify({"error": "Missing authorization"}), 401
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


@bp.route("/<agent_id>/rotate-token", methods=["POST"])
@require_auth
def rotate_token(agent_id):
    """Generate a new token for an agent. Admin-only."""
    mgr = _get_agent_manager()
    result = mgr.rotate_token(agent_id)
    if result is None:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify(result)
