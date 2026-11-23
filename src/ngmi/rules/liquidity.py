import pandas as pd

from ngmi.config import LiquidityConfig
from ngmi.models import Signal
from ngmi.rules.base import classify_low_is_bad, state_since, tail_days

NAMES = {"WALCL": "Fed balance sheet", "M2SL": "M2 money supply"}


def evaluate(series: pd.Series, cfg: LiquidityConfig) -> Signal:
    earlier = series.asof(series.index - pd.Timedelta(days=cfg.lookback_days))
    pct = pd.Series((series.to_numpy() / earlier.to_numpy() - 1) * 100, index=series.index).dropna()
    statuses = pct.map(lambda v: classify_low_is_bad(v, cfg.amber, cfg.red))
    value = float(pct.iloc[-1])
    status = statuses.iloc[-1]

    change = f"{value:+.1f}% in {cfg.lookback_days}d"
    if status == "red":
        rule = f"Shrinking ({change}). Liquidity is draining: a headwind for risk assets."
    elif status == "amber":
        rule = f"Flat to shrinking ({change}). Red below {cfg.red:g}%."
    else:
        rule = f"Growing ({change}). Liquidity is supportive."

    return Signal(
        id="liquidity",
        name=NAMES.get(cfg.series, cfg.series),
        unit=f"% {cfg.lookback_days}d",
        value=round(value, 1),
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=tail_days(series, 365),
        spark_days=365,
        signed=True,
        source_url=f"https://fred.stlouisfed.org/series/{cfg.series}",
    )


