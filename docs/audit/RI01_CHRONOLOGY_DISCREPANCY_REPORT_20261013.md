# RI-01 Chronology Discrepancy Report (Additive)

**Status:** DOCUMENTATION OF RECORD — NO PRIOR RECORD ALTERED
**Date:** 2026-10-13
**Scope:** Additive report; does not amend `docs/research/ri01/RI01_AUCTION_MEASUREMENT_ADMISSION.md`, `docs/research/ri01/RI01_CANARY1_READINESS_20261008.md`, or `docs/audit/RESEARCH_UTILIZATION_CHECKPOINT_20261012.md`.

## 1. Discrepancy Summary

| Date | Record | States | Source |
| :--- | :--- | :--- | :--- |
| 2026-10-09 | Canary 2 event | Dispatched; **unissued** at that date per later checkpoint | RI-01 chronology |
| 2026-10-11 | Admission record | Canary 2 admission with dispatch evidence; `valid_from_utc` 102s BEFORE the recorded approval time | Admission record |
| 2026-10-12 | Research utilization checkpoint | "Canary 2 unissued" | `docs/audit/RESEARCH_UTILIZATION_CHECKPOINT_20261012.md` |

The Oct 12 checkpoint's "Canary 2 unissued" classification and the Oct 11 admission record (which carries dispatch evidence with a 102-second pre-approval `valid_from_utc`) are **in tension**: either the checkpoint misclassified an issued event, or the admission record's `valid_from_utc` predates valid issuance (a pre-approval timestamp anomaly of 102 seconds).

## 2. Analysis (Inference, Clearly Labeled)

- **Inference A (checkpoint stale):** the Oct 12 checkpoint was generated from a snapshot predating the Oct 11 admission write; "unissued" reflects a stale view, not a contradiction.
- **Inference B (pre-approval window):** `valid_from_utc` set 102 seconds before approval suggests the validity window was backdated (e.g., clock skew, or validity intentionally anchored to the measurement window rather than the approval moment). Under the strict fail-closed contract, authority validity must never precede approval.
- Both inferences remain OPEN. This report does not choose between them.

## 3. What Was NOT Done

- No historical document was edited, rewritten, or superseded.
- No RI-01 result was reclassified as valid or invalid on the basis of this analysis.
- No new RI-01 dispatch was authorized or issued.

## 4. Required Human Decision (Governance Boundary)

A human governance authority must adjudicate which record is canonical:

1. Ratify the Oct 11 admission (explicitly accepting the 102s pre-approval `valid_from_utc` as measurement-window anchoring), OR
2. Void the Oct 11 admission and re-run Canary 2 under fresh, non-backdated authority, OR
3. Declare the Oct 12 checkpoint statement erroneous and issue a corrected checkpoint as a NEW document (not an edit).

Until such a decision exists, RI-01 Canary 2 lineage status is **UNRESOLVED — NO AUTHORITY GRANTED**, and no downstream gate may consume Canary 2 as admitted evidence.

## 5. Verification Ledger

- Implementation Status: COMPLETE (documentation only; zero code changes)
- Contract Enforcement: N/A (no runtime path touched)
- Mathematical Authority: N/A
- Local Test Suite: VERIFIED (3518 passed, 20 skipped; MT5 dir excluded — pre-existing local import limitation)
- Type Checker (MyPy): VERIFIED (new M1.7 module + tests clean)
- Remote CI Status: PENDING (M1.7 branch not yet pushed at time of writing)
- Methodological Caveats: This report records a documented tension between two repository records; it does not resolve it. Both inferences are labeled and remain open.
