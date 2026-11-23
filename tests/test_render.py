from datetime import date

from rich.console import Console

from ngmi.models import Signal, SignalError
from ngmi.render import TILE_HEIGHT, TILE_WIDTH, columns_for, render

TODAY = date(2026, 11, 23)


def signal(status: str = "red", since: date = date(2026, 11, 9)) -> Signal:
    return Signal(
        id="x", name="BTC · drawdown", unit="%", value=24.9, status=status,
        rule="24.9% off the 90d high of 118,490 (29 Sep). Past 20%: the trend broke, take profits.",
        state_since=since, source_url="https://www.coingecko.com/en/coins/bitcoin",
    )


def draw(results, width: int) -> list[str]:
    console = Console(width=width, record=True, file=open("/dev/null", "w"), color_system=None)
    render(results, console, today=TODAY)
    return console.export_text().splitlines()


def test_columns_fit_terminal_and_cap_at_five():
    assert columns_for(TILE_WIDTH * 3 + 5) == 3
    assert columns_for(500) == 5
    assert columns_for(10) == 1
    assert columns_for(500, requested=4) == 4


def test_grid_rows_of_fixed_size_tiles():
    results = [signal(), signal("amber"), signal("green", TODAY), SignalError(id="e", name="Gold · trend", error="boom")]
    lines = draw(results, width=TILE_WIDTH * 3)
    tile_rows, footer = lines[:-1], lines[-1]
    assert len(tile_rows) == 2 * TILE_HEIGHT
    assert all(len(line.rstrip()) <= TILE_WIDTH * 3 for line in tile_rows)
    text = "\n".join(lines)
    assert "Red for 14d · 09 Nov" in text and "Green since today" in text
    assert "↗ coingecko.com" in text and "? NO DATA" in text
    assert "1 red" in footer and "1 no data" in footer and "ngmi" in footer


def test_sparkline_scales_and_downsamples():
    from ngmi.render import sparkline

    assert sparkline([1, 2, 3, 4, 5, 6, 7, 8], 8) == "▁▂▃▄▅▆▇█"
    assert sparkline([5, 5, 5], 10) == "▄▄▄"
    assert sparkline([], 10) == ""
    line = sparkline(list(range(200)), 20)
    assert len(line) == 20 and line[0] == "▁" and line[-1] == "█"


def test_tile_shows_sparkline_with_period():
    with_spark = signal().model_copy(update={"spark": list(range(90)), "spark_days": 90})
    text = "\n".join(draw([with_spark], width=TILE_WIDTH))
    assert "▁" in text and "█" in text and " 90d" in text


def test_spark_is_not_in_json():
    dumped = signal().model_copy(update={"spark": [1.0, 2.0], "spark_days": 90}).model_dump()
    assert "spark" not in dumped and "spark_days" not in dumped
