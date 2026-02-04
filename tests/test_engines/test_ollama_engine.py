"""Tests for Ollama engine diagnostics."""

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch


class TestOllamaDiagnose:
    def _get_engine_cls(self):
        from kitt.engines.ollama_engine import OllamaEngine

        return OllamaEngine

    def test_diagnose_server_available(self):
        cls = self._get_engine_cls()
        response_data = json.dumps(
            {"models": [{"name": "llama3:latest"}, {"name": "mistral:latest"}]}
        ).encode()
        mock_response = MagicMock()
        mock_response.read.return_value = response_data
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            diag = cls.diagnose()
        assert diag.available is True
        assert diag.engine_type == "http_server"
        assert "2 model(s)" in diag.guidance

    def test_diagnose_server_not_running(self):
        cls = self._get_engine_cls()
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            diag = cls.diagnose()
        assert diag.available is False
        assert "Cannot connect" in diag.error
        assert "ollama serve" in diag.guidance

    def test_diagnose_server_timeout(self):
        cls = self._get_engine_cls()
        with patch(
            "urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            diag = cls.diagnose()
        assert diag.available is False
        assert "Connection error" in diag.error
        assert "ollama serve" in diag.guidance
