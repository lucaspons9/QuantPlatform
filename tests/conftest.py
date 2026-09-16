import pandas as pd
import pytest
from quantlab.data.core import Dataset, sessions
from quantlab.experiments.config import ExperimentConfig


@pytest.fixture
def small_data():
    dates = sessions("2020-01-02", "2020-02-07")
    rows = [
        [d, s, price, price, price, price, 1000.0, 1.0, 0.0]
        for d in dates
        for s, price in [("A", 10.0), ("B", 20.0)]
    ]
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
        {"provider": "test"},
    )


@pytest.fixture
def config():
    return ExperimentConfig.model_validate(
        {
            "dataset": "unused",
            "start": "2020-01-03",
            "end": "2020-02-07",
            "universe": {"symbols": ["A", "B"]},
            "portfolio": {"initial_cash": 1000, "max_weight": 1},
            "parameters": {"lookback": 2, "skip": 0, "top_n": 1},
            "costs": {"commission_bps": 0, "spread_bps": 0, "slippage_bps": 0},
            "periods": [{"name": "train", "start": "2020-01-01", "end": "2020-12-31"}],
        }
    )
