"""Input validation utilities."""

from pathlib import Path
from typing import List, Optional


def validate_model_path(path: str) -> Optional[str]:
    """Validate a model path exists.

    Returns error message or None if valid.
    """
    p = Path(path)
    if not p.exists():
        return f"Model path does not exist: {path}"
    return None


def validate_engine_name(name: str, available: List[str]) -> Optional[str]:
    """Validate an engine name.

    Returns error message or None if valid.
    """
    if name not in available:
        return f"Engine '{name}' not available. Options: {', '.join(available)}"
    return None
