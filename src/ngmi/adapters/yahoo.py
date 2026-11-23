from typing import Any

import pandas as pd

from ngmi.adapters.base import http_client, to_daily

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
# Yahoo rejects requests without a browser-like user agent.
HEADERS = {"User-Agent": "Mozilla/5.0"}


def parse(payload: dict[str, Any], symbol: str) -> pd.Series:
    result = payload["chart"]["result"][0]
    tz = result["meta"].get("exchangeTimezoneName", "UTC")
    index = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert(tz).tz_localize(None)
    closes = result["indicators"]["quote"][0]["close"]
    return to_daily(index, closes, symbol)


class YahooAdapter:
    def fetch(self, symbol: str) -> pd.Series:
        with http_client() as client:
            response = client.get(URL.format(symbol=symbol), params={"range": "5y", "interval": "1d"}, headers=HEADERS)
            response.raise_for_status()
            return parse(response.json(), symbol)
