# ACASH Standing By / Governance Invariant Hardening Audit Report

> **Document ID:** `AUDIT-GOV-HARDENING-20260906-001`  
> **Timestamp:** `2026-09-06T23:10:00+00:00`  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed)  
> **Status:** `COMPLETE / VERIFIED`  
> **Overall Verdict:** `PASS`  

---

## 1. Executive Summary & Non-Execution Affirmation

This audit documents the mechanical and structural hardening of the ACASH governance architecture following the terminal falsification and formal closure of Phase 8.5 Track B (`HYP_TSMOM_EURUSD_001` / `STRAT-MOM-MULTI-HORIZON-V1`).

### Non-Negotiable Boundary Affirmations
1. **Zero Empirical Research:** No empirical backtests, machine learning fits, or feature evaluations were executed during this hardening.
2. **Zero New Hypotheses:** No `HYP_..._002` was registered, created, or tested.
3. **Zero Holdout Exposure:** The held-out M5 validation and OOS partitions (bars 6,060 to 9,999) were **never accessed, read, or exposed**.
4. **Terminal Closure Preserved:** `HYP_TSMOM_EURUSD_001` remains permanently closed in `TERMINALLY_FALSIFIED` state.
5. **Zero Capital Authority:** Capital authority remains strictly hard-locked at **`$0.00`**.
6. **Phase 13 Locked:** Phase 13 Step 8 (Human GO) and Step 9 (90-Day Continuous Paper) remain strictly locked.

---

## 2. Governance Amendments & Architectural Implementation

The hardening was executed under the three governance amendments ratified by the human operator:

### Amendment 1: Execution Authorization vs. Universal Ownership
- **Rule:** Separation of dataset planes is formalized in `acash.research.quarantine`:
  $$\mathbf{PHYSICAL\_FILE\_EXISTS \neq REPOSITORY\_CATALOGED \neq AUTHORIZED\_FOR\_HYPOTHESIS \neq EXPOSED\_PRIOR\_LIFECYCLE}$$
- **Implementation:** Datasets in the repository catalog can serve as shared research infrastructure, but *empirical research execution* requires explicit authorization and cryptographic binding (`allowed_hypothesis_ids` or matching `hypothesis_id` and `hypothesis_sha256`).
- **Fail-Closed Policy:** An un-authorized hypothesis attempting to load an existing dataset fails immediately with `CROSS_HYPOTHESIS_CONTAMINATION_ERROR`.

### Amendment 2: Protocol-Scoped Epistemic Semantics
- **Rule:** `DatasetExposureState.UNEXPOSED_PRISTINE` is explicitly documented and bound as **protocol-scoped**:
  > *"Data partition has never been accessed by any empirical search or evaluation within the controlled ACASH research protocol."*
- **Epistemic Invariant:** It does not assert or claim universal human ignorance of outside market data, preserving scientific honesty.

### Amendment 3: Four Decoupled Readiness Planes (No Master Switch)
- **Rule:** There is **NO single master boolean switch** (`system_ready = True`) in `acash.core.readiness_planes`.
- **Implementation:** `SystemReadinessPlanes` represents the four decoupled planes:
  1. `InfrastructureReadinessState` (`SOAK_VERIFIED_PASS`)
  2. `ResearchEngineReadinessState` (`ENGINE_VERIFIED_PASS`)
  3. `StrategyAlphaReadinessState` (`UNPROVEN_ZERO_QUALIFIED` / `TERMINALLY_FALSIFIED`)
  4. `TradingCapitalAuthorityState` (`HARD_LOCKED_ZERO_CAPITAL`)
  plus non-delegable `HumanGOCheckpointState` (`LOCKED_PENDING_PREREQUISITES`).
- **Conjunctive Gate Enforcement:** Trading authorization and Phase 13 Step 9 require independent, non-delegable conjunction across all planes:
  $$\mathbf{Step\ 9\ Paper = Infrastructure(PASS) \land Engine(PASS) \land Strategy(RESEARCH\_QUALIFIED) \land HumanGO(SIGNED)}$$

---

## 3. Modified & Created Files Inventory

| File Path | Nature | Purpose / Contract Enforced |
| :--- | :--- | :--- |
| `src/acash/research/quarantine.py` | **NEW** | Cross-hypothesis data quarantine, exposure states, execution authorization validator |
| `src/acash/core/readiness_planes.py` | **NEW** | Four decoupled readiness plane models, conjunctive gate evaluators, zero master switch |
| `src/acash/research/alpha_schema.py` | **MODIFIED** | Added `TERMINALLY_FALSIFIED` state (0 outbound transitions), added `validate_hypothesis_immutability()` |
| `scripts/execute_phase8_5_step_r3.py` | **MODIFIED** | Integrated `DatasetQuarantineValidator` before parquet loading |
| `tests/unit/research/test_governance_hardening.py` | **NEW** | 12 targeted unit and invariant tests covering quarantine, immutability, and readiness decoupling |
| `tests/unit/research/test_alpha_schema.py` | **MODIFIED** | Updated lifecycle completeness and terminal states tests for `TERMINALLY_FALSIFIED` |
| `docs/ROADMAP.md` | **MODIFIED** | Synchronized Phase 8.5 Track B terminal closure and Phase 13 Steps 5–7 status |
| `docs/README.md` | **MODIFIED** | Synchronized Phase 8.5 documentation hub and Current Governance State table |
| `docs/governance/governance_hardening_audit.md` | **NEW** | This canonical audit report |

