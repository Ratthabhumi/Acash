# PHASE 5 — PRODUCTION RESEARCH / EVIDENCE ORCHESTRATION READINESS

**Status:** `[PHASE 5 READINESS]` · `[NON-TRADING]` · `[NO HYP_003]` · `[NO R1]` · `[DESIGN / PREFLIGHT]`

**Document ID:** `docs/phase14/phase5_production_orchestration_readiness.md`

**Grounding HEAD:** `649dd50` (D6 Option A implementation commit; parent `9037ce3`)
**Date:** 2026-09-09
**Authorized scope:** READ-ONLY preflight + design only. No implementation occurred.

> **This document does not authorize implementation.**
>
> **No production orchestrator is implemented by this task.**
>
> **HYP_003 is NOT created. R1 is NOT started.**
>
> **No hypothesis identity is invented** (neither `HYP-PHASE5-POC`, `HYP-NAUTILUS-SUBSTRATE`, nor any
> other placeholder). The upstream hypothesis identity remains an explicit **input contract**.

---

## 1. Current Phase 5 state

Phase 5 (sovereign event-driven backtesting execution) is **implemented and verified at the
component level** but is **not production-orchestrated**:

- `EventBacktestRunner` (`src/acash/backtest/engine.py:300`), aliased as `ACASHNativeBacktestEngine`
  (`src/acash/backtest/nautilus_bridge.py:68`): full event-driven execution loop, shadow accounting,
  FILLS + EQUITY canonical tables, deterministic `BacktestManifest` emission
  (`engine.py:933-949`), canonical Sharpe emission (`engine.py:886-889`).
- The **only production (non-test) caller** of the Phase 5 runner is the OOS held-out path
  `run_separate_oos_backtest` (`src/acash/research/oos_provenance.py:300-331`).
- There is **no production code path** that executes an in-sample candidate census, assembles a
  sealed `SearchTrialLedger`, constructs the perturbation grid, and invokes the Phase 6 gate.
- `census_seal_authority.py:10-12` itself states: *"No production orchestrator exists in this
  repository (Production Orchestration = ABSENT). Until an orchestrator is integrated,
  `SearchTrialCensusSealAuthority` itself is the designated owner acting on behalf of production
  orchestration."*

**Phase 5 overall status: `IMPLEMENTED (components) · ABSENT (production orchestration seam)`.**

## 2. D6 acceptance dependency

Phase 5 orchestration MUST respect the now-human-accepted D6 Option A
(`./phase14_d5_d6_ratification_record.md` §10):

- K = frozen declared/pre-registered census size; `FAILED ∈ census`; `INVALID ∈ census`.
- K MUST NOT silently become successful-count.
- FAILED/INVALID MUST NOT receive fabricated statistical evidence (return = 0 / Sharpe = 0 / p = 1 /
  neutral / synthetic / imputed / zero-filled evidence are all forbidden).
- **MIXED CENSUS → NO COMPLETE STATISTICAL EVIDENCE → FAIL CLOSED.** A Phase 5 orchestration seam
  MUST produce the sealed census truthfully and let the gate fail closed on any mixed census; it
  MUST NOT bypass the D6 fail-closed accessors (`schema.py` `_assert_census_evidence`).
- The Evidence Bridge remains a **non-sealing** assembler
  (`src/acash/research/evidence_bridge.py`; static test `test_evidence_bridge_never_seals`). An
  orchestrator MUST NOT turn it into a sealing authority; sealing goes through
  `SearchTrialCensusSealAuthority.seal_census` (`src/acash/research/census_seal_authority.py`),
  which is governance-enforced, not capability-enforced (see §10).

## 3. Actual Phase 5 source map

