import argparse
import json
import sys
from quantlab.data.core import Dataset
from quantlab.data.synthetic import synthetic
from quantlab.data.providers.tiingo import TiingoProvider
from quantlab.experiments.config import ExperimentConfig
from quantlab.experiments.runner import Experiment, run_experiment
from quantlab.experiments.registry import ExperimentRegistry
from quantlab.analytics.reporting import report
from quantlab.analytics.robustness import cost_sensitivity, parameter_sensitivity


def main() -> None:
    parser = argparse.ArgumentParser(description="Local research laboratory; no live trading")
    commands = parser.add_subparsers(dest="command", required=True)
    data = commands.add_parser("data").add_subparsers(dest="action", required=True)
    for operation in ("synthetic", "download"):
        p = data.add_parser(operation)
        p.add_argument("--start", default="2018-01-01")
        p.add_argument("--end", default="2024-12-31")
        p.add_argument("--root", default="data")
        if operation == "download":
            p.add_argument("--symbols", nargs="+", required=True)
    p = data.add_parser("validate")
    p.add_argument("dataset")
    experiment = commands.add_parser("experiment").add_subparsers(dest="action", required=True)
    p = experiment.add_parser("run")
    p.add_argument("config")
    p.add_argument("--dataset", help="Override snapshot path without editing source")
    p.add_argument("--root", default="experiments")
    for operation in ("list", "report", "reproduce", "sweep"):
        p = experiment.add_parser(operation)
        p.add_argument("--root", default="experiments")
        if operation != "list":
            p.add_argument("id")
        if operation == "sweep":
            p.add_argument("--kind", choices=["cost", "parameter"], required=True)
    args = parser.parse_args()
    try:
        if args.command == "data":
            if args.action == "validate":
                print(json.dumps(Dataset.load(args.dataset).quality, indent=2))
            else:
                dataset = (
                    synthetic(args.start, args.end)
                    if args.action == "synthetic"
                    else TiingoProvider().download(args.symbols, args.start, args.end)
                )
                print(dataset.save(args.root).resolve())
        elif args.action == "run":
            config = ExperimentConfig.load(args.config)
            if args.dataset:
                config = config.model_copy(update={"dataset": args.dataset})
            print(run_experiment(config, args.root).path)
        elif args.action == "list":
            print(ExperimentRegistry(args.root).list().to_string(index=False))
        else:
            exp = Experiment.load(args.id, args.root)
            if args.action == "report":
                print(report(exp))
            elif args.action == "reproduce":
                print(exp.reproduce(args.root).path)
            else:
                print(
                    (cost_sensitivity if args.kind == "cost" else parameter_sensitivity)(
                        exp
                    ).to_string(index=False)
                )
    except (ValueError, FileNotFoundError) as exc:
        print(f"quantlab: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
