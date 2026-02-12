"""Quick test blueprint — single benchmark execution pages."""

from flask import Blueprint, render_template

bp = Blueprint("quicktest", __name__, url_prefix="/quicktest")


@bp.route("/")
def form():
    """Quick test launch form."""
    from kitt.web.app import get_services

    agent_mgr = get_services()["agent_manager"]
    agents = agent_mgr.list_agents()

    return render_template("quicktest/form.html", agents=agents)
