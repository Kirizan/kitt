"""Campaign REST API endpoints."""

import logging

from flask import Blueprint, jsonify, request

from kitt.web.auth import require_auth

logger = logging.getLogger(__name__)

bp = Blueprint("api_campaigns", __name__, url_prefix="/api/v1/campaigns")


def _get_campaign_service():
    from kitt.web.app import get_services

    return get_services()["campaign_service"]


@bp.route("/", methods=["GET"])
def list_campaigns():
    """List campaigns."""
    status = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    svc = _get_campaign_service()
    result = svc.list_campaigns(status=status, page=page, per_page=per_page)
    return jsonify(result)


@bp.route("/", methods=["POST"])
@require_auth
def create_campaign():
    """Create a new campaign."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    name = data.get("name")
    if not name:
        return jsonify({"error": "Campaign name is required"}), 400

    svc = _get_campaign_service()
    campaign_id = svc.create(
        name=name,
        config_json=data.get("config", {}),
        description=data.get("description", ""),
        agent_id=data.get("agent_id", ""),
    )
    return jsonify({"id": campaign_id}), 201


@bp.route("/<campaign_id>", methods=["GET"])
def get_campaign(campaign_id):
    """Get campaign details."""
    svc = _get_campaign_service()
    campaign = svc.get(campaign_id)
    if campaign is None:
        return jsonify({"error": "Campaign not found"}), 404
    return jsonify(campaign)


@bp.route("/<campaign_id>", methods=["DELETE"])
@require_auth
def delete_campaign(campaign_id):
    """Delete a campaign."""
    svc = _get_campaign_service()
    if svc.delete(campaign_id):
        return jsonify({"deleted": True})
    return jsonify({"error": "Campaign not found"}), 404


@bp.route("/<campaign_id>/launch", methods=["POST"])
@require_auth
def launch_campaign(campaign_id):
    """Launch a campaign on the assigned agent."""
    svc = _get_campaign_service()
    campaign = svc.get(campaign_id)
    if campaign is None:
        return jsonify({"error": "Campaign not found"}), 404

    if campaign["status"] not in ("draft", "failed"):
        return jsonify(
            {"error": f"Cannot launch campaign in '{campaign['status']}' status"}
        ), 400

    if not campaign.get("agent_id"):
        return jsonify({"error": "No agent assigned to this campaign"}), 400

    svc.update_status(campaign_id, "queued")
    return jsonify({"status": "queued"}), 202


@bp.route("/<campaign_id>/cancel", methods=["POST"])
@require_auth
def cancel_campaign(campaign_id):
    """Cancel a running campaign."""
    svc = _get_campaign_service()
    campaign = svc.get(campaign_id)
    if campaign is None:
        return jsonify({"error": "Campaign not found"}), 404

    if campaign["status"] not in ("queued", "running"):
        return jsonify(
            {"error": f"Cannot cancel campaign in '{campaign['status']}' status"}
        ), 400

    svc.update_status(campaign_id, "cancelled")
    return jsonify({"status": "cancelled"})


@bp.route("/<campaign_id>/config", methods=["PUT"])
@require_auth
def update_config(campaign_id):
    """Update campaign configuration (draft only)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    svc = _get_campaign_service()
    if svc.update_config(campaign_id, data):
        return jsonify({"updated": True})
    return jsonify({"error": "Campaign not found or not in draft status"}), 400
