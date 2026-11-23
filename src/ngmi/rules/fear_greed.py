import pandas as pd

from ngmi.config import FearGreedConfig
from ngmi.models import Signal
from ngmi.rules.base import classify_high_is_bad, state_since, tail_days

SOURCE_URL = "https://alternative.me/crypto/fear-and-greed-index/"


def _label(value: float) -> str:
    if value >= 75:
        return "Extreme greed"
    if value >= 55:
        return "Greed"
    if value > 45:
        return "Neutral"
    if value > 25:
        return "Fear"
    return "Extreme fear"


def evaluate(series: pd.Series, cfg: FearGreedConfig) -> Signal:
    statuses = series.map(lambda v: classify_high_is_bad(v, cfg.amber, cfg.red))
    value = float(series.iloc[-1])
    status = statuses.iloc[-1]

    if status == "red":
        rule = f"{_label(value)}: the crowd is euphoric. Consider trimming."
    elif status == "amber":
        rule = f"{_label(value)} is building. Red at {cfg.red:g}."
    else:
        rule = f"{_label(value)}. No greed warning until {cfg.amber:g}."

    return Signal(
        id="fear_greed",
        name="Crypto Fear & Greed",
        unit="/100",
        value=value,
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=tail_days(series, 90),
        spark_days=90,
        source_url=SOURCE_URL,
    )
