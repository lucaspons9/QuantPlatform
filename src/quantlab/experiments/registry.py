from pathlib import Path
import json
from typing import Any
import duckdb
import pandas as pd


class ExperimentRegistry:
    def __init__(self, root: str | Path = "experiments"):
        self.root = Path(root)

    def list(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("exp_*/metadata.json")):
            meta = json.loads(path.read_text())
            metric = json.loads((path.parent / "metrics.json").read_text())["net"]
            rows.append(
                {
                    **meta,
                    "sharpe": metric["sharpe"],
                    "cagr": metric["cagr"],
                    "max_drawdown": metric["max_drawdown"],
                }
            )
        if not rows:
            return pd.DataFrame()
        frame = pd.DataFrame(rows)
        # Derived, disposable analytical index; files are the source of truth.
        with duckdb.connect() as connection:
            connection.register("experiments", frame)
            return connection.execute("SELECT * FROM experiments ORDER BY created_at").df()
