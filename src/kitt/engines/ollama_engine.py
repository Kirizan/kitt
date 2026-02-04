"""Ollama inference engine implementation — Docker container."""

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import GenerationMetrics, GenerationResult, InferenceEngine
from .registry import register_engine

logger = logging.getLogger(__name__)


@register_engine
class OllamaEngine(InferenceEngine):
    """Ollama inference engine running in a Docker container.

    Communicates via the Ollama HTTP API (/api/generate).
    Model pulling is handled via docker exec.
    """

    def __init__(self) -> None:
        self._container_id: Optional[str] = None
        self._base_url: str = ""
        self._model_name: str = ""

    @classmethod
    def name(cls) -> str:
        return "ollama"

    @classmethod
    def supported_formats(cls) -> List[str]:
        return ["gguf"]

    @classmethod
    def default_image(cls) -> str:
        return "ollama/ollama:latest"

    @classmethod
    def default_port(cls) -> int:
        return 11434

    @classmethod
    def container_port(cls) -> int:
        return 11434

    @classmethod
    def health_endpoint(cls) -> str:
        return "/api/tags"

    def initialize(self, model_path: str, config: Dict[str, Any]) -> None:
        """Start Ollama container, wait for healthy, and pull the model."""
        from .docker_manager import ContainerConfig, DockerManager

        self._model_name = model_path
        port = config.get("port", self.default_port())

        container_cfg = ContainerConfig(
            image=config.get("image", self.default_image()),
            port=port,
            container_port=self.container_port(),
            volumes=config.get("volumes", {}),
            env=config.get("env", {}),
            extra_args=config.get("extra_args", []),
            command_args=[],
        )
        self._container_id = DockerManager.run_container(container_cfg)

        health_url = f"http://localhost:{port}{self.health_endpoint()}"
        DockerManager.wait_for_healthy(
            health_url, container_id=self._container_id
        )
        self._base_url = f"http://localhost:{port}"

        # Pull the model inside the container
        logger.info(f"Pulling model '{self._model_name}' in Ollama container...")
        DockerManager.exec_in_container(
            self._container_id, ["ollama", "pull", self._model_name]
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
            "model": self._model_name,
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
            f"{self._base_url}/api/generate",
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
        """Stop and remove the Ollama container."""
        from .docker_manager import DockerManager

        if self._container_id:
            DockerManager.stop_container(self._container_id)
            self._container_id = None
