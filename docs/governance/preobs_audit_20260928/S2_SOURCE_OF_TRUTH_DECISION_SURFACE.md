# ACASH Stage S2 Source-of-Truth Reconciliation & Decision Surface

**Document:** `docs/governance/preobs_audit_20260928/S2_SOURCE_OF_TRUTH_DECISION_SURFACE.md`  
**Evaluation Scope:** Stage S2 Window Semantics (60 Actually Observed vs. 60 Consecutive Calendar Sessions)  
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 4, 6  
**Status:** NEUTRAL DECISION SURFACE — PENDING HUMAN SCIENTIFIC ADJUDICATION  
**Notice:** Implementation agents do NOT choose scientific semantics. This document gathers primary empirical evidence from repository history and presents an unweighted decision matrix for human operator ratification.

---

## 1. Context & The Discovered Governance Conflict

A fundamental semantic divergence exists between two governance records regarding the qualification window for **Stage S2 (Short Prospective Qualification)**:

1. **Source Alpha (`docs/CORE_001_STAGED_EVIDENCE_FRAMEWORK_V1.md` on branch `governance/core001-staged-evidence-v1-preobs`):**  
   Defines the S2 window as **"exactly 60 ACTUALLY OBSERVED eligible sessions"**. Under this interpretation, an unobserved or missed session (such as `2026-09-25` being locked) is logged as missed, but does *not* reset the evaluation window. Once 60 successful prospective observation records are accumulated (e.g. across 61 or 65 calendar days), the 60 observations are evaluated as a complete sequence.
2. **Source Beta (Current Governance Session Handoff & Operator Working Notes):**  
   States that historical HYP_011 backtest calibration was based on **"60 consecutive eligible sessions"**, and posits that if an eligible session is missed in prospective execution, the contiguous qualification window is broken and must restart from zero (or cannot be directly compared against the continuous historical calibration distribution).

This audit investigates the primary repository evidence, answers the critical technical questions, and delineates what is mathematically proven versus what requires human governance adjudication.

---

## 2. Primary Repository Evidence & Empirical Answers

### 2.1 How were historical 60-session calibration windows actually generated?
- **Historical Dataset:** HYP_011 daily backtest return series covering the frozen universe from **2016-01-04 to 2024-12-31** (2,264 trading days).
- **Window Generation Mechanism:** Rolling windows were generated using a fixed step of 1 session: $2,264 - 60 + 1 = 2,205$ total rolling windows.
- **Empirical Finding:** In historical backtest data, every single trading session in the NYSE calendar was populated with complete data. There were **zero missed sessions, zero feed dropouts, and zero unobserved trading days**.
- **Equivalence in Backtest:** Because the historical simulation had 100% data coverage, **"60 consecutive calendar trading days"** and **"60 observed trading days"** were mathematically and computationally identical ($N_{\text{calendar}} = N_{\text{observed}} = 60$). The backtest code never had to handle a "gap" or a missed trading day.

### 2.2 What does each governance source explicitly say?

#### A. Source Alpha (`docs/CORE_001_STAGED_EVIDENCE_FRAMEWORK_V1.md`, commit `a95b9a4`):
- Line 116: *"S2 window length = exactly 60 ACTUALLY OBSERVED eligible sessions — NOT a calendar-day window, NOT a calendar-month window, and NOT eligible for qualification until 60 sessions are actually observed."*
- Lines 251-255: *"OBSERVED ELIGIBLE SESSION ≠ EXPECTED ELIGIBLE SESSION ACCOUNTED FOR. S1 needs 20 actually observed + all expected sessions through the 20th accounted for; S2 needs 60 actually observed + all expected through the 60th accounted for. Adjudicated misses stay in the operational record but never increment the observed counter. The 2026-09-25 session stays MISSED_UNOBSERVED_DUE_TO_AUTHORIZATION_LOCK forever."*

#### B. Source Beta (Governance Handoff & Calibration Rationale):
- Notes that the historical sampling distribution of Maximum Drawdown ($\text{MDD} < 25.0\%$) and Cumulative Return ($\text{cumret} > -20.0\%$) was estimated across unbroken, continuous multi-day market paths.
- Argues that skipping a missed session (e.g. stitching Day $t$ directly to Day $t+2$) alters the statistical return series (compounding return across an unmonitored interval or ignoring market volatility on the missed day), and that true statistical fidelity to the calibrated distribution requires contiguous observation.

