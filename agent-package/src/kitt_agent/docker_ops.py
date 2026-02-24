"""Docker container management for the thin agent.

Manages container lifecycle via the Docker CLI (no SDK dependency).
"""

import logging
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContainerSpec:
    """Specification for running a Docker container."""

    image: str
    port: int = 0
    container_port: int = 0
    gpu: bool = True
    volumes: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    extra_args: list[str] = field(default_factory=list)
    command_args: list[str] = field(default_factory=list)
    name: str = ""
    health_url: str = ""


class DockerOps:
    """Docker operations for the thin agent."""

    @staticmethod
    def is_available() -> bool:
        """Check if Docker is installed and daemon is running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def pull_image(image: str) -> bool:
        """Pull a Docker image."""
        logger.info(f"Pulling image: {image}")
        result = subprocess.run(
            ["docker", "pull", image],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            logger.error(f"Pull failed: {result.stderr}")
            return False
        return True

    @staticmethod
    def run_container(
        spec: ContainerSpec,
        on_log: Callable[[str], None] | None = None,
    ) -> str:
        """Start a container and return the container ID.

        Args:
            spec: Container specification.
            on_log: Optional callback for log lines.

        Returns:
            Container ID string.
        """
        name = spec.name or f"kitt-agent-{int(time.time())}"
        args = ["docker", "run", "-d", "--name", name]

        if spec.gpu:
            args.extend(["--gpus", "all"])

        if spec.port and spec.container_port:
            args.extend(["-p", f"{spec.port}:{spec.container_port}"])

        for host_path, container_path in spec.volumes.items():
            args.extend(["-v", f"{host_path}:{container_path}"])

        for key, val in spec.env.items():
            args.extend(["-e", f"{key}={val}"])

        args.extend(spec.extra_args)
        args.append(spec.image)
        args.extend(spec.command_args)

        logger.info(f"Starting container: {' '.join(args)}")
        result = subprocess.run(args, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise RuntimeError(f"Container start failed: {result.stderr.strip()}")

        container_id = result.stdout.strip()[:12]
        logger.info(f"Container started: {container_id} ({name})")

        if on_log:
            on_log(f"Container started: {container_id}")

        return container_id

    @staticmethod
    def stop_container(container_id: str) -> bool:
        """Stop and remove a container."""
        logger.info(f"Stopping container: {container_id}")
        subprocess.run(
            ["docker", "stop", container_id],
            capture_output=True,
            timeout=30,
        )
        result = subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0

    @staticmethod
    def stream_logs(
        container_id: str,
        on_log: Callable[[str], None],
        follow: bool = True,
    ) -> None:
        """Stream container logs, calling on_log for each line."""
        args = ["docker", "logs", container_id]
        if follow:
            args.append("-f")

        proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in proc.stdout or []:
            on_log(line.rstrip())
        proc.wait()

    @staticmethod
    def wait_for_healthy(
        url: str, timeout: float = 300, interval: float = 2.0
    ) -> bool:
        """Poll a URL until it responds with < 500 status."""
        import urllib.request

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    if resp.status < 500:
                        return True
            except Exception:
                pass
            time.sleep(min(interval, 10.0))
            interval = min(interval * 1.5, 10.0)
        return False

    @staticmethod
    def container_running(container_id: str) -> bool:
        """Check if a container is running."""
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_id],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() == "true"
