# HYP_009 Terminal Closure at Locked M2 (CONTRACT-VALID FAILURE)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_M2_DIVIDEND_AUTHORITY_CORRECTION_AND_REPRODUCIBILITY]
[HYP_009_STATE: HYP_009_TERMINAL_NOT_SUPPORTED_AT_LOCKED_M2]
[CORE-001_STATE: CORE-001_RESEARCH_OBJECTIVE_REMAINS_OPEN]
```

- **Manifest:** `docs/phase14/manifests/HYP_009_TERMINAL_M2_DECISION.json`
- **Corrected M2 result:** `docs/phase14/manifests/HYP_009_R2_M2_DIVIDEND_CORRECTED_RESULT.json`
- **Verdict:** `FAIL_CORE_EDGE_NOT_SUPPORTED` (contract-valid, 16-event authority)

## 1. What Was Tested

Frozen CORE-001 candidate specification #1 (SPY monthly 10M SMA LONG/CASH)
evaluated once over locked M2 (2021-01-01..2024-12-31) with complete dividend
authority, evidence-derived G6, and unchanged G1–G6.

## 2. Outcome

- G1 PASS (+37.51%), G2 PASS (0.7504), G3 PASS (0.2558), G5 PASS (+36.47% stress).
- G4 FAIL: core MDD 0.2558 vs benchmark MDD 0.2409 — the filter did not improve
  on buy-and-hold drawdown in 2021–2024. G6 PASS (derived 10/10).
- HYP_009 progression TERMINATES. No rescue, no tuning, no parameter search.
- M3 stays LOCKED. M3 must not rescue HYP_009.

## 3. CORE-001 Remains Open

HYP_009 was one frozen candidate specification under CORE-001, not the
objective itself. A successor CORE-001 hypothesis requires a new
pre-performance specification, a new hypothesis ID, and a new R1 seal.
HYP_010 is NOT created in this task.
