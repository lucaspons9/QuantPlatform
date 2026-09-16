# Research readiness

## Trust boundary

V0 is suitable for formulating hypotheses, inspecting deterministic daily experiments, comparing explicit assumptions, and identifying fragile results. It is not evidence that any strategy is investable. Synthetic test outcomes establish engineering properties only.

Trust claims are limited to the tests actually executed in `docs/ACCEPTANCE.md`. Deterministic accounting tests check purchases, sales, average cost, cash, split neutrality, dividend economics, closing positions, fees and exact known NAV. Adversarial timing tests change future prices, verify prefix copying and next-open fills, and check momentum endpoints and skipped observations. Persistence verifies hashes and exact result-table reproduction. Performance metrics use explicit definitions and include initial losses in drawdown.

## Approximate simulation

Raw-open fills assume unlimited fractional liquidity, no capacity or market impact, no halts, no order rejection except zero-volume sessions, no auction uncertainty, no taxes, no borrow or leverage. Next-open target-weight sizing is idealized; it cannot be guaranteed by an order submitted at the previous close. Costs are configurable fixed bps charged against traded notional; the default is not calibrated. Spread assumptions are full quoted spreads; half is charged per side. Gross and net portfolios drift differently because costs affect sizing.

Dividends become spendable on ex-date rather than payable date. Splits are supported but complex simultaneous distributions fail. Spin-offs, mergers, symbol reuse, fractional cash-in-lieu, rights issues and delisting proceeds are not modeled. A complete panel is required. Incomplete histories fail instead of inventing prices or liquidating at an arbitrary mark. This can make the platform unsuitable for an unbiased all-stock historical universe until event-aware missingness and delisting support are added.

## Data guarantees not supplied

Tiingo EOD provides raw/adjusted bars and action fields, but this adapter supplies no historically known constituent sets, point-in-time fundamentals, permanent security identity mapping or delisting settlements. Current corrected historical data are not archived historical knowledge vintages. Corporate-action completeness is not independently verified. Warnings flag stale series and large unexplained jumps; they do not certify correctness. The example stock list contains recognizable surviving securities selected for workflow demonstration, not performance.

Credentialed Tiingo integration was not tested without a user token. Provider account availability, licenses and quotas must be confirmed by the researcher. No real history or market performance was fabricated. Offline synthetic and mocked response tests cannot establish provider data quality.

## Biases and safeguards

* Survivorship and selection bias: static lists and complete-panel restrictions may exclude failures. Never describe the example as historical index membership.
* Look-ahead: prefix-only strategy input and next-open timing prevent ordinary dataframe leakage. They do not protect against malicious code, revised provider history, or wrongly timestamped source events.
* Multiple testing and overfitting: every sweep child is saved with its parent, all variants shown, and no winner selected. Counts reveal local attempts but cannot reveal research outside this registry. Maximum observed Sharpe is a selected statistic, not an unbiased expectation.
* Holdout reuse: explicit permission is recorded in configuration; sweeps refuse test overlap. Software cannot prevent humans from repeatedly inspecting held-out results or manually relabeling dates. Treat a viewed test set as consumed for that research cycle.
* Costs and exposure: report both, compare control exposure, and rerun sensitivity. Outperforming a differently exposed benchmark is not proof of alpha.

## Before investable interpretation

Choose a defensible point-in-time universe and stable identifiers; add lifecycle-aware listings/delistings, action entitlement/payment timing, and independent corporate-action verification. Archive knowledge vintages where relevant. Validate vendor data against an independent source. Calibrate execution assumptions to liquidity and intended capital, define feasible order timing, include taxes if applicable, and independently audit accounting on real actions. Predeclare hypotheses, evaluation periods, cost budgets and acceptable risks. Use appropriate uncertainty and multiple-testing analysis; this platform deliberately does not claim significance. Human judgment is required on economic rationale and capital allocation.
