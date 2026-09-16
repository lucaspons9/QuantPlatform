import numpy as np
import pandas as pd
import pytest
from quantlab.analytics.metrics import metrics, drawdown, rolling, calendar_returns


def test_known_metrics():
    r = pd.Series([0.1, -0.1, 0.2])
    m = metrics(r, 3)
    assert m["cumulative_return"] == pytest.approx(0.188)
    assert m["cagr"] == pytest.approx(0.188)
    assert m["max_drawdown"] == pytest.approx(-0.1)
    assert m["annualized_volatility"] == pytest.approx(r.std() * np.sqrt(3))
    assert m["sortino"] == pytest.approx(r.mean() * 3 / 0.1)


def test_initial_loss_drawdown():
    assert drawdown(pd.Series([-0.1, 0])).tolist() == pytest.approx([-0.1, -0.1])


def test_zero_and_short_series():
    m = metrics(pd.Series([0.0, 0.0]))
    assert m["sharpe"] is None and m["sortino"] is None and m["calmar"] is None
    assert metrics(pd.Series([0.1]))["annualized_volatility"] is None


def test_rolling_and_monthly():
    r = pd.Series([0.1, 0.2, -0.1, 0.3])
    rolled = rolling(r, 2)
    assert np.isnan(rolled.rolling_return.iloc[0])
    assert rolled.rolling_return.iloc[1] == pytest.approx(0.32)
    assert rolled.rolling_return.iloc[2] == pytest.approx(0.08)
    f = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-02", "2020-01-03", "2020-02-03", "2020-02-04"]),
            "return": r,
        }
    )
    assert calendar_returns(f, "ME").tolist() == pytest.approx([0.32, 0.17])
