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
    from kitt.engines.image_resolver import is_kitt_managed_image
    from kitt.engines.registry import EngineRegistry

    EngineRegistry.auto_discover()

    table = Table(title="Inference Engines")
    table.add_column("Engine", style="cyan")
    table.add_column("Image")
    table.add_column("Source")
    table.add_column("Status", style="bold")
    table.add_column("Formats")

    for name in sorted(EngineRegistry.list_all()):
        engine_cls = EngineRegistry.get_engine(name)
        image = engine_cls.resolved_image()
        available = engine_cls.is_available()
        is_build = is_kitt_managed_image(image)
        source = "Build" if is_build else "Registry"
        if available:
            status = "[green]Ready[/green]"
        elif is_build:
            status = "[red]Not Built[/red]"
        else:
            status = "[red]Not Pulled[/red]"
        table.add_row(
            name,
            image,
            source,
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
        raise SystemExit(1) from e

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
@click.option(
    "--force-rebuild", is_flag=True, help="Rebuild even if image already exists"
)
def setup_engine(engine_name, dry_run, force_rebuild):
    """Pull or build the Docker image for an engine."""
    from kitt.engines.docker_manager import DockerManager
    from kitt.engines.image_resolver import get_build_recipe
    from kitt.engines.registry import EngineRegistry

    EngineRegistry.auto_discover()

    try:
        engine_cls = EngineRegistry.get_engine(engine_name)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e

    image = engine_cls.resolved_image()

    if not DockerManager.is_docker_available():
        console.print("[red]Docker is not installed or not running.[/red]")
        console.print("Install Docker: https://docs.docker.com/get-docker/")
        raise SystemExit(1)

    recipe = get_build_recipe(image)

    if recipe is not None:
        # KITT-managed image — build from Dockerfile
        dockerfile = str(recipe.dockerfile_path)
        context_dir = str(recipe.dockerfile_path.parent)

        if dry_run:
            cmd_parts = ["docker build", f"-f {dockerfile}", f"-t {image}"]
            if recipe.target:
                cmd_parts.append(f"--target {recipe.target}")
            for k, v in recipe.build_args.items():
                cmd_parts.append(f"--build-arg {k}={v}")
            cmd_parts.append(context_dir)
            console.print(f"  [dim]would run:[/dim] {' '.join(cmd_parts)}")
            if recipe.experimental:
                console.print(
                    "  [yellow]WARNING: This is an experimental build.[/yellow]"
                )
            console.print("\n[yellow]Dry run — no commands were executed.[/yellow]")
            return

        if not force_rebuild and DockerManager.image_exists(image):
            console.print(
                f"Image {image} already exists. Use --force-rebuild to rebuild."
            )
            return

        if recipe.experimental:
            console.print(
                f"[yellow]WARNING: {image} is an experimental build.[/yellow]"
            )

        console.print(
            f"Building {image} (this may take 10-60 minutes for CUDA builds)..."
        )
        try:
            DockerManager.build_image(
                image=image,
                dockerfile=dockerfile,
                context_dir=context_dir,
                target=recipe.target,
                build_args=recipe.build_args,
            )
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(1) from e
    else:
        # Registry image — pull
        if dry_run:
            console.print(f"  [dim]would run:[/dim] docker pull {image}")
            console.print("\n[yellow]Dry run — no commands were executed.[/yellow]")
            return

        console.print(f"Pulling {image}...")
        try:
            DockerManager.pull_image(image)
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(1) from e

    console.print(f"[green]{engine_name} ready.[/green]")
