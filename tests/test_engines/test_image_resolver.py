"""Tests for hardware-aware Docker image selection."""

from unittest.mock import patch

from kitt.engines.image_resolver import (
    clear_cache,
    get_supported_engines,
    has_hardware_overrides,
    resolve_image,
)


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
    def test_blackwell_gb10_llama_cpp_returns_spark(self, mock_cc):
        result = resolve_image("llama_cpp", "ghcr.io/ggml-org/llama.cpp:server-cuda")
        assert result == "llama.cpp:server-spark"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(10, 0))
    def test_blackwell_b200_llama_cpp_returns_spark(self, mock_cc):
        result = resolve_image("llama_cpp", "ghcr.io/ggml-org/llama.cpp:server-cuda")
        assert result == "llama.cpp:server-spark"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(8, 9))
    def test_ada_lovelace_llama_cpp_returns_default(self, mock_cc):
        result = resolve_image("llama_cpp", "ghcr.io/ggml-org/llama.cpp:server-cuda")
        assert result == "ghcr.io/ggml-org/llama.cpp:server-cuda"

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


class TestGetSupportedEngines:
    def test_returns_all_registered_engines(self):
        """All engines in _IMAGE_OVERRIDES should be returned."""
        engines = get_supported_engines()
        assert "vllm" in engines
        assert "tgi" in engines
        assert "llama_cpp" in engines
        assert "ollama" in engines

    def test_returns_list(self):
        engines = get_supported_engines()
        assert isinstance(engines, list)


class TestHasHardwareOverrides:
    def test_vllm_has_overrides(self):
        """vLLM has Blackwell overrides."""
        assert has_hardware_overrides("vllm") is True

    def test_tgi_no_overrides(self):
        """TGI currently has no hardware-specific overrides."""
        assert has_hardware_overrides("tgi") is False

    def test_llama_cpp_has_overrides(self):
        """llama.cpp has Blackwell overrides for ARM64+CUDA."""
        assert has_hardware_overrides("llama_cpp") is True

    def test_ollama_no_overrides(self):
        """Ollama currently has no hardware-specific overrides."""
        assert has_hardware_overrides("ollama") is False

    def test_unknown_engine_no_overrides(self):
        """Unknown engines have no overrides."""
        assert has_hardware_overrides("nonexistent_engine") is False


class TestFutureHardwareCompatibility:
    """Tests to ensure graceful handling of future/unknown hardware."""

    def setup_method(self):
        clear_cache()

    def teardown_method(self):
        clear_cache()

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(15, 0))
    def test_future_gpu_falls_back_to_highest_override(self, mock_cc):
        """A future GPU (cc 15.0) should match the highest available override."""
        result = resolve_image("vllm", "vllm/vllm-openai:latest")
        # Should match (10, 0) override since 15.0 >= 10.0
        assert result == "nvcr.io/nvidia/vllm:26.01-py3"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(15, 0))
    def test_future_gpu_llama_cpp_uses_spark(self, mock_cc):
        """A future GPU should match llama.cpp Blackwell override."""
        result = resolve_image("llama_cpp", "ghcr.io/ggml-org/llama.cpp:server-cuda")
        assert result == "llama.cpp:server-spark"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(15, 0))
    def test_future_gpu_tgi_returns_default(self, mock_cc):
        """TGI with future GPU returns default (no overrides)."""
        default = "ghcr.io/huggingface/text-generation-inference:latest"
        result = resolve_image("tgi", default)
        assert result == default

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(7, 5))
    def test_older_gpu_returns_default(self, mock_cc):
        """Older GPUs (Turing) return default image."""
        result = resolve_image("vllm", "vllm/vllm-openai:latest")
        assert result == "vllm/vllm-openai:latest"

    @patch("kitt.engines.image_resolver._detect_cc", return_value=(8, 6))
    def test_ampere_returns_default(self, mock_cc):
        """Ampere GPUs (RTX 30 series) return default image."""
        result = resolve_image("vllm", "vllm/vllm-openai:latest")
        assert result == "vllm/vllm-openai:latest"
