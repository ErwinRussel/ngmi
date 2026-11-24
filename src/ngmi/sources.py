from concurrent.futures import Future
from dataclasses import dataclass, fields
from threading import Lock

from ngmi.adapters.alternative_me import FearGreedAdapter
from ngmi.adapters.base import SeriesAdapter, SymbolAdapter
from ngmi.adapters.coingecko import CoinGeckoAdapter
from ngmi.adapters.fred import FredAdapter
from ngmi.adapters.okx import OkxFundingAdapter
from ngmi.adapters.wikipedia import WikipediaPageviewsAdapter
from ngmi.adapters.yahoo import YahooAdapter


@dataclass(frozen=True)
class Sources:
    """Every adapter the signals depend on, injected so tests and --demo can swap in mocks."""

    fear_greed: SeriesAdapter
    crypto: SymbolAdapter
    stocks: SymbolAdapter
    funding: SymbolAdapter
    fred: SymbolAdapter
    pageviews: SymbolAdapter


def live_sources() -> Sources:
    return Sources(
        fear_greed=FearGreedAdapter(),
        crypto=CoinGeckoAdapter(),
        stocks=YahooAdapter(),
        funding=OkxFundingAdapter(),
        fred=FredAdapter(),
        pageviews=WikipediaPageviewsAdapter(),
    )


class _Memo:
    """Per-run cache so a symbol used by several tiles is fetched once, even from parallel jobs."""

    def __init__(self, adapter):
        self._adapter = adapter
        self._results: dict[tuple, Future] = {}
        self._lock = Lock()

    def fetch(self, *args):
        with self._lock:
            future = self._results.get(args)
            owner = future is None
            if owner:
                future = self._results[args] = Future()
        if owner:
            try:
                future.set_result(self._adapter.fetch(*args))
            except Exception as exc:
                future.set_exception(exc)
        return future.result()


def memoized(sources: Sources) -> Sources:
    return Sources(**{f.name: _Memo(getattr(sources, f.name)) for f in fields(sources)})
