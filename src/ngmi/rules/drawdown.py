import pandas as pd

from ngmi.config import DrawdownConfig
from ngmi.models import Signal
from ngmi.rules.base import classify_high_is_bad, state_since, tail_days
from ngmi.rules.format import money


def drawdown_pct(prices: pd.Series, window_days: int) -> pd.Series:
    rolling_high = prices.rolling(f"{window_days}D").max()
    return (1 - prices / rolling_high) * 100


def evaluate(prices: pd.Series, cfg: DrawdownConfig, label: str, source_url: str, signal_id: str | None = None) -> Signal:
    drawdowns = drawdown_pct(prices, cfg.window_days)
    # The first window has an incomplete lookback, so it can't say how long a state has lasted.
    full_window = drawdowns[drawdowns.index >= prices.index[0] + pd.Timedelta(days=cfg.window_days)]
    history = full_window if not full_window.empty else drawdowns
    statuses = history.map(lambda d: classify_high_is_bad(d, cfg.amber, cfg.red))

    value = float(drawdowns.iloc[-1])
    status = statuses.iloc[-1]
    window = prices[prices.index > prices.index[-1] - pd.Timedelta(days=cfg.window_days)]
    high = f"{cfg.window_days}d high of {money(window.max())} ({window.idxmax():%d %b})"

    if value < 0.05:
        rule = f"At its {cfg.window_days}d high. Let it run."
    elif status == "red":
        rule = f"{value:.1f}% off the {high}. Past {cfg.red:g}%: the trend broke, take profits."
    elif status == "amber":
        rule = f"{value:.1f}% off the {high}. Red at {cfg.red:g}%."
    else:
        rule = f"{value:.1f}% off the {high}. Amber at {cfg.amber:g}%."

    return Signal(
        id=signal_id or f"drawdown:{label.lower()}",
        name=f"{label} · drawdown",
        unit="%",
        value=round(value, 1),
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=tail_days(prices, cfg.window_days),
        spark_days=cfg.window_days,
        source_url=source_url,
    )
