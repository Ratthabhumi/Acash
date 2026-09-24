# HYP_009 Pre-M2 Accounting / Continuity Clarification (SEALED PRE-M2-READ)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_PRE_M2_RECONCILIATION_AND_LOCKED_M2_EXECUTION]
[TYPE: ADDITIVE_PRE_M2_CLARIFICATION]
[SEALED_BEFORE_ANY_M2_MARKET_DATA_ACCESS]
```

- **Manifest:** `docs/phase14/manifests/HYP_009_PRE_M2_ACCOUNTING_CLARIFICATION.json`
- **M2 partition:** 2021-01-01 .. 2024-12-31
- **M2 classification:** `LOCKED_HISTORICAL_OOS_NOT_PRISTINE_RESEARCHER_BLIND`
- **M2 evaluation:** INDEPENDENT normalized partition (not a continuation of M1 P&L)

## 1. Capital Continuity

- `SIMULATED_M2_STARTING_AUM_USD = 100000.00` (fresh simulation cash).
- M1 ending AUM (~145227.31) is NOT carried into M2.
- Real capital authority remains `0.00`. `NO_REAL_ORDERS = true`.

## 2. Signal Continuity (Causal, No Refetch of M1)

- The frozen 10-month SMA requires pre-M2 month-end history.
- Warmup authority: the already-sealed corrected M1 dataset + signal ledger
  through 2020-12-31. M1 market data serves ONLY as signal warmup/history.
- Total-return index continues causally: sealed M1 TR levels are preserved
  (verified equal before M2 evaluation); M2 observations extend the same index.
  No restart from an arbitrary M2-only base. No future leakage.

## 3. December-2020 Frozen Signal (Initial M2 State Authority)

- Sealed Dec-2020 decision (2020-12-31): level `2.051430715393109079173373811`,
  SMA10 `1.760537145277627779062534321`, state **LONG** (no transition).
- For M2 this exact frozen signal is the initial state authority.
- Execution at the first eligible M2 regular session OPEN (derived from the
  canonical calendar at runtime: 2021-01-04; 2021-01-01 was a holiday).
- Do NOT regenerate a different December-2020 signal.

## 4. M2 Benchmark (Independent)

- Starts simulated 100000.00 at the first eligible M2 session open.
- Whole shares, baseline 2 bps adverse initial buy, residual cash 0 return.
- Same corporate-action economics. No rebalance. No forced terminal liquidation.

## 5. M2 Terminal

- Terminal valuation: final eligible NYSE M2 session in 2024 (derived at runtime).
- If the final December-2024 signal's next execution lies in 2025: mark
  `PENDING_NEXT_PARTITION_EXECUTION_NOT_EXECUTED`. Do NOT fetch 2025 data.
