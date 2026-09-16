from dataclasses import dataclass, field
import math


@dataclass
class Account:
    cash: float
    quantities: dict[str, float] = field(default_factory=dict)
    basis: dict[str, float] = field(default_factory=dict)
    realized: float = 0.0
    dividends: float = 0.0
    costs: float = 0.0

    def value(self, prices: dict[str, float]) -> float:
        result = self.cash + sum(q * prices[s] for s, q in self.quantities.items())
        if not math.isfinite(result) or result <= 0 or self.cash < -1e-7:
            raise ValueError("Invalid portfolio value or negative cash")
        return result

    def action(self, symbol: str, split: float, dividend: float) -> None:
        quantity = self.quantities.get(symbol, 0.0)
        if quantity:
            self.quantities[symbol] = quantity * split
            self.basis[symbol] /= split
            income = quantity * split * dividend
            self.cash += income
            self.dividends += income

    def fill(self, symbol: str, quantity: float, price: float, fee: float) -> None:
        if not all(math.isfinite(x) for x in (quantity, price, fee)):
            raise ValueError("Nonfinite fill")
        old = self.quantities.get(symbol, 0.0)
        new = old + quantity
        if new < -1e-9 or price <= 0 or fee < 0:
            raise ValueError("Invalid fill or short position")
        cash = self.cash - quantity * price - fee
        if cash < -1e-7:
            raise ValueError("Insufficient cash")
        if quantity > 0:
            self.basis[symbol] = (old * self.basis.get(symbol, 0) + quantity * price) / new
        else:
            self.realized += -quantity * (price - self.basis.get(symbol, 0))
        self.quantities[symbol] = max(0, new)
        self.cash = max(0, cash)
        self.costs += fee
