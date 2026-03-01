"""REST API for engine profiles and engine status."""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from kitt.web.app import get_services

logger = logging.getLogger(__name__)

bp = Blueprint("api_engines", __name__, url_prefix="/api/v1/engines")


def _svc():
    return get_services()["engine_service"]


# ------------------------------------------------------------------
# Engine profiles CRUD
# ------------------------------------------------------------------


@bp.route("/profiles", methods=["GET"])
def list_profiles():
    """List all engine profiles, optionally filtered by engine."""
    engine = request.args.get("engine")
    profiles = _svc().list_profiles(engine=engine)
    return jsonify({"profiles": profiles})


@bp.route("/profiles", methods=["POST"])
def create_profile():
    """Create a new engine profile."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    name = data.get("name", "").strip()
    engine = data.get("engine", "").strip()
    if not name or not engine:
        return jsonify({"error": "name and engine are required"}), 400

    # Check for duplicate name.
    existing = _svc().get_profile_by_name(name)
    if existing:
        return jsonify({"error": f"Profile '{name}' already exists"}), 409

    profile = _svc().create_profile(data)
    return jsonify(profile), 201


@bp.route("/profiles/<profile_id>", methods=["GET"])
def get_profile(profile_id):
    """Get a single engine profile."""
    profile = _svc().get_profile(profile_id)
    if profile is None:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile)


@bp.route("/profiles/<profile_id>", methods=["PUT"])
def update_profile(profile_id):
    """Update an engine profile."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    profile = _svc().update_profile(profile_id, data)
    if profile is None:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile)


@bp.route("/profiles/<profile_id>", methods=["DELETE"])
def delete_profile(profile_id):
    """Delete an engine profile."""
    deleted = _svc().delete_profile(profile_id)
    if not deleted:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify({"deleted": True})


# ------------------------------------------------------------------
# Engine status
# ------------------------------------------------------------------


@bp.route("/status", methods=["GET"])
def engine_status_matrix():
    """Get per-agent engine status matrix."""
    matrix = _svc().get_engine_status_matrix()
    return jsonify({"matrix": matrix})


@bp.route("/registry", methods=["GET"])
def engine_registry():
    """List registered engines with their supported modes."""
    try:
        from kitt.engines.registry import EngineRegistry

        EngineRegistry.auto_discover()
        engines = []
        for name, cls in EngineRegistry.list_engines().items():
            engines.append({
                "name": name,
                "supported_modes": [m.value for m in cls.supported_modes()],
                "default_mode": cls.default_mode().value,
                "default_image": cls.default_image(),
                "container_port": cls.container_port(),
            })
        return jsonify({"engines": engines})
    except Exception as e:
        logger.warning("Failed to list engine registry: %s", e)
        return jsonify({"engines": [], "error": str(e)})
