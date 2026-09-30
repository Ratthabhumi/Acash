# ACASH Repository Defect Register & Audit Findings

**Date Context**: 2026-09-30<br>
**Baseline Anchor**: Canonical `origin/main` at `becec27f5eacf283dcb191cf72d0858682d8e055`<br>
**Classification Authority**: Canonical Audit Register (F01 – F13)<br>
**Contract Enforcement Classification**: `CONTRACT_ENFORCEMENT = PARTIAL_FAIL_CLOSED_WITH_KNOWN_INTEGRITY_GAPS_F01_F02_F09`<br>
**Runtime Repair Status**: `RUNTIME_REPAIR_STATUS = PROPOSED_NOT_IMPLEMENTED`<br>
**Offline Reproductions Invariant**: `PASSING_REPRODUCTION_TEST != DEFECT_REPAIRED`

---

## 1. Canonical Audit Summary Table (F01 – F13)

| ID | Finding Title / Description | Component / Location | Operational Risk for Attempt #2 | Required Timing | Status |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **F01** | Economic-state reconciliation gap (tampered state values accepted) | `src/acash/research/hyp_011/shadow_ops.py:600-602` | LOW (initial state is pure starting AUM $100k) | Post-Attempt #2 (Before Obs #2) | REPRODUCED (UNPATCHED) |
| **F02** | Orphan observation bypass when `state.json` absent | `src/acash/research/hyp_011/shadow_ops.py:496-497` | LOW (mitigated by wrapper preflight) | Post-Attempt #2 (Before Obs #2) | REPRODUCED (UNPATCHED) |
| **F03** | CRLF/LF historical seal/hash mismatch on Windows checkouts | `docs/phase14/manifests/` | NONE (Stage C-B verified LF `eea52f69...`) | IMMEDIATE (audit register) | REGISTER CREATED |
| **F04** | Stale HYP_011 test assumptions after Stage C-B integration | `tests/unit/research/test_phase14_hyp_011_*.py` | NONE (test assumptions) | IMMEDIATE (audit branch) | RESOLVED VIA FIXTURES |
| ↳ **F04-A** | `stage_c_b_absent` fixture isolation for pre-recovery boundaries | `tests/conftest.py`, `test_phase14_hyp_011_sip_recovery.py` | NONE (test isolation) | IMMEDIATE (audit branch) | RESOLVED VIA FIXTURE |
| ↳ **F04-B** | Historical target/session fixture isolation in dry-run tests | `test_phase14_hyp_011_prospective_shadow.py` | NONE (test isolation) | IMMEDIATE (audit branch) | RESOLVED VIA FIXTURE |
| **F05** | Module-level `sys.path.insert(0, "scripts")` contamination | `tests/unit/research/test_phase14_hyp_011_*.py` | NONE (test environment hygiene) | IMMEDIATE (audit branch) | RESOLVED VIA LOADER |
| ↳ **F05-A** | Dynamic script module isolation (`spec_from_file_location`) | `tests/unit/research/test_phase14_hyp_011_*.py` | NONE (environment hygiene) | IMMEDIATE (audit branch) | RESOLVED VIA LOADER |
| **F06** | Missing CI execution / branch protection assurance | GitHub Repository Settings / Actions | LOW (human review active) | Pre-Merge to Canonical `main` | DOCUMENTED / MATRIX DEFINED |
| **F07** | Stale README / ROADMAP / status / handoff summaries | `README.md`, `ROADMAP.md`, `docs/handoffs/` | NONE (informational docs) | Post-Attempt #2 Documentation Pass | REGISTERED |
| **F08** | Non-hermetic / native / sealed-data / Git reproducibility dependencies | Repository Test Suite Partitioning | NONE (operational freeze) | IMMEDIATE (audit branch) | PARTITIONED (Hermetic + Audit) |
| ↳ **F08-A** | Synthetic temp Git repository fixture for builder unit tests | `test_phase14_hyp_011_sip_recovery.py` | NONE (hermeticity) | IMMEDIATE (audit branch) | RESOLVED VIA FIXTURE |
| ↳ **F08-B** | Non-hermetic historical Git audit partitioned via pytest marker | `test_phase14_hyp_011_sip_recovery.py` | NONE (governance lineage check) | IMMEDIATE (audit branch) | PARTITIONED (`@pytest.mark.non_hermetic`) |
| **F09** | Stage C-B loader does not enforce `locks` subdocument | `src/acash/research/hyp_011/shadow.py:93-105` | LOW (production Stage C-B has valid locks) | Post-Attempt #2 (Before Obs #2) | REPRODUCED (UNPATCHED) |
| **F10** | CA operational intake pipeline absent for Observation $\ge 2$ | Research Operations & Corporate Actions Pipeline | BLOCKING FOR OBS #2 (Non-blocking for Obs #1) | Prior to Obs #2 Authorization | REGISTERED / HARD STOP GATE |
| **F11** | Docker / install / execution image provenance gap | Deployment & Runtime Container Infrastructure | LOW (homelab uses direct virtualenv) | Prior to Production Activation | REGISTERED |
| **F12** | API / network exposure assumptions require deployment isolation | Homelab Network Architecture & Broker API | LOW (homelab is local, orders locked) | Ongoing Operational Invariant | REGISTERED |
| **F13** | Public repository vs confidential / proprietary wording inconsistency | Repository Metadata & Documentation Tone | NONE (governance alignment) | Post-Attempt #2 Documentation Pass | REGISTERED |