| Layer | Source | Status |
|---|---|---|
| Canonical event stream / data adapter | `src/acash/backtest/adapter.py` (`CanonicalDataAdapter`, `BacktestMarketEvent`) | IMPLEMENTED |
| Execution engine | `src/acash/backtest/engine.py` (`EventBacktestRunner`) = `ACASHNativeBacktestEngine` (`nautilus_bridge.py:68`) | IMPLEMENTED |
| Shadow accounting ledger | `src/acash/backtest/accounting.py` (`ShadowAccountingLedger`) | IMPLEMENTED |
| Fills table (canonical) | `CANONICAL_BACKTEST_FILLS_SCHEMA` (`backtest/schema.py:455`), `engine.py:955-979` | IMPLEMENTED |
| Equity curve table (canonical) | `CANONICAL_EQUITY_CURVE_SCHEMA` (`backtest/schema.py:470`), `engine.py:981-1003` | IMPLEMENTED |
| BacktestManifest + manifest id | `backtest/schema.py:326`, `calculate_backtest_manifest_id` (`:427`) | IMPLEMENTED |
| Execution summary + canonical Sharpe emission | `backtest/schema.py:270`; `engine.py:886-905` | IMPLEMENTED |
| Canonical equity→return derivation | `src/acash/backtest/equity_returns.py:33` | IMPLEMENTED (authoritative) |
| Trial record materialization | `SearchTrialRecord.create` in `validation/schema.py` | IMPLEMENTED (component; test-only callers) |
| Evidence assembly | `src/acash/research/evidence_bridge.py:70` (`assemble_phase_six_evidence`) | IMPLEMENTED (component; test-only callers) |
| Census model / sealing | `SearchTrialLedger` / `seal` (`validation/schema.py`); `SearchTrialCensusSealAuthority` (`research/census_seal_authority.py`) | IMPLEMENTED (component) |
| Phase 6 gate | `StatisticalValidationGate` (`validation/gate.py:131`), `ValidationReport` | IMPLEMENTED (component; test/benchmark-only callers) |
| OOS held-out run + provenance | `src/acash/research/oos_provenance.py` (`build_oos_backtest_evidence:425`) | IMPLEMENTED (production-capable; test-only callers) |
| Perturbation grid model | `ParameterPerturbationGrid` (`validation/schema.py:822`) | IMPLEMENTED (model); production grid-run orchestration ABSENT |
| Research manifest / governance ledger store | `src/acash/research/manifest.py` (`ResearchManifestEngine`, `ResearchGovernanceLedger`, default `data/manifests/research/`) | IMPLEMENTED |

## 4. Production vs test-only distinction

**Production (research) code callers of Phase 5 runners:**
- `run_separate_oos_backtest` → `EventBacktestRunner.run_backtest` (`oos_provenance.py:320-321`),
  reachable via `build_oos_backtest_evidence` (`:485`). This is the **only** non-test runner path.

**Test/benchmark-only callers (NOT production):**
- `tests/integration/test_phase14_s5_governance_pipeline.py` (engine + gate wiring, synthetic
  in-memory; header explicitly declares TEST-ONLY, zero runtime wiring).
- `tests/unit/research/test_evidence_bridge.py`, `tests/unit/research/test_oos_provenance.py`,
  `tests/unit/validation/test_d6_failed_trial_census.py`,
  `tests/unit/validation/test_statistical_validation_gate.py` (synthetic ledger/grid/matrix
  generators, e.g. `_create_trial_ledger`, `_make_valid_perturbation_grid`).
- `src/acash/validation/benchmarks/dgp_experiments.py` (DGP governance benchmarks: `_create_mock_manifest`,
  `_create_perturbation_grid`, `_create_trial_ledger` produce synthetic census artifacts —
  methodology experiments, not production evidence).
- `tests/unit/backtest/*`, `tests/integration/test_cross_phase_full_lineage_invariants.py`
  (engine-level unit/invariant coverage).

**Consequence:** all Phase 6 gate-consumable ledger + grid evens produced today are synthetic
(test/benchmark). No truthful census produced by real Phase 5 runs is consumed by the gate anywhere in
production code. This is the core orchestration gap (S1/S2).

## 5. Phase 5 → Phase 6 evidence map

Actual/proposed production data flow (arrow = status):

