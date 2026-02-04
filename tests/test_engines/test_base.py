"""Tests for engine base classes."""

from datetime import datetime

from kitt.engines.base import EngineDiagnostics, GenerationMetrics, GenerationResult, InferenceEngine


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


class TestEngineDiagnostics:
    def test_creation_defaults(self):
        diag = EngineDiagnostics(available=True, engine_type="python_import")
        assert diag.available is True
        assert diag.engine_type == "python_import"
        assert diag.error is None
        assert diag.guidance is None

    def test_creation_full(self):
        diag = EngineDiagnostics(
            available=False,
            engine_type="http_server",
            error="Connection refused",
            guidance="Start the server",
        )
        assert diag.available is False
        assert diag.engine_type == "http_server"
        assert diag.error == "Connection refused"
        assert diag.guidance == "Start the server"


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

    def test_diagnose_available(self):
        """Base diagnose returns available when _check_dependencies returns True."""

        class AvailableEngine(InferenceEngine):
            @classmethod
            def name(cls):
                return "available"

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

        diag = AvailableEngine.diagnose()
        assert diag.available is True
        assert diag.engine_type == "python_import"
        assert diag.error is None

    def test_diagnose_unavailable(self):
        """Base diagnose returns unavailable when _check_dependencies returns False."""

        class UnavailableEngine(InferenceEngine):
            @classmethod
            def name(cls):
                return "unavailable"

            @classmethod
            def supported_formats(cls):
                return ["test"]

            @classmethod
            def _check_dependencies(cls):
                return False

            def initialize(self, model_path, config):
                pass

            def generate(self, prompt, **kwargs):
                pass

            def cleanup(self):
                pass

        diag = UnavailableEngine.diagnose()
        assert diag.available is False
        assert diag.error == "Dependency check failed"

    def test_diagnose_exception(self):
        """Base diagnose captures exceptions from _check_dependencies."""

        class BrokenEngine(InferenceEngine):
            @classmethod
            def name(cls):
                return "broken"

            @classmethod
            def supported_formats(cls):
                return ["test"]

            @classmethod
            def _check_dependencies(cls):
                raise RuntimeError("something went wrong")

            def initialize(self, model_path, config):
                pass

            def generate(self, prompt, **kwargs):
                pass

            def cleanup(self):
                pass

        diag = BrokenEngine.diagnose()
        assert diag.available is False
        assert "something went wrong" in diag.error
