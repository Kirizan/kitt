"""CLI for the KITT thin agent."""

import logging
import os
import signal
import socket
from pathlib import Path

import click
import yaml

logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
def cli():
    """KITT thin agent — Docker orchestration daemon."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


@cli.command()
@click.option(
    "--server", required=True, help="KITT server URL (e.g., https://server:8080)"
)
@click.option("--token", required=True, help="Bearer token for authentication")
@click.option("--name", default="", help="Agent name (defaults to hostname)")
@click.option("--port", default=8090, help="Agent listening port")
def init(server, token, name, port):
    """Initialize agent configuration."""
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

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    click.echo(f"Agent config saved: {config_path}")
    click.echo(f"  Name: {agent_name}")
    click.echo(f"  Server: {server}")
    click.echo(f"  Port: {port}")
    click.echo()
    click.echo("Start the agent with: kitt-agent start")


@cli.command()
@click.option("--config", "config_path", type=click.Path(), help="Path to agent.yaml")
@click.option("--insecure", is_flag=True, help="Disable TLS verification")
def start(config_path, insecure):
    """Start the KITT agent daemon."""
    config_file = (
        Path(config_path) if config_path else Path.home() / ".kitt" / "agent.yaml"
    )

    if not config_file.exists():
        click.echo("Agent not configured. Run: kitt-agent init --server <URL> --token <TOKEN>")
        raise SystemExit(1)

    with open(config_file) as f:
        config = yaml.safe_load(f)

    agent_name = config.get("name", "unknown")
    server_url = config.get("server_url", "")
    token = config.get("token", "")
    port = config.get("port", 8090)

    if not server_url or not token:
        click.echo("Invalid agent config — missing server_url or token")
        raise SystemExit(1)

    click.echo(f"KITT Agent: {agent_name}")
    click.echo(f"  Server: {server_url}")
    click.echo(f"  Port: {port}")

    # Register
    try:
        from kitt_agent.registration import register_with_server

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
        click.echo(f"  Registered: {agent_id}")
    except Exception as e:
        click.echo(f"  Registration failed: {e}")
        click.echo("  Starting anyway — will retry on heartbeat")
        agent_id = agent_name
        heartbeat_interval = 30

    # Heartbeat
    from kitt_agent.heartbeat import HeartbeatThread

    hb = HeartbeatThread(
        server_url=server_url,
        agent_id=agent_id,
        token=token,
        interval_s=heartbeat_interval,
        verify=verify if not insecure else False,
        client_cert=client_cert if not insecure else None,
    )
    hb.start()

    # Flask app
    from kitt_agent.daemon import create_agent_app

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

    click.echo(f"  Listening on port {port}")
    click.echo()

    try:
        app.run(host="0.0.0.0", port=port, ssl_context=ssl_ctx, use_reloader=False)
    except KeyboardInterrupt:
        click.echo("\nAgent stopped")
    finally:
        hb.stop()


@cli.command()
def status():
    """Check agent status."""
    config_file = Path.home() / ".kitt" / "agent.yaml"

    if not config_file.exists():
        click.echo("Agent not configured")
        return

    with open(config_file) as f:
        config = yaml.safe_load(f)

    click.echo("KITT Agent Status")
    click.echo(f"  Name: {config.get('name', 'unknown')}")
    click.echo(f"  Server: {config.get('server_url', 'not set')}")
    click.echo(f"  Port: {config.get('port', 8090)}")

    import json
    import urllib.request

    port = config.get("port", 8090)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=2) as resp:
            data = json.loads(resp.read())
            click.echo("  Running: yes")
            click.echo(f"  Active containers: {data.get('active_containers', 0)}")
    except Exception:
        click.echo("  Running: no")


@cli.command()
def stop():
    """Stop the KITT agent daemon."""
    pid_file = Path.home() / ".kitt" / "agent.pid"
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            click.echo(f"Agent stopped (PID {pid})")
            pid_file.unlink()
        except ProcessLookupError:
            click.echo("Agent process not found")
            pid_file.unlink()
    else:
        click.echo("No PID file found — agent may not be running")
