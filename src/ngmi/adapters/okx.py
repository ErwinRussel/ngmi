from typing import Any

import pandas as pd

from ngmi.adapters.base import http_client

URL = "https://www.okx.com/api/v5/public/funding-rate-history"
PAGES = 3  # 100 rows per page, 3 fundings a day: ~100 days of history


def parse(rows: list[dict[str, Any]], instrument: str) -> pd.Series:
    """Per-funding rates -> daily annualized funding in percent."""
    index = pd.to_datetime([int(r["fundingTime"]) for r in rows], unit="ms")
    rates = pd.Series([float(r["fundingRate"]) for r in rows], index=index).sort_index()
    daily = rates.groupby(rates.index.normalize()).mean()
    return (daily * 3 * 365 * 100).rename(instrument)


class OkxFundingAdapter:
    """Annualized daily funding (%) for an OKX perpetual; works from US IPs, unlike Binance."""

    def fetch(self, instrument: str) -> pd.Series:
        rows: list[dict[str, Any]] = []
        with http_client() as client:
            params: dict[str, Any] = {"instId": instrument, "limit": 100}
            for _ in range(PAGES):
                response = client.get(URL, params=params)
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") != "0":
                    raise RuntimeError(payload.get("msg") or f"OKX error {payload.get('code')}")
                page = payload["data"]
                if not page:
                    break
                rows.extend(page)
                params["after"] = page[-1]["fundingTime"]
        return parse(rows, instrument)
