# ACASH — Evidence Bridge Governance Freeze: D1–D9 — Human Decision / Acceptance Record

**Document ID:** `docs/phase14/phase14_evidence_bridge_governance_freeze.md`
**Type:** Governance decision / acceptance record — formal freeze of the Evidence Bridge contract **before** implementation.
**Status:** `[GOVERNANCE FREEZE RECORD]` — decisions are recorded with explicit statuses (PROPOSED / RECOMMENDED / HUMAN-RATIFIED / DEFERRED / UNRESOLVED). **No decision is auto-ratified.**
**Date:** 2026-09-09
**Mode:** GOVERNANCE FREEZE ONLY — NO IMPLEMENTATION · NO SOURCE CODE CHANGES · DOCUMENTATION-ONLY
**Related:** [`docs/AGENTS.md`](../AGENTS.md), [`docs/ROADMAP.md`](../ROADMAP.md),
[`docs/phase14/phase14_gate14_acceptance_record.md`](phase14_gate14_acceptance_record.md),
[`docs/phase14/phase14_seam_b_acceptance_record.md`](phase14_seam_b_acceptance_record.md),
[`docs/phase14/phase14_s5_test_only_acceptance_record.md`](phase14_s5_test_only_acceptance_record.md),
[`docs/phase14/phase14_master_research_architecture_plan.md`](phase14_master_research_architecture_plan.md),
[`docs/phase14/phase14_architecture_and_governance_plan.md`](phase14_architecture_and_governance_plan.md),
`docs/phase14/phase14_ratification_record_D1_D4.md`,
`docs/phase14/phase14_ratification_record_E1_E9.md`
**Source audit references:** the two preceding (conversation-delivered, read-only) audit deliverables — (1) *ACASH — Production Evidence Bridge Design Audit* (SPEC-ONLY) and (2) *ACASH — Evidence Bridge Governance Freeze: Decision Surface (D1–D9)* — together with the repository source anchors cited inline in §0 and §2–§12.

> [!CAUTION]
> ### GOVERNANCE BOUNDARIES OF THIS RECORD
> - **This record freezes governance decisions only.** It does **NOT** authorize implementation unless each decision's status explicitly grants that authority (see §5).
> - **Implementation authorization must NOT be inferred from recommendations or proposals.**
> - This record is documentation-only. It does not modify any source file, test file, schema, gate, R3 script, runtime wiring, authority-bearing subsystem, HYP_003, R1, trading, or capital.
> - Existing governance records are NOT modified.
> - `features_manifest_hash` remains **UNRESOLVED / SEPARATE GOVERNANCE DECISION SURFACE** and is explicitly NOT resolved by this record (see §14).
> - Phase 8.5 `AlphaEconomicDecomposition` remains a **SEPARATE FUTURE SEAM / DEFERRED** (D9). It must NOT be silently absorbed into an EvidenceBridge implementation.

---

## 0. Classification Discipline

Decision statuses used in this record (mutually exclusive, no auto-escalation):

| Tag | Meaning |
|---|---|
| `[HUMAN-RATIFIED]` | Human approval explicitly supplied for this task. Recorded verbatim. |
| `[RECOMMENDED]` | Designated recommendation from the prior decision surface / audit; still requires human ratification. |
| `[PROPOSED]` | Proposed model/architecture; not yet ratified. |
| `[DEFERRED]` | Recognized as a separate future seam; no action now. |
| `[UNRESOLVED]` | Open item with no binding; no canonical authority assigned. |

Rules:
- Nothing in this record upgrades a `[PROPOSED]`, `[RECOMMENDED]`, or `[UNRESOLVED]` item into `[HUMAN-RATIFIED]`.
- No decision is marked `[HUMAN-RATIFIED]` in this record because **no explicit human approval for D1–D9 was supplied to this task**.

---

## 1. Scope

This record:
- Captures the source-backed baseline findings of the Evidence Bridge SPEC-ONLY audit.
- Records decisions **D1–D9** with explicit statuses.
- Records the dependency graph, the intended (future) Option-B implementation boundary, the forbidden scope, the D7 safety invariant, and the governance impact.

This record does **NOT**:
- Implement `EvidenceBridge`, canonical Sharpe, OOS, `SearchTrialLedger` production lifecycle, or orchestration.
- Modify Phase 5 / Phase 6 / Phase 8.5.
- Create a hypothesis or invoke any gate.

---

## 2. Source-Backed Baseline Findings (from the SPEC-ONLY audit)

