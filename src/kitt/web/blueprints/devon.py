"""Devon blueprint — embedded Devon web UI."""

import logging

from flask import Blueprint, render_template

logger = logging.getLogger(__name__)

bp = Blueprint("devon", __name__, url_prefix="/devon")


@bp.route("/")
def index():
    """Devon web UI page (iframe or configuration instructions)."""
    from flask import current_app

    from kitt.web.app import get_services

    devon_url = current_app.config.get("DEVON_URL", "")
    settings_svc = get_services()["settings_service"]
    devon_visible = settings_svc.get_bool("devon_tab_visible", default=True)

    return render_template(
        "devon/index.html",
        devon_url=devon_url,
        devon_configured=bool(devon_url),
        devon_tab_visible=devon_visible,
    )
