# D6 Statistical Semantics — Decision Surface & D6 Acceptance Readiness

**Status:** `[DECISION SURFACE]` · `[NON-IMPLEMENTING]` · `[HUMAN RATIFICATION REQUIRED]`

**Document ID:** `docs/phase14/d6_statistical_semantics_decision_surface.md`

**Audited HEAD:** `649dd50b7f0f83d0a733a43d2b33a91252527219` (`649dd50`)
**Audited parent:** `9037ce3a34edd4eb87bd6e90365ab8f1d52825c2` (`9037ce3`)

> **This document does not authorize implementation.**
>
> **Passing tests do not constitute human acceptance.**
>
> **D6 sealing authority is governance-enforced, not capability-enforced.**
>
> **K remains the frozen declared census unless and until a human-ratified governance decision
> explicitly changes the semantics.**
>
> **FAILED/INVALID trials must not receive fabricated statistical evidence.**

This task was **READ-ONLY analysis + documentation only**. No source, test, schema, registry, gate,
threshold, or statistical implementation was modified. No decision is made on behalf of the human.

---

## 1. Purpose

Two distinct outputs requested by the human:

1. **Part A — D6 Option A acceptance-readiness audit:** determine whether the D6 Option A
   implementation at `649dd50` matches the human-ratified semantics, from **source inspection**,
   not from test reports.
2. **Part B — D6 statistical semantics decision surface:** expose, for a human decision, how
   FAILED/INVALID trials should interact with DSR, Holm, effective-K, and multiple-testing when K
   stays frozen to the declared census. **No option is chosen here.**

**D6 Acceptance ≠ statistical-semantics choice.** Accepting the D6 implementation and choosing how
mixed censuses enter DSR/Holm/effective-K are **separate governance decisions** and require separate
human ratification.

---

## 2. Method & Scope

Sources inspected at HEAD (line references are to `649dd50`):

| Component | File | Covered |
|---|---|---|
| Status model, record, ledger, digest, accessors, sealing | `src/acash/validation/schema.py` | A1, A2, A4, A5, A6 |
| Sealing-owner authority | `src/acash/research/census_seal_authority.py` | A6 |
| Gate orchestrator, effective-K, matrix coupling | `src/acash/validation/gate.py` | A2, A5, A9, B3, B6 |
| DSR engine | `src/acash/validation/deflated_sharpe.py` | A9, B3, B5 |
| Holm / BH / Haircut engine | `src/acash/validation/multiple_testing.py` | A9, B4, B5 |
| CPCV/CSCV, PBO engines | `src/acash/validation/cpcv.py`, `src/acash/validation/overfitting.py` | A9, B6 |
| Evidence Bridge | `src/acash/research/evidence_bridge.py` | A7 |
| D6 adversarial tests | `tests/unit/validation/test_d6_failed_trial_census.py` | A10 |
| D5 provenance (status only) | `src/acash/research/oos_provenance.py`, Phase 14 records | Part C |
| Persisted Phase 8.5 artifacts | `docs/phase8.5/ledgers/*.json`, `docs/phase8.5/manifests/*.json` | A8 |
| Governance records | `docs/phase14/*.md` (D5/D6, D8-B, Seam A/B) | Context, unchanged |

The D6 commit surface (`git show 649dd50 --stat`) touched only: the ratification/decision/ledger
JSON artifacts, `schema.py`, `gate.py`, `dgp_experiments.py`, `census_seal_authority.py`, and tests.
No statistical engine file (`deflated_sharpe.py`, `multiple_testing.py`, `cpcv.py`,
`overfitting.py`) appears in the D6 diff (verified: zero-diff).

---

## PART A — D6 OPTION A ACCEPTANCE READINESS AUDIT

### A1. Status model

Source: `schema.py:67-103` (`SearchTrialStatus`), `:104-163` (fields), `:264-397` (validators),
`:472-520` (`create_declared`).

