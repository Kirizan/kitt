"""vLLM inference engine implementation."""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import GenerationMetrics, GenerationResult, InferenceEngine
from .registry import register_engine

logger = logging.getLogger(__name__)


@register_engine
class VLLMEngine(InferenceEngine):
    """vLLM inference engine implementation."""

    def __init__(self) -> None:
        self.llm = None

    @classmethod
    def name(cls) -> str:
        return "vllm"

    @classmethod
    def supported_formats(cls) -> List[str]:
        return ["safetensors", "pytorch"]

    @staticmethod
    def _cuda_mismatch_guidance() -> Optional[str]:
        """Check for CUDA version mismatch and return fix instructions."""
        from kitt.hardware.detector import check_cuda_compatibility

        mismatch = check_cuda_compatibility()
        if mismatch is None:
            return None

        cu_tag = f"cu{mismatch.system_major}0"
        return (
            f"CUDA version mismatch: system has CUDA {mismatch.system_cuda} "
            f"but PyTorch was built for CUDA {mismatch.torch_cuda}.\n"
            f"Fix by reinstalling with the correct CUDA wheels:\n"
            f"  pip install torch --force-reinstall --index-url https://download.pytorch.org/whl/{cu_tag}\n"
            f"  pip install vllm --force-reinstall --extra-index-url https://download.pytorch.org/whl/{cu_tag}\n"
            f"Or run: kitt engines setup vllm"
        )

    @classmethod
    def _check_dependencies(cls) -> bool:
        try:
            import vllm  # noqa: F401

            return True
        except ModuleNotFoundError:
            return False
        except ImportError as e:
            error_msg = str(e)
            if "libcudart" in error_msg or "libcuda" in error_msg:
                guidance = cls._cuda_mismatch_guidance()
                if guidance:
                    logger.warning(guidance)
                else:
                    logger.warning(
                        f"vLLM failed to import due to a CUDA library error: {e}\n"
                        "Check that your CUDA runtime matches the installed PyTorch version."
                    )
            else:
                logger.warning(f"vLLM is installed but failed to import: {e}")
            return False

    def initialize(self, model_path: str, config: Dict[str, Any]) -> None:
        """Initialize vLLM engine."""
        try:
            from vllm import LLM
        except ModuleNotFoundError:
            raise RuntimeError(
                "vLLM not installed. Install with: poetry install -E vllm"
            )
        except ImportError as e:
            error_msg = str(e)
            if "libcudart" in error_msg or "libcuda" in error_msg:
                guidance = self._cuda_mismatch_guidance()
                if guidance:
                    raise RuntimeError(
                        f"vLLM failed to load: {e}\n\n{guidance}"
                    )
            raise RuntimeError(
                f"vLLM is installed but failed to load: {e}"
            )

        tensor_parallel_size = config.get("tensor_parallel_size", 1)
        gpu_memory_utilization = config.get("gpu_memory_utilization", 0.9)

        self.llm = LLM(
            model=model_path,
            tensor_parallel_size=tensor_parallel_size,
            gpu_memory_utilization=gpu_memory_utilization,
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
        """Generate with vLLM and GPU memory tracking."""
        from vllm import SamplingParams

        from kitt.collectors.gpu_stats import GPUMemoryTracker

        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_tokens=max_tokens,
        )

        with GPUMemoryTracker(gpu_index=0) as tracker:
            start_time = time.perf_counter()
            outputs = self.llm.generate([prompt], sampling_params)
            end_time = time.perf_counter()

        total_latency_ms = (end_time - start_time) * 1000

        output = outputs[0].outputs[0].text
        prompt_tokens = len(outputs[0].prompt_token_ids)
        completion_tokens = len(outputs[0].outputs[0].token_ids)

        tps = (
            completion_tokens / (total_latency_ms / 1000)
            if total_latency_ms > 0
            else 0
        )

        gpu_memory_peak_gb = tracker.get_peak_memory_mb() / 1024
        gpu_memory_avg_gb = tracker.get_average_memory_mb() / 1024

        metrics = GenerationMetrics(
            ttft_ms=0,  # TODO: Extract from vLLM metrics if available
            tps=tps,
            total_latency_ms=total_latency_ms,
            gpu_memory_peak_gb=gpu_memory_peak_gb,
            gpu_memory_avg_gb=gpu_memory_avg_gb,
            timestamp=datetime.now(),
        )

        return GenerationResult(
            output=output,
            metrics=metrics,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def cleanup(self) -> None:
        """Cleanup vLLM resources."""
        if self.llm is not None:
            del self.llm
            self.llm = None
