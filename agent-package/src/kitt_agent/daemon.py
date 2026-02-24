"""KITT thin agent daemon — Flask mini-app that receives Docker commands."""

import logging
import threading
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
    """Create the thin agent Flask app.

    The thin agent receives Docker orchestration commands from the
    KITT server rather than running benchmarks locally.
    """
    if not FLASK_AVAILABLE:
        raise ImportError("Flask is required. Install with: pip install kitt-agent")

    app = Flask(__name__)

    from kitt_agent.docker_ops import ContainerSpec, DockerOps
    from kitt_agent.log_streamer import LogStreamer

    log_streamers: dict[str, LogStreamer] = {}
    active_containers: dict[str, str] = {}  # command_id -> container_id
    _lock = threading.Lock()

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

        if cmd_type == "run_container":
            streamer = LogStreamer(command_id)
            log_streamers[command_id] = streamer

            def _run():
                try:
                    spec = ContainerSpec(
                        image=payload.get("image", ""),
                        port=payload.get("port", 0),
                        container_port=payload.get("container_port", 0),
                        gpu=payload.get("gpu", True),
                        volumes=payload.get("volumes", {}),
                        env=payload.get("env", {}),
                        extra_args=payload.get("extra_args", []),
                        command_args=payload.get("command_args", []),
                        name=payload.get("name", ""),
                        health_url=payload.get("health_url", ""),
                    )

                    # Pull image if needed
                    streamer.emit(f"Pulling image: {spec.image}")
                    DockerOps.pull_image(spec.image)

                    # Start container
                    streamer.emit("Starting container...")
                    container_id = DockerOps.run_container(spec, on_log=streamer.emit)

                    with _lock:
                        active_containers[command_id] = container_id

                    # Wait for health if URL provided
                    if spec.health_url:
                        streamer.emit(f"Waiting for health: {spec.health_url}")
                        healthy = DockerOps.wait_for_healthy(spec.health_url)
                        if not healthy:
                            streamer.emit("Health check timed out")
                            _report(
                                server_url,
                                token,
                                name,
                                command_id,
                                {
                                    "status": "failed",
                                    "error": "Health check timeout",
                                    "container_id": container_id,
                                },
                                insecure,
                            )
                            return

                    streamer.emit(f"Container healthy: {container_id}")

                    # Stream logs
                    DockerOps.stream_logs(container_id, on_log=streamer.emit)

                    streamer.emit("--- Container exited ---")
                    _report(
                        server_url,
                        token,
                        name,
                        command_id,
                        {"status": "completed", "container_id": container_id},
                        insecure,
                    )
                except Exception as e:
                    streamer.emit(f"Error: {e}")
                    _report(
                        server_url,
                        token,
                        name,
                        command_id,
                        {"status": "failed", "error": str(e)},
                        insecure,
                    )
                finally:
                    with _lock:
                        active_containers.pop(command_id, None)
                        log_streamers.pop(command_id, None)

            threading.Thread(target=_run, daemon=True).start()
            return jsonify({"accepted": True, "command_id": command_id}), 202

        elif cmd_type == "stop_container":
            target_cmd = payload.get("command_id", "")
            with _lock:
                cid = active_containers.get(target_cmd)
            if cid:
                DockerOps.stop_container(cid)
                return jsonify({"stopped": True})
            return jsonify({"error": "No active container for this command"}), 404

        elif cmd_type == "check_docker":
            return jsonify({"available": DockerOps.is_available()})

        # Legacy: still support run_test for backward compatibility
        elif cmd_type == "run_test":
            _VALID_ENGINES = {"vllm", "tgi", "llama_cpp", "ollama"}
            _VALID_SUITES = {"quick", "standard", "performance"}

            engine = payload.get("engine_name", "vllm")
            suite = payload.get("suite_name", "quick")
            if engine not in _VALID_ENGINES:
                return jsonify({"error": f"Invalid engine: {engine}"}), 400
            if suite not in _VALID_SUITES:
                return jsonify({"error": f"Invalid suite: {suite}"}), 400

            streamer = LogStreamer(command_id)
            log_streamers[command_id] = streamer

            def _run_legacy():
                import subprocess as sp

                args = [
                    "kitt",
                    "run",
                    "-m",
                    payload.get("model_path", ""),
                    "-e",
                    engine,
                    "-s",
                    suite,
                ]
                try:
                    proc = sp.Popen(
                        args,
                        stdout=sp.PIPE,
                        stderr=sp.STDOUT,
                        text=True,
                        bufsize=1,
                    )
                    for line in proc.stdout or []:
                        streamer.emit(line.rstrip())
                    proc.wait()
                    status = "completed" if proc.returncode == 0 else "failed"
                    streamer.emit(f"--- Finished: {status} ---")
                    _report(
                        server_url,
                        token,
                        name,
                        command_id,
                        {
                            "status": status,
                            "error": ""
                            if status == "completed"
                            else f"Exit {proc.returncode}",
                        },
                        insecure,
                    )
                except Exception as e:
                    streamer.emit(f"Error: {e}")
                    _report(
                        server_url,
                        token,
                        name,
                        command_id,
                        {"status": "failed", "error": str(e)},
                        insecure,
                    )

            threading.Thread(target=_run_legacy, daemon=True).start()
            return jsonify({"accepted": True, "command_id": command_id}), 202

        return jsonify({"error": f"Unknown command type: {cmd_type}"}), 400

    @app.route("/api/logs/<command_id>")
    def stream_logs_endpoint(command_id):
        """Stream logs for a command as SSE."""
        if not _check_auth():
            return jsonify({"error": "Unauthorized"}), 401
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
        with _lock:
            container_count = len(active_containers)
            stream_count = len(log_streamers)
        return jsonify(
            {
                "name": name,
                "running": container_count > 0,
                "active_containers": container_count,
                "active_streams": stream_count,
            }
        )

    return app


def _report(
    server_url: str,
    token: str,
    agent_name: str,
    command_id: str,
    result: dict[str, Any],
    insecure: bool = False,
    verify: str | bool = True,
    client_cert: tuple[str, str] | None = None,
) -> None:
    """Report a result back to the server."""
    import json
    import ssl
    import urllib.request
    from urllib.parse import quote

    url = f"{server_url.rstrip('/')}/api/v1/agents/{quote(agent_name, safe='')}/results"
    data = json.dumps(
        {
            "command_id": command_id,
            "status": result.get("status", ""),
            "container_id": result.get("container_id", ""),
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
        if isinstance(verify, str):
            ctx.load_verify_locations(verify)
        elif not verify or insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        if client_cert:
            ctx.load_cert_chain(client_cert[0], client_cert[1])

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            response.read()
    except Exception as e:
        logger.error(f"Failed to report result: {e}")
