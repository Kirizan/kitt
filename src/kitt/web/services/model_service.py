"""Devon bridge for the web UI — model search, download, and management."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _is_devon_available() -> bool:
    """Check if Devon is importable."""
    try:
        from kitt.campaign.devon_bridge import is_devon_available

        return is_devon_available()
    except ImportError:
        return False


class ModelService:
    """Web-facing service for Devon model operations."""

    def __init__(self) -> None:
        self._devon_available = _is_devon_available()

    @property
    def available(self) -> bool:
        return self._devon_available

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search for models via Devon sources.

        Returns:
            List of model info dicts.
        """
        if not self._devon_available:
            return []

        try:
            from devon.sources.registry import SourceRegistry

            registry = SourceRegistry()
            results = registry.search(query, limit=limit)
            return [
                {
                    "repo_id": r.repo_id if hasattr(r, "repo_id") else str(r),
                    "name": getattr(r, "name", str(r)),
                    "source": getattr(r, "source", ""),
                    "size_gb": getattr(r, "size_gb", 0),
                    "downloads": getattr(r, "downloads", 0),
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Devon search failed: {e}")
            return []

    def list_local(self) -> list[dict[str, Any]]:
        """List locally available models via Devon."""
        if not self._devon_available:
            return []

        try:
            from kitt.campaign.devon_bridge import DevonBridge

            bridge = DevonBridge()
            models = bridge.list_models()
            return [
                {
                    "repo_id": m,
                    "path": bridge.find_path(m),
                    "size_gb": bridge.disk_usage_gb(m),
                }
                for m in models
            ]
        except Exception as e:
            logger.warning(f"Devon list_local failed: {e}")
            return []

    def download(self, repo_id: str, allow_patterns: list[str] | None = None) -> str:
        """Download a model via Devon.

        Returns:
            Local path to the downloaded model.
        """
        if not self._devon_available:
            raise RuntimeError("Devon is not available")

        from kitt.campaign.devon_bridge import DevonBridge

        bridge = DevonBridge()
        path = bridge.download(repo_id, allow_patterns=allow_patterns)
        return str(path)

    def remove(self, repo_id: str) -> bool:
        """Remove a locally downloaded model."""
        if not self._devon_available:
            return False

        try:
            from kitt.campaign.devon_bridge import DevonBridge

            bridge = DevonBridge()
            bridge.remove(repo_id)
            return True
        except Exception as e:
            logger.warning(f"Devon remove failed: {e}")
            return False
