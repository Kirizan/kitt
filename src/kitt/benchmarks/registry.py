"""Benchmark discovery and registration."""

import logging
from pathlib import Path
from typing import Dict, List, Type

from .base import LLMBenchmark

logger = logging.getLogger(__name__)


class BenchmarkRegistry:
    """Registry for discovering and managing benchmarks."""

    _benchmarks: Dict[str, Type[LLMBenchmark]] = {}

    @classmethod
    def register(cls, benchmark_class: Type[LLMBenchmark]) -> None:
        """Register a benchmark class."""
        cls._benchmarks[benchmark_class.name] = benchmark_class

    @classmethod
    def get_benchmark(cls, name: str) -> Type[LLMBenchmark]:
        """Get benchmark class by name.

        Raises:
            ValueError: If benchmark is not registered.
        """
        if name not in cls._benchmarks:
            available = ", ".join(cls._benchmarks.keys()) or "none"
            raise ValueError(
                f"Benchmark '{name}' not found. Available: {available}"
            )
        return cls._benchmarks[name]

    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered benchmark names."""
        return list(cls._benchmarks.keys())

    @classmethod
    def list_by_category(cls, category: str) -> List[str]:
        """List benchmarks filtered by category."""
        return [
            name
            for name, bench_cls in cls._benchmarks.items()
            if bench_cls.category == category
        ]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered benchmarks (for testing)."""
        cls._benchmarks.clear()

    @classmethod
    def auto_discover(cls) -> None:
        """Import built-in benchmark modules to trigger registration."""
        from .performance import throughput  # noqa: F401


def register_benchmark(benchmark_class: Type[LLMBenchmark]) -> Type[LLMBenchmark]:
    """Decorator to auto-register benchmark classes."""
    BenchmarkRegistry.register(benchmark_class)
    return benchmark_class
