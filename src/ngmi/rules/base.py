from datetime import date

import pandas as pd

from ngmi.models import Status


def classify_high_is_bad(value: float, amber: float, red: float) -> Status:
    if value >= red:
        return "red"
    if value >= amber:
        return "amber"
    return "green"


def classify_low_is_bad(value: float, amber: float, red: float) -> Status:
    if value < red:
        return "red"
    if value < amber:
        return "amber"
    return "green"


def change_over(series: pd.Series, days: int) -> pd.Series:
    """Value minus the last known value `days` calendar days earlier (NaN before history starts)."""
    earlier = series.asof(series.index - pd.Timedelta(days=days))
    return pd.Series(series.to_numpy() - earlier.to_numpy(), index=series.index)


def tail_days(series: pd.Series, days: int) -> list[float]:
    """The last `days` calendar days of a series, for sparklines."""
    return series[series.index > series.index[-1] - pd.Timedelta(days=days)].dropna().tolist()


def state_since(statuses: pd.Series) -> date:
    """First date of the current unbroken run of the latest status."""
    current = statuses.iloc[-1]
    changed = statuses[statuses != current]
    run = statuses if changed.empty else statuses[statuses.index > changed.index[-1]]
    return run.index[0].date()