| Status | Evidence allowed | Evidence required | `failure_reason` | `in_sample_returns` |
|---|---|---|---|---|
| `EXECUTED_SUCCESSFULLY` | Yes | All evidence fields: `in_sample_sharpe`, `p_value`, `p_value_input_hash`, `in_sample_return_series_sha256`, `execution_manifest_id`. `config_sha256` (census identity) always mandatory. | MUST be `None` | Allowed as `create()` input only (raw series is NOT stored; only its sha256 + derived p-value); on direct construction, either `in_sample_returns` or an explicit verified `p_value` + series-sha is required |
| `FAILED` | No | None (all evidence fields `None`); `config_sha256` still mandatory | MUST be non-empty | Forbidden (rejected by before-validator) |
| `INVALID` | No | None (as `FAILED`) | MUST be non-empty | Forbidden |

**Verification:** the status-aware before-validator (`schema.py:287-316`) rejects any supplied
evidence field or `in_sample_returns` on non-executed trials; the after-validator
`validate_status_conditional_evidence` (`schema.py:355-397`) requires full evidence iff
`EXECUTED_SUCCESSFULLY`, requires `failure_reason == None` for executed and a non-empty deterministic
`failure_reason` for FAILED/INVALID, and rejects any evidence on FAILED/INVALID. Status is exactly 3
values — no other status can be constructed (`schema.py:283-297` parses and rejects unknown
strings). **FAILED/INVALID cannot carry fabricated statistical evidence.**

### A2. Census K invariant

- `total_trials` = `len(trials)` (census K, `schema.py:668-671`); no accessor recomputes K from
  evidence-bearing records only.
- Ledger uniqueness validator enforces `K == |unique trial_id|` (`schema.py:630-636`).
- Gate: `effective_k = trial_ledger.total_trials` (`gate.py:364`), then **strict coupling**
  `K_ledger == |unique ids| == |p_values| == K_DSR == K_Holm == K_BH == K_Haircut == M_CPCV`
  (`gate.py:362-374`); mismatches are hard `DataContractError` raises.
- Global scan for `effective_k / successful_count / executed_count / valid_count /
  len(successful) / evidence_bearing / census_size` found **no location** that substitutes the
  successful-trial count for K. The only clustering is `len(p_values)` (gate invariant) and
  `total_trials` (schema, gate, DSR). No silent K-shrink path exists.
- `PASS` — no code computes K from only evidence-bearing records.

### A3. No fabricated evidence

- Source scan for `return = 0 / sharpe = 0 / synthetic / neutral / placeholder / fabricat`
  found only **reject-message and docstring negations** (e.g. `schema.py:287-298`,
  `oos_provenance.py:482`); no fabrication logic in `src/`.
- Evidence fields are `Optional` but status-guarded: `None` on non-executed is enforced (not a
  "nullable = neutral" escape); executed trials require all fields (no partial evidence).
- No NaN-replacement / zero-filled / default-performance path was found; gate per-column guards
  (`gate.py:420-449`) raise on any `None` evidence member.
- `PASS` — no implicit or explicit fabrication, including via defaults/optional fields.

### A4. Digest binding

`compute_ledger_digest()` (`schema.py:571-602`) binds per trial: `trial_id`, `config_sha256`,
`in_sample_return_series_sha256`, `execution_manifest_id`, `in_sample_sharpe`, `p_value`,
`p_value_method`, `p_value_input_hash`, **`trial_status`**, **`failure_reason`**. Ledger-level:
`ledger_id`, `strategy_id`, `hypothesis_id`, `sharpe_space`.

- Same content → same digest (test: `test_mixed_census_keeps_k_frozen_and_digest_binds_status`).
- Status mutation (`FAILED`→`INVALID`) → digest changes (same test).
- `failure_reason` mutation → digest changes (same test).
- Order permutation → digest changes (order-locked identity; same test).
- Operational metadata (`sealed_at_utc`, `sealed_by_owner`) excluded — `test_sealing_metadata_excluded_from_ledger_digest`.
- `PASS` — the digest binds all fields that define trial meaning, including status and reason.

### A5. Mixed-census behavior

Conceptual example audited: **K = 10 = 8 EXECUTED_SUCCESSFULLY + 1 FAILED + 1 INVALID.**
Source-traced behavior:

