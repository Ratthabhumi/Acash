# HYP_009 M1 Post-Result Integrity Adjudication

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_M1_POST_RESULT_INTEGRITY_CORRECTION_AND_REPRODUCIBILITY]
[ORIGINAL_RUN: M1_ORIGINAL_RESULT_INVALIDATED_FOR_ARTIFACT_INTEGRITY_REPRODUCIBILITY_REQUIRED]
[HYPOTHESIS_FALSIFIED: false] [STRATEGY_FAILED: false] [METRICS_INCORRECT: unproven]
```

- **Document ID:** `docs/phase14/HYP_009_M1_POST_RESULT_INTEGRITY_ADJUDICATION.md`
- **Original commit:** `a3170aa` (preserved historical evidence, NOT overwritten)
- **Original result manifest:** `docs/phase14/manifests/HYP_009_R2_M1_RESULT.json` (immutable)

## 1. Audited Defects (All Post-Result, All Provenance/Reporting)

- **A. Serialization/hash correction after result:** CRLF-vs-LF file-byte hash
  mismatch was corrected post-observation. Numerical content unchanged, but the
  original seal is not sufficient M2 authority.
- **B. HTTP attempt accounting:** runner counted logical fetches (`+= 1` after
  success), not actual transport attempts (retries/pagination undercounted).
- **C. Raw page provenance:** dataset seal stored bar counts only; raw provider
  page SHA-256 lineage missing.
- **D. G6 hard-coded:** `no_material_contract_failure=True` injected literally
  instead of derived from qualification state.
- **E. Friction mislabel (reporting):** `total_friction` accumulated regulatory
  fees only while slippage lives in fill prices. Renamed to
  `regulatory_fees_paid` with separately reported `execution_slippage_cost`.
  Zero economic change (AUM/returns/Sharpe/MDD/gates unaffected).

## 2. Scientific Contract

Unchanged in full: CORE-001/HYP_009, SPY MONTHLY 10M SMA LONG/CASH, strict >,
equality CASH, next-open execution, whole shares, 100000.00 simulated AUM,
cash 0, no leverage/short/margin, 2/10 bps friction, frozen regulatory fees,
benchmark, G1-G6 thresholds, calendar/dividend authorities, partitions. K = 1.

## 3. Corrective Path Authorized

ONE technical reproducibility re-acquisition of the identical M1 scope +
ONE reproducibility execution, requiring exact reproduction of the frozen
§14 targets. No third run. No M2 under this authorization.
