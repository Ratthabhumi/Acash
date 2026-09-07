# ACASH - Session Handoff

> **Document:** `docs/SESSION_HANDOFF.md`
> **Status:** PHASE 14 SLICES 1-4 COMPLETE - F-1 PROPOSAL REQUIRES REVISION - GATE NOT INVOKED - HYP_003 NOT CREATED
> **Date:** 2026-09-07
> **Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Implementation Correctness != Mathematical Validity, Single Canonical Authority, Separation of Concerns)
>
> **THIS DOCUMENT IS A CONTINUATION AID. IT IS NOT A GOVERNANCE AUTHORITY.**
> A new session MUST re-read all canonical sources independently and MUST NOT treat this
> handoff as a replacement for the source documents it references.

---

## 1. CURRENT SESSION STATUS (operational)

**System is RESEARCH RE-INCEPTION READY IN PRINCIPLE, but F-1 has NOT completed human freeze.**

- Phase 14 implementation is **COMPLETE through Slice 4**. Implementation endpoint: `d6f1a67`.
- Human decision: **STOP Phase 14 implementation at Slice 4.** Slice 5: **NOT AUTHORIZED / DO NOT START.**
- F-1 candidate selected by human; first-principles review and pre-registration proposal drafts exist.
- The governance audit verdict is **PASS WITH REQUIRED FREEZES**; final recommendation is
  **B - REQUIRES PROPOSAL REVISION**.
- **The immediate next task is: revise the F-1 proposal documentation to address the audit findings,
  then re-run the governance review. Target verdict after revision: A - READY FOR HUMAN FREEZE.**
- **NO GATE. NO HYP_003. NO R1.** This is mandatory for the next session.

---

## 2. CURRENT CANONICAL STATE

```
+---------------------------------------------------------------------------------------------+
|                                    ACASH GOVERNANCE LEDGER                                   |
+-----------------------------------------------------------+---------------------------------+
| HYP_001 (EURUSD M5)                                       | TERMINALLY_FALSIFIED / CLOSED   |
| HYP_002 (EURUSD H4)                                       | TERMINALLY_FALSIFIED / CLOSED   |
| HYP_003                                                    | NOT CREATED                     |
| EURUSD_M5_HOLDOUT (2026-08-18..2026-09-04, bars 6060-9999) | QUARANTINED / PRISTINE          |
| EURUSD_H4_VALIDATION_OOS (2023-05-29..2024-12-31)          | QUARANTINED / PRISTINE          |
| Live Capital Authority                                    | $0.00 (Hard-Locked)             |
| Live Trading Authority                                    | LOCKED                          |
| Paper Trading Authority                                   | NOT AUTHORIZED                  |
| Live Trading Authorization                                | NOT AUTHORIZED                  |
| ResearchReInceptionGate                                   | NOT INVOKED                     |
| R1 (Research Inception)                                   | NOT STARTED                     |
| Hypothesis Seal                                           | NONE                            |
| Phase 14 implementation                                   | COMPLETE THROUGH SLICE 4 (d6f1a67) |
| Slice 5                                                    | NOT AUTHORIZED                  |
| F-1 Proposal Freeze                                       | NOT COMPLETE (REVISION REQUIRED) |
| System                                                     | RESEARCH RE-INCEPTION READY IN PRINCIPLE |
+-----------------------------------------------------------+---------------------------------+
```

---

## 3. REPOSITORY STATE (VERIFIED)

- Local repository: `C:\Users\Ratthabhumi\Desktop\CO-OP_Project\Acash`
- Branch: `main`
- Working tree: **CLEAN**
- **HEAD (exact):** `cff8960c7b9ee275d719e4c88a83bb18a40d3b57` (short `cff8960`)
- HEAD commit message: `docs(phase14): add F-1 first-principles review and pre-registration proposal draft`

### HEAD commit contents (documentation only)
- `docs/phase14/reviews/review_cand_flow_calendar_rebalance_001.md`
- `docs/phase14/reviews/proposal_cand_flow_calendar_rebalance_001.md`

### Commit chain (newest first, VERIFIED via `git log`)
| Commit | Message |
|---|---|
| `cff8960` | docs(phase14): add F-1 first-principles review and pre-registration proposal draft |
| `28aef5e` | docs(phase14): add research candidate discovery registry |
| `dd7bfa9` | docs(phase14): preserve quantitative research doctrine |
| `d6f1a67` | feat(phase14): implement slice4 research report generator |
| `e401716` | feat(phase14): implement slice3 exploratory feature discovery |
| `70f1f0a` | docs(phase14): preserve quantframe integration architecture reference |
| `6e995e7` | fix(phase14): harden slice2 evidence and retrieval boundaries |
| `b0d19fd` | docs(phase14): add global arbitrage research direction |
| `b2dcf5a` | docs(phase14): record prediction market ai research direction |
| `9895a3c` | feat(phase14): implement slice2 source retrieval foundation with deterministic evidence collection |
| `dcb2e64` | feat(phase14): implement slice1 research intelligence foundation |

