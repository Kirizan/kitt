"""Plugin system for extending KITT with external engines, benchmarks, and reporters."""

from .discovery import discover_plugins, discover_external_benchmarks, discover_external_engines
from .manifest import PluginManifest

__all__ = [
    "discover_plugins",
    "discover_external_benchmarks",
    "discover_external_engines",
    "PluginManifest",
]
