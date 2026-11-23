from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["green", "amber", "red"]


class Signal(BaseModel):
    id: str
    name: str
    unit: str
    value: float
    status: Status
    rule: str
    state_since: date
    source_url: str
    signed: bool = False  # show +/- on the value
    spark: list[float] = Field(default_factory=list, exclude=True)  # recent history for the sparkline
    spark_days: int = Field(default=0, exclude=True)


class SignalError(BaseModel):
    id: str
    name: str
    error: str