1. Phase 5 entry points return `(BacktestManifest, fills_table, equity_table)`:
   - `src/acash/backtest/engine.py` — `EventBacktestRunner.run_backtest` (def at :747, return at :943).
   - `src/acash/backtest/nautilus_bridge.py` — `NautilusTraderSubstrate.run_simulation` (def at :329, return at :674).
2. Phase 5 emits `execution_summary.sharpe_ratio = None` and `sortino_ratio = None` (`engine.py:889-890`). Phase 6 requires a non-None `sharpe_ratio` for candidate (`gate.py:513-517`) and perturbed (`validation/schema.py:552-559`) manifests.
3. Phase 6 requires a canonical return-series lineage within `epsilon_sr = 0.001` (`gate.py:446`):
   - `in_sample_returns` ≡ `trial_return_matrix[:,0]` (`gate.py:393-399`)
   - ≡ `SearchTrialRecord.in_sample_return_series_sha256` (`gate.py:421-425`)
   - ≡ manifest `execution_summary.sharpe_ratio` vs ledger `in_sample_sharpe` (`gate.py:513-522`).
4. Phase 5 has no canonical IS/OOS return-series rule. Equity table is per-**event**, not per-bar (`engine.py:844-855`, `CANONICAL_EQUITY_CURVE_SCHEMA` at `backtest/schema.py:470`).
5. Phase 5 has no canonical annualization authority. `ValidationConfig.periods_per_year` defaults to 252 (`validation/schema.py:921`); historical R3 census used √72576 for M5 (`scripts/execute_phase8_5_step_r3.py:209,263`).
6. Phase 5 has no production `SearchTrialLedger` producer/sealer (`validation/schema.py:343`); construction occurs only in benchmark (`validation/benchmarks/dgp_experiments.py`), R3 census scripts (`scripts/execute_phase8_5_step_r3*.py`), and tests. The R3 census records used synthetic non-resolvable `execution_manifest_id` strings.
7. Phase 5 has no production evidence bridge into Phase 6. All `evaluate_strategy` callers assemble inputs with synthetic/mock evidence only.
8. Phase 8.5 `qualify_alpha` requires `AlphaEconomicDecomposition` (`research/qualification.py:346-347`). Schema exists (`research/alpha_schema.py:155`); pure constructor `create_economic_decomposition` exists (`research/qualification.py:96-121`); **no producer derives its bps inputs from a Phase 5 run**. Natural upstream exists via `RealityGapAttributionEngine` outputs.
9. `features_manifest_hash` — `Optional[str] = None` at `src/acash/research/ai/schema.py:274`; **no canonical producer/consumer binding exists**. `[UNRESOLVED]` / separate governance decision surface.

---

## 3. Decisions D1–D9

### DECISION D1 — SEAM A OPTION A

**Proposal (scope preserved from the prior decision surface):**
- Required `hypothesis_id` in Phase 5 (`engine.py:750` / `nautilus_bridge.py:329`).
- Genuine upstream `HypothesisSpecification.hypothesis_id` — sole identity authority.
- No placeholder IDs (`HYP-PHASE5-POC`, `HYP-NAUTILUS-SUBSTRATE` remain test-constant / stale-doc only).
- No auto-generated or substitute IDs.
- No `manifest_id` digest semantic change (`calculate_backtest_manifest_id` payload is `{hypothesis_spec_sha256, canonical_data_hashes, engine_config_hash, strategy_config_hash, prng_seed}` — `hypothesis_id` NOT added; `backtest/schema.py:427-447`).
- No gate changes.
- No HYP_003. No R1.

**Current state:** IMPLEMENTED / **HUMAN ACCEPTANCE PENDING**.

**Status in this record:** `[PROPOSED / HUMAN ACCEPTANCE PENDING]` — **NOT ratified in this task.** `[UNRESOLVED]` ratification.

### DECISION D2 — CANONICAL RETURN SERIES

**Two legitimate options (exactly, from source context):**

- **D2-A — Phase 5 accounting equity-implied returns.** Canonical Phase 6 series derived from Phase 5 `total_equity`, including fees, slippage, fills, P&L, and equity evolution.
  - Consequence: validation matches economic reality; forces a frozen derivation rule (D3) and Phase 5 Sharpe emission (D7); historical R3-style frictionless numbers become upstream/descriptive only.
- **D2-B — Research signal × forward-return series.** Series = `signal[t] * forward_return[t]` as in R3 (`execute_phase8_5_step_r3.py:176`).
  - Consequence: no new derivation rule needed in principle, but any nonzero friction makes execution Sharpe diverge from the series Sharpe, violating the `gate.py:513-522` equality within `epsilon_sr` — unless Phase 5 runs frictionless.

