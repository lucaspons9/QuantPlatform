from html import escape
import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from quantlab.analytics.metrics import calendar_returns, subperiods
from quantlab.analytics.plots import equity_plot, drawdown_plot, rolling_plot
from quantlab.experiments.runner import Experiment


def report(experiment: Experiment) -> Path:
    exp = experiment
    frame = exp.tables["returns"]
    figures = [equity_plot(exp), drawdown_plot(exp), rolling_plot(exp)]
    for frequency in ("ME", "YE"):
        r = calendar_returns(frame, frequency)
        figures.append(
            go.Figure(go.Bar(x=r.index, y=r.values)).update_layout(
                title=f"{frequency} compounded returns (boundary periods may be partial)"
            )
        )
    for name in ("turnover", "cost", "exposure"):
        figures.append(go.Figure(go.Scatter(x=frame.date, y=frame[name])).update_layout(title=name))
    benchmark = exp.tables["benchmark_returns"]
    figures.append(
        go.Figure(go.Scatter(x=frame.date, y=frame.equity / benchmark.equity - 1)).update_layout(
            title="Relative wealth versus control; not an alpha estimate"
        )
    )
    figures.append(
        go.Figure(go.Scatter(x=frame.date, y=benchmark.exposure, name="Benchmark"))
        .add_scatter(x=frame.date, y=frame.exposure, name="Strategy")
        .update_layout(title="Exposure comparison")
    )
    for fig in figures[:3]:
        for p in exp.config.periods:
            if p.end >= exp.config.start and p.start <= exp.config.end:
                fig.add_vrect(
                    x0=max(p.start, exp.config.start),
                    x1=min(p.end, exp.config.end),
                    opacity=0.08,
                    fillcolor={"train": "blue", "validation": "orange", "test": "red"}[p.name],
                    line_width=0,
                    annotation_text=p.name,
                )
    sections = [
        '<!doctype html><html><head><meta charset="utf-8"><title>QuantLab research report</title></head><body>',
        "<h1>QuantLab research report</h1>",
        f"<p>{escape(exp.path.name)}</p>",
        "<p>Reference infrastructure experiment. No claim of alpha or investability.</p>",
        "<h2>Metrics</h2>",
        pd.DataFrame(exp.metrics).drop(index="undefined", errors="ignore").to_html(),
        "<h2>Assumptions and limitations</h2><pre>"
        + escape(
            json.dumps(
                {
                    "assumptions": exp.metadata["assumptions"],
                    "data": exp.metadata["provider"],
                    "validation": exp.metadata["validation"],
                },
                indent=2,
            )
        )
        + "</pre>",
        "<p>Ratios with zero denominators are null. Rolling gaps indicate insufficient history or zero risk. "
        "Annualization uses "
        + str(exp.config.annualization)
        + " sessions, zero risk-free rate. No statistical significance inference. "
        "Missing observations are fatal; this selects a complete-history panel and can introduce selection bias. "
        "Test access is explicit and recorded; software cannot undo human inspection.</p>",
        "<h2>Research periods</h2>",
        subperiods(frame, exp.config.annualization).to_html(),
    ]
    for i, fig in enumerate(figures):
        sections.append(fig.to_html(full_html=False, include_plotlyjs=True if i == 0 else False))
    sections += ["<h2>Predeclared robustness results (all variants)</h2>"]
    paths = sorted((exp.path / "robustness").glob("results_*.parquet"))
    sections += [pd.read_parquet(p).to_html(index=False) for p in paths] or [
        "<p>No sweeps run.</p>"
    ]
    sections += [
        "<h2>Trades (first 50)</h2>",
        exp.tables["trades"].head(50).to_html(index=False),
        "<h2>Final holdings</h2>",
        exp.tables["holdings"].query("date == date.max()").to_html(index=False),
        "<h2>Configuration</h2><pre>",
        escape(json.dumps(exp.config.model_dump(), indent=2)),
        "</pre><h2>Provenance and undefined-metric reasons</h2><pre>",
        escape(json.dumps({"metadata": exp.metadata, "metrics": exp.metrics}, indent=2)),
        "</pre></body></html>",
    ]
    target = exp.path / "report.html"
    target.write_text("\n".join(sections))
    return target
