# HYP_011 Prospective Shadow Recovery Governance (Stage C)

**Date context:** 2026-09-29  
**Status:** RATIFIED_STAGE_C_A (PENDING_CANONICAL_MAIN_STAGE_C_B_BINDING)  
**Authority:** Human Governance Adjudication (Phase 14 / HYP_011)  
**Recovery Policy:** OPTION_B_ADDITIVE_OPERATIONAL_REACTIVATION  

---

## 1. Executive Summary & Recovery Ratification

Following the blocked provider access during dispatch attempt 1 on session 2026-09-28 (HTTP 403 due to Alpaca historical SIP 15-minute provider access delay boundary), human governance ratified **Option B — Additive Operational Re-Activation**.

Under Option B:
1. **The scientific prospective boundary remains 2026-09-25** without modification. No retroactive prices may be inserted, and no historical metrics are altered.
2. **Session 2026-09-28 is permanently preserved as unobserved**:
   - `failed_dispatch_session = 2026-09-28`
   - `failed_dispatch_attempt = 1`
   - `failed_dispatch_classification = BLOCKED_PROVIDER_ACCESS_BEFORE_OBSERVATION_COMMIT`
   - `failed_session_classification = MISSED_UNOBSERVED_DUE_TO_PROVIDER_ACCESS_BLOCK`
   - Sample contribution: 0 observed sessions, 0 rebalances.
   - Retry of 2026-09-28 is **strictly forbidden**.
3. **Operational activation is advanced additively via Stage C**:
   - Reuses the existing ACASH operational activation reconciliation mechanism (`derive_activation_session`).
   - Does not require mutating `state.json` schema or injecting synthetic `missed_sessions` into runtime state.
   - All trading sessions in $[2026\text{-}09\text{-}25, \text{new\_operational\_activation\_session})$ are formally unobserved/missed.

---

## 2. Two-Stage Recovery Process (Stage C-A vs Stage C-B)

To ensure that operational activation is bound exclusively to canonical `main` history rather than a feature branch commit:

### Stage C-A: Governance Specification & Pre-Merge Fail-Closed Guards (CURRENT)
- Established on corrective branch `fix/hyp011-prospective-sip-window-recovery-20260929`.
- Defines recovery authority, ordinal semantics, attempt lineage, and provider window guards.
- Manifest: `docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_A.json`.
- `stage_c_b_binding = PENDING_CANONICAL_MAIN_AUTHORIZATION`.
- **Pre-Network Guard:** In the absence of a ratified Stage C-B binding, any runner execution after 2026-09-28 market close fails closed immediately with `SHADOW_RECOVERY_BINDING_REQUIRED`. Network requests remain **strictly zero**.

### Stage C-B: Canonical Main Activation Binding (POST-MERGE ONLY)
- To be created **strictly after** human authorization and merge of the recovery branch into canonical `main`.
- Binds the canonical `main` merge commit SHA and commit timestamp in UTC.
- Canonical operational activation session will be derived dynamically via `acash.research.hyp_011.shadow.derive_activation_session(calendar, merge_commit_utc)` (the first NYSE session open strictly after the canonical commit timestamp).
- Manifest: `docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json`.
- **Authority Binding Requirement:** The Stage C-B production manifest strictly requires both canonical `main` commit SHA (`binding_commit_sha`, 40 hex characters) and timezone-aware UTC commit timestamp (`binding_commit_utc`). It cannot authorize an `activation_session` by itself; runtime independently derives the expected activation session from the calendar and commit timestamp and fails closed on any mismatch (`SHADOW_RECOVERY_BINDING_ACTIVATION_MISMATCH`).
- **Canonical Path Requirement:** Production recovery authority must come exclusively from `docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json` relative to the canonical repository checkout. Arbitrary CLI filesystem paths (`--recovery-binding`) are forbidden and rejected.

---

## 3. Observation Ordinal vs Dispatch Attempt Semantics

To prevent ambiguity between scientific sample count and operational attempt history:

- **Observation Ordinal Semantics:**
  $$\text{observation\_ordinal} = \text{number of successfully committed observations} + 1$$
  Because 0 observations have been committed to disk (`observed_session_count = 0`), the next successful observation remains:
  $$\text{OBSERVATION\_ORDINAL} = 1$$
  $$\text{S1\_PROGRESS} = 0/20$$

