"""Canonical raw OHLCV data, strict validation, and immutable content-addressed snapshots."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import exchange_calendars as xcals

COLUMNS = ["date", "symbol", "open", "high", "low", "close", "volume", "split", "dividend"]


def sessions(start: str, end: str) -> pd.DatetimeIndex:
    begin, finish = pd.Timestamp(start), pd.Timestamp(end)
    if begin > finish:
        raise ValueError("Calendar start exceeds end")
    calendar = xcals.get_calendar(
        "XNYS", start=begin - pd.Timedelta(days=10), end=finish + pd.Timedelta(days=10)
    )
    return calendar.sessions_in_range(begin, finish).tz_localize(None)


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    """Only normalize representation; never fill prices or infer corporate actions."""
    if set(frame.columns) != set(COLUMNS):
        raise ValueError(f"Expected exactly {COLUMNS}")
    df = frame[COLUMNS].copy()
    df["date"] = pd.to_datetime(df.date, errors="raise")
    if df.date.dt.tz is not None or (df.date != df.date.dt.normalize()).any():
        raise ValueError("Dates must be timezone-naive midnight exchange-session labels")
    for col in COLUMNS[2:]:
        df[col] = pd.to_numeric(df[col], errors="raise").astype(float)
    return df.sort_values(["date", "symbol"]).reset_index(drop=True)


def validate(df: pd.DataFrame) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if df.empty:
        return {"errors": ["Empty dataset"], "warnings": [], "rows": 0}
    if df.isna().any().any():
        errors.append("Missing values")
    if not df.symbol.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
        errors.append("Missing/invalid identifiers")
    if df.duplicated(["date", "symbol"]).any():
        errors.append("Duplicate symbol/session observations")
    if not np.isfinite(df[COLUMNS[2:]].to_numpy()).all():
        errors.append("Nonfinite numeric values")
    if (df[["open", "high", "low", "close", "split"]] <= 0).any().any():
        errors.append("Nonpositive prices or split factors")
    if (df[["volume", "dividend"]] < 0).any().any():
        errors.append("Negative volume/dividend; unsupported distribution")
    if (
        (df.high < df[["open", "close", "low"]].max(axis=1))
        | (df.low > df[["open", "close", "high"]].min(axis=1))
    ).any():
        errors.append("Invalid OHLC relationships")
    if ((df.split != 1) & (df.dividend != 0)).any():
        errors.append("Simultaneous split/dividend needs explicit vendor entitlement convention")
    expected = sessions(str(df.date.min().date()), str(df.date.max().date()))
    if not df.date.isin(expected).all():
        errors.append("Observations outside XNYS calendar")
    for symbol, group in df.groupby("symbol"):
        if len(group) != len(expected):
            errors.append(f"{symbol}: missing sessions (V0 requires a complete rectangular panel)")
        if group.close.diff().eq(0).rolling(10).sum().ge(10).any():
            warnings.append(f"{symbol}: at least 10 unchanged closes")
        change = (group.close * group.split + group.dividend) / group.close.shift(1) - 1
        if change.abs().gt(0.4).any():
            warnings.append(f"{symbol}: action-adjusted discontinuity >40%; review source")
        if group.volume.eq(0).any():
            warnings.append(f"{symbol}: zero volume; engine rejects trading on such dates")
    return {"errors": errors, "warnings": warnings, "rows": len(df), "calendar": "XNYS"}


def total_return_index(df: pd.DataFrame) -> pd.DataFrame:
    """Forward-only index; splits first, dividends per post-split share. No future adjustment."""
    prices = df.pivot(index="date", columns="symbol", values="close")
    splits = df.pivot(index="date", columns="symbol", values="split")
    dividends = df.pivot(index="date", columns="symbol", values="dividend")
    factors = splits * (prices + dividends) / prices.shift(1)
    factors.iloc[0] = 1.0
    return factors.cumprod()


@dataclass
class Dataset:
    frame: pd.DataFrame
    metadata: dict[str, Any]
    quality: dict[str, Any]
    fingerprint: str

    @classmethod
    def create(cls, frame: pd.DataFrame, metadata: dict[str, Any]) -> "Dataset":
        df = normalize(frame)
        quality = validate(df)
        if quality["errors"]:
            raise ValueError("; ".join(quality["errors"]))
        canonical = df.to_csv(index=False, float_format="%.17g", date_format="%Y-%m-%d")
        digest = sha256((canonical + json.dumps(metadata, sort_keys=True)).encode()).hexdigest()
        return cls(df, metadata, quality, digest)

    def save(self, root: str | Path) -> Path:
        path = Path(root) / self.fingerprint
        if path.exists():
            Dataset.load(path)
            return path
        path.mkdir(parents=True)
        self.frame.to_parquet(path / "bars.parquet", index=False)
        (path / "metadata.json").write_text(json.dumps(self.metadata, indent=2))
        (path / "validation.json").write_text(json.dumps(self.quality, indent=2))
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Dataset":
        path = Path(path)
        result = cls.create(
            pd.read_parquet(path / "bars.parquet"), json.loads((path / "metadata.json").read_text())
        )
        if result.fingerprint != path.name:
            raise ValueError("Dataset fingerprint mismatch: snapshot was modified")
        return result
