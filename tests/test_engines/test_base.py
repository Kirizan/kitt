"""Tests for engine base classes."""

from datetime import datetime

from kitt.engines.base import GenerationMetrics, GenerationResult, InferenceEngine


class TestGenerationMetrics:
    def test_creation(self):
        metrics = GenerationMetrics(
            ttft_ms=50.0,
            tps=30.0,
            total_latency_ms=1000.0,
            gpu_memory_peak_gb=4.5,
            gpu_memory_avg_gb=3.8,
            timestamp=datetime.now(),
        )
        assert metrics.ttft_ms == 50.0
        assert metrics.tps == 30.0
        assert metrics.total_latency_ms == 1000.0


class TestGenerationResult:
    def test_creation(self):
        metrics = GenerationMetrics(
            ttft_ms=50.0,
            tps=30.0,
            total_latency_ms=1000.0,
            gpu_memory_peak_gb=4.5,
            gpu_memory_avg_gb=3.8,
            timestamp=datetime.now(),
        )
        result = GenerationResult(
            output="Hello world",
            metrics=metrics,
            prompt_tokens=10,
            completion_tokens=5,
        )
        assert result.output == "Hello world"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 5


class TestInferenceEngineABC:
    def test_cannot_instantiate_directly(self):
        """InferenceEngine cannot be instantiated directly."""
        import pytest

        with pytest.raises(TypeError):
            InferenceEngine()

    def test_translate_params_default(self):
        """Default translate_params returns input unchanged."""

        # Create a minimal concrete subclass for testing
        class DummyEngine(InferenceEngine):
            @classmethod
            def name(cls):
                return "dummy"

            @classmethod
            def supported_formats(cls):
                return ["test"]

            @classmethod
            def _check_dependencies(cls):
                return True

            def initialize(self, model_path, config):
                pass

            def generate(self, prompt, **kwargs):
                pass

            def cleanup(self):
                pass

        engine = DummyEngine()
        params = {"temperature": 0.5, "max_tokens": 100}
        assert engine.translate_params(params) == params
