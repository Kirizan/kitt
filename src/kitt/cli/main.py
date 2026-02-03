"""KITT CLI - Main entry point."""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="1.1.0", prog_name="KITT")
def cli():
    """KITT - Kirizan's Inference Testing Tools

    End-to-end testing suite for LLM inference engines.
    """


from .engine_commands import engines  # noqa: E402
from .results_commands import results  # noqa: E402
from .run import run  # noqa: E402
from .test_commands import test  # noqa: E402

cli.add_command(run)
cli.add_command(test)
cli.add_command(engines)
cli.add_command(results)


@cli.command()
@click.option("--verbose", is_flag=True, help="Show detailed hardware info")
def fingerprint(verbose):
    """Display hardware fingerprint for this system."""
    from kitt.hardware.fingerprint import HardwareFingerprint

    if verbose:
        info = HardwareFingerprint.detect_system()
        console.print()
        console.print("[bold]System Information[/bold]")
        console.print(f"  Environment: {info.environment_type}")
        console.print(f"  OS: {info.os}")
        console.print(f"  Kernel: {info.kernel}")
        if info.gpu:
            gpu_str = f"{info.gpu.model} ({info.gpu.vram_gb}GB)"
            if info.gpu.count > 1:
                gpu_str += f" x{info.gpu.count}"
            console.print(f"  GPU: {gpu_str}")
        elif info.environment_type in ("dgx_spark", "dgx"):
            console.print(
                "  GPU: [red]Not detected[/red] "
                "(expected on this system — check NVIDIA drivers and permissions)"
            )
        else:
            console.print("  GPU: [yellow]None detected[/yellow]")
        console.print(f"  CPU: {info.cpu.model} ({info.cpu.cores}c/{info.cpu.threads}t)")
        console.print(f"  RAM: {info.ram_gb}GB {info.ram_type}")
        console.print(f"  Storage: {info.storage.brand} {info.storage.model} ({info.storage.type})")
        if info.cuda_version:
            console.print(f"  CUDA: {info.cuda_version}")
        if info.driver_version:
            console.print(f"  Driver: {info.driver_version}")

    fp = HardwareFingerprint.generate()
    console.print(f"\n[bold green]Hardware Fingerprint:[/bold green] {fp}")


@cli.command()
@click.argument("runs", nargs=-1, required=True)
def compare(runs):
    """Launch TUI for comparing benchmark results.

    Pass paths to result directories or metrics.json files.

    Example: kitt compare ./result-1 ./result-2
    """
    from kitt.cli.compare_tui import check_textual_available, launch_comparison_tui

    if not check_textual_available():
        console.print("[red]Textual is not installed.[/red]")
        console.print("Install with: pip install kitt[cli_ui]")
        raise SystemExit(1)

    launch_comparison_tui(list(runs))


@cli.command()
@click.option("--port", default=8080, help="Port for web UI")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--results-dir", type=click.Path(exists=True), help="Results directory")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def web(port, host, results_dir, debug):
    """Launch web dashboard for viewing results."""
    try:
        from kitt.web.app import create_app
    except ImportError:
        console.print("[red]Flask is not installed.[/red]")
        console.print("Install with: pip install kitt[web]")
        raise SystemExit(1)

    console.print(f"[bold]KITT Web Dashboard[/bold]")
    console.print(f"  URL: http://{host}:{port}")
    console.print(f"  Results: {results_dir or 'current directory'}")
    console.print()

    app = create_app(results_dir)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    cli()
