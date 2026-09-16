import pytest
from quantlab.backtest.accounting import Account
from quantlab.backtest.engine import run
from quantlab.experiments.config import Costs


class Fixed:
    def targets(self, history):
        return {"A": 1.0}


def test_manual_purchase_sale_close():
    a = Account(1000)
    a.fill("A", 10, 20, 2)
    assert a.cash == 798
    assert a.basis["A"] == 20
    a.fill("A", 10, 30, 3)
    assert a.basis["A"] == 25
    a.fill("A", -5, 40, 2)
    assert a.realized == 75
    assert a.cash == 693
    assert a.value({"A": 40}) == 1293
    a.fill("A", -15, 20, 1)
    assert a.realized == 0
    assert a.cash == 992
    assert a.costs == 8
    assert a.quantities["A"] == 0


def test_split_and_dividend():
    a = Account(1000)
    a.fill("A", 10, 20, 0)
    a.action("A", 2, 0)
    assert a.quantities["A"] == 20
    assert a.basis["A"] == 10
    assert a.value({"A": 10}) == 1000
    a.action("A", 1, 1)
    assert a.cash == 820
    assert a.dividends == 20
    assert a.value({"A": 9}) == 1000


def test_invalid_fill():
    a = Account(100)
    with pytest.raises(ValueError):
        a.fill("A", 11, 10, 0)
    with pytest.raises(ValueError):
        a.fill("A", -1, 10, 0)


def test_fully_invested_cost_budget(small_data, config):
    config.costs = Costs(commission_bps=100, spread_bps=0, slippage_bps=0)
    result = run(small_data, config, Fixed())
    assert result.trades.iloc[0].quantity == pytest.approx(1000 / 1.01 / 10)
    assert result.returns.iloc[0].equity == pytest.approx(1000 / 1.01)
    assert result.returns.cost.sum() == pytest.approx(1000 - 1000 / 1.01)
    assert result.returns.cash.min() >= 0
    assert len(result.trades) == 1


def test_rebalance_sell_before_buy(small_data, config):
    class Rotate:
        def targets(self, h):
            return {"A": 1} if h.asof.month == 1 and h.asof.day < 20 else {"B": 1}

    result = run(small_data, config, Rotate())
    assert list(result.trades.quantity) == [100, -100, 50]
    assert list(result.trades.symbol) == ["A", "A", "B"]
    assert result.returns.equity.eq(1000).all()


def test_engine_actions_and_pnl(small_data, config):
    from quantlab.data.core import Dataset

    frame = small_data.frame.copy()
    dates = frame.date.unique()
    mask = (frame.symbol == "A") & (frame.date >= dates[3])
    frame.loc[mask, ["open", "high", "low", "close"]] = 5
    frame.loc[(frame.symbol == "A") & (frame.date == dates[3]), "split"] = 2
    frame.loc[
        (frame.symbol == "A") & (frame.date >= dates[4]), ["open", "high", "low", "close"]
    ] = 4
    frame.loc[(frame.symbol == "A") & (frame.date == dates[4]), "dividend"] = 1
    result = run(Dataset.create(frame, {}), config, Fixed(), buy_hold=True)
    assert result.returns.equity.to_numpy() == pytest.approx(1000)
    assert result.returns.iloc[-1]["cash"] == 200
    assert result.returns.iloc[-1]["dividends"] == 200
    assert result.returns.iloc[-1]["unrealized_pnl"] == -200
    assert result.holdings.query("symbol == 'A'").iloc[-1]["quantity"] == 200


def test_nonfinite_fill_rejected():
    for value in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="Nonfinite"):
            Account(100).fill("A", 1, value, 0)


def test_cost_components(small_data, config):
    config.costs = Costs(commission_bps=10, spread_bps=20, slippage_bps=30)
    result = run(small_data, config, Fixed())
    trade = result.trades.iloc[0]
    assert trade.commission == pytest.approx(trade.notional * 0.001)
    assert trade.spread == pytest.approx(trade.notional * 0.001)
    assert trade.slippage == pytest.approx(trade.notional * 0.003)
    assert result.returns.iloc[0].equity == pytest.approx(1000 / 1.005)
