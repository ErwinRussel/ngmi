from ngmi.adapters.mock import DEMO_PLANS, DEMO_POSITIONS, DEMO_WATCH, MockSymbolAdapter, MockSeriesAdapter, demo_sources, scripted_series
from ngmi.config import Config, Positions
from ngmi.models import Signal, SignalError
from ngmi.registry import run_all
from ngmi.sources import Sources


def test_demo_sources_produce_every_tile():
    results = run_all(Config(positions=DEMO_POSITIONS, watch=DEMO_WATCH, plans=DEMO_PLANS), demo_sources())
    assert [r.id for r in results] == [
        "plan:bitcoin", "plan:ethereum", "plan:NVDA",
        "drawdown:bitcoin", "drawdown:ethereum", "drawdown:solana", "drawdown:NVDA",
        "trend:bitcoin", "trend:ethereum", "trend:solana", "trend:NVDA", "trend:GC=F", "trend:SI=F",
        "rsi:bitcoin", "rsi:ethereum", "rsi:solana", "rsi:NVDA", "pi_cycle",
        "fear_greed", "funding", "liquidity", "rates",
    ]
    assert all(isinstance(r, Signal) for r in results)
    assert {r.status for r in results} == {"green", "amber", "red"}


def test_one_failing_position_does_not_hide_the_others():
    prices = scripted_series([(250, 10)], 100, seed=0)
    sources = Sources(
        fear_greed=MockSeriesAdapter(scripted_series([(200, 0)], 50, seed=0)),
        crypto=MockSymbolAdapter({"bitcoin": prices}),
        stocks=MockSymbolAdapter({}),
        funding=MockSymbolAdapter({}),
        fred=MockSymbolAdapter({}),
    )
    cfg = Config(positions=Positions(crypto=["bitcoin"], stocks=["NOPE"]))
    by_id = {r.id: r for r in run_all(cfg, sources)}
    assert isinstance(by_id["drawdown:bitcoin"], Signal)
    assert isinstance(by_id["trend:bitcoin"], Signal)
    assert isinstance(by_id["drawdown:NOPE"], SignalError) and "NOPE" in by_id["drawdown:NOPE"].error
    assert isinstance(by_id["fear_greed"], Signal)
    assert isinstance(by_id["rates"], SignalError)


def test_shared_symbol_is_fetched_once():
    calls = []

    class Counting(MockSymbolAdapter):
        def fetch(self, symbol):
            calls.append(symbol)
            return super().fetch(symbol)

    prices = scripted_series([(250, 10)], 100, seed=0)
    sources = demo_sources()
    sources = Sources(**{**sources.__dict__, "crypto": Counting({"bitcoin": prices})})
    run_all(Config(positions=Positions(crypto=["bitcoin"])), sources)
    assert calls == ["bitcoin"]


def test_plan_for_unknown_symbol_is_an_error_tile():
    cfg = Config(plans={"dogecoin": DEMO_PLANS["bitcoin"]})
    (result,) = [r for r in run_all(cfg, demo_sources()) if r.id == "plan:dogecoin"]
    assert isinstance(result, SignalError) and "isn't in [positions]" in result.error
