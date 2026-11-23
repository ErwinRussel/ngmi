"""Writes synthetic API responses shaped like the real ones, so the repo ships no third-party data.

Run from the repo root: uv run python tests/fixtures/generate.py
"""

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
START = datetime(2025, 1, 1, tzinfo=UTC)
rng = random.Random(42)


def walk(n: int, start: float, drift: float = 0.001, vol: float = 0.02) -> list[float]:
    values, value = [], start
    for _ in range(n):
        value *= 1 + drift + rng.gauss(0, vol)
        values.append(round(value, 2))
    return values


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def coingecko() -> dict:
    # 366 daily points at 00:00 UTC, plus a live intraday point on the last day, like the real API
    days = [START + timedelta(days=i) for i in range(366)]
    prices = walk(len(days) + 1, 40_000)
    points = [[ms(d), p] for d, p in zip(days, prices)] + [[ms(days[-1] + timedelta(hours=11)), prices[-1]]]
    return {
        "prices": points,
        "market_caps": [[t, round(p * 19_500_000, 2)] for t, p in points],
        "total_volumes": [[t, round(p * 500_000, 2)] for t, p in points],
    }


def yahoo() -> dict:
    # Weekday sessions opening 09:30 New York (14:30 UTC), with one missing close as Yahoo sometimes has
    days = [START + timedelta(days=i) for i in range(365)]
    sessions = [d.replace(hour=14, minute=30) for d in days if d.weekday() < 5]
    closes: list[float | None] = walk(len(sessions), 100)
    closes[100] = None
    return {
        "chart": {
            "result": [
                {
                    "meta": {"currency": "USD", "symbol": "DEMO", "exchangeTimezoneName": "America/New_York"},
                    "timestamp": [int(s.timestamp()) for s in sessions],
                    "indicators": {"quote": [{"close": closes}], "adjclose": [{"adjclose": closes}]},
                }
            ],
            "error": None,
        }
    }


def fear_greed() -> dict:
    labels = [(25, "Extreme Fear"), (45, "Fear"), (55, "Neutral"), (75, "Greed"), (101, "Extreme Greed")]
    rows = []
    for i, value in enumerate([62, 58, 55, 49, 44]):  # newest first, like the real API
        day = START + timedelta(days=4 - i)
        label = next(name for limit, name in labels if value < limit)
        rows.append({"value": str(value), "value_classification": label, "timestamp": str(int(day.timestamp()))})
    return {"name": "Fear and Greed Index", "data": rows, "metadata": {"error": None}}


if __name__ == "__main__":
    for name, payload in [("coingecko_bitcoin", coingecko()), ("yahoo_stock", yahoo()), ("fear_greed", fear_greed())]:
        (HERE / f"{name}.json").write_text(json.dumps(payload, indent=1) + "\n")
        print(f"wrote {name}.json")
