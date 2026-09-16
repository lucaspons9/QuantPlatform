from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import importlib.metadata
import json
import platform
from pathlib import Path
import shutil
import subprocess
from typing import Any
import uuid
import pandas as pd
import yaml
from quantlab.analytics.metrics import metrics
from quantlab.backtest.engine import run
from quantlab.data.core import Dataset
from quantlab.experiments.config import ExperimentConfig, Costs
from quantlab.strategies.momentum import Momentum, BuyHold

TABLES = ["returns", "holdings", "trades", "gross_returns", "benchmark_returns", "costs"]


@dataclass
class Experiment:
    path: Path
    config: ExperimentConfig
    metadata: dict[str, Any]
    metrics: dict[str, Any]
    tables: dict[str, pd.DataFrame]

    @classmethod
    def load(cls, experiment_id: str, root: str | Path = "experiments") -> "Experiment":
        if Path(experiment_id).name != experiment_id or not experiment_id.startswith("exp_"):
            raise ValueError("Invalid experiment ID")
        path = Path(root) / experiment_id
        hashes = json.loads((path / "manifest.json").read_text())
        for name, digest in hashes.items():
            if sha256((path / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Artifact integrity mismatch: {name}")
        return cls(
            path,
            ExperimentConfig.load(path / "config.yaml"),
            json.loads((path / "metadata.json").read_text()),
            json.loads((path / "metrics.json").read_text()),
            {name: pd.read_parquet(path / f"{name}.parquet") for name in TABLES},
        )

    def reproduce(self, root: str | Path = "experiments") -> "Experiment":
        other = run_experiment(self.config, root, parent_id=self.path.name, purpose="reproduction")
        for name in TABLES:
            pd.testing.assert_frame_equal(self.tables[name], other.tables[name], check_exact=True)
        return other


def strategy_for(config: ExperimentConfig) -> Any:
    if config.strategy == "momentum":
        return Momentum(config.parameters, config.portfolio)
    if config.strategy == "buy_hold":
        return BuyHold(config.portfolio)
    if ":" not in config.strategy:
        raise ValueError("Strategy must be momentum, buy_hold, or module:Class")
    module, name = config.strategy.split(":", 1)
    return getattr(importlib.import_module(module), name)(config.parameters, config.portfolio)


def git_info() -> dict[str, Any]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
        return {"commit": commit, "dirty": dirty}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"commit": None, "dirty": None}


def run_experiment(
    config: ExperimentConfig,
    root: str | Path = "experiments",
    parent_id: str | None = None,
    purpose: str = "reference",
) -> Experiment:
    dataset = Dataset.load(config.dataset)
    net = run(dataset, config, strategy_for(config), config.strategy == "buy_hold")
    gross_config = config.model_copy(
        update={"costs": Costs(commission_bps=0, spread_bps=0, slippage_bps=0)}
    )
    gross = run(dataset, gross_config, strategy_for(gross_config), config.strategy == "buy_hold")
    benchmark = run(dataset, config, BuyHold(config.portfolio), True)
    result_metrics = {
        name: metrics(result.returns["return"], config.annualization)
        for name, result in [("net", net), ("gross", gross), ("benchmark", benchmark)]
    }
    result_metrics["net"]["transaction_costs"] = float(net.returns.cost.sum())
    result_metrics["net"]["turnover"] = float(net.returns.turnover.sum())
    eid = "exp_" + uuid.uuid4().hex[:16]
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    temp = root / ("." + eid)
    final = root / eid
    temp.mkdir()
    # Persist a concrete absolute snapshot location; relocation is an explicit config change.
    config = config.model_copy(update={"dataset": str(Path(config.dataset).resolve())})
    source_root = Path(__file__).parents[1]
    source_hash = sha256(
        b"".join(
            p.relative_to(source_root).as_posix().encode() + p.read_bytes()
            for p in sorted(source_root.rglob("*.py"))
        )
    ).hexdigest()
    metadata = {
        "id": eid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "strategy": config.strategy,
        "strategy_version": "v0",
        "start": config.start,
        "end": config.end,
        "universe": config.universe.model_dump(),
        "parameters": config.parameters.model_dump(),
        "costs": config.costs.model_dump(),
        "parent_id": parent_id,
        "purpose": purpose,
        "dataset_fingerprint": dataset.fingerprint,
        "provider": dataset.metadata,
        "validation": dataset.quality,
        "git": git_info(),
        "package_source_sha256": source_hash,
        "python": platform.python_version(),
        "environment": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
        "assumptions": [
            "Signals use previous session close; fills next open; close marks",
            "Fractional shares, no leverage, zero cash yield, no taxes or liquidity impact",
            "Spread is full quoted spread; half charged each side; slippage and commission separately charged",
            "Dividend cash credited ex-date (payment-date approximation)",
            "Gross is an independent zero-cost simulation; not net plus accumulated fees",
            "Static universe; no claim of historically unbiased membership",
            "Benchmark uses same universe, initial cap/exposure and costs; weights subsequently drift",
        ],
    }
    tables = {
        "returns": net.returns,
        "holdings": net.holdings,
        "trades": net.trades,
        "gross_returns": gross.returns,
        "benchmark_returns": benchmark.returns,
        "costs": net.trades[["date", "symbol", "commission", "spread", "slippage", "cost"]],
    }
    try:
        (temp / "config.yaml").write_text(yaml.safe_dump(config.model_dump(), sort_keys=False))
        (temp / "metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False))
        (temp / "metrics.json").write_text(json.dumps(result_metrics, indent=2, allow_nan=False))
        for name, table in tables.items():
            table.to_parquet(temp / f"{name}.parquet", index=False)
        exp = Experiment(temp, config, metadata, result_metrics, tables)
        from quantlab.analytics.reporting import report

        report(exp)
        hashes = {
            p.name: sha256(p.read_bytes()).hexdigest()
            for p in temp.iterdir()
            if p.is_file() and p.name != "report.html"
        }
        (temp / "manifest.json").write_text(json.dumps(hashes, indent=2))
        temp.rename(final)
    except Exception:
        shutil.rmtree(temp)
        raise
    return Experiment.load(eid, root)
