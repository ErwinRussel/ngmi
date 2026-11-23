import pandas as pd

from ngmi.config import PiCycleConfig
from ngmi.models import Signal
from ngmi.rules.base import classify_high_is_bad, state_since, tail_days

FAST, SLOW = 111, 350
SOURCE_URL = "https://www.bitcoinmagazinepro.com/charts/pi-cycle-top-indicator/"


def evaluate(prices: pd.Series, cfg: PiCycleConfig) -> Signal:
    if len(prices) < SLOW:
        raise ValueError(f"need {SLOW} days of BTC prices, got {len(prices)}")
    ratio = (prices.rolling(FAST).mean() / (2 * prices.rolling(SLOW).mean()) * 100).dropna()
    statuses = ratio.map(lambda v: classify_high_is_bad(v, cfg.amber, cfg.red))
    value, status = float(ratio.iloc[-1]), statuses.iloc[-1]

    if status == "red":
        rule = "The 111d MA crossed 2x the 350d MA. This has marked past cycle tops within days. Sell."
    elif status == "amber":
        rule = "The 111d MA is closing in on 2x the 350d MA. A cross (100%) has marked past tops."
    else:
        rule = f"Far from a top signal: the 111d MA is {value:.0f}% of 2x the 350d MA. Cross at 100%."

    return Signal(
        id="pi_cycle",
        name="BTC · Pi Cycle Top",
        unit="% of cross",
        value=round(value, 1),
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=tail_days(ratio, 365),
        spark_days=365,
        source_url=SOURCE_URL,
    )
