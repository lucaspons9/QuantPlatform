from typing import Literal
from pathlib import Path
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Universe(Strict):
    symbols: list[str]
    label: str = "User-selected static universe; selection/survivorship bias possible"
    kind: Literal["static"] = "static"

    @model_validator(mode="after")
    def valid(self) -> "Universe":
        if not self.symbols or len(set(self.symbols)) != len(self.symbols):
            raise ValueError("Universe requires unique symbols")
        return self


class Costs(Strict):
    commission_bps: float = Field(default=1, ge=0, le=1000)
    spread_bps: float = Field(default=4, ge=0, le=1000)
    slippage_bps: float = Field(default=2, ge=0, le=1000)

    @property
    def rate(self) -> float:
        return (self.commission_bps + self.spread_bps / 2 + self.slippage_bps) / 10000


class Portfolio(Strict):
    initial_cash: float = Field(default=100000, gt=0)
    gross_exposure: float = Field(default=1, gt=0, le=1)
    max_weight: float = Field(default=0.25, gt=0, le=1)
    cash_behavior: Literal["retain_zero_interest"] = "retain_zero_interest"


class Parameters(Strict):
    lookback: int = Field(default=252, ge=2)
    skip: int = Field(default=21, ge=0)
    top_n: int = Field(default=4, ge=1)

    @model_validator(mode="after")
    def valid(self) -> "Parameters":
        if self.skip >= self.lookback:
            raise ValueError("skip must be less than lookback")
        return self


class Period(Strict):
    name: Literal["train", "validation", "test"]
    start: str
    end: str


class ExperimentConfig(Strict):
    dataset: str
    start: str
    end: str
    universe: Universe
    strategy: str = "momentum"
    parameters: Parameters = Field(default_factory=Parameters)
    portfolio: Portfolio = Field(default_factory=Portfolio)
    costs: Costs = Field(default_factory=Costs)
    periods: list[Period]
    allow_test: bool = False
    execution: Literal["next_open"] = "next_open"
    benchmark: Literal["equal_weight_buy_hold"] = "equal_weight_buy_hold"
    annualization: int = Field(default=252, ge=1)
    seed: int = 0

    @model_validator(mode="after")
    def valid(self) -> "ExperimentConfig":
        import pandas as pd

        start, end = pd.Timestamp(self.start), pd.Timestamp(self.end)
        if start > end:
            raise ValueError("start exceeds end")
        previous = None
        for period in sorted(self.periods, key=lambda x: x.start):
            a, b = pd.Timestamp(period.start), pd.Timestamp(period.end)
            if a > b or (previous is not None and a <= previous):
                raise ValueError("Invalid or overlapping periods")
            previous = b
        if not self.periods:
            raise ValueError("Explicit research periods required")
        return self

    @classmethod
    def load(cls, path: str | Path) -> "ExperimentConfig":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()))
