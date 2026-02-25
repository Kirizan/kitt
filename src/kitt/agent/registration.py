"""Agent registration with the KITT server."""

import json
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
        fingerprint_str = HardwareFingerprint.generate()
        payload["fingerprint"] = fingerprint_str
        payload["environment_type"] = info.environment_type
        payload["ram_gb"] = info.ram_gb
        payload["cpu_info"] = f"{info.cpu.model} ({info.cpu.cores}c)"

        if info.gpu:
            # Unified memory fallback: use system RAM when dedicated VRAM is 0
            vram = info.gpu.vram_gb if info.gpu.vram_gb > 0 else info.ram_gb
            payload["gpu_info"] = info.gpu.model
            if vram:
                payload["gpu_info"] += f" {vram}GB"
            payload["gpu_count"] = info.gpu.count

        # Build hardware_details JSON
        hw = {
            "gpu_model": info.gpu.model if info.gpu else "",
            "gpu_vram_gb": info.gpu.vram_gb if info.gpu else 0,
            "gpu_count": info.gpu.count if info.gpu else 0,
            "gpu_compute_capability": (
                f"{info.gpu.compute_capability[0]}.{info.gpu.compute_capability[1]}"
                if info.gpu and info.gpu.compute_capability
                else ""
            ),
            "cpu_model": info.cpu.model,
            "cpu_cores": info.cpu.cores,
            "cpu_threads": info.cpu.threads,
            "ram_gb": info.ram_gb,
            "ram_type": info.ram_type,
            "storage_brand": info.storage.brand,
            "storage_model": info.storage.model,
            "storage_type": info.storage.type,
            "cuda_version": info.cuda_version or "",
            "driver_version": info.driver_version or "",
            "os": info.os,
            "kernel": info.kernel,
            "environment_type": info.environment_type,
            "fingerprint": fingerprint_str,
        }
        # For unified memory, store the effective VRAM
        if info.gpu and info.gpu.vram_gb == 0 and info.ram_gb > 0:
            hw["gpu_vram_gb"] = info.ram_gb
        payload["hardware_details"] = json.dumps(hw)
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
