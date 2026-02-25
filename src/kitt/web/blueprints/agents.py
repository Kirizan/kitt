"""Agents blueprint — agent management pages."""

import contextlib
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for

bp = Blueprint("agents", __name__, url_prefix="/agents")


@bp.route("/")
def list_agents():
    """Agent list page."""
    from kitt.web.app import get_services

    agent_mgr = get_services()["agent_manager"]
    agents = agent_mgr.list_agents()

    return render_template("agents/list.html", agents=agents)


@bp.route("/<agent_id>")
def detail(agent_id):
    """Agent detail page."""
    from kitt.web.app import get_services

    agent_mgr = get_services()["agent_manager"]
    agent = agent_mgr.get_agent(agent_id)

    if agent is None:
        flash("Agent not found", "error")
        return redirect(url_for("agents.list_agents"))

    # Parse hardware_details JSON for the template
    hw_details = {}
    raw_details = agent.get("hardware_details", "")
    if raw_details:
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            hw_details = json.loads(raw_details)

    return render_template("agents/detail.html", agent=agent, hw=hw_details)


@bp.route("/add")
def add():
    """Add agent page with setup instructions."""
    from flask import current_app

    server_url = request.host_url.rstrip("/")
    auth_token = current_app.config.get("AUTH_TOKEN", "")

    return render_template(
        "agents/add.html",
        server_url=server_url,
        auth_token=auth_token,
    )


@bp.route("/<agent_id>/delete", methods=["POST"])
def delete(agent_id):
    """Delete an agent."""
    from kitt.web.app import get_services

    agent_mgr = get_services()["agent_manager"]
    agent_mgr.delete_agent(agent_id)
    flash("Agent removed", "success")
    return redirect(url_for("agents.list_agents"))
