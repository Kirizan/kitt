"""llama.cpp inference engine implementation — Docker + OpenAI-compatible API."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import GenerationResult, InferenceEngine
from .registry import register_engine

logger = logging.getLogger(__name__)


@register_engine
class LlamaCppEngine(InferenceEngine):
    """llama.cpp inference engine running in a Docker container.

    Uses the llama.cpp server image which exposes an OpenAI-compatible API.
    """

    def __init__(self) -> None:
        self._container_id: Optional[str] = None
        self._base_url: str = ""
        self._model_name: str = ""

    @classmethod
    def name(cls) -> str:
        return "llama_cpp"

    @classmethod
    def supported_formats(cls) -> List[str]:
        return ["gguf"]

    @classmethod
    def default_image(cls) -> str:
        return "ghcr.io/ggml-org/llama.cpp:server-cuda"

    @classmethod
    def default_port(cls) -> int:
        return 8081

    @classmethod
    def container_port(cls) -> int:
        return 8080

    @classmethod
    def health_endpoint(cls) -> str:
        return "/health"

    def initialize(self, model_path: str, config: Dict[str, Any]) -> None:
        """Start llama.cpp server container and wait for healthy."""
        from .docker_manager import ContainerConfig, DockerManager

        model_abs = str(Path(model_path).resolve())
        model_basename = Path(model_path).name
        # Use full container path for consistency (llama.cpp serves single model)
        self._model_name = f"/models/{model_basename}"
        port = config.get("port", self.default_port())

        n_gpu_layers = config.get("n_gpu_layers", -1)
        n_ctx = config.get("n_ctx", 4096)

        cmd_args = [
            "-m", self._model_name,
            "--n-gpu-layers", str(n_gpu_layers),
            "-c", str(n_ctx),
            "--host", "0.0.0.0",
            "--port", str(self.container_port()),
        ]

        # Mount the model file's parent directory
        model_dir = str(Path(model_abs).parent)

        container_cfg = ContainerConfig(
            image=config.get("image", self.resolved_image()),
            port=port,
            container_port=self.container_port(),
            volumes={model_dir: "/models"},
            env=config.get("env", {}),
            extra_args=config.get("extra_args", []),
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
                top_k=top_k,
                max_tokens=max_tokens,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

        return parse_openai_result(response, elapsed_ms, tracker)

    def cleanup(self) -> None:
        """Stop and remove the llama.cpp container."""
        from .docker_manager import DockerManager

        if self._container_id:
            DockerManager.stop_container(self._container_id)
            self._container_id = None
