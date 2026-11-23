from typing import Any

import pandas as pd

from ngmi.adapters.base import http_client, to_daily

URL = "https://api.alternative.me/fng/"


def parse(payload: dict[str, Any]) -> pd.Series:
    rows = payload["data"]
    index = pd.to_datetime([int(r["timestamp"]) for r in rows], unit="s")
    return to_daily(index, [float(r["value"]) for r in rows], "fear_greed")


class FearGreedAdapter:
    def fetch(self) -> pd.Series:
        with http_client() as client:
            response = client.get(URL, params={"limit": 0, "format": "json"})
            response.raise_for_status()
            return parse(response.json())
