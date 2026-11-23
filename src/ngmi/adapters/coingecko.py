from typing import Any

import pandas as pd

from ngmi.adapters.base import http_client, to_daily

URL = "https://api.coingecko.com/api/v3/coins/{id}/market_chart"
DAYS = 365  # free public API caps history at one year


def parse(payload: dict[str, Any], symbol: str) -> pd.Series:
    prices = payload["prices"]
    index = pd.to_datetime([ms for ms, _ in prices], unit="ms")
    return to_daily(index, [price for _, price in prices], symbol)


class CoinGeckoAdapter:
    def fetch(self, symbol: str) -> pd.Series:
        with http_client() as client:
            params = {"vs_currency": "usd", "days": DAYS, "interval": "daily"}
            response = client.get(URL.format(id=symbol), params=params)
            response.raise_for_status()
            return parse(response.json(), symbol)
