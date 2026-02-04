"""vLLM inference engine implementation — Docker + OpenAI-compatible API."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import GenerationResult, InferenceEngine
from .registry import register_engine

logger = logging.getLogger(__name__)


@register_engine
class VLLMEngine(InferenceEngine):
    """vLLM inference engine running in a Docker container.

    Communicates via the OpenAI-compatible /v1/completions API.
    """

    def __init__(self) -> None:
        self._container_id: Optional[str] = None
        self._base_url: str = ""
        self._model_name: str = ""

    @classmethod
    def name(cls) -> str:
        return "vllm"

    @classmethod
    def supported_formats(cls) -> List[str]:
        return ["safetensors", "pytorch"]

    @classmethod
    def default_image(cls) -> str:
        return "vllm/vllm-openai:latest"

    @classmethod
    def default_port(cls) -> int:
        return 8000

    @classmethod
    def container_port(cls) -> int:
        return 8000

    @classmethod
    def health_endpoint(cls) -> str:
        return "/health"

    def initialize(self, model_path: str, config: Dict[str, Any]) -> None:
        """Start vLLM container and wait for healthy."""
        from .docker_manager import ContainerConfig, DockerManager

        model_abs = str(Path(model_path).resolve())
        self._model_name = Path(model_path).name
        port = config.get("port", self.default_port())

        cmd_args = ["--model", f"/models/{self._model_name}"]
        if config.get("tensor_parallel_size", 1) > 1:
            cmd_args += [
                "--tensor-parallel-size",
                str(config["tensor_parallel_size"]),
            ]
        if "gpu_memory_utilization" in config:
            cmd_args += [
                "--gpu-memory-utilization",
                str(config["gpu_memory_utilization"]),
            ]

        container_cfg = ContainerConfig(
            image=config.get("image", self.default_image()),
            port=port,
            container_port=self.container_port(),
            volumes={model_abs: f"/models/{self._model_name}"},
            env=config.get("env", {}),
            extra_args=config.get("extra_args", ["--shm-size=8g"]),
            command_args=cmd_args,
        )
        self._container_id = DockerManager.run_container(container_cfg)

        health_url = f"http://localhost:{port}{self.health_endpoint()}"
        DockerManager.wait_for_healthy(
            health_url, container_id=self._container_id
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
        """Generate via OpenAI-compatible API."""
        from kitt.collectors.gpu_stats import GPUMemoryTracker

        from .openai_compat import openai_generate, parse_openai_result

        with GPUMemoryTracker(gpu_index=0) as tracker:
            start = time.perf_counter()
            response = openai_generate(
                self._base_url,
                prompt,
                model=self._model_name,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

        return parse_openai_result(response, elapsed_ms, tracker)

    def cleanup(self) -> None:
        """Stop and remove the vLLM container."""
        from .docker_manager import DockerManager

        if self._container_id:
            DockerManager.stop_container(self._container_id)
            self._container_id = None
