# PHASE 14 — D5/D6 HUMAN-RATIFIED FREEZE & IMPLEMENTATION RECORD

**Document ID:** `docs/phase14/phase14_d5_d6_ratification_record.md`
**Type:** Governance acceptance/freeze record (ONE record for this authorization).
**Status:** `D5 = HUMAN-ACCEPTED · PIT LINEAGE IN D5 SCOPE · D6 = OPTION A HUMAN-ACCEPTED · MIXED-CENSUS EVALUATION FAIL-CLOSED · PHASE 5 READINESS PREFLIGHT — STOP`
**Date:** 2026-09-09
**Authority:** `./AGENTS.md`, `./phase14_d5_d6_decision_surface.md` (decision surface),
`./phase14_d8b_acceptance_record.md`, `./phase14_evidence_bridge_ratification_D1_D9.md`,
`./phase14_evidence_bridge_governance_freeze.md`
**Origin:** Human-supplied ratified decisions (verbatim mandate) for continuous execution with hard
governance checkpoints.

---

## 1. Human-ratified state (canonical)

```text
Gate 14                    = ACCEPTED
Seam B                     = ACCEPTED
S5                         = ACCEPTED
Seam A Option A            = HUMAN-RATIFIED / ACCEPTED
D2-A / D3 / D4 / D7        = HUMAN-RATIFIED
D8-B                       = HUMAN-RATIFIED / ACCEPTED
D5                        = HUMAN-ACCEPTED   (this record)
D6                        = HUMAN-ACCEPTED — OPTION A ACTIVE: frozen K / FAILED+INVALID stay in census /
                             no fabricated evidence / mixed-census evaluation FAIL CLOSED (this record §10)
D6 statistical semantics  = MIXED-CENSUS EVALUATION FAIL CLOSED; additional mixed/incomplete-census
                             methodology NOT REQUIRED FOR CURRENT OPERATION / OUT OF SCOPE (§10)
D9                        = DEFERRED
HYP_003                    = ABSENT
R1                         = NOT STARTED
ResearchReInceptionGate    = NOT INVOKED
Production Orchestration   = ABSENT (Phase 5 readiness preflight:
                             ./phase5_production_orchestration_readiness.md)
Trading                    = LOCKED
Capital                    = $0.00
features_manifest_hash    = UNRESOLVED (unchanged; dependency reported in Phase 5 readiness doc)
HEAD                        = 649dd50 (D6 Option A implementation commit; pushed to origin/main)
NO COMMIT / NO PUSH (this acceptance + preflight round)
```

## 2. Ratified D5 decision

**D5 = HUMAN-RATIFIED. Selected model: D5-A** — Canonical OOS provenance using the existing canonical
`SplitPolicy` where applicable, executed as a **SEPARATE HELD-OUT PHASE 5 RUN**.

- **PIT LINEAGE = HUMAN-RATIFIED / IN SCOPE OF D5.** D5 must establish truthful point-in-time
  provenance sufficient to prevent temporal/data leakage across the IS/OOS boundary.
- The implementation MUST NOT split an IS equity curve after the fact and call the resulting segment OOS.
- Required structure: `Dataset -> IS -> Phase 5 run -> IS BacktestManifest`;
  `Dataset -> OOS -> separate Phase 5 run -> OOS BacktestManifest -> OOS evidence`.
- Required invariants (contractual): explicit IS/OOS separation; deterministic temporal ordering;
  explicit boundary inclusivity/exclusivity; separate held-out Phase 5 execution; truthful OOS
  `BacktestManifest`; OOS identity bound to its own run; IS equity MUST NOT be reused as OOS evidence;
  no future information crosses the OOS boundary; dataset identity/version/provenance auditable;
  corporate-action/data-availability lineage must not be silently treated as PIT; missing PIT provenance
  FAILS CLOSED where required; no synthetic OOS evidence; no post-hoc OOS construction from observed results.
- Implementation rules: re-use existing primitives (canonical `SplitPolicy` /
  `partition_dataset_with_embargo`; Phase 5 runner; canonical equity-return derivation; canonical
  Sharpe; canonical serialization hashing); do NOT invent a parallel SplitPolicy framework; do NOT
  redesign `BacktestManifest`. If an invariant cannot be satisfied without a material
  governance/schema change, STOP and report the exact gap instead of silently weakening it.

