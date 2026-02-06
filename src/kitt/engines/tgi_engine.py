"""Text Generation Inference (HuggingFace TGI) engine implementation — Docker container."""

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import GenerationMetrics, GenerationResult, InferenceEngine
from .registry import register_engine

logger = logging.getLogger(__name__)


@register_engine
class TGIEngine(InferenceEngine):
    """HuggingFace Text Generation Inference engine running in a Docker container.

    Communicates via the HuggingFace /generate API.
    """

    def __init__(self) -> None:
        self._container_id: Optional[str] = None
        self._base_url: str = ""
        self._model_id: str = ""

    @classmethod
    def name(cls) -> str:
        return "tgi"

    @classmethod
    def supported_formats(cls) -> List[str]:
        return ["safetensors", "pytorch"]

    @classmethod
    def default_image(cls) -> str:
        return "ghcr.io/huggingface/text-generation-inference:latest"

    @classmethod
    def default_port(cls) -> int:
        return 8080

    @classmethod
    def container_port(cls) -> int:
        return 80

    @classmethod
    def health_endpoint(cls) -> str:
        return "/info"

    def initialize(self, model_path: str, config: Dict[str, Any]) -> None:
        """Start TGI container and wait for healthy."""
        from .docker_manager import ContainerConfig, DockerManager

        self._model_id = model_path
        port = config.get("port", self.default_port())

        # Determine if model_path is a local directory or a HuggingFace model ID
        model_abs = Path(model_path).resolve()
        volumes = {}
        cmd_args = []

        if model_abs.is_dir():
            model_name = model_abs.name
            volumes[str(model_abs)] = f"/models/{model_name}"
            cmd_args = ["--model-id", f"/models/{model_name}", "--port", str(port)]
        else:
            # Treat as HuggingFace model ID (e.g. "meta-llama/Llama-3-8B")
            cmd_args = ["--model-id", model_path, "--port", str(port)]

        container_cfg = ContainerConfig(
            image=config.get("image", self.resolved_image()),
            port=port,
            container_port=self.container_port(),
            volumes=volumes,
            env=config.get("env", {}),
            extra_args=config.get("extra_args", ["--shm-size=8g"]),
            command_args=cmd_args,
        )
        self._container_id = DockerManager.run_container(container_cfg)

        health_url = f"http://localhost:{port}{self.health_endpoint()}"
        startup_timeout = config.get("startup_timeout", 600.0)
        DockerManager.wait_for_healthy(
            health_url, timeout=startup_timeout, container_id=self._container_id
        )
        self._base_url = f"http://localhost:{port}"

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
            f"{self._base_url}/generate",
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
            ttft_ms=0,
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
        """Stop and remove the TGI container."""
        from .docker_manager import DockerManager

        if self._container_id:
            DockerManager.stop_container(self._container_id)
            self._container_id = None