### 2.3 Which sources predate prospective observation?
- **Both sources predate prospective observation.**
- Ratification records on `governance/core001-staged-evidence-v1-preobs` and the Phase 14 prospective manifests were all committed when `observed_sessions = 0` (prior to Observation #0001).
- Neither source has been contaminated by post-observation outcome data.

### 2.4 Is there an actual contradiction?
**Yes.** The two sources define different state-transition graphs upon encountering a missed session:
- Under Source Alpha: A missed session causes a pause in counter increment (`observed_sessions` remains $k$), but the previous $k$ sessions remain valid components of the eventual 60-observation sample.
- Under Source Beta: A missed session breaks temporal contiguity, potentially invalidating the preceding $k$ sessions and requiring a contiguous window restart ($k \to 0$) to qualify for Stage S2.

### 2.5 What would happen with ONE missed prospective session under each interpretation?

| Metric / Event | Interpretation Alpha (60 Actually Observed) | Interpretation Beta (60 Contiguous Consecutive) |
| :--- | :--- | :--- |
| **Observation Event** | Session 1..15 observed, Session 16 missed, Session 17..61 observed. | Session 1..15 observed, Session 16 missed, Session 17..61 observed. |
| **Observation Count** | Increments to 60 at Session 61. | At Session 16, contiguous streak breaks. Streak at Session 61 is only 45. |
| **S2 Qualification Date** | Evaluated at Session 61 (60 total observed rows). | Cannot evaluate at Session 61; requires waiting until Session 76 (to achieve 60 consecutive). |
| **Return Compounding** | Return from Session 15 close to Session 17 close spans 2 trading days; overnight gap or intermediate return must be handled. | Each window comprises 60 strictly consecutive 1-day returns. |
| **Operational Leniency** | Robust to intermittent network dropouts or authorization freezes. | Extremely strict: a single network outage on day 59 wipes out 59 days of operational qualification. |

### 2.6 Which dashboard fields currently encode either interpretation?
Inspecting `src/acash/observability/core001_dashboard.py` on branch `origin/feature/core001-observability-dashboard-v1`:
- Line 97: `observed = list(state_doc.get("observed_sessions", []))`
- Line 416: `window = records[:S2_REQUIRED]` (where `S2_REQUIRED = 60`)
- Line 422: `if len(records) < S2_REQUIRED: base["evaluation_state"] = "S2_QUALIFICATION_REVIEW_REQUIRED"`
- **Empirical Finding:** The dashboard currently implements **Interpretation Alpha (Observed Row Slicing)**. It simply takes the first 60 records in the `records` list without asserting calendar-date continuity or checking for missing dates between consecutive records.

---

## 3. What Facts are Established vs. What Remains a Human Decision

### Established Empirical Facts:
1. `observed_sessions` is currently **0** across all prospective branches. Observation #0001 has not yet run.
2. In historical simulation, all 2,205 rolling 60-session windows were both consecutive and fully observed.
3. The existing dashboard prototype slices `records[:60]` without calendar continuity checks.
4. Neither policy weakens any quantitative threshold (both enforce $\text{MDD} < 25.0\%$, $\text{cumret} > -20.0\%$, daily return $> -10.0\%$).

### Unresolved Human Scientific & Governance Decisions:
1. **Window Continuity Contract:** Should Stage S2 evaluate the first 60 *accumulated* prospective observations, or must it evaluate a strictly *unbroken contiguous sequence* of 60 trading days?
2. **Missing Session Penalty Policy:** If an infrastructure outage or data-feed disconnect causes a session to be missed, does the operator:
   - **Option 1 (Alpha):** Record the session as `MISSED_UNOBSERVED`, leave the accumulated observations intact, and extend the calendar time required to reach 60 observed sessions?
   - **Option 2 (Beta):** Invalidate the current qualification window and reset the contiguous streak counter to zero?
   - **Option 3 (Hybrid):** Allow up to $M$ non-consecutive missed sessions (e.g. $M \le 2$) provided no two misses are adjacent and portfolio equity is reconciled using official exchange cash distributions?

---

## 4. Neutral Decision Surface for Human Adjudication

| Evaluation Dimension | Option 1: Accumulated Observed (Alpha) | Option 2: Contiguous Consecutive (Beta) | Option 3: Bounded Gap Hybrid |
| :--- | :--- | :--- | :--- |
| **Statistical Purity** | Moderate (stitching across missed days creates multi-day return intervals). | High (exact match to unbroken historical daily return distribution). | High (preserves path integrity within strict tolerance). |
| **Operational Robustness** | High (survives homelab reboots, ISP drops, or local maintenance). | Fragile (single transient failure on Day 59 resets entire 3-month qualification). | Balanced (tolerates transient operator intervention without reset). |
| **Codebase Impact** | Zero (matches existing `core001_dashboard.py` and staged framework text). | Moderate (requires adding calendar contiguity validator and streak reset engine). | Moderate (requires gap tracker and reconciliation validator). |
| **Recommended Threshold** | MDD < 25%, CumRet > -20% | MDD < 25%, CumRet > -20% | MDD < 25%, CumRet > -20%, Max Misses $\le 2$ |

---

## 5. Final Recommendation & Operational Status

- **Status:** **HOLD** on both `origin/governance/core001-staged-evidence-v1-preobs` and `origin/feature/core001-observability-dashboard-v1`.
- **Immediate Action:** **Do NOT modify dashboard code or staged framework text before Observation #0001**.
- **Reasoning:** Observation #0001 is the **first single observation** ($N = 1$). The distinction between "60 accumulated" versus "60 consecutive" has zero mathematical or operational effect on Observation #1, #2, or any session prior to an actual missed session.
- **Human Adjudication Window:** The operator may formally ratify this semantic choice during Stage S1 (Observations 1–20), well in advance of S2 qualification at Observation 60.
