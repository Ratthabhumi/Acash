# CAND-FREE-MACRO-001 — Human Binding Worksheet (Decision Compression)

**Document ID:** `docs/phase14/cand_free_macro_001_human_binding_worksheet.md`

**Document status:**
```
[DECISION COMPRESSION / BINDING WORKSHEET]
[DOCUMENTATION-ONLY]
[HUMAN GOVERNANCE REQUIRED]
[EMPIRICAL VALIDATION NOT AUTHORIZED]
```

**Grounding input:** `docs/phase14/cand_free_macro_001_human_specification_decision_surface.md`
(at commit `954af2c`, HEAD = `origin/main`). No other document is reopened; no research re-run; no
audit repeat; no backtest; no literature search. `[VERIFIED FACT — this task's contract]`

---

## 1. Purpose & Scope

This worksheet compresses the canonical **22-row Human Decision Table** (D1–D22, decision surface §8)
into the **smallest practical number of Human decision rounds**, without creating new research choices,
without reopening completed feasibility, and without silently resolving any substantive gap.

Compression objective achieved:

```
22 decision dimensions
  → 5 batch-confirmable defaults        (Group A — confirm once, as a set)
  → 12 true Human-choice items          (Group B — grouped into 5 decision rounds)
  →  3 derivable items                  (Group C — computed after upstream choices)
  →  2 process/governance items         (Group D — recorded; not research choices)
```

Decisions are classified per the task mandate into four classes (A–D), and the document is structured
as sections A–G.

---

## 2. Non-Negotiable Scope Guard (unchanged from decision surface §4 / §32)

This worksheet does **NOT** authorize or perform: empirical validation, backtest, performance data
retrieval, event study, statistical test, parameter search, optimization, OOS validation, Phase 6 gate,
HYP_003 creation, ResearchReInceptionGate invocation, R1, trading, capital, broker connectivity.
`[VERIFIED FACT — task mandate; decision surface §4]`

This worksheet does **NOT** modify: candidate registry, F-1 status, HYP-003/R1 status, Phase 6 status,
trading status, or any runtime file. Documentation-only. `[VERIFIED FACT — task mandate]`

No `APPROVED` / `FROZEN` / `ACCEPTED` is written for any decision here unless that exact decision already
exists in canonical governance records. `[VERIFIED FACT — decision surface §6 mandate]`

---

## 3. Classification Key

| Class | Meaning | Action |
|-------|---------|--------|
| **A — BATCH-CONFIRMABLE DEFAULT** | Already-established reasonable default from governance material; no research debate warranted | One batch confirmation; no per-item discussion needed |
| **B — HUMAN CHOICE REQUIRED** | True research-design judgment; agent must not select | Explicit Human choice; downstream depends on it |
| **C — DERIVABLE FROM AN UPSTREAM DECISION** | Computable deterministically once upstream B/A choices are fixed | Derive; never “choose to fit results” |
| **D — NON-NEGOTIABLE GOVERNANCE CONSTRAINT / PROCESS** | Already canonical or process-only; not a candidate alpha choice | Recorded; enforced; not open for selection |

---

## A. Already Settled / Batch-Confirmable (GROUP A — confirm as a single round)

These are defaults already present in canonical material (decision surface §8 rows where the Canonical
State alternative matches the Proposed Default, or where the governance review already establishes them).
They require **one batch Human confirmation** — they do not need five separate debates. They are listed
with their canonical source. `[MODEL INFERENCE — decision surface §8; registry §95-114 reconciliation]`

| Batch ID | Dimension | Batch-confirmable value | Canonical source |
|----------|-----------|-------------------------|------------------|
| A1 | D1 Event universe | FOMC + CPI + NFP, one shared protocol | registry §100/§102; surface §9.1 |
| A2 | D2 Timestamp/timezone | Official release timestamp; primary official source; US Eastern Time (ET); archive release times at retrieval | registry §111; surface §10.1 |
| A3 | D5 Direction/hypothesis | PRIMARY = two-sided deviation; statistical/descriptive object (NOT a directional trade claim) | registry §103-104; ssrn; surface §13 |
| A4 | D6 Instrument/SPX/SPY | SPX = primary research series; SPY = robustness/implantation proxy ONLY; separate statistical vs tradability evidence | registry §106; review §310; surface §14 |
| A5 | D13 Multiple-testing semantics | Adopt ratified D6 canonical semantics: frozen census K; FAILED/INVALID remain; mixed census → FAIL CLOSED; no new DSR/Holm/effective-K introduced | ratification §10; D6 surface §A5; surface §21 |