---

## 2. Detailed Technical Defect Records

### F01: Economic-State Reconciliation Gap (State Tamper Accepted)
- **Location**: `src/acash/research/hyp_011/shadow_ops.py:600-602`
- **Mechanism**:
  ```python
  ShadowPortfolio.from_dict(state_doc["strategy"])
  ShadowBenchmark.from_dict(state_doc["benchmark"])
  ```
  `verify_chain()` verifies that state subdocuments can be deserialized into domain dataclasses. It does **not** cross-verify that the accumulated balances (`cash`, `previous_equity`, `holdings`, `SPY_shares`) match the corresponding fields in the terminal observation artifact in the backward hash chain. Tampered or divergent economic values are accepted if the schema is syntactically valid.
- **Operational Impact on Attempt #2**: Negligible for Observation #1 because starting equity is fixed at `$100,000.00` with zero prior observations.
- **Remediation Plan**: In post-Attempt #2 runtime repair, implement cross-document validation verifying that `state_doc["strategy"]["cash"]`, `previous_equity`, `holdings` match the terminal observation artifact.
- **Offline Reproduction**: `test_reproduce_f01_economic_state_not_reconciled_with_terminal_observation` in [`tests/unit/research/test_hyp011_audit_reproductions.py`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/tests/unit/research/test_hyp011_audit_reproductions.py#L40).

---

### F02: Orphan Observation Bypass When `state.json` Absent
- **Location**: `src/acash/research/hyp_011/shadow_ops.py:496-497`
- **Mechanism**:
  ```python
  state_path = state_dir / "state.json"
  if not state_path.exists():
      return build_initial_state(expected_activation)
  ```
  If `state.json` is missing while orphaned observation artifacts exist in `observations/`, `verify_chain()` returns `build_initial_state` immediately. Orphan inspection at line 604 is bypassed.
- **Operational Impact on Attempt #2**: Mitigated because `/usr/local/sbin/acash-hyp011-observation-0001-attempt-0002` explicitly verifies that `data/hyp_011/prospective/observations/2026-09-30.json` and `state.json` are absent before invocation.
- **Remediation Plan**: In post-Attempt #2 runtime repair, check for orphaned observation files before generating initial state; raise `DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: orphan observation files exist without state.json.")`.
- **Offline Reproduction**: `test_reproduce_f02_orphan_detection_bypassed_when_state_json_absent` in [`tests/unit/research/test_hyp011_audit_reproductions.py`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/tests/unit/research/test_hyp011_audit_reproductions.py#L149).

---

### F03: CRLF/LF Historical Seal/Hash Mismatch
- **Location**: `docs/phase14/manifests/`, `docs/phase8.5/hypotheses/`, git checkout layer
- **Mechanism**:
  On Windows environments with `core.autocrlf = true`, files checked out with `\r\n` (CRLF) produce divergent raw binary SHA-256 digests (`read_bytes()`) compared to canonical Linux/Git-tree representations (`\n` LF).
- **Remediation**: Documented in [`docs/audit/LINE_ENDING_HASH_CONVENTION_REGISTER.md`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/docs/audit/LINE_ENDING_HASH_CONVENTION_REGISTER.md). Canonical point of authority is the binary LF representation; historical sealed digests remain immutable.

---

### F04: Stale HYP_011 Test Assumptions After Stage C-B Integration
- **Location**: `tests/unit/research/test_phase14_hyp_011_sip_recovery.py`, `test_phase14_hyp_011_prospective_shadow.py`, `test_phase14_hyp_011_shadow_ops.py`
- **Sub-Findings**:
  - **F04-A**: Tests expecting pre-recovery failure behavior (e.g. absent manifest, same-day retry block) failed because commit `becec27f...` added `HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json` to the filesystem. Resolved via explicit [`stage_c_b_absent`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/tests/conftest.py) monkeypatch fixture.
  - **F04-B**: Dry-run tests assumed hardcoded target session `2026-09-28`. Resolved by binding dynamic or isolated test fixtures.

---

### F05: Module-Level `sys.path.insert(0, "scripts")` Contamination
- **Location**: `tests/unit/research/test_phase14_hyp_011_*.py`
- **Sub-Finding F05-A**: Multiple test modules mutated Python's global `sys.path` at module import time, violating test environment hygiene and risking test ordering contamination. Resolved by replacing module-scope `sys.path.insert` with localized `_load_script_module()` dynamic loaders via `importlib.util.spec_from_file_location`.

---

### F06: Missing CI / Branch Protection Assurance
- **Location**: GitHub Repository Settings / Actions Workflows
- **Mechanism**: Currently zero GitHub Actions CI runs and zero commit statuses exist on `main`. Repository rulesets are empty. Verification currently relies exclusively on local human audits.
- **Remediation**: Documented in [`docs/audit/CI_TEST_MATRIX.md`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/docs/audit/CI_TEST_MATRIX.md); CI pipeline configuration scheduled post-Attempt #2.

---

### F07: Stale Status Documents
- **Location**: `README.md`, `ROADMAP.md`, `docs/handoffs/`
- **Mechanism**: Certain top-level documentation summaries lag behind Phase 14 prospective execution realities.
- **Remediation**: Scheduled for post-Attempt #2 documentation synchronization.

---

### F08: Non-Hermetic / Native / Sealed-Data / Git Reproducibility Dependencies
- **Location**: Repository-wide test suite
- **Sub-Findings**:
  - **F08-A**: `test_builder_dry_run_and_invariants` depended on the live repository's Git commit history (`git log`), failing if run in shallow clones or modified branches. Resolved by replacing with an isolated synthetic temp Git repository fixture.
  - **F08-B**: Live repository ancestry audit was preserved as a dedicated non-hermetic test `test_builder_historical_git_audit` marked `@pytest.mark.non_hermetic`.

---

### F09: Stage C-B Loader Does Not Enforce `locks` Subdocument
- **Location**: `src/acash/research/hyp_011/shadow.py:93-105`
- **Mechanism**:
  `load_stage_c_recovery_authority()` verifies 11 top-level keys but ignores the `locks` sub-dictionary. A corrupt manifest permitting paper trading or capital authorization would be accepted without error.
- **Operational Impact on Attempt #2**: Low, because production manifest `HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json` contains valid locks matching `paper_trading: false`, `live_trading: false`, `real_capital_authority_usd: "0.00"`, `no_real_orders: true`.
- **Remediation Plan**: In post-Attempt #2 runtime repair, strictly validate `locks` sub-dictionary.
- **Offline Reproduction**: `test_reproduce_f09_stage_c_b_loader_ignores_locks` in [`tests/unit/research/test_hyp011_audit_reproductions.py`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/tests/unit/research/test_hyp011_audit_reproductions.py#L178).

---

### F10: Corporate Actions (CA) Operational Intake Missing for Observation $\ge 2$
- **Location**: `scripts/process_hyp_011_prospective_shadow.py:382-409`
- **Mechanism**:
  Observation #1 requires no prior close ratio check (`NO_PRIOR_HISTORY_SINGLE_SESSION`). However, starting at Observation #2, `_check_split_continuity()` requires verified official split and dividend determinations. If unprovided, corporate action processing fails closed.
- **Operational Impact**: Observation #1 is unblocked. Observation #2 cannot proceed without an audited CA determination workflow.
- **Remediation Plan**: Bound to Hard Stop Gate in [`docs/audit/OBSERVATION_0002_READINESS_CHECKLIST.md`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/docs/audit/OBSERVATION_0002_READINESS_CHECKLIST.md).

---

### F11: Docker / Install / Image Provenance Gap
- **Location**: Containerization Infrastructure
- **Mechanism**: Docker images and container execution wrappers lack formal image digest pinning and reproducible multi-stage build manifests.
- **Remediation**: Operationalized prior to live broker activation.

---

### F12: API / Network Exposure Assumptions Require Deployment Isolation
- **Location**: Broker Network Boundary
- **Mechanism**: Assumption that execution hosts will operate within airgapped or strictly firewall-isolated network perimeters without explicit host network security verification.
- **Remediation**: Ongoing operational security invariant.

---

### F13: Public Repository vs Confidential / Proprietary Policy Inconsistency
- **Location**: Documentation License & Proprietary Disclaimers
- **Mechanism**: Inconsistent wording across historical docs regarding proprietary vs public open-source status.
- **Remediation**: Scheduled for post-Attempt #2 documentation cleanup.
