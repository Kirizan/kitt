"""Ollama inference engine implementation."""

import json
import logging
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Dict, List

from .base import EngineDiagnostics, GenerationMetrics, GenerationResult, InferenceEngine
from .registry import register_engine

logger = logging.getLogger(__name__)


@register_engine
class OllamaEngine(InferenceEngine):
    """Ollama inference engine via HTTP API.

    Communicates with a running Ollama server (default: localhost:11434).
    No special Python dependencies needed beyond stdlib.
    """

    def __init__(self) -> None:
        self.base_url: str = ""
        self.model_name: str = ""

    @classmethod
    def name(cls) -> str:
        return "ollama"

    @classmethod
    def supported_formats(cls) -> List[str]:
        return ["gguf"]

    @classmethod
    def diagnose(cls) -> EngineDiagnostics:
        """Check Ollama server connectivity with detailed error info."""
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read())
                model_count = len(data.get("models", []))
                return EngineDiagnostics(
                    available=True,
                    engine_type="http_server",
                    guidance=f"{model_count} model(s) available" if model_count else None,
                )
        except urllib.error.URLError:
            return EngineDiagnostics(
                available=False,
                engine_type="http_server",
                error="Cannot connect to Ollama server at localhost:11434",
                guidance="Start the server with: ollama serve",
            )
        except (TimeoutError, OSError) as e:
            return EngineDiagnostics(
                available=False,
                engine_type="http_server",
                error=f"Connection error: {e}",
                guidance="Start the server with: ollama serve",
            )

    @classmethod
    def _check_dependencies(cls) -> bool:
        # Ollama uses HTTP API - check if server is reachable
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2):
                return True
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def initialize(self, model_path: str, config: Dict[str, Any]) -> None:
        """Initialize Ollama engine connection.

        Args:
            model_path: Ollama model name (e.g., 'llama3', 'mistral').
            config: Must contain optional 'base_url' (default: http://localhost:11434).
        """
        self.base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
        self.model_name = model_path

        # Verify server is reachable and model exists
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                models = [m["name"] for m in data.get("models", [])]
                # Check if model is available (with or without :latest tag)
                model_found = any(
                    m == self.model_name or m.startswith(f"{self.model_name}:")
                    for m in models
                )
                if not model_found:
                    logger.warning(
                        f"Model '{self.model_name}' not found locally. "
                        f"Available: {models}. Ollama may pull it on first use."
                    )
        except (urllib.error.URLError, TimeoutError) as e:
            raise RuntimeError(
                f"Cannot connect to Ollama server at {self.base_url}: {e}"
            )

    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        top_p: float = 1.0,
        top_k: int = 50,
        max_tokens: int = 2048,
        **engine_specific_params: Any,
    ) -> GenerationResult:
        """Generate via Ollama HTTP API."""
        from kitt.collectors.gpu_stats import GPUMemoryTracker

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "num_predict": max_tokens,
            },
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        with GPUMemoryTracker(gpu_index=0) as tracker:
            start_time = time.perf_counter()
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read())
            end_time = time.perf_counter()

        total_latency_ms = (end_time - start_time) * 1000

        output = result.get("response", "")
        prompt_tokens = result.get("prompt_eval_count", 0)
        completion_tokens = result.get("eval_count", 0)

        # Ollama provides eval_duration in nanoseconds
        eval_duration_ns = result.get("eval_duration", 0)
        if eval_duration_ns > 0 and completion_tokens > 0:
            tps = completion_tokens / (eval_duration_ns / 1e9)
        elif total_latency_ms > 0 and completion_tokens > 0:
            tps = completion_tokens / (total_latency_ms / 1000)
        else:
            tps = 0

        # TTFT from Ollama's prompt eval timing
        prompt_eval_duration_ns = result.get("prompt_eval_duration", 0)
        ttft_ms = prompt_eval_duration_ns / 1e6 if prompt_eval_duration_ns > 0 else 0

        metrics = GenerationMetrics(
            ttft_ms=ttft_ms,
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
        """No cleanup needed for HTTP client."""
        pass
