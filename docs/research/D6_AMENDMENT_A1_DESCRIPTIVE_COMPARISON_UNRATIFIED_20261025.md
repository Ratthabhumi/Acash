# D6 Amendment A1 — Descriptive After-Cost Comparison (UNRATIFIED)

- Status: `PROPOSED_UNRATIFIED`. Amends `docs/research/D6_PREREGISTERED_CONTRACT_20261023.md`
  only if the owner ratifies it. Until then the original contract text stands unchanged.
- Prepared by the engineering agent (V27); no human signature is implied.

## Problem

Section 7 of the D6 contract refers to a "stated risk limit" but never states a number.
A decision rule with an undefined threshold cannot be applied without inventing one after
seeing data, which would be a post-hoc choice.

## Proposed text

1. The initial D6 study is a **descriptive after-cost risk/return comparison** of the five
   registered USD 1,000 comparators (Cash; BIL 100; VOO 100; VOO/BND 60/40;
   VOO/BND/GLD/BIL 50/30/10/10). It reports the section 6 metrics side by side and the
   after-cost terminal-NAV / maximum-drawdown frontier. It does not declare a winner
   against a risk threshold.
2. No numeric risk threshold is set by this amendment. Any hard threshold (for example a
   maximum drawdown limit) requires a **separate prospective owner decision**, recorded
   before any admitted empirical D6 run.
3. All other D6 sections are unchanged.

## Engineering conventions made explicit (no contract change)

| Topic | Convention in `src/acash/research/d6/accounting.py` |
|---|---|
| Price basis | Raw prices plus explicit distributions and splits; adjusted series rejected (`D6_ADJUSTED_PRICES_REJECTED`) to prevent double counting |
| Expense ratio | Embedded in observed ETF prices; never deducted again |
| Execution | Superseded in V28 by proposed A2 (`D6_AMENDMENT_A2_CAUSAL_EXECUTION_TIMING_UNRATIFIED_20261025.md`): prior-close decision, next-open execution is primary; same-open sizing is a labelled sensitivity |
| Distributions | Entitlement on ex-date into a receivable; cash on payable date; receivables are not spendable; unpaid at end reported as `terminal_receivable` |
| GLD | Any cash distribution input fails closed (`D6_NO_CASH_DISTRIBUTION_ENTITLEMENT`) |
| Withholding | Scenario parameter only; never a universal default |
| FX (USD/THB) | Not modelled in the engine; THB reporting stays a separate sensitivity |
| Labels | Outputs carry `SYNTHETIC_VERIFICATION`; no historical ETF run exists |
