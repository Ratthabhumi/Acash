# RI-01 Chronology Discrepancy Report (Additive)

**Status:** DOCUMENTATION OF RECORD — NO PRIOR RECORD ALTERED
**Date:** 2026-10-13
**Scope:** Additive report; does not amend `docs/research/ri01/RI01_AUCTION_MEASUREMENT_ADMISSION.md`, `docs/research/ri01/RI01_CANARY1_READINESS_20261008.md`, or `docs/audit/RESEARCH_UTILIZATION_CHECKPOINT_20261012.md`.

## 1. Discrepancy Summary

| Date | Record | States | Source |
| :--- | :--- | :--- | :--- |
| 2026-10-09 | Canary 2 readiness record (**document date only**) | "Prepared, Empirical Acquisition Not Authorized"; unissued candidate with `null` validity windows; **no dispatch is recorded at this date** | `docs/research/ri01/RI01_CANARY2_READINESS_20261009.md` |
| 2026-10-11 | Admission record (**claimed event times**) | Operator modal approval `2026-10-11T13:18:42.87Z`; claimed actual dispatch `2026-10-11T13:18:56Z` (after approval); `valid_from_utc` `2026-10-11T13:17:00Z` = 102 s BEFORE the recorded approval | `docs/research/ri01/RI01_AUCTION_MEASUREMENT_ADMISSION.md` |
| 2026-10-12 | Research utilization checkpoint | "Canary 2 unissued" | `docs/audit/RESEARCH_UTILIZATION_CHECKPOINT_20261012.md` |

**Documentary correction (2026-10-13):** an earlier version of this report stated that Canary 2 was "Dispatched" on 2026-10-09. That conflated a document date with an event timestamp. 2026-10-09 is the readiness record's document date and records **no dispatch**; the claimed actual dispatch per the admission record is `2026-10-11T13:18:56Z`. This correction changes only this report; no source record was altered, and it does not validate, ratify, or retroactively authorize any authority.

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

**Separation invariant:** the decision about *scientific measurement admissibility* (whether the recorded measurements may be accepted for carefully bounded descriptive use) is SEPARATE from the decision about *authorization validity* (whether the authority preceding the dispatch was valid). A later measurement-admissibility decision never retroactively proves that the backdated `valid_from_utc` was valid; none of the options above ratifies anything automatically.

## 5. Timestamp & Provenance Separation (Additive Clarification)

The records in §1 reference DIFFERENT kinds of timestamps with different provenances; they must not be read as one homogeneous chronology, and day-granularity record dates are not interchangeable with sub-day event timestamps:

| Concept | What it denotes | Value/evidence as recorded | Provenance (source record) |
| :--- | :--- | :--- | :--- |
| Readiness record date | Document date of the Canary 2 readiness checkpoint — a status document, NOT an event time | 2026-10-09; states "Prepared, Empirical Acquisition Not Authorized" | `docs/research/ri01/RI01_CANARY2_READINESS_20261009.md` |
| UNISSUED status | Governance classification of Canary 2 at a record date | Readiness record dated 2026-10-09 = prepared / awaiting authorization; checkpoint dated 2026-10-12 states "Canary 2 unissued" | `docs/research/ri01/RI01_CANARY2_READINESS_20261009.md`; `docs/audit/RESEARCH_UTILIZATION_CHECKPOINT_20261012.md` |
| Approval time | Moment the human approval decision was recorded | `2026-10-11T13:18:42.87Z` (claimed); 102 s AFTER its `valid_from_utc` | Admission record (dated 2026-10-11) |
| Dispatch time | Moment the measurement request was dispatched | `2026-10-11T13:18:56Z` (claimed; AFTER approval) — NOT 2026-10-09 | Admission record (dated 2026-10-11) |
| `valid_from_utc` | Start of the admitted validity window | `2026-10-11T13:17:00Z` — 102 s BEFORE the recorded approval (backdated) | Admission record (dated 2026-10-11) |
| Measurement window | Period the auction measurement itself covers | Not specified in the records cited here | Measurement artifact |
| Admission write | Moment the admission record was written | Record dated 2026-10-11 | Admission record |

Cross-concept ordering claims (e.g., "dispatch precedes admission", "validity precedes approval") are only as trustworthy as each source record's own clock and provenance; none of these orderings is independently verified in this report, and this section resolves none of them. Correcting the documentary date (2026-10-09 = readiness record, not dispatch) likewise validates no authority. The adjudication options in §4 remain the only path to a canonical chronology.

## 6. Verification Ledger

- Implementation Status: COMPLETE (documentation only; zero code changes)
- Contract Enforcement: N/A (no runtime path touched)
- Mathematical Authority: N/A
- Local Test Suite: VERIFIED (3518 passed, 20 skipped; MT5 dir excluded — pre-existing local import limitation)
- Type Checker (MyPy): VERIFIED (new M1.7 module + tests clean)
- Remote CI Status: At original write, PENDING (branch not yet pushed at that time). Current status is determined by the PR #26 checks for the head SHA that carries this report — never inferred from this line.
- Methodological Caveats: This report records a documented tension between two repository records; it does not resolve it. Both inferences are labeled and remain open.
