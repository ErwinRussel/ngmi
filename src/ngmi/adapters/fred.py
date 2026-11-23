import io
from datetime import date, timedelta

import pandas as pd

from ngmi.adapters.base import http_client, to_daily

# The public graph CSV needs no API key (it rejects browser user agents, so keep ours).
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
HISTORY_DAYS = 3 * 365


def parse(text: str, series_id: str) -> pd.Series:
    frame = pd.read_csv(io.StringIO(text), na_values=["."])
    values = pd.to_numeric(frame[series_id], errors="coerce")
    return to_daily(pd.DatetimeIndex(pd.to_datetime(frame["observation_date"])), values.tolist(), series_id)


class FredAdapter:
    def fetch(self, series_id: str) -> pd.Series:
        start = date.today() - timedelta(days=HISTORY_DAYS)
        with http_client() as client:
            response = client.get(URL, params={"id": series_id, "cosd": start.isoformat()})
            response.raise_for_status()
            return parse(response.text, series_id)
