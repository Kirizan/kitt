"""KITT Agent daemon — Flask mini-app that receives commands from the server."""

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

try:
    from flask import Flask, Response, jsonify, request

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


def create_agent_app(
    name: str,
    server_url: str,
    token: str,
    port: int = 8090,
    insecure: bool = False,
) -> "Flask":
    """Create the agent Flask mini-app.

    Args:
        name: Agent name.
        server_url: KITT server URL.
        token: Bearer token.
        port: Agent listening port.
        insecure: Skip TLS.

    Returns:
        Flask app for the agent daemon.
    """
    if not FLASK_AVAILABLE:
        raise ImportError(
            "Flask is required for the agent. Install with: pip install kitt[web]"
        )

    app = Flask(__name__)

    from kitt.agent.executor import BenchmarkExecutor
    from kitt.agent.log_streamer import LogStreamer

    executor = BenchmarkExecutor()
    log_streamers: dict[str, LogStreamer] = {}

    def _check_auth():
        auth = request.headers.get("Authorization", "")
        return auth == f"Bearer {token}"

    @app.route("/api/commands", methods=["POST"])
    def receive_command():
        """Receive a command from the server."""
        if not _check_auth():
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        command_id = data.get("command_id", uuid.uuid4().hex[:16])
        cmd_type = data.get("type", "")
        payload = data.get("payload", {})

        if cmd_type == "run_test":
            streamer = LogStreamer(command_id)
            log_streamers[command_id] = streamer

            import threading

            def _run():
                result = executor.run_benchmark(
                    model_path=payload.get("model_path", ""),
                    engine=payload.get("engine_name", "vllm"),
                    suite=payload.get("suite_name", "quick"),
                    on_log=streamer.emit,
                )
                streamer.emit(f"--- Finished: {result['status']} ---")
                # Report result back to server
                _report_result(server_url, token, name, command_id, result, insecure)

            threading.Thread(target=_run, daemon=True).start()
            return jsonify({"accepted": True}), 202

        elif cmd_type == "cancel":
            if executor.cancel():
                return jsonify({"cancelled": True})
            return jsonify({"error": "No running task"}), 400

        elif cmd_type == "check_engine":
            engine_name = payload.get("engine_name", "")
            try:
                from kitt.engines.registry import EngineRegistry

                EngineRegistry.auto_discover()
                engine_cls = EngineRegistry.get_engine(engine_name)
                diag = engine_cls.diagnose()
                return jsonify(
                    {
                        "available": diag.available,
                        "image": diag.image,
                        "error": diag.error,
                        "guidance": diag.guidance,
                    }
                )
            except Exception as e:
                return jsonify({"available": False, "error": str(e)})

        return jsonify({"error": f"Unknown command type: {cmd_type}"}), 400

    @app.route("/api/logs/<command_id>")
    def stream_logs(command_id):
        """Stream logs for a command as SSE."""
        streamer = log_streamers.get(command_id)
        if streamer is None:
            return jsonify({"error": "No logs for this command"}), 404

        subscriber_id = f"log-{uuid.uuid4().hex[:8]}"
        return Response(
            streamer.subscribe(subscriber_id),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @app.route("/api/status")
    def agent_status():
        """Agent status endpoint."""
        return jsonify(
            {
                "name": name,
                "running": executor.is_running,
                "active_streams": len(log_streamers),
            }
        )

    return app


def _report_result(
    server_url: str,
    token: str,
    agent_name: str,
    command_id: str,
    result: dict[str, Any],
    insecure: bool = False,
) -> None:
    """Report a benchmark result back to the server."""
    import json
    import ssl
    import urllib.request

    url = f"{server_url.rstrip('/')}/api/v1/agents/{agent_name}/results"
    data = json.dumps(
        {
            "command_id": command_id,
            "status": result.get("status", ""),
            "output_dir": result.get("output_dir", ""),
            "error": result.get("error", ""),
        }
    ).encode("utf-8")

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
        if insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            response.read()
    except Exception as e:
        logger.error(f"Failed to report result: {e}")
