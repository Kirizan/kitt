"""Tests for vLLM engine CUDA mismatch handling."""

from unittest.mock import patch

from kitt.hardware.detector import CudaMismatchInfo


class TestVLLMCudaMismatchGuidance:
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
    def test_returns_guidance_on_mismatch(self, mock_check):
        cls = self._get_engine_cls()
        guidance = cls._cuda_mismatch_guidance()
        assert guidance is not None
        assert "CUDA version mismatch" in guidance
        assert "cu130" in guidance
        assert "kitt engines setup vllm" in guidance

    @patch("kitt.hardware.detector.check_cuda_compatibility", return_value=None)
    def test_returns_none_when_no_mismatch(self, mock_check):
        cls = self._get_engine_cls()
        guidance = cls._cuda_mismatch_guidance()
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
        "kitt.engines.vllm_engine.VLLMEngine._cuda_mismatch_guidance",
        return_value="mismatch guidance here",
    )
    def test_libcudart_import_error_triggers_guidance(self, mock_guidance):
        cls = self._get_engine_cls()

        def raise_import_error():
            raise ImportError("libcudart.so.12: cannot open shared object file")

        with patch.dict("sys.modules", {"vllm": None}):
            # Remove the None entry so import triggers our side effect
            import sys

            del sys.modules["vllm"]

            with patch("builtins.__import__", side_effect=ImportError(
                "libcudart.so.12: cannot open shared object file"
            )):
                result = cls._check_dependencies()

        assert result is False
        mock_guidance.assert_called()