| Capability | Outcome (verified from source) | Mechanism |
|---|---|---|
| `p_values` retrieval | **Fails closed** — `DataContractError` | `schema.py:733-744` → `_assert_census_evidence` raises on first non-executed member (`schema.py:680-687`) |
| Empirical mean | **Fails closed** — `DataContractError` | `schema.py:717-730` |
| Empirical variance | **Fails closed** — `DataContractError` | `schema.py:695-715` |
| DSR via gate | **Blocked** — `DataContractError` before DSR | gate: `len(trial_ledger.p_values) != effective_k` (`gate.py:370`) precedes DSR call (`gate.py:565`) |
| DSR direct (`evaluate_dsr(trial_ledger=...)`) | **Fails closed** | `declared_k = total_trials` (`deflated_sharpe.py:498`); `use_empirical_trial_mean` → mean raises; `declared_k >= 2` always pulls variance (`deflated_sharpe.py:513-514`) → raises |
| Holm | **Fails closed** | p-value family mandatory; `K = len(p_values)` and `declared_k != K` → error (`multiple_testing.py:227-237`); p_values accessor raises first |
| Effective-K | Computable as census K (10) but **unusable**: `len(p_values) != effective_k` hard-fails | `gate.py:364-371` |
| ValidationReport | **Not produced** — hard `DataContractError` propagates | gate raises on K/p-values invariants; only missing-input conditions (`REJECT_MISSING_*`, `gate.py:236-335`) produce reports |
| Trial matrix | **Blocked**: gate requires `M == K` (10 columns) and rectangular `(T, 10)` | `gate.py:376-390`; a mixed census has only 8 truthful evidence columns — no truthful rectangular 10-column matrix exists |

**Verified baseline:** *mixed census → statistical semantics unresolved → fail closed.* No
option/implementation chosen.

### A6. Sealing authority (exact caveat)

Source: `census_seal_authority.py:32-63`, `schema.py:605-625`.

- `SearchTrialCensusSealAuthority.seal_census()` accepts **`expected_k: Optional[int] = None`**
  (`census_seal_authority.py:36`). When provided it enforces `total_trials == expected_k`
  (`:46-52`); when **omitted, no K anchor is bound**.
- `SearchTrialLedger.seal()` remains **directly callable** by any caller (`schema.py:605`); its
  `sealing_owner` is a recorded metadata string, not a verified credential.
- The authority stamps `sealed_by_owner = "ACASH_D6_CENSUS_AUTHORITY"` and post-checks the recorded
  value (`census_seal_authority.py:54-62`), but the gate **does not** verify `sealed_by_owner` at
  consumption time (`gate.py:342-357` checks only sealed state + digest).
- **Accurate characterization, recorded verbatim for governance:**

> **D6 sealing authority is governance-enforced / convention-enforced, supported by the designated
> authority and static/audit controls, but NOT capability-enforced at the object/API boundary.**

This is intentionally **not** described as cryptographically exclusive, and was **not** changed.
Follow-up hardening (e.g. mandatory `expected_k`, gate-level owner verification, or capability
bounding) requires a separate human decision.

### A7. Evidence Bridge

`evidence_bridge.py` (verified, all 181 lines): constructs `SearchTrialRecord`s via `create()`
(`:137-146`), enforces manifest/Sharpe lineage (`:104-134`), returns **equal-length rectangular**
matrix contract (`:155-172`), assembles evidence only. **It cannot seal** (no `.seal(` anywhere;
static test `test_evidence_bridge_never_seals`), cannot mutate a frozen census (stateless assembly,
frozen models), and cannot fabricate evidence (records derived from manifests + canonical returns
under lineage checks). `PASS`.

### A8. Persisted artifacts

- `docs/phase8.5/ledgers/*.json`, `manifest_census_*, terminal_decision_*,
  r3_manifest_*`: the D6 commit changed **only the `ledger_digest` lines** (verified JSON diffs
  are digest-only).
