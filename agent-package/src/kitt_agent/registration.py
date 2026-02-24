"""Agent registration with the KITT server."""

import json
import logging
import ssl
import urllib.request
from typing import Any

from kitt_agent import __version__
from kitt_agent.hardware import detect_system

logger = logging.getLogger(__name__)


def build_registration_payload() -> dict[str, Any]:
    """Build the agent registration payload from local system info."""
    info = detect_system()
    payload: dict[str, Any] = {
        "hostname": info["hostname"],
        "gpu_info": info.get("gpu_info", ""),
        "gpu_count": info.get("gpu_count", 0),
        "cpu_info": info.get("cpu_info", ""),
        "ram_gb": info.get("ram_gb", 0),
        "kitt_version": __version__,
        "capabilities": [],
    }

    # Check which engine images are available locally
    from kitt_agent.docker_ops import DockerOps

    if DockerOps.is_available():
        import subprocess

        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            images = set(result.stdout.strip().splitlines())
            engine_images = {
                "vllm": "vllm/vllm-openai",
                "tgi": "ghcr.io/huggingface/text-generation-inference",
                "llama_cpp": "ghcr.io/ggerganov/llama.cpp",
                "ollama": "ollama/ollama",
            }
            for engine, prefix in engine_images.items():
                if any(img.startswith(prefix) for img in images):
                    payload["capabilities"].append(engine)

    return payload


def register_with_server(
    server_url: str,
    token: str,
    name: str,
    port: int = 8090,
    verify: str | bool = True,
    client_cert: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Register this agent with the KITT server."""
    payload = build_registration_payload()
    payload["name"] = name
    payload["port"] = port

    url = f"{server_url.rstrip('/')}/api/v1/agents/register"
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    ctx = None
    if server_url.startswith("https"):
        ctx = ssl.create_default_context()
        if isinstance(verify, str):
            ctx.load_verify_locations(verify)
        elif not verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        if client_cert:
            ctx.load_cert_chain(client_cert[0], client_cert[1])

    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))