**Why only ONE canonical series can satisfy the Phase 6 equality chain:** the gate re-derives the column Sharpe from `trial_return_matrix[:, m]`, requires it to equal the ledger `in_sample_sharpe` within `epsilon_sr` (`gate.py:436-453`), requires `trial_return_matrix[:,0]` to be hash-identical to `in_sample_returns` (`gate.py:393-399`), and requires the manifest `execution_summary.sharpe_ratio` to equal the ledger `in_sample_sharpe` within `epsilon_sr` (`gate.py:513-522`). Two distinct series cannot both satisfy this closed triangle of equalities.

**Prior inclination (preserved, not ratified):** D2-A.

**Status in this record:** `[HUMAN DECISION REQUIRED / NOT YET RATIFIED]`.

### DECISION D3 — RETURN DERIVATION RULE

Depends on D2 (`[PROPOSED]` dependency). Before any implementation, the rule must freeze, with **no implementation allowed to invent any of these**:
- formula
- timestamp alignment
- sampling frequency
- first observation handling
- duplicate timestamps
- missing observations
- zero equity
- negative equity
- NaN / Inf handling
- zero variance (precedent: fail closed at `std <= 1e-12`, `validation/deflated_sharpe.py:278`)
- ordering
- minimum sample size (precedent: Phase 6 requires ≥ 4, `gate.py:338-340`)
- gap handling (reject vs tolerated)

Proposed example name (example only, **not ratified**): `EQUITY_SIMPLE_RETURN_PER_BAR_V1`.

**Status in this record:** `[HUMAN DECISION REQUIRED / NOT YET RATIFIED]` (blocked on D2).

### DECISION D4 — ANNUALIZATION AUTHORITY

**Recommended option (designated, not ratified):** `ValidationConfig.periods_per_year` as the **single** authority.

All of the following MUST use the same value:
- Phase 5 Sharpe emission (future)
- ledger recording (`SearchTrialRecord.in_sample_sharpe` is ANNUALIZED per `validation/schema.py:80`)
- Phase 6 validation (`ValidationConfig.periods_per_year`, `validation/schema.py:921`)
- DSR (`deflated_sharpe.py`), CPCV/CSCV (`validation/cpcv.py`), Bonferroni haircut (`validation/multiple_testing.py`), and gate consistency math (`gate.py:440-452`)

Unsupported-timeframe behavior must **fail closed** (precedent: unsupported `sharpe_space` raises `DataContractError`, `validation/schema.py:376-386`). No silent multi-authority defaults (e.g., M5 → one value, Phase 6 → 252, R3 → another value).

**Status in this record:** `[RECOMMENDED / NOT YET RATIFIED]`.

### DECISION D5 — OOS PROVENANCE

**Proposed model:**
- OOS uses the canonical `SplitPolicy` (train / validation / OOS boundaries + embargo; `research/schema.py:144-151`; `research/outcomes.py:115`).
- Held-out OOS event segment.
- Generated by the **same Phase 5 runner** on the OOS segment.
- Separate OOS `BacktestManifest`.
- OOS single-use exposure governance remains enforced (OOS exhausts on first use; `research/manifest.py:67-98`, consumed at `research/pipeline.py:318-346`).
- OOS feeds Phase 6 only as `out_of_sample_returns` (≥ 4, finite; `gate.py:238-267`).
- OOS is **NOT** part of the IS trial ledger / matrix lineage.

**Status in this record:** `[PROPOSED / NOT YET RATIFIED]`.

### DECISION D6 — SEARCHTRIALLEDGER CENSUS OWNERSHIP

**Proposed model:**
- K is defined by the **pre-registered blind census** (research counterpart: `research/reinception.py:155-173`).
- K freezes **before** backtesting.
- Failed trials remain in the census.
- Deterministic trial ordering; primary trial = index 0 (`gate.py:401-412`).
- Bridge materializes `SearchTrialRecord` via existing `SearchTrialRecord.create` (single hashing authority, `validation/schema.py:260-338`).
- Production orchestrator is the **sole sealer** (`SearchTrialLedger.seal`, `validation/schema.py:418`).
- Ledger sealed **once** per hypothesis; post-seal mutation prohibited (schema enforced).
- `execution_manifest_id` binds to the `manifest_store` key (`gate.py:485-495`).
- `hypothesis_id` binds ledger → trial → specification (`validation/schema.py:451-454`).

