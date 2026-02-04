"""kitt engines - Engine management commands."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def engines():
    """Manage inference engines."""


@engines.command("list")
def list_engines():
    """List all registered inference engines and their availability."""
    from kitt.engines.registry import EngineRegistry

    EngineRegistry.auto_discover()

    table = Table(title="Inference Engines")
    table.add_column("Engine", style="cyan")
    table.add_column("Image")
    table.add_column("Status", style="bold")
    table.add_column("Formats")

    for name in sorted(EngineRegistry.list_all()):
        engine_cls = EngineRegistry.get_engine(name)
        available = engine_cls.is_available()
        status = "[green]Ready[/green]" if available else "[red]Not Pulled[/red]"
        table.add_row(
            name,
            engine_cls.default_image(),
            status,
            ", ".join(engine_cls.supported_formats()),
        )

    console.print(table)


@engines.command("check")
@click.argument("engine_name")
def check_engine(engine_name):
    """Check if a specific engine is available and show details."""
    from kitt.engines.registry import EngineRegistry

    EngineRegistry.auto_discover()

    try:
        engine_cls = EngineRegistry.get_engine(engine_name)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    diag = engine_cls.diagnose()

    console.print(f"[bold]Engine: {engine_name}[/bold]")
    console.print(f"  Image: {diag.image}")
    console.print(f"  Formats: {', '.join(engine_cls.supported_formats())}")

    if diag.available:
        console.print("  Status: [green]Available[/green]")
    else:
        console.print("  Status: [red]Not Available[/red]")
        if diag.error:
            console.print(f"  [yellow]Error: {diag.error}[/yellow]")
        if diag.guidance:
            console.print(f"  [bold]Fix:[/bold] {diag.guidance}")


@engines.command("setup")
@click.argument("engine_name")
@click.option("--dry-run", is_flag=True, help="Show commands without executing them")
def setup_engine(engine_name, dry_run):
    """Pull the Docker image for an engine."""
    from kitt.engines.docker_manager import DockerManager
    from kitt.engines.registry import EngineRegistry

    EngineRegistry.auto_discover()

    try:
        engine_cls = EngineRegistry.get_engine(engine_name)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    image = engine_cls.default_image()

    if not DockerManager.is_docker_available():
        console.print("[red]Docker is not installed or not running.[/red]")
        console.print("Install Docker: https://docs.docker.com/get-docker/")
        raise SystemExit(1)

    if dry_run:
        console.print(f"  [dim]would run:[/dim] docker pull {image}")
        console.print("\n[yellow]Dry run — no commands were executed.[/yellow]")
        return

    console.print(f"Pulling {image}...")
    try:
        DockerManager.pull_image(image)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    console.print(f"[green]{engine_name} ready.[/green]")