## 3. Ratified D6 decision

**D6 = HUMAN-RATIFIED. Census model:**
- Trial census PRE-REGISTERED before blind evaluation.
- K FROZEN before evaluation begins.
- Deterministic trial registration order and trial identity.
- NO post-hoc trial insertion.
- Every pre-registered trial REMAINS represented in the census.
- Evidence Bridge may construct trial records; MUST NOT seal the ledger.
- The production orchestration/sealing owner is the sole authority to seal the authoritative
  `SearchTrialLedger`; the minimum governance mechanism necessary and nothing more.
- K used by downstream statistical accounting corresponds to the frozen registered census.

**Ratified failed/crashed trial rule:**
- A failed/crashed/invalid trial REMAINS in the pre-registered census.
- MUST NOT: be silently removed; be converted to return = `0`; receive fabricated performance; be
  replaced by another trial; cause K to shrink; be silently retried as a different trial identity.
- MUST carry an explicit failure/invalid status preserving the distinction:
  `REGISTERED + EXECUTED SUCCESSFULLY / REGISTERED + FAILED / REGISTERED + INVALID`.
- No new financial return convention for failed trials.
- **If the existing `SearchTrialRecord`/`SearchTrialLedger` schema cannot represent this status
  without schema change, STOP and report the minimum required schema decision rather than inventing
  semantics.**

## 4. Forbidden authorities (preserved — NO implementation below)

- HYP_003 creation/registration; R1; ResearchReInceptionGate invocation.
- Production Orchestration beyond the minimum D6 sealing-owner infrastructure.
- Phase 8.5 economic decomposition; new Alpha Qualification invocations.
- Trading, paper/live trading, broker connectivity, capital deployment.
- `features_manifest_hash` redesign; gate threshold changes; qualification threshold changes;
  `BacktestManifest` digest redesign.
- Any schema redesign not explicitly authorized (see §5).

## 5. Audit finding — D6 failed-trial status requires a schema decision (STOP condition)

During the D6 implementation audit (Stage 2) the following was verified against source
(`validation/schema.py:70-338`, `:343-478`):

- `SearchTrialRecord` requires `in_sample_sharpe`, `p_value`, `p_value_input_hash`,
  `in_sample_return_series_sha256`, and `execution_manifest_id` — all mandatory, no `None` escape
  hatch, no failure/invalid status field.
- `SearchTrialRecord.create()` derives p-value/hashes from a real return series; a crashed/invalid
  trial has no truthful return evidence, so it cannot be materialized as a `SearchTrialRecord`
  without fabricating values (forbidden) or inventing a representation (forbidden).
- `SearchTrialLedger.compute_ledger_digest()` computes over `in_sample_sharpe`/`p_value` directly,
  and the gate couples K = `|trials|` with order-locked matrix columns; a sibling "side census"
  would break the `K_ledger == K_DSR == K_Holm` contract.
- **Conclusion:** REGISTERED+FAILED and REGISTERED+INVALID cannot be represented under the current
  schema WITHOUT a schema change. Per the ratified rule, the agent STOPS and surfaces the minimum
  required schema decision rather than inventing semantics.
- The authoritative decision request is recorded separately: `./phase14_d6_schema_decision_request.md`.
- **RESOLVED (2026-09-09):** The human ratified **D6 Option A** following the Stage 1 audit:
  - Per-trial status `EXECUTED_SUCCESSFULLY / FAILED / INVALID` (every census member is implicitly REGISTERED).
  - Evidence fields become Optional; non-executed trials carry `None` evidence plus a non-empty deterministic
    `failure_reason` (no fabricated performance, no `return = 0`, no row removal).
  - K = frozen census = `|trials|` remains the invariant; failed/invalid trials remain represented in the census.
  - `compute_ledger_digest()` binds the status + identity of every census member (ratified digest change).
  - Statistical deep-return consumption over mixed censuses (`p_values`, empirical trial mean/variance)
    FAILS CLOSED pending the human D6 statistical-semantics decision (Stage 7 artifact
    `D6 STATISTICAL SEMANTICS DECISION REQUIRED`). No replacement DSR/Holm accounting is invented.
  - D5 (Stage 1) is NOT blocked by this finding and is implemented under this record per §2.

