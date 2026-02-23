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
    error = None

    if query:
        try:
            results = model_svc.search(query)
        except Exception as e:
            error = str(e)

    return render_template(
        "models/search.html",
        query=query,
        results=results,
        error=error,
        devon_configured=model_svc.configured,
    )


@bp.route("/library")
def library():
    """Local model library page."""
    from kitt.web.app import get_services

    model_svc = get_services()["model_service"]
    models = []
    error = None

    try:
        models = model_svc.list_local()
    except Exception as e:
        error = str(e)

    return render_template(
        "models/library.html",
        models=models,
        error=error,
        devon_configured=model_svc.configured,
    )
