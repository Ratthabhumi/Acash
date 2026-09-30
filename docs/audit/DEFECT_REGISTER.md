# ACASH Repository Defect Register & Audit Findings

**Date Context**: 2026-09-30  
**Baseline Anchor**: Canonical `main` at `becec27f5eacf283dcb191cf72d0858682d8e055`  
**Classification**: Audit Findings F01 – F10

---

## Summary Overview

| ID | Description | Component | Operational Risk for Attempt #2 | Required Timing | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F01** | State economic values deserialized but not reconciled with observation | `src/acash/research/hyp_011/shadow_ops.py` | LOW (initial state is pure AUM $100k) | Post-Attempt #2 (Before Obs #2) | REGISTERED / REPRODUCED (UNPATCHED) |
| **F02** | `verify_chain()` orphan detection bypassed when `state.json` absent | `src/acash/research/hyp_011/shadow_ops.py` | LOW (mitigated by wrapper preflight) | Post-Attempt #2 (Before Obs #2) | REGISTERED / REPRODUCED (UNPATCHED) |
| **F03** | Runner dry-run tests assumed hardcoded 2026-09-28 without manifest isolation | `tests/unit/research/test_phase14_hyp_011_*.py` | NONE (test assumption) | IMMEDIATE (in audit branch) | RESOLVED VIA FIXTURE |
| **F04** | SIP recovery tests called `resolve_operational_activation` without absent fixture | `tests/unit/research/test_phase14_hyp_011_sip_recovery.py` | NONE (test assumption) | IMMEDIATE (in audit branch) | RESOLVED VIA FIXTURE |
| **F05** | Module-scope `sys.path.insert(0, "scripts")` contaminating test environment | `tests/unit/research/test_phase14_hyp_011_sip_recovery.py` | NONE (test hygiene) | IMMEDIATE (in audit branch) | RESOLVED VIA SPEC LOADER |
| **F06** | Builder unit tests queried live repository Git history instead of temp fixture | `tests/unit/research/test_phase14_hyp_011_sip_recovery.py` | NONE (test hermeticity) | IMMEDIATE (in audit branch) | PARTITIONED (Hermetic + Audit) |
| **F07** | Cross-platform CRLF/LF raw binary hash sensitivity in manifests | `docs/phase14/manifests/` | NONE (Stage C-B verified LF eea52f...) | IMMEDIATE (document register) | REGISTER CREATED |
| **F08** | Monolithic test suite lacks formal CI tier partitioning | Repository Test Configuration | NONE (operational freeze) | IMMEDIATE (matrix defined) | MATRIX CREATED |
| **F09** | `load_stage_c_recovery_authority()` omitted `locks` block verification | `src/acash/research/hyp_011/shadow.py` | LOW (production Stage C-B has valid locks) | Post-Attempt #2 (Before Obs #2) | REGISTERED / REPRODUCED (UNPATCHED) |
| **F10** | Corporate Actions (CA) operational acquisition pipeline absent for Session $\ge 2$ | Research Operations & Qualification | BLOCKING FOR OBS #2 (Non-blocking for Obs #1) | Prior to Obs #2 Authorization | REGISTERED |

> [!NOTE]
> **GOVERNANCE STATUS**:  
> `CONTRACT_ENFORCEMENT = PARTIAL_FAIL_CLOSED_WITH_KNOWN_INTEGRITY_GAPS_F01_F02_F09`  
> `RUNTIME_REPAIR_STATUS = PROPOSED_NOT_IMPLEMENTED`  
> `PASSING_REPRODUCTION_TEST != DEFECT_REPAIRED`  
> Offline reproduction tests pass because they successfully assert the presence of the unpatched gap.

---

## Detailed Defect Records

### F01: State Economic Values Not Reconciled with Observation Artifact
- **Location**: `src/acash/research/hyp_011/shadow_ops.py:600-602`
- **Mechanism**:
  ```python
  ShadowPortfolio.from_dict(state_doc["strategy"])
  ShadowBenchmark.from_dict(state_doc["benchmark"])
  ```
  `verify_chain()` tests only that state subdocuments can be deserialized. It does not check that `state_doc["strategy"]["equity"]`, cash, holdings, and benchmark metrics match the terminal observation artifact in the backward hash chain. Tampered or diverged economic values are accepted if the schema matches.
- **Impact on Attempt #2**: For Observation #1, initial portfolio equity is fixed at `$100,000.00` with zero prior observations.
- **Remediation Plan**: Add cross-document validation verifying that the post-session portfolio equity, cash balance, and benchmark equity in `state_doc` equal the corresponding fields in `last_obs["strategy"]` and `last_obs["benchmark"]`.

---

### F02: `verify_chain()` Orphan Detection Bypass When `state.json` Absent
- **Location**: `src/acash/research/hyp_011/shadow_ops.py:496-497`
- **Mechanism**:
  ```python
  state_path = state_dir / "state.json"
  if not state_path.exists():
      return build_initial_state(expected_activation)
  ```
  If `state.json` was deleted or uncommitted while orphaned observation files exist in `state_dir / "observations"`, `verify_chain()` returns `build_initial_state` immediately. Orphan file detection at line 604 is never reached.
- **Impact on Attempt #2**: The scheduled wrapper in `/usr/local/sbin/acash-hyp011-observation-0001-attempt-0002` explicitly verifies that `data/hyp_011/prospective/observations/2026-09-30.json` does NOT exist and `state.json` is absent before execution.
- **Remediation Plan**: In post-Attempt #2 runtime repair, move orphan detection to the entry of `verify_chain()`. If `state.json` is missing but `observations/` contains `*.json` files, raise `DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: orphan files without state.json.")`.

---

### F09: `load_stage_c_recovery_authority()` Omits `locks` Verification
- **Location**: `src/acash/research/hyp_011/shadow.py:93-105`
- **Mechanism**:
  The function iterates over 11 required top-level fields, but does not validate the `locks` sub-dictionary or enforce:
  `locks.paper_trading == false`, `locks.live_trading == false`, `locks.real_capital_authority_usd == "0.00"`, `locks.no_real_orders == true`.
- **Impact on Attempt #2**: The production manifest `HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json` contains valid locks matching these exact values.
- **Remediation Plan**: Add explicit lock validation in `load_stage_c_recovery_authority()` raising `DataContractError("SHADOW_RECOVERY_BINDING_LOCKS_INVALID")` if any lock is breached.

---

### F10: Corporate Actions (CA) Operational Intake Missing for Session $\ge 2$
- **Location**: `scripts/process_hyp_011_prospective_shadow.py:382-409`
- **Mechanism**:
  Observation #1 requires no prior close ratio check (`NO_PRIOR_HISTORY_SINGLE_SESSION`). However, starting at Observation #2, `_check_split_continuity()` requires verified official split and dividend determinations. If unprovided, corporate action processing fails closed.
- **Impact**: Observation #1 is unblocked. Observation #2 cannot proceed without an audited CA determination workflow.
