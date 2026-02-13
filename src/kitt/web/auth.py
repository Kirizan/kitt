"""Authentication middleware for KITT web API."""

import hmac
import logging
from functools import wraps

from flask import current_app, jsonify, request

logger = logging.getLogger(__name__)


def require_auth(f):
    """Decorator that enforces Bearer token authentication.

    Uses timing-safe comparison to prevent timing attacks.
    When AUTH_TOKEN is empty, auth is disabled (development mode).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        configured_token = current_app.config.get("AUTH_TOKEN", "")
        if not configured_token:
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization"}), 401

        provided_token = auth_header[7:]
        if not hmac.compare_digest(provided_token, configured_token):
            return jsonify({"error": "Invalid authentication token"}), 403

        return f(*args, **kwargs)
    return decorated
