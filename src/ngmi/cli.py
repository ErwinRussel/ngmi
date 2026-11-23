import json
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from ngmi import history
from ngmi.config import config_path, default_config_text, load_config
from ngmi.registry import SPECS, run_all
from ngmi.render import history_table, render
from ngmi.sources import live_sources

app = typer.Typer(help="Not gonna make it: objective exit signals, so you sell before you round-trip.")
console = Console()

ConfigOption = Annotated[Path | None, typer.Option("--config", "-c", help="Path to config.toml.")]


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    as_json: Annotated[bool, typer.Option("--json", help="Print signals as JSON.")] = False,
    demo: Annotated[bool, typer.Option("--demo", help="Use built-in mock data (no network).")] = False,
    cols: Annotated[int | None, typer.Option("--cols", min=1, help="Tiles per row (default: fit the terminal, max 5).")] = None,
    no_log: Annotated[bool, typer.Option("--no-log", help="Don't record this run in the history log.")] = False,
    config: ConfigOption = None,
) -> None:
    """Show all exit signals."""
    if ctx.invoked_subcommand:
        return
    cfg = load_config(config)
    if demo:
        from ngmi.adapters.mock import DEMO_PLANS, DEMO_POSITIONS, DEMO_WATCH, demo_sources

        cfg = cfg.model_copy(update={"positions": DEMO_POSITIONS, "watch": DEMO_WATCH, "plans": DEMO_PLANS})
        sources = demo_sources()
    else:
        sources = live_sources()
    if as_json:
        results = run_all(cfg, sources)
    else:
        with console.status("Fetching signals…"):
            results = run_all(cfg, sources)

    streaks = []
    if not demo and not no_log:
        history.record(results, date.today())
        streaks = history.red_streaks(history.load())

    if as_json:
        print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
        return
    render(results, console, columns=cols, streaks=streaks)


@app.command()
def init(force: Annotated[bool, typer.Option("--force", help="Overwrite an existing config.")] = False) -> None:
    """Write a starter config to ~/.config/ngmi/config.toml."""
    path = config_path()
    if path.exists() and not force:
        console.print(f"Config already exists at {path} (use --force to overwrite).")
        raise typer.Exit(1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(default_config_text())
    console.print(f"Wrote {path}")


@app.command()
def signals(config: ConfigOption = None) -> None:
    """List available signals and whether they're enabled."""
    cfg = load_config(config)
    for spec in SPECS:
        mark = "[green]on [/green]" if spec.enabled(cfg) else "[dim]off[/dim]"
        console.print(f"{mark} {spec.id:<14} {spec.name}")


@app.command(name="history")
def show_history(days: Annotated[int, typer.Option("--days", "-d", min=1, help="Days to show.")] = 30) -> None:
    """Show each signal's status per day, from the local log."""
    snapshots = history.load()
    if not snapshots:
        console.print(f"No history yet. Every `ngmi` run logs to {history.history_path()}.")
        raise typer.Exit()
    console.print(history_table(snapshots, days, date.today()))
    for streak in history.red_streaks(snapshots):
        console.print(f"[red]■[/red] {streak.name}: red on your last {streak.checks} checks (since {streak.since:%d %b})")
