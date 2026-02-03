"""KITT CLI - Main entry point."""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="1.1.0", prog_name="KITT")
def cli():
    """KITT - Kirby's Inference Testing Tools

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
@click.option("--port", default=8080, help="Port for web UI")
def web(port):
    """Launch web UI for result comparison."""
    console.print(f"[yellow]Starting web UI on port {port}...[/yellow]")
    console.print("[red]Web UI not yet implemented (planned for Phase 4)[/red]")


if __name__ == "__main__":
    cli()
