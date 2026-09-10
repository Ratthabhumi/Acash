# ACASH — Evidence Bridge Human-Ratified Freeze & Option-B Implementation Authorization: D1–D9

**Document ID:** `docs/phase14/phase14_evidence_bridge_ratification_D1_D9.md`
**Type:** Governance acceptance / freeze record — HUMAN-RATIFIED decisions for the contiguous phase
(Evidence Bridge Freeze → Option B Implementation → Verification → Audit) authorized by this task.
**Status:** `[HUMAN-RATIFIED]` for D1, D2, D3, D4, D7, D8-B · `[NOT RATIFIED]` for D5, D6 · `[DEFERRED]` for D9.
**Date:** 2026-09-09
**Mode:** CONTINUOUS EXECUTION WITH GOVERNANCE CHECKPOINTS — bounded continuation of the already-audited Phase 14 Evidence Bridge work.
**Related:** [`docs/AGENTS.md`](../AGENTS.md), [`docs/ROADMAP.md`](../ROADMAP.md),
[`docs/phase14/phase14_evidence_bridge_governance_freeze.md`](phase14_evidence_bridge_governance_freeze.md),
[`docs/phase14/phase14_gate14_acceptance_record.md`](phase14_gate14_acceptance_record.md),
[`docs/phase14/phase14_seam_b_acceptance_record.md`](phase14_seam_b_acceptance_record.md),
[`docs/phase14/phase14_s5_test_only_acceptance_record.md`](phase14_s5_test_only_acceptance_record.md),
[`docs/phase14/phase14_master_research_architecture_plan.md`](phase14_master_research_architecture_plan.md),
`docs/phase14/phase14_ratification_record_D1_D4.md`.

> [!CAUTION]
> ### GOVERNANCE BOUNDARIES OF THIS TASK
> - **This record ratifies ONLY the explicitly stated human decisions below. Do NOT infer additional authority.**
> - Do NOT create HYP_003. Do NOT start R1. Do NOT invoke ResearchReInceptionGate.
> - Do NOT connect brokers. Do NOT place orders. Do NOT change capital state.
> - Do NOT implement Production Orchestration. Do NOT implement Phase 8.5 economic decomposition.
> - Do NOT modify `features_manifest_hash`. Do NOT modify Phase 6 gate semantics. Do NOT modify AlphaQualificationGate semantics.
> - D5, D6 remain `[NOT RATIFIED]`; D9 remains `[DEFERRED]`. No recommendation is elevated by this record.
> - `features_manifest_hash` remains `[UNRESOLVED] / SEPARATE GOVERNANCE SURFACE` and is NOT resolved here.
> - This task ends at the final verification/audit report. **NO COMMIT. NO PUSH.**

---

## 0. Classification Discipline

| Tag | Meaning |
|---|---|
| `[HUMAN-RATIFIED]` | Human approval explicitly supplied for this task. Recorded verbatim. |
| `[NOT RATIFIED]` | Explicitly excluded from this task's ratification; remains a future human decision. |
| `[DEFERRED]` | Recognized as a separate future seam; no action now. |
| `[UNRESOLVED]` | Open item with no binding; no canonical authority assigned. |
| `[EXISTING]` | Pre-existing repository behavior/state. |

Rules:
- Each ratified decision is marked `[HUMAN-RATIFIED]` with its exact ratified meaning.
- No recommendation is accidentally represented as a ratification.
- D8 authorization is limited to **Option B exactly** as enumerated in §8.

---

## 1. Ratified Decision D1 — Seam A (Option A) ACCEPTED

> `[HUMAN-RATIFIED]` **D1 = Option A — ACCEPT.**
>
> Meaning:
> - `EventBacktestRunner.run_backtest` requires an explicit `hypothesis_id`.
> - `NautilusTraderSubstrate.run_simulation` requires an explicit `hypothesis_id`.
> - The exact upstream `hypothesis_id` is propagated into `BacktestManifest`.
> - No placeholder hypothesis identity is permitted. No default `hypothesis_id`. No auto-generated `hypothesis_id`.
>
> The already-implemented Seam A changes are accepted as the intended Phase 5 provenance behavior.

## 2. Ratified Decision D2 — Canonical Return Series (D2-A)

