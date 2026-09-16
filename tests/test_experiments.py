import json
import pandas as pd
import pytest
from quantlab.experiments.runner import run_experiment, Experiment
from quantlab.experiments.registry import ExperimentRegistry
from quantlab.experiments.config import Period
from quantlab.analytics.robustness import sweep


def test_roundtrip_reproduction_and_registry(small_data, config, tmp_path):
    config.dataset = str(small_data.save(tmp_path / "data"))
    config.strategy = "buy_hold"
    result = run_experiment(config, tmp_path / "experiments")
    again = Experiment.load(result.path.name, tmp_path / "experiments")
    pd.testing.assert_frame_equal(result.tables["returns"], again.tables["returns"])
    reproduced = again.reproduce(tmp_path / "experiments")
    assert reproduced.metadata["parent_id"] == result.path.name
    assert len(ExperimentRegistry(tmp_path / "experiments").list()) == 2
    assert "plotly.js" in (result.path / "report.html").read_text()
    assert (
        json.loads((result.path / "metadata.json").read_text())["dataset_fingerprint"]
        == small_data.fingerprint
    )
    (result.path / "metrics.json").write_text("{}")
    with pytest.raises(ValueError, match="integrity"):
        Experiment.load(result.path.name, tmp_path / "experiments")


def test_holdout_gates(small_data, config, tmp_path):
    config.dataset = str(small_data.save(tmp_path / "data"))
    config.periods = [Period(name="test", start="2020-01-01", end="2020-12-31")]
    with pytest.raises(ValueError, match="Untouched test"):
        run_experiment(config, tmp_path / "experiments")
    config.allow_test = True
    result = run_experiment(config, tmp_path / "experiments")
    with pytest.raises(ValueError, match="cannot access test"):
        sweep(result, [{"parameters": {"lookback": 3}}])


def test_sweep_all_variants_persist(small_data, config, tmp_path):
    config.dataset = str(small_data.save(tmp_path / "data"))
    result = run_experiment(config, tmp_path / "experiments")
    table = sweep(result, [{"parameters": {"lookback": 3}}, {"parameters": {"lookback": 4}}])
    assert len(table) == 2
    assert len(ExperimentRegistry(tmp_path / "experiments").list()) == 3


def test_date_variant_cannot_bypass_holdout(small_data, config, tmp_path):
    config.dataset = str(small_data.save(tmp_path / "data"))
    config.end = "2020-01-31"
    config.allow_test = True
    config.periods = [
        Period(name="train", start="2020-01-01", end="2020-01-31"),
        Period(name="test", start="2020-02-01", end="2020-02-07"),
    ]
    result = run_experiment(config, tmp_path / "experiments")
    with pytest.raises(ValueError, match="cannot access test"):
        sweep(result, [{"end": "2020-02-07"}])
