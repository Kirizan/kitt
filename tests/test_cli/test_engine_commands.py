"""Tests for engine CLI commands (setup and enhanced check)."""

from unittest.mock import patch

from click.testing import CliRunner

from kitt.cli.engine_commands import engines
from kitt.hardware.detector import CudaMismatchInfo


class TestSetupEngine:
    def test_unsupported_engine_exits(self):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "ollama"])
        assert result.exit_code != 0
        assert "not supported by setup" in result.output

    @patch("kitt.hardware.detector.detect_cuda_version", return_value=None)
    def test_no_cuda_exits(self, mock_cuda):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code != 0
        assert "No system CUDA detected" in result.output

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    def test_dry_run_shows_commands(self, mock_cuda):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "--dry-run", "vllm"])
        assert result.exit_code == 0
        assert "cu130" in result.output
        assert "would run:" in result.output
        assert "torch" in result.output
        assert "vllm" in result.output
        assert "--force-reinstall" in result.output
        assert "--no-deps" in result.output
        assert "Dry run" in result.output

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="12.6")
    def test_dry_run_cuda12(self, mock_cuda):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "--dry-run", "vllm"])
        assert result.exit_code == 0
        assert "cu120" in result.output


class TestCheckEngineEnhanced:
    @patch(
        "kitt.hardware.detector.check_cuda_compatibility",
        return_value=CudaMismatchInfo(
            system_cuda="13.0",
            torch_cuda="12.4",
            system_major=13,
            torch_major=12,
        ),
    )
    @patch("kitt.hardware.detector.detect_torch_cuda_version", return_value="12.4")
    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    def test_check_shows_mismatch(self, mock_sys, mock_torch, mock_compat):
        runner = CliRunner()
        result = runner.invoke(engines, ["check", "vllm"])
        assert "System CUDA: 13.0" in result.output
        assert "PyTorch CUDA: 12.4" in result.output
        assert "CUDA mismatch" in result.output
        assert "cu130" in result.output
        assert "kitt engines setup vllm" in result.output

    @patch("kitt.hardware.detector.check_cuda_compatibility", return_value=None)
    @patch("kitt.hardware.detector.detect_torch_cuda_version", return_value="13.0")
    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    def test_check_no_mismatch(self, mock_sys, mock_torch, mock_compat):
        runner = CliRunner()
        result = runner.invoke(engines, ["check", "vllm"])
        assert "System CUDA: 13.0" in result.output
        assert "PyTorch CUDA: 13.0" in result.output
        assert "CUDA mismatch" not in result.output

    @patch("kitt.hardware.detector.check_cuda_compatibility", return_value=None)
    @patch("kitt.hardware.detector.detect_torch_cuda_version", return_value=None)
    @patch("kitt.hardware.detector.detect_cuda_version", return_value=None)
    def test_check_no_cuda(self, mock_sys, mock_torch, mock_compat):
        runner = CliRunner()
        result = runner.invoke(engines, ["check", "vllm"])
        assert "not detected" in result.output
        assert "not installed or CPU-only" in result.output
