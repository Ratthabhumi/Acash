# ACASH Stage S2 Source-of-Truth Reconciliation & Decision Surface

**Document:** `docs/governance/preobs_audit_20260928/S2_SOURCE_OF_TRUTH_DECISION_SURFACE.md`
**Evaluation Scope:** Stage S2 Window Semantics Reconciliation (Actually Observed vs. Contiguous Eligible Sessions)
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 4, 6
**Status:** NEUTRAL DECISION SURFACE — PENDING HUMAN SCIENTIFIC ADJUDICATION
**Notice:** Implementation agents do NOT choose scientific semantics. This document gathers primary empirical evidence from repository history and presents an unweighted decision surface for human operator adjudication.

---

## 1. Context & The Discovered Governance Conflict

A semantic conflict exists between two governance records regarding the qualification window definition for **Stage S2 (Short Prospective Qualification)**:

1. **Interpretation Alpha (Accumulated Actually Observed Sessions):**
   Defines the S2 evaluation window as **"exactly 60 ACTUALLY OBSERVED eligible sessions"**. Under this interpretation, an unobserved or missed session (e.g. `2026-09-25` being locked) is logged as missed, but does *not* reset the evaluation window. Prospective observations accumulate until 60 valid observations exist (Observations 1–60 inclusive).
2. **Interpretation Beta (Complete Contiguous Eligible Sessions):**
   States that historical HYP_011 calibration was derived from unbroken sequences of **"60 consecutive eligible sessions"**, and posits that if an eligible session is missed in prospective execution, temporal contiguity is broken, requiring the contiguous S2 window to restart from zero.

This document inventories primary evidence, records historical construction, and details the behavior of both interpretations without selecting a winner or creating new thresholds.

---

## 2. Primary Repository Evidence

### 2.1 Historical HYP_011 Calibration Construction
- **Historical Simulation Horizon:** HYP_011 backtest series covering the frozen universe from **2016-01-04 to 2024-12-31** (2,264 trading sessions).
- **Rolling Window Generation:** 2,205 rolling 60-session windows ($2,264 - 60 + 1 = 2,205$) generated with a fixed 1-session stride.
- **Empirical Baseline Fact:** The historical simulation series contains 100% complete data with zero missed trading days, zero feed dropouts, and zero unobserved sessions. Therefore, in the historical dataset, **"60 consecutive calendar trading sessions"** and **"60 observed trading sessions"** were computationally identical ($N_{\text{calendar}} = N_{\text{observed}} = 60$). The historical calibration algorithm never encountered a non-contiguous or missing trading session.

---

### 2.2 Competing Governance Sources

