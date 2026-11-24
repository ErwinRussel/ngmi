"""VIX zones from @AskLivermore's "VIX Cheat Sheet" (https://x.com/AskLivermore, 7 Jul 2026)."""

import pandas as pd

from ngmi.config import VixConfig
from ngmi.models import Signal
from ngmi.rules.base import classify_low_is_bad, state_since, tail_days

SOURCE_URL = "https://x.com/AskLivermore"


def _rule(value: float, cfg: VixConfig) -> str:
    if value >= cfg.buy:
        return "Buy zone: panic. Buy aggressively: high-beta tech, growth, small caps."
    if value >= cfg.scale_in:
        return "Scale-in zone: add gradually. Quality tech, financials, industrials, cyclicals."
    if value < cfg.red:
        return "Sell zone: nobody is hedging. Reduce exposure: utilities, healthcare, staples, bonds."
    if value < cfg.amber:
        return f"Hold zone, close to complacency. Stay positioned but alert; red below {cfg.red:g}."
    return "Hold zone: stay positioned. Tech + defensives, dividend growers."


def evaluate(vix: pd.Series, cfg: VixConfig) -> Signal:
    statuses = vix.map(lambda v: classify_low_is_bad(v, cfg.amber, cfg.red))
    value = float(vix.iloc[-1])

    return Signal(
        id="vix",
        name="VIX",
        unit="",
        value=round(value, 2),
        status=statuses.iloc[-1],
        rule=_rule(value, cfg),
        state_since=state_since(statuses),
        spark=tail_days(vix, 365),
        spark_days=365,
        source_url=SOURCE_URL,
    )
