"""kitt engines - Engine management commands."""

import subprocess
import sys
import textwrap

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

    diag = engine_cls.diagnose()

    console.print(f"[bold]Engine: {engine_name}[/bold]")
    console.print(f"  Formats: {', '.join(engine_cls.supported_formats())}")

    check_label = "Server check" if diag.engine_type == "http_server" else "Import check"
    console.print(f"  Check: {check_label}")

    if diag.available:
        console.print("  Status: [green]Available[/green]")
        if diag.guidance:
            console.print(f"  [dim]{diag.guidance}[/dim]")
    else:
        console.print("  Status: [red]Not Available[/red]")
        if diag.error:
            console.print(f"  [yellow]Error: {diag.error}[/yellow]")
        if diag.guidance:
            console.print("  [bold]Suggested fix:[/bold]")
            for line in diag.guidance.splitlines():
                console.print(f"    {line}")

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
                f"    pip install torch --force-reinstall --index-url https://download.pytorch.org/whl/{cu_tag}"
            )
            console.print(
                f"    pip install vllm --force-reinstall --extra-index-url https://download.pytorch.org/whl/{cu_tag}"
            )
            console.print(f"  Or run: kitt engines setup {engine_name}")


@engines.command("setup")
@click.argument("engine_name")
@click.option("--dry-run", is_flag=True, help="Show commands without executing them")
@click.option("--verbose", is_flag=True, help="Show full pip output")
def setup_engine(engine_name, dry_run, verbose):
    """Install an engine with the correct CUDA-matched wheels.

    Detects the system CUDA version and installs PyTorch and the engine
    with matching CUDA wheel index URLs.  Pip output is suppressed by
    default; use --verbose to see it.
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

    # Suppress pip output unless --verbose is passed.  When quiet, capture
    # both stdout and stderr so notices / dep-resolver warnings don't clutter
    # the screen.  Captured stderr is shown if the command fails.
    pip_kwargs: dict = {} if verbose else {"capture_output": True, "text": True}

    # Use --force-reinstall so pip replaces existing wheels even if the
    # version number matches, and --no-deps so transitive dependencies
    # aren't forcefully reinstalled (which would pull versions that
    # conflict with KITT's own constraints).
    commands = [
        [
            sys.executable, "-m", "pip", "install", "torch",
            "--force-reinstall", "--no-deps", "--index-url", torch_index,
        ],
        [
            sys.executable, "-m", "pip", "install", "vllm",
            "--force-reinstall", "--no-deps", "--extra-index-url", torch_index,
        ],
    ]

    # After replacing torch/vllm wheels, reinstall their missing
    # dependencies (without --force-reinstall) so pip only fetches
    # what is actually needed.
    dep_commands = [
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
            result = subprocess.run(cmd, **pip_kwargs)
            if result.returncode != 0:
                console.print(f"  [red]Command failed with exit code {result.returncode}[/red]")
                if not verbose and result.stderr:
                    console.print(f"  {result.stderr.strip()}")
                raise SystemExit(result.returncode)

    console.print()
    if not dry_run:
        console.print("[bold]Installing dependencies...[/bold]")

    for cmd in dep_commands:
        cmd_str = " ".join(cmd)
        if dry_run:
            console.print(f"  [dim]would run:[/dim] {cmd_str}")
        else:
            console.print(f"  [cyan]running:[/cyan] {cmd_str}")
            result = subprocess.run(cmd, **pip_kwargs)
            if result.returncode != 0:
                console.print(f"  [red]Command failed with exit code {result.returncode}[/red]")
                if not verbose and result.stderr:
                    console.print(f"  {result.stderr.strip()}")
                raise SystemExit(result.returncode)

    # Re-pin torch after dependency resolution.  Step 4 (pip install vllm
    # --extra-index-url) may silently replace the cu{N}0 torch with a cu12
    # build from PyPI.  Force-reinstalling torch with --no-deps undoes that.
    torch_fixup_cmd = [
        sys.executable, "-m", "pip", "install", "torch",
        "--force-reinstall", "--no-deps", "--index-url", torch_index,
    ]
    fixup_str = " ".join(torch_fixup_cmd)
    if dry_run:
        console.print(f"  [dim]would run:[/dim] {fixup_str}")
    else:
        console.print()
        console.print("[bold]Re-pinning torch to correct CUDA index...[/bold]")
        console.print(f"  [cyan]running:[/cyan] {fixup_str}")
        result = subprocess.run(torch_fixup_cmd, **pip_kwargs)
        if result.returncode != 0:
            console.print(f"  [red]Command failed with exit code {result.returncode}[/red]")
            if not verbose and result.stderr:
                console.print(f"  {result.stderr.strip()}")
            raise SystemExit(result.returncode)

    if dry_run:
        console.print("\n[yellow]Dry run — no commands were executed.[/yellow]")
        return

    # Verify the install actually worked by importing vllm, loading its CUDA
    # C extensions (from vllm import LLM), and initialising the CUDA runtime.
    console.print()
    console.print("[bold]Verifying installation...[/bold]")

    verify_script = textwrap.dedent("""\
        import sys
        import vllm
        from vllm import LLM
        import torch
        print(f'torch_cuda={torch.version.cuda}')
        if torch.cuda.is_available():
            try:
                torch.zeros(1, device='cuda')
                print(f'device={torch.cuda.get_device_name(0)}')
            except Exception as e:
                print(str(e), file=sys.stderr)
                sys.exit(2)
        print('ok')
    """)

    verify = subprocess.run(
        [sys.executable, "-c", verify_script],
        capture_output=True,
        text=True,
    )

    if verify.returncode == 0 and "ok" in verify.stdout:
        # Parse diagnostic info from stdout
        torch_cuda = ""
        device_name = ""
        for line in verify.stdout.splitlines():
            if line.startswith("torch_cuda="):
                torch_cuda = line.split("=", 1)[1]
            elif line.startswith("device="):
                device_name = line.split("=", 1)[1]
        msg = f"[green]{engine_name} setup complete — import verified.[/green]"
        if torch_cuda:
            msg += f"\n  PyTorch CUDA: {torch_cuda}"
        if device_name:
            msg += f"\n  GPU: {device_name}"
        console.print(msg)
    else:
        stderr = verify.stderr.strip()
        # Parse torch_cuda from stdout even on failure (it may have printed
        # before the error).
        torch_cuda = ""
        for line in verify.stdout.splitlines():
            if line.startswith("torch_cuda="):
                torch_cuda = line.split("=", 1)[1]

        if verify.returncode == 2:
            console.print(f"[red]{engine_name} installed but CUDA initialization failed.[/red]")
        else:
            console.print(f"[red]{engine_name} installed but import failed.[/red]")

        if torch_cuda:
            console.print(f"  PyTorch CUDA: {torch_cuda}")

        # Check if it's a CUDA library mismatch
        if "libcudart" in stderr or "libcuda" in stderr:
            import re

            match = re.search(r"libcuda\w*\.so\.(\d+)", stderr)
            lib_major = int(match.group(1)) if match else None
            if lib_major and lib_major != cuda_major:
                console.print(
                    f"\n  The installed vLLM package requires CUDA {lib_major} "
                    f"runtime libraries but this system has CUDA {system_cuda}."
                )
                console.print(
                    f"  CUDA {cuda_major} wheels for vLLM may not be available yet.\n"
                )
                console.print("  Options:")
                console.print(
                    f"    1. Install the CUDA {lib_major} compatibility package:"
                )
                console.print(f"         sudo apt install cuda-compat-{lib_major}")
                console.print(
                    f"    2. Build vLLM from source against CUDA {cuda_major}:"
                )
                console.print("         pip install vllm --no-binary vllm")
                console.print("    3. Check for a nightly/pre-release wheel:")
                console.print(
                    f"         pip install vllm --pre --extra-index-url "
                    f"https://download.pytorch.org/whl/nightly/{cu_tag}"
                )
            else:
                console.print(f"\n  Error: {stderr[:2000]}")
        else:
            console.print(f"\n  Error: {stderr[:500]}")
        raise SystemExit(1)