### Remote / push status
- Remote: `https://github.com/Ratthabhumi/Acash.git`
- **IMPORTANT:** commit `cff8960` is **LOCAL-ONLY and has NOT been pushed**. Do NOT push.
- The prior QE note about `acashcrypto/acash` was already resolved: the actual remote is
  `Ratthabhumi/Acash`; commit `cff8960` exists locally on `main` and was NOT pushed.

---

## 4. PHASE 14 IMPLEMENTATION STATUS

- **COMPLETE through Slice 4.** Endpoint commit: `d6f1a67`.
- Slices covered: Slice 1 (research intelligence foundation), Slice 2 (source retrieval /
  evidence boundaries), Slice 3 (deterministic feature discovery), Slice 4 (Section 33 research
  report generator).
- **Human decision: STOP Phase 14 implementation at Slice 4.** Slice 5 is **NOT AUTHORIZED**.
- Last verified gate checks (prior sessions, reference only - re-verify if needed):
  - Full local suite last verified reference: ~1715 passed / 12 skipped (full repo), with the
    ai-directory slice4 suite passing separately. Mypy clean over the whole project at last run.
    Exact current numbers MUST be re-run by the next session before any code change.
  - 3 pre-existing warnings classified as expected behavior / dependency debt
    (Pandas4 deprecation in a tangent reference test; expected pydantic serializer warning), not
    actionable defects.

---

## 5. HYPOTHESIS LINEAGE

| Hypothesis | Market / TF | Lifecycle | Final State |
|---|---|---|---|
| `HYP_TSMOM_EURUSD_001` | EURUSD M5 | R1-R3 (0/9 qualified) -> R4-R7 early-terminated | **TERMINALLY_FALSIFIED / CLOSED / IMMUTABLE** |
| `HYP_TSMOM_EURUSD_HTF_002` | EURUSD H4 | R1-R3 (0/12 qualified) -> R4 early-terminated | **TERMINALLY_FALSIFIED / CLOSED** |
| `HYP_003` | - | - | **NOT CREATED** |

### Immutable HYP_002 digests (historical; MUST NOT be altered)
- Sealed hypothesis spec: `47c077a65f3057ae5ec83c8e7cf9179ababea9e5b18bc999bdc480a44f544afe`
- R3 Search Trial Ledger digest: `d6d627334a1560193c495947e4f9ab3a62e983ac46cba1ef4cf51a1707dd6565`
- R3 Manifest digest: `809ac530c69745924550723b19b79a7a82bd4182659f6eb2a5cfc4b019c24ccd`

---

## 6. DATA QUARANTINE STATE

Cross-Hypothesis Data Quarantine is a **HARD INVARIANT**. Protected partitions remain `PRISTINE`.

| Protected Span | Bars | Status |
|---|---|---|
| 2026 M5 Holdout (HYP_001) | 6060..9999 | `QUARANTINED / PRISTINE` |
| HYP_002 H4 Validation + Blind OOS | 3751..6230 | `QUARANTINED / PRISTINE` |

Enforced in code:
- `src/acash/research/quarantine.py` and `src/acash/research/reinception.py`,
  `PERMANENTLY_QUARANTINED_WINDOWS`:
  - `"EURUSD_M5_HOLDOUT"`: `2026-08-18T04:40:00+00:00` -> `2026-09-04T21:00:00+00:00`
  - `"EURUSD_H4_VALIDATION_OOS"`: `2023-05-29T16:00:00+00:00` -> `2024-12-31T20:00:00+00:00`
- `TERMINAL_HYPOTHESIS_REGISTRY` contains both terminal hypotheses.

F-1 (US equity index universe) is disjoint from EURUSD by construction; this must be preserved for
any future instrument choice.

---

## 7. CAPITAL / TRADING AUTHORITY

| Authority | State |
|---|---|
| Live Capital Authority | `$0.00` (Hard-Locked) |
| Trading Authority | `LOCKED` |
| Paper Trading | `NOT AUTHORIZED` |
| Live Trading | `NOT AUTHORIZED` |
| Broker Connection | `DISCONNECTED / NONE` |

Status: `VERIFIED`. No capital or trading authorization was modified.

---

## 8. F-1 CANDIDATE STATE

