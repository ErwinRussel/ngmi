import pandas as pd

from ngmi.config import WeeklyRsiConfig
from ngmi.models import Signal
from ngmi.rules.base import classify_high_is_bad, state_since


def rsi(series: pd.Series, period: int) -> pd.Series:
    """Wilder's RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return (100 - 100 / (1 + gain / loss)).dropna()


def evaluate(prices: pd.Series, cfg: WeeklyRsiConfig, label: str, source_url: str, signal_id: str) -> Signal:
    weekly = prices.resample("W").last().dropna()  # the current week ends at today's price
    values = rsi(weekly, cfg.period)
    if values.empty:
        raise ValueError(f"need {cfg.period + 1} weeks of prices, got {len(weekly)}")
    statuses = values.map(lambda v: classify_high_is_bad(v, cfg.amber, cfg.red))
    value, status = float(values.iloc[-1]), statuses.iloc[-1]

    if status == "red":
        rule = f"Overheated: weekly RSI {value:.0f} is above {cfg.red:g}. Cycle tops print here. Trim into strength."
    elif status == "amber":
        rule = f"Running hot (above {cfg.amber:g}). Red at {cfg.red:g}."
    elif value < 30:
        rule = "Oversold on the weekly. No overheating."
    else:
        rule = f"No overheating. Amber at {cfg.amber:g}."

    return Signal(
        id=signal_id,
        name=f"{label} · weekly RSI",
        unit="/100",
        value=round(value, 1),
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=values.tail(52).tolist(),
        spark_days=365,
        source_url=source_url,
    )
