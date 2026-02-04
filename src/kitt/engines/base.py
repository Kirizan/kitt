"""Abstract base class for inference engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


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


class InferenceEngine(ABC):
    """Abstract base class for inference engines."""

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """Engine identifier (e.g., 'vllm', 'tgi')."""

    @classmethod
    @abstractmethod
    def supported_formats(cls) -> List[str]:
        """Model formats this engine supports (e.g., ['safetensors', 'pytorch'])."""

    @classmethod
    def is_available(cls) -> bool:
        """Check if this engine is available on the system."""
        try:
            return cls._check_dependencies()
        except Exception:
            return False

    @classmethod
    @abstractmethod
    def _check_dependencies(cls) -> bool:
        """Engine-specific dependency check."""

    @abstractmethod
    def initialize(self, model_path: str, config: Dict[str, Any]) -> None:
        """Load model and prepare engine.

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
        """Generate response with metrics collection.

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

    @abstractmethod
    def cleanup(self) -> None:
        """Clean shutdown and resource cleanup."""

    def translate_params(self, universal_params: Dict[str, Any]) -> Dict[str, Any]:
        """Translate universal parameters to engine-specific parameters.

        Override if engine has different parameter names.
        """
        return universal_params
