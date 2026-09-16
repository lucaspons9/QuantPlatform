from quantlab.experiments.config import Portfolio


def equal_weights(symbols: list[str], portfolio: Portfolio) -> dict[str, float]:
    if not symbols:
        return {}
    weight = min(portfolio.gross_exposure / len(symbols), portfolio.max_weight)
    return {symbol: weight for symbol in sorted(symbols)}
