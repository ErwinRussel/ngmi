from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from ngmi import history
from ngmi.config import PiCycleConfig, Plan, PlanSignalConfig, WeeklyRsiConfig
from ngmi.models import Signal, SignalError
from ngmi.rules import pi_cycle, plan, weekly_rsi

CFG = PlanSignalConfig(amber_within=10)


def daily(values: list[float], start: str = "2026-01-01") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


def make_plan(done: int = 0) -> Plan:
    return Plan(entry=100, done=done, steps=[{"gain": 100, "sell": 25}, {"gain": 200, "sell": 25}])


def run(prices: list[float], done: int = 0) -> Signal:
    return plan.evaluate(daily(prices), make_plan(done), CFG, "BTC", "", "plan:bitcoin")


def test_plan_step_due_is_red_with_instructions():
    signal = run([150, 190, 210])
    assert signal.status == "red" and signal.value == 110
    assert signal.rule.startswith("Step 1 due: sell 25%") and "done = 1" in signal.rule
    assert signal.state_since == date(2026, 1, 3)


def test_plan_multiple_steps_due_at_once():
    signal = run([310])
    assert "Steps 1–2 due: sell 50%" in signal.rule and "done = 2" in signal.rule


def test_plan_amber_near_next_step_and_green_far_away():
    assert run([185]).status == "amber"  # 200 is 8% away
    far = run([150])
    assert far.status == "green" and "Step 1 sells 25% at +100% (200.00), 33% away" in far.rule


def test_plan_done_steps_are_skipped_and_finished_plan_is_green():
    assert run([210], done=1).status == "green"  # step 2 is at 300
    finished = run([500], done=2)
    assert finished.status == "green" and finished.rule.startswith("Plan done")


def test_plan_below_entry():
    assert "Below your entry" in run([80]).rule


def test_plan_validation():
    with pytest.raises(ValidationError, match="increasing gains"):
        Plan(entry=1, steps=[{"gain": 200, "sell": 10}, {"gain": 100, "sell": 10}])
    with pytest.raises(ValidationError, match="more than 100%"):
        Plan(entry=1, steps=[{"gain": 100, "sell": 60}, {"gain": 200, "sell": 60}])
    with pytest.raises(ValidationError, match="only 1 steps"):
        Plan(entry=1, done=2, steps=[{"gain": 100, "sell": 10}])


def test_history_record_replaces_same_day_and_counts_red_streaks(tmp_path):
    path = tmp_path / "history.jsonl"

    def sig(status: str) -> Signal:
        return Signal(id="dd", name="BTC · drawdown", unit="%", value=1, status=status, rule="",
                      state_since=date(2026, 1, 1), source_url="")

    history.record([sig("green")], date(2026, 1, 1), path)
    history.record([sig("red")], date(2026, 1, 2), path)
    history.record([sig("amber")], date(2026, 1, 3), path)
    history.record([sig("red"), SignalError(id="x", name="X", error="boom")], date(2026, 1, 3), path)  # rerun
    history.record([sig("red")], date(2026, 1, 5), path)

    snapshots = history.load(path)
    assert [s.day.day for s in snapshots] == [1, 2, 3, 5]
    (streak,) = history.red_streaks(snapshots)
    assert (streak.checks, streak.since) == (3, date(2026, 1, 2))


def test_weekly_rsi_overheated_on_relentless_rally():
    rally = daily([100 * 1.01**i for i in range(200)])
    assert weekly_rsi.evaluate(rally, WeeklyRsiConfig(), "X", "", "rsi:x").status == "red"
    chop = daily([100 + (5 if i % 14 < 7 else -5) for i in range(200)])
    assert weekly_rsi.evaluate(chop, WeeklyRsiConfig(), "X", "", "rsi:x").status == "green"


def test_pi_cycle_needs_history_and_flags_parabolic_moves():
    with pytest.raises(ValueError, match="need 350 days"):
        pi_cycle.evaluate(daily([1.0] * 100), PiCycleConfig())
    flat = pi_cycle.evaluate(daily([100.0] * 400), PiCycleConfig())
    assert flat.status == "green" and flat.value == 50
    parabolic = daily([100.0] * 300 + [100 * 1.02**i for i in range(200)])
    assert pi_cycle.evaluate(parabolic, PiCycleConfig()).status == "red"