---

## 4. Test Suite Execution & Invariant Verification

### 4.1 Targeted Governance Hardening Invariant Tests
Command: `uv run pytest tests/unit/research/test_governance_hardening.py -v`
- **Result:** 12 passed in 2.37s.

| Test Name | Tested Invariant | Result |
| :--- | :--- | :--- |
| `test_new_hypothesis_cannot_implicitly_inherit_prior_dataset` | Cross-hypothesis contamination blocked fail-closed | ✅ PASS |
| `test_quarantined_m5_holdout_inaccessible_to_any_new_research` | M5 holdout bars 6,060..9,999 permanently quarantined | ✅ PASS |
| `test_unknown_dataset_exposure_state_fails_closed` | UNKNOWN exposure state fails closed | ✅ PASS |
| `test_revoked_dataset_exposure_state_fails_closed` | REVOKED exposure state fails closed | ✅ PASS |
| `test_positive_path_authorized_hypothesis_dataset_passes` | Authorized hypothesis and dataset binding succeeds | ✅ PASS |
| `test_terminally_falsified_hypothesis_cannot_be_reopened` | `TERMINALLY_FALSIFIED` has 0 outbound transitions | ✅ PASS |
| `test_sealed_hypothesis_parameter_mutation_fails_closed` | Parameter mutation under existing ID fails closed | ✅ PASS |
| `test_current_hyp_tsmom_eurusd_001_lineage_remains_immutable_and_readable` | SHA-256 seal `5afb92d...` verified exact | ✅ PASS |
| `test_no_single_master_switch_in_readiness_planes` | Absence of boolean master switch verified | ✅ PASS |
| `test_infrastructure_ready_cannot_authorize_trading` | Infrastructure PASS does not authorize trading | ✅ PASS |
| `test_alpha_qualification_cannot_authorize_capital_without_human_go` | Alpha qualification requires Step 8 Human GO | ✅ PASS |
| `test_standing_by_state_enforces_zero_capital_authority` | Standing-by enforces strictly $0.00 capital | ✅ PASS |

### 4.2 Research Unit Test Suite
Command: `uv run pytest tests/unit/research/`
- **Result:** 94 passed in 3.96s (100% pass rate).

### 4.3 Full Repository Test Suite
Command: `uv run pytest`
- **Result:** 1,506 passed, 1 skipped, 0 failed in 39.66s.

### 4.4 Static Type Checker (MyPy)
Command: `uv run mypy src/acash/research/quarantine.py src/acash/core/readiness_planes.py src/acash/research/alpha_schema.py scripts/execute_phase8_5_step_r3.py tests/unit/research/test_governance_hardening.py tests/unit/research/test_alpha_schema.py`
- **Result:** `Success: no issues found in 6 source files`.

---

## 5. Evidence Classification Table

| Finding / Property | Evidence Classification | Ground Truth Reference |
| :--- | :--- | :--- |
| **Cross-Hypothesis Data Quarantine** | **VERIFIED** | Enforced by `DatasetQuarantineValidator`; verified in 5 unit tests |
| **Holdout Bar Quarantine (6,060–9,999)** | **VERIFIED** | `PERMANENTLY_QUARANTINED_HOLDOUTS` registry blocks access; 0 holdout bars read |
| **Protocol-Scoped Epistemic Semantics** | **VERIFIED** | Documented in `DatasetExposureState.UNEXPOSED_PRISTINE` |
| **Decoupled Readiness Planes (4 Planes)** | **VERIFIED** | Enforced by `SystemReadinessPlanes` and `ReadinessPlaneEvaluator` |
| **Absence of Master Trading Switch** | **VERIFIED** | Tested via `test_no_single_master_switch_in_readiness_planes()` |
| **Terminal Immutability (0 Outbound)** | **VERIFIED** | Enforced by `ALLOWED_LIFECYCLE_TRANSITIONS[TERMINALLY_FALSIFIED] == set()` |
| **Anti-HARKing Mutation Lock** | **VERIFIED** | Enforced by `validate_hypothesis_immutability()` |
| **Capital Authority Hard-Lock ($0.00)** | **VERIFIED** | Enforced by `SystemReadinessPlanes.enforce_fail_closed_capital_invariant()` |
| **Phase 13 Step 8/9 Lock** | **VERIFIED** | Enforced by `ReadinessPlaneEvaluator.validate_step9_continuous_paper_transition()` |
| **Future Macro Trend Viability** | **NOT PROVEN** | Categorized strictly as `PROMISING RESEARCH DIRECTION / NOT PROVEN` |
| **Live Broker Trading Authority** | **BLOCKED** | $0.00 Capital Authority, Disconnected wire, 0 orders |

---

## 6. Final Audit Verdict

$$\boxed{\mathbf{VERDICT:\ PASS}}$$

The ACASH repository governance scaffolding is mathematically, architecturally, and procedurally hardened. All invariants are machine-enforced and fail-closed across tested canonical execution paths (VERIFIED FOR TESTED ENFORCEMENT PATHS). No exploratory research was run, no data holdout was accessed, and capital authority remains strictly $0.00.
