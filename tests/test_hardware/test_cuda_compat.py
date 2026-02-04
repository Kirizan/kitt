"""Tests for CUDA compatibility detection."""

from unittest.mock import MagicMock, patch

from kitt.hardware.detector import (
    CudaMismatchInfo,
    check_cuda_compatibility,
    detect_torch_cuda_version,
)


class TestDetectTorchCudaVersion:
    @patch.dict("sys.modules", {"torch": MagicMock()})
    def test_returns_cuda_version(self):
        import sys

        mock_torch = sys.modules["torch"]
        mock_torch.version.cuda = "12.4"
        result = detect_torch_cuda_version()
        assert result == "12.4"

    @patch.dict("sys.modules", {"torch": MagicMock()})
    def test_returns_none_when_cpu_only(self):
        import sys

        mock_torch = sys.modules["torch"]
        mock_torch.version.cuda = None
        result = detect_torch_cuda_version()
        assert result is None

    def test_returns_none_when_torch_not_installed(self):
        with patch.dict("sys.modules", {"torch": None}):
            result = detect_torch_cuda_version()
            assert result is None


class TestCheckCudaCompatibility:
    @patch("kitt.hardware.detector.detect_torch_cuda_version", return_value="12.4")
    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    def test_detects_mismatch(self, mock_sys, mock_torch):
        result = check_cuda_compatibility()
        assert result is not None
        assert isinstance(result, CudaMismatchInfo)
        assert result.system_cuda == "13.0"
        assert result.torch_cuda == "12.4"
        assert result.system_major == 13
        assert result.torch_major == 12

    @patch("kitt.hardware.detector.detect_torch_cuda_version", return_value="13.1")
    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    def test_no_mismatch_same_major(self, mock_sys, mock_torch):
        result = check_cuda_compatibility()
        assert result is None

    @patch("kitt.hardware.detector.detect_torch_cuda_version", return_value="12.4")
    @patch("kitt.hardware.detector.detect_cuda_version", return_value=None)
    def test_no_system_cuda(self, mock_sys, mock_torch):
        result = check_cuda_compatibility()
        assert result is None

    @patch("kitt.hardware.detector.detect_torch_cuda_version", return_value=None)
    @patch("kitt.hardware.detector.detect_cuda_version", return_value="13.0")
    def test_no_torch(self, mock_sys, mock_torch):
        result = check_cuda_compatibility()
        assert result is None

    @patch("kitt.hardware.detector.detect_torch_cuda_version", return_value="12.1")
    @patch("kitt.hardware.detector.detect_cuda_version", return_value="12.4")
    def test_same_major_different_minor(self, mock_sys, mock_torch):
        result = check_cuda_compatibility()
        assert result is None