## 6. Implementation surfaces created under this record

| File | Purpose | Status |
|---|---|---|
| `src/acash/research/oos_provenance.py` | D5-A canonical OOS provenance: partition re-use, OOS event segment extraction, separate held-out OOS run, OOS evidence record, PIT attestation + fail-closed lineage verification | NEW |
| `tests/unit/research/test_oos_provenance.py` | Adversarial D5 tests (separation, identity, boundaries, no IS-equity reuse, PIT fail-closed, determinism, gate-consumability) | NEW |
| `docs/phase14/phase14_d6_schema_decision_request.md` | Minimum schema decision request for the D6 failed-trial invariant (STOP artifact) — superseded by the human D6 Option A ratification (§5 RESOLVED) | RESOLVED |
| `src/acash/validation/schema.py` | D6 Option A: `SearchTrialStatus` enum (3 values); Optional evidence fields; status-conditional before/after validators; `create_declared()`; digest binds status + failure_reason; fail-closed `p_values` / empirical mean/variance; `sealed_by_owner`; `seal(..., sealing_owner=...)` | RATIFIED MODIFICATION |
| `src/acash/validation/gate.py` | D6 fail-closed evidence guards per trial-record column (type-level None narrowing; ZERO statistical change) | RATIFIED MODIFICATION |
| `src/acash/validation/benchmarks/dgp_experiments.py` | D6-typed narrowing annotations on `in_sample_sharpe` consumers (no math change) | RATIFIED MODIFICATION |
| `src/acash/research/census_seal_authority.py` | Minimum D6 sealing-owner authority: sole sanctioned `seal_census` (owner attestation + frozen-K `planned_trial_count` anchor) | NEW |
| `tests/unit/validation/test_d6_failed_trial_census.py` | 23 adversarial D6 tests (status matrix, no-fabrication, digest binding/exclusion, K frozen, fail-closed accessors + gate, sealing authority, Evidence-Bridge-never-seals, persisted R3 artifact golden) | NEW |
| `docs/phase8.5/ledgers/*.json`, `docs/phase8.5/manifests/{manifest_census,terminal_decision,r3_manifest}*.json` | Ratified digest migration: stored `ledger_digest` recomputed under the status-binding digest rule (digest-only JSON diffs) | RATIFIED MODIFICATION |
| `src/acash/research/evidence_bridge.py`, `src/acash/backtest/*` | NOT modified (Evidence Bridge constructs records but never seals; no backtest/manifest redesign) | ⛔ |

The D5/D6 new work products of this authorization extend `docs/` + `src/` + `tests/` as listed above.
No BacktestManifest, gate-threshold, features_manifest_hash, or qualification-threshold change is made.

## 7. Verification contract (to be executed)

`uv run pytest` (full), `uv run mypy src/ tests/`, placeholder/static scan, governance
negative-authority scan, `git diff` inspection. Results appended below on completion.

## 8. Execution report (Stages 3-7) — VERIFIED

**Stage 3 — adversarial tests:** `tests/unit/research/test_oos_provenance.py` — **32 passed**
(partition canonicality/single-authority; OOS-only membership; embargo exclusion; boundary window;
determinism; no-future-leakage; contradiction fail-closed; PIT fail-closed: unverified / no
provenance / adjustment-without-proof / knowledge-unavailable / ordering-violation / missing columns /
unsupported source_kind / dataset-identity mismatch; separate fresh OOS run; OOS-manifest binding;
returns derived from OOS equity only; no-IS-equity-reuse fail-closed; INSUFFICIENT OOS observations
fail-closed; record digest determinism incl. `created_at_utc` exclusion; content-dependency).

**Stage 4 — repository verification:**
- `pytest` (full): **1967 passed, 1 skipped, 3 pre-existing warnings** (nautilus `pandas4`
  dependency warning; pydantic serializer warning from an existing intentional test) — no new
  failure, no weakened existing test.
- `mypy src/ tests/`: **no issues found in 369 source files**.
- Static scan of new code: no `TODO`/`FIXME`/`PLACEHOLDER`/`XXX`; no magic numeric floors
  (`max(1e-12, ...)`), no silent fallbacks; no default-constructed performance values.

**Stage 5 — lineage audit:** `git status` shows the ONLY new work products of this authorization are
`docs/phase14/phase14_d5_d6_ratification_record.md`, `src/acash/research/oos_provenance.py`,
`tests/unit/research/test_oos_provenance.py`. All `M`/`??` entries otherwise visible are
pre-existing ratified work from earlier phase-14 rounds. `HEAD` unchanged at `cff8960`. **No commit,
no push.** No tracked file was modified by this authorization.

**Stage 6 — negative-governance audit:** verified ABSENT — HYP_003 (none created; existing code
references are zero-authority declarations), R1 (NOT STARTED), ResearchReInceptionGate (NOT
INVOKED), Production Orchestration (absent; no new sealer authority), Phase 8.5 (no new
implementation), Alpha Qualification (not invoked), trading/broker/capital (locked / absent / $0.00),
gate thresholds / BacktestManifest digest / features_manifest_hash (unchanged), schema
(`SearchTrialRecord`/`SearchTrialLedger`; untouched pending the D6 schema decision).

**Stage 7 — readiness:** D5-A + PIT lineage are IMPLEMENTED and VERIFIED and ready for Human
Acceptance. D6 census foundations already existing and preserved in ratified form (pre-registration
K anchor `ResearchInceptionProposal.planned_trial_count`; Evidence Bridge constructs but never seals);
the failed-trial status representation is BLOCKED pending the human schema decision in
`./phase14_d6_schema_decision_request.md`. **Hard stop #1 reached: awaiting Human Acceptance.**

### Verification Ledger (final)
- Implementation Status: COMPLETE (D5-A + PIT). D6 failed-trial representation BLOCKED pending
  human schema decision (§5 + `./phase14_d6_schema_decision_request.md`).
- Contract Enforcement: STRICT FAIL-CLOSED (no magic floors, no fabricated failed-trial values, no
  schema mutation, no silent fallbacks).
- Mathematical Authority: CANONICAL SPEC (existing `SplitPolicy` + `partition_dataset_with_embargo`;
  D3 equity-return derivation; D7 canonical Sharpe; canonical serialization hashing; gate OOS minimum
  = 4).
- Local Test Suite: VERIFIED (1967 passed, 1 skipped).
- Type Checker (MyPy): VERIFIED (369 files clean).
- Remote CI Status: PENDING / NOT AVAILABLE.
- Methodological Caveats: OOS identity binding is enforced at the OOS-evidence-record layer because
  `BacktestManifest` digest redesign is forbidden. D6 failed-trial status representation is
  unresolved pending the human schema decision.

---

## 9. D6 Option A execution report (Stages 2-9, this round) — VERIFIED

**Stage 2 — schema (ratified modification):** `src/acash/validation/schema.py` implements D6
Option A exactly as ratified: 3-value `SearchTrialStatus` enum, single-authority
`SEARCH_TRIAL_EVIDENCE_FIELDS`, Optional evidence fields, status-aware before-validator
(FAILED/INVALID -> rejects all evidence + `in_sample_returns`, returns early), after-validator
`validate_status_conditional_evidence` (full evidence iff EXECUTED_SUCCESSFULLY; None evidence +
non-empty `failure_reason` otherwise), `create_declared()` factory, digest now binds per-trial
`trial_status` + `failure_reason`, and fail-closed `p_values` / `get_empirical_sharpe_mean` /
`get_empirical_sharpe_variance` over mixed censuses. `sealed_by_owner` operational metadata added;
`seal(..., sealing_owner=...)` records it; BOTH excluded from `ledger_digest`.

**Stage 2 guards (zero statistical change):** `gate.py` per-column loop adds five fail-closed
`None` guards (`rec_sharpe`, `rec_p_value`, `rec_p_value_input_hash`, `rec_manifest_id`,
`rec_series_sha256`) replacing usages; `dgp_experiments.py` adds 4 typed narrowing annotations.
Digest migration: `data/manifests/research/` copies and `docs/phase8.5/` ledgers/manifests
recomputed under the ratified digest rule (`stored == recomputed`).

**Stage 4 — D6 adversarial tests:** `tests/unit/validation/test_d6_failed_trial_census.py` —
**23 passed** (happy/golden executed + failed/invalid; boundary: forbidden evidence on FAILED/INVALID,
invalid status string, `create_declared` rejects EXECUTED + blank reason; contradictory: executed
with `failure_reason`, missing evidence, forged-replay tamper smuggling/stripping evidence; census-K
frozen, digest determinism/content-dependency/permutation, sealing-metadata exclusion; fail-closed
accessors + gate rejection on mixed census; sealing-owner authority incl. future-forward
re-seal guard + `planned_trial_count` K anchor; Evidence-Bridge NEVER seals; persisted R3 ledger
golden under the new digest).

**Stage 6 — repository verification:**
- `pytest` (full): **1990 passed, 1 skipped** (1967 baseline + 23 new D6 tests; no new failure).
- `mypy src/ tests/`: **no issues found in 371 source files**.
- Static scan of the diff: no `TODO`/`FIXME`/`PLACEHOLDER`; no magic floors introduced; only
  pre-existing out-of-scope behaviors retained (`get_empirical_sharpe_mean` empty-census `return 0.0`
  and `max(0.0, var)` — both exist in the baseline, flagged for a future human decision, NOT touched).
- `git status` audit: only the surfaces in §6 are new/modified; `HEAD` unchanged at `9037ce3`.

**Stage 7 — STOP artifact (inevitable):** `D6 STATISTICAL SEMANTICS DECISION REQUIRED`. Mixed
censuses (any FAILED/INVALID member) cannot be consumed by DSR/Holm accounting without a human
decision on how K is treated for `len(p_values)`, effective-K, and multi-gate dependence accounting.
The implementation does NOT invent replacement DSR/Holm semantics; `p_values` and the empirical
Sharpe consumers FAIL CLOSED with an explicit `DataContractError` naming this required decision.
Gate evaluation of a mixed census is therefore rejected rather than silently weakened.

**Stage 8 — negative-governance audit (this round):** verified ABSENT/UNCHANGED — HYP_003 (absent),
R1 (NOT STARTED), ResearchReInceptionGate (NOT INVOKED), Production Orchestration (only the minimum
D6 sealing-owner authority added; Evidence Bridge never seals), Phase 8.5 (no new economic
decomposition), Alpha Qualification (not invoked), trading/broker/capital (locked / absent / $0.00),
gate and qualification thresholds + `BacktestManifest` digest (unchanged),
`features_manifest_hash` (UNRESOLVED, untouched), D9 (DEFERRED).

**Stage 9 — acceptance record:** updated this record (Status, §1, §6, §9). `HEAD = 9037ce3`.
**NO COMMIT. NO PUSH.**

### D6 Verification Ledger (this round)
- Implementation Status: COMPLETE (D6 Option A implemented + verified; D5-A intact).
- Contract Enforcement: STRICT FAIL-CLOSED (status-conditional evidence, K frozen, no fabricated
  performance/`return = 0`/row removal/silent floors; mixed-census consumption fails closed).
- Mathematical Authority: CANONICAL SPEC + ratified D6 Option A (§3, §5 RESOLVED); no new
  statistical DSR/Holm accounting introduced.
- Local Test Suite: VERIFIED (1990 passed, 1 skipped).
- Type Checker (MyPy): VERIFIED (371 files clean).
- Remote CI Status: PENDING / NOT AVAILABLE.
- Methodological Caveats: mixed-census consumption remains blocked by the Stage 7
  `D6 STATISTICAL SEMANTICS DECISION REQUIRED` artifact. Pre-existing empty-census `return 0.0`
  and float-variance `max(0.0, var)` floor in the empirical accessors were NOT in scope and are
  flagged for a future human decision. `data/manifests/research/` copies are gitignored local
  artifacts kept byte-identical to the tracked `docs/phase8.5/` twins.

## 10. D6 Option A — HUMAN ACCEPTANCE (2026-09-09)

The human has explicitly ratified the following decision verbatim: **"I ACCEPT D6 Option A."**

```text
The declared/pre-registered census K remains frozen.
FAILED and INVALID trials remain members of the census.
FAILED and INVALID trials must not receive fabricated statistical evidence.
Mixed-census statistical evaluation remains fail-closed.
Final statistical semantics for DSR, Holm, and effective-K for mixed/incomplete censuses are
NOT REQUIRED FOR CURRENT OPERATION and are deferred unless a future explicit requirement requires
statistical evaluation of such a census.
The D6 sealing authority is accepted as governance-enforced, not capability-enforced.
D6 Option A is therefore ACCEPTED as the current operational governance/safety semantics.
```

**Terminology (mandatory per mandate):** this record does NOT state "final DSR/Holm/effective-K
semantics = approved". It records only:

- **"Mixed-census statistical evaluation = fail-closed."**
- **"Additional statistical methodology for evaluable mixed/incomplete censuses = not required for
  current operation; out of scope unless a future explicit requirement requires it."**

Options B/C/D/E of the statistical-semantics decision surface are **NOT selected**; no new D6
statistical methodology is created; DSR, Holm, and effective-K are **NOT modified**.

**Frozen operational semantics:**
- K = frozen declared/pre-registered census size. `FAILED ∈ census`. `INVALID ∈ census`.
- K MUST NOT silently become successful-count. Example: K = 20 (16 SUCCESS + 2 FAILED + 2 INVALID)
  ⇒ K = 20, NOT 16.
- FAILED/INVALID MUST NOT be represented as: return = 0, Sharpe = 0, p = 1, neutral return, synthetic
  evidence, imputed evidence, or zero-filled evidence.
- Operational behavior: MIXED CENSUS → NO COMPLETE STATISTICAL EVIDENCE → FAIL CLOSED.

**Acceptance scope (all verified at HEAD `649dd50`):**
- `SearchTrialStatus` model (`EXECUTED_SUCCESSFULLY / FAILED / INVALID`)
- FAILED/INVALID census membership
- Frozen K invariant
- No fabricated evidence
- Mixed-census fail-closed behavior
- Digest binding (`trial_status` + `failure_reason`)
- Evidence validation (status-conditional)
- Census sealing-owner governance mechanism
- Evidence Bridge non-sealing behavior

**Explicitly NOT authorized by this acceptance:** HYP_003 · R1 · candidate admission · statistical
research execution · paper trading · live trading · capital · broker connectivity · strategy
admission · Phase 13 Step 8.

**Sealing-authority caveat (accepted verbatim, no implementation change):**
"D6 sealing authority is governance-enforced, not capability-enforced." `SearchTrialLedger.seal()`
remains directly callable; `sealed_by_owner` is metadata/governance evidence, not a technical
capability boundary. No hardening was applied (e.g. mandatory `expected_k`, gate-side owner
verification) because none was authorized.

**D5 separation:** D6 acceptance does NOT mean D5 is fully resolved. D5 remains a separate
workstream with known follow-ups: (1) PIT attestation vs actual point-in-time availability evidence;
(2) OOS strategy actor state isolation; (3) run-level identity vs BacktestManifest identity.

**Implementation untouched:** `schema.py`, `gate.py`, `deflated_sharpe.py`, `multiple_testing.py`,
`cpcv.py`, `overfitting.py`, `census_seal_authority.py`, `evidence_bridge.py`, D6 tests, and
statistical math were NOT modified by this acceptance. This round changed documentation only.

**Phase 5 transition:** D6 acceptance closes the current D6 decision surface and the previously
deferred mixed-census methodology is demoted to a future *contingent* (only if a future explicit
requirement demands statistical evaluation of an incomplete/mixed census). The next authorized
surface — Phase 5 production research/evidence-orchestration readiness — is preflighted in
`./phase5_production_orchestration_readiness.md` (READ-ONLY; no implementation).