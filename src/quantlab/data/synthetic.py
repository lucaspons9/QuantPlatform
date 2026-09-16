"""Deterministic fictional data; never represented as downloaded market history."""

import numpy as np
import pandas as pd
from quantlab.data.core import Dataset, sessions


def synthetic(start: str = "2018-01-01", end: str = "2024-12-31") -> Dataset:
    dates = sessions(start, end)
    rows = []
    for symbol, slope in [("UP", 0.0007), ("DOWN", -0.0004), ("FLAT", 0), ("CYCLE", 0.0001)]:
        for i, date in enumerate(dates):
            price = 100 * np.exp(slope * i + (0.08 * np.sin(i / 45) if symbol == "CYCLE" else 0))
            split = 2.0 if symbol == "UP" and i == 300 else 1.0
            if symbol == "UP" and i >= 300:
                price /= 2
            rows.append([date, symbol, price, price * 1.01, price * 0.99, price, 1e6, split, 0.0])
    return Dataset.create(
        pd.DataFrame(
            rows,
            columns=[
                "date",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "split",
                "dividend",
            ],
        ),
        {
            "provider": "synthetic-v1",
            "limitations": ["Fictional deterministic prices; no investment evidence"],
        },
    )
