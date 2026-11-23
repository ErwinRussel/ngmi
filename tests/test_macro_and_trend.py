from datetime import date

import pandas as pd

from ngmi.adapters import fred, okx
from ngmi.config import FundingConfig, LiquidityConfig, MovingAverageConfig, RatesConfig
from ngmi.rules import funding, liquidity, moving_average, rates

MA = MovingAverageConfig(fast=3, slow=5)


def daily(values: list[float], start: str = "2026-01-01") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


def test_trend_red_below_slow_ma():
    signal = moving_average.evaluate(daily([10, 10, 10, 10, 10, 10, 6]), MA, "X", "", "trend:x")
    assert signal.status == "red" and signal.value < 0 and signal.signed


def test_trend_amber_below_fast_only():
    # slow MA dragged down by early lows, fast MA held up by the recent spike
    signal = moving_average.evaluate(daily([1, 1, 1, 1, 10, 10, 8]), MA, "X", "", "trend:x")
    assert signal.status == "amber"


def test_trend_green_and_needs_enough_history():
    assert moving_average.evaluate(daily([1, 2, 3, 4, 5, 6, 7]), MA, "X", "", "t").status == "green"
    try:
        moving_average.evaluate(daily([1, 2, 3]), MA, "X", "", "t")
    except ValueError as exc:
        assert "need 5 days" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_funding_uses_rolling_average_not_last_print():
    cfg = FundingConfig(avg_days=3, amber=15, red=30)
    spiky = funding.evaluate(daily([10, 10, 10, 10, 60]), cfg)  # one hot day, 3d avg ~27
    assert spiky.status == "amber"
    hot = funding.evaluate(daily([10, 40, 40, 40, 40]), cfg)
    assert hot.status == "red" and hot.state_since == date(2026, 1, 3)  # (10+40+40)/3 hits 30


def test_liquidity_contracting_is_red():
    cfg = LiquidityConfig(lookback_days=7, amber=0, red=-2)
    weekly = pd.Series([100, 100, 99, 97], index=pd.date_range("2026-01-07", periods=4, freq="7D"))
    signal = liquidity.evaluate(weekly, cfg)
    assert signal.status == "red" and signal.value == -2.0


def test_rates_fast_rise_is_red_and_value_is_the_yield():
    cfg = RatesConfig(lookback_days=5, amber=25, red=50)
    signal = rates.evaluate(daily([4.0] * 6 + [4.3, 4.6]), cfg)
    assert signal.status == "red" and signal.value == 4.6
    assert signal.rule.startswith("+60bp in 5d")


def test_fred_csv_parse_skips_missing():
    text = "observation_date,DGS10\n2026-11-18,5.07\n2026-11-19,.\n2026-11-20,5.04\n"
    series = fred.parse(text, "DGS10")
    assert series.tolist() == [5.07, 5.04]


def test_okx_parse_annualizes_daily_mean():
    ms = lambda ts: str(int(pd.Timestamp(ts).timestamp() * 1000))  # noqa: E731
    rows = [{"fundingTime": ms(f"2026-11-20 {h:02d}:00"), "fundingRate": "0.0001"} for h in (0, 8, 16)]
    series = okx.parse(rows, "BTC-USDT-SWAP")
    assert round(series.iloc[0], 2) == 10.95
