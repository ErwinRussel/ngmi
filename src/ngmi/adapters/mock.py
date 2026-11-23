from datetime import date

import numpy as np
import pandas as pd

from ngmi.config import Plan, Positions
from ngmi.sources import Sources

# (days, total % move over those days); the path ends today.
Segments = list[tuple[int, float]]


def scripted_series(segments: Segments, start_value: float, seed: int, noise: float = 0.01, name: str = "") -> pd.Series:
    rng = np.random.default_rng(seed)
    steps = np.concatenate([np.full(days, (1 + move / 100) ** (1 / days)) for days, move in segments])
    path = start_value * np.cumprod(steps * (1 + rng.normal(0, noise, steps.size)))
    index = pd.date_range(end=pd.Timestamp(date.today()), periods=steps.size, freq="D")
    return pd.Series(path, index=index, name=name)


def waypoint_series(points: list[tuple[int, float]], seed: int, noise: float = 2.0) -> pd.Series:
    """Linear path through (day, value) waypoints, day 0 = first point, last waypoint = today."""
    rng = np.random.default_rng(seed)
    days, values = zip(*points)
    path = np.interp(np.arange(days[-1] + 1), days, values) + rng.normal(0, noise, days[-1] + 1)
    path[-1] = values[-1]
    index = pd.date_range(end=pd.Timestamp(date.today()), periods=path.size, freq="D")
    return pd.Series(path, index=index)


class MockSeriesAdapter:
    def __init__(self, series: pd.Series):
        self.series = series

    def fetch(self) -> pd.Series:
        return self.series


class MockSymbolAdapter:
    def __init__(self, series_by_symbol: dict[str, pd.Series]):
        self.series_by_symbol = series_by_symbol

    def fetch(self, symbol: str) -> pd.Series:
        if symbol not in self.series_by_symbol:
            raise KeyError(f"no mock data for {symbol!r}")
        return self.series_by_symbol[symbol]


DEMO_POSITIONS = Positions(crypto=["bitcoin", "ethereum", "solana"], stocks=["NVDA"])
DEMO_WATCH = Positions(stocks=["GC=F", "SI=F"])
DEMO_PLANS = {
    "bitcoin": Plan(entry=40_000, done=1, steps=[{"gain": 100, "sell": 20}, {"gain": 200, "sell": 25}, {"gain": 300, "sell": 25}]),
    "ethereum": Plan(entry=1_500, steps=[{"gain": 100, "sell": 25}, {"gain": 200, "sell": 25}]),
    "NVDA": Plan(entry=110, steps=[{"gain": 125, "sell": 30}, {"gain": 250, "sell": 30}]),
}


def demo_sources() -> Sources:
    fear_greed = waypoint_series([(0, 35), (280, 55), (335, 84), (364, 68)], seed=1).clip(1, 99).round()
    crypto = {
        "bitcoin": scripted_series([(250, 80), (60, 25), (55, -26)], 60_000, seed=2),
        "ethereum": scripted_series([(250, 40), (80, 30), (35, -13)], 2_400, seed=3),
        "solana": scripted_series([(200, 60), (130, 40), (35, -6)], 140, seed=7, noise=0.012),
    }
    stocks = {
        "NVDA": scripted_series([(300, 35), (65, 18)], 120, seed=4, noise=0.008),
        "GC=F": scripted_series([(300, 25), (65, 9)], 2_600, seed=5, noise=0.006),
        "SI=F": scripted_series([(300, 30), (40, 6), (25, -9)], 30, seed=6, noise=0.01),
        "BTC-USD": scripted_series([(650, 0), (120, 200), (130, 60)], 17_300, seed=12, noise=0.02),
    }
    funding = waypoint_series([(0, 10), (60, 14), (85, 24), (99, 21)], seed=8, noise=3)
    fred = {
        "WALCL": scripted_series([(900, -12), (195, -1.5)], 7_500_000, seed=9, noise=0.0005),
        "M2SL": scripted_series([(1095, 8)], 21_000, seed=10, noise=0.0003),
        "DGS10": waypoint_series([(0, 4.2), (1040, 4.6), (1095, 5.15)], seed=11, noise=0.03),
    }
    return Sources(
        fear_greed=MockSeriesAdapter(fear_greed),
        crypto=MockSymbolAdapter(crypto),
        stocks=MockSymbolAdapter(stocks),
        funding=MockSymbolAdapter({"BTC-USDT-SWAP": funding}),
        fred=MockSymbolAdapter(fred),
    )