```
INPUT (canonical events/bars + features)
    →  IMPLEMENTED   Phase 5 runner (ACASHNativeBacktestEngine / EventBacktestRunner, engine.py:748)
    →  IMPLEMENTED   BacktestManifest (engine.py:933; id at backtest/schema.py:427)
    →  IMPLEMENTED   fills_table (engine.py:951; CANONICAL_BACKTEST_FILLS_SCHEMA)
    →  IMPLEMENTED   equity_table (engine.py:981; CANONICAL_EQUITY_CURVE_SCHEMA)
    →  IMPLEMENTED   returns  derive_canonical_equity_returns (equity_returns.py:33)
    →  ABSENT*       trial evidence  SearchTrialRecord.create + canonical Sharpe consistency
    →  ABSENT*       ledger          SearchTrialLedger census built + sealed (authority)
    →  ABSENT*       Phase 6 gate    StatisticalValidationGate.evaluate_strategy (gate.py:131)
```

*"ABSENT" = no production invocation path exists; components are implemented and unit/integration
verified (see §4). The Phase 5 runner is the only fully wired production arrow today (via the OOS
path).

Per-arrow detail:

| Arrow | Implemented | Test-only | Absent | Ambiguous |
|---|---|---|---|---|
| INPUT → runner | ✅ engine + adapter | — | — | Dataset→event-stream production adapter producer not part of this audit's chain |
| runner → manifest | ✅ | — | — | — |
| runner → fills | ✅ | — | — | — |
| runner → equity | ✅ | — | — | — |
| equity → returns | ✅ (single authority D3) | — | — | — |
| returns → trial record | ✅ (evidence_bridge:137) | ✅ (only tests call) | — | — |
| trial record → ledger census | — | ✅ (synthetic) | ✅ production census builder | ledger_id / strategy / sharpe_space choice is design |
| census → seal | ✅ (census_seal_authority) | ✅ | orchestrator owner not integrated | expected_k optional → MUST bind to planned_trial_count in production |
| evidence → Phase 6 gate | ✅ (gate.py) | ✅ (tests/dgp) | ✅ production invocation | — |
| OOS → gate | ✅ (oos_provenance returns oos_return_series) | — | ✅ wiring into gate call | PIT/actor-state/run-identity semantics open (D5) |
| perturbation runs → grid | — | ✅ (mock grids) | ✅ production perturbation-run orchestration | grid runs must be ≥ 3 distinct real runs? (see §16) |

## 6. Identity lineage

- The Phase 5 engine REQUIRES `hypothesis_id` + `hypothesis_spec_sha256` as explicit arguments
  (`engine.py:748-756`) and binds them into `BacktestManifest` (`engine.py:936-937`). No default, no
  placeholder — **Seam A resolved**: the manifest carries the genuine upstream
  `HypothesisSpecification.hypothesis_id` (proven in
  `tests/integration/test_phase14_s5_governance_pipeline.py:773-833`).
- `SearchTrialRecord` binds `hypothesis_id` and `SearchTrialLedger` binds `hypothesis_id + strategy_id +
  ledger instance` (evidence_bridge enforces manifest ↔ trial hypothesis identity match,
  `evidence_bridge.py:104-108`).
- **Orchestration-seam rule:** hypothesis identity (and `hypothesis_spec_sha256`,
  `strategy_config_hash`, `pyproject_toml_sha256`, `git_commit_hash`, `canonical_data_hashes`,
  `periods_per_year`, `uv_lock_sha256`) must be **inputs**, never invented. No
  `HYP-PHASE5-POC` / `HYP-NAUTILUS-SUBSTRATE` or other placeholder may be introduced.
- `periods_per_year` is supplied from `ValidationConfig` (D4 sole annualization authority) — the
  seam must thread it through, not recompute it.

## 7. Return-series lineage

- Canonical rule: `r_t = E_t / E_{t-1} - 1` over canonical `total_equity` (`CANONICAL_EQUITY_COLUMN`)
  in canonical row order; first observation excluded; duplicates preserved; no imputation, padding,
  interpolation, resampling, or look-ahead (`src/acash/backtest/equity_returns.py:33-124`,
  `equity_returns.py:1-18` semantics).
- Fail-closed: <2 observations, missing column, non-monotonic timestamps, non-finite equity, zero/
  negative previous equity, negative equity, non-finite returns → `DataContractError`.
- **This rule is the single authority (D3). The seam MUST reuse it; no second return definition may
  be introduced.**
- The gate's `in_sample_returns` / `out_of_sample_returns` must be exactly what
  `derive_canonical_equity_returns` produces (as the evidence bridge already requires,
  `evidence_bridge.py:117`).

