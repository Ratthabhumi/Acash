# D6 Preregistered Contract: USD 1,000 After-Cost Baseline

**Date:** 2026-10-23
**Status:** `DRAFT_PREREGISTRATION_NOT_RATIFIED`
**Data status:** `D5_REAL_DATA_NOT_ADMITTED`
**Execution status:** `NOT_RUN`
**Capital authority:** USD 0.00; `NO_REAL_ORDERS=true`

This contract defines the question and the rules before any empirical run. It does not
authorize data acquisition, a backtest, paper trading, live trading or capital.

## 1. Question

For a hypothetical USD 1,000 investor over the admitted matched period, which simple
allocation answers the investment question after realistic costs:

1. cash / no trade;
2. broad US equity;
3. equity + bond;
4. low-turnover diversified ETF mix?

The purpose is decision support, including the answer “cash / no trade”. It is not a
search for a high-Sharpe strategy and not a claim of alpha.

## 2. Data Contract

- Only a D5-admitted bundle may feed the primary run.
- A `RETROSPECTIVE_QUALITY_QUALIFIED` run must be labelled retrospective and must not be
  described as PIT.
- A `PIT_EVIDENCE_QUALIFIED` run may claim PIT for the admitted fields only.
- The period, symbols, adjustments and corporate actions must match the D5 manifest
  exactly. No post-hoc window changes.
- GLD is treated as `NO_CASH_DISTRIBUTION_ENTITLEMENT`; no synthetic GLD dividend.

## 3. Instruments and Portfolios

| Portfolio | Definition | Rebalancing |
| :--- | :--- | :--- |
| Cash / no trade | USD cash at 0% nominal | None |
| T-bill reference | 100% BIL total return | None |
| US equity | 100% VOO total return | None |
| Equity + bond | 60% VOO / 40% BND | Annual, first session |
| Diversified low-turnover | 50% VOO / 30% BND / 10% GLD / 10% BIL | Annual, first session |

Annual rebalancing executes at the first admitted session of each calendar year, using
only information available at that session. No intra-year tactical changes, no
look-ahead, no regime switching.

## 4. Accounting

- Initial NAV: USD 1,000.00.
- Base currency: USD. THB reporting is a separate sensitivity, not the primary result.
- Use total return: price return plus cash distributions, with splits applied.
- Cash distributions are credited on payable date; no double counting.
- Fractional shares are allowed for accounting only; minimum lot and whole-share
  constraints are a separate sensitivity.
- No leverage, shorting, derivatives or margin.
- Terminal NAV is marked at the final admitted close.

## 5. Costs and Frictions

Primary case must disclose and, where the input is known, charge:

1. commissions using a named published tariff (for example IBKR Pro Tiered/Fixed), with
   the tariff date recorded;
2. bid/ask spread and slippage assumptions, with sensitivity;
3. ETF expense ratios;
4. FX conversion and USD/THB sensitivity;
5. withholding/tax scenarios, explicitly labelled as scenarios;
6. regulatory/Exchange fees where applicable;
7. cash yield and funding assumptions.

Unknown costs must be shown as sensitivity ranges, not silently set to zero. A zero-cost
run may be shown only as a labelled upper bound.

## 6. Metrics

Report at minimum:

- terminal NAV and total return;
- CAGR;
- annualized volatility;
- Sharpe ratio, annualized with `sqrt(252)`;
- Sortino ratio;
- maximum drawdown and recovery;
- Calmar ratio;
- annual turnover and cost drag;
- number of trades and rebalances;
- per-year returns and worst year;
- confidence intervals from a deterministic block bootstrap with a fixed seed and stated
  block length.

Do not report DSR/PBO as if the four baselines were an unconstrained strategy search.
If multiple variants are compared, the trial count must be sealed and the dependence
between shared-data variants must be disclosed.

## 7. Decision Rules

The primary comparison is after-cost terminal NAV and drawdown over the same admitted
period. The contract is falsified for a portfolio if it fails to beat the stated
comparator after costs, or if its drawdown exceeds the stated risk limit. A failure is a
valid result and must be reported.

No rule may be changed after seeing results. Any change creates a new preregistration
with a new identifier and lineage.

## 8. Required Outputs

- D5 manifest SHA and evidence level;
- exact run configuration and code commit;
- cost/tariff assumptions and sensitivity table;
- per-portfolio ledger and reconciliation;
- metrics table with confidence intervals;
- limitations: PIT status, corporate-action authority, survivorship, taxes, FX and
  execution assumptions;
- explicit statement that the result is not live-capital authorization.

## 9. Gates

1. D5 admission.
2. Separate empirical-run authorization.
3. Frozen code/config digest.
4. Post-run independent verification.
5. Owner decision, including the option of no deployment.

Until those gates pass, the correct state is `NOT_RUN`, Lane B remains `UNISSUED`, and
no real order may be placed.