> `[HUMAN-RATIFIED]` **D2 = A — Accounting / equity-implied return series.**
>
> The canonical Phase 5 → Phase 6 return series MUST be derived from the canonical
> equity/accounting series rather than signal × forward-return reconstruction.
> The return series is a property of realized accounting/equity evolution from the backtest output.
> Signal-based forward-return reconstruction is NOT introduced as an alternative canonical path.

## 3. Ratified Decision D3 — Return Derivation Rule (frozen)

> `[HUMAN-RATIFIED]` **D3 = freeze deterministic equity simple return per bar:**
>
>     r_t = E_t / E_(t-1) - 1
>
> Frozen semantics (verbatim intent):
> - observations are ordered deterministically by canonical event timestamp and the existing
>   canonical tie-break/order semantics;
> - the first observation has no return and is excluded from the return series;
> - duplicate observations must not be silently collapsed;
> - missing observations are not imputed;
> - non-finite equity values fail closed;
> - non-finite derived returns fail closed;
> - zero or invalid denominator fails closed;
> - negative/invalid equity states fail closed according to existing canonical accounting validity rules;
> - zero-variance return series fail closed for Sharpe computation;
> - insufficient observations fail closed;
> - no future padding; no interpolation; no look-ahead;
> - no resampling rule may be silently introduced.
>
> The implementation MUST document exactly which existing Phase 5 equity column/table is authoritative.
> If the source contains ambiguity that materially changes these semantics, STOP and report the ambiguity
> rather than inventing behavior.

**Authoritative Phase 5 equity column (documented per the ratified mandate):** the canonical equity
curve table (`CANONICAL_EQUITY_CURVE_SCHEMA` in `src/acash/backtest/schema.py`) column **`total_equity`**
(balance-sheet equity). The existing canonical accounting validity rules referenced by D3 are the
**double-entry balance-sheet equity conservation invariant** enforced by `ShadowAccountingLedger`
(`src/acash/backtest/accounting.py`). No source ambiguity that materially changes these semantics was found
during the audit; the implementation therefore proceeds.

## 4. Ratified Decision D4 — Annualization Authority

> `[HUMAN-RATIFIED]` **D4 = `ValidationConfig.periods_per_year` is the sole annualization authority.**
>
> - No other annualization configuration is created.
> - Unsupported or undefined annualization fails closed.
> - The canonical Sharpe calculation uses the frozen `periods_per_year` value supplied through `ValidationConfig`.

## 5. Ratified Decision D7 — Sharpe Authority (with safety invariant)

> `[HUMAN-RATIFIED]` **D7 = canonical pure Sharpe function as the single source of truth.**
>
> Preferred location: `src/acash/validation/deflated_sharpe.py`.
> The canonical function MUST be behaviorally equivalent to the existing Phase 6 Sharpe mathematics:
> - arithmetic mean;
> - sample standard deviation with `ddof=1`;
> - annualization by `sqrt(periods_per_year)`;
> - `std <= 1e-12` ⇒ fail closed;
> - non-finite input ⇒ fail closed;
> - invalid `periods_per_year` ⇒ fail closed.
>
> **Safety invariant:** `canonical_sharpe(series, periods_per_year)` must be behaviorally equivalent to
> current Phase 6 gate verification math within `epsilon_sr = 0.001`.
>
> **IMPORTANT:** Do **NOT** modify Phase 6 gate semantics. Instead:
> 1. implement the canonical pure calculation;
> 2. prove behavioral equivalence against the current gate formula;
> 3. refactor only internal duplicated arithmetic to call the canonical function **if appropriate**
>    while preserving externally observable gate behavior;
> 4. tests must explicitly demonstrate equivalence.
>
> Do NOT alter gate thresholds, acceptance criteria, or governance semantics.

## 6. Ratified Decision D8 — First Implementation Scope (D8-B)

> `[HUMAN-RATIFIED]` **D8 = B — Evidence assembly + Phase 5 Sharpe emission.**
>
> AUTHORIZED IMPLEMENTATION SCOPE:
> - **A.** Implement the minimal Evidence Bridge capability required to assemble truthful Phase 6
>   evidence inputs from already-produced Phase 5 outputs.
> - **B.** Emit a truthful Phase 5 `execution_summary.sharpe_ratio` using the frozen canonical return
>   series and annualization authority.
> - **C.** Add deterministic tests for the evidence assembly and Sharpe emission.
> - **D.** Preserve identity/hash/lineage invariants.
> - **E.** Keep the implementation pure/deterministic wherever possible.

