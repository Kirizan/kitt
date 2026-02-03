"""Text Generation Inference (HuggingFace TGI) engine implementation."""

import json
import logging
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Dict, List

from .base import GenerationMetrics, GenerationResult, InferenceEngine
from .registry import register_engine

logger = logging.getLogger(__name__)


@register_engine
class TGIEngine(InferenceEngine):
    """HuggingFace Text Generation Inference engine.

    Communicates with a running TGI server via HTTP API.
    """

    def __init__(self) -> None:
        self.base_url: str = ""
        self.model_id: str = ""

    @classmethod
    def name(cls) -> str:
        return "tgi"

    @classmethod
    def supported_formats(cls) -> List[str]:
        return ["safetensors", "pytorch"]

    @classmethod
    def _check_dependencies(cls) -> bool:
        # TGI is a server - check if it's reachable
        # For registration purposes, always return True since it's HTTP-based
        return True

    def initialize(self, model_path: str, config: Dict[str, Any]) -> None:
        """Initialize TGI engine connection.

        Args:
            model_path: Model identifier (for reference only; model is loaded by TGI server).
            config: Must contain 'base_url' for TGI server (default: http://localhost:8080).
        """
        self.base_url = config.get("base_url", "http://localhost:8080").rstrip("/")
        self.model_id = model_path

        # Verify server is reachable
        try:
            req = urllib.request.Request(f"{self.base_url}/info")
            with urllib.request.urlopen(req, timeout=5) as response:
                info = json.loads(response.read())
                logger.info(f"Connected to TGI server: {info.get('model_id', 'unknown')}")
        except (urllib.error.URLError, TimeoutError) as e:
            raise RuntimeError(
                f"Cannot connect to TGI server at {self.base_url}: {e}"
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
        """Generate via TGI HTTP API."""
        from kitt.collectors.gpu_stats import GPUMemoryTracker

        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature if temperature > 0 else None,
                "top_p": top_p,
                "top_k": top_k,
                "max_new_tokens": max_tokens,
                "details": True,
            },
        }
        # Remove None values
        payload["parameters"] = {
            k: v for k, v in payload["parameters"].items() if v is not None
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        with GPUMemoryTracker(gpu_index=0) as tracker:
            start_time = time.perf_counter()
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read())
            end_time = time.perf_counter()

        total_latency_ms = (end_time - start_time) * 1000

        generated_text = result.get("generated_text", "")
        details = result.get("details", {})

        prompt_tokens = details.get("prefill", [{}])
        prompt_token_count = len(prompt_tokens) if isinstance(prompt_tokens, list) else 0
        completion_tokens = details.get("generated_tokens", 0)

        tps = (
            completion_tokens / (total_latency_ms / 1000)
            if total_latency_ms > 0
            else 0
        )

        metrics = GenerationMetrics(
            ttft_ms=0,  # TODO: Extract from TGI response timing
            tps=tps,
            total_latency_ms=total_latency_ms,
            gpu_memory_peak_gb=tracker.get_peak_memory_mb() / 1024,
            gpu_memory_avg_gb=tracker.get_average_memory_mb() / 1024,
            timestamp=datetime.now(),
        )

        return GenerationResult(
            output=generated_text,
            metrics=metrics,
            prompt_tokens=prompt_token_count,
            completion_tokens=completion_tokens,
        )

    def cleanup(self) -> None:
        """No cleanup needed for HTTP client."""
        pass
