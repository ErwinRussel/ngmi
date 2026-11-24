import os
import tomllib
from importlib.resources import files
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator


class Thresholds(BaseModel):
    """Higher values are worse: amber at or above `amber`, red at or above `red`."""

    enabled: bool = True
    amber: float
    red: float

    @model_validator(mode="after")
    def _ordered(self):
        if self.amber > self.red:
            raise ValueError(f"{type(self).__name__}: amber must be <= red")
        return self


class LowIsBadThresholds(BaseModel):
    """Lower values are worse: amber below `amber`, red below `red`."""

    enabled: bool = True
    amber: float
    red: float

    @model_validator(mode="after")
    def _ordered(self):
        if self.amber < self.red:
            raise ValueError(f"{type(self).__name__}: amber must be >= red")
        return self


class FearGreedConfig(Thresholds):
    amber: float = 60
    red: float = 75


class DrawdownConfig(Thresholds):
    window_days: int = Field(default=90, gt=0)
    amber: float = 10
    red: float = 20


class MovingAverageConfig(BaseModel):
    enabled: bool = True
    fast: int = Field(default=50, gt=0)
    slow: int = Field(default=200, gt=0)

    @model_validator(mode="after")
    def _ordered(self):
        if self.fast >= self.slow:
            raise ValueError("moving_average: fast must be < slow")
        return self


class FundingConfig(Thresholds):
    instrument: str = "BTC-USDT-SWAP"
    avg_days: int = Field(default=7, gt=0)
    amber: float = 15
    red: float = 30


class LiquidityConfig(LowIsBadThresholds):
    series: str = "WALCL"
    lookback_days: int = Field(default=90, gt=0)
    amber: float = 0
    red: float = -2


class RatesConfig(Thresholds):
    series: str = "DGS10"
    lookback_days: int = Field(default=30, gt=0)
    amber: float = 25
    red: float = 50


class WeeklyRsiConfig(Thresholds):
    period: int = Field(default=14, gt=1)
    amber: float = 70
    red: float = 80


class AttentionConfig(Thresholds):
    articles: list[str] = Field(default_factory=lambda: ["Bitcoin", "Cryptocurrency"])  # English Wikipedia titles
    avg_days: int = Field(default=7, gt=0)
    amber: float = 2  # 7d avg pageviews as a multiple of the 1y median
    red: float = 3


class PiCycleConfig(Thresholds):
    symbol: str = "BTC-USD"  # Yahoo: long daily history, unlike CoinGecko's free year
    amber: float = 90  # 111d MA as % of 2x the 350d MA
    red: float = 100


class VixConfig(LowIsBadThresholds):
    symbol: str = "^VIX"
    amber: float = 17
    red: float = 15  # sell zone: complacency
    scale_in: float = 25
    buy: float = 35

    @model_validator(mode="after")
    def _zones(self):
        if not self.amber < self.scale_in < self.buy:
            raise ValueError("vix: need amber < scale_in < buy")
        return self


class PlanSignalConfig(BaseModel):
    enabled: bool = True
    amber_within: float = Field(default=10, gt=0)  # % away from the next sell price


class PlanStep(BaseModel):
    gain: float = Field(gt=0)  # % above entry
    sell: float = Field(gt=0, le=100)  # % of the original position


class Plan(BaseModel):
    entry: float = Field(gt=0)
    steps: list[PlanStep] = Field(min_length=1)
    done: int = Field(default=0, ge=0)  # steps you've already sold

    @model_validator(mode="after")
    def _valid(self) -> "Plan":
        gains = [s.gain for s in self.steps]
        if gains != sorted(gains) or len(set(gains)) != len(gains):
            raise ValueError("plan steps must have increasing gains")
        if sum(s.sell for s in self.steps) > 100:
            raise ValueError("plan steps sell more than 100% of the position")
        if self.done > len(self.steps):
            raise ValueError(f"done = {self.done} but the plan has only {len(self.steps)} steps")
        return self


class Positions(BaseModel):
    crypto: list[str] = Field(default_factory=list)
    stocks: list[str] = Field(default_factory=list)


class Signals(BaseModel):
    fear_greed: FearGreedConfig = Field(default_factory=FearGreedConfig)
    drawdown: DrawdownConfig = Field(default_factory=DrawdownConfig)
    moving_average: MovingAverageConfig = Field(default_factory=MovingAverageConfig)
    funding: FundingConfig = Field(default_factory=FundingConfig)
    liquidity: LiquidityConfig = Field(default_factory=LiquidityConfig)
    rates: RatesConfig = Field(default_factory=RatesConfig)
    weekly_rsi: WeeklyRsiConfig = Field(default_factory=WeeklyRsiConfig)
    pi_cycle: PiCycleConfig = Field(default_factory=PiCycleConfig)
    vix: VixConfig = Field(default_factory=VixConfig)
    attention: AttentionConfig = Field(default_factory=AttentionConfig)
    plan: PlanSignalConfig = Field(default_factory=PlanSignalConfig)


class Config(BaseModel):
    positions: Positions = Field(default_factory=Positions)
    watch: Positions = Field(default_factory=Positions)
    plans: dict[str, Plan] = Field(default_factory=dict)  # keyed by position symbol
    signals: Signals = Field(default_factory=Signals)


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "ngmi"


def config_path() -> Path:
    return config_dir() / "config.toml"


def default_config_text() -> str:
    return files("ngmi").joinpath("default_config.toml").read_text()


def load_config(path: Path | None = None) -> Config:
    load_dotenv(config_dir() / ".env")
    load_dotenv()
    path = path or config_path()
    text = path.read_text() if path.exists() else default_config_text()
    return Config.model_validate(tomllib.loads(text))
