from collections import Counter
from datetime import date, timedelta
from urllib.parse import urlparse

from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ngmi.history import Snapshot, Streak
from ngmi.models import Signal, SignalError

# Terminal cells are about twice as tall as wide, so 28x14 cells looks square.
TILE_WIDTH = 28
TILE_HEIGHT = 14
MAX_COLUMNS = 5
COLORS = {"green": "green", "amber": "yellow", "red": "red"}
ICONS = {"green": "●", "amber": "▲", "red": "■"}
INNER_WIDTH = TILE_WIDTH - 4  # borders + padding
BARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float], width: int) -> str:
    if not values:
        return ""
    if len(values) > width:
        # bucket means keep the shape; the last bucket ends at the latest value
        size = len(values) / width
        values = [
            sum(chunk) / len(chunk)
            for i in range(width)
            if (chunk := values[round(i * size) : round((i + 1) * size)])
        ]
    low, high = min(values), max(values)
    if high == low:
        return BARS[3] * len(values)
    return "".join(BARS[round((v - low) / (high - low) * (len(BARS) - 1))] for v in values)


def _period(days: int) -> str:
    return f"{days // 365}y" if days >= 365 else f"{days}d"


def _spark(signal: Signal, color: str) -> Text:
    if not signal.spark:
        return Text()
    label = f" {_period(signal.spark_days)}" if signal.spark_days else ""
    text = Text(sparkline(signal.spark, INNER_WIDTH - len(label)), style=color)
    text.append(label, style="dim")
    return text


def _duration(status: str, since: date, today: date) -> str:
    days = (today - since).days
    if days <= 0:
        return f"{status.capitalize()} since today"
    return f"{status.capitalize()} for {days}d · {since:%d %b}"


def _value(signal: Signal) -> Text:
    text = Text(f"{signal.value:{'+' if signal.signed else ''},g}", style="bold")
    text.append(signal.unit if signal.unit.startswith(("%", "/")) else f" {signal.unit}", style="dim")
    return text


def _domain(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.")


def _frame(title: str, body: RenderableType, border: str) -> Panel:
    return Panel(
        body,
        title=f"[bold]{title}[/bold]",
        title_align="left",
        border_style=border,
        width=TILE_WIDTH,
        height=TILE_HEIGHT,
        padding=(0, 1),
    )


def signal_tile(signal: Signal, today: date) -> Panel:
    color = COLORS[signal.status]
    status = Text(f"{ICONS[signal.status]} {signal.status.upper()}", style=f"bold {color}")
    footer = Group(
        Text(_duration(signal.status, signal.state_since, today), style=color, no_wrap=True, overflow="ellipsis"),
        Text(
            f"↗ {_domain(signal.source_url)}",
            style=f"dim link {signal.source_url}",
            no_wrap=True,
            overflow="ellipsis",
        ),
    )
    layout = Layout()
    layout.split_column(
        Layout(Group(Text(), status, _value(signal), _spark(signal, color), Text()), size=5),
        Layout(Text(signal.rule)),
        Layout(footer, size=2),
    )
    return _frame(signal.name, layout, color)


def error_tile(err: SignalError) -> Panel:
    body = Group(Text(), Text("? NO DATA", style="bold bright_black"), Text(), Text(err.error, style="dim"))
    return _frame(err.name, body, "bright_black")


def columns_for(width: int, requested: int | None = None) -> int:
    return max(1, min(requested or MAX_COLUMNS, width // TILE_WIDTH))


def grid(results: list[Signal | SignalError], columns: int, today: date) -> Table:
    table = Table.grid()
    for _ in range(columns):
        table.add_column(width=TILE_WIDTH)
    tiles = [signal_tile(r, today) if isinstance(r, Signal) else error_tile(r) for r in results]
    for i in range(0, len(tiles), columns):
        table.add_row(*tiles[i : i + columns])
    return table


def summary(results: list[Signal | SignalError]) -> Text:
    counts = Counter(r.status for r in results if isinstance(r, Signal))
    text = Text()
    for status in ("red", "amber", "green"):
        if counts[status]:
            text.append(f"{ICONS[status]} {counts[status]} {status}   ", style=COLORS[status])
    errors = sum(isinstance(r, SignalError) for r in results)
    if errors:
        text.append(f"? {errors} no data   ", style="bright_black")
    if counts["red"]:
        text.append("ngmi", style="bold red")
        text.append(" if you ignore the red ones.", style="dim")
    return text


NAG_AFTER = 3  # checks in a row before calling out a red tile


def nag(streaks: list[Streak]) -> Text | None:
    ignored = [s for s in streaks if s.checks >= NAG_AFTER]
    if not ignored:
        return None
    text = Text()
    text.append("Red on every check: ", style="bold red")
    text.append(", ".join(f"{s.name} ({s.checks}x since {s.since:%d %b})" for s in ignored[:4]))
    text.append(". Still holding?", style="bold")
    return text


def render(
    results: list[Signal | SignalError],
    console: Console,
    columns: int | None = None,
    today: date | None = None,
    streaks: list[Streak] | None = None,
) -> None:
    today = today or date.today()
    console.print(grid(results, columns_for(console.width, columns), today))
    console.print(summary(results))
    if streaks and (line := nag(streaks)):
        console.print(line)


def history_table(snapshots: list[Snapshot], days: int, today: date) -> Table:
    by_day = {s.day: s for s in snapshots}
    span = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    names: dict[str, str] = {}
    for snap in snapshots:
        names.update({signal_id: v["name"] for signal_id, v in snap.signals.items()})

    table = Table(box=None, pad_edge=False, show_edge=False)
    table.add_column("Signal", no_wrap=True)
    table.add_column(f"{span[0]:%d %b} → {today:%d %b}", no_wrap=True)
    table.add_column("Red checks", justify="right")
    for signal_id, name in names.items():
        strip, red = Text(), 0
        for day in span:
            snap = by_day.get(day)
            entry = snap.signals.get(signal_id) if snap else None
            if entry is None:
                strip.append("·", style="bright_black")
            else:
                strip.append(ICONS[entry["status"]], style=COLORS[entry["status"]])
                red += entry["status"] == "red"
        table.add_row(name, strip, Text(str(red), style="red") if red else Text("0", style="dim"))
    return table
