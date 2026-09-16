import plotly.graph_objects as go
from quantlab.analytics.metrics import drawdown, rolling
from quantlab.experiments.runner import Experiment


def equity_plot(experiment: Experiment) -> go.Figure:
    figure = go.Figure()
    for name, key in [
        ("Net", "returns"),
        ("Gross", "gross_returns"),
        ("Benchmark", "benchmark_returns"),
    ]:
        frame = experiment.tables[key]
        figure.add_scatter(
            x=frame.date, y=frame.equity / experiment.config.portfolio.initial_cash, name=name
        )
    figure.update_layout(
        title="Wealth / initial capital (includes first-session costs)",
        yaxis_title="Wealth multiple",
    )
    return figure


def drawdown_plot(experiment: Experiment) -> go.Figure:
    figure = go.Figure()
    for name, key in [("Strategy", "returns"), ("Benchmark", "benchmark_returns")]:
        frame = experiment.tables[key]
        figure.add_scatter(x=frame.date, y=drawdown(frame["return"]), name=name)
    figure.update_layout(title="Drawdown, including initial capital as a high-water mark")
    return figure


def rolling_plot(experiment: Experiment) -> go.Figure:
    frame = experiment.tables["returns"]
    values = rolling(frame["return"], annualization=experiment.config.annualization)
    figure = go.Figure()
    for name in values:
        figure.add_scatter(x=frame.date, y=values[name], name=name)
    figure.update_layout(
        title="63-session rolling metrics; blank until sufficient history / nonzero risk"
    )
    return figure
