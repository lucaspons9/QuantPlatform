import pandas as pd
import pytest
from quantlab.backtest.engine import run
from quantlab.data.core import Dataset
from quantlab.strategies.base import History
from quantlab.strategies.momentum import Momentum
from quantlab.experiments.config import Parameters, Portfolio
from test_accounting import Fixed


def test_next_open_not_signal_close(small_data, config):
    frame = small_data.frame.copy()
    frame.loc[
        (frame.symbol == "A") & (frame.date >= config.start), ["open", "high", "low", "close"]
    ] = 20
    result = run(Dataset.create(frame, {}), config, Fixed())
    first = result.trades.iloc[0]
    assert first.signal_date == pd.Timestamp("2020-01-02")
    assert first.date == pd.Timestamp("2020-01-03")
    assert first.price == 20 and first.quantity == 50
    assert result.returns.iloc[0].equity == 1000


def test_future_trap_and_copy_isolation(small_data, config):
    observed = []

    class Spy:
        def targets(self, h):
            assert h.total_returns.index.max() == h.asof
            observed.append(h.total_returns.copy())
            h.total_returns.iloc[:] = 999
            return {"A": 1}

    original = run(small_data, config, Spy())
    frame = small_data.frame.copy()
    frame.loc[
        (frame.symbol == "A") & (frame.date >= pd.Timestamp("2020-02-04")),
        ["open", "high", "low", "close"],
    ] = 100
    changed = run(Dataset.create(frame, {}), config, Spy())
    pd.testing.assert_frame_equal(original.trades, changed.trades)
    pd.testing.assert_frame_equal(observed[0], observed[2])
    assert observed[1].iloc[0, 0] == 1  # mutation did not poison engine index


def test_momentum_skip_and_exact_endpoints():
    p = Parameters(lookback=4, skip=1, top_n=1)
    index = pd.date_range("2020-01-01", periods=5)
    prices = pd.DataFrame({"A": [1, 2, 3, 4, 0.01], "B": [1, 1, 1, 2, 1000]}, index=index)
    h = History(index[-1], prices, ("A", "B"))
    assert Momentum(p, Portfolio(max_weight=1)).targets(h) == {"A": 1}
    assert (
        Momentum(p, Portfolio(max_weight=1)).targets(
            History(index[-2], prices.iloc[:-1], ("A", "B"))
        )
        == {}
    )


def test_unknown_universe_and_weights(small_data, config):
    class Invalid:
        def targets(self, h):
            return {"FUTURE": 1}

    with pytest.raises(ValueError, match="invalid target"):
        run(small_data, config, Invalid())
    config.universe.symbols = ["FUTURE"]
    with pytest.raises(ValueError, match="missing securities"):
        run(small_data, config, Fixed())
