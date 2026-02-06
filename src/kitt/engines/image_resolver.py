"""Hardware-aware Docker image selection for inference engines.

Maps GPU compute capabilities to the best Docker image for each engine.
Blackwell-class GPUs (compute capability >= 10.0) require NVIDIA NGC
containers with proper sm_100+/sm_120+/sm_121 support.

Compute Capability Reference:
- 7.x: Turing (RTX 20 series)
- 8.x: Ampere (RTX 30 series, A100)
- 8.9: Ada Lovelace (RTX 40 series)
- 9.0: Hopper (H100, H200)
- 10.0+: Blackwell (B100, B200)
- 12.0: Blackwell consumer (RTX 50 series)
- 12.1: Blackwell edge (GB10 on DGX Spark)

When adding new overrides:
1. Test on actual hardware when possible
2. Document which GPU models are affected
3. Add corresponding tests in test_image_resolver.py
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Image overrides keyed by engine name.
# Each entry is a list of (min_compute_capability, image) tuples,
# sorted descending by compute capability. First match wins.
#
# IMPORTANT: Keep lists sorted by compute capability DESCENDING so that
# more specific (higher cc) matches are checked first.
_IMAGE_OVERRIDES: Dict[str, List[Tuple[Tuple[int, int], str]]] = {
    # vLLM: Standard images use Triton which requires ptxas for the target arch.
    # Blackwell (sm_100+, sm_120, sm_121a) is not supported in standard vLLM.
    # NGC containers include proper Blackwell support.
    "vllm": [
        ((10, 0), "nvcr.io/nvidia/vllm:26.01-py3"),
    ],
    # TGI: No ARM64 Docker images published. Cannot run on aarch64 platforms
    # like DGX Spark. Add overrides here if ARM64 images become available.
    "tgi": [],
    # llama.cpp: Official CUDA images are x86_64-only. On Blackwell/aarch64
    # (DGX Spark, GB10), use a locally-built image targeting sm_121.
    # Build with: docker build -f .devops/cuda.Dockerfile --build-arg
    #   CUDA_VERSION=13.1.1 --build-arg UBUNTU_VERSION=24.04
    #   --build-arg CUDA_DOCKER_ARCH=121 --target server
    #   -t llama.cpp:server-spark .
    "llama_cpp": [
        ((10, 0), "llama.cpp:server-spark"),
    ],
    # Ollama: Bundles its own llama.cpp, works on all supported hardware.
    "ollama": [],
}

# Cache for detected compute capability (None = not yet detected)
_cc_cache: Optional[Tuple[int, int]] = None
_cc_detected: bool = False


def _detect_cc() -> Optional[Tuple[int, int]]:
    """Detect and cache GPU compute capability."""
    global _cc_cache, _cc_detected
    if _cc_detected:
        return _cc_cache
    _cc_detected = True

    try:
        from kitt.hardware.detector import detect_gpu_compute_capability

        _cc_cache = detect_gpu_compute_capability()
    except Exception as e:
        logger.debug(f"Compute capability detection failed: {e}")
        _cc_cache = None

    if _cc_cache:
        logger.info(
            f"GPU compute capability: {_cc_cache[0]}.{_cc_cache[1]}"
        )
    return _cc_cache


def resolve_image(engine_name: str, default_image: str) -> str:
    """Return the best Docker image for an engine on the current GPU.

    Args:
        engine_name: Engine identifier (e.g. 'vllm', 'tgi').
        default_image: Fallback image when no override matches.

    Returns:
        Docker image string appropriate for the detected hardware.
    """
    cc = _detect_cc()
    if cc is None:
        return default_image

    overrides = _IMAGE_OVERRIDES.get(engine_name, [])
    for min_cc, image in overrides:
        if cc >= min_cc:
            logger.info(
                f"GPU cc {cc[0]}.{cc[1]} matched override for "
                f"{engine_name}: {image}"
            )
            return image

    return default_image


def clear_cache() -> None:
    """Reset the cached compute capability (for testing)."""
    global _cc_cache, _cc_detected
    _cc_cache = None
    _cc_detected = False


def get_supported_engines() -> List[str]:
    """Return list of engines with hardware-aware image selection.

    All engines in _IMAGE_OVERRIDES are supported, even if they have
    empty override lists (meaning default image works on all hardware).
    """
    return list(_IMAGE_OVERRIDES.keys())


def has_hardware_overrides(engine_name: str) -> bool:
    """Check if an engine has any hardware-specific image overrides.

    Args:
        engine_name: Engine identifier (e.g. 'vllm', 'tgi').

    Returns:
        True if the engine has non-empty overrides list.
    """
    return bool(_IMAGE_OVERRIDES.get(engine_name, []))
