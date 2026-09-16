from dataclasses import dataclass
from typing import Protocol
import pandas as pd


@dataclass(frozen=True)
class History:
    """Owns a copied prefix only. No reference to the engine or future dataset."""

    asof: pd.Timestamp
    total_returns: pd.DataFrame
    symbols: tuple[str, ...]


class Strategy(Protocol):
    def targets(self, history: History) -> dict[str, float]: ...
