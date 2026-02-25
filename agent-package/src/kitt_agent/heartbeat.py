"""Agent heartbeat thread — sends periodic status to the server."""

import json
import logging
import shutil
import ssl
import threading
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
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
        on_command: Callable[[dict[str, Any]], None] | None = None,
        on_settings: Callable[[dict[str, str]], None] | None = None,
        storage_dir: str = "",
    ) -> None:
        super().__init__(daemon=True, name="kitt-heartbeat")
        self.server_url = server_url.rstrip("/")
        self.agent_id = agent_id
        self.token = token
        self._base_interval_s = interval_s
        self._active_interval_s = interval_s
        self.verify = verify
        self.client_cert = client_cert
        self.on_command = on_command
        self.on_settings = on_settings
        self._storage_dir = storage_dir
        self._stop_event = threading.Event()
        self._start_time = time.monotonic()
        self._status = "idle"
        self._current_task = ""

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                resp = self._send_heartbeat()
                # Process any commands returned from the server
                if self.on_command and resp:
                    for cmd in resp.get("commands", []):
                        try:
                            self.on_command(cmd)
                        except Exception as e:
                            logger.error(f"Command handler failed: {e}")
                # Sync settings from server
                if self.on_settings and resp and "settings" in resp:
                    try:
                        settings = resp["settings"]
                        self.on_settings(settings)
                        # Update heartbeat interval from settings
                        if "heartbeat_interval_s" in settings:
                            new_interval = int(settings["heartbeat_interval_s"])
                            if 10 <= new_interval <= 300:
                                self._base_interval_s = new_interval
                                # Recompute active interval
                                if self._status == "running":
                                    self._active_interval_s = max(new_interval, 60)
                                else:
                                    self._active_interval_s = new_interval
                    except Exception as e:
                        logger.warning(f"Settings sync failed: {e}")
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
            self._stop_event.wait(self._active_interval_s)

    def stop(self) -> None:
        self._stop_event.set()

    def set_status(self, status: str, task: str = "") -> None:
        """Update agent status. Auto-throttles heartbeat during benchmarks."""
        self._status = status
        self._current_task = task
        if status == "running":
            self._active_interval_s = max(self._base_interval_s, 60)
        else:
            self._active_interval_s = self._base_interval_s

    def set_interval(self, seconds: int) -> None:
        """Directly set the heartbeat interval."""
        if 10 <= seconds <= 300:
            self._base_interval_s = seconds
            if self._status != "running":
                self._active_interval_s = seconds

    def _send_heartbeat(self) -> dict[str, Any]:
        from urllib.parse import quote

        url = (
            f"{self.server_url}/api/v1/agents/{quote(self.agent_id, safe='')}/heartbeat"
        )

        payload: dict[str, Any] = {
            "status": self._status,
            "current_task": self._current_task,
        }

        # Add GPU stats if available
        try:
            import pynvml

            pynvml.nvmlInit()
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                payload["gpu_utilization_pct"] = util.gpu
                payload["gpu_memory_used_gb"] = round(mem.used / (1024**3), 2)
            finally:
                pynvml.nvmlShutdown()
        except Exception:
            pass

        # Add storage usage
        storage_path = self._storage_dir or str(Path.home() / ".kitt" / "models")
        try:
            usage = shutil.disk_usage(storage_path)
            payload["storage_gb_free"] = round(usage.free / (1024**3), 2)
        except OSError:
            pass

        payload["uptime_s"] = time.monotonic() - self._start_time

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
