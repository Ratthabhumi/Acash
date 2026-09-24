# HYP_009 R2 M2 Dividend-Corrected Execution Report (SEALED, K=1 SINGLE RUN)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_M2_DIVIDEND_AUTHORITY_CORRECTION_AND_REPRODUCIBILITY]
[RUN: ONE_CORRECTED_M2_EXECUTION_16_EVENT_AUTHORITY]
[VERDICT: FAIL_CORE_EDGE_NOT_SUPPORTED]
```

- **Manifest:** `docs/phase14/manifests/HYP_009_R2_M2_DIVIDEND_CORRECTED_RESULT.json`
- **Source HEAD:** `2d3c1b23c0db621a8c677df005809f7f7fee9629`
- **Dataset:** `DS_SPY_CORE001_HYP009_M2_ALPACA_1DAY_SIP_DIVIDEND_CORRECTED_001` (`a5a24f02…`)
- **Supersedes (invalidated):** `HYP_009_R2_M2_RESULT.json`
  (`M2_INVALIDATED_BY_DIVIDEND_AUTHORITY_GAP`, preserved untouched)

## 1. corrected M2 Numbers (Exact)

- Signals: 48 (38 LONG / 10 CASH); 9 trades (5 BUY / 4 SELL); first exec
  2021-01-04 (Dec-2020 LONG); last exec 2023-12-01; Dec-2024 LONG no-transition,
  no pending, no 2025 access. Terminal LONG 231 shares.
- Baseline: 100000.00 → **137508.7611884** | ret **0.375087611884** |
  Sharpe **0.7503662265800349025883731009** | MDD **0.2557624443312489943856781208** |
  reg fees 4.44, slippage 190.9548676, divs received 5229.014056,
  terminal receivable 454.04205 (Dec-2024 dividend payable 2025-02-14).
- Stress: **136468.430449** | ret 0.36468430449 | Sharpe 0.7362489911056248154166420563 |
  MDD 0.2596240811274515820595574966 | reg fees 8.82 | slippage 952.245247.
- Benchmark: **162891.092082** | ret 0.62891092082 |
  MDD **0.2409397072449208847315742869**.

## 2. Gates

- G1 PASS | G2 PASS | G3 PASS | **G4 FAIL** (0.2558 < 0.2409 false) |
  G5 PASS | G6 PASS (evidence-derived 10/10) → conjunction FAIL.
- Verdict: **FAIL_CORE_EDGE_NOT_SUPPORTED** (contract-valid).

## 3. Comparison With Invalidated Run

Same signal/trade structure (48/38/10, 9 trades); economics shifted by the
three restored 2024 distributions (baseline +37.51% vs +36.25%). The G4
outcome is unchanged: the filter did not beat buy-and-hold drawdown in M2.

## 4. Terminal

HYP_009 progression terminates (`HYP_009_TERMINAL_NOT_SUPPORTED_AT_LOCKED_M2`).
M3 locked. CORE-001 research objective remains open. No HYP_010 created here.
Paper NOT_AUTHORIZED, live LOCKED, capital $0.00, NO_REAL_ORDERS=true.
