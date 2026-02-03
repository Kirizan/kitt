"""kitt results - Results management commands."""

import subprocess

import click
from rich.console import Console
from pathlib import Path

console = Console()


@click.group()
def results():
    """Manage benchmark results."""


@results.command("init")
@click.option("--path", "-p", type=click.Path(), help="Path for KARR repo")
def init_results(path):
    """Initialize a new KARR results repository."""
    from kitt.git_ops.repo_manager import KARRRepoManager
    from kitt.hardware.fingerprint import HardwareFingerprint

    fingerprint = HardwareFingerprint.generate()

    if path:
        repo_path = Path(path)
    else:
        repo_path = Path.cwd() / f"karr-{fingerprint[:40]}"

    if repo_path.exists():
        console.print(f"[yellow]Directory already exists: {repo_path}[/yellow]")
        return

    console.print(f"[cyan]Creating KARR repository at {repo_path}...[/cyan]")
    repo = KARRRepoManager.create_results_repo(repo_path, fingerprint)
    console.print(f"[green]KARR repository created![/green]")
    console.print(f"  Path: {repo_path}")
    console.print(f"  Fingerprint: {fingerprint}")


@results.command("submit")
@click.option("--repo", type=click.Path(), help="Results repository path")
def submit_results(repo):
    """Submit results via pull request."""
    from kitt.git_ops.pr_creator import PRCreator

    if not PRCreator.check_git_config():
        console.print("[red]Git not configured[/red]")
        console.print("\nConfigure Git with:")
        console.print("  git config --global user.name 'Your Name'")
        console.print("  git config --global user.email 'your.email@example.com'")
        return

    console.print("[cyan]Submitting results...[/cyan]")
    console.print("[yellow]PR submission not yet connected to remote. "
                  "Commit your changes and push manually.[/yellow]")


@results.command("list")
@click.option("--model", help="Filter by model")
@click.option("--engine", help="Filter by engine")
def list_results(model, engine):
    """List local benchmark results."""
    import json

    results_dirs = list(Path(".").glob("kitt-results/**/**/metrics.json"))
    results_dirs += list(Path(".").glob("karr-*/**/metrics.json"))

    if not results_dirs:
        console.print("[yellow]No results found in current directory[/yellow]")
        return

    from rich.table import Table

    table = Table(title="Local Results")
    table.add_column("Model")
    table.add_column("Engine")
    table.add_column("Timestamp")
    table.add_column("Status")

    for metrics_path in sorted(results_dirs):
        try:
            with open(metrics_path) as f:
                data = json.load(f)
            m = data.get("model", "unknown")
            e = data.get("engine", "unknown")
            ts = data.get("timestamp", "unknown")

            if model and model not in m:
                continue
            if engine and engine != e:
                continue

            passed = data.get("passed", False)
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            table.add_row(m, e, ts[:19], status)
        except Exception:
            continue

    console.print(table)


@results.command("compare")
@click.argument("run1")
@click.argument("run2")
@click.option("--additional", multiple=True, help="Additional runs to compare")
def compare_results(run1, run2, additional):
    """Compare benchmark results from different runs."""
    import json

    runs = [run1, run2] + list(additional)
    console.print(f"[cyan]Comparing {len(runs)} result set(s)...[/cyan]")

    result_data = []
    for run_path in runs:
        path = Path(run_path)
        metrics_file = path / "metrics.json" if path.is_dir() else path
        if not metrics_file.exists():
            console.print(f"[red]Not found: {metrics_file}[/red]")
            continue
        with open(metrics_file) as f:
            result_data.append(json.load(f))

    if len(result_data) < 2:
        console.print("[red]Need at least 2 valid result sets to compare[/red]")
        raise SystemExit(1)

    from kitt.reporters.comparison import compare_metrics

    comparison = compare_metrics(result_data)

    from rich.table import Table

    table = Table(title="Metrics Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Min")
    table.add_column("Max")
    table.add_column("Avg")
    table.add_column("Std Dev")
    table.add_column("CV%")

    for metric, stats in comparison.items():
        std_dev = f"{stats.get('std_dev', 0):.4f}" if "std_dev" in stats else "-"
        cv = f"{stats.get('cv_percent', 0):.1f}%" if "cv_percent" in stats else "-"
        table.add_row(
            metric,
            f"{stats['min']:.4f}",
            f"{stats['max']:.4f}",
            f"{stats['avg']:.4f}",
            std_dev,
            cv,
        )

    console.print(table)


@results.command("cleanup")
@click.option("--repo", type=click.Path(), help="Results repository path")
@click.option("--days", default=90, help="Keep objects from last N days")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted")
def cleanup_lfs(repo, days, dry_run):
    """Clean up old Git LFS objects to reduce repository size."""
    repo_path = Path(repo) if repo else Path.cwd()

    console.print(f"[cyan]Cleaning up LFS objects in {repo_path}[/cyan]")
    console.print(f"[yellow]Keeping objects from last {days} days[/yellow]")

    if dry_run:
        console.print("[bold yellow]DRY RUN - No changes will be made[/bold yellow]\n")

    try:
        result = subprocess.run(
            [
                "git", "lfs", "prune", "--dry-run", "--verbose",
                "--verify-remote", "--recent", f"--days={days}",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)

        if not dry_run and result.returncode == 0:
            if click.confirm("Proceed with cleanup?"):
                subprocess.run(
                    [
                        "git", "lfs", "prune", "--verbose",
                        "--verify-remote", "--recent", f"--days={days}",
                    ],
                    cwd=repo_path,
                    check=True,
                )
                console.print("[green]Cleanup complete[/green]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")
    except FileNotFoundError:
        console.print("[red]Git LFS not found. Install from: https://git-lfs.github.com[/red]")
