from typing import Protocol

import httpx
import pandas as pd

TIMEOUT = httpx.Timeout(15.0)
USER_AGENT = "ngmi/0.1"


class SeriesAdapter(Protocol):
    """A single daily series: DatetimeIndex (ascending, tz-naive, one row per day) -> float."""

    def fetch(self) -> pd.Series: ...


class SymbolAdapter(Protocol):
    """A daily series for one symbol or series id, same shape as SeriesAdapter."""

    def fetch(self, symbol: str) -> pd.Series: ...


def http_client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})


def to_daily(index: pd.DatetimeIndex, values: list[float | None], name: str) -> pd.Series:
    series = pd.Series(values, index=index.normalize(), name=name, dtype=float).dropna()
    return series[~series.index.duplicated(keep="last")].sort_index()
