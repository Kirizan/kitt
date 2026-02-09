"""CLI commands for managing the monitoring stack."""

import logging
import subprocess
from pathlib import Path

import click
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

COMPOSE_DIR = Path(__file__).parent.parent.parent.parent / "docker" / "monitoring"


@click.group()
def monitoring():
    """Manage the Grafana/Prometheus monitoring stack."""


@monitoring.command()
@click.option(
    "--compose-dir",
    type=click.Path(exists=True),
    default=None,
    help="Path to docker-compose directory (auto-detected by default).",
)
def start(compose_dir):
    """Start the monitoring stack (Prometheus, Grafana, InfluxDB)."""
    compose_path = Path(compose_dir) if compose_dir else _find_compose_dir()
    if not compose_path:
        console.print("[red]Could not find docker/monitoring/ directory.[/red]")
        console.print("Specify with --compose-dir or run from the KITT project root.")
        raise SystemExit(1)

    console.print("[bold]Starting KITT monitoring stack...[/bold]")
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=str(compose_path),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        console.print("[red]Failed to start monitoring stack:[/red]")
        console.print(result.stderr)
        raise SystemExit(1)

    console.print("[green]Monitoring stack started:[/green]")
    console.print("  Grafana:    http://localhost:3000  (admin/kitt)")
    console.print("  Prometheus: http://localhost:9090")
    console.print("  InfluxDB:   http://localhost:8086")


@monitoring.command()
@click.option(
    "--compose-dir",
    type=click.Path(exists=True),
    default=None,
    help="Path to docker-compose directory.",
)
def stop(compose_dir):
    """Stop the monitoring stack."""
    compose_path = Path(compose_dir) if compose_dir else _find_compose_dir()
    if not compose_path:
        console.print("[red]Could not find docker/monitoring/ directory.[/red]")
        raise SystemExit(1)

    console.print("[bold]Stopping KITT monitoring stack...[/bold]")
    result = subprocess.run(
        ["docker", "compose", "down"],
        cwd=str(compose_path),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        console.print("[red]Failed to stop monitoring stack:[/red]")
        console.print(result.stderr)
        raise SystemExit(1)

    console.print("[green]Monitoring stack stopped.[/green]")


@monitoring.command()
@click.option(
    "--compose-dir",
    type=click.Path(exists=True),
    default=None,
    help="Path to docker-compose directory.",
)
def status(compose_dir):
    """Show monitoring stack status."""
    compose_path = Path(compose_dir) if compose_dir else _find_compose_dir()
    if not compose_path:
        console.print("[red]Could not find docker/monitoring/ directory.[/red]")
        raise SystemExit(1)

    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "table"],
        cwd=str(compose_path),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        console.print("[yellow]Monitoring stack is not running.[/yellow]")
        return

    if result.stdout.strip():
        console.print("[bold]Monitoring Stack Status:[/bold]")
        console.print(result.stdout)
    else:
        console.print("[yellow]No monitoring containers running.[/yellow]")


def _find_compose_dir() -> Path | None:
    """Find the docker/monitoring directory relative to the project."""
    # Try relative to this file (installed package)
    if COMPOSE_DIR.exists():
        return COMPOSE_DIR

    # Try current working directory
    cwd_path = Path.cwd() / "docker" / "monitoring"
    if cwd_path.exists():
        return cwd_path

    return None