## 8. Sharpe lineage

- Phase 5 emits `execution_summary.sharpe_ratio` via the canonical helper
  `calculate_annualized_sharpe(canonical_returns, periods_per_year)` (`engine.py:886-889`;
  `src/acash/validation/deflated_sharpe.py`), using the D4-frozen `periods_per_year`.
- The evidence bridge verifies emission consistency against the same canonical authority within
  `MANIFEST_SHARPE_CONSISTENCY_TOLERANCE = 0.001` (`evidence_bridge.py:32,123-134`), then binds the
  canonical Sharpe into the trial record (`evidence_bridge.py:137-146`).
- **No modification to canonical Sharpe math or annualization authority is authorized by this task.**

## 9. SearchTrialLedger lifecycle

Current (verified) lifecycle in code:
`SearchTrialRecord.create` → aggregate into `SearchTrialLedger(trials=...)` → `seal(sealing_owner)`
(sets `is_sealed`, `ledger_digest`, `sealed_at_utc`, `sealed_by_owner`) → gate consumption checks
sealed state + recomputed digest (`gate.py:342-357`).

Gaps for production:
1. **No production builder** aggregates executed trial records into a census in the pre-registration
   order (order is frozen and order-locked via the digest; `schema.py` digest binds trial order).
2. **No production sealing call** exists (all sealing today is in tests/DGP).
3. `SearchTrialCensusSealAuthority.seal_census(..., expected_k: Optional[int] = None)` leaves the K
   anchor optional by default (`census_seal_authority.py:36`); a production seam MUST pass
   `expected_k = ResearchInceptionProposal.planned_trial_count`
   (`src/acash/research/reinception.py:162`, enforced by ResearchReInceptionGate cardinal-equality,
   `reinception.py:329`) so frozen-K is cryptographically anchored.

## 10. Sealing authority boundary

- "D6 sealing authority is **governance-enforced, not capability-enforced.**"
- `SearchTrialLedger.seal()` remains directly callable by any caller
  (`validation/schema.py`); `sealed_by_owner` is metadata/governance evidence, not a technical
  capability boundary; the gate checks sealed state + digest only (`gate.py:342-357`), not owner.
- The sanctioned path is `SearchTrialCensusSealAuthority.seal_census` (the designated owner for
  production orchestration, `census_seal_authority.py:3-12`). Any future orchestrator MUST seal
  through it, and MUST keep the Evidence Bridge non-sealing.
- Hardening (mandatory `expected_k`, gate-side owner verification) is a deferred separate human
  decision; NOT implemented here.

## 11. OOS dependency (D5 interaction)

Phase 5 → Phase 6 requires OOS evidence: the gate computes an OOS Sharpe from
`out_of_sample_returns` and rejects on `REJECT_MISSING_OOS_DATA` / `REJECT_OOS_DEGRADATION`
(`gate.py:236-267`, `:620-662`) and `min_oos_sharpe_retention_pct`.

Capable production OOS seam exists: `build_oos_backtest_evidence`
(`oos_provenance.py:425-542`) — PIT attestation verification, OOS segment extraction, FRESH separate
held-out Phase 5 run, OOS canonical returns, `OosEvidenceRecord` (window/segment/manifest/series
binding + no-IS-reuse invariant), returning `oos_return_series` directly consumable by the gate.

**Unresolved D5 surfaces (do NOT silently resolve):**
1. PIT attestation vs actual point-in-time availability evidence (attestation is self-declared with
   provenance; independent proof is a separate decision).
2. OOS strategy actor state isolation (fresh-run IS/OOS state separation is enforced by construction;
   actor-level state carry-over is a runtime-discipline surface).
3. Run-level identity vs `BacktestManifest` identity (OOS identity is bound at the
   `OosEvidenceRecord` layer because manifest digest redesign is forbidden).

Rule: if an orchestration-seam implementation would require DECIDING any of these three, STOP and
create a decision surface instead of choosing.

## 12. features_manifest_hash dependency

