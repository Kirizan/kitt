"""CLI commands for the KITT agent daemon."""

import logging
import os
import signal
from pathlib import Path

import click
import yaml
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


@click.group()
def agent():
    """Manage the KITT agent daemon."""


@agent.command()
@click.option(
    "--server", required=True, help="KITT server URL (e.g., https://server:8080)"
)
@click.option("--token", default="", help="Bearer token for authentication (optional)")
@click.option("--name", default="", help="Agent name (defaults to hostname)")
@click.option("--port", default=8090, help="Agent listening port")
def init(server, token, name, port):
    """Initialize agent configuration and certificates.

    This fetches the server's CA certificate, generates agent certificates,
    and stores configuration in ~/.kitt/agent.yaml.
    """
    import socket

    agent_name = name or socket.gethostname()
    config_dir = Path.home() / ".kitt"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "agent.yaml"

    config = {
        "name": agent_name,
        "server_url": server,
        "token": token,
        "port": port,
    }

    # Generate agent certificate if server is HTTPS
    if server.startswith("https"):
        try:
            from kitt.security.cert_manager import generate_agent_cert
            from kitt.security.tls_config import DEFAULT_CERTS_DIR

            ca_path = DEFAULT_CERTS_DIR / "ca.pem"
            if not ca_path.exists():
                console.print("[yellow]CA certificate not found locally.[/yellow]")
                console.print("Copy ca.pem from the server to ~/.kitt/certs/ca.pem")
            else:
                cert_path, key_path = generate_agent_cert(agent_name)
                config["tls"] = {
                    "cert": str(cert_path),
                    "key": str(key_path),
                    "ca": str(ca_path),
                }
                console.print(
                    f"[green]Agent certificate generated:[/green] {cert_path}"
                )
        except ImportError:
            console.print(
                "[yellow]cryptography not installed — skipping cert generation[/yellow]"
            )

    # Write config
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    console.print(f"[green]Agent config saved:[/green] {config_path}")
    console.print(f"  Name: {agent_name}")
    console.print(f"  Server: {server}")
    console.print(f"  Port: {port}")
    console.print()
    console.print("Start the agent with: [bold]kitt agent start[/bold]")


@agent.command()
@click.option("--config", "config_path", type=click.Path(), help="Path to agent.yaml")
@click.option("--insecure", is_flag=True, help="Disable TLS verification")
@click.option("--foreground", is_flag=True, help="Run in foreground (no daemonize)")
def start(config_path, insecure, foreground):
    """Start the KITT agent daemon."""
    config_file = (
        Path(config_path) if config_path else Path.home() / ".kitt" / "agent.yaml"
    )

    if not config_file.exists():
        console.print("[red]Agent not configured.[/red]")
        console.print("Run: kitt agent init --server <URL>")
        raise SystemExit(1)

    with open(config_file) as f:
        config = yaml.safe_load(f)

    agent_name = config.get("name", "unknown")
    server_url = config.get("server_url", "")
    token = config.get("token", "")
    port = config.get("port", 8090)

    if not server_url:
        console.print("[red]Invalid agent config — missing server_url[/red]")
        raise SystemExit(1)

    console.print(f"[bold]KITT Agent: {agent_name}[/bold]")
    console.print(f"  Server: {server_url}")
    console.print(f"  Port: {port}")

    # Register with server
    try:
        from kitt.agent.registration import register_with_server

        tls_config = config.get("tls", {})
        verify: str | bool = tls_config.get("ca", True)
        client_cert = None
        if tls_config.get("cert") and tls_config.get("key"):
            client_cert = (tls_config["cert"], tls_config["key"])

        if insecure:
            verify = False

        result = register_with_server(
            server_url=server_url,
            token=token,
            name=agent_name,
            port=port,
            verify=verify,
            client_cert=client_cert,
        )
        agent_id = result.get("agent_id", "")
        heartbeat_interval = result.get("heartbeat_interval_s", 30)
        console.print(f"  [green]Registered:[/green] {agent_id}")
    except Exception as e:
        console.print(f"  [red]Registration failed:[/red] {e}")
        console.print("  Starting anyway — will retry on heartbeat")
        agent_id = agent_name
        heartbeat_interval = 30

    # Start heartbeat thread
    from kitt.agent.heartbeat import HeartbeatThread

    hb = HeartbeatThread(
        server_url=server_url,
        agent_id=agent_id,
        token=token,
        interval_s=heartbeat_interval,
        verify=verify if not insecure else False,
        client_cert=client_cert if not insecure else None,
    )
    hb.start()

    # Start agent Flask app
    try:
        from kitt.agent.daemon import create_agent_app
    except ImportError:
        console.print("[red]Flask is not installed.[/red]")
        console.print("Install with: pip install kitt[web]")
        raise SystemExit(1) from None

    app = create_agent_app(
        name=agent_name,
        server_url=server_url,
        token=token,
        port=port,
        insecure=insecure,
    )

    ssl_ctx = None
    if not insecure:
        tls_config = config.get("tls", {})
        if tls_config.get("cert") and tls_config.get("key"):
            ssl_ctx = (tls_config["cert"], tls_config["key"])

    console.print(f"  Listening on port {port}")
    console.print()

    try:
        app.run(host="0.0.0.0", port=port, ssl_context=ssl_ctx, use_reloader=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Agent stopped[/yellow]")
    finally:
        hb.stop()


@agent.command()
def status():
    """Check agent status."""
    config_file = Path.home() / ".kitt" / "agent.yaml"

    if not config_file.exists():
        console.print("[yellow]Agent not configured[/yellow]")
        return

    with open(config_file) as f:
        config = yaml.safe_load(f)

    console.print("[bold]KITT Agent Status[/bold]")
    console.print(f"  Name: {config.get('name', 'unknown')}")
    console.print(f"  Server: {config.get('server_url', 'not set')}")
    console.print(f"  Port: {config.get('port', 8090)}")

    # Try to reach the local agent
    import urllib.request

    port = config.get("port", 8090)
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/status", timeout=2
        ) as resp:
            import json

            data = json.loads(resp.read())
            console.print("  Running: [green]yes[/green]")
            console.print(f"  Active task: {data.get('running', False)}")
    except Exception:
        console.print("  Running: [red]no[/red]")


@agent.command()
def stop():
    """Stop the KITT agent daemon."""
    pid_file = Path.home() / ".kitt" / "agent.pid"
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            console.print(f"[green]Agent stopped (PID {pid})[/green]")
            pid_file.unlink()
        except ProcessLookupError:
            console.print("[yellow]Agent process not found[/yellow]")
            pid_file.unlink()
    else:
        console.print("[yellow]No PID file found — agent may not be running[/yellow]")