- **Why digests changed:** the ratified digest rule now binds `trial_status` + `failure_reason` per
  trial. The persisted R3 artifacts carry neither field, so on load they default to
  `EXECUTED_SUCCESSFULLY` / `None` (backward-compatible; `schema.py:114-127`) and the stored digest
  was recomputed under the extended rule so `stored == recomputed` holds (`schema.py:656-661`
  sealed-digest validator would otherwise reject them).
- Semantic identity is unchanged (all persisted trials are executed; no status/reason was invented).
- Schema/digest/status compatibility verified by `test_persisted_r3_ledger_remains_valid_under_new_digest`
  and the Phase 8.5 R3 census suite (7/7). No fabrication introduced. `PASS`.

### A9. Statistical math preservation

`git diff 9037ce3..649dd50 --stat` for `deflated_sharpe.py`, `multiple_testing.py`, `cpcv.py`,
`overfitting.py` = **empty**. D6 diff against `schema.py` shows no `ValidationConfig` field,
threshold, period, or alpha change (zero diff on those symbols). D6 changes are
**TYPE / VALIDATION / FAIL-CLOSED GUARDS** only:

- `gate.py:420-449` — five `None` guards narrowing `Optional` evidence (then identical values flow
  into the pre-existing math). The `len(p_values)` / matrix / digest invariants are unchanged
  conditions, now automatically fail-closed for mixed censuses.
- `schema.py` — additive status model + guarded accessors; existing DSR/Holm formulas untouched.
- `PASS` — no mathematical change; if any is ever introduced it must be reported as a governance
  issue.

### A10. Test evidence

Inspected `tests/unit/validation/test_d6_failed_trial_census.py`: **21 test functions, 23 collected**
(one parametrized ×3). Coverage: status matrix (construct + prohibit/require per status), factory
positive/negative, invalid-status string, forged-replay tamper (add evidence to FAILED; strip
evidence from EXECUTED; retroactive `failure_reason`), K-frozen census, digest determinism /
content-dependency / permutation, sealing-metadata exclusion, fail-closed accessors (mean, variance,
p_values) on mixed census, gate rejection of mixed census, sealing authority (owner stamp, K-anchor
mismatch, refusal of other-owner-sealed census), Evidence-Bridge-never-seals static audit, persisted
R3 golden. Regression suites (`test_statistical_validation_gate.py`, `test_phase8_5_r3_census.py`,
`test_dgp_methodology_experiments.py`, `test_oos_provenance.py`) all still pass.

Reproducible in this environment earlier today against this working tree: **full `pytest` 1990 passed /
1 skipped** (1967 pre-D6 + 23 D6), **mypy src/ tests/ 371 files clean**.

---

## PART B — D6 STATISTICAL SEMANTICS DECISION SURFACE

### B1. Required principle (preserved, not chosen)

- `K_frozen` = declared / pre-registered census size. **Never** silently redefine as successful count.
- No fabricated evidence for failed/invalid trials.
- Any statistical treatment must explicitly distinguish: **census membership**, **statistical
  evidence availability**, **multiplicity**, **successful execution**, **failure/invalidity**.

### B2. Candidate option families (analyzed — NOT selected)

**OPTION A — FAIL CLOSED ON MIXED CENSUS** (current behavior)
- Definition: if any declared trial lacks valid statistical evidence, evaluation requiring the
  complete census is blocked.
- Governance consequence: strongest protection of frozen-K; no silent redefinition; requires a
  separate human decision before any mixed census is evaluated.
- Statistical consequence: no DSR/Holm/effective-K output for mixed censuses; statistically
  conservative; censuses are either fully evidence-bearing or not evaluable.
- Operational consequence: mixed censuses (e.g. K=10 with a FAILED trial) cannot proceed to
  validation until the census is completed/resolved (rerun decision) or a ratified semantics applies.
- Unresolved requirements: none internally; the open question is when/how a failed trial is resolved
  (rerun identity — see B7 Q8-Q10).

**OPTION B — FROZEN K WITH EVIDENCE SUBSET**
- Definition: K remains `K_census` in the declared family; estimators use only evidence-bearing
  trials; `K_census` vs `K_evidence` made explicit.