- `features_manifest_hash` is an **unresolved decision surface** (unchanged, per governance).
- Source reality: the field exists only as `Optional[str] = None` on `AIFeatureManifest`-adjacent
  schema (`src/acash/research/ai/schema.py:274`); `research/ai/features/materializer.py:52`
  documents it is intentionally NOT promoted into a stored `ResearchManifest.features_manifest_hash`.
  The canonical Phase 4 `ResearchManifest` (`research/schema.py`) does not carry the field.
- The **Phase 5 → Phase 6 backtest evidence chain does not require it**: Phase 6 evidence binds
  feature identity via `input_feature_hashes` in `ResearchManifest` and per-trial `feature_names` /
  `parameter_config_hash` in `SearchTrialRecord`.
- **Dependency to report, not resolve:** it is a binding in the AI feature materialization surface
  (Seam 2, currently DEFERRED). The orchestration seam MUST NOT invent its canonical binding and MUST
  NOT modify `ResearchManifest` merely to make the pipeline pass.

## 13. Production orchestrator status

**"Production research orchestrator remains absent."** — verified two ways:
- Source: no production caller connects census execution → evidence assembly → sealing → gate. The
  only non-test runner path is the OOS held-out run (`oos_provenance.py:300-331`).
- `census_seal_authority.py:10` states it explicitly. Tests, benchmark callers, examples, and
  documentation do not count as a production orchestrator.

## 14. Minimum implementation scope (design — NOT implemented in this task)

The smallest truthful seam that connects the authorized research workflow, preserving all invariants:
a new research-side **orchestration module** (proposal: `src/acash/research/backtest_orchestrator.py`)
that:

1. **Inputs (all explicit, none invented):** `HypothesisSpecification` (or its stable serialized
   inputs), `ResearchInceptionProposal.planned_trial_count` (K anchor), pre-registered parameter
   grid (order-locked), canonical dataset (bars/events, `canonical_data_hashes`), `SplitPolicy`,
   `ValidationConfig.periods_per_year`, `BacktestEngineConfig`, strategy actor factory, env hashes
   (`pyproject_toml_sha256`, `uv_lock_sha256`, `git_commit_hash`).
2. **Executes pre-registered in-sample census trials** through `EventBacktestRunner` in deterministic
   order, producing `BacktestRunEvidence` per trial.
3. **Runs the perturbation set** (base ±25% at `ParameterPerturbationGrid`, `validation/schema.py:822`)
   as distinct runs with distinct `run_id`, `manifest_id`, `output_artifact_hash`.
4. **Runs the OOS held-out segment** via `build_oos_backtest_evidence` (D5-A) with a verified PIT
   attestation; obtains `oos_return_series` for the gate.
5. **Assembles evidence** via `assemble_phase_six_evidence` → `PhaseSixEvidenceAssembly` (matrix,
   manifest store, trial records).
6. **Builds + seals the census:** `SearchTrialLedger` in pre-registration order, then
   `SearchTrialCensusSealAuthority.seal_census(..., expected_k=planned_trial_count)`.
7. **Invokes `StatisticalValidationGate.evaluate_strategy`** with the sealed ledger, matrix column
   ids, manifest store, IS returns, OOS returns, and perturbation grid; emits + persists the
   `ValidationReport` (and artifacts via `ResearchManifestEngine` / `ResearchGovernanceLedger`).
8. **D6 guardrails enforced:** a FAILED/INVALID trial remains a census member; mixed census →
   gate fails closed; zero fabricated evidence; the module never seals except through the authority.

Non-goals inside this scope: no HYP_003, no R1, no ResearchReInceptionGate invocation, no candidate
selection, no AlphaEconomicDecomposition, no features_manifest_hash binding, no D5 semantic
decisions, no trading.

## 15. Explicit non-goals

- Create/register HYP_003 or any hypothesis; choose a candidate (incl. F-1 / Time / Session).
- Start R1; seal R1; invoke any gate as an execution authority.
- Run a research backtest for an actual candidate; optimize/search parameters; generate alpha
  results; compute admission performance; produce economic qualification evidence; perform OOS
  strategy validation.
- Paper trading, live trading, broker connectivity, capital.
- Modify Phase 6 statistical math, thresholds, DSR/Holm/effective-K, or tolerance constants.
- Modify `BacktestManifest` / `ResearchManifest` digest design; resolve `features_manifest_hash`.
- Modify D6 code, D6 tests, sealed artifacts, or any ratified record.
- Implement the production orchestrator (deferred to a separate authorized task).

