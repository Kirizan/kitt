"""Settings blueprint — server configuration page."""

from flask import Blueprint, render_template, render_template_string, request

bp = Blueprint("settings", __name__, url_prefix="/settings")

# Only these keys can be toggled via the settings UI.
_ALLOWED_TOGGLE_KEYS = {"devon_tab_visible"}

_TOGGLE_TEMPLATE = """\
<button type="button" hx-post="/settings/toggle" hx-vals='{"key": "{{ key }"}' hx-swap="outerHTML"
        class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {{ 'bg-kitt-accent' if value else 'bg-kitt-primary' }}"
        role="switch" aria-checked="{{ 'true' if value else 'false' }}">
    <span class="inline-block h-4 w-4 rounded-full bg-white transition-transform {{ 'translate-x-5' if value else 'translate-x-0' }}"></span>
</button>
<span class="text-sm ml-2 {{ 'text-green-400' if value else 'text-kitt-dim' }}">{{ 'Visible' if value else 'Hidden' }}</span>"""


@bp.route("/")
def index():
    """Settings page."""
    from flask import current_app

    from kitt.web.app import get_services

    settings_svc = get_services()["settings_service"]

    config = {
        "host": current_app.config.get("HOST", "0.0.0.0"),
        "port": current_app.config.get("PORT", 8080),
        "debug": current_app.config.get("DEBUG", False),
        "tls_enabled": current_app.config.get("TLS_ENABLED", True),
        "insecure": current_app.config.get("INSECURE", False),
        "db_path": str(current_app.config.get("DB_PATH", "")),
        "results_dir": str(current_app.config.get("RESULTS_DIR", "")),
        "devon_url": current_app.config.get("DEVON_URL", ""),
    }
    web_settings = settings_svc.get_all()

    return render_template(
        "settings/index.html", config=config, web_settings=web_settings
    )


@bp.route("/toggle", methods=["POST"])
def toggle():
    """Toggle a boolean web setting."""
    from kitt.web.app import get_services

    settings_svc = get_services()["settings_service"]

    key = request.form.get("key", "")
    if key not in _ALLOWED_TOGGLE_KEYS:
        return "Invalid key", 400

    current = settings_svc.get_bool(key, default=True)
    settings_svc.set(key, "false" if current else "true")

    return render_template_string(_TOGGLE_TEMPLATE, key=key, value=not current)