**Batch-confirmation statement (Human fills):**
```
I confirm Group A defaults A1–A5 as the frozen starting values for CAND-FREE-MACRO-001.
[ ] A1  [ ] A2  [ ] A3  [ ] A4  [ ] A5
Decision date: ______________
```

If any A-item requires change, it is a **new Human choice** → moves to Group B and is routed to the
corresponding round.

---

## B. Decisions Requiring Human Choice (GROUP B — the only true debates, folded into 5 rounds)

12 real choices remain. They are grouped into **5 rounds** so Human answers a small decision set per
round instead of 22 individual items. Each row: decision ID as in surface §8; current canonical state;
exact alternatives already on the canonical decision surface; downstream dependents; why it must be
frozen before validation.

### ROUND 1 — Event Window + Horizon + Return Definition

| ID | Current state (surface §8) | Exact alternatives (from §11/§12) | Downstream dependents | Why freeze before validation |
|----|----------------------------|-----------------------------------|-----------------------|------------------------------|
| D3 Event window | CONFLICT C1/C2: registry §105 vs review §310 vs ssrn | W-A prev-close→event-close · W-B event-close→next-close · W-C prev-close→next-close · W-D intraday (needs intraday data; NOT available at $0 daily) | D4 return; D7 baseline; D10 grid; D18 manifest | Window is the measurement domain; every statistic is computed over it |
| D4 Return definition | Return-space ambiguity (readiness §24.10); no formula | R-CC close-to-close · R-PC prev-close→event-close · R-EC event-close→next · R-W window-return (formula depends on D3) | D12 stats; D20 PASS/FAIL; D18 manifest | Return IS the dependent variable; must be deterministic before any run |

