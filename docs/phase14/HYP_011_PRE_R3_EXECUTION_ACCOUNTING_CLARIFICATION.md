# HYP_011 Pre-R3 Execution-Accounting Clarification (ADDITIVE, PRE-RESULT)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_R3_HISTORICAL_DATASET_BUILD_AND_SINGLE_EXECUTION]
[TYPE: ADDITIVE_PRE_RESULT_BOOKKEEPING_CLARIFICATION]
[SEALED_BEFORE_ANY_HISTORICAL_MARKET_DATA_ACCESS]
[R1_SEAL_UNMODIFIED]
[NETWORK_REQUESTS_DURING_PHASE_A = 0]
```

- **Document ID:** `docs/phase14/HYP_011_PRE_R3_EXECUTION_ACCOUNTING_CLARIFICATION.md`
- **Manifest:** `docs/phase14/manifests/HYP_011_PRE_R3_EXECUTION_ACCOUNTING_CLARIFICATION.json`
- **HYPOTHESIS:** `HYP_011` (`R1_PREREGISTERED_SEALED`) | **CORE:** `CORE-001`

## 1. Performance Session Set

- Universe: all eligible NYSE sessions 2016-01-01..2024-12-31 from the canonical
  calendar (early closes INCLUDED; no synthetic sessions; count calendar-derived).
- First performance session: first eligible open on/after 2016-01-01
  (calendar-derived; sanity 2016-01-04, never hard-coded).

## 2. Rebalance Schedule

- Initial allocation at the first performance session open.
- Scheduled rebalances at the first eligible open of each new calendar year
  2017–2024 (8 annual events + initial = 9 allocation events). No 2025 prices,
  no terminal rebalance, no drift/performance-triggered rebalance. Full
  expected date list derived from the calendar BEFORE performance.

## 3. Capital

- `SIMULATED_STARTING_AUM_USD = 100000.00` (normalization only).
- `CAPITAL_AUTHORITY_USD = 0.00`. Paper `NOT_AUTHORIZED`. Live `LOCKED`.
  `NO_REAL_ORDERS = true`.

## 4. Dividend Event Ordering (Per Session)

1. Entitlement from PREVIOUS eligible close holdings → receivable on ex-date.
2. Receivables with payable_date ≤ current session → spendable cash.
3. Scheduled open rebalance (if any) using spendable cash only.
4. EOD valuation at raw close.
- Ex-date BUY not entitled; ex-date SELL retains prior-close entitlement.
- Payable on non-session → spendable on first later session. No double count.

## 5. Equity / Returns / Drawdown

- `TOTAL_EQUITY = spendable_cash + Σ shares×raw_close + outstanding_receivables`.
- First-day return = EOD_1/100000 − 1 (first day NOT dropped); subsequent
  EOD_t/EOD_t−1 − 1. One return per performance session; identical for
  baseline/stress/benchmark.
- MDD curve = [100000.00, EOD_1, …, EOD_N] (initial peak included).
- Sharpe: daily net returns, 252/ddof1/rf0, zero variance fail-closed.

## 6. Whole-Share Solver

- Targets T = 0.80/0.20 × pretrade spendable value (receivables excluded);
  Q = floor(T/raw_open); SELLS first, then BUYS; baseline fills ×1.0002/×0.9998,
  stress ×1.0010/×0.9990; commission 0; canonical date-aware sell-side
  regulatory fees (SEC31 ROUND_CEILING + TAF); CAT recorded zero (no canonical
  authority establishes applicability to these executions).
- Negative-cash guard: iterative one-share BUY decrements minimizing increase
  in ABS(w_ACWI−0.80)+ABS(w_AGG−0.20); exact tie → AGG first; until cash ≥ 0.
- Baseline/stress independent paths (quantities may differ). No leverage,
  no short, no margin, no negative cash, no borrowing, no discretion.

## 7. Benchmarks

- Primary SPY B&H: independent 100000.00, first performance-session open, whole
  shares, 2bps adverse buy, residual cash 0, same dividend/split economics, no
  rebalance/liquidation. G4 is drawdown-only.
- Secondary ACWI B&H (informational, non-binding): same construction on ACWI.

## 8. Upstream Pins (Verified at Seal)

- R1 manifest SHA (canonical): recomputed at seal.
- R2 requalified summary state:
  `R2_PROVIDER_AND_SPONSOR_AUTHORITIES_QUALIFIED_HISTORICAL_BUILD_NOT_EXECUTED`.
- Strategy/provider/partition/gate pins: frozen R1 values (verified pre-data).

## 9. Boundary

Accounting clarification only. Zero market-data access. M2/M3/quarantine/
prospective untouched and locked.
