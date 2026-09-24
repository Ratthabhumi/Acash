# HYP_009 M2 Dividend-Authority Adjudication

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_M2_DIVIDEND_AUTHORITY_CORRECTION_AND_REPRODUCIBILITY]
[PRIOR_M2_RUN: M2_INVALIDATED_BY_DIVIDEND_AUTHORITY_GAP]
[SCIENTIFIC_TERMINAL_VERDICT: NOT_ESTABLISHED]
```

- **Manifest:** `docs/phase14/manifests/HYP_009_M2_DIVIDEND_AUTHORITY_ADJUDICATION.json`
- **Prior evidence preserved:** commit `2d3c1b2` (historical observation, immutable)

## 1. Finding

The MEC-0015 dividend authority manifest ends 2024-04-30, but M2 extends
through 2024-12-31. The prior M2 run treated absent Q2/Q3/Q4-2024 records as
D=0, violating the frozen contract (missing dividend lineage → FAIL CLOSED)
and contradicting official State Street distribution history. Dividends enter
both signal construction (`G_t`) and portfolio accounting, so the state path,
trades, and G4 may change under corrected authority.

## 2. Classification

- Prior M2 run: `M2_INVALIDATED_BY_DIVIDEND_AUTHORITY_GAP`
- `FAIL_CORE_EDGE_NOT_SUPPORTED` from that run is NOT terminal scientific authority.
- Hypothesis NOT falsified by that run. Re-evaluating its sealed evidence only:
  `dividend_contract_pass = false`, therefore G6 = false independent of G4.

## 3. Corrective Path

New additive HYP_009-specific official supplement (Q2/Q3/Q4 2024, values
supplied by the external research authority — no web research performed here)
plus composite-authority coverage validation, then ONE corrected M2 execution.
No science change. No M3. No new hypothesis in this task.
