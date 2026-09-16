"""Daily simple returns; zero risk-free rate; undefined ratios are null with reasons."""

from typing import Any
import numpy as np
import pandas as pd


def drawdown(returns: pd.Series) -> pd.Series:
    equity = (1 + returns).cumprod()
    peak = equity.cummax().clip(lower=1)
    return equity / peak - 1


def metrics(returns: pd.Series, annualization: int = 252) -> dict[str, Any]:
    r = returns.astype(float)
    if r.empty or not np.isfinite(r).all() or (r <= -1).any():
        raise ValueError("Metrics require finite simple returns greater than -1")
    n = len(r)
    growth = float(np.prod(1 + r.to_numpy(dtype=float)))
    cagr = growth ** (annualization / n) - 1
    vol = float(r.std(ddof=1) * np.sqrt(annualization)) if n > 1 else None
    downside = float(
        np.sqrt(np.square(np.minimum(r.to_numpy(dtype=float), 0)).mean()) * np.sqrt(annualization)
    )
    dd = float(drawdown(r).min())
    mean = float(r.mean() * annualization)
    ratios = {
        "sharpe": mean / vol if vol is not None and vol > 1e-14 else None,
        "sortino": mean / downside if downside > 1e-14 else None,
        "calmar": cagr / abs(dd) if dd < -1e-14 else None,
    }
    return {
        "observations": n,
        "cumulative_return": growth - 1,
        "cagr": cagr,
        "annualized_volatility": vol,
        "max_drawdown": dd,
        **ratios,
        "undefined": {
            k: "Zero denominator or insufficient history" for k, v in ratios.items() if v is None
        },
    }


def rolling(returns: pd.Series, window: int = 63, annualization: int = 252) -> pd.DataFrame:
    if window < 2:
        raise ValueError("Rolling window must be >=2")
    vol = returns.rolling(window).std() * np.sqrt(annualization)
    return pd.DataFrame(
        {
            "rolling_return": (1 + returns).rolling(window).apply(np.prod, raw=True) - 1,
            "rolling_volatility": vol,
            "rolling_sharpe": returns.rolling(window).mean()
            * annualization
            / vol.where(vol > 1e-14),
        }
    )


def calendar_returns(frame: pd.DataFrame, frequency: str) -> pd.Series:
    if frequency not in ("ME", "YE"):
        raise ValueError("Expected ME or YE")
    return (1 + frame.set_index("date")["return"]).resample(frequency).prod() - 1


def subperiods(frame: pd.DataFrame, annualization: int = 252) -> pd.DataFrame:
    return pd.DataFrame(
        {name: metrics(group["return"], annualization) for name, group in frame.groupby("period")}
    ).T
