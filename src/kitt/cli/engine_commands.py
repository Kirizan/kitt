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
    table.add_column("Status", style="bold")
    table.add_column("Formats")

    for name in sorted(EngineRegistry.list_all()):
        engine_cls = EngineRegistry.get_engine(name)
        available = engine_cls.is_available()
        status = "[green]Available[/green]" if available else "[red]Not Available[/red]"
        formats = ", ".join(engine_cls.supported_formats())
        table.add_row(name, status, formats)

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

    console.print(f"[bold]Engine: {engine_name}[/bold]")
    console.print(f"  Formats: {', '.join(engine_cls.supported_formats())}")

    available = engine_cls.is_available()
    if available:
        console.print(f"  Status: [green]Available[/green]")
    else:
        console.print(f"  Status: [red]Not Available[/red]")
        console.print(f"  [yellow]Dependencies may be missing. Check installation.[/yellow]")
