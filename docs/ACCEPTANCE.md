# V0 acceptance evidence

Implementation acceptance uses fictional deterministic data only. No market profitability, alpha, or statistical significance is asserted.

## Executed checks

* `pytest -q`: **36 passed**. Manual cash/basis/purchase/sale/close examples; post-cost fully invested sizing; all three fee components; sell-before-buy rotation; engine-level split/dividend neutrality and P&L reconciliation; nonfinite fill rejection.
* Data checks cover duplicates, missing observations and identifiers, OHLC inconsistencies, negative volume, invalid split factors, unsupported simultaneous actions, timezone/intraday labels, holiday bounds, stale warnings, causal total-return transformation and fingerprint tampering.
* Timing checks verify previous-close signal versus next-open execution, known momentum offsets and skip, changed future prices, copied-prefix isolation, and unknown universe/invalid target rejection. Dynamic historical membership is unsupported rather than claimed tested.
* Metric checks cover known compounded return/CAGR/volatility/Sortino/drawdown, initial-capital drawdown, undefined ratios, rolling offsets and monthly compounding.
* Integration checks cover atomic completed-run artifacts, integrity hashes, reload, exact table reproduction, DuckDB registry, all sweep variants retained, explicit holdout access, and date-variant holdout bypass rejection.
* Provider tests mock raw response field mapping, credential handling, and HTTP denial. **No credentialed Tiingo request was made.**
* Ruff lint and formatting passed. Mypy passed on all 25 package source files. `pip check` found no broken requirements.
* All **12 notebook code cells** executed in-process through IPython, including five cost variants, three lookbacks, subperiod metrics, save/load, and exact reproduction. Notebook structure validated with nbformat.
* Full Jupyter kernel execution was attempted, but this execution environment disallowed kernel socket/interface initialization (`Operation not permitted`). This is a disclosed verification limitation; CI includes ordinary Jupyter notebook execution on Ubuntu.
* CLI synthetic generation, validation, reference run, report generation, and reproduction succeeded. Dataset fingerprint: `cdb6ffb6620608043ba3e5cf65dfe30a305a132195b03dad4b8d331ba50f7b1b`. The fixture has 7,044 bars. The reference interval has 987 sessions and 101 fills. Cash + holdings reconciliation error was 0.0 in the inspected run.
* Standalone report generated with embedded Plotly (about 5.4 MB), metrics, period shading, exposure comparison, trades, provenance, and assumptions. Plot objects generated successfully; browser visual interaction was not independently exercised here.

Generated snapshots, experiment artifacts, notebook outputs, credentials and environments are excluded from Git. The full workflow regenerates them. Source, lock file, notebook and tests are committed.

## Clean-clone gate

A separate local clone with a new virtual environment installed all packages from `requirements-lock.txt`, installed QuantLab without dependency resolution or isolated build changes, passed `pip check`, all **36 tests**, Ruff lint/format checks and Mypy. The documented CLI then regenerated and validated the synthetic dataset and completed the reference experiment with its standalone report. No source edits were made in that clone.

## Conservative limits

Complete-panel static-universe research only; no delisting settlement, historical constituents, fundamental filters, complex action engine, liquidity model or live trading. Fixed-bps fees and ex-date dividend cash are approximations. See RESEARCH_READINESS.md and DECISIONS_REQUIRED.md. None of these limits were concealed by selecting profitable outputs.
