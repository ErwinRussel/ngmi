from datetime import date

import pandas as pd
import pytest

from ngmi.config import VixConfig
from ngmi.rules import vix

CFG = VixConfig()


def daily(values: list[float], start: str = "2026-01-01") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


def test_complacency_is_red_and_counts_from_first_day_below_15():
    signal = vix.evaluate(daily([20, 18, 14.5, 13, 12]), CFG)
    assert signal.status == "red" and signal.value == 12
    assert signal.state_since == date(2026, 1, 3)
    assert signal.rule.startswith("Sell zone")


@pytest.mark.parametrize(
    ("value", "status", "zone"),
    [(16, "amber", "Hold zone, close"), (20, "green", "Hold zone: stay"), (30, "green", "Scale-in"), (40, "green", "Buy zone")],
)
def test_zones(value, status, zone):
    signal = vix.evaluate(daily([20, value]), CFG)
    assert signal.status == status and signal.rule.startswith(zone)


def test_zones_must_be_ordered():
    with pytest.raises(ValueError):
        VixConfig(scale_in=40, buy=35)