**Round-1 rule:** D3 must be chosen first (D4's exact formula depends on it), but both are
decision **inputs to one round** — Human may answer both together. `[MODEL INFERENCE — surface §9/§11/§12]`

### ROUND 2 — Baseline + Overlap

| ID | Current state | Exact alternatives (from §15/§16) | Downstream dependents | Why freeze before validation |
|----|---------------|----------------------------------|-----------------------|------------------------------|
| D7 Baseline | "unconditioned behavior" undefined (registry §103) | B-A all non-event days · B-B matched weekday · B-C matched calendar-date · B-D event-family-specific · B-E other source-supported | D10 grid; K; D12 stats | Baseline is the counterfactual; without it the "deviation" has no reference |
| D8 Overlap/dependence | Not defined | no-double-counting principle confirmed; alternatives: allow with pre-registered rule / drop-overlapping / cluster-by-family | D10 grid; K; T_eff; D12 stats | Double-counting inflates effective sample; must be pre-registered |

### ROUND 3 — Parameter Grid + K + Statistical Protocol

| ID | Current state | Exact alternatives (from §18/§19/§20) | Downstream dependents | Why freeze before validation |
|----|---------------|----------------------------------------|-----------------------|------------------------------|
| D10 Parameter grid | No grid declared (readiness §9 AB/BD) | dimensions: event-family × window × baseline × instrument(SPX/SPY) × cost(SPY) ; sensitivity tests outside census explicitly | K (D11, derived); D12 stats; D20; D18 manifest | Grid defines the full search space; K derives from it |
| D11 K | UNRESOLVED (surface §19) | **GROUP C — derived:** K = |grid| (Cartesian product), NOT chosen by hand | D12 stats; D20 | K is the D6 multiplicity anchor; must be frozen pre-run |
| D12 Statistical protocol | Canonical D5/D6/OOS/gate primitives exist (ratified) | Adopt canonical primitives (default) vs candidate-specific event-study object (NOT in canonical gate infra) | D20; D18 manifest | Only a pre-registered protocol can be audited |

**Round-3 rule (K):** K is NOT a Human choice. Once D3/D4/D7/D8/D10 are fixed,
`K = Cartesian product of the frozen grid`. The agent derives it; Human only confirms the derivation is
correct. No "pick K = 30 or 60" debate. `[VERIFIED FACT — task mandate §16; D6 ratification §3]`

### ROUND 4 — IS/OOS + Blind Period + Cost

| ID | Current state | Exact alternatives (from §22/§23/§17) | Downstream dependents | Why freeze before validation |
|----|---------------|----------------------------------------|-----------------------|------------------------------|
| D14 IS dates | Not declared | exact IS start/end (Human-specified only; agent never selects) | D15 OOS; D16 blind; D12 stats | IS defines the estimation window |
| D15 OOS dates | Not declared; D5-A requires separate held-out Phase5 run | exact OOS start/end; min event counts per family; embargo/gap; SplitPolicy-equivalent (train .60/val .20/oos .20, embargo 5) | D12 stats; D20 | OOS integrity is the core validity claim; MUST be fixed before validation |
| D16 Blind period | Not declared | exact blind start/end; what data/metadata/diagnostics are prohibited; who accesses OOS | D20 | Blindness prevents OOS contamination |
| D9 Cost / execution | $0 (registry §109); SPY costs not modeled | SPX = research (no executable cost claim) · SPY = fixed deterministic model if included · includes/excludes from primary test | D10 grid (SPY dim); D20; D18 manifest | Hidden cost assumption would masquerade as performance |

### ROUND 5 — Kill Conditions + PASS/FAIL/INVALID Criteria

| ID | Current state | Exact alternatives (from §26/§27) | Downstream dependents | Why freeze before validation |
|----|---------------|-----------------------------------|-----------------------|------------------------------|
| D19 Kill conditions | Not declared (readiness §9 AK) | trigger × threshold × scope (global/family) × IS/OOS/both × pre/post-all-trials; canonical thresholds where cited only | D20; D18 manifest | Kill rules change census meaning if post-hoc |
| D20 PASS/FAIL/INVALID | D6 semantics canonical; candidate thresholds NOT declared | semantics preserved (PASS executed+accepted / FAIL executed-not-accepted / INVALID integrity-only, INVALID ≠ negative evidence); **thresholds = Human choice** | D12 stats; D18 manifest | Acceptance thresholds must exist before any run |

**Group-B total:** 12 items, folded into 5 rounds. This is the "true debate" set. `[MODEL INFERENCE]`

---

## C. Decisions Derivable After Upstream Choices (GROUP C — derive, do not debate)

| ID | Dimension | Derivation rule | Upstream inputs |
|----|-----------|-----------------|-----------------|
| D11 K | Trial count | `K = |Cartesian product(Grid)|` (including ALL event-family × window × baseline × instrument × SPY-cost cells; sensitivity/robustness memberships per ROUND-3 rule) | D3, D4, D7, D8, D10 |
| D17 Data vintage/archive/PIT | PIT archive artifacts | Source-archive set is deterministic from the frozen source set (S-04/S-08/S-05/S-06 primary, S-10/S-18 SPY-conditional); as-published + archive-at-retrieval + digest manifest schema | A2, A4 (source set) |
| D18 Reproducibility/manifest | Manifest binding set | Binds: candidate ID · spec version · source IDs/retrieval timestamps · event universe · timestamp convention · event window · return formula · baseline · instrument · cost · grid · K · IS/OOS/blind · statistical protocol · kill · PASS/FAIL/INVALID (surface §25.1) — schema assembled after rounds 1–5 complete | All of B + A |

Equally, any "robustness vs census membership" question inside the grid is a derivable consequence of
Rounds 3–4 choices, never a separate debate. `[MODEL INFERENCE — task mandate §16 "The final K must be
derived from the declared Cartesian grid"]`

**C-rules:**
- K is never post-hoc chosen based on favorable-result counts. `[VERIFIED FACT — D6 ratification §3]`
- No derivation is performed in this worksheet (nothing is computed); the worksheet only specifies the
  derivation rule. `[VERIFIED FACT — task mandate; §33 no-empirical]`

---

## D. Blocking Decisions (what actually blocks Pre-Registration Freeze)

Nothing blocks ROUND 1 today — this is a green path to binding. The **only** blockers to
`PRE-REGISTRATION FROZEN` are the **12 Group-B items** (rounds 1–5) plus the **batch confirmation of
Group A** and the **final anti-HARKing sign-off** (below). Group C items cannot be derived until their
upstream items are fixed, and therefore inherit the upstream blocker status.

| Blocker | Type | Unblocked by |
|---------|------|--------------|
| D3 + D4 | Group B | ROUND 1 |
| D7 + D8 | Group B | ROUND 2 |
| D10 + D12 (+ D11 derived) | Group B (+ C) | ROUND 3 |
| D14 + D15 + D16 + D9 | Group B | ROUND 4 |
| D19 + D20 | Group B | ROUND 5 |
| A1–A5 confirmation | Group A | Batch confirmation (before/with ROUND 1) |
| K (D11) | Group C | After ROUND 3 or after ROUND 4 (if SPY-cost membership affects grid) |
| Manifest/D17/D18 | Group C | After all B rounds |
| Anti-HARKing sign-off | Group D process | Final Human review of Draft Freeze Candidate |

**Anti-HARKing process requirement (Group D / process):** after rounds 1–5 are answered, do NOT
auto-freeze. Produce a **Draft Freeze Candidate**; Human reviews once: "Is there any parameter that was
chosen because we already saw the outcome?" If any → recommence binding with re-registration as a NEW
candidate (registry §195-202). If none → freeze → then authorize. `[VERIFIED FACT — task mandate;
registry §195-202]`

---

## E. Exact Dependency Graph

```
ROUND 0: A1–A5 batch confirm
            │
            ▼
ROUND 1: D3 Event Window ──► D4 Return Definition
            │                      │
            ▼                      ▼
ROUND 2: D7 Baseline ──► D8 Overlap
            │              │
            ▼              ▼
ROUND 3: D10 Parameter Grid ──► D11 K (= |Cartesian product(grid)|)
            │                            │
            └──► D12 Statistical Protocol (canonical baseline; event-study tail only if Human routes it)
                          │
                          ▼
ROUND 4: D15 OOS ──► D16 Blind ──► D14 IS ──► D9 Cost
                          │              │
                          ▼              ▼
ROUND 5: D19 Kill ──► D20 PASS/FAIL/INVALID thresholds
                          │
                          ▼
            PRE-REGISTRATION (Draft Freeze Candidate)
                          │
                          ▼
            Anti-HARKing review ──► freeze ──► D17/D18 archive+manifest ──► Human authorization ──► backtest
```

**Note on horizontal arrows:** D4 depends on D3 (return formula uses the window). D8 depends on D7
(overlap rule must respect baseline exclusions). D14/D15 are a couplet (IS/OOS boundary). D20 depends on
D19 (kill rules may define FAIL). All other arrows are strict `A → B` single-dependencies. `[MODEL
INFERENCE — surface §11/§15/§16/§17/§22/§26/§27]`

**Rounds do NOT require strict serialization across the whole chain** — rounds 4 and 5 do not depend on
round 3's *content*, only on the *freeze discipline* (nothing may change after results). Optional
parallelization is possible between rounds 1-2 (window/baseline are independent) and rounds 4-5 (cost/
IS-OOS are independent of kill/PASS-FAIL-INVALID thresholds) — but Human may prefer serial rounds. The
minimum practical Human decision count is **5 rounds + 1 batch confirmation + 1 final sign-off = 7
interactions**, down from 22. `[MODEL INFERENCE]`

---

## F. Proposed Order of Decisions (compression schedule)

| Step | Action | Content | Blocking? |
|------|--------|---------|-----------|
| 0 | Batch confirm Group A | A1–A5 (event set, timestamp/ET, two-sided, SPX/SPY split, D6 semantics) | gates Rounds 1–5 (shared defaults) |
| 1 | ROUND 1 | D3 Event Window → D4 Return Definition | gates K, stats, PASS/FAIL |
| 2 | ROUND 2 | D7 Baseline → D8 Overlap | gates grid, K, stats |
| 3 | ROUND 3 | D10 Parameter Grid → (derive D11 K) → D12 Statistical Protocol | gates K, stats |
| 4 | ROUND 4 | D15 OOS → D16 Blind → D14 IS → D9 Cost | gates acceptance |
| 5 | ROUND 5 | D19 Kill → D20 PASS/FAIL/INVALID thresholds | finalizes acceptance |
| 6 | Draft Freeze Candidate | assemble ALL bound values; no auto-freeze | anti-HARKing review |
| 7 | Final review | "any parameter chosen because we saw the outcome?" No → freeze; Yes → new candidate path | freeze gate |
| 8 | Derive Group C | D17 archive + D18 manifest + final K verification | data/manifest infra (future task) |
| 9 | Human authorization | explicit empirical-validation authorization (new, separate record) | gates backtest |
| 10 | Backtest | ONLY after authorization | — |

Steps 0–7 are decision/governance work; steps 8–10 are execution/authorization work OUTSIDE this
worksheet's scope. `[MODEL INFERENCE — surface §26/§30; D6 ratification §3/§10]`

---

## G. Final Freeze Checklist (mapped from decision surface §26)

Completion status for this worksheet: `0/26` — nothing is frozen by this document.

```
[ ] Event universe frozen                  → A1 (ROUND 0)
[ ] Timestamp source frozen                → A2 (ROUND 0)
[ ] Timezone frozen                        → A2 (ROUND 0)
[ ] Event window frozen                    → ROUND 1 (D3)
[ ] Return formula frozen                  → ROUND 1 (D4)
[ ] Direction/hypothesis frozen            → A3 (ROUND 0)
[ ] Instrument role frozen                 → A4 (ROUND 0)
[ ] Baseline frozen                        → ROUND 2 (D7)
[ ] Overlap rule frozen                    → ROUND 2 (D8)
[ ] Cost model frozen                      → ROUND 4 (D9)
[ ] Parameter grid frozen                  → ROUND 3 (D10)
[ ] K computed and frozen                  → ROUND 3 (D11, derived)
[ ] Statistical protocol frozen            → ROUND 3 (D12)
[ ] Multiple-testing semantics frozen      → A5 (ROUND 0)
[ ] IS dates frozen                        → ROUND 4 (D14)
[ ] OOS dates frozen                       → ROUND 4 (D15)
[ ] Blind dates frozen                     → ROUND 4 (D16)
[ ] PIT/data-vintage rules frozen          → GROUP C (D17)
[ ] Data archive requirement frozen        → GROUP C (D17/A2)
[ ] Manifest schema frozen                 → GROUP C (D18)
[ ] Kill conditions frozen                 → ROUND 5 (D19)
[ ] PASS criteria frozen                   → ROUND 5 (D20)
[ ] FAIL criteria frozen                   → ROUND 5 (D20)
[ ] INVALID criteria frozen                → ROUND 5 (D20)
[ ] Reproducibility requirements frozen    → GROUP C (D18)
[ ] Human authorization recorded           → Step 9 (OUTSIDE this worksheet)
```

```
Any unchecked substantive item ⇒  PRE-REGISTRATION NOT FROZEN
                                  EMPIRICAL VALIDATION NOT AUTHORIZED
```

---

## H. Governance Status (verbatim — unchanged by this worksheet)

```text
CAND-FREE-MACRO-001 = CONDITIONALLY READY
PRE-REGISTRATION = NOT FULLY FROZEN
EMPIRICAL VALIDATION = NOT AUTHORIZED
BACKTEST = NOT AUTHORIZED
```

Candidate registry status (`HUMAN_REVIEW_REQUIRED`), F-1 status, HYP-003/R1 status, Phase 6 status, and
trading status: **UNCHANGED**. No authorization granted by this worksheet. `[VERIFIED FACT — this
document's contract]`

---

## I. STOP Condition

```
STOP — CAND-FREE-MACRO-001 HUMAN BINDING WORKSHEET COMPLETE.

Current status remains:
    CAND-FREE-MACRO-001 = CONDITIONALLY READY
    PRE-REGISTRATION = NOT FULLY FROZEN
    EMPIRICAL VALIDATION = NOT AUTHORIZED
    BACKTEST = NOT AUTHORIZED

No HYP_003.
No ResearchReInceptionGate.
No R1.
No Phase 6 execution.
No trading.
No capital deployment.
Only Human Governance converts the worksheet into a frozen pre-registration.
```

---

### Verification Ledger
- Implementation Status: **COMPLETE** (documentation-only compression worksheet; no code/test change).
- Contract Enforcement: **STRICT FAIL-CLOSED** — no GROUP-B item silently resolved; no value invented; K marked derived (never hand-picked); no `APPROVED/FROZEN/ACCEPTED` written where not canonical.
- Mathematical Authority: **CANONICAL SPEC / RATIFIED RECORDS** referenced; no statistics computed.
- Local Test Suite: **NOT RUN** (docs-only).
- Type Checker (MyPy): **NOT RUN** (docs-only).
- Remote CI Status: **NOT APPLICABLE** (docs-only).
- Methodological Caveats: The compression schedule (F) and parallelization note (E) are structural
  suggestions to reduce interaction count; they do not alter any governance requirement. MINIMUM Human
  interactions = 5 decision rounds + 1 batch confirmation + 1 final anti-HARKing sign-off = 7. Nothing in
  this worksheet is an empirical result, an authorization, or a freeze.