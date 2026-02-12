"""Agent registration with the KITT server."""

import logging
import socket
from typing import Any

logger = logging.getLogger(__name__)


def build_registration_payload() -> dict[str, Any]:
    """Build the agent registration payload from local system info."""
    payload: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "capabilities": [],
    }

    # Hardware fingerprint
    try:
        from kitt.hardware.fingerprint import HardwareFingerprint

        info = HardwareFingerprint.detect_system()
        payload["fingerprint"] = HardwareFingerprint.generate()
        payload["environment_type"] = info.environment_type
        payload["ram_gb"] = info.ram_gb
        payload["cpu_info"] = f"{info.cpu.model} ({info.cpu.cores}c)"

        if info.gpu:
            payload["gpu_info"] = info.gpu.model
            if info.gpu.vram_gb:
                payload["gpu_info"] += f" {info.gpu.vram_gb}GB"
            payload["gpu_count"] = info.gpu.count
    except Exception as e:
        logger.warning(f"Hardware detection failed: {e}")

    # KITT version
    try:
        import kitt

        payload["kitt_version"] = getattr(kitt, "__version__", "unknown")
    except Exception:
        payload["kitt_version"] = "unknown"

    # Available engines
    try:
        from kitt.engines.registry import EngineRegistry

        EngineRegistry.auto_discover()
        payload["capabilities"] = EngineRegistry.list_available()
    except Exception:
        pass

    return payload


def register_with_server(
    server_url: str,
    token: str,
    name: str,
    port: int = 8090,
    verify: str | bool = True,
    client_cert: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Register this agent with the KITT server.

    Args:
        server_url: Base URL of the KITT server (e.g., https://server:8080).
        token: Bearer token for authentication.
        name: Agent name.
        port: Agent's listening port.
        verify: CA cert path or False to skip verification.
        client_cert: Tuple of (cert_path, key_path) for mTLS.

    Returns:
        Server response dict with agent_id and heartbeat_interval_s.
    """
    import json
    import ssl
    import urllib.request

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

    # Build SSL context
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

    with urllib.request.urlopen(req, context=ctx) as response:
        return json.loads(response.read().decode("utf-8"))
