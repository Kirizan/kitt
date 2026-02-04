"""Tests for engine CLI commands (setup, check, list) — Docker-only."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kitt.cli.engine_commands import engines
from kitt.engines.base import EngineDiagnostics


class TestSetupEngine:
    @patch("kitt.engines.docker_manager.DockerManager.pull_image")
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_setup_pulls_image(self, mock_avail, mock_pull):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code == 0
        assert "ready" in result.output
        mock_pull.assert_called_once_with("vllm/vllm-openai:latest")

    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_setup_dry_run(self, mock_avail):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "--dry-run", "vllm"])
        assert result.exit_code == 0
        assert "would run" in result.output
        assert "docker pull" in result.output
        assert "vllm/vllm-openai" in result.output
        assert "Dry run" in result.output

    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=False)
    def test_setup_no_docker(self, mock_avail):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code != 0
        assert "Docker is not installed" in result.output

    @patch("kitt.engines.docker_manager.DockerManager.pull_image", side_effect=RuntimeError("network error"))
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_setup_pull_failure(self, mock_avail, mock_pull):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code != 0
        assert "network error" in result.output

    def test_setup_unknown_engine(self):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output

    @patch("kitt.engines.docker_manager.DockerManager.pull_image")
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_setup_ollama(self, mock_avail, mock_pull):
        """All engines are now supported by setup (not just vllm)."""
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "ollama"])
        assert result.exit_code == 0
        assert "ready" in result.output
        mock_pull.assert_called_once_with("ollama/ollama:latest")

    @patch("kitt.engines.docker_manager.DockerManager.pull_image")
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_setup_tgi(self, mock_avail, mock_pull):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "tgi"])
        assert result.exit_code == 0
        mock_pull.assert_called_once()
        image_arg = mock_pull.call_args[0][0]
        assert "text-generation-inference" in image_arg

    @patch("kitt.engines.docker_manager.DockerManager.pull_image")
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_setup_llama_cpp(self, mock_avail, mock_pull):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "llama_cpp"])
        assert result.exit_code == 0
        mock_pull.assert_called_once_with(
            "ghcr.io/ggerganov/llama.cpp:server"
        )


class TestCheckEngine:
    def test_check_available(self):
        diag = EngineDiagnostics(
            available=True,
            image="vllm/vllm-openai:latest",
        )
        with patch(
            "kitt.engines.vllm_engine.VLLMEngine.diagnose", return_value=diag
        ):
            runner = CliRunner()
            result = runner.invoke(engines, ["check", "vllm"])
        assert "Available" in result.output
        assert "vllm/vllm-openai:latest" in result.output

    def test_check_not_available(self):
        diag = EngineDiagnostics(
            available=False,
            image="vllm/vllm-openai:latest",
            error="Docker image not pulled: vllm/vllm-openai:latest",
            guidance="Pull with: kitt engines setup vllm",
        )
        with patch(
            "kitt.engines.vllm_engine.VLLMEngine.diagnose", return_value=diag
        ):
            runner = CliRunner()
            result = runner.invoke(engines, ["check", "vllm"])
        assert "Not Available" in result.output
        assert "not pulled" in result.output
        assert "kitt engines setup vllm" in result.output

    def test_check_no_docker(self):
        diag = EngineDiagnostics(
            available=False,
            image="vllm/vllm-openai:latest",
            error="Docker is not installed or not running",
            guidance="Install Docker: https://docs.docker.com/get-docker/",
        )
        with patch(
            "kitt.engines.vllm_engine.VLLMEngine.diagnose", return_value=diag
        ):
            runner = CliRunner()
            result = runner.invoke(engines, ["check", "vllm"])
        assert "Docker is not installed" in result.output

    def test_check_unknown_engine(self):
        runner = CliRunner()
        result = runner.invoke(engines, ["check", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestListEngines:
    @patch("kitt.engines.docker_manager.DockerManager.image_exists", return_value=True)
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_list_shows_all_engines(self, mock_avail, mock_exists):
        runner = CliRunner()
        result = runner.invoke(engines, ["list"])
        assert result.exit_code == 0
        assert "vllm" in result.output
        assert "tgi" in result.output
        assert "llama_cpp" in result.output
        assert "ollama" in result.output

    @patch("kitt.engines.docker_manager.DockerManager.image_exists", return_value=False)
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_list_shows_image_column(self, mock_avail, mock_exists):
        runner = CliRunner()
        result = runner.invoke(engines, ["list"])
        assert "vllm/vllm-openai" in result.output
        assert "ollama/ollama" in result.output

    @patch("kitt.engines.docker_manager.DockerManager.image_exists", return_value=False)
    @patch("kitt.engines.docker_manager.DockerManager.is_docker_available", return_value=True)
    def test_list_shows_status(self, mock_avail, mock_exists):
        runner = CliRunner()
        result = runner.invoke(engines, ["list"])
        assert "Not Pulled" in result.output