## 7. NOT AUTHORIZED IN THIS SLICE (D8-B)

The following are explicitly NOT authorized:
- OOS orchestration
- production end-to-end orchestrator
- Phase 8.5 integration
- `AlphaEconomicDecomposition` producer
- `SearchTrialLedger` production orchestration/sealing
- CPCV execution
- perturbation-run orchestration
- live/paper trading
- HYP_003
- R1
- ResearchReInceptionGate
- broker integration
- `features_manifest_hash`
- schema redesign
- gate redesign
- qualification redesign

## 8. Not Ratified / Deferred Decisions

- **D5 — OOS Provenance:** `[NOT RATIFIED]`. Remains a future human decision.
- **D6 — Census Ownership:** `[NOT RATIFIED]`. Remains a future human decision.
- **D9 — Economic Decomposition:** `[DEFERRED]`. Separate future seam. Must NOT be silently absorbed
  into the D8-B Evidence Bridge implementation.

---

## 9. Authorized Source / Test Scope

**Preferred allowed source scope:**
- `src/acash/backtest/engine.py`
- `src/acash/backtest/nautilus_bridge.py`
- `src/acash/validation/deflated_sharpe.py`
- `src/acash/research/evidence_bridge.py` (new file if the existing architecture supports this placement)

**Tests** may be added/updated in the corresponding unit/integration test locations.

**Do NOT modify unrelated modules. Do NOT redesign `BacktestManifest`. Do NOT change
`BacktestManifest.manifest_id` semantics unless absolutely required by an already-frozen invariant
(if such a change appears necessary, STOP and report it).**

**Do NOT touch:**
- Phase 6 gate thresholds/semantics
- Phase 8.5 qualification logic
- ResearchReInceptionGate
- HYP registry
- R1
- trading/broker code
- `features_manifest_hash` schema
- portfolio lifecycle governance

---

## 10. Lineage Invariant Chain (D8-B)

```
Phase 5 hypothesis identity
        ↓
BacktestManifest.hypothesis_id
        ↓
canonical return series (D2-A / D3)
        ↓
execution_summary.sharpe_ratio (D7 canonical authority, D4 annualization)
        ↓
Phase 6-compatible evidence
```

Where the existing architecture already requires hash/identity binding, those bindings are preserved.
Do NOT fabricate evidence. Do NOT use placeholder values. Do NOT silently substitute synthetic data
in production code. Do NOT silently derive OOS evidence from IS evidence.

---

## 11. Verified Governance State at Task Start (before implementation)

- Gate 14 = ACCEPTED · Seam B = ACCEPTED · S5 = ACCEPTED · Seam A Option A = IMPLEMENTED (pending task ratification)
- HYP_001 = TERMINALLY FALSIFIED · HYP_002 = TERMINALLY FALSIFIED · HYP_003 = ABSENT
- R1 = NOT STARTED · ResearchReInceptionGate = NOT INVOKED
- Production Orchestration = ABSENT · Evidence Bridge = NOT IMPLEMENTED
- Trading = LOCKED · Capital = $0.00
- `features_manifest_hash` = UNRESOLVED
- Manifest identity digest (`calculate_backtest_manifest_id`) excludes `hypothesis_id` from the digest
  inputs and MUST remain unchanged.

---

## 12. Final Required Governance State (at task end)

```
Gate 14                  = ACCEPTED
Seam B                   = ACCEPTED
S5                       = ACCEPTED
Seam A Option A          = HUMAN-RATIFIED
D2                       = HUMAN-RATIFIED
D3                       = HUMAN-RATIFIED
D4                       = HUMAN-RATIFIED
D7                       = HUMAN-RATIFIED
D8-B                     = HUMAN-RATIFIED / IMPLEMENTATION AUTHORIZED

D5                       = NOT RATIFIED
D6                       = NOT RATIFIED
D9                       = DEFERRED

Evidence Bridge          = D8-B IMPLEMENTED
Production Orchestration = ABSENT
HYP_003                  = ABSENT
R1                       = NOT STARTED
ResearchReInceptionGate  = NOT INVOKED
Trading                  = LOCKED
Capital                  = $0.00
features_manifest_hash   = UNRESOLVED

NO COMMIT
NO PUSH
```