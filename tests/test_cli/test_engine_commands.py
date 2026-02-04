"""Tests for engine CLI commands (setup, enhanced check, and diagnostics)."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kitt.cli.engine_commands import engines
from kitt.engines.base import EngineDiagnostics
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
        # Torch fixup: --force-reinstall --no-deps should appear at least
        # twice (initial install + fixup after dep resolution)
        force_lines = [
            line for line in result.output.splitlines()
            if "--force-reinstall" in line and "--no-deps" in line and "torch" in line
        ]
        assert len(force_lines) >= 2, (
            f"Expected at least 2 torch --force-reinstall --no-deps lines, got {len(force_lines)}"
        )

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="12.6")
    def test_dry_run_cuda12(self, mock_cuda):
        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "--dry-run", "vllm"])
        assert result.exit_code == 0
        assert "cu120" in result.output

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    @patch("kitt.cli.engine_commands.subprocess")
    def test_verify_failure_shows_cuda_compat_guidance(self, mock_subprocess, mock_cuda):
        """When install succeeds but import fails with libcudart, show compat guidance."""
        install_result = MagicMock(returncode=0)
        verify_result = MagicMock(
            returncode=1,
            stdout="",
            stderr="libcudart.so.12: cannot open shared object file",
        )
        mock_subprocess.run = MagicMock(
            side_effect=[
                install_result, install_result,  # force-reinstall --no-deps
                install_result, install_result,  # dep installs
                install_result,                  # torch fixup
                verify_result,                   # verification
            ]
        )

        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code != 0
        assert "import failed" in result.output
        assert "CUDA 12" in result.output
        assert "cuda-compat-12" in result.output
        assert "--no-binary" in result.output

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    @patch("kitt.cli.engine_commands.subprocess")
    def test_verify_cuda_init_failure(self, mock_subprocess, mock_cuda):
        """Exit code 2 from verification means CUDA init failed."""
        install_result = MagicMock(returncode=0)
        verify_result = MagicMock(
            returncode=2,
            stdout="torch_cuda=13.0\n",
            stderr="libcudart.so.12: cannot open shared object file",
        )
        mock_subprocess.run = MagicMock(
            side_effect=[
                install_result, install_result,  # force-reinstall --no-deps
                install_result, install_result,  # dep installs
                install_result,                  # torch fixup
                verify_result,                   # verification
            ]
        )

        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code != 0
        assert "CUDA initialization failed" in result.output
        assert "PyTorch CUDA: 13.0" in result.output

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    @patch("kitt.cli.engine_commands.subprocess")
    def test_verify_success_shows_details(self, mock_subprocess, mock_cuda):
        """Successful verification shows torch CUDA version and GPU name."""
        install_result = MagicMock(returncode=0)
        verify_result = MagicMock(
            returncode=0,
            stdout="torch_cuda=13.0\ndevice=NVIDIA GH200\nok\n",
            stderr="",
        )
        mock_subprocess.run = MagicMock(
            side_effect=[
                install_result, install_result,  # force-reinstall --no-deps
                install_result, install_result,  # dep installs
                install_result,                  # torch fixup
                verify_result,                   # verification
            ]
        )

        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code == 0
        assert "setup complete" in result.output
        assert "PyTorch CUDA: 13.0" in result.output
        assert "GPU: NVIDIA GH200" in result.output

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    @patch("kitt.cli.engine_commands.subprocess")
    def test_torch_fixup_runs_after_deps(self, mock_subprocess, mock_cuda):
        """The 5th subprocess call is torch --force-reinstall --no-deps with correct index."""
        install_result = MagicMock(returncode=0)
        verify_result = MagicMock(
            returncode=0,
            stdout="torch_cuda=13.0\nok\n",
            stderr="",
        )
        mock_subprocess.run = MagicMock(
            side_effect=[
                install_result, install_result,  # force-reinstall --no-deps
                install_result, install_result,  # dep installs
                install_result,                  # torch fixup
                verify_result,                   # verification
            ]
        )

        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code == 0

        # The 5th call (index 4) should be the torch fixup
        fixup_call = mock_subprocess.run.call_args_list[4]
        fixup_cmd = fixup_call[0][0]  # positional arg
        assert "torch" in fixup_cmd
        assert "--force-reinstall" in fixup_cmd
        assert "--no-deps" in fixup_cmd
        assert any("cu130" in arg for arg in fixup_cmd)

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    @patch("kitt.cli.engine_commands.subprocess")
    def test_pip_stdout_suppressed_by_default(self, mock_subprocess, mock_cuda):
        """Pip stdout is sent to DEVNULL when --verbose is not passed."""
        install_result = MagicMock(returncode=0)
        verify_result = MagicMock(
            returncode=0,
            stdout="torch_cuda=13.0\nok\n",
            stderr="",
        )
        mock_subprocess.run = MagicMock(
            side_effect=[
                install_result, install_result,
                install_result, install_result,
                install_result,
                verify_result,
            ]
        )

        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code == 0

        # All pip install calls (indices 0-4) should pass stdout=DEVNULL
        for i in range(5):
            call_kwargs = mock_subprocess.run.call_args_list[i][1]
            assert call_kwargs.get("stdout") == mock_subprocess.DEVNULL

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    @patch("kitt.cli.engine_commands.subprocess")
    def test_pip_stdout_shown_with_verbose(self, mock_subprocess, mock_cuda):
        """Pip stdout is not suppressed when --verbose is passed."""
        install_result = MagicMock(returncode=0)
        verify_result = MagicMock(
            returncode=0,
            stdout="torch_cuda=13.0\nok\n",
            stderr="",
        )
        mock_subprocess.run = MagicMock(
            side_effect=[
                install_result, install_result,
                install_result, install_result,
                install_result,
                verify_result,
            ]
        )

        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "--verbose", "vllm"])
        assert result.exit_code == 0

        # All pip install calls (indices 0-4) should pass stdout=None
        for i in range(5):
            call_kwargs = mock_subprocess.run.call_args_list[i][1]
            assert call_kwargs.get("stdout") is None

    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    @patch("kitt.cli.engine_commands.subprocess")
    def test_verify_non_cuda_failure(self, mock_subprocess, mock_cuda):
        """Exit code 1 with non-CUDA error shows raw error text."""
        install_result = MagicMock(returncode=0)
        verify_result = MagicMock(
            returncode=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'vllm'",
        )
        mock_subprocess.run = MagicMock(
            side_effect=[
                install_result, install_result,
                install_result, install_result,
                install_result,
                verify_result,
            ]
        )

        runner = CliRunner()
        result = runner.invoke(engines, ["setup", "vllm"])
        assert result.exit_code != 0
        assert "import failed" in result.output
        assert "ModuleNotFoundError" in result.output


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


class TestCheckEngineDiagnose:
    def test_check_shows_import_error_and_guidance(self):
        """check command displays diagnose error and guidance for import-based engines."""
        diag = EngineDiagnostics(
            available=False,
            engine_type="python_import",
            error="vllm is not installed",
            guidance="pip install vllm\nOr: poetry install -E vllm",
        )

        with patch(
            "kitt.engines.vllm_engine.VLLMEngine.diagnose", return_value=diag
        ):
            runner = CliRunner()
            result = runner.invoke(engines, ["check", "vllm"])
        assert "Import check" in result.output
        assert "Not Available" in result.output
        assert "vllm is not installed" in result.output
        assert "Suggested fix:" in result.output
        assert "pip install vllm" in result.output

    def test_check_shows_server_error(self):
        """check command displays diagnose error and guidance for server-based engines."""
        diag = EngineDiagnostics(
            available=False,
            engine_type="http_server",
            error="Cannot connect to Ollama server at localhost:11434",
            guidance="Start the server with: ollama serve",
        )

        with patch(
            "kitt.engines.ollama_engine.OllamaEngine.diagnose", return_value=diag
        ):
            runner = CliRunner()
            result = runner.invoke(engines, ["check", "ollama"])
        assert "Server check" in result.output
        assert "Not Available" in result.output
        assert "Cannot connect" in result.output
        assert "ollama serve" in result.output

    def test_check_shows_available_with_info(self):
        """check command displays available status with optional info."""
        diag = EngineDiagnostics(
            available=True,
            engine_type="http_server",
            guidance="2 model(s) available",
        )

        with patch(
            "kitt.engines.ollama_engine.OllamaEngine.diagnose", return_value=diag
        ):
            runner = CliRunner()
            result = runner.invoke(engines, ["check", "ollama"])
        assert "Server check" in result.output
        assert "Available" in result.output
        assert "2 model(s) available" in result.output
