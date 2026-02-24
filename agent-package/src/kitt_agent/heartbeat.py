"""Agent heartbeat thread — sends periodic status to the server."""

import json
import logging
import ssl
import threading
import time
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class HeartbeatThread(threading.Thread):
    """Background thread that sends heartbeats to the KITT server."""

    def __init__(
        self,
        server_url: str,
        agent_id: str,
        token: str,
        interval_s: int = 30,
        verify: str | bool = True,
        client_cert: tuple[str, str] | None = None,
    ) -> None:
        super().__init__(daemon=True, name="kitt-heartbeat")
        self.server_url = server_url.rstrip("/")
        self.agent_id = agent_id
        self.token = token
        self.interval_s = interval_s
        self.verify = verify
        self.client_cert = client_cert
        self._stop_event = threading.Event()
        self._status = "idle"
        self._current_task = ""

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._send_heartbeat()
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
            self._stop_event.wait(self.interval_s)

    def stop(self) -> None:
        self._stop_event.set()

    def set_status(self, status: str, task: str = "") -> None:
        self._status = status
        self._current_task = task

    def _send_heartbeat(self) -> dict[str, Any]:
        url = f"{self.server_url}/api/v1/agents/{self.agent_id}/heartbeat"

        payload: dict[str, Any] = {
            "status": self._status,
            "current_task": self._current_task,
        }

        # Add GPU stats if available
        try:
            import pynvml

            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            payload["gpu_utilization_pct"] = util.gpu
            payload["gpu_memory_used_gb"] = round(mem.used / (1024**3), 2)
            pynvml.nvmlShutdown()
        except Exception:
            pass

        payload["uptime_s"] = time.monotonic()

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST",
        )

        ctx = None
        if self.server_url.startswith("https"):
            ctx = ssl.create_default_context()
            if isinstance(self.verify, str):
                ctx.load_verify_locations(self.verify)
            elif not self.verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            if self.client_cert:
                ctx.load_cert_chain(self.client_cert[0], self.client_cert[1])

        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
