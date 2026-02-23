"""Devon integration API endpoints."""

import logging
import urllib.request

from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

bp = Blueprint("api_devon", __name__, url_prefix="/api/v1/devon")


def _get_devon_url() -> str:
    from flask import current_app

    return current_app.config.get("DEVON_URL", "")


@bp.route("/status")
def status():
    """Check if the Devon web UI is reachable."""
    devon_url = _get_devon_url()
    if not devon_url:
        return jsonify({"available": False, "url": "", "reason": "not_configured"})

    try:
        req = urllib.request.Request(devon_url, method="HEAD")
        with urllib.request.urlopen(req, timeout=3):
            pass
        return jsonify({"available": True, "url": devon_url})
    except Exception as e:
        logger.debug(f"Devon health check failed: {e}")
        return jsonify(
            {"available": False, "url": devon_url, "reason": "unreachable"}
        )
