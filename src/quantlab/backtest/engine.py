"""Close signals -> next open target execution -> close mark. Long-only fractional shares."""

from dataclasses import dataclass
from typing import cast
import numpy as np
import pandas as pd
from quantlab.backtest.accounting import Account
from quantlab.data.core import Dataset, total_return_index
from quantlab.experiments.config import ExperimentConfig
from quantlab.strategies.base import History, Strategy


@dataclass
class BacktestResult:
    returns: pd.DataFrame
    holdings: pd.DataFrame
    trades: pd.DataFrame


def run(
    dataset: Dataset, config: ExperimentConfig, strategy: Strategy, buy_hold: bool = False
) -> BacktestResult:
    config = ExperimentConfig.model_validate(config.model_dump())
    symbols = tuple(sorted(config.universe.symbols))
    if not set(symbols).issubset(set(dataset.frame.symbol)):
        raise ValueError("Universe contains missing securities")
    bars = dataset.frame[dataset.frame.symbol.isin(symbols)]
    index = total_return_index(bars)
    dates = index.index[(index.index >= config.start) & (index.index <= config.end)]
    if len(dates) < 2 or dates[0] < index.index[1]:
        raise ValueError("Need at least two run sessions and a pre-start signal session")
    if pd.Timestamp(config.end) > index.index[-1]:
        raise ValueError("Dataset ends before requested end")
    labels = {}
    for date in dates:
        matching = [
            p.name for p in config.periods if pd.Timestamp(p.start) <= date <= pd.Timestamp(p.end)
        ]
        if len(matching) != 1:
            raise ValueError(f"Exactly one research period required for {date}")
        if matching[0] == "test" and not config.allow_test:
            raise ValueError("Untouched test access requires explicit allow_test=true")
        labels[date] = matching[0]
    account = Account(config.portfolio.initial_cash)
    returns, holdings, trades = [], [], []
    previous_value = config.portfolio.initial_cash
    previous_month = None
    for date in dates:
        loc = cast(int, index.index.get_loc(date))
        signal_date = pd.Timestamp(index.index[loc - 1])
        month = (date.year, date.month)
        rebalance = previous_month is None or (not buy_hold and month != previous_month)
        # No execution-day data has been provided to strategy at this point.
        targets = None
        if rebalance:
            targets = strategy.targets(
                History(signal_date, index.iloc[:loc].copy(deep=True), symbols)
            )
            values = list(targets.values())
            if (
                not set(targets).issubset(symbols)
                or not all(
                    np.isfinite(v) and 0 <= v <= config.portfolio.max_weight + 1e-12 for v in values
                )
                or sum(values) > config.portfolio.gross_exposure + 1e-12
            ):
                raise ValueError("Strategy emitted invalid target weights")
        today = bars[bars.date.eq(date)].set_index("symbol")
        for s in symbols:
            account.action(
                s,
                float(cast(float, today.at[s, "split"])),
                float(cast(float, today.at[s, "dividend"])),
            )
        opens = today.open.to_dict()
        closes = today.close.to_dict()
        opening_value = account.value(opens)
        daily_cost, notional = 0.0, 0.0
        if targets is not None:
            current = {s: account.quantities.get(s, 0) * opens[s] for s in symbols}
            # Solve V_after = V_before - rate * absolute traded notional.
            low, high = 0.0, opening_value
            rate = config.costs.rate
            for _ in range(80):
                mid = (low + high) / 2
                f = (
                    mid
                    + rate * sum(abs(targets.get(s, 0) * mid - current[s]) for s in symbols)
                    - opening_value
                )
                if f > 0:
                    high = mid
                else:
                    low = mid
            capital = (low + high) / 2
            orders = [
                (s, targets.get(s, 0) * capital / opens[s] - account.quantities.get(s, 0))
                for s in symbols
            ]
            for s, q in sorted(orders, key=lambda x: (x[1] > 0, x[0])):
                if abs(q * opens[s]) < 1e-8:
                    continue
                if cast(float, today.at[s, "volume"]) <= 0:
                    raise ValueError(f"Cannot trade {s} on zero-volume session {date}")
                amount = abs(q * opens[s])
                fees = {
                    "commission": amount * config.costs.commission_bps / 10000,
                    "spread": amount * config.costs.spread_bps / 20000,
                    "slippage": amount * config.costs.slippage_bps / 10000,
                }
                fee = sum(fees.values())
                account.fill(s, q, opens[s], fee)
                daily_cost += fee
                notional += amount
                trades.append(
                    {
                        "date": date,
                        "signal_date": signal_date,
                        "symbol": s,
                        "quantity": q,
                        "price": opens[s],
                        "notional": amount,
                        "cost": fee,
                        **fees,
                    }
                )
        value = account.value(closes)
        market_value = value - account.cash
        unrealized = sum(
            q * (closes[s] - account.basis.get(s, 0)) for s, q in account.quantities.items()
        )
        pnl = account.realized + unrealized + account.dividends - account.costs
        if not np.isclose(value - config.portfolio.initial_cash, pnl, atol=1e-6, rtol=1e-10):
            raise ValueError("P&L reconciliation failed")
        returns.append(
            {
                "date": date,
                "equity": value,
                "return": value / previous_value - 1,
                "cash": account.cash,
                "market_value": market_value,
                "exposure": market_value / value,
                "cost": daily_cost,
                "turnover": notional / opening_value,
                "realized_pnl": account.realized,
                "unrealized_pnl": unrealized,
                "dividends": account.dividends,
                "period": labels[date],
            }
        )
        for s in symbols:
            holdings.append(
                {
                    "date": date,
                    "symbol": s,
                    "quantity": account.quantities.get(s, 0),
                    "price": closes[s],
                    "average_cost": account.basis.get(s, 0),
                    "value": account.quantities.get(s, 0) * closes[s],
                }
            )
        previous_value, previous_month = value, month
    return BacktestResult(
        pd.DataFrame(returns),
        pd.DataFrame(holdings),
        pd.DataFrame(
            trades,
            columns=[
                "date",
                "signal_date",
                "symbol",
                "quantity",
                "price",
                "notional",
                "cost",
                "commission",
                "spread",
                "slippage",
            ],
        ),
    )
