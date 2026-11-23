import pandas as pd

from ngmi.config import FundingConfig
from ngmi.models import Signal
from ngmi.rules.base import classify_high_is_bad, state_since, tail_days


def evaluate(annualized: pd.Series, cfg: FundingConfig) -> Signal:
    avg = annualized.rolling(f"{cfg.avg_days}D").mean()
    history = avg[avg.index >= annualized.index[0] + pd.Timedelta(days=cfg.avg_days - 1)]
    history = history if not history.empty else avg
    statuses = history.map(lambda v: classify_high_is_bad(v, cfg.amber, cfg.red))
    value = float(avg.iloc[-1])
    status = statuses.iloc[-1]

    window = f"{cfg.avg_days}d avg"
    if status == "red":
        rule = f"Longs have paid {value:.0f}%/yr ({window}). Leverage is crowded: tops form here."
    elif status == "amber":
        rule = f"Longs are paying up ({window} {value:.0f}%/yr). Red at {cfg.red:g}%."
    elif value < 0:
        rule = f"Shorts are paying ({window} {value:.0f}%/yr). No froth."
    else:
        rule = f"Calm ({window} {value:.0f}%/yr, ~11% is neutral). Amber at {cfg.amber:g}%."

    coin = cfg.instrument.split("-")[0]
    return Signal(
        id="funding",
        name=f"{coin} funding",
        unit="%/yr",
        value=round(value, 1),
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=tail_days(avg, 90),
        spark_days=90,
        source_url=f"https://www.okx.com/trade-swap/{cfg.instrument.lower()}",
    )
