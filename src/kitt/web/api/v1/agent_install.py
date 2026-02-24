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

AGENT_PACKAGE_DIR = Path(__file__).parent.parent.parent.parent.parent / "agent-package"

_INSTALL_SCRIPT = """\
#!/usr/bin/env bash
set -euo pipefail

KITT_SERVER={server_url}
KITT_TOKEN={token}
AGENT_PORT={port}
AGENT_NAME="$(hostname)"
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
curl -sfL "$KITT_SERVER/api/v1/agent/package" \\
    -o "$TMPFILE"

# Install
echo "==> Installing agent package"
"$VENV_DIR/bin/pip" install "$TMPFILE" -q
rm -f "$TMPFILE"

# Configure
echo "==> Configuring agent"
"$VENV_DIR/bin/kitt-agent" init \\
    --server "$KITT_SERVER" \\
    --token "$KITT_TOKEN" \\
    --name "$AGENT_NAME" \\
    --port "$AGENT_PORT"

echo ""
echo "==> Agent installed successfully!"
echo "    Start with: $VENV_DIR/bin/kitt-agent start"
echo ""
echo "    Or install as systemd service:"
echo "    cat > /tmp/kitt-agent.service << 'UNIT'"
echo "    [Unit]"
echo "    Description=KITT Agent"
echo "    After=network-online.target docker.service"
echo "    Wants=network-online.target"
echo "    [Service]"
echo "    Type=simple"
echo "    User=$(whoami)"
echo "    ExecStart=$VENV_DIR/bin/kitt-agent start"
echo "    Restart=always"
echo "    RestartSec=10"
echo "    [Install]"
echo "    WantedBy=multi-user.target"
echo "    UNIT"
echo "    sudo cp /tmp/kitt-agent.service /etc/systemd/system/"
echo "    sudo systemctl enable --now kitt-agent"
"""


@bp.route("/install.sh")
def install_script():
    """Serve the agent bootstrap install script.

    Query params:
        port: Agent listening port (default 8090).
    """
    token = current_app.config.get("AUTH_TOKEN", "")
    port_str = request.args.get("port", "8090")

    # Validate port is numeric
    try:
        port_int = int(port_str)
        if not (1 <= port_int <= 65535):
            return Response("Invalid port number", status=400)
    except ValueError:
        return Response("Port must be a number", status=400)

    # Build the server URL from the request
    server_url = request.url_root.rstrip("/")

    script = _INSTALL_SCRIPT.format(
        server_url=shlex.quote(server_url),
        token=shlex.quote(token),
        port=port_int,
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