- Governance consequence: requires explicit human ratification of a new `K_evidence` distinction;
  risks ambiguity between census and multiplicity unless `K` usage is renamed per consumer.
- Statistical consequence: DSR's EVT SR0 uses `K_census` while empirical mean/variance use
  `K_evidence` — **incoherence risk**: the ACASH gate currently enforces
  `len(p_values) == effective_k` (`multiple_testing.py:227-237`, `gate.py:370`), so Option B would
  require **changing that coupling**. DSR SR0 (Bailey & López de Prado 2014) is defined over the
  tested-trials multiplicity; mixing families needs formal grounding.
- Operational consequence: per-consumer K provenance (DSR vs Holm vs BH vs haircut) must be
  explicitly tracked in result records.
- Unresolved requirements: formal literature grounding for using `K_census` with `K_evidence`
  p-values; changes to gate/engine invariants (a governance item).

**OPTION C — DECLARED K + EXPLICIT NON-EXECUTION SEMANTICS**
- Definition: failed/invalid trials remain in multiplicity `K` but receive an explicit statistical
  treatment defined by a **pre-ratified method** rather than fabricated values — e.g.
  missingness-aware multiple testing, incomplete/censored execution methodology, pre-registered
  failure handling. **Conceptually only; no mathematical implementation is invented here.**
- Governance consequence: highest rigor; but requires a formal methodology decision and literature
  validation before implementation.
- Statistical consequence: would preserve frozen K as multiplicity while handling missing evidence
  in a principled way; depends entirely on the chosen method.
- Operational consequence: requires a methodological review milestone and new engine surface.
- Unresolved requirements: **formal statistical literature / methodological review is required**
  before any concrete formula is adopted.

**OPTION D — EXECUTION-ONLY K**
- Definition: use only executed-successfully trials as statistical multiplicity.
- Governance consequence: **effectively redefines K = successful count**, contradicting the
  ratified frozen-census invariant. Not compatible with current ratified D6 without an explicit
  constitutional change.
- Statistical consequence: reduces the multiple-testing family, lowering the SR0/holmenm burden —
  an anti-conservative bias relative to declared trials.
- Operational consequence: simplest, but invalidates the census-K accounting already sealed in the
  Phase 8.5 lineage.
- Unresolved requirements: a human decision whether frozen K is a census invariant or a
  multiplicity invariant (B7 Q1) and whether the D6 ratification is being amended.

**OPTION E — TWO-STAGE / SEPARATE CENSUS**
- Definition: separate `declared census` from `statistical evaluation census` with an explicit
  governance transition (a second pre-registered census).
- Governance consequence: requires pre-registration of the evaluation census before evaluation; a
  new trial-family/census artifact; must not be post-hoc (would violate the "no post-hoc insertion"
  rule).
- Statistical consequence: multiplicity becomes the evaluation-census count; DSR/Holm families are
  internally coherent per census.
- Operational consequence: equivalent to opening a new research round (governance transition,
  re-registration, new manifest/census artifacts).
- Unresolved requirements: whether post-failure reruns form a second census or amend the first
  (B7 Q8-Q10); interaction with the R3 lineage already recorded.

### B3. DSR-specific findings (grounded in source)

- **What DSR consumes:** the **primary candidate's return series** only (`deflated_sharpe.py:531`),
  plus trial **mean/variance summaries** and **K**. It does NOT consume the full trial matrix or a
  p-value family. The full matrix feeds CPCV/PBO and per-column lineage checks, not DSR itself.
- **Literal K interpretation:** when passed a `trial_ledger`, `declared_k = trial_ledger.total_trials`
  and `k_for_dsr = declared_k` (`deflated_sharpe.py:497-499`). K = **declared census**, not
  successful count.
- **K enters the SR0 correction:** `compute_expected_max_sharpe_sr0(dsr_trials_k=k_for_dsr, ...)`
  (`:539-543`); increasing declared K monotonically raises the EVT selection hurdle
  (`:461-466`). Missing trials that increase K therefore penalize DSR via SR0 — a key semantic
  question (B7 Q5).
