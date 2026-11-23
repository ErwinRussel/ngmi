import pandas as pd

from ngmi.config import RatesConfig
from ngmi.models import Signal
from ngmi.rules.base import change_over, classify_high_is_bad, state_since, tail_days

NAMES = {"DGS10": "US 10Y yield", "DGS2": "US 2Y yield", "DGS30": "US 30Y yield"}


def evaluate(yields: pd.Series, cfg: RatesConfig) -> Signal:
    bp = (change_over(yields, cfg.lookback_days) * 100).dropna()
    statuses = bp.map(lambda v: classify_high_is_bad(v, cfg.amber, cfg.red))
    change = float(bp.iloc[-1])
    status = statuses.iloc[-1]

    moved = f"{change:+.0f}bp in {cfg.lookback_days}d"
    if status == "red":
        rule = f"{moved}. Rising fast: tighter conditions, pressure on risk assets."
    elif status == "amber":
        rule = f"{moved}. Climbing; red at +{cfg.red:g}bp."
    else:
        rule = f"{moved}. No rate shock."

    return Signal(
        id="rates",
        name=NAMES.get(cfg.series, cfg.series),
        unit="%",
        value=round(float(yields.iloc[-1]), 2),
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=tail_days(yields, 90),
        spark_days=90,
        source_url=f"https://fred.stlouisfed.org/series/{cfg.series}",
    )
