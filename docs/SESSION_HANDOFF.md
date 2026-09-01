# ACASH — Session Handoff

---

## 1. Immutable Frozen Baselines

- **Phase 7 (Live Execution Reality):** `FROZEN`
- **Phase 8 (Portfolio Allocation & Tournament):** `FROZEN` (`e6f1d04`)
- **Phase 8.5 (Alpha Research & Economic Evidence):** `FROZEN` (`9ce1365`)
- **Phase 9 (Deterministic Risk Engine & Kill Switch):** `FROZEN` (`6bd40d8`, `HEAD == origin/main`)

---

## 2. Current Project State

### What is Actually Implemented & Working:
- **Full End-to-End Vertical Control Stack**:
  $$\text{Data (1–3)} \longrightarrow \text{Research (4–5)} \longrightarrow \text{Validation (6)} \longrightarrow \text{Evidence (8.5)} \longrightarrow \text{Allocation (8)} \longrightarrow \text{Risk (9)} \longrightarrow \text{Execution (7)}$$
- **Phase 9 Components (`src/acash/risk/`)**:
  - `risk_schema.py`: Canonical domain contracts, enums (`RiskVerdict`, `DeriskPolicy`, `KillSwitchState`, `EmergencyFlattenStatus`), `RiskPolicyConfig`, `CandidateRiskAllocation`, `RiskEvaluationReport`, `KillSwitchResetEvent`, `EmergencyFlattenIntent`.
  - `risk_engine.py`: `DeterministicRiskEngine` realizing `IRiskEngine`, multi-tier exposure evaluations (leverage, concentration, cash floor), `DeriskEngine` implementing `EXACT_SCALE_DOWN` (proven monotonic scaling) and `BINARY_REJECT`.
  - `kill_switch.py`: `SovereignKillSwitchController`, append-only disk ledger (`.jsonl`) with cryptographic SHA-256 event chaining, crash/restart recovery, and multi-sig quorum reset verification via `Ed25519TrustStore`.
  - `emergency.py`: `EmergencyFlattenGenerator` (emits zero-target intents $\Delta q_i = -q_i$) and `EmergencyFlattenTracker` (evaluates completion strictly against authoritative Phase 7 broker reconciliation).
  - `bridge.py`: `RiskStateBridge` (type-safe, validated conversion across `PortfolioState`, `RiskSnapshot`, `CandidateRiskAllocation`, and `RiskState`).
- **Phase 9 Test Coverage (`tests/unit/risk/`, `tests/integration/test_phase9_risk_pipeline.py`)**:
  - 70 Phase 9 tests passing (63 unit tests + 7 integration tests).
  - 842 total tests passing across the repository with exit code 0 (`uv run pytest`).
  - MyPy clean: 0 errors across all 12 Phase 9 source and test files.

---

## 3. Four Core Architectural Invariants Enforced

1. **Four-Way Sovereign Separation**:
   $$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7)}}$$
2. **Sovereign Risk Veto**:
   $$\boxed{\mathbf{Risk\ Rejection\ /\ Kill\ Switch\ Block} \implies \text{Execution Blocked (Fail-Closed, 0 Orders Allowed)}}$$
3. **Emergency Intent Boundary**:
   $$\boxed{\mathbf{EmergencyFlattenIntent\ Emitted} \neq \mathbf{Orders\ Transmitted} \neq \mathbf{Positions\ Flattened}}$$
4. **Zero Direct Broker Wire Authority in Phase 9**:
   $$\boxed{\mathbf{Phase\ 9} \nRightarrow \text{Direct Broker Wire Access}}$$

---

## 4. Immediate Next Step

- **Next Task:** **Post-Phase-9 Architectural Review & Capability Gap Audit**.
- **Rule:** Do NOT implement Phase 10 or make arbitrary feature assumptions until the repository architecture has been comprehensively audited for operational, observability, and lifecycle feedback gaps.
- **Verification Baseline:** `6bd40d8` (842 tests passing, MyPy clean).
