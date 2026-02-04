"""Tests for TGI engine diagnostics."""

import json
import urllib.error
from unittest.mock import MagicMock, patch


class TestTGIDiagnose:
    def _get_engine_cls(self):
        from kitt.engines.tgi_engine import TGIEngine

        return TGIEngine

    def test_diagnose_server_available(self):
        cls = self._get_engine_cls()
        response_data = json.dumps(
            {"model_id": "meta-llama/Llama-3-8B"}
        ).encode()
        mock_response = MagicMock()
        mock_response.read.return_value = response_data
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            diag = cls.diagnose()
        assert diag.available is True
        assert diag.engine_type == "http_server"
        assert "meta-llama/Llama-3-8B" in diag.guidance

    def test_diagnose_server_not_running(self):
        cls = self._get_engine_cls()
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            diag = cls.diagnose()
        assert diag.available is False
        assert "Cannot connect" in diag.error
        assert "docker run" in diag.guidance

    def test_diagnose_server_timeout(self):
        cls = self._get_engine_cls()
        with patch(
            "urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            diag = cls.diagnose()
        assert diag.available is False
        assert "Connection error" in diag.error
        assert "docker run" in diag.guidance

    def test_check_dependencies_still_returns_true(self):
        """_check_dependencies behavior is unchanged — always True for TGI."""
        cls = self._get_engine_cls()
        assert cls._check_dependencies() is True
