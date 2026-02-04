"""kitt engines - Engine management commands."""

import subprocess
import sys

import click
from rich.console import Console
from rich.table import Table

console = Console()

GPU_ENGINES = {"vllm", "llama_cpp"}
SUPPORTED_SETUP_ENGINES = {"vllm"}


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
    from kitt.hardware.detector import (
        check_cuda_compatibility,
        detect_cuda_version,
        detect_torch_cuda_version,
    )

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
        console.print("  Status: [green]Available[/green]")
    else:
        console.print("  Status: [red]Not Available[/red]")
        console.print("  [yellow]Dependencies may be missing. Check installation.[/yellow]")

    # Show CUDA details for GPU-based engines
    if engine_name in GPU_ENGINES:
        system_cuda = detect_cuda_version()
        torch_cuda = detect_torch_cuda_version()

        if system_cuda:
            console.print(f"  System CUDA: {system_cuda}")
        else:
            console.print("  System CUDA: [yellow]not detected[/yellow]")

        if torch_cuda:
            console.print(f"  PyTorch CUDA: {torch_cuda}")
        else:
            console.print("  PyTorch CUDA: [yellow]not installed or CPU-only[/yellow]")

        mismatch = check_cuda_compatibility()
        if mismatch:
            cu_tag = f"cu{mismatch.system_major}0"
            console.print(
                f"  [red]CUDA mismatch:[/red] system CUDA {mismatch.system_cuda} "
                f"vs PyTorch CUDA {mismatch.torch_cuda}"
            )
            console.print(f"  Fix with:")
            console.print(
                f"    pip install torch --index-url https://download.pytorch.org/whl/{cu_tag}"
            )
            console.print(
                f"    pip install vllm --extra-index-url https://download.pytorch.org/whl/{cu_tag}"
            )
            console.print(f"  Or run: kitt engines setup {engine_name}")


@engines.command("setup")
@click.argument("engine_name")
@click.option("--dry-run", is_flag=True, help="Show commands without executing them")
def setup_engine(engine_name, dry_run):
    """Install an engine with the correct CUDA-matched wheels.

    Detects the system CUDA version and installs PyTorch and the engine
    with matching CUDA wheel index URLs.
    """
    from kitt.hardware.detector import detect_cuda_version

    if engine_name not in SUPPORTED_SETUP_ENGINES:
        supported = ", ".join(sorted(SUPPORTED_SETUP_ENGINES))
        console.print(
            f"[red]Engine '{engine_name}' is not supported by setup.[/red]\n"
            f"Supported engines: {supported}"
        )
        raise SystemExit(1)

    system_cuda = detect_cuda_version()
    if not system_cuda:
        console.print(
            "[red]No system CUDA detected.[/red]\n"
            "Install the NVIDIA CUDA toolkit first, or ensure 'nvcc' is on your PATH."
        )
        raise SystemExit(1)

    try:
        cuda_major = int(system_cuda.split(".")[0])
    except (ValueError, IndexError):
        console.print(f"[red]Could not parse CUDA version: {system_cuda}[/red]")
        raise SystemExit(1)

    cu_tag = f"cu{cuda_major}0"
    torch_index = f"https://download.pytorch.org/whl/{cu_tag}"

    commands = [
        [sys.executable, "-m", "pip", "install", "torch", "--index-url", torch_index],
        [
            sys.executable, "-m", "pip", "install", "vllm",
            "--extra-index-url", torch_index,
        ],
    ]

    console.print(f"[bold]Setting up {engine_name} for CUDA {system_cuda} ({cu_tag})[/bold]")

    for cmd in commands:
        cmd_str = " ".join(cmd)
        if dry_run:
            console.print(f"  [dim]would run:[/dim] {cmd_str}")
        else:
            console.print(f"  [cyan]running:[/cyan] {cmd_str}")
            result = subprocess.run(cmd)
            if result.returncode != 0:
                console.print(f"  [red]Command failed with exit code {result.returncode}[/red]")
                raise SystemExit(result.returncode)

    if dry_run:
        console.print("\n[yellow]Dry run — no commands were executed.[/yellow]")
    else:
        console.print(f"\n[green]{engine_name} setup complete.[/green]")
