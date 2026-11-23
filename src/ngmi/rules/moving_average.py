import pandas as pd

from ngmi.config import MovingAverageConfig
from ngmi.models import Signal, Status
from ngmi.rules.base import state_since, tail_days
from ngmi.rules.format import money


def _status(price: float, fast: float, slow: float) -> Status:
    if price < slow:
        return "red"
    if price < fast:
        return "amber"
    return "green"


def evaluate(prices: pd.Series, cfg: MovingAverageConfig, label: str, source_url: str, signal_id: str) -> Signal:
    if len(prices) < cfg.slow:
        raise ValueError(f"need {cfg.slow} days of prices, got {len(prices)}")
    fast = prices.rolling(cfg.fast).mean()
    slow = prices.rolling(cfg.slow).mean()
    valid = slow.notna()
    statuses = pd.Series(
        [_status(p, f, s) for p, f, s in zip(prices[valid], fast[valid], slow[valid])], index=prices.index[valid]
    )

    price, f, s = prices.iloc[-1], fast.iloc[-1], slow.iloc[-1]
    vs_slow = (price / s - 1) * 100
    status = statuses.iloc[-1]
    if status == "red":
        rule = f"{abs(vs_slow):.1f}% below the {cfg.slow}d MA ({money(s)}). Long-term trend is broken."
    elif status == "amber":
        rule = f"Below the {cfg.fast}d MA ({money(f)}), still above the {cfg.slow}d. Trend is weakening."
    else:
        rule = f"Above the {cfg.fast}d ({money(f)}) and {cfg.slow}d MA ({money(s)}). Trend intact."

    return Signal(
        id=signal_id,
        name=f"{label} · trend",
        unit=f"% vs {cfg.slow}d",
        value=round(vs_slow, 1),
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=tail_days(prices, cfg.slow),
        spark_days=cfg.slow,
        signed=True,
        source_url=source_url,
    )