## 16. Human decisions required

1. **Authorize Phase 5 orchestrator implementation** (next task) and bind the exact scope of §14.
2. **`features_manifest_hash`**: define its canonical binding or explicitly exclude it from the
   Phase 5 → Phase 6 chain.
3. **D5 follow-ups** (PIT actual-availability evidence; OOS actor state isolation; run-level vs
   manifest identity): decide resolution pathway; a Phase 5 seam may consume `OosEvidenceRecord` only
   while keeping these open unless a task explicitly includes them.
4. **Sealing hardening** (mandatory `expected_k`; gate-side `sealed_by_owner` verification): separate
   decision whether to move beyond governance-enforced sealing.
5. **Perturbation-run source:** confirm the orchestration scope must produce ≥3 distinct real
   perturbation runs (K census + 3 perturbations + 1 OOS held-out) rather than reusing census runs
   (grid enforces distinct `run_ids` / `manifest_ids` / `output_artifact_hashes`,
   `validation/schema.py:852-871`).
6. **Census determinism inputs:** confirm the per-trial event-stream / actor determinism contract the
   seam must enforce (fresh runner per trial, identical streams, frozen seed per
   `BacktestEngineConfig.prng_seed`).

## 17. STOP condition

STOP is achieved in this task after:
1. D6 Option A human acceptance is recorded (`./phase14_d5_d6_ratification_record.md` §10) — DONE.
2. Phase 5 readiness/preflight documentation (this document, §1-§16) — DONE.

**Hard stop: no further implementation of the production orchestrator in this task.** The orchestrator
is implemented only in a subsequent task explicitly authorized by the human. If any phase of that
future implementation encounters an unresolved D5 semantic (§11) or `features_manifest_hash` binding
requirement (§12), the agent MUST stop and create a decision surface instead of choosing.

---

### Verification Ledger (this document)
- Implementation Status: NONE (this task is READ-ONLY preflight + documentation; no source/test
  change).
- Contract Enforcement: STRICT FAIL-CLOSED (D6 semantics preserved; orchestrator NOT implemented).
- Mathematical Authority: CANONICAL SPEC (D3 returns, D7 Sharpe, D4 periods_per_year — unmodified).
- Local Test Suite: NOT RUN (no code changed; pre-existing verified state 1990 passed / 1 skipped,
  mypy 371 clean at `649dd50`).
- Remote CI Status: NOT AVAILABLE.
- Methodological Caveats: production orchestrator ABSENT by design; ledger/grid evidence production
  today is test/DGP-synthetic only; D5 items and `features_manifest_hash` remain open decision
  surfaces (reported, not resolved).

---

## 18. IMPLEMENTATION RESULT (appended by the authorized Phase 5 orchestrator task)

This section supersedes §13 ("orchestrator absent") and §17-2 with the verified outcome of the
authorized implementation task. Everything else in §1-§16 stands; human decisions §16-1, §16-3,
§16-5, and §16-6 are hereby executed by the ratifying human for this scope.

### 18.1 What was implemented

- **`src/acash/research/backtest_orchestrator.py`** — the minimum production Phase 5 →
  Phase 6 orchestration seam, implemented exactly on the §14 scope:
  1. Frozen pre-registration mesh (`FrozenResearchPlan`) with census order-lock, hypothesis
     identity binding, single annualization authority, 100% partition allocation, dataset/lineage
     binding, and perturbation config identity binding (§14-1).
  2. Ordered in-sample census execution via fresh `EventBacktestRunner` per trial (§14-2).
  3. Canonical 3-point perturbation grid (exact 0.75/1.0/1.25 × theta_0, distinct real runs,
     distinct `run_id` / `manifest_id` / `output_artifact_hash`, exact manifest-Sharpe match,
     `input_artifact_hash = SHA256("{hyp_spec_sha256}:{strategy_config_hash}")`) (§14-3,
     decision §16-5: three distinct real perturbation executions).
  4. Separate held-out OOS via `build_oos_backtest_evidence` (D5-A, PIT fail-closed, no-reuse
     bound bound to `primary_in_sample_returns`) (§14-4), fresh OOS actor from an independent
     factory (§16-6).
  5. Evidence assembly via `assemble_phase_six_evidence` (≠ naive tuple) (§14-5).
  6. Census sealing ONLY via `SearchTrialCensusSealAuthority.seal_census(expected_k=
     planned_trial_count)`; K never shrinks; no bare `ledger.seal()` anywhere (§14-8).
  7. `StatisticalValidationGate.evaluate_strategy` invoked only on a SEALED_COMPLETE census with
     the sealed ledger, matrix column ids, bound manifest store, perturbation grid, IS returns,
     and OOS returns; gate exceptions PROPAGATE (never swallowed) (§14-7).
