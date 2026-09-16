"""Predeclared comparisons, no ranking or winner selection. Test periods are forbidden."""

from pathlib import Path
import json
from typing import Any
import pandas as pd
from quantlab.experiments.config import ExperimentConfig
from quantlab.experiments.runner import Experiment, run_experiment


def sweep(
    experiment: Experiment, variants: list[dict[str, Any]], root: str | Path | None = None
) -> pd.DataFrame:
    if not variants or len(variants) > 20:
        raise ValueError("V0 sweep limited to 20 predeclared variants")
    config = experiment.config
    # Reject rather than silently shorten a supplied research interval.
    for p in config.periods:
        if p.name == "test" and p.start <= config.end and p.end >= config.start:
            raise ValueError("Sweeps cannot access test periods, even with allow_test=true")
    destination = experiment.path / "robustness"
    destination.mkdir(exist_ok=True)
    batch = len(list(destination.glob("plan_*.json"))) + 1
    (destination / f"plan_{batch}.json").write_text(json.dumps(variants, indent=2))
    rows = []
    for variant in variants:
        raw = config.model_dump()
        for key, value in variant.items():
            if key not in ("parameters", "costs", "universe", "start", "end"):
                raise ValueError(f"Unsupported sweep dimension {key}")
            raw[key] = {**raw[key], **value} if isinstance(value, dict) else value
        variant_config = ExperimentConfig.model_validate(raw)
        for p in variant_config.periods:
            if (
                p.name == "test"
                and pd.Timestamp(p.start) <= pd.Timestamp(variant_config.end)
                and pd.Timestamp(p.end) >= pd.Timestamp(variant_config.start)
            ):
                raise ValueError("Sweeps cannot access test periods through date variants")
        child = run_experiment(
            variant_config,
            root or experiment.path.parent,
            parent_id=experiment.path.name,
            purpose=f"robustness_{batch}",
        )
        rows.append(
            {
                "experiment_id": child.path.name,
                "variant": json.dumps(variant, sort_keys=True),
                **child.metrics["net"],
            }
        )
    table = pd.DataFrame(rows)
    table.drop(columns=["undefined"], errors="ignore").to_parquet(
        destination / f"results_{batch}.parquet", index=False
    )
    from quantlab.analytics.reporting import report

    report(experiment)
    return table


def cost_sensitivity(
    experiment: Experiment, bps: tuple[float, ...] = (0, 5, 10, 25, 50)
) -> pd.DataFrame:
    return sweep(
        experiment,
        [{"costs": {"commission_bps": b, "spread_bps": 0, "slippage_bps": 0}} for b in bps],
    )


def parameter_sensitivity(
    experiment: Experiment, lookbacks: tuple[int, ...] = (126, 189, 252)
) -> pd.DataFrame:
    return sweep(experiment, [{"parameters": {"lookback": n}} for n in lookbacks])
