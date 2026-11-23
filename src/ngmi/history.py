import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ngmi.models import Signal, SignalError


def data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "ngmi"


def history_path() -> Path:
    return data_dir() / "history.jsonl"


@dataclass(frozen=True)
class Snapshot:
    day: date
    signals: dict[str, dict]  # id -> {"name", "status", "value"}


def load(path: Path | None = None) -> list[Snapshot]:
    path = path or history_path()
    if not path.exists():
        return []
    snapshots = []
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            snapshots.append(Snapshot(date.fromisoformat(row["date"]), row["signals"]))
    return sorted(snapshots, key=lambda s: s.day)


def record(results: list[Signal | SignalError], today: date, path: Path | None = None) -> None:
    """Store today's statuses; a rerun on the same day replaces that day's entry."""
    path = path or history_path()
    signals = {
        r.id: {"name": r.name, "status": r.status, "value": r.value} for r in results if isinstance(r, Signal)
    }
    kept = [s for s in load(path) if s.day != today] + [Snapshot(today, signals)]
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"date": s.day.isoformat(), "signals": s.signals}) for s in sorted(kept, key=lambda s: s.day)]
    path.write_text("\n".join(lines) + "\n")


@dataclass(frozen=True)
class Streak:
    id: str
    name: str
    checks: int  # consecutive logged days it was red, ending with the latest
    since: date


def red_streaks(snapshots: list[Snapshot]) -> list[Streak]:
    """Signals red on every check up to the latest, longest first."""
    if not snapshots:
        return []
    streaks = []
    for signal_id, latest in snapshots[-1].signals.items():
        if latest["status"] != "red":
            continue
        checks, since = 0, snapshots[-1].day
        for snap in reversed(snapshots):
            if snap.signals.get(signal_id, {}).get("status") != "red":
                break
            checks, since = checks + 1, snap.day
        streaks.append(Streak(signal_id, latest["name"], checks, since))
    return sorted(streaks, key=lambda s: (-s.checks, s.name))
