"""Devon bridge for the web UI — model search, download, and management.

Supports three backends in priority order:
1. Remote Devon (HTTP) — when a Devon URL is configured
2. Local DevonBridge — when Devon is installed as a Python package
3. Unavailable — methods return empty results
"""

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
    """Web-facing service for Devon model operations.

    Prefers a remote Devon client when configured, falls back to the
    local DevonBridge when Devon is installed as a Python package.
    """

    def __init__(
        self,
        devon_url: str | None = None,
        devon_api_key: str | None = None,
    ) -> None:
        self._devon_available = _is_devon_available()
        self._remote_client = None

        if devon_url:
            try:
                from kitt.devon import DevonConnectionConfig, RemoteDevonClient

                config = DevonConnectionConfig(url=devon_url, api_key=devon_api_key)
                client = RemoteDevonClient(config)
                if client.is_healthy():
                    self._remote_client = client
                    logger.info(f"Connected to remote Devon at {devon_url}")
                else:
                    logger.warning(
                        f"Remote Devon at {devon_url} is not healthy, falling back to local"
                    )
            except ImportError:
                logger.warning("httpx not installed, cannot use remote Devon")
            except Exception as e:
                logger.warning(f"Failed to connect to remote Devon: {e}")

    @property
    def available(self) -> bool:
        return self._remote_client is not None or self._devon_available

    @property
    def is_remote(self) -> bool:
        """True if using a remote Devon instance."""
        return self._remote_client is not None

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search for models via Devon sources.

        Returns:
            List of model info dicts.
        """
        if self._remote_client:
            try:
                results = self._remote_client.search(query=query, limit=limit)
                return [
                    {
                        "repo_id": r.get("model_id", ""),
                        "name": r.get("model_name", r.get("model_id", "")),
                        "source": r.get("source", ""),
                        "size_gb": r.get("total_size_bytes", 0) / (1024**3),
                        "downloads": r.get("downloads", 0),
                    }
                    for r in results
                ]
            except Exception as e:
                logger.warning(f"Remote Devon search failed: {e}")
                return []

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
        if self._remote_client:
            try:
                models = self._remote_client.list_models()
                return [
                    {
                        "repo_id": m.get("model_id", ""),
                        "path": m.get("path", ""),
                        "size_gb": m.get("size_bytes", 0) / (1024**3),
                    }
                    for m in models
                ]
            except Exception as e:
                logger.warning(f"Remote Devon list_local failed: {e}")
                return []

        if not self._devon_available:
            return []

        try:
            from kitt.campaign.devon_bridge import DevonBridge

            bridge = DevonBridge()
            repo_ids = bridge.list_models()
            return [
                {
                    "repo_id": repo_id,
                    "path": bridge.find_path(repo_id),
                    "size_gb": bridge.disk_usage_gb(repo_id),
                }
                for repo_id in repo_ids
            ]
        except Exception as e:
            logger.warning(f"Devon list_local failed: {e}")
            return []

    def download(self, repo_id: str, allow_patterns: list[str] | None = None) -> str:
        """Download a model via Devon.

        Returns:
            Local path to the downloaded model.
        """
        if self._remote_client:
            path = self._remote_client.download(repo_id, allow_patterns=allow_patterns)
            return str(path)

        if not self._devon_available:
            raise RuntimeError("Devon is not available")

        from kitt.campaign.devon_bridge import DevonBridge

        bridge = DevonBridge()
        path = bridge.download(repo_id, allow_patterns=allow_patterns)
        return str(path)

    def remove(self, repo_id: str) -> bool:
        """Remove a locally downloaded model."""
        if self._remote_client:
            try:
                return self._remote_client.remove(repo_id)
            except Exception as e:
                logger.warning(f"Remote Devon remove failed: {e}")
                return False

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

    def status(self) -> dict[str, Any] | None:
        """Get storage status from Devon. Only available with remote client."""
        if self._remote_client:
            try:
                return self._remote_client.status()
            except Exception as e:
                logger.warning(f"Remote Devon status failed: {e}")
        return None