Existing ledger hashing / sealing implementation is preserved unchanged.

**Status in this record:** `[PROPOSED / NOT YET RATIFIED]`.

### DECISION D7 — SHARPE CALCULATION AUTHORITY

**Proposed architecture (statistical source-of-truth change — requires human decision):**
- ONE canonical Sharpe implementation.
- Behaviorally equivalent to current Phase 6 verification math:
  - arithmetic mean
  - sample standard deviation, `ddof=1`
  - annualization via the D4 authority
  - `std <= 1e-12` fails closed
  - results remain within `epsilon_sr = 0.001` of the gate's re-derivation
  - consumes the same canonical return series as D2/D3
- Proposed location from the prior audit (proposal only): `src/acash/validation/deflated_sharpe.py`.

**D7 SAFETY INVARIANT (recorded):**

```text
canonical_sharpe(series, periods_per_year)
    must be behaviorally equivalent to
    current Phase 6 gate Sharpe verification math
within epsilon_sr = 0.001.
```

The future implementation is NOT authorized to modify `gate.py` merely to make the new canonical function pass. **No gate modification is authorized by this record.**

**Status in this record:** `[HUMAN DECISION REQUIRED / NOT YET RATIFIED]`.

### DECISION D8 — FIRST IMPLEMENTATION SCOPE

**Options:**
- **A** = deterministic evidence assembly only. *Not independently verifiable:* output cannot pass Phase 6 while `sharpe_ratio = None`.
- **B** = evidence assembly + Phase 5 Sharpe emission. First independently verifiable slice.
- **C** = B + OOS execution (requires D5).
- **D** = full orchestration through Phase 6.

**Prior recommendation (designated):** **D8 = OPTION B.**

Scope (Option B):
- `EvidenceBridge` (new module)
- canonical return derivation (D3-frozen rule)
- `manifest_store` assembly
- `SearchTrialRecord` materialization
- ledger construction / sealing
- `trial_return_matrix` assembly
- perturbation evidence assembly
- Phase 5 Sharpe emission (D7 canonical function)

Explicitly EXCLUDED from any Option-B scope:
- OOS execution
- Phase 8.5 economic decomposition
- full production orchestrator
- trading
- HYP_003
- R1

**Status in this record:** `[RECOMMENDED OPTION B / NOT YET AUTHORIZED]`.

### DECISION D9 — PHASE 8.5 ECONOMIC DECOMPOSITION

**Recorded:**
- `AlphaEconomicDecomposition` remains a **separate seam**.
- Schema and constructor exist; **no production producer derives its inputs from a Phase 5 run**.
- Natural upstream evidence exists via `RealityGapAttributionEngine` outputs (`fee_drag_bps`, `spread_drag_bps`, `slippage_drag_bps`, `latency_drag_bps`, `maker_adverse_selection_drag_bps`, `phase5_simulated_realized_bps`, `phase4_analytical_edge_bps`).
- **Do NOT absorb this into EvidenceBridge. Do NOT implement it.**

**Status in this record:** `[SEPARATE FUTURE SEAM / DEFERRED]`.

---

## 4. Cross-Decision Dependency Map

```text
D1
 ↓
D2
 ↓
D3 ─────┐
        ├──→ D7 ──→ D8
D4 ─────┘

D5 = required for the later OOS seam (D8-C+)
D6 = required for a valid trial census / ledger (precondition of D8-B)
D9 = separate future seam (never absorbed into D8)
```

Implementation authorization must NOT be claimed until **all prerequisites required for that implementation** are explicitly ratified (`[HUMAN-RATIFIED]`).

---

## 5. No Implementation Authorization

> **This record freezes governance decisions only. It does not authorize implementation unless each decision's status explicitly grants that authority.**

- No decision in this record is marked `[HUMAN-RATIFIED]`.
- No recommendation (`[RECOMMENDED]`) or proposal (`[PROPOSED]`) confers implementation authorization.
- `EvidenceBridge`, canonical Sharpe, OOS, ledger production lifecycle, and orchestration remain **NOT IMPLEMENTED** and **NOT AUTHORIZED**.
- No gate modification is authorized. No schema modification is authorized. No R3 modification is authorized.

---

## 6. Implementation Boundary (future, intended Option B — recorded, NOT implemented)

**Potential future files, ONLY IF separately authorized:**
- `src/acash/backtest/engine.py` — Phase 5 Sharpe emission only (via D7 canonical function).
- `src/acash/validation/deflated_sharpe.py` — ONE canonical annualized-Sharpe pure function (if D7 ratified).
- **new** `src/acash/research/evidence_bridge.py` — bundle DTO + pure deterministic assemblers.
- **new** corresponding tests (unit + S5 integration extension exercising a real-run Phase 5 → Phase 6 lineage).

