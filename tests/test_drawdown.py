import json
from datetime import date
from pathlib import Path

import pandas as pd

from ngmi.adapters import coingecko, yahoo
from ngmi.config import DrawdownConfig
from ngmi.rules.drawdown import drawdown_pct, evaluate

FIXTURES = Path(__file__).parent / "fixtures"
CFG = DrawdownConfig(window_days=10, amber=10, red=20)


def daily(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2026-01-01", periods=len(values), freq="D"), dtype=float)


def test_drawdown_pct_against_rolling_high():
    dd = drawdown_pct(daily([100, 120, 90]), window_days=10)
    assert dd.iloc[-1] == 25


def test_rolling_window_forgets_old_highs():
    prices = daily([200] + [100] * 15)
    assert drawdown_pct(prices, window_days=10).iloc[-1] == 0


def test_red_with_state_since_after_warmup():
    prices = daily([100] * 12 + [95, 85, 75, 70])
    signal = evaluate(prices, CFG, "BTC", "https://example.com")
    assert signal.status == "red"
    assert round(signal.value) == 30
    assert signal.state_since == date(2026, 1, 15)
    assert signal.rule.startswith("30.0% off the 10d high")


def test_amber_and_green():
    assert evaluate(daily([100] * 12 + [88]), CFG, "X", "").status == "amber"
    assert evaluate(daily([100] * 12 + [101]), CFG, "X", "").status == "green"


def test_coingecko_fixture_one_row_per_day():
    series = coingecko.parse(json.loads((FIXTURES / "coingecko_bitcoin.json").read_text()), "bitcoin")
    assert series.index.is_unique and series.index.is_monotonic_increasing
    assert len(series) == 366  # the intraday point collapses into the last day


def test_yahoo_fixture_drops_missing_closes():  # fixture has one null close
    series = yahoo.parse(json.loads((FIXTURES / "yahoo_stock.json").read_text()), "DEMO")
    assert series.notna().all() and series.index.is_monotonic_increasing
    assert (series.index == series.index.normalize()).all()
    assert len(series) == 260  # 261 weekday sessions minus the null
    assert series.index.day_of_week.max() < 5  # sessions land on their New York date
