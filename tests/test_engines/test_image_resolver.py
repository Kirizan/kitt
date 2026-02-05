"""Tests for hardware-aware Docker image selection."""

from unittest.mock import patch

from kitt.engines.image_resolver import clear_cache, resolve_image


class TestResolveImage:
    def setup_method(self):
        clear_cache()

    def teardown_method(self):
        clear_cache()

    @patch("kitt.engines.image_resolver._detect_cc", return_value=None)
    def test_no_gpu_returns_default(self, mock_cc):
        result = resolve_image("vllm", "vllm/vllm-openai:latest")
        assert result == "vllm/vllm-openai:latest"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(8, 9))
    def test_ada_lovelace_returns_default(self, mock_cc):
        result = resolve_image("vllm", "vllm/vllm-openai:latest")
        assert result == "vllm/vllm-openai:latest"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(9, 0))
    def test_hopper_returns_default(self, mock_cc):
        result = resolve_image("vllm", "vllm/vllm-openai:latest")
        assert result == "vllm/vllm-openai:latest"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(10, 0))
    def test_blackwell_b200_returns_ngc(self, mock_cc):
        result = resolve_image("vllm", "vllm/vllm-openai:latest")
        assert result == "nvcr.io/nvidia/vllm:26.01-py3"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(12, 0))
    def test_blackwell_rtx5090_returns_ngc(self, mock_cc):
        result = resolve_image("vllm", "vllm/vllm-openai:latest")
        assert result == "nvcr.io/nvidia/vllm:26.01-py3"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(12, 1))
    def test_blackwell_gb10_returns_ngc(self, mock_cc):
        result = resolve_image("vllm", "vllm/vllm-openai:latest")
        assert result == "nvcr.io/nvidia/vllm:26.01-py3"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(12, 1))
    def test_tgi_blackwell_returns_default(self, mock_cc):
        """TGI has no Blackwell overrides, so default is returned."""
        default = "ghcr.io/huggingface/text-generation-inference:latest"
        result = resolve_image("tgi", default)
        assert result == default

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(12, 1))
    def test_unknown_engine_returns_default(self, mock_cc):
        result = resolve_image("unknown_engine", "some/image:latest")
        assert result == "some/image:latest"


class TestClearCache:
    def test_clear_allows_redetection(self):
        """After clear, the next call re-detects compute capability."""
        with patch(
            "kitt.engines.image_resolver._detect_cc", return_value=(12, 1)
        ):
            result1 = resolve_image("vllm", "vllm/vllm-openai:latest")
            assert result1 == "nvcr.io/nvidia/vllm:26.01-py3"

        clear_cache()

        with patch(
            "kitt.engines.image_resolver._detect_cc", return_value=None
        ):
            result2 = resolve_image("vllm", "vllm/vllm-openai:latest")
            assert result2 == "vllm/vllm-openai:latest"
