# QuantPlatform / QuantLab V0

A local measuring instrument for daily US-equity research. This is not a strategy search, trading system, or claim of alpha. Negative reference results are acceptable.

## Fresh-clone quick start (Python 3.12)

```bash
git clone https://github.com/lucaspons9/QuantPlatform.git
cd QuantPlatform
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps --no-build-isolation -e .
pytest
ruff check src tests
ruff format --check src tests
mypy src/quantlab
```

A completely offline research demonstration after installation:

```bash
DATASET=$(quantlab data synthetic)
quantlab data validate "$DATASET"
quantlab experiment run configs/momentum_synthetic.yaml --dataset "$DATASET"
quantlab experiment list
# Copy the exp_... ID printed by the run:
quantlab experiment report EXPERIMENT_ID
quantlab experiment reproduce EXPERIMENT_ID
quantlab experiment sweep EXPERIMENT_ID --kind cost
quantlab experiment sweep EXPERIMENT_ID --kind parameter
jupyter lab notebooks/getting_started.ipynb
```

Open `experiments/EXPERIMENT_ID/report.html` directly in a browser. Plotly is embedded; no server or network is needed. Paths in configuration are relative to the working directory; run commands at repository root. CLI `--dataset` overrides the placeholder without source changes. Synthetic prices are fictional and never evidence about markets.

## Historical market data

V0 implements Tiingo EOD through a replaceable `DataProvider` protocol. Obtain your own token and verify your account's historical-data entitlement, limits, and license. No paid subscription is selected or purchased for you. See [official EOD documentation](https://www.tiingo.com/documentation/end-of-day) and [dividend conventions](https://www.tiingo.com/documentation/corporate-actions/dividends).

```bash
export TIINGO_API_TOKEN='YOUR_TOKEN'
DATASET=$(quantlab data download --symbols AAPL MSFT JNJ JPM XOM WMT PG KO \
  --start 2018-01-01 --end 2024-12-31)
quantlab data validate "$DATASET"
quantlab experiment run configs/momentum_reference.yaml --dataset "$DATASET"
```

The adapter retrieves raw OHLCV, split factors and ex-date cash dividends. It does **not** promise historical constituents, permanent identifiers, delisting settlements, publication-time data vintages or complete corporate actions. The example is a manually selected survivor list, not a historical index universe. It is an engineering example, not a recommended research universe. Live credentialed integration was not exercised during implementation; mocked request/response tests cover the adapter. Do not commit keys, downloaded data, or generated experiments.

For an existing canonical CSV, use Python without changing source:

```python
import pandas as pd
from quantlab.data.core import Dataset
snapshot = Dataset.create(pd.read_csv('my_bars.csv'), {
    'provider': 'my-export', 'limitations': ['Document the provenance and limitations here']
}).save('data')
```

Schema: `date,symbol,open,high,low,close,volume,split,dividend`. Prices are raw USD prices; dates are timezone-naive midnight XNYS session labels; split defaults must be explicitly supplied as 1 and dividends as 0 by the source, never inferred. A split factor of 2 means two new shares per old share. Every requested security must have every session over the dataset range. Missing data is fatal; narrow the requested interval only for a documented research reason, never to suppress bad performance. Simultaneous split/dividend events are rejected pending a source-specific entitlement convention.

## Research conventions

* Default signal: total-return index at T−21 divided by T−252 minus one, using session offsets; deterministic symbol tie breaks. Signals computed from the last session of the prior month; first run session also rebalances using its preceding session. At least 253 prior observations are required to produce a momentum selection; otherwise remain in cash.
* Next-session open execution, close valuation. Fractional shares, long-only, no borrowing. Weights are desired **post-cost** weights, solved against the cost budget. Sell before buy. Position caps apply at rebalances; drift between rebalances is allowed. Unallocated capital remains cash at zero interest.
* Full quoted spread defaults to 4 bps, half charged each side, plus 1 bp commission and 2 bps slippage per traded notional. These are illustrative assumptions, not calibrated execution costs. Costs are cash charges at raw open, preserving a separately auditable price and fee ledger.
* Split shares and basis before open; dividends credited on ex-date to overnight holders. Ex-date cash availability approximates payment timing. No dividend double counting through adjusted closes.
* Equal-weight buy-and-hold control on the same universe, costs, cap, starting capital and dates; its exposure can drift. Gross is independently rerun with zero costs. There is no risk-free yield, taxes, liquidity/market impact, or delisting engine.
* Annualization uses 252 sessions, sample volatility, zero risk-free rate; Sortino downside deviation uses all observations. CAGR uses session count, including the first day's return from initial cash. Turnover is absolute buys plus sells divided by pretrade NAV (not half-turnover). Annualization on short samples is unstable. Undefined ratios return JSON null with reasons.
* Research periods must cover every run session exactly once. Test access requires `allow_test: true`; sweeps reject all test overlap even with that switch. Default runs end in validation. Sweeps show every variant and never select a winner.

## Python APIs and extensions

```python
from quantlab.experiments.runner import Experiment, run_experiment
from quantlab.experiments.config import ExperimentConfig
from quantlab.experiments.registry import ExperimentRegistry
from quantlab.analytics.robustness import sweep

runs = ExperimentRegistry().list()
result = Experiment.load('exp_...')
result.reproduce()  # exact table comparison; raises on differences
# Includes full run provenance and retains each variant:
sweep(result, [{'universe': {'symbols': ['AAPL', 'MSFT'],
    'label': 'Predeclared static subset; selection bias'}}])
```

To add a strategy, implement `targets(history) -> dict[str, float]` in a normal Python module. Its constructor accepts `(Parameters, Portfolio)` for CLI custom strategies; set `strategy: your_package.your_module:YourStrategy` in YAML. The engine is unchanged. Direct Python callers may supply any object implementing `Strategy` to `backtest.engine.run`. V0's CLI parameter schema is deliberately the reference schema; richer future strategy configuration may require extending configuration, not the engine. Strategies receive a copied history prefix only and must be deterministic. This is accidental-leakage prevention, not a security sandbox against malicious Python reading disk.

`Experiment.load` verifies persisted artifact hashes; `Dataset.load` verifies canonical data plus provenance hashes. Reproduction requires the original dataset snapshot, source and environment. Preserve `data/<hash>` alongside experiments when moving machines; change the explicit dataset path when relocated. Registry queries use DuckDB over a derived metadata table, with immutable files as the source of truth. The report can be regenerated and robustness appended without changing original result tables.

## Repository map

| Path | Responsibility |
|---|---|
| `src/quantlab/data` | provider protocol, Tiingo, normalization, validation, fingerprints, synthetic fixture |
| `src/quantlab/strategies` | prefix-only strategy interface, momentum and buy-and-hold |
| `src/quantlab/portfolio` | deterministic equal weights and cash residual |
| `src/quantlab/backtest` | timing, fills, actions, cash/basis/P&L reconciliation |
| `src/quantlab/experiments` | strict YAML configuration, atomic persistence, reload, DuckDB registry |
| `src/quantlab/analytics` | metrics, charts, standalone report, predeclared sweeps |
| `configs`, `notebooks` | editable experiments and thin research introduction |
| `tests` | manual accounting examples, adversarial timing, validation and integration |
| `docs` | acceptance evidence |

Read [ARCHITECTURE.md](ARCHITECTURE.md), [RESEARCH_READINESS.md](RESEARCH_READINESS.md), and [DECISIONS_REQUIRED.md](DECISIONS_REQUIRED.md) before interpreting a result.
