from typing import Protocol
from quantlab.data.core import Dataset


class DataProvider(Protocol):
    def download(self, symbols: list[str], start: str, end: str) -> Dataset: ...
