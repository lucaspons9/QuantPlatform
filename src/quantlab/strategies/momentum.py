from quantlab.strategies.base import History
from quantlab.experiments.config import Parameters, Portfolio
from quantlab.portfolio.construction import equal_weights


class Momentum:
    def __init__(self, parameters: Parameters, portfolio: Portfolio):
        self.parameters, self.portfolio = parameters, portfolio

    def targets(self, history: History) -> dict[str, float]:
        p = self.parameters
        prices = history.total_returns
        if len(prices) <= p.lookback:
            return {}
        scores = prices.iloc[-1 - p.skip] / prices.iloc[-1 - p.lookback] - 1
        # Stable symbol tie-break; never let column/input order alter ranking.
        ranked = sorted(history.symbols, key=lambda s: (-float(scores[s]), s))
        return equal_weights(ranked[: p.top_n], self.portfolio)


class BuyHold:
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio
        self.started = False

    def targets(self, history: History) -> dict[str, float]:
        self.started = True
        return equal_weights(list(history.symbols), self.portfolio)