- **Can DSR accommodate missing trials mathematically?** Not as a family: trials enter via mean/
  variance, and both fail closed on non-executed members (`schema.py:680-687`); declared_k>=2
  always pulls variance (`deflated_sharpe.py:513-514`). DSR **does not require a rectangular
  matrix** (that is a gate/CPCV requirement), but it does require coherent trial summaries.
- **Incomplete matrix:** matrix/census coupling is enforced at the gate (`gate.py:376-390`); DSR
  primitives never see the matrix.

### B4. Holm-specific findings (grounded in source)

- **Multiplicity family = the p-value vector** passed in; `K = len(p_values)`
  (`multiple_testing.py:46,84,233`); Holm multiplier `(K - i + 1)` for the i-th ordered p-value.
- **Strict coupling:** `declared_k != K` → `DataContractError` (`multiple_testing.py:227-237`);
  gate passes `effective_k` (census K) and `trial_ledger.p_values` (`gate.py:577-586`).
- **Under frozen-K semantics, FAILED/INVALID cannot be absent from the p-value family** while the
  gate requires `len(p_values) == K` — excluding them would (a) reduce the family and (b) trip the
  length invariant. Excluding failed trials **does change multiplicity** → inconsistent with frozen
  K unless a ratified Option B/C/E redefines the family.
- So "would excluding them effectively reduce multiplicity?" → **yes, and current source forbids
  the inconsistency**; the decision (B7 Q6) must resolve which multiplicity Holm uses.

### B5. Effective-K map (each meaning, explicitly)

| Meaning | Where | Represents |
|---|---|---|
| `effective_k` (gate) | `gate.py:364` | **Census K** = `total_trials`; coupling anchor for matrix M, unique ids, p-values, DSR-K, Holm-K, BH-K, haircut-K, CPCV-M (comment `gate.py:363`) |
| `declared_k` / `k_for_dsr` (DSR) | `deflated_sharpe.py:497-499` | **Declared census K** (from ledger) |
| DSR canonical `K_eff` | `deflated_sharpe.py:459-464` and parameter `effective_independent_trials_k` (`:452`) | **Effective number of independent trials** (Bailey & López de Prado 2014); parameter exists but is **not wired from the gate** — defaults unset => not applied in the pipeline |
| Holm/BH/haircut `K` | `multiple_testing.py:46,84,227-237` | **len(p_values)**, must equal declared `dsr_trials_k` under current contract |
| Result record `effective_trials_k` | `schema.py:948,1050`; `multiple_testing.py:287` | Legacy alias of `dsr_trials_k` = K of the evaluated p-value family |

**Ambiguity flagged:** "effective K" is overloaded. In all *activated* paths it equals census K; the
truly independent-trial concept (DSR K_eff) exists as a named parameter but is not applied. The
human decision must pin one canonical definition (B7 Q7).

### B6. Trial matrix assumptions

- The gate **assumes every declared trial has a return series**: rectangular `(T, M)` with
  `M == K`, `T == n_is`, column 0 hashing to `in_sample_returns`, and ordered column ids == ledger
  ids (`gate.py:376-412`).
- `evidence_bridge.assemble_phase_six_evidence` likewise enforces **equal-length rectangular**
  construction (`evidence_bridge.py:155-172`).
- Under a mixed census there is no truthful rectangular matrix (missing columns for FAILED/INVALID).
  **Current behavior:** fail closed at the gate (`gate.py:382` for M mismatch; `:370` for p-values
  mismatch, whichever first). No code path assumes partial/non-rectangular matrices.

### B7. Governance questions (for the human; NOT answered here)

1. Is frozen K a multiplicity invariant or merely a census invariant?
2. Does failed/invalid membership remain part of the multiple-testing family?
3. Can statistical evaluation proceed with incomplete evidence?
4. If yes, what exact statistical methodology authorizes it?
5. Does DSR use `K_census` or another explicitly defined multiplicity?
6. Does Holm use `K_census`, p-value family size, or another defined multiplicity?
7. What exactly does "effective K" mean in ACASH (one canonical definition)?
8. Does a new execution after failure remain the same pre-registered trial or become a new trial?
9. Can a failed trial be rerun without changing the pre-registered census?
10. Does replacing a FAILED/INVALID trial with a successful rerun preserve trial identity and
    digest semantics?