- **Candidate ID:** `CAND-FLOW-CALENDAR-REBALANCE-001` (NOT HYP_003)
- **Family:** Structural / Forced-Flow (calendar-forced rebalancing)
- **Selected candidate:** F-1 (human-selected)
- **First-Principles Review:** `docs/phase14/reviews/review_cand_flow_calendar_rebalance_001.md`
- **Proposal draft:** `docs/phase14/reviews/proposal_cand_flow_calendar_rebalance_001.md`
- **Proposal commit:** `cff8960` (both docs, documentation only)
- Research doctrine: `docs/phase14/research_doctrine.md`
- Candidate registry: `docs/phase14/research_candidates.md`
- Phase 14 plans: `docs/phase14/phase14_master_research_architecture_plan.md`,
  `docs/phase14/phase14_architecture_and_governance_plan.md`

---

## 9. GOVERNANCE AUDIT RESULT (most recent, this handoff's basis)

- **Overall verdict:** `PASS WITH REQUIRED FREEZES`
- **Final recommendation:** `B - REQUIRES PROPOSAL REVISION`
- **Blockers / governance blockers:** NONE (no open item is decidable only after seeing data).

### Priority finding 1 - BORROW / SHORTING MODEL (not fully frozen as written)
Canonical `CostModelConfig` fields are exactly: `quoted_spread_bps`, `roundtrip_broker_fee_bps`,
`fixed_slippage_bps`, `latency_delay_ms`. **There is NO dedicated borrow field.** The proposal
references a deletion-leg borrow cost line but does not state its canonical encoding. The encoding
MUST be explicitly frozen before R1. Governance choices identified by the audit:
- **A.** Fold borrow into `fixed_slippage_bps` as a documented conservative lump.
- **B.** Add borrow as a parameter-grid dimension, with corresponding impact on
  `grid_cardinality` (`planned_trial_count == grid_cardinality` must hold).
- **C.** Another explicitly human-approved frozen convention.
- **No post-hoc encoding.**

### Priority finding 2 - SURVIVORSHIP / CORPORATE ACTIONS (under-specified)
Top-level point-in-time principle exists, but operational conventions remain under-specified.
Before R1 the following MUST be explicitly frozen (and must NOT be chosen after looking at results):
- delisting return convention
- merger handling
- ticker-change mapping
- historical index-list versioning/source
- corporate-action date ordering
- split / corporate-action treatment

### Priority finding 3 - SPARSE-EVENT METHODOLOGY
- Audit classification: **C - correctly left unresolved as HUMAN FREEZE.**
- The review proposed `T_eff >= 25 per composite leg`, but the proposal did NOT carry that
  candidate value into the formal freeze item.
- It should be carried forward as **PROPOSED / NOT YET SEALED** for human approval or override.
- R1 must NOT resolve the sample-size method by selecting it after seeing data.

### Priority finding 4 - ECONOMIC SIGNIFICANCE (needs alignment)
Proposal currently has both:
- a cumulative-reversal threshold, and
- `min_cost_adjusted_spread_ratio >= 1.50`.

These must be aligned so the economic-significance rule is **deterministic and non-overlapping**.

---

## 10. REQUIRED HUMAN FREEZE BEFORE R1

### Original 9 freeze items (remain required)
1. **Event family** - reconstitution vs. quarterly rebalance vs. separable month-end; one family only.
2. **Universe / filters** - index spin, size band, min-ADV / free-float floor.
3. **Horizons** - final set {1, 5, 10} or alternative; primary horizon.
4. **Direction** - SHORT on the composite indicator (sign frozen).
5. **Threshold set** - exact rank IC, HAC t, autocorrelation, cost-ratio values for F-1 R1.
6. **Cost + borrow model** - exact bps stack and locate/borrow assumption.
7. **Fresh blind window** - de novo dataset window declared before any returns inspection.
8. **Complete trial grid** - full Cartesian product matching `planned_trial_count == grid_cardinality`.
9. **Formal hypothesis ID minting path** - ordinal HYP_003 minted only through the formal
   pre-registration path; never by any review/proposal document.

### Audit-added obligations (must be resolved before R1)
10. **Borrow-cost canonical encoding** (finding F-1; choice A/B/C above).
11. **Survivorship / corporate-action operational conventions** (finding F-2; full list above).
12. **Proposed sparse-event sufficiency:** `T_eff >= 25 per composite leg` carried forward as
    PROPOSED / NOT YET SEALED (finding F-3).
13. **Economic-significance alignment** (finding F-4; deterministic, non-overlapping rule).

---

## 11. FORBIDDEN CLAIMS (F-1 epistemic boundaries)

F-1 remains a **research candidate**. The mechanism is a **hypothesis, not empirical proof**.

Do NOT state that:
- the dislocation is proven
- reversal is proven
- alpha exists
- the strategy is validated
- the strategy is profitable

Use **PROPOSED / NOT PROVEN / REQUIRES HUMAN FREEZE** where appropriate.
"No empirical claim is established by this document" applies to all F-1 review documents.

---

## 12. HARD PROHIBITIONS (next session)

