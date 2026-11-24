from datetime import date
from typing import Any

import pandas as pd

from ngmi.adapters.base import http_client, to_daily

# Wikimedia's official pageviews API: free, no key, daily since July 2015. Counts humans only.
URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{article}/daily/{start}/{end}"
START = "20150701"


def parse(payload: dict[str, Any], article: str) -> pd.Series:
    items = payload["items"]
    index = pd.DatetimeIndex(pd.to_datetime([i["timestamp"][:8] for i in items], format="%Y%m%d"))
    return to_daily(index, [float(i["views"]) for i in items], article)


class WikipediaPageviewsAdapter:
    def fetch(self, article: str) -> pd.Series:
        url = URL.format(article=article, start=START, end=date.today().strftime("%Y%m%d"))
        with http_client() as client:
            response = client.get(url)
            response.raise_for_status()
            return parse(response.json(), article)
