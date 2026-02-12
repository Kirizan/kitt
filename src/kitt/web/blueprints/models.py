"""Models blueprint — Devon model browser pages."""

from flask import Blueprint, render_template, request

bp = Blueprint("models", __name__, url_prefix="/models")


@bp.route("/")
def search():
    """Model search page."""
    from kitt.web.app import get_services

    model_svc = get_services()["model_service"]
    query = request.args.get("q", "")
    results = []

    if query:
        results = model_svc.search(query)

    return render_template(
        "models/search.html",
        query=query,
        results=results,
        devon_available=model_svc.available,
    )


@bp.route("/library")
def library():
    """Local model library page."""
    from kitt.web.app import get_services

    model_svc = get_services()["model_service"]
    models = model_svc.list_local()

    return render_template(
        "models/library.html",
        models=models,
        devon_available=model_svc.available,
    )
