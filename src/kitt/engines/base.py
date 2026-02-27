"""Abstract base class for inference engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class GenerationMetrics:
    """Metrics collected during generation."""

    ttft_ms: float  # Time to first token
    tps: float  # Tokens per second
    total_latency_ms: float
    gpu_memory_peak_gb: float
    gpu_memory_avg_gb: float
    timestamp: datetime


@dataclass
class GenerationResult:
    """Result from a generation call."""

    output: str
    metrics: GenerationMetrics
    prompt_tokens: int
    completion_tokens: int


@dataclass
class EngineDiagnostics:
    """Structured diagnostics from an engine availability check."""

    available: bool
    image: str = ""
    error: str | None = None
    guidance: str | None = None


class InferenceEngine(ABC):
    """Abstract base class for inference engines.

    All engines run inside Docker containers and communicate via HTTP APIs.
    """

    _container_id: str | None = None

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """Engine identifier (e.g., 'vllm', 'tgi')."""

    @classmethod
    @abstractmethod
    def supported_formats(cls) -> list[str]:
        """Model formats this engine supports (e.g., ['safetensors', 'pytorch'])."""

    @classmethod
    @abstractmethod
    def default_image(cls) -> str:
        """Default Docker image for this engine."""

    @classmethod
    @abstractmethod
    def default_port(cls) -> int:
        """Default host port for this engine's container."""

    @classmethod
    @abstractmethod
    def container_port(cls) -> int:
        """Port the engine listens on inside the container."""

    @classmethod
    @abstractmethod
    def health_endpoint(cls) -> str:
        """Health check URL path (e.g. '/health')."""

    @classmethod
    def resolved_image(cls) -> str:
        """Return the best Docker image for this engine on the current GPU.

        Uses hardware detection to select an optimized image when available
        (e.g. NGC containers for Blackwell GPUs), falling back to the
        default image otherwise.
        """
        from .image_resolver import resolve_image

        return resolve_image(cls.name(), cls.default_image())

    @classmethod
    def setup(cls) -> None:
        """Pull or build the Docker image for this engine.

        Uses the build recipe for KITT-managed images, or pulls from the
        registry for standard images.  Passes ``--platform linux/{arch}``
        to ensure the correct manifest is selected on multi-arch registries.

        Raises:
            RuntimeError: If Docker is not available or pull/build fails.
        """
        from .docker_manager import DockerManager
        from .image_resolver import _detect_arch, get_build_recipe

        if not DockerManager.is_docker_available():
            raise RuntimeError("Docker is not installed or not running")

        image = cls.resolved_image()
        recipe = get_build_recipe(image)
        arch = _detect_arch()
        docker_platform = f"linux/{arch}" if arch else None

        if recipe is not None:
            DockerManager.build_image(
                image=image,
                dockerfile=str(recipe.dockerfile_path),
                context_dir=str(recipe.dockerfile_path.parent),
                target=recipe.target,
                build_args=recipe.build_args,
                platform=docker_platform,
            )
        else:
            DockerManager.pull_image(image, platform=docker_platform)

    @classmethod
    def validate_model(cls, model_path: str) -> str | None:
        """Check if a model's format is compatible with this engine.

        Returns:
            Error string if the model is incompatible, None if OK.
        """
        from kitt.utils.validation import validate_model_format

        return validate_model_format(model_path, cls.supported_formats())

    @classmethod
    def is_available(cls) -> bool:
        """Check if Docker is available and the engine's image is pulled."""
        from .docker_manager import DockerManager

        return DockerManager.is_docker_available() and DockerManager.image_exists(
            cls.resolved_image()
        )

    @classmethod
    def diagnose(cls) -> EngineDiagnostics:
        """Check Docker availability and image status.

        Returns structured diagnostics including the exact error message
        and actionable fix suggestions.
        """
        from .docker_manager import DockerManager

        image = cls.resolved_image()

        if not DockerManager.is_docker_available():
            return EngineDiagnostics(
                available=False,
                image=image,
                error="Docker is not installed or not running",
                guidance="Install Docker: https://docs.docker.com/get-docker/",
            )
        if not DockerManager.image_exists(image):
            from .image_resolver import is_kitt_managed_image

            if is_kitt_managed_image(image):
                return EngineDiagnostics(
                    available=False,
                    image=image,
                    error=f"Docker image not built: {image}",
                    guidance=f"Build with: kitt engines setup {cls.name()}",
                )
            return EngineDiagnostics(
                available=False,
                image=image,
                error=f"Docker image not pulled: {image}",
                guidance=f"Pull with: kitt engines setup {cls.name()}",
            )
        return EngineDiagnostics(available=True, image=image)

    @abstractmethod
    def initialize(self, model_path: str, config: dict[str, Any]) -> None:
        """Start Docker container and wait for healthy.

        Args:
            model_path: Path to model directory or model identifier.
            config: Engine-specific configuration.
        """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        top_p: float = 1.0,
        top_k: int = 50,
        max_tokens: int = 2048,
        **engine_specific_params: Any,
    ) -> GenerationResult:
        """Generate response via HTTP API to container.

        Args:
            prompt: Input prompt.
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.
            top_k: Top-k sampling parameter.
            max_tokens: Maximum tokens to generate.
            **engine_specific_params: Engine-specific parameters.

        Returns:
            GenerationResult with output and metrics.
        """

    def cleanup(self) -> None:
        """Stop and remove the Docker container."""
        from .docker_manager import DockerManager

        if hasattr(self, "_container_id") and self._container_id:
            DockerManager.stop_container(self._container_id)
            self._container_id = None
