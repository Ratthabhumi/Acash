# PHASE 14 — D5 OOS PROVENANCE & D6 TRIAL CENSUS — GOVERNANCE DECISION SURFACE

**Document ID:** `docs/phase14/phase14_d5_d6_decision_surface.md`
**Type:** Governance decision surface — **READ-ONLY ANALYSIS + PROPOSAL ONLY**. NOT a ratification record. NOT authorization.
**Status:** `D5 = HUMAN DECISION REQUIRED · D6 = HUMAN DECISION REQUIRED`
**Date:** 2026-09-09
**Authority:** `./AGENTS.md`, `./phase14_d8b_acceptance_record.md` (D8-B implementation ACCEPTED),
`./phase14_evidence_bridge_ratification_D1_D9.md` (D1/D2-A/D3/D4/D7/D8-B HUMAN-RATIFIED; D5/D6 NOT RATIFIED; D9 DEFERRED),
`./phase14_evidence_bridge_governance_freeze.md` (D5/D6 proposal anchors),
`./phase14_gate14_acceptance_record.md`, `./phase14_seam_b_acceptance_record.md`, `./phase14_s5_test_only_acceptance_record.md`
**Origin stage:** Continuous governance-bounded research re-entry — Stages 1–3 (read-only D5/D6 audits → ONE decision surface → Human Checkpoint #1).

> [!CAUTION]
> ### GOVERNANCE BOUNDARIES OF THIS SURFACE
> - **This document contains NO ratification.** It only records read-only evidence and a *recommended
>   proposal* for each decision. A proposal is NOT authorization.
> - **D5 and D6 are HUMAN DECISIONS REQUIRED.** They must be explicitly ratified by a human in a
>   later ratification record before ANY implementation of D5/D6 begins.
> - **Nothing below authorizes:** HYP_003; R1; ResearchReInceptionGate invocation; Production
>   Orchestration; Phase 6 execution as a new research run; Alpha Qualification; trading/broker/
>   capital; `features_manifest_hash` changes; `BacktestManifest` digest redesign; gate/qualification
>   threshold changes; silent schema migration.
> - **No source or test file was created, modified, or deleted for this surface.** Analysis is
>   read-only; all claims are anchored to repository paths/line numbers.
> - HEAD remains `cff8960`. NO COMMIT. NO PUSH.

---

## 0. Checkpoint context

```text
D8-B                  ✅ HUMAN-RATIFIED / ACCEPTED
        │
        ▼
D5 OOS Provenance     ⏳  ← THIS DECISION REQUIRED
D6 Trial Census       ⏳  ← THIS DECISION REQUIRED
        │
        ▼
HYP_003               🔒  (must remain ABSENT)
        │
        ▼
R1                    🔒  (must remain NOT STARTED)
```

Per the governing task: D5 and D6 are **governance decisions that directly affect research validity**,
so the agent must STOP here for human decision. The surface below records the read-only audit facts
(Stage 1, Stage 2) and the recommended proposal (D5-A; D6 census model). It does NOT implement.

---

## 1. STAGE 1 — D5 OOS PROVENANCE DECISION SURFACE

### 1.1 Audit anchor — what exists today (read-only facts)

| # | Area | Existing primitive / authority | Reference |
|---|---|---|---|
| D5-1 | Split policy | `SplitPolicy` (`train_pct=0.60, val_pct=0.20, oos_pct=0.20, embargo_bars=5`) | `research/schema.py:144-151` |
| D5-2 | Temporal split impl | `partition_dataset_with_embargo` → inclusive `{"TRAIN","VAL","OOS"}` ranges; embargo bodies are **unallocated buffers** (not membership); boundary purging via `is_purged_boundary` | `research/outcomes.py:115-143`, `:86-91` |
| D5-3 | Risk model connectivity | `compute_discrete_forward_returns R(t,H)=(Close[t+H]-Open[t+1])/Open[t+1]`, non-overlapping CAPM/S/OLS/HAC stats | `research/outcomes.py:21-112` |
| D5-4 | IS/OOS boundary governance | `OosExposureState` UNEXPOSED → EVALUATED_LOCKED → EXHAUSTED; OOS evaluation requires mandatory `ResearchSearchRecord` | `research/schema.py:61-63`; `research/pipeline.py:318-346` |
| D5-5 | Dataset identity (research) | `ResearchManifest` seed embeds `evaluate_oos` (`res_{hyp}_{h}h_{digest16}`); canonical hypothesis/search digest authorities | `research/pipeline.py:307-313`; `research/manifest.py:27-36` |
| D5-6 | Phase 5 backtest engine | **Partition-agnostic** — consumes an already-sorted event stream; NO OOS/partition parameter; equity per-event | `backtest/engine.py:748-760`; `backtest/schema.py:470-480` |
| D5-7 | Manifest provenance gap | `calculate_backtest_manifest_id` digests only spec-hashes/config/prng; **no partition identity**, no hypothesis_id | `backtest/schema.py:427-447` |
| D5-8 | Phase 6 gate OOS input | `evaluate_strategy(..., out_of_sample_returns=None)`; `None` or `<4` observations → `REJECT_MISSING_OOS_DATA`; OOS Sharpe = `(mean/std)*sqrt(ppy)`; retention `< min_oos_sharpe_retention_pct` (default 50%) → `REJECT_OOS_DEGRADATION`; OOS bound into `evidence_digest` via `_compute_canonical_series_sha256` | `validation/gate.py:163-171`, `:238-243`, `:589-592`, `:598-630`, `:633-643` |
| D5-9 | Return-series canonical hash | `_compute_canonical_series_sha256` (18-decimal canonical serialization + `"NONE"` for empty) | `validation/gate.py:97-108` |
| D5-10 | ValidationReport OOS fields | `out_of_sample_sharpe`, `oos_retention_pct` exist (Optional, None pre-OOS) | `validation/schema.py:998-1040` |
| D5-11 | PIT / leakage controls | **No dedicated PIT module exists.** Partial analogs: `exchange_time_utc`/`knowledge_time_utc` book-feature columns; R2 feature non-anticipation tests; embargo/purging in CPCV (`CVSplit` purged/embargoed index sets) | `data/features/hashing.py:116-117`; `tests/unit/research/test_phase8_5_r2_data_preparation.py`; `validation/schema.py:671-680` |
| D5-12 | Timeframe coordinates (documented) | `EURUSD_H4_VALIDATION_OOS=(2023-05-29T16:00:00+00:00, 2024-12-31T20:00:00+00:00)`; M5 2026 Holdout quarantined `6060..9999`; H4 `3751..4996`/`5009..6230` | `research/reinception.py:79-80,353-356`; `research/quarantine.py:130-137` |
| D5-13 | OOS test coverage | Gate-level synthetic OOS series; blind-OOS state machine; **NO test runs a Phase 5 backtest over a true OOS event segment** | `tests/unit/research/test_blind_oos_governance.py`; `tests/unit/validation/*` |

### 1.2 Recommended proposal — D5-A: Canonical OOS provenance via existing `SplitPolicy` + separate held-out Phase 5 run

**Required decision items (each must be explicitly ratified by the human):**

1. **IS/OOS separation** — OOS = the canonical `SplitPolicy` OOS partition (`(val_end+1+embargo, total_bars-1)`, inclusive semantics per `partition_dataset_with_embargo`). IS (train+validation) trials use the same canonical split, purged/embargoed exactly as the research pipeline already does.
2. **Temporal ordering** — OOS segment is strictly later in event time than IS segment; enforced by the canonical event ordering already required by the Phase 5 adapter (sorted 5-tuple keys).
3. **Boundary inclusivity/exclusivity** — embargo buffers are unallocated (never IS, never OOS); purged label windows crossing IS/OOS boundary are dropped from IS; the OOS event slice is exactly the OOS bar range.
4. **Separate OOS BacktestManifest** — a fresh Phase 5 run (fresh runner instance, `initial_cash` reset, fresh ledger) over ONLY the OOS event segment produces its own `BacktestManifest` + OOS equity table. **No sharing of IS runner/ledger state.**
5. **Separate OOS return series** — derived from the OOS equity table with the same D3 rule; must satisfy the gate's minimum (`≥ 4` finite observations); annualized with the same D4 `periods_per_year`.
6. **OOS identity binding** — `BacktestManifest` digest redesign is FORBIDDEN, so partition identity is bound OUTSIDE the manifest digest: (a) canonical OOS segment data hash (existing data-layer canonical hashing authorities), (b) OOS return series `_compute_canonical_series_sha256`, (c) `ResearchManifest` seed that already embeds `evaluate_oos` + `ResearchGovernanceLedger` state transition. Report difference: **Phase 5 manifest_id itself cannot distinguish IS vs OOS by design**; a dedicated OOS-run record (segment hash + OOS series hash + manifest_id + retention artifacts) is the identity carrier.
7. **Prevention of IS→OOS contamination** — OOS events never appear in IS runs; OOS evaluation single-use only; feature generation remains causal (no look-ahead); no PIT window reuse.
8. **No reuse of IS equity as OOS** — the OOS equity table is produced by the separate OOS run; the Evidence Bridge must never feed IS equity into OOS.
9. **No future leakage** — OOS partition is defined and sealed before IS evaluation completes; no data beyond the OOS slice is consumed by the OOS run.
10. **Single-use held-out provenance** — reuse the existing `OosExposureState` + `ResearchSearchRecord` machinery: OOS exhausts on first evaluation.

**Existing-primitive differences reported (not invented):**
- The Phase 5 engine has NO partition concept — the OOS event slice is a caller-side concern (fits the frozen engine surface).
- `calculate_backtest_manifest_id` excludes partition identity → OOS identity MUST live in a dedicated OOS-run record, never by redesigning the digest.
- The gate already accepts an OOS series parameter but has NO producer — D5-A adds the producer + provenance contract, not gate changes.
- No PIT module exists. PIT/causal controls are today only partial (book feature knowledge-time columns + R2 non-anticipation tests + embargo/purging). **D5 ratification must decide whether PIT lineage is in-scope for D5 implementation or tracked as a separate seam.**

### 1.3 D5 status

> `D5 = HUMAN DECISION REQUIRED` — **NOT RATIFIED.** No implementation performed.

---

## 2. STAGE 2 — D6 TRIAL CENSUS DECISION SURFACE

### 2.1 Audit anchor — what exists today (read-only facts)

| # | Area | Existing primitive / authority | Reference |
|---|---|---|---|
| D6-1 | Trial record | `SearchTrialRecord`: trial_id, strategy_id, hypothesis_id, feature_names (sorted tuple), parameters (deep-frozen), in_sample_sharpe, p_value, p_value_method, p_value_input_hash, in_sample_return_series_sha256, config_sha256, execution_manifest_id | `validation/schema.py:70-106` |
| D6-2 | Single-authority materialization | `SearchTrialRecord.create(...)` — p-value derived canonically from returns (tolerance `1e-6`), trial-id hash, config hash | `validation/schema.py:260-338` |
| D6-3 | Ledger construction | `SearchTrialLedger` — trials is a **non-empty tuple**; `add()`/`register()` do NOT exist; census = construction-time tuple (INSERTION ORDER preserved) | `validation/schema.py:343-372` |
| D6-4 | Duplicate rejection | Duplicate trial_ids → `DataContractError`; per-trial strategy_id & hypothesis_id must equal ledger identity | `validation/schema.py:434-455` |
| D6-5 | Sealing | `seal()` computes `ledger_digest` (= pure content identity; sealing timestamp EXCLUDED) and sets `is_sealed=True`; sealed+missing digest / digest mismatch both `DataContractError` | `validation/schema.py:388-432`, `:456-468` |
| D6-6 | K definition | `total_trials = len(trials)` — census K is the full ledger trial count | `validation/schema.py:475-478` |
| D6-7 | Gate census dependency | Gate REFUSES unsealed ledgers; verifies `ledger_digest` before validation; K = ledger size (`block_search` does NOT exist repo-wide) | `validation/gate.py:343-356`, `:402-412` |
| D6-8 | Deterministic trial ordering | `trial_matrix_column_trial_ids` must EXACTLY equal ordered ledger trial_ids; column 0 = primary = `ledger.trials[0]` | `validation/gate.py:401-412` |
| D6-9 | Digest ordering sensitivity | `compute_ledger_digest` serializes trials IN PROVIDED ORDER (NOT sorted by trial_id) → digest is order-sensitive | `validation/schema.py:396-415` |
| D6-10 | Per-trial gate lineage proofs | matrix col ↔ return-series hash; config hash; p-value + hash; manifest-in-store; manifest `strategy_config_hash == config_sha256`; manifest sharpe (non-None) within `epsilon_sr`; hypothesis identity | `validation/gate.py:414-524` |
| D6-11 | Perturbation grid (separate concept) | `ParameterPerturbationGrid`: base value + `[0.75,1.0,1.25]` sharpe profile + 3 run_ids/manifest_ids/hash bindings — **does NOT participate in census K** | `validation/schema.py:~584-640`; `validation/overfitting.py:156+` |
| D6-12 | DSR K semantics | Selection correction consumes effective/dsr K (`SINGLE_TRIAL` K=1 special-case); multiple testing K = `len(p_values)` | `validation/deflated_sharpe.py:389-450`; `validation/multiple_testing.py:46-47,84-85` |
| D6-13 | Blind-window pre-registration | **ABSENT** in validation layer. Research counterpart exists only as hypothesis grid cardinality at re-inception | `research/reinception.py:155-173` |
| D6-14 | Failed/crashed trial representation | **ABSENT** — no NaN/invalid-trial representation in `SearchTrialRecord`; gate-failing trials remain in census, but crashed/unevaluated runs have NO representation convention | `validation/schema.py` (no failure-state field) |
| D6-15 | Bridge construction authority | Evidence Bridge materializes records via `SearchTrialRecord.create` but NEVER seals (D8-B) | `research/evidence_bridge.py:137-146`, docstring `:13-16` |

### 2.2 Recommended proposal — D6: Census Ownership & Pre-Registration (mirrors freeze-doc D6, expanded)

**Required decision items (each must be explicitly ratified by the human):**

1. **Who owns census K** — K = the pre-registered blind census of trials bound to the hypothesis (`|trials|`), declared BEFORE any backtest evaluation of those trials. The human must ratify the census owner explicitly (recommended: the production research orchestrator, whose ledger construction authority is explicit; the Evidence Bridge may construct records but is NEVER the census owner or sealer).
2. **When K is frozen** — K freezes (ledger sealed) BEFORE blind evaluation / before any Phase 6 gate invocation; post-seal insertion is prohibited by schema and must additionally be prevented by construction-window rules.
3. **Deterministic trial ordering** — registration order IS the canonical order (digest is order-sensitive); primary trial = index 0 must be designated pre-registration (not chosen post-hoc from results).
4. **Trial identity** — trial_id uniqueness enforced at construction + gate; config/return/p-value/execution lineage proven per column by the gate; all preserved unchanged.
5. **Failed trials** — every registered trial remains in the census (gate-failing trials currently do). **The human must ratify the convention for crashed/unevaluated runs**: recommended = represent failures truthfully in the census under the pre-registered failure rule (e.g., a recorded-but-failed marker) so census K is not silently reduced by attrition. This convention is a decision, not something to invent at implementation time.
6. **Invalid trials** — invalid (non-canonical) trials fail closed at materialization; they do NOT enter the census under valid identities.
7. **Duplicate trials** — rejected at ledger construction (`DataContractError`), unchanged.
8. **Blind-window registration** — census declared pre-evaluation; the re-inception grid cardinality (`research/reinception.py:155-173`) is the existing research-side anchor the census must reconcile with.
9. **Ledger construction** — full census tuple assembled from pre-registered trials, in canonical order, before sealing.
10. **Ledger sealing authority** — the production orchestrator is the SOLE sealer (`SearchTrialLedger.seal`, once per hypothesis); the bridge never seals.
11. **Trial-return matrix alignment** — n_is equal across columns (already enforced by Evidence Bridge); columns order-locked to the ledger (gate `:401-412`).
12. **Prevention of post-hoc trial insertion** — sealed ledger + schema invariants; construction-window freeze before evaluation.

**Existing vs absent classification:**
- **EXISTS (preserved unchanged):** record materialization authority, tuple immutability, duplicate rejection, sealed+digest invariant, digest tamper detection, gate census-K derivation, per-column cryptographic lineage, matrix↔ledger order binding, primary-at-index-0 check.
- **ABSENT (requires the D6 decision):** census pre-registration artifact/owner, census-K freeze timing orchestration, failure-representation convention for crashed runs, construction window before seal.

### 2.3 D6 status

> `D6 = HUMAN DECISION REQUIRED` — **NOT RATIFIED.** No implementation performed.

---

## 3. STAGE 3 — HUMAN CHECKPOINT #1 (STOP HERE)

**The following HUMAN DECISIONS are required (verbatim):**

```text
DECISION 1 — D5 OOS PROVENANCE
  Choose:  D5-A  = Canonical OOS provenance via existing SplitPolicy + separate held-out Phase 5 run
           (recommended proposal, enumerated in §1.2)
       OR  the human-specified alternative.
  Also decide: whether PIT lineage control is IN-SCOPE for D5 implementation
       (open item §1.2.10) or a separate seam.

DECISION 2 — D6 TRIAL CENSUS OWNERSHIP
  Choose:  Census model per §2.2 (pre-registered K; freeze-before-evaluation; deterministic
           registration order; failed trials remain represented per a ratified failure rule;
           production orchestrator = sole sealer; bridge constructs but never seals)
       OR  the human-specified alternative.
  Also decide: the crash/failure representation convention (§2.2 item 5).
```

- **No D5/D6 implementation was performed.**
- **No HYP_003 was created.**
- **No R1 was started.**
- **No ResearchReInceptionGate was invoked.**
- **HEAD = `cff8960`. NO COMMIT. NO PUSH.**

---

## 4. Invariant matrix (verified after this surface was written)

| Invariant | State |
|---|---|
| D5 | NOT RATIFIED / HUMAN DECISION REQUIRED |
| D6 | NOT RATIFIED / HUMAN DECISION REQUIRED |
| D9 | DEFERRED |
| D8-B (implementation) | HUMAN-RATIFIED / ACCEPTED |
| D1/D2-A/D3/D4/D7 | HUMAN-RATIFIED |
| HYP_003 | ABSENT |
| R1 | NOT STARTED |
| ResearchReInceptionGate | NOT INVOKED |
| Production Orchestration | ABSENT |
| Phase 6 gate thresholds / semantics | UNCHANGED |
| `BacktestManifest` digest semantics | UNCHANGED |
| Qualification logic | UNCHANGED |
| `features_manifest_hash` | UNRESOLVED |
| Trading / Capital / Broker | LOCKED / $0.00 / NO AUTHORITY |
| Source/test mutation (by this surface) | NONE |
| Commit / push | NONE |

---

## 5. RESUME RULE (for the next human-ratified instruction)

When a human supplies ratified D5/D6 decisions, resume from THIS checkpoint: implement ONLY the ratified
contracts (Stage 4), verify (Stage 5), stop at acceptance (Stage 6), then D8-B-seal the HYP_003
preparation audit (Stage 7). Do NOT repeat this read-only analysis unless the ratification changes
the chosen option.

### Verification Ledger
- Implementation Status: COMPLETE (read-only decision surface; nothing modified)
- Contract Enforcement: N/A (no changes made)
- Mathematical Authority: N/A (audit facts anchored to source; proposals explicitly marked NOT ratified)
- Local Test Suite: NOT RUN (read-only stage; prior state: 1935 passed, 1 skipped)
- Type Checker (MyPy): NOT RUN (read-only stage; prior state: 367 files clean)
- Remote CI Status: PENDING / NOT AVAILABLE
- Methodological Caveats: This is the OUTPUT OF STAGES 1–3 ONLY (Human Checkpoint #1). All D5/D6 content is proposal, not authorization. The manifest_id digest cannot carry partition identity BY DESIGN (forbidden to redesign), so OOS identity binding is proposed at the OOS-run record + research-manifest layer. PIT module does not exist; partial analogs only. Census failure-representation and PIT in-scope are open human decisions, deliberately NOT resolved here. No source/test change; HEAD `cff8960`; no commit/push.