- **Dispatch Attempt Lineage & Scoping:**
  $$\text{FAILED\_DISPATCH\_ATTEMPT} = 1 \quad (\text{Session 2026-09-28})$$
  $$\text{NEXT\_DISPATCH\_ATTEMPT} = 2 \quad (\text{Recovery Dispatch for Observation \#0001})$$
  *Scoping Rule:* `dispatch_attempt` is strictly scoped to the current observation ordinal.
  - Observation ordinal 1: attempt 1 = failed (blocked provider access); attempt 2 = next recovery dispatch.
  - After Observation 1 successfully commits, Observation 2 begins with its own attempt ordinal (attempt 1) under the standard prospective operational contract.
  - `NEXT_DISPATCH_ATTEMPT = 2` applies exclusively to Observation #0001 recovery and is NOT a forever-global monotonic counter.

- **Authorization Token Specification:**
  For post-recovery dispatches ($\text{dispatch\_attempt} \ge 2$), authorization tokens must make both the observation ordinal and dispatch attempt explicit:
  ```text
  AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_{ordinal:04d}_ATTEMPT_{attempt:04d}
  ```
  For Observation #0001 under Attempt #0002:
  ```text
  AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002
  ```
  The runner enforces exact match on ordinal, dispatch attempt, and recovery binding identity pre-network. Any mismatch raises `DataContractError` and halts with zero network requests.

---

## 4. Provider Timing & Schedule Derivation

### Historical Timing Rule Supersession
- **Historical rule:** `MARKET_CLOSE_ONLY` (observation eligible immediately at market close).
- **Superseded operational rule:** `MARKET_CLOSE + PROVIDER_ACCESS_DELAY + FAIL_CLOSED_BOUNDARY`.
- Historical manifests remain immutable evidence. Future runtime execution uses the superseded rule.

### Provider Eligibility vs Candidate Operational Schedule
Operational timing strictly distinguishes between **provider data eligibility** (when delayed historical SIP bars become queryable without HTTP 403) and **candidate operational schedule** (when the automation runner should be scheduled):

1. **Provider Data Eligibility Boundary (Strict Condition):**
   $$\text{provider\_eligible\_after\_utc} = \text{calendar.get\_session}(\text{session}).\text{close\_utc} + \text{ALPACA\_SIP\_DELAY} + \text{PROVIDER\_SAFETY\_MARGIN}$$
   - `ALPACA_SIP_DELAY = 15 minutes` (Alpaca delayed SIP requirement)
   - `PROVIDER_SAFETY_MARGIN = 0 minutes`
   - Execution rule: queries are permitted strictly when $\text{now\_utc} > \text{provider\_eligible\_after\_utc}$. At exactly the boundary or earlier, requests fail closed immediately.

2. **Candidate Operational Schedule (Automation Buffer):**
   $$\text{candidate\_schedule\_time} = \text{session}.\text{close\_utc} + \text{ALPACA\_SIP\_DELAY} + \text{CANDIDATE\_OPERATIONAL\_MARGIN}$$
   - `CANDIDATE_OPERATIONAL_MARGIN = 5 minutes` (operational margin for dispatch scheduling)
   - Summer/Fall regular session (DST, close 20:00 UTC): $20:00\text{ UTC} + 15\text{m} + 5\text{m} = 20:20\text{ UTC}$.
   - Winter standard time session (EST, close 21:00 UTC): $21:00\text{ UTC} + 15\text{m} + 5\text{m} = 21:20\text{ UTC}$.
   - Early close session (close 18:00 UTC): $18:00\text{ UTC} + 15\text{m} + 5\text{m} = 18:20\text{ UTC}$.

---

## 5. Security & Safety Locks (Strict Invariants)

All execution and capital locks remain strictly enforced:
- `REAL_CAPITAL_AUTHORITY = $0.00`
- `PAPER_TRADING_AUTHORITY = false`
- `LIVE_TRADING_AUTHORITY = false`
- `NO_REAL_ORDERS = true`
- `HOMELAB = DO_NOT_TOUCH`