#### Source Alpha: Staged Evidence Framework V1
- **File:** `docs/CORE_001_STAGED_EVIDENCE_FRAMEWORK_V1.md`
- **Branch:** `governance/core001-staged-evidence-v1-preobs`
- **Current Remote Tip SHA:** `1375ccf4be87a3c0390fc94ddb82b1ac942a419e`
- **Parent Commit:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`
- **Merge Status:** UNMERGED (Isolated Evidence Branch)
- **Explicit Text:**
  - Section 6: *"S2 window length = exactly 60 ACTUALLY OBSERVED eligible sessions — NOT a calendar-day window, NOT a calendar-month window, and NOT eligible for qualification until 60 sessions are actually observed."*
  - Section 9.1: *"OBSERVED ELIGIBLE SESSION ≠ EXPECTED ELIGIBLE SESSION ACCOUNTED FOR. S1 needs 20 actually observed + all expected sessions through the 20th accounted for; S2 needs 60 actually observed + all expected through the 60th accounted for. Adjudicated misses stay in the operational record but never increment the observed counter. The 2026-09-25 session stays MISSED_UNOBSERVED_DUE_TO_AUTHORIZATION_LOCK forever."*

#### Source Beta: Operational Governance Handoff & Calibration Rationale
- **Document / Record:** Governance Handoff and Operator Calibration Working Notes
- **Context:** Rationale accompanying HYP_011 prospective activation
- **Merge Status:** UNMERGED
- **Explicit Text:**
  - Historical sampling distribution of Maximum Drawdown ($\text{MDD} < 25.0\%$) and Cumulative Return ($\text{cumret} > -20.0\%$) was calculated over continuous calendar-trading paths.
  - A missed session in prospective operation introduces a non-contiguous break in the price path; therefore, assessing non-consecutive returns against thresholds derived from consecutive historical paths may violate the distributional assumption of the backtest calibration.
  - Under this view, a missed session requires restarting the contiguous window counter.

---

## 3. Comparative Behavior Matrix

The following table contrasts the mechanics of both interpretations across prospective execution dimensions:

| Evaluation Dimension | Interpretation Alpha: Accumulated Actually Observed | Interpretation Beta: Complete Contiguous Eligible |
| :--- | :--- | :--- |
| **Primary Reference Source** | `docs/CORE_001_STAGED_EVIDENCE_FRAMEWORK_V1.md` (`1375ccf4...`) | Operational Calibration Notes & Handoff Records |
| **Window Boundary Rule** | First 60 successful prospective observation records. | First 60 unbroken consecutive eligible trading sessions. |
| **Effect of a Single Missed Session (e.g. Session 15 missed)** | Counter does not increment; previous 14 observations remain valid; qualification evaluated upon reaching 60 total observed sessions. | Contiguous streak is broken; streak counter resets to zero; requires 60 subsequent consecutive sessions without misses. |
| **Return Calculation across Missed Session** | Compounding spans from Session 14 close to Session 16 close across the unobserved interval. | Compounding is strictly daily across adjacent trading days. |
| **Current Dashboard Implementation** | `src/acash/observability/core001_dashboard.py` (tip `3269c438...`): slices `records[:60]` from `observed_sessions`. Does **not** validate calendar contiguity. | Not implemented in current dashboard code. |
| **Repository Integration Status** | Unmerged branch (`governance/core001-staged-evidence-v1-preobs`). | Unmerged notes; not committed in standalone canonical specification. |

---

## 4. Established Facts vs. Unresolved Governance Decision

### Established Empirical Facts:
1. `observed_sessions` is currently **0** across all prospective branches. Observation #0001 has not yet executed.
2. In historical simulation, all 2,205 rolling 60-session windows were both consecutive and fully observed.
3. The dashboard prototype on `feature/core001-observability-dashboard-v1` implements row slicing (`records[:60]`) without contiguity checks.
4. Neither source modifies the quantitative thresholds themselves ($\text{MDD} < 25.0\%$, $\text{cumret} > -20.0\%$, daily return $> -10.0\%$).
5. Observation #0001 is a single observation ($N=1$); the semantic divergence between Interpretation Alpha and Interpretation Beta has zero operational effect on Observation #0001.

### Unresolved Items for Human Adjudication:
1. Does Stage S2 qualification permit accumulated observations across non-contiguous calendar days, or does it require an unbroken sequence of consecutive eligible days?
2. If an infrastructure dropout occurs during Stage S2, does the operator log an unobserved session and continue accumulating, or does the qualification window restart?

---

## 5. Governance Operating Status

- **Semantic Decision Authority:** Human Operator / Sovereign Governance (Implementation agents do not choose scientific semantics).
- **Immediate Action:** **HOLD** on both `governance/core001-staged-evidence-v1-preobs` and `feature/core001-observability-dashboard-v1`. Zero code or rule changes in this task.
- **Operating Invariants:**
  ```text
  S2_SEMANTIC_ADJUDICATION_REQUIRED = true
  STAGED_EVIDENCE_MERGE_STATUS = HOLD
  DASHBOARD_SCIENTIFIC_MERGE_STATUS = HOLD
  ```
