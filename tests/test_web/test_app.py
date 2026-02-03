"""Tests for the Flask web application."""

import json
from pathlib import Path

import pytest

from kitt.web.app import create_app, _scan_results


@pytest.fixture
def app(tmp_path):
    """Create a test Flask app with sample results."""
    # Create sample results
    results_dir = tmp_path / "kitt-results" / "test-model" / "ollama" / "2025-01-01_120000"
    results_dir.mkdir(parents=True)

    metrics = {
        "kitt_version": "1.1.0",
        "suite_name": "quick",
        "timestamp": "2025-01-01T12:00:00",
        "engine": "ollama",
        "model": "test-model",
        "passed": True,
        "total_benchmarks": 1,
        "passed_count": 1,
        "failed_count": 0,
        "total_time_seconds": 5.0,
        "results": [
            {
                "test_name": "throughput",
                "test_version": "1.0.0",
                "run_number": 1,
                "passed": True,
                "metrics": {"avg_tps": 50.0, "total_iterations": 5},
                "errors": [],
                "warmup_times": [],
            }
        ],
    }

    with open(results_dir / "metrics.json", "w") as f:
        json.dump(metrics, f)

    flask_app = create_app(str(tmp_path))
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"KITT" in response.data
    assert b"test-model" in response.data


def test_api_results(client):
    response = client.get("/api/results")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["model"] == "test-model"


def test_api_result_detail(client):
    response = client.get("/api/results/0")
    assert response.status_code == 200
    data = response.get_json()
    assert data["engine"] == "ollama"


def test_api_result_not_found(client):
    response = client.get("/api/results/99")
    assert response.status_code == 404


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_empty_results(tmp_path):
    app = create_app(str(tmp_path))
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    assert b"No Results Found" in response.data


def test_scan_results(tmp_path):
    results = _scan_results(tmp_path)
    assert results == []
