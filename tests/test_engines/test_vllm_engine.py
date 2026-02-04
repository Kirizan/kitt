"""Tests for vLLM engine CUDA mismatch handling."""

from unittest.mock import patch

from kitt.hardware.detector import CudaMismatchInfo


class TestVLLMCudaGuidance:
    def _get_engine_cls(self):
        from kitt.engines.vllm_engine import VLLMEngine

        return VLLMEngine

    @patch(
        "kitt.hardware.detector.check_cuda_compatibility",
        return_value=CudaMismatchInfo(
            system_cuda="13.0",
            torch_cuda="12.4",
            system_major=13,
            torch_major=12,
        ),
    )
    def test_returns_guidance_on_torch_mismatch(self, mock_check):
        cls = self._get_engine_cls()
        guidance = cls._cuda_guidance()
        assert guidance is not None
        assert "CUDA version mismatch" in guidance
        assert "cu130" in guidance
        assert "--force-reinstall" in guidance
        assert "kitt engines setup vllm" in guidance

    @patch("kitt.hardware.detector.check_cuda_compatibility", return_value=None)
    @patch("kitt.hardware.detector.detect_cuda_version", return_value=None)
    def test_returns_none_when_no_cuda(self, mock_sys, mock_check):
        cls = self._get_engine_cls()
        guidance = cls._cuda_guidance()
        assert guidance is None

    @patch("kitt.hardware.detector.check_cuda_compatibility", return_value=None)
    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    def test_returns_guidance_on_library_mismatch(self, mock_sys, mock_check):
        """When torch matches system but vllm needs a different CUDA runtime."""
        cls = self._get_engine_cls()
        error = "libcudart.so.12: cannot open shared object file"
        guidance = cls._cuda_guidance(error)
        assert guidance is not None
        assert "CUDA 12" in guidance
        assert "CUDA 13" in guidance
        assert "cuda-compat-12" in guidance
        assert "--no-binary" in guidance

    @patch("kitt.hardware.detector.check_cuda_compatibility", return_value=None)
    @patch("kitt.hardware.detector.detect_cuda_version", return_value="12.4")
    def test_returns_none_when_library_matches_system(self, mock_sys, mock_check):
        """No guidance when the library version matches system CUDA."""
        cls = self._get_engine_cls()
        error = "libcudart.so.12: cannot open shared object file"
        guidance = cls._cuda_guidance(error)
        assert guidance is None


class TestVLLMCheckDependencies:
    def _get_engine_cls(self):
        from kitt.engines.vllm_engine import VLLMEngine

        return VLLMEngine

    @patch.dict("sys.modules", {"vllm": None})
    def test_module_not_found_returns_false(self):
        cls = self._get_engine_cls()
        assert cls._check_dependencies() is False

    @patch(
        "kitt.engines.vllm_engine.VLLMEngine._cuda_guidance",
        return_value="mismatch guidance here",
    )
    def test_libcudart_import_error_triggers_guidance(self, mock_guidance):
        cls = self._get_engine_cls()

        with patch.dict("sys.modules", {"vllm": None}):
            import sys

            del sys.modules["vllm"]

            with patch("builtins.__import__", side_effect=ImportError(
                "libcudart.so.12: cannot open shared object file"
            )):
                result = cls._check_dependencies()

        assert result is False
        mock_guidance.assert_called()