- **`tests/unit/research/test_phase5_production_orchestrator.py`** — 37 adversarial tests
  (happy path → governance → mixed-census D6 Option A → fail-closed → module invariants),
  including the AST firewall (no execution/portfolio/runtime/risk/broker/networking/reinception
  imports, no `eval`/`exec`/`compile`/`__import__`/`importlib`, no bare `.seal(` call).

### 18.2 D6 Option A (human-accepted) enforcement

FAILED/INVALID trials REMAIN census members with NO evidence (`SEARCH_TRIAL_EVIDENCE_FIELDS`
None, `failure_reason` free-form). A mixed census is sealed truthfully as `SEALED_MIXED`
(`ledger_digest`, designated owner `ACASH_D6_CENSUS_AUTHORITY`), Phase 6 / perturbation / OOS are
NOT invoked, and the report carries an explicit `blocked_reason`. `successful_count` is a report
metric only — it is never substituted for K and the seal always uses `expected_k=
planned_trial_count`.

### 18.3 Fail-closed hardening applied during implementation verification

- `ledger_digest is None` → `DataContractError` (never `""`).
- `sealed_by_owner` absent → `DataContractError` (never falsy-coalesced).
- `failure_reason` absent on a non-successful trial → `DataContractError` (no `"unknown failure"`
  fabrication).
- Perturbation grid length != 3 → `DataContractError`; strict 3-tuple `points` typing matches
  `ParameterPerturbationGrid` (`validation/schema.py`).
- No `max(floor)`/`clip`/NaN fabrication, no magic p=1.0 / SR=0.0 substitution in the module.
- `raw_predictive_edge_bps=15.0` is a documented explicit policy INPUT to the gate's friction
  stress battery (not a data-derived edge and not a silent floor).

### 18.4 Verification ledger (this task)

- Implementation Status: **COMPLETE** (`src/acash/research/backtest_orchestrator.py`; NO commit,
  HEAD remains `649dd50`).
- Contract Enforcement: **STRICT FAIL-CLOSED** (verified per §18.2/§18.3 and the anti-floor AST
  tests).
- Mathematical Authority: CANONICAL SPEC (D3 returns, D7 annualized Sharpe ddof=1, D4
  periods_per_year, Evidence Bridge single authority, seal authority, D5 OOS, Phase 6 gate —
  none modified).
- Module-internal invariants: SINGLE AUTHORITY on ledger sealing (authority-only), single authority
  on record construction (Evidence Bridge), K anchored at seal time.
- Local Test Suite: **VERIFIED** — full `uv run pytest`: 2027 passed / 1 skipped (1990 baseline +
  37 new); focused `test_phase5_production_orchestrator.py`: 37/37 passed.
- Type Checker (MyPy): **VERIFIED** — `uv run mypy src/ tests/` clean across 373 source files.
- Remote CI Status: NOT AVAILABLE.
- Methodological Caveats: (1) `features_manifest_hash` remains UNSOLVED and OUT of scope (decision
  §16-2 stands open; the seam does not invent a binding and does not shield it). (2) D5 follow-ups
  (PIT actual-availability, OOS actor state isolation, run-level identity) remain open; the seam
  consumes `OosEvidenceRecord` per decision §16-3. (3) `raw_predictive_edge_bps=15.0` is a fixed
  policy input, not evidence-derived. (4) The gate remains a NON-execution authority — no tradeable
  admission. NO HYP_003, NO R1, NO candidate selection, NO trading/broker/capital in this scope.