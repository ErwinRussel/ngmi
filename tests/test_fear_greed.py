import json
from datetime import date
from pathlib import Path

import pandas as pd

from ngmi.adapters.alternative_me import parse
from ngmi.config import FearGreedConfig
from ngmi.rules.fear_greed import evaluate

FIXTURE = Path(__file__).parent / "fixtures" / "fear_greed.json"
CFG = FearGreedConfig(amber=60, red=75)


def daily(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2026-01-01", periods=len(values), freq="D"))


def test_parse_fixture_is_ascending_daily_floats():
    series = parse(json.loads(FIXTURE.read_text()))
    assert series.index.is_monotonic_increasing
    assert series.dtype == float
    assert len(series) == 5


def test_red_at_extreme_greed_with_run_start():
    signal = evaluate(daily([40, 65, 80, 78, 90]), CFG)
    assert signal.status == "red"
    assert signal.value == 90
    assert signal.state_since == date(2026, 1, 3)


def test_amber_between_thresholds():
    assert evaluate(daily([20, 62]), CFG).status == "amber"


def test_green_for_whole_history_starts_at_first_point():
    signal = evaluate(daily([10, 20, 30]), CFG)
    assert signal.status == "green"
    assert signal.state_since == date(2026, 1, 1)


def test_threshold_is_inclusive():
    assert evaluate(daily([75]), CFG).status == "red"
