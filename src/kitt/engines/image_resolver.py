"""Hardware-aware Docker image selection for inference engines.

Maps GPU compute capabilities to the best Docker image for each engine.
Blackwell-class GPUs (compute capability >= 10.0) require NVIDIA NGC
containers with proper sm_100+/sm_120+/sm_121 support.
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Image overrides keyed by engine name.
# Each entry is a list of (min_compute_capability, image) tuples,
# sorted descending by compute capability.  First match wins.
_IMAGE_OVERRIDES: Dict[str, List[Tuple[Tuple[int, int], str]]] = {
    "vllm": [
        ((10, 0), "nvcr.io/nvidia/vllm:26.01-py3"),
    ],
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
