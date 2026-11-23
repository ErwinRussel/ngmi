import pandas as pd

from ngmi.config import Plan, PlanSignalConfig
from ngmi.models import Signal, Status
from ngmi.rules.base import state_since, tail_days
from ngmi.rules.format import money


def _status(gain: float, price: float, plan: Plan, cfg: PlanSignalConfig) -> Status:
    pending = plan.steps[plan.done :]
    if not pending:
        return "green"
    if gain >= pending[0].gain:
        return "red"
    target = plan.entry * (1 + pending[0].gain / 100)
    return "amber" if (target / price - 1) * 100 <= cfg.amber_within else "green"


def _steps(first: int, last: int) -> str:
    return f"Step {first}" if first == last else f"Steps {first}–{last}"


def evaluate(prices: pd.Series, plan: Plan, cfg: PlanSignalConfig, label: str, source_url: str, signal_id: str) -> Signal:
    gains = (prices / plan.entry - 1) * 100
    statuses = pd.Series([_status(g, p, plan, cfg) for g, p in zip(gains, prices)], index=prices.index)
    price, gain, status = float(prices.iloc[-1]), float(gains.iloc[-1]), statuses.iloc[-1]
    pending = plan.steps[plan.done :]
    due = [s for s in pending if gain >= s.gain]

    if not pending:
        rule = f"Plan done: all {len(plan.steps)} steps sold. Let the rest ride, or add a step."
    elif due:
        first, last = plan.done + 1, plan.done + len(due)
        rule = (
            f"{_steps(first, last)} due: sell {sum(s.sell for s in due):g}% of the position now."
            f" Then set done = {last}."
        )
    else:
        step = pending[0]
        target = plan.entry * (1 + step.gain / 100)
        away = (target / price - 1) * 100
        if gain < 0:
            rule = f"Below your entry ({money(plan.entry)}). Step {plan.done + 1} sells at {money(target)}."
        elif status == "amber":
            rule = f"Step {plan.done + 1} (sell {step.sell:g}%) is {away:.1f}% away at {money(target)}. Get the order ready."
        else:
            rule = f"Step {plan.done + 1} sells {step.sell:g}% at +{step.gain:g}% ({money(target)}), {away:.0f}% away."

    return Signal(
        id=signal_id,
        name=f"{label} · profit plan",
        unit="% gain",
        value=round(gain, 1),
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=tail_days(prices, 90),
        spark_days=90,
        signed=True,
        source_url=source_url,
    )
