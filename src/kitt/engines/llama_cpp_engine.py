"""llama.cpp inference engine implementation."""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

from .base import GenerationMetrics, GenerationResult, InferenceEngine
from .registry import register_engine

logger = logging.getLogger(__name__)


@register_engine
class LlamaCppEngine(InferenceEngine):
    """llama.cpp inference engine via llama-cpp-python bindings."""

    def __init__(self) -> None:
        self.llm = None

    @classmethod
    def name(cls) -> str:
        return "llama_cpp"

    @classmethod
    def supported_formats(cls) -> List[str]:
        return ["gguf"]

    @classmethod
    def _check_dependencies(cls) -> bool:
        try:
            import llama_cpp  # noqa: F401

            return True
        except ImportError:
            return False

    def initialize(self, model_path: str, config: Dict[str, Any]) -> None:
        """Initialize llama.cpp engine.

        Args:
            model_path: Path to GGUF model file.
            config: Engine-specific configuration.
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            raise RuntimeError(
                "llama-cpp-python not installed. "
                "Install with: pip install llama-cpp-python"
            )

        n_ctx = config.get("n_ctx", 4096)
        n_gpu_layers = config.get("n_gpu_layers", -1)  # -1 = all layers on GPU
        n_threads = config.get("n_threads", None)

        kwargs: Dict[str, Any] = {
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu_layers,
            "verbose": config.get("verbose", False),
        }
        if n_threads is not None:
            kwargs["n_threads"] = n_threads

        self.llm = Llama(**kwargs)

    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        top_p: float = 1.0,
        top_k: int = 50,
        max_tokens: int = 2048,
        **engine_specific_params: Any,
    ) -> GenerationResult:
        """Generate with llama.cpp."""
        from kitt.collectors.gpu_stats import GPUMemoryTracker

        with GPUMemoryTracker(gpu_index=0) as tracker:
            start_time = time.perf_counter()
            result = self.llm(
                prompt,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
            )
            end_time = time.perf_counter()

        total_latency_ms = (end_time - start_time) * 1000

        output = result["choices"][0]["text"]
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        tps = (
            completion_tokens / (total_latency_ms / 1000)
            if total_latency_ms > 0
            else 0
        )

        metrics = GenerationMetrics(
            ttft_ms=0,  # TODO: Extract TTFT from llama.cpp timings
            tps=tps,
            total_latency_ms=total_latency_ms,
            gpu_memory_peak_gb=tracker.get_peak_memory_mb() / 1024,
            gpu_memory_avg_gb=tracker.get_average_memory_mb() / 1024,
            timestamp=datetime.now(),
        )

        return GenerationResult(
            output=output,
            metrics=metrics,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def cleanup(self) -> None:
        """Cleanup llama.cpp resources."""
        if self.llm is not None:
            del self.llm
            self.llm = None

    def translate_params(self, universal_params: Dict[str, Any]) -> Dict[str, Any]:
        """Translate universal params to llama.cpp params."""
        translated = universal_params.copy()
        # llama.cpp uses 'max_tokens' same as universal
        return translated
