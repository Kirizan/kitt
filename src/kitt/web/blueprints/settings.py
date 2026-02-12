"""Settings blueprint — server configuration page."""

from flask import Blueprint, render_template

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/")
def index():
    """Settings page."""
    from flask import current_app

    config = {
        "host": current_app.config.get("HOST", "0.0.0.0"),
        "port": current_app.config.get("PORT", 8080),
        "debug": current_app.config.get("DEBUG", False),
        "tls_enabled": current_app.config.get("TLS_ENABLED", True),
        "insecure": current_app.config.get("INSECURE", False),
        "db_path": str(current_app.config.get("DB_PATH", "")),
        "results_dir": str(current_app.config.get("RESULTS_DIR", "")),
    }

    return render_template("settings/index.html", config=config)