**Forbidden list (does not vary with scope):**
- `validation/gate.py`
- `validation/schema.py`
- `research/qualification.py`
- `backtest/schema.py` — `calculate_backtest_manifest_id` digest semantics (`:427-447`), `BacktestManifest.compute_sha256` payload (`:421-423`)
- `features_manifest_hash` (`research/ai/schema.py:274`)
- R3 census scripts
- trading / portfolio / risk / broker / capital
- HYP_003 / R1 authority

---

## 7. D1–D9 Status Summary

| Decision | Status |
|---|---|
| D1 — Seam A Option A | IMPLEMENTED / HUMAN ACCEPTANCE PENDING — `[NOT RATIFIED IN THIS TASK]` |
| D2 — Canonical Return Series | `[HUMAN DECISION REQUIRED / NOT YET RATIFIED]` (prior inclination: D2-A) |
| D3 — Return Derivation Rule | `[HUMAN DECISION REQUIRED / NOT YET RATIFIED]` (blocked on D2; example name NOT ratified) |
| D4 — Annualization Authority | `[RECOMMENDED / NOT YET RATIFIED]` (`ValidationConfig.periods_per_year` sole authority) |
| D5 — OOS Provenance | `[PROPOSED / NOT YET RATIFIED]` |
| D6 — Census Ownership | `[PROPOSED / NOT YET RATIFIED]` |
| D7 — Sharpe Authority | `[HUMAN DECISION REQUIRED / NOT YET RATIFIED]` (statistical source-of-truth change; D7 safety invariant recorded) |
| D8 — First Scope | `[RECOMMENDED OPTION B / NOT YET AUTHORIZED]` |
| D9 — Phase 8.5 Economic Decomposition | `[SEPARATE FUTURE SEAM / DEFERRED]` |

---

## 8. Governance Impact

- The freeze contract binds every future implementation to the recorded statuses and the D7 safety invariant.
- Bridge, when/if authorized, is a **producer of gate inputs, never a decision-maker**; gates remain sovereign and fail-closed.
- No test thresholds, trading thresholds, authority, or capital are affected.
- HYP_003 / R1 remain blocked by the absence of a ratified, implemented, human-accepted full chain — by design.
- `features_manifest_hash` remains `[UNRESOLVED]` / separate decision surface.

---

## 9. Final Governance State (unchanged by this record)

```text
Gate 14                    = ACCEPTED
Seam B                     = ACCEPTED
S5                         = ACCEPTED
Seam A Option A            = IMPLEMENTED / HUMAN ACCEPTANCE PENDING

HYP_001                    = TERMINALLY FALSIFIED
HYP_002                    = TERMINALLY FALSIFIED
HYP_003                    = ABSENT

R1                         = NOT STARTED
ResearchReInceptionGate    = NOT INVOKED

Production Orchestration   = ABSENT
Evidence Bridge            = NOT IMPLEMENTED

Trading                    = LOCKED
Capital                    = $0.00

features_manifest_hash     = UNRESOLVED

NO NEW AUTHORITY GRANTED
```

**This record is documentation-only.** No source change, no test change, no schema change, no gate change, no R3 change, no HYP_003, no R1 invocation, no trading/capital activity, no commit, no push.

### Verification Ledger
- Implementation Status: N/A — DOCUMENTATION-ONLY GOVERNANCE RECORD
- Contract Enforcement: STRICT FAIL-CLOSED (no decision auto-ratified; no implementation authorized)
- Mathematical Authority: PRESERVED (no source-of-truth change made; D7 safety invariant recorded, gate math untouched)
- Local Test Suite: NOT RUN (task is documentation-only; no code or tests changed)
- Type Checker (MyPy): NOT RUN (task is documentation-only; no code or tests changed)
- Remote CI Status: NOT AVAILABLE
- Methodological Caveats: D1 is IMPLEMENTED with HUMAN ACCEPTANCE PENDING (pending the separate human acceptance action). D2/D3/D7 are `[HUMAN DECISION REQUIRED]`; D4/D8 are `[RECOMMENDED]` awaiting ratification; D5/D6 are `[PROPOSED]`; D9 is `[DEFERRED]`. No implementation authorization is granted or inferred anywhere in this record. `features_manifest_hash` remains UNRESOLVED. This record does not modify any existing governance record.