- Do NOT invoke `ResearchReInceptionGate`.
- Do NOT create / mint HYP_003.
- Do NOT start R1. Do NOT seal any hypothesis.
- Do NOT start Slice 5.
- Do NOT access / download / generate market data.
- Do NOT connect broker / MT5.
- Do NOT run backtests, statistical experiments, optimization, or OOS inspection.
- Do NOT modify Slice 1-4, governance gates, FrozenCore, ExecutionCoordinator, or quarantine.
- Do NOT push `cff8960` (or any commit) to the remote.
- Do NOT freeze the F-1 choices yourself; the human must freeze them.

---

## 13. IMMEDIATE NEXT TASK (for the next session)

1. **Revise the F-1 proposal documentation** (`docs/phase14/reviews/proposal_cand_flow_calendar_rebalance_001.md`)
   to address governance audit findings F-1..F-4 (sections 3, 13, 14, 15, 18, 22, 28 of the proposal).
2. **Re-run the governance review** (read-only audit).
3. **Target verdict after revision: A - READY FOR HUMAN FREEZE.**

### Strict sequence (do not skip steps)
```
PROPOSAL REVISION
    -> GOVERNANCE RE-REVIEW (TARGET A)
    -> HUMAN APPROVAL + FREEZE of the required choices
    -> ResearchReInceptionGate invocation (human-authorized)
    -> Gate success
    -> mint formal hypothesis ID through canonical path
    -> FRESH, INDEPENDENT R1
```
Do NOT skip directly to HYP_003 or R1.

---

## 14. EXACT RESUME CHECKLIST FOR NEXT SESSION

> This handoff is a continuation aid, NOT a replacement for canonical sources. Re-read everything.

### Step 1 - Read this handoff (done on open).
### Step 2 - Independently re-read canonical sources
- `AGENTS.md`
- `docs/phase14/research_doctrine.md`
- `docs/phase14/research_candidates.md` (F-1 entry)
- `docs/phase14/reviews/review_cand_flow_calendar_rebalance_001.md`
- `docs/phase14/reviews/proposal_cand_flow_calendar_rebalance_001.md`
- `src/acash/research/reinception.py`
- `src/acash/research/schema.py`
- `docs/proposals/phase_4_alpha_engine.md` (N_valid >= 250 rule, HAC policy)
- Quarantine rules in `src/acash/research/quarantine.py`
- Section 33 reporting shape in `src/acash/research/ai/reporting/`

### Step 3 - Verify repository state
```powershell
git status               # expect: working tree CLEAN
git branch --show-current # expect: main
git rev-parse HEAD        # expect: cff8960c7b9ee275d719e4c88a83bb18a40d3b57 (short cff8960)
git log --oneline -4
git remote -v             # expect: https://github.com/Ratthabhumi/Acash.git (NOT pushed)
```

### Step 4 - Verify F-1 proposal blob matches commit
```powershell
git hash-object docs/phase14/reviews/proposal_cand_flow_calendar_rebalance_001.md
git rev-parse HEAD:docs/phase14/reviews/proposal_cand_flow_calendar_rebalance_001.md
# expect: identical blob hashes
```

### Step 5 - Resume from the ACTIVE NEXT TASK
Resume from Section 13 (proposal revision / governance re-review). Do NOT infer that any pending
governance decision has been approved. All F-1 numerics remain PROPOSED / NOT YET SEALED.

---

## 15. HANDOFF SELF-VALIDATION (state at handoff time)

- HYP_003 = **NOT CREATED**
- Gate = **NOT INVOKED**
- R1 = **NOT STARTED**
- Hypothesis = **NOT SEALED**
- No market data accessed
- No broker / MT5 accessed
- No backtest run
- No statistical experiment run
- No optimization run
- No OOS inspection
- No trading implementation
- No Slice 1-4 modification
- No governance-core modification
- No FrozenCore modification
- No ExecutionCoordinator modification
- No quarantine modification
- No push to remote
- Capital: `$0.00`; Trading: **LOCKED**; Paper: **NOT AUTHORIZED**; Live: **NOT AUTHORIZED**

---

## Appendix A - Superseded Prior Handoff

The prior canonical handoff content (HYP_002 closure, Phase 14 design-pending, 2026-09-07) is
superseded for *current-state* purposes by this document. Its governance evidence (HYP_002 digests,
quarantine spans, HAC-methodology annotation, haircut-Sharpe terminology note, governance hardening
fixes) remains valid and is preserved in repository history and in `docs/phase14/` and
`docs/phase8.5/` artifacts. This supersession does not alter any sealed digest or historical result.

**System is RESEARCH RE-INCEPTION READY IN PRINCIPLE. F-1 FREEZE INCOMPLETE. HYP_003 NOT CREATED.**