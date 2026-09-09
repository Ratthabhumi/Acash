# PHASE 14 — D5/D6 HUMAN-RATIFIED FREEZE & IMPLEMENTATION RECORD

**Document ID:** `docs/phase14/phase14_d5_d6_ratification_record.md`
**Type:** Governance acceptance/freeze record (ONE record for this authorization).
**Status:** `D5 = HUMAN-RATIFIED · PIT LINEAGE IN D5 SCOPE · D6 = HUMAN-RATIFIED`
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
D5                        = HUMAN-RATIFIED   (this record)
D6                        = HUMAN-RATIFIED   (this record)
D9                        = DEFERRED
HYP_003                    = ABSENT
R1                         = NOT STARTED
ResearchReInceptionGate    = NOT INVOKED
Production Orchestration   = ABSENT
Trading                    = LOCKED
Capital                    = $0.00
features_manifest_hash    = UNRESOLVED
HEAD                        = cff8960
NO COMMIT / NO PUSH
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
- D5 (Stage 1) is NOT blocked by this finding and is implemented under this record per §2.

## 6. Implementation surfaces created under this record

| File | Purpose | Status |
|---|---|---|
| `src/acash/research/oos_provenance.py` | D5-A canonical OOS provenance: partition re-use, OOS event segment extraction, separate held-out OOS run, OOS evidence record, PIT attestation + fail-closed lineage verification | NEW |
| `tests/unit/research/test_oos_provenance.py` | Adversarial D5 tests (separation, identity, boundaries, no IS-equity reuse, PIT fail-closed, determinism, gate-consumability) | NEW |
| `docs/phase14/phase14_d6_schema_decision_request.md` | Minimum schema decision request for the D6 failed-trial invariant (STOP artifact) | NEW |
| `src/acash/validation/schema.py`, `validation/gate.py`, `research/evidence_bridge.py`, `backtest/*` | NOT modified under this record | ⛔ |

No existing source or test is modified by this authorization. No schema, gate, bridge, engine, or
manifest change is made.

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