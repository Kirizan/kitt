"""Simplified hardware detection for agent registration."""

import logging
import platform
import socket
from typing import Any

logger = logging.getLogger(__name__)


def detect_system() -> dict[str, Any]:
    """Gather basic system info for registration payload."""
    info: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "os": platform.system(),
    }

    # CPU
    try:
        import cpuinfo

        cpu = cpuinfo.get_cpu_info()
        info["cpu_info"] = cpu.get("brand_raw", "unknown")
        info["cpu_cores"] = cpu.get("count", 0)
    except Exception:
        info["cpu_info"] = platform.processor() or "unknown"
        info["cpu_cores"] = 0

    # RAM
    try:
        import psutil

        info["ram_gb"] = round(psutil.virtual_memory().total / (1024**3))
    except Exception:
        info["ram_gb"] = 0

    # GPU
    try:
        import pynvml

        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode()
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_gb = round(mem.total / (1024**3))
        pynvml.nvmlShutdown()

        info["gpu_info"] = f"{name} {vram_gb}GB"
        info["gpu_count"] = count
    except Exception:
        info["gpu_info"] = ""
        info["gpu_count"] = 0

    return info
