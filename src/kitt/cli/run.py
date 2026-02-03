"""kitt run - Execute benchmarks against a model."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--model", "-m",
    required=True,
    help="Path to model or model identifier",
)
@click.option(
    "--engine", "-e",
    required=True,
    help="Inference engine to use (vllm, tgi, llama_cpp, ollama)",
)
@click.option(
    "--suite", "-s",
    default="quick",
    help="Test suite to run (quick, standard, performance)",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output directory for results",
)
@click.option(
    "--skip-warmup",
    is_flag=True,
    help="Skip warmup phase for all benchmarks",
)
@click.option(
    "--runs",
    type=int,
    default=None,
    help="Override number of runs per benchmark",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to custom configuration file",
)
def run(model, engine, suite, output, skip_warmup, runs, config):
    """Run benchmarks against a model using a specified engine."""
    from kitt.benchmarks.loader import BenchmarkLoader
    from kitt.benchmarks.registry import BenchmarkRegistry
    from kitt.config.loader import load_suite_config
    from kitt.engines.registry import EngineRegistry
    from kitt.hardware.fingerprint import HardwareFingerprint
    from kitt.reporters.json_reporter import save_json_report
    from kitt.reporters.markdown import generate_summary
    from kitt.runners.suite import SuiteRunner

    # Discover engines
    EngineRegistry.auto_discover()

    # Validate engine
    all_engines = EngineRegistry.list_all()
    if engine not in all_engines:
        console.print(
            f"[red]Engine '{engine}' not found.[/red] "
            f"Available: {', '.join(all_engines)}"
        )
        raise SystemExit(1)

    engine_cls = EngineRegistry.get_engine(engine)
    if not engine_cls.is_available():
        console.print(
            f"[yellow]Warning: Engine '{engine}' is registered but "
            f"dependencies may not be fully available.[/yellow]"
        )

    console.print(f"[bold]KITT Benchmark Runner[/bold]")
    console.print(f"  Model:  {model}")
    console.print(f"  Engine: {engine}")
    console.print(f"  Suite:  {suite}")
    console.print()

    # Load suite config
    suite_config_path = _find_suite_config(suite)
    if suite_config_path:
        suite_cfg = load_suite_config(suite_config_path)
        console.print(f"  Loaded suite: {suite_cfg.suite_name} v{suite_cfg.version}")
    else:
        console.print(f"[yellow]Suite config '{suite}' not found, using defaults[/yellow]")

    # Detect hardware
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Detecting hardware...", total=None)
        system_info = HardwareFingerprint.detect_system()
        progress.update(task, description="Hardware detected")

    # Initialize engine
    console.print(f"\n[cyan]Initializing {engine} engine...[/cyan]")
    engine_instance = engine_cls()
    engine_config = {}
    if config:
        import yaml

        with open(config) as f:
            engine_config = yaml.safe_load(f) or {}

    try:
        engine_instance.initialize(model, engine_config)
    except Exception as e:
        console.print(f"[red]Failed to initialize engine: {e}[/red]")
        raise SystemExit(1)

    # Load benchmarks
    BenchmarkRegistry.auto_discover()
    benchmarks = []

    if suite_config_path and suite_cfg:
        for test_name in suite_cfg.tests:
            try:
                bench_cls = BenchmarkRegistry.get_benchmark(test_name)
                benchmarks.append(bench_cls())
            except ValueError:
                console.print(f"[yellow]Benchmark '{test_name}' not found, skipping[/yellow]")
    else:
        # Default: run throughput only
        bench_cls = BenchmarkRegistry.get_benchmark("throughput")
        benchmarks.append(bench_cls())

    if not benchmarks:
        console.print("[red]No benchmarks to run[/red]")
        engine_instance.cleanup()
        raise SystemExit(1)

    # Build global config
    global_config = {}
    if skip_warmup:
        global_config["warmup"] = {"enabled": False}
    if runs is not None:
        global_config["runs"] = runs

    # Run suite
    console.print(f"\n[bold green]Running {len(benchmarks)} benchmark(s)...[/bold green]\n")
    runner = SuiteRunner(engine_instance)

    suite_result = runner.run(
        suite_name=suite,
        benchmarks=benchmarks,
        global_config=global_config,
    )

    # Cleanup engine
    engine_instance.cleanup()

    # Generate reports
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_dir = Path(output) if output else Path(f"kitt-results/{model}/{engine}/{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON report
    json_path = save_json_report(
        suite_result, output_dir / "metrics.json",
        system_info=system_info,
        engine_name=engine,
        model_name=model,
    )

    # Save markdown summary
    summary = generate_summary(
        suite_result,
        system_info=system_info,
        engine_name=engine,
        model_name=model,
    )
    (output_dir / "summary.md").write_text(summary)

    # Print summary
    console.print(f"\n{'=' * 60}")
    status = "[bold green]PASSED[/bold green]" if suite_result.passed else "[bold red]FAILED[/bold red]"
    console.print(f"Status: {status}")
    console.print(
        f"Results: {suite_result.passed_count}/{suite_result.total_benchmarks} passed"
    )
    console.print(f"Time: {suite_result.total_time_seconds:.1f}s")
    console.print(f"Output: {output_dir}")


def _find_suite_config(suite_name: str) -> Optional[Path]:
    """Find suite configuration file."""
    # Check standard locations
    search_paths = [
        Path("configs/suites") / f"{suite_name}.yaml",
        Path(__file__).parent.parent.parent.parent / "configs" / "suites" / f"{suite_name}.yaml",
    ]

    for path in search_paths:
        if path.exists():
            return path

    return None
