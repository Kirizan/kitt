"""Tests for TGI engine — Docker lifecycle and HuggingFace API generation."""

import json
from unittest.mock import MagicMock, patch

from kitt.engines.tgi_engine import TGIEngine


class TestTGIEngineMetadata:
    def test_name(self):
        assert TGIEngine.name() == "tgi"

    def test_supported_formats(self):
        assert "safetensors" in TGIEngine.supported_formats()
        assert "pytorch" in TGIEngine.supported_formats()

    def test_default_image(self):
        assert "text-generation-inference" in TGIEngine.default_image()

    def test_default_port(self):
        assert TGIEngine.default_port() == 8080

    def test_container_port(self):
        assert TGIEngine.container_port() == 80

    def test_health_endpoint(self):
        assert TGIEngine.health_endpoint() == "/info"


class TestTGIEngineAvailability:
    @patch("kitt.engines.docker_manager.DockerManager.image_exists", return_value=True)
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_is_available_true(self, mock_avail, mock_exists):
        assert TGIEngine.is_available() is True

    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=False)
    def test_diagnose_no_docker(self, mock_avail):
        diag = TGIEngine.diagnose()
        assert diag.available is False
        assert "Docker is not installed" in diag.error

    @patch("kitt.engines.docker_manager.DockerManager.image_exists", return_value=False)
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_diagnose_image_not_pulled(self, mock_avail, mock_exists):
        diag = TGIEngine.diagnose()
        assert diag.available is False
        assert "not pulled" in diag.error
        assert "kitt engines setup tgi" in diag.guidance


class TestTGIEngineInitialize:
    @patch("kitt.engines.tgi_engine.Path")
    @patch("kitt.engines.docker_manager.DockerManager.wait_for_healthy", return_value=True)
    @patch("kitt.engines.docker_manager.DockerManager.run_container", return_value="container123")
    def test_initialize_with_hf_model(self, mock_run, mock_wait, mock_path):
        # model_path is not a local directory
        mock_path.return_value.resolve.return_value.is_dir.return_value = False

        engine = TGIEngine()
        engine.initialize("meta-llama/Llama-3-8B", {})

        mock_run.assert_called_once()
        config = mock_run.call_args[0][0]
        assert "--model-id" in config.command_args
        assert "meta-llama/Llama-3-8B" in config.command_args

    @patch("kitt.engines.tgi_engine.Path")
    @patch("kitt.engines.docker_manager.DockerManager.wait_for_healthy", return_value=True)
    @patch("kitt.engines.docker_manager.DockerManager.run_container", return_value="container123")
    def test_initialize_with_local_model(self, mock_run, mock_wait, mock_path):
        # model_path is a local directory
        mock_resolved = MagicMock()
        mock_resolved.is_dir.return_value = True
        mock_resolved.name = "llama-7b"
        mock_resolved.__str__ = lambda s: "/models/llama-7b"
        mock_path.return_value.resolve.return_value = mock_resolved

        engine = TGIEngine()
        engine.initialize("/models/llama-7b", {})

        config = mock_run.call_args[0][0]
        assert "--model-id" in config.command_args
        assert "/models/llama-7b" in config.command_args


class TestTGIEngineGenerate:
    @patch("kitt.collectors.gpu_stats.GPUMemoryTracker")
    @patch("kitt.engines.tgi_engine.urllib.request.urlopen")
    def test_generate_calls_tgi_api(self, mock_urlopen, mock_tracker_cls):
        mock_tracker = MagicMock()
        mock_tracker.get_peak_memory_mb.return_value = 0.0
        mock_tracker.get_average_memory_mb.return_value = 0.0
        mock_tracker_cls.return_value.__enter__ = lambda s: mock_tracker
        mock_tracker_cls.return_value.__exit__ = MagicMock(return_value=False)

        response_data = {
            "generated_text": "Hello world",
            "details": {"prefill": [{}] * 5, "generated_tokens": 10},
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        engine = TGIEngine()
        engine._base_url = "http://localhost:8080"
        result = engine.generate("test prompt")

        assert result.output == "Hello world"
        assert result.completion_tokens == 10
        assert result.prompt_tokens == 5


class TestTGIEngineCleanup:
    @patch("kitt.engines.docker_manager.DockerManager.stop_container")
    def test_cleanup_stops_container(self, mock_stop):
        engine = TGIEngine()
        engine._container_id = "abc123"
        engine.cleanup()
        mock_stop.assert_called_once_with("abc123")
        assert engine._container_id is None
