"""Agent installation API — serves the bootstrap script and agent package."""

import logging
import shlex
import subprocess
import tempfile
import threading
from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, request, send_file

logger = logging.getLogger(__name__)

bp = Blueprint("api_agent_install", __name__, url_prefix="/api/v1/agent")

# Cache the built sdist path so we only build once per process.
_sdist_cache: dict[str, Path | None] = {"path": None}
_build_lock = threading.Lock()

AGENT_PACKAGE_DIR = (
    Path(__file__).parent.parent.parent.parent.parent.parent / "agent-package"
)

_INSTALL_SCRIPT = """\
#!/usr/bin/env bash
set -euo pipefail

KITT_SERVER={server_url}
KITT_TOKEN={token}
AGENT_PORT={port}
AGENT_NAME={agent_name}
AGENT_DIR="$HOME/.kitt"
VENV_DIR="$AGENT_DIR/agent-venv"

echo "==> Installing KITT agent from $KITT_SERVER"

# Create directories
mkdir -p "$AGENT_DIR"

# Create virtual environment
echo "==> Creating virtual environment at $VENV_DIR"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q

# Download agent package
echo "==> Downloading agent package"
TMPFILE="$(mktemp /tmp/kitt-agent-XXXXXX.tar.gz)"
curl -fL "$KITT_SERVER/api/v1/agent/package" \\
    -o "$TMPFILE"

# Install
echo "==> Installing agent package"
"$VENV_DIR/bin/pip" install "$TMPFILE" -q
rm -f "$TMPFILE"

# Configure with provisioned token
echo "==> Configuring agent"
"$VENV_DIR/bin/kitt-agent" init --server "$KITT_SERVER" --name "$AGENT_NAME" \\
    --port "$AGENT_PORT" --token "$KITT_TOKEN"

echo ""
echo "==> Agent installed successfully!"
echo "    Start with: $VENV_DIR/bin/kitt-agent start"
echo ""
echo "    Or install as a service:"
echo "    $VENV_DIR/bin/kitt-agent service install"
"""


@bp.route("/install.sh")
def install_script():
    """Serve the agent bootstrap install script.

    Provisions a unique per-agent token at serve time. Each request
    generates a new token — the raw token is embedded in the script
    and the server stores only its SHA-256 hash.

    Query params:
        port: Agent listening port (default 8090).
        name: Agent name (default: uses $(hostname) at install time).
    """
    port_str = request.args.get("port", "8090")
    name_param = request.args.get("name", "")

    # Validate port is numeric
    try:
        port_int = int(port_str)
        if not (1 <= port_int <= 65535):
            return Response("Invalid port number", status=400)
    except ValueError:
        return Response("Port must be a number", status=400)

    # Build the server URL from the request
    server_url = request.url_root.rstrip("/")

    # Provision the agent — generates a unique token, stores hash in DB.
    # If name is provided, provision now. Otherwise the script uses
    # $(hostname) — we provision with a placeholder and the agent
    # re-provisions on registration.
    from kitt.web.app import get_services

    mgr = get_services()["agent_manager"]

    if name_param:
        result = mgr.provision(name_param, port_int)
        raw_token = result["token"]
        agent_name = shlex.quote(name_param)
    else:
        # Use $(hostname) — provision with hostname at install time
        # The script will embed $(hostname) as the name
        agent_name = '"$(hostname)"'
        # Generate a token for a placeholder name; the agent will
        # re-register with its real hostname and this token
        import socket

        placeholder_name = f"pending-{socket.getfqdn()}-{port_int}"
        result = mgr.provision(placeholder_name, port_int)
        raw_token = result["token"]

    script = _INSTALL_SCRIPT.format(
        server_url=shlex.quote(server_url),
        token=shlex.quote(raw_token),
        port=port_int,
        agent_name=agent_name,
    )
    return Response(script, mimetype="text/x-shellscript")


@bp.route("/package")
def package():
    """Serve the agent package as a tarball (sdist)."""
    sdist_path = _get_or_build_package()
    if sdist_path is None:
        return jsonify({"error": "Failed to build agent package"}), 500

    return send_file(
        sdist_path,
        mimetype="application/gzip",
        as_attachment=True,
        download_name=sdist_path.name,
    )


def _get_or_build_package() -> Path | None:
    """Build the agent sdist if not already cached."""
    with _build_lock:
        if _sdist_cache["path"] and _sdist_cache["path"].exists():
            return _sdist_cache["path"]

        if not AGENT_PACKAGE_DIR.exists():
            logger.error(f"Agent package directory not found: {AGENT_PACKAGE_DIR}")
            return None

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = subprocess.run(
                    ["python", "-m", "build", "--sdist", "--outdir", tmpdir],
                    cwd=str(AGENT_PACKAGE_DIR),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    logger.error(f"Agent package build failed: {result.stderr}")
                    return None

                tarballs = list(Path(tmpdir).glob("*.tar.gz"))
                if not tarballs:
                    logger.error("No tarball produced by build")
                    return None

                # Copy to a persistent location
                dest_dir = Path.home() / ".kitt" / "agent-dist"
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / tarballs[0].name

                import shutil

                shutil.copy2(tarballs[0], dest)
                _sdist_cache["path"] = dest
                logger.info(f"Agent package built: {dest}")
                return dest

        except Exception as e:
            logger.error(f"Failed to build agent package: {e}")
            return None