11. When is a census considered complete?
12. Who has authority to declare the census complete?
13. What evidence is sufficient to transition from *incomplete census* to *statistically evaluable
    census*?
14. Must the chosen semantics be frozen before any HYP_003/R1 work?

---

## PART C — D5 SEPARATE STATUS CHECK (context only)

D5 (OOS provenance, D5-A + PIT lineage) was human-accepted in the prior round and is recorded in
`docs/phase14/phase14_d5_d6_ratification_record.md`. **D6 acceptance does not depend on D5 being
fully proven**; these are separate surfaces with no source-level dependency D5 → D6 found.

Known D5 follow-up surfaces, preserved **separately** (NOT addressed here):

1. **PIT attestation vs actual PIT-availability proof:** the module enforces fail-closed internal
   consistency of `PitLineageAttestation` (`oos_provenance.py:63-140`), but an attestation is a
   self-declared claim with provenance — independent proof of actual point-in-time availability
   requires external data-source evidence and is a separate decision.
2. **OOS strategy actor state isolation:** OOS uses a separate fresh held-out run; actor state
   isolation across the IS/OOS boundary is a runtime-discipline surface, tracked separately.
3. **Run-level identity vs BacktestManifest identity:** OOS identity is bound at the
   OOS-evidence-record layer because `BacktestManifest` digest redesign is forbidden — a documented
   boundary (recorded in the D5/D6 record verification caveats).

Do **not** let these contaminate D6 acceptance unless a direct dependency is later shown by source.

---

## PART D — ACCEPTANCE DECISION MATRIX

| Area | Evidence | Status | Human Decision? |
|---|---|---|---|
| Status model | §A1; exactly 3 values; evidence prohibited on FAILED/INVALID; `failure_reason` enforced | PASS | YES |
| Frozen K | §A2; `total_trials` only; no successful-count substitution anywhere | PASS | YES |
| No fabricated evidence | §A3; no fabrication/default/NaN/zero-fill paths | PASS | YES |
| Digest binding | §A4; binds identity+status+reason; metadata excluded; mutation→different digest | PASS | YES |
| Mixed census | §A5; all consumers fail closed, verified per capability | PASS | YES |
| Sealing authority | §A6; governance-enforced, NOT capability-enforced; `expected_k` optional; `ledger.seal()` public | CONDITIONAL | YES |
| Evidence Bridge | §A7; constructs only; never seals; cannot fabricate | PASS | YES |
| Persisted artifacts | §A8; digest-only migration, semantics unchanged, recompute-consistent | PASS | YES |
| Statistical math unchanged | §A9; DSR/Holm/BH/CPCV/PBO zero-diff; only guards added | PASS | YES |
| Tests | §A10; 23 D6 tests, adversarial; 1990/1 full; mypy 371 clean | PASS | YES |

**D6 TECHNICAL STATUS:** `[IMPLEMENTED + VERIFIED]`

**D6 HUMAN ACCEPTANCE:** `[PENDING]`

No explicit human ratification of D6 acceptance exists in the repository attributable to this task;
technical verification does **not** constitute governance acceptance.

---

## 3. Documentation-task verification

After producing this document (`git status`):
- Files changed: **exactly one new file** — `docs/phase14/d6_statistical_semantics_decision_surface.md`.
  (The pre-existing `docs/phase14/acash_market_research_ontology_v1.md` remains an untracked artifact
  from the prior human-approved ontology round; it is not part of this task.)
- No `src/`, `tests/`, registry, acceptance record, `ROADMAP.md`, or statistical file changed.
- No `HYP_003` created; no `R1` started; no gate changed; no trading/capital authorized.
- No commit, no push.

---

STOP — D6 ACCEPTANCE READINESS AND STATISTICAL SEMANTICS DECISION SURFACE COMPLETE.
HUMAN RATIFICATION REQUIRED. NO IMPLEMENTATION AUTHORIZED.