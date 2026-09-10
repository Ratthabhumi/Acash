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

## J. Recorded Human Decisions (ROUND 0 - ROUND 3B)

Authority: **HUMAN GOVERNANCE** (recorded verbatim from Human's explicit statements on 2026-09-10; the agent
transcribes decisions only and does not fabricate any signature, date, or approval. These are binding
decisions toward pre-registration; none of them individually constitutes a full freeze or an empirical
authorization.)

### ROUND 0 - Group A batch confirmation: CONFIRMED

```
CONFIRM ROUND 0 - A1-A5
```

| Batch ID | Dimension | Confirmed value (frozen starting value) |
|----------|-----------|------------------------------------------|
| A1 | D1 Event universe | FOMC + CPI + NFP, one shared protocol |
| A2 | D2 Timestamp/timezone | Official release timestamp; primary official source; US Eastern Time (ET); archive release times at retrieval |
| A3 | D5 Direction/hypothesis | PRIMARY = two-sided deviation; statistical/descriptive object (NOT a directional trade claim) |
| A4 | D6 Instrument | SPX = primary research series; SPY = robustness/implantation proxy ONLY; separate statistical vs tradability evidence |
| A5 | D13 Multiple-testing semantics | Adopt ratified D6 canonical semantics: frozen census K; FAILED/INVALID remain; mixed census -> FAIL CLOSED; no new DSR/Holm/effective-K |

### ROUND 1 - D3 Event Window + D4 Return Definition

- **D3 = W-B** — event-day close -> next trading-day close (post-event window).
  Human rationale: W-A contains pre-announcement movement; W-C mixes pre + post mechanisms; W-D is
  conceptually best for event-time identification but intraday data is unavailable at $0 daily granularity.
- **D4 = R-EC** — `R_event = Close(next) / Close(event) - 1` (1-day post-event return).
- **BINDING CAVEAT (Human):** W-B/R-EC measures the **post-event next-trading-day response**, NOT an
  immediate announcement reaction. Pre-registration MUST describe the object as post-event
  next-trading-day response; it must NEVER be labeled "announcement-day return" or "immediate market
  reaction", because the intraday announcement interval is not directly observed in daily data.

### ROUND 2 - D7 Baseline + D8 Overlap

- **D7 = B-A** — All non-event trading days.
  Baseline return: `Close(t) -> Close(next)` over non-event trading days (same 1-trading-day horizon as the
  event return, per W-B).
  Purge rule: event day + next trading day (window-adjacent per W-B) are excluded from the baseline so no
  control observation sits inside an event window.
- **D8 = O-2** — Drop overlapping event windows (later event dropped by chronological event timestamp).
  Human rationale: O-1 would allow stacked observations needing an aggregation/tie policy (extra
  specification complexity); O-3 treats cluster-by-family as an inference/dependence treatment, not an
  observation-selection rule.
- **Deterministic rule required:** when event windows overlap, apply O-2 and drop the later event in event
  timestamp order. **Tie-break rule for equal timestamps MUST be pre-registered before validation** and
  must NOT be chosen after seeing data.
- **No double-counting CONFIRMED:** "No double-counting without an explicit pre-registered rule."
- **BINDING CAVEAT (Human):** O-2 reduces the overlapping-observation problem; it does NOT imply IID.
  Residual temporal dependence (e.g., FOMC events across quarters) and common market conditions across
  macro events remain. Inference/cluster/HAC treatment is deferred to ROUND 3.

### ROUND 3A - Parameter Grid (D10) + K Derivation (D11)

Human confirmed ROUND 3A as a single batch (no re-confirmation requested):

| Dim | Decision | Confirmed value |
|-----|----------|-----------------|
| G-1 | Grid structure | **G-1a crossed single grid** — `EventFamily = {FOMC, CPI, NFP}` one shared protocol |
| G-2 | Window | **G-2a W-B only** — `Window = {W-B}` single primary window; no robustness windows in the grid |
| G-3 | Baseline | **G-3a purge = event-day + next-trading-day only** — `Baseline = {B-A}` no extra buffer |
| G-4 | Instrument | **G-4b** — SPX = formal primary in census; SPY = robustness OUTSIDE formal K |
| G-5 | Cost | **SKIP -> ROUND 4 (D9)** — not decided now |
| G-6 | Robustness membership | **G-6b** — robustness entries OUTSIDE formal census |
| G-7 | Sensitivity | **G-7a** — sensitivity outside formal census, declared pre-run |

**K DERIVATION (D11, derived — never hand-picked):**

Frozen formal grid `CensusGrid = EventFamily (x) Window (x) Baseline (x) Instrument_in_census`:

```
EventFamily = {FOMC, CPI, NFP}   -> 3
Window      = {W-B}              -> 1
Baseline    = {B-A}              -> 1
Instrument  = {SPX}              -> 1   (SPY robustness OUTSIDE formal census)
Cost_SPY    = {}                 -> deferred (not in census this round)
```

```
K = |CensusGrid| = 3 (x) 1 (x) 1 (x) 1 = 3 DECLARED GRID CELLS
```

- K is the **size of the frozen declared census** (grid-cell trial count), NOT the number of realized
  events/observations. `[VERIFIED FACT — ratification record §10; D6 surface §A5; surface §19]`
- Declared cells (each a trial on the sealed census):
  1. `FOMC / W-B / B-A / SPX`
  2. `CPI  / W-B / B-A / SPX`
  3. `NFP  / W-B / B-A / SPX`
- D6 ratified semantics (unchanged): `EXECUTED_SUCCESSFULLY`, `FAILED`, `INVALID` all remain census
  members; K does not silently shrink to the success count; FAILED/INVALID are never imputed (no return=0 /
  Sharpe=0 / p=1 / synthetic); mixed census -> statistical evaluation FAILS CLOSED; no new DSR/Holm/
  effective-K semantics added. `[VERIFIED FACT — ratification record §10; D6 surface §A5]`
- Verbatim caveat from rationale: "Do NOT confuse K with number of realized events/observations" — the
  per-cell realized observation count is a separate empirical quantity to be recorded at run time, not
  part of the sealed K.

### ROUND 3B - Statistical Protocol (D12) - CONFIRMED DECISIONS

Human confirmed the following ROUND 3B decisions as a batch (S-2 and S-9 NOT confirmed yet):

| S# | Item | Confirmed value |
|----|------|-----------------|
| S-1 | Statistical object | **(a) Event-study object** — two-sided post-event deviation vs baseline; NOT forced into canonical Phase-5 Sharpe machinery |
| S-3 | Null hypothesis | `H0: E[D] = 0` vs `H1: E[D] != 0` (two-sided deviation) |
| S-4 | Sidedness | **(b) two-sided test + descriptive sign only** (sign is descriptive, NOT tradable) |
| S-5 | Clustering unit | **(c) Family x calendar** (two-way cluster: event family + time block) |
| S-6 | HAC / dependence | **(a) Cluster-robust SE** (by S-5 unit); O-2 does NOT imply IID — residual dependence addressed here |
| S-7 | T_eff | **(c) post-O-2 T_eff** — formula MUST be pre-registered (open: see current decision surface; not yet bound) |
| S-8 | Missing observations | **(b) shift per W-B + (c) INVALID fail-closed**; imputation (0/neutral/p=1/SUCCESS) PROHIBITED |
| S-10 | Inference sample | **IS-based inference**; exact IS/OOS dates deferred to ROUND 4 |
| S-11 | Gate-6 machinery | **(b) ratified D6 subset** — census + fail-closed + two-sided test; NO new DSR/Holm/PBO/CPCV/effective-K |

Blinding reminder: `S-2` (test statistic) and `S-9` (minimum sample size) remain
`HUMAN DECISION REQUIRED` — NOT recorded as confirmed.

### Status after ROUNDS 0-3B

- Recorded: A1-A5 confirmed; D3 = W-B; D4 = R-EC; D7 = B-A; D8 = O-2; no-double-counting confirmed;
  G-1a/G-2a/G-3a/G-4b/G-6b/G-7a confirmed; G-5 deferred to ROUND 4; S-1(a)/S-3/S-4(b)/S-5(c)/S-6(a)/
  S-7(c direction)/S-8(b+c)/S-10(IS-based)/S-11(b) confirmed; S-2 + S-9 formula + S-9 minimum UNRESOLVED.
- **K = 3 declared grid cells** (derived from the frozen Cartesian grid, per D6/D11).
- Freeze checklist: **Parameter grid (D10), K (D11), Statistical protocol (D12) are now BOUND but still
  counted `0/26 FROZEN`** — binding recorded here is not the Draft Freeze Candidate; full freeze occurs
  after all rounds + Group C + anti-HARKing review.
- PRE-REGISTRATION = **NOT FULLY FROZEN**; EMPIRICAL VALIDATION = **NOT AUTHORIZED**; BACKTEST = **NOT
  AUTHORIZED**.
- Candidate registry, F-1, HYP_003, R1, Phase 5/6, trading/capital: **UNCHANGED**.

---

## K. CONTINUATION AUDIT — S-2 / S-7 / S-9 CHECKOUT (2026-09-10)

**Object:** Continuation of MACRO-001 specification work from the ROUNDS 0-3B state, resolving all
derivable/non-Human specification work around S-2, S-7, S-9, then evaluating the Round 4 entry
condition. Documentation-only; no empirical work, no data retrieval, no download, no statistics.
`[VERIFIED FACT — this section's contract]`

**Status classification:**
```
[DOCUMENTATION-ONLY]
[NON-EMPIRICAL]
[NON-AUTHORIZING]
[RESEARCH CHECKPOINT - NOT A FREEZE, NOT AN AUTHORIZATION]
```

### K.1 MEC-0011 Closeout Verification (Phase A)

- `docs/phase14/mec_0011_research_audit_closeout.md` present and classified
  `[RESEARCH CHECKPOINT]` `[SOURCE / PROVENANCE AUDIT]` `[NON-AUTHORIZATION RECORD]`. `[VERIFIED FACT]`
- MEC-0011 status confirmed: `CLOSED AS A RESEARCH CHECKPOINT` / `NOT VALIDATED` / `NOT A CANDIDATE` /
  `NOT HYP_003` / `NOT AUTHORIZED FOR EMPIRICAL VALIDATION`. `[VERIFIED FACT — closeout §12]`
- MEC-0011 is a PARALLEL research track. It is NOT reopened. No MEC-0011 assumption is imported into
  MACRO-001 by this audit. `[VERIFIED FACT — this section]`
- The closeout file is NOT modified. `[VERIFIED FACT — this run]`

### K.2 MACRO-001 Current State Confirmed (Phase B)

- Frozen: ROUND 0 A1-A5; D3 = W-B; D4 = R-EC; D7 = B-A; D8 = O-2; no-double-counting confirmed;
  G-1a/G-2a/G-3a/G-4b/G-6b/G-7a confirmed; G-5 deferred; S-1(a)/S-3/S-4(b)/S-5(c)/S-6(a)/S-7(c direction)/
  S-8(b+c)/S-10(IS-based)/S-11(b) confirmed. `[VERIFIED FACT — worksheet §J]`
- **K = 3** frozen declared grid cells (FOMC/CPI/NFP x W-B x B-A x SPX). K = grid cardinality, NOT
  realized event count. `[VERIFIED FACT — worksheet §J ROUND 3A]`
- **S-2** (test statistic): NOT confirmed, remains open. `[VERIFIED FACT — worksheet §J ROUND 3B]`
- **S-7** (post-O-2 T_eff formula): direction confirmed, formula open. `[VERIFIED FACT — worksheet §J ROUND 3B]`
- **S-9** (candidate-specific minimum requirement): NOT confirmed, remains open. `[VERIFIED FACT — worksheet §J ROUND 3B]`
- ROUND 4 (IS/OOS/blind/cost), ROUND 5 (kill/PASS-FAIL-INVALID): NOT STARTED. `[VERIFIED FACT — this run]`

### K.3 Quantity Distinction (must be preserved, never conflated)

The following are SEPARATE quantities in this candidate's design. Each is recorded, never merged:

| Quantity | Meaning | Current binding state |
|----------|---------|------------------------|
| K | DECLARED grid-cell trial count (sealed census) | **3** (FROZEN) |
| Realized event count | raw count of candidate events for a cell in the inference window | NOT recorded (no empirical work) |
| Valid event count | realized events surviving O-2 overlap drop + purge, with no INVALID | NOT recorded; rule derivable (K.5) |
| N_valid | per-cell minimum event requirement (S-9) | **OPEN - HUMAN DECISION REQUIRED** |
| T_eff | post-O-2 effective independent observations (S-7) | **OPEN - HUMAN DECISION REQUIRED** |
| Fixed-horizon HAC unit | inference dependence treatment (S-5/S-6) | cluster unit = family x calendar; time-block granularity **OPEN** |

No threshold values are invented anywhere in this section. `[VERIFIED FACT — this section]`

### K.4 S-2 RESULT — TEST STATISTIC (Phase C)

**Recorded Round 3B starting point:** standardized two-sided t-test on the mean deviation.
`[VERIFIED FACT — Human's recorded recommendation; this audit verifies it, does not replace it]`

**Derivable components (consistent with confirmed S-1/S-3/S-4/S-6/S-10):**
- Deviation object (S-1 event-study object): `D_i = R_EC(i) - mu_b_c` per cell c, where
  `R_EC(i) = Close(next trading day)/Close(event day) - 1` (D4 = R-EC) and `mu_b_c` = mean of the
  B-A baseline 1-trading-day returns `Close(t+1)/Close(t) - 1` over non-event, non-purged baseline days
  in the IS sample for the same cell. `[MODEL INFERENCE — concatenation of frozen decisions]`
- Test statistic: `t = mean(D) / SE_cluster_robust(mean(D))`, two-sided, per declared cell (K=3
  independent trials on the sealed census). `[MODEL INFERENCE — S-3/S-4/S-6]`
- Alternative: `H1: E[D] != 0`; sign reported descriptively only, never as a trade direction
  (S-3/S-4; registry §104). `[VERIFIED FACT]`
- Inference sample: IS-based only (S-10); exact IS dates deferred to ROUND 4. `[VERIFIED FACT]`
- Cluster-robust SE uses the S-5 cluster unit (family x calendar). `[VERIFIED FACT — S-5/S-6]`

**IRREDUCIBLE HUMAN CHOICE (S-2 residual):** the t-test's rejection rule is not fully bound. Which
reference distribution / critical-value convention converts the standardized statistic into an
acceptance decision is NOT pinned by any ratified record (D6 pins census-K and fail-closed semantics;
S-11(b) explicitly excludes gate-6 DSR machinery; the candidate is NOT routed to Phase-5 Sharpe
machinery per S-1(a)). The unresolved S-2 sub-choice is:

- small-sample cluster-robust reference distribution for the two-way cluster:
  (a) asymptotic standard normal, (b) t with G-1 degrees of freedom (number of clusters - 1),
  (c) t with an effective-degrees-of-freedom convention (e.g., Cameron-Gelbach-Miller-type), or
  (d) another pre-registered convention chosen by Human.

Additionally the S-5 calendar-block granularity (which determines the number of clusters and therefore
the SE and df) is itself open (see K.5). The significance level alpha is NOT an S-2 item: it is
already routed to ROUND 5 (D20 acceptance thresholds) in the binding schedule. `[MODEL INFERENCE —
reconciliation of confirmed S-items; no new estimator or test introduced]`

**Conclusion S-2:** test-statistic DEFINITION is derivable; the SMALL-SAMPLE CRITICAL-VALUE/
DF CONVENTION is an irreducible Human choice.
`HUMAN DECISION REQUIRED` — S-2 is NOT frozen.

### K.5 S-7 RESULT — POST-O-2 T_eff (Phase D)

**Derivable structure (from confirmed decisions only):**
- T_eff is computed AFTER O-2 overlap dropping (later event dropped by chronological event timestamp)
  and AFTER purge/label exclusion (D8=O-2; D7=B-A purge event-day + next-trading-day). `[VERIFIED FACT]`
- T_eff is computed ONLY from valid observations; FAILED/INVALID observations are never imputed
  (S-8; ratification D6). Any INVALID input to a cell fails the cell closed - no statistics. `[VERIFIED FACT]`
- T_eff is distinct from K (declared census size) and from N_valid (S-9 minimum); the integrity
  chain `realized events >= valid events >= T_eff` is invariant, with equality only under full
  independence after O-2. `[MODEL INFERENCE]`
- T_eff must account for the fact that O-2 does NOT imply IID (residual temporal dependence and common
  market conditions across macro events remain). `[VERIFIED FACT — worksheet §J ROUND 2 caveat]`
- Cluster-robust inference (S-6(a)) carries the dependence treatment; T_eff is the effective
  observation count used to describe the sample and guard power, not a second estimator. `[MODEL INFERENCE]`

**IRREDUCIBLE HUMAN CHOICES (S-7):**
1. **S-5 calendar-block granularity** was never bound: the S-5(i) confirmation "Family x calendar"
   does not fix the time-block size (yearly / quarterly / monthly / other). This block size drives the
   cluster count, the cluster-robust SE, AND the number of independent effective blocks. It is a
   genuine Human choice; the agent does not select it.
2. **T_eff formula convention**: without a pre-registered dependence-adjustment convention, T_eff is
   not uniquely determined (e.g., block-count convention vs variance-ratio convention vs
   `T_eff = N_valid` under cluster-robust SE). This is a genuine Human choice.

**NOT IMPORTED:** the F-1-frozen `T_eff >= 25` / `N_valid >= 250` thresholds
(`f1_d1_blocker_resolution.md` §, `f1_d1_free_data_feasibility.md` §, ratified N/A) are F-1-specific
and are NOT binding on MACRO-001; no existing MACRO-001 binding imports them. They are listed here only
to record the explicit non-import. `[VERIFIED FACT — F-1 docs; worksheet §J]`

**Conclusion S-7:** the T_eff structural chain is derivable; the calendar-block granularity and the
T_eff formula convention are irreducible Human choices.
`HUMAN DECISION REQUIRED` — S-7 is NOT frozen.

### K.6 S-9 RESULT — CANDIDATE-SPECIFIC MINIMUM REQUIREMENT (Phase E)

**The five layers are preserved and NOT conflated (doctrine separation):**
1. Statistical validity/readiness (pre-registration completeness) - NOT yet reached (S-2/S-7/S-9 open).
2. Candidate promotion criteria (registry) - unchanged; `CAND-FREE-MACRO-001` remains `HUMAN_REVIEW_REQUIRED`.
3. Phase 6 gate criteria (DSR >= 0.95, MinTRL, Holm-Bonferroni FWER, PBO < 0.25, curvature, OOS retention
   SR_OOS >= 0.50*SR_IS) - canonical for the return-series path (`ROADMAP.md` Phase 6); NOT applicable to
   this candidate's primary test, because S-11(b) explicitly adopted the D6 subset with NO new
   DSR/Holm/PBO/CPCV/effective-K. `[VERIFIED FACT — worksheet §J S-11(b); ROADMAP Phase 6]`
4. R1 authorization - NOT STARTED; orthogonal to S-9.
5. Trading authorization - LOCKED; orthogonal to S-9.

**Why S-9 is not derivable:** no ratified record fixes a per-cell event-count minimum for an
event-study object at $0 daily granularity; the F-1 thresholds are F-1-specific (non-import, K.5); the
Phase 6 minima cannot be applied to a non-Sharpe event-study object (S-11(b)). A per-cell minimum is a
research-design judgment for Human. `[MODEL INFERENCE]`

**SMALLEST DECISION SURFACE (presented for Human; agent does NOT select):**
| ID | Item | Options |
|----|------|---------|
| Q-1 | Per-cell minimum valid post-O-2 events | (a) none required (evaluate whatever valid count exists, subject to power caveat) / (b) a Human-specified positive minimum / (c) other pre-registered rule. **No numeric value is proposed here.** |
| Q-2 | Cell disposition if below minimum | (a) FAIL (executed, acceptance not met) / (b) INVALID (integrity/feasibility failure) / (c) deferred with census preserved. Must respect D6 semantics; INVALID is NOT negative evidence; FAILED/INVALID remain census members; mixed census fails closed. |
| Q-3 | Scope of the minimum | (a) one rule shared by all three family cells / (b) per-family rules. Family-specific minima must be pre-registered, not derived post-hoc. |
| Q-4 | Fixed before results | yes - any minimum/rule is fixed in the pre-registration BEFORE empirical execution; selection after seeing counts is prohibited (registry §195-202). |

**Conclusion S-9:** not derivable; Q-1..Q-4 are irreducible Human choices.
`HUMAN DECISION REQUIRED` — S-9 is NOT frozen.

### K.7 ROUND 4 / ROUND 5 / FREEZE — ENTRY EVALUATION (Phases F/G/H)

- ROUND 4 entry condition (per continuation policy): ROUND 4 may be entered only if S-2, S-7, S-9 are
  either fully derivable OR already Human-bound. **NOT SATISFIED** (K.4-K.6 leave irreducible Human
  choices). ROUND 4 is therefore NOT entered in this run. `[VERIFIED FACT — this section]`
- ROUND 5: depends on ROUND 4 completion per the binding schedule; NOT reached. `[VERIFIED FACT]`
- Anti-HARKing audit and final freeze audit: require a COMPLETE Draft Freeze Candidate; the
  pre-registration is not frozen (checklist 0/26 bound); NOT reached. `[VERIFIED FACT]`
- No freeze is executed, no authorization is granted, no empirical step is recommended by this section.

### K.8 GOVERNANCE BOUNDARY — STOP

```
[HUMAN DECISION REQUIRED]
```

Reached at the S-2 / S-7 / S-9 checkout. The exact unresolved items:
1. **S-2**: small-sample cluster-robust critical-value/df convention for the standardized two-sided
   t-test on the mean deviation (and its dependency on the S-5 time-block granularity).
2. **S-7**: S-5 calendar-block granularity + post-O-2 T_eff formula convention (non-import of
   F-1 thresholds confirmed).
3. **S-9**: per-cell minimum/rule (Q-1..Q-4) - no value invented, no rule selected.

These items precede ROUNDS 4-5 and the Draft Freeze Candidate in the binding schedule (worksheet §F).
STOP here. No Round 4, no Round 5, no freeze audit, no anti-HARKing sign-off, no empirical step, no
authorization. `[VERIFIED FACT — this section's contract]`

### K.9 CONFIRMATIONS (this run)

- No empirical validation. No backtest. No data download. No statistics computed. `[VERIFIED FACT]`
- No HYP_003. No R1. No ResearchReInceptionGate. No gate change. No trading. Capital $0.00. `[VERIFIED FACT]`
- No F-1 threshold imported. No MEC-0011 assumption imported. No DXY/ETF/futures substitution. No
  D6/D8-B/OOS/Phase-6 re-design. K = 3 unchanged. Grid unchanged. `[VERIFIED FACT]`
- Only this worksheet (designated live binding document) is modified by this continuation. `[VERIFIED FACT]`

### Continuation Verification Ledger
- Implementation Status: COMPLETE (documentation-only continuation audit appended to the live binding worksheet; no code/test change)
- Contract Enforcement: STRICT FAIL-CLOSED - no Group-B item silently resolved; no value invented; no threshold proposed; no path selected
- Mathematical Authority: CANONICAL SPEC / RATIFIED RECORDS referenced; derivation is `[MODEL INFERENCE]` from frozen decisions only
- Local Test Suite: NOT RUN (docs-only)
- Type Checker (MyPy): NOT RUN (docs-only)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: S-2/S-7/S-9 remain HUMAN DECISION REQUIRED; ROUNDS 4-5 gated off because the entry condition is unmet; the F-1 `T_eff >= 25`/`N_valid >= 250` thresholds and Phase 6 gate minima are recorded as canonical-but-NOT-applied, not imported; everything in this section is pre-registration-preservation work, not a freeze or an authorization.

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