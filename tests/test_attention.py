import pandas as pd
import pytest

from ngmi.adapters import wikipedia
from ngmi.config import AttentionConfig
from ngmi.rules import attention

CFG = AttentionConfig()


def views(base: float, tail: list[float]) -> pd.Series:
    values = [base] * 365 + tail
    return pd.Series(values, index=pd.date_range("2025-01-01", periods=len(values), freq="D"), dtype=float)


@pytest.mark.parametrize(("tail", "status"), [([1000] * 7, "green"), ([2500] * 7, "amber"), ([4000] * 7, "red")])
def test_status_is_seven_day_average_vs_yearly_median(tail, status):
    signal = attention.evaluate(views(1000, tail), CFG, "Bitcoin")
    assert signal.status == status and signal.id == "attention:Bitcoin"


def test_one_day_spike_is_smoothed():
    assert attention.evaluate(views(1000, [1000] * 6 + [5_000]), CFG, "Bitcoin").status == "green"


def test_needs_a_year_of_history():
    with pytest.raises(ValueError, match="need 365 days"):
        attention.evaluate(views(1000, [])[:100], CFG, "Bitcoin")


def test_wikipedia_parse():
    payload = {"items": [{"timestamp": "2026112200", "views": 3800}, {"timestamp": "2026112300", "views": 3792}]}
    series = wikipedia.parse(payload, "Bitcoin")
    assert series.tolist() == [3800, 3792] and str(series.index[-1].date()) == "2026-11-23"
