"""Engine discovery and registration."""

import logging
from typing import Dict, List, Type

from .base import InferenceEngine

logger = logging.getLogger(__name__)


class EngineRegistry:
    """Registry for discovering and managing inference engines."""

    _engines: Dict[str, Type[InferenceEngine]] = {}

    @classmethod
    def register(cls, engine_class: Type[InferenceEngine]) -> None:
        """Register an engine class."""
        cls._engines[engine_class.name()] = engine_class

    @classmethod
    def get_engine(cls, name: str) -> Type[InferenceEngine]:
        """Get engine class by name.

        Raises:
            ValueError: If engine is not registered.
        """
        if name not in cls._engines:
            available = ", ".join(cls._engines.keys()) or "none"
            raise ValueError(
                f"Engine '{name}' not found. Available engines: {available}"
            )
        return cls._engines[name]

    @classmethod
    def list_available(cls) -> List[str]:
        """List all available (installed and functional) engines."""
        return [
            name
            for name, engine_class in cls._engines.items()
            if engine_class.is_available()
        ]

    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered engines (available or not)."""
        return list(cls._engines.keys())

    @classmethod
    def auto_discover(cls) -> None:
        """Auto-discover and register all engine implementations."""
        # Import all engine modules to trigger registration
        from . import (  # noqa: F401
            llama_cpp_engine,
            ollama_engine,
            tgi_engine,
            vllm_engine,
        )

    @classmethod
    def clear(cls) -> None:
        """Clear all registered engines (for testing)."""
        cls._engines.clear()


def register_engine(engine_class: Type[InferenceEngine]) -> Type[InferenceEngine]:
    """Decorator to auto-register engine classes."""
    EngineRegistry.register(engine_class)
    return engine_class
