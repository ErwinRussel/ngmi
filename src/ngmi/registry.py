from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ngmi.config import Config, Positions
from ngmi.models import Signal, SignalError
from ngmi.rules import attention, drawdown, fear_greed, funding, liquidity, moving_average, pi_cycle, plan, rates, vix, weekly_rsi
from ngmi.sources import Sources, memoized

CRYPTO_TICKERS = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP", "dogecoin": "DOGE"}
STOCK_NAMES = {"GC=F": "Gold", "SI=F": "Silver", "^GSPC": "S&P 500", "^NDX": "Nasdaq 100"}


@dataclass(frozen=True)
class Job:
    """One tile's worth of work; failures are isolated per job."""

    id: str
    name: str
    run: Callable[[], Signal]


@dataclass(frozen=True)
class Asset:
    symbol: str
    label: str
    url: str
    kind: str  # "crypto" | "stocks"


@dataclass(frozen=True)
class SignalSpec:
    id: str
    name: str
    enabled: Callable[[Config], bool]
    jobs: Callable[[Config, Sources], list[Job]]


def assets(positions: Positions) -> list[Asset]:
    crypto = [
        Asset(c, CRYPTO_TICKERS.get(c, c.upper()), f"https://www.coingecko.com/en/coins/{c}", "crypto")
        for c in positions.crypto
    ]
    stocks = [
        Asset(t, STOCK_NAMES.get(t, t), f"https://finance.yahoo.com/quote/{t}", "stocks") for t in positions.stocks
    ]
    return crypto + stocks


def _prices(src: Sources, asset: Asset):
    adapter = src.crypto if asset.kind == "crypto" else src.stocks
    return adapter.fetch(asset.symbol)


def _drawdown_jobs(cfg: Config, src: Sources) -> list[Job]:
    dd = cfg.signals.drawdown
    return [
        Job(f"drawdown:{a.symbol}", f"{a.label} · drawdown",
            lambda a=a: drawdown.evaluate(_prices(src, a), dd, a.label, a.url, f"drawdown:{a.symbol}"))
        for a in assets(cfg.positions)
    ]


def _trend_jobs(cfg: Config, src: Sources) -> list[Job]:
    ma = cfg.signals.moving_average
    return [
        Job(f"trend:{a.symbol}", f"{a.label} · trend",
            lambda a=a: moving_average.evaluate(_prices(src, a), ma, a.label, a.url, f"trend:{a.symbol}"))
        for a in assets(cfg.positions) + assets(cfg.watch)
    ]


def _plan_jobs(cfg: Config, src: Sources) -> list[Job]:
    known = {a.symbol: a for a in assets(cfg.positions) + assets(cfg.watch)}
    jobs = []
    for symbol, p in cfg.plans.items():
        asset = known.get(symbol)
        if asset is None:
            jobs.append(Job(f"plan:{symbol}", f"{symbol} · profit plan", lambda symbol=symbol: _unknown(symbol)))
            continue
        jobs.append(Job(f"plan:{symbol}", f"{asset.label} · profit plan",
                        lambda a=asset, p=p: plan.evaluate(_prices(src, a), p, cfg.signals.plan, a.label, a.url, f"plan:{a.symbol}")))
    return jobs


def _unknown(symbol: str) -> Signal:
    raise ValueError(f"{symbol!r} has a plan but isn't in [positions]")


def _rsi_jobs(cfg: Config, src: Sources) -> list[Job]:
    r = cfg.signals.weekly_rsi
    return [
        Job(f"rsi:{a.symbol}", f"{a.label} · weekly RSI",
            lambda a=a: weekly_rsi.evaluate(_prices(src, a), r, a.label, a.url, f"rsi:{a.symbol}"))
        for a in assets(cfg.positions)
    ]


SPECS: list[SignalSpec] = [
    SignalSpec("plan", "Take-profit plan steps (positions with a [plans] entry)",
               lambda c: c.signals.plan.enabled, _plan_jobs),
    SignalSpec("drawdown", "Drawdown from rolling high (positions)",
               lambda c: c.signals.drawdown.enabled, _drawdown_jobs),
    SignalSpec("trend", "Price vs 50d / 200d MA (positions + watch)",
               lambda c: c.signals.moving_average.enabled, _trend_jobs),
    SignalSpec("weekly_rsi", "Weekly RSI overheating (positions)",
               lambda c: c.signals.weekly_rsi.enabled, _rsi_jobs),
    SignalSpec("pi_cycle", "BTC Pi Cycle Top (Yahoo BTC-USD)",
               lambda c: c.signals.pi_cycle.enabled,
               lambda c, s: [Job("pi_cycle", "BTC · Pi Cycle Top",
                                 lambda: pi_cycle.evaluate(s.stocks.fetch(c.signals.pi_cycle.symbol), c.signals.pi_cycle))]),
    SignalSpec("attention", "Retail attention: Wikipedia pageviews vs 1y normal",
               lambda c: c.signals.attention.enabled,
               lambda c, s: [Job(f"attention:{a}", f"{a} · attention",
                                 lambda a=a: attention.evaluate(s.pageviews.fetch(a), c.signals.attention, a))
                             for a in c.signals.attention.articles]),
    SignalSpec("fear_greed", "Crypto Fear & Greed",
               lambda c: c.signals.fear_greed.enabled,
               lambda c, s: [Job("fear_greed", "Crypto Fear & Greed",
                                 lambda: fear_greed.evaluate(s.fear_greed.fetch(), c.signals.fear_greed))]),
    SignalSpec("funding", "Perp funding rate (OKX)",
               lambda c: c.signals.funding.enabled,
               lambda c, s: [Job("funding", "Funding",
                                 lambda: funding.evaluate(s.funding.fetch(c.signals.funding.instrument), c.signals.funding))]),
    SignalSpec("liquidity", "Liquidity: Fed balance sheet or M2 (FRED)",
               lambda c: c.signals.liquidity.enabled,
               lambda c, s: [Job("liquidity", "Liquidity",
                                 lambda: liquidity.evaluate(s.fred.fetch(c.signals.liquidity.series), c.signals.liquidity))]),
    SignalSpec("rates", "Treasury yield speed (FRED)",
               lambda c: c.signals.rates.enabled,
               lambda c, s: [Job("rates", "Rates",
                                 lambda: rates.evaluate(s.fred.fetch(c.signals.rates.series), c.signals.rates))]),
    SignalSpec("vix", "VIX zones, after @AskLivermore (Yahoo ^VIX)",
               lambda c: c.signals.vix.enabled,
               lambda c, s: [Job("vix", "VIX",
                                 lambda: vix.evaluate(s.stocks.fetch(c.signals.vix.symbol), c.signals.vix))]),
]


def _run(job: Job) -> Signal | SignalError:
    try:
        return job.run()
    except Exception as exc:  # one broken source must not hide the others
        return SignalError(id=job.id, name=job.name, error=str(exc) or type(exc).__name__)


def run_all(config: Config, sources: Sources) -> list[Signal | SignalError]:
    sources = memoized(sources)
    jobs = [job for spec in SPECS if spec.enabled(config) for job in spec.jobs(config, sources)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(_run, jobs))
