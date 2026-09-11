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
| D19 Kill conditions | **HUMAN-RATIFIED / BOUND (2026-09-10)** — INTEGRITY/PROTOCOL KILL SET ONLY; zero-tolerance (>0); global scope; INVALID; pre-run + during + pre-verdict; NOT part of K; 5-trigger catalog (worksheet O.10); frozen O-2/G-3a/TR-1/CA-1/T_eff/D6 rules NOT redefined | trigger × threshold × scope (global/family) × IS/OOS/both × pre/post-all-trials; canonical thresholds where cited only | D20; D18 manifest | Kill rules change census meaning if post-hoc |
| D20 PASS/FAIL/INVALID | **HUMAN-RATIFIED / BOUND (2026-09-10, O.11)** — H0: E[D]=0 vs H1: E[D]!=0 (two-sided); df = G-1; alpha = 0.05; p < 0.05 => PASS; p >= 0.05 => FAIL; INVALID = D6/D19 integrity semantics; effect magnitude descriptive only; NO effect-size/PBO/DSR/Holm/F-1 threshold imported | semantics preserved (PASS executed+accepted / FAIL executed-not-accepted / INVALID integrity-only, INVALID ≠ negative evidence); **thresholds = ratified** | D12 stats; D18 manifest | Acceptance thresholds must exist before any run |

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

Completion status for this worksheet: `24/26 checked` — 24 substantive items bound across Rounds 0–5
(worksheet Sections J, K, M, N, O and Round 4 Specification §0–§2). D18 manifest schema is specified in
macro_001_d18_manifest_specification.md (unsealed on D17-E); final Human authorization remains open.

```
[x] Event universe frozen                  → A1 (ROUND 0, worksheet O.1)
[x] Timestamp source frozen                → A2 (ROUND 0, worksheet O.1)
[x] Timezone frozen                        → A2 (ROUND 0, worksheet O.1)
[x] Event window frozen                    → ROUND 1 (D3, worksheet O.1)
[x] Return formula frozen                  → ROUND 1 (D4, worksheet O.1)
[x] Direction/hypothesis frozen            → A3 (ROUND 0, worksheet O.1)
[x] Instrument role frozen                 → A4 (ROUND 0, worksheet O.1)
[x] Baseline frozen                        → ROUND 2 (D7, worksheet O.1)
[x] Overlap rule frozen                    → ROUND 2 (D8, worksheet O.1)
[x] Cost model frozen                      → ROUND 4 (CO, worksheet O.6)
[x] Parameter grid frozen                  → ROUND 3A (D11, worksheet O.1)
[x] K computed and frozen                  → ROUND 3A (D12, K=3, worksheet O.1)
[x] Statistical protocol frozen            → ROUND 3B (S-2/S-5/S-7, Round 4 §1)
[x] Multiple-testing semantics frozen      → A5 (ROUND 0, D6 census, worksheet O.1)
[x] IS dates frozen                        → ROUND 4 (D14, worksheet O.1)
[x] OOS dates frozen                       → ROUND 4 (D15, worksheet O.1)
[x] Blind dates frozen                     → ROUND 4 (D16, worksheet O.1)
[x] PIT/data-vintage rules frozen          → ROUND 3B (S-7 / F2 variance ratio, Round 4 §1)
[x] Data archive requirement frozen        → ROUND 3B (S-9, Round 4 §1)
[ ] Manifest schema frozen                 → GROUP C (D18 unsealed template, blocked on D17-E)
[x] Kill conditions frozen                 → ROUND 5 (D19, worksheet O.10, HUMAN-RATIFIED 2026-09-10)
[x] PASS criteria frozen                   → ROUND 5 (D20, worksheet O.11, HUMAN-RATIFIED 2026-09-10: p < 0.05 => PASS)
[x] FAIL criteria frozen                   → ROUND 5 (D20, worksheet O.11, HUMAN-RATIFIED 2026-09-10: p >= 0.05 => FAIL)
[x] INVALID criteria frozen                → ROUND 5 (D20, worksheet O.11, HUMAN-RATIFIED 2026-09-10: INVALID = D6/D19 integrity)
[x] Reproducibility requirements frozen    → CA-1 / TR-1 / S-9 (Round 4 §0/§2, NYSE pinned, TR-1 tie-break)
[ ] Human authorization recorded           → Final Empirical Authorization (OUTSIDE this worksheet; NOT AUTHORIZED)
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

---

## L. HUMAN DECISION PACKAGE — PRE-ROUND-4 (S-2 / S-7 / S-9)

**Object:** package the three irreducible Human choices ahead of ROUND 4 into one maximally clear,
deterministic, minimal decision surface ready for a single Human response. The agent does NOT select,
ratify, freeze, pre-register, authorize, or promote anything. `[VERIFIED FACT — this section's contract]`

**Status classification:**
```
[DOCUMENTATION-ONLY]
[NON-EMPIRICAL]
[NON-AUTHORIZING]
[HUMAN DECISION REQUIRED]
[READY FOR HUMAN DECISION]
[ROUND 4 NOT ENTERED]
```

### L.0 Consistency Audit (16 checks — all verified before packaging)

| # | Check | Result |
|---|-------|--------|
| 1 | No existing frozen Human decision contradicted | VERIFIED — ROUNDS 0-3B unchanged (§J) |
| 2 | K remains 3 | VERIFIED — frozen declared grid cells (§J/ROUND 3A) |
| 3 | D6 semantics unchanged | VERIFIED — census/K/fail-closed untouched (S-11(b)) |
| 4 | D8-B / O-2 semantics unchanged | VERIFIED — O-2 drop-later, NOT IID (§J/ROUND 2) |
| 5 | OOS semantics unchanged | VERIFIED — D5-A held-out Phase 5 (ROUND 4 decision, not taken) |
| 6 | F-1 thresholds remain isolated | VERIFIED — `T_eff>=25` / `N_valid>=250` NOT imported (K.5) |
| 7 | Phase 6 gate criteria remain isolated | VERIFIED — DSR/Holm/PBO/CPCV/effective-K excluded (S-11(b); K.6) |
| 8 | MEC-0011 remains isolated | VERIFIED — CLOSED research checkpoint; not reopened |
| 9 | No directional trading claim introduced | VERIFIED — two-sided object; sign descriptive only (A3/S-4) |
| 10 | SPX remains statistical primary | VERIFIED (A4) |
| 11 | SPY remains robustness/implementation proxy only | VERIFIED (A4/G-4b) |
| 12 | No empirical evidence introduced | VERIFIED |
| 13 | No data downloaded | VERIFIED |
| 14 | No backtest run | VERIFIED |
| 15 | No statistical computation run | VERIFIED — no T_eff, no SE, no df, no counts computed |
| 16 | No parameter optimization performed | VERIFIED |

### L.1 Current State (authoritative, for decision context)

- **Frozen (ROUNDS 0-3B):** A1-A5; D3=W-B; D4=R-EC; D7=B-A (purge event-day + next trading day); D8=O-2;
  G-1a/G-2a/G-3a/G-4b/G-6b/G-7a; G-5 deferred; S-1(a)/S-3/S-4(b)/S-5(c)/S-6(a)/S-7(c direction)/S-8(b+c)/
  S-10(IS-based)/S-11(b). **K = 3** declared grid cells. `[VERIFIED FACT — §J; K.2]`
- **Open (this package):** S-2 reference-distribution/df convention; S-7 calendar-block granularity +
  T_eff formula convention; S-9 per-cell minimum/readiness rule (Q-1..Q-4). `[VERIFIED FACT — §K.4/K.5/K.6]`
- **Not started:** ROUND 4 (IS/OOS/blind/cost), ROUND 5 (kill/PASS/FAIL/INVALID incl. alpha/D20),
  anti-HARKing freeze. `[VERIFIED FACT — K.7]`

### L.2 S-2 — Reference-Distribution / Critical-Value Convention

**Derivable structure (frozen):** `t = mean(D) / SE_cluster_robust(mean(D))`, two-sided, per declared cell
(K=3), IS-based, cluster unit = S-5(c) family x calendar. `[MODEL INFERENCE — S-1/S-3/S-4/S-6/S-10]`

**Remaining Human choice — ONLY the reference distribution for the critical value.** Three alternatives,
exactly as documented in K.4. Alpha is NOT here (routed to ROUND 5 / D20).

| Option | What it means | Additional assumption/convention introduced | Compatible with frozen cluster structure? | Implementation consequence |
|--------|---------------|---------------------------------------------|-------------------------------------------|----------------------------|
| **S2-A — Asymptotic normal reference** | Reject H0 if `|t| > z_(alpha/2)` from standard normal (1.960 at 5%) | Assumes cluster count is large enough that the cluster-robust t is approximately standard normal under H0; no df concept | YES — SE is unchanged; only the critical value is taken from N(0,1) | No df computation; fixed critical values; simplest and most permissive of the three |
| **S2-B — t reference, df = G - 1** | Reject H0 if `|t| > t_(alpha/2, G-1)`; G = number of clusters (per the S-5(c) two-way cluster design) | Adopts the small-sample cluster-robust convention that G clusters provide G-1 degrees of freedom; requires a deterministic definition of "one cluster" | YES — G is produced by the frozen S-5(c) design; BUT G depends on the S-7 calendar-block granularity → bind S-7-1 first | Needs G (number of clusters) from the clustered design; conservative critical values when G is small |
| **S2-C — Effective-df convention** | Reject H0 if `|t| > t_(alpha/2, df_eff)` where df_eff comes from a named effective-degrees-of-freedom formula (cluster-robust df adjustment, e.g., Cameron-Gelbach-Miller / Satterthwaite-type) | Adds a specific, named df-approximation formula that MUST be pre-registered (the exact formula is then frozen, not improvised) | YES — stays inside the cluster-robust SE family; no new estimator | Requires a fixed, pre-registered df formula; generally the most conservative of the three at small G |

**Dependency note:** S2-B and S2-C both require the cluster count G, which is produced by the S-7
calendar-block granularity (L.3 sub-choice 1). S2-A is independent of G. `[MODEL INFERENCE]`

**Boundary:** no DSR, Holm, PBO, CPCV, effective-K, or other correction is added; no new statistical
machinery; alpha remains unresolved in ROUND 5 / D20. `[VERIFIED FACT — S-11(b); schedule §F ROUND 5]`

### L.3 S-7 — Calendar-Block Granularity + T_eff Formula Convention

**Structure (frozen):** `realized >= valid >= T_eff`; T_eff computed AFTER O-2 drop, purge exclusion,
INVALID exclusion, no-imputation, and calendar-block definition. `[VERIFIED FACT — K.5]`

**Sub-choice 1 — Calendar-block granularity.** The set actually supported by the existing documents is
reproduced exactly (worksheet K.5: "yearly / quarterly / monthly / other"). No new alternative is
invented. Each option defines one time-block cluster dimension under the S-5(c) two-way (family x
calendar) design; for each: one cluster/block = the (family x block) intersection cell.

| Option | One cluster/block is... | Event-family boundaries | Across-calendar boundaries | O-2 membership effect | INVALID effect | T_eff conceptually represents |
|--------|-------------------------|--------------------------|----------------------------|----------------------|----------------|-------------------------------|
| **T1 — Calendar-year block** | one (family x calendar-year) cell | All FOMC/CPI/NFP events of the same family and same year share one cluster | Events in different years are in different clusters; no cross-year merging | O-2 operates first (drops later overlapping event by event-timestamp order); surviving events re-assigned to clusters; no cluster spans two years | INVALID observations are never imputed; any INVALID in a cell fails the cell closed → T_eff only ever computed on fully-valid cells | the number of effectively independent (family x year) dependence units represented by the valid sample |
| **T2 — Calendar-quarter block** | one (family x calendar-quarter) cell | Same-family events in the same quarter share one cluster | Quarter boundaries split clusters even within one year | Same as T1, applied post-O-2 | Same as T1 | the number of effectively independent (family x quarter) dependence units |
| **T3 — Calendar-month block** | one (family x calendar-month) cell | Same-family events in the same month share one cluster | Month boundaries split clusters even within one quarter/year | Same as T1, applied post-O-2 | Same as T1 | the number of effectively independent (family x month) dependence units (closest to per-event independence for ~monthly schedules) |
| **T4 — Other pre-registered block** | Human-specified deterministic block (must be defined in words BEFORE results) | Human-defined | Human-defined | Same O-2-first logic | Same INVALID logic | Human-defined |

Note: block granularity determines the number of calendar clusters and therefore (a) the cluster-robust
SE small-sample behavior, (b) G for S2-B/S2-C, and (c) the denominators of T_eff formulas F1/F2 below.
`[MODEL INFERENCE]`

**Sub-choice 2 — T_eff formula convention.** The conventions actually named by the existing
documentation (K.5: "block-count convention vs variance-ratio convention vs `T_eff = N_valid` under
cluster-robust SE") are reproduced. No new formula is invented. No numeric threshold is set.

| Option | Convention | What it means | O-2 / family / calendar behavior | INVALID behavior | T_eff conceptually represents |
|--------|-----------|---------------|----------------------------------|------------------|-------------------------------|
| **F1 — Block-count convention** | `T_eff = number of (family x calendar-block) clusters holding >= 1 valid post-O-2 observation` | Effective observations = number of represented dependence units | Each distinct cluster counts once regardless of how many events it holds (post-O-2 set) | INVALID excluded; valid-only cells only | the number of independent dependence units in the IS sample |
| **F2 — Variance-ratio convention** | `T_eff = (sum_g n_g)^2 / sum_g n_g^2` over clusters (n_g = valid post-O-2 observations in cluster g) | Effective observations shrink toward the cluster count as within-cluster counts grow (inverse design effect) | Cluster sizes n_g are computed on the post-O-2, post-purge, valid set only | INVALID never imputed; excluded from n_g | the information-equivalent independent count given within-cluster dependence |
| **F3 — Full-count convention** | `T_eff = N_valid` (each valid post-O-2 observation counts as one effective observation) | Dependence is carried exclusively by the cluster-robust SE (S-6(a)); T_eff does not shrink | O-2 drops are already applied; surviving valid observations each count | INVALID never imputed; excluded | the raw valid count; dependence handled by SE, not by T_eff |
| **F4 — Other pre-registered formula** | Human-specified deterministic formula | Must be written in full and fixed before results | Human-defined | INVALID never imputed | Human-defined |

**NOT imported — explicit:** F-1 thresholds `T_eff >= 25 / leg` and `N_valid >= 250` remain
F-1-only and are NOT MACRO-001 requirements (K.5). No numerical T_eff threshold is imposed by this
package; no T_eff is computed from real data. `[VERIFIED FACT]`

### L.4 S-9 — Candidate-Specific Minimum / Readiness Rule

**Layer separation (preserved, never conflated):** A. statistical validity · B. research-readiness ·
C. candidate promotion (`HUMAN_REVIEW_REQUIRED`, unchanged) · D. Phase 6 gate (excluded, S-11(b)) ·
E. R1 authorization (NOT STARTED) · F. live trading authorization (LOCKED). `[VERIFIED FACT — K.6]`

**Existing decision surface reproduced exactly (Q-1..Q-4, from K.6).** For each: meaning · layer
governed · what it prevents · threshold type. No option is selected.

| ID | Surface (verbatim scope) | Meaning | Layer governed | Prevents | Type |
|----|--------------------------|---------|----------------|----------|------|
| **Q-1** | Per-cell minimum valid post-O-2 events: (a) none required — evaluate whatever valid count exists, subject to power caveat / (b) a Human-specified positive minimum / (c) other pre-registered rule | The rule that decides whether a cell has enough valid observations to be statistically evaluated | A (statistical validity) + B (readiness) | evaluating cells whose sample makes the test uninformative / power-less | (b) = NUMERICAL threshold (Human states the number); (a)/(c) = STRUCTURAL rule |
| **Q-2** | Cell disposition if below minimum: (a) FAIL (executed, acceptance not met) / (b) INVALID (integrity/feasibility failure) / (c) deferred with census preserved | What census status a below-minimum cell receives | A + D6 census semantics (S-11(b), A5) | silently dropping under-powered cells from the census, or treating insufficiency as either evidence or absolution | STRUCTURAL (status assignment); must respect D6: FAILED/INVALID remain census members; mixed census fails closed; INVALID is NOT negative evidence |
| **Q-3** | Scope of the minimum: (a) one rule shared by all three family cells / (b) per-family rules | Whether the minimum is uniform or family-specific | A | post-hoc re-scoping of the minimum after counts are observed | STRUCTURAL |
| **Q-4** | Fixed before results: YES — any minimum/rule is fixed in the pre-registration BEFORE empirical execution (registry §195-202) | Confirm the chosen minimum/rule is locked pre-run, never selected after seeing counts | B (anti-HARKing) | threshold/rule selection after observing results | STRUCTURAL (process rule) |

**Boundary:** no numeric minimum is invented here; F-1 `N_valid >= 250` is NOT imported; Phase 6 gate
minima are NOT applied to this event-study object (S-11(b)). `[VERIFIED FACT]`

### L.5 Cross-Decision Dependencies

```
S-7 sub-choice 1 (calendar-block granularity: T1/T2/T3/T4)
        │
        ├──► determines G (number of clusters)
        │         │
        │         └──► S-2: S2-B (df = G-1) and S2-C (effective df) depend on G
        │                 │   S2-A is independent of G
        │                 │
        │                 └──► D20 alpha stays in ROUND 5 (independent)
        │
        ├──► determines cluster sizes n_g and cluster count
        │         │
        │         └──► S-7 sub-choice 2 (T_eff formula):
        │                 F1 (block-count) needs the cluster count
        │                 F2 (variance-ratio) needs cluster sizes
        │                 F3 (T_eff = N_valid) needs neither
        │                 F4 (other) Human-defined
        │
S-9 (Q-1..Q-4): independent of S-2/S-7 structure (no dependence on G or T_eff); governed only by
its own rules + D6 semantics (Q-2) and anti-HARKing (Q-4).
```

**Ordering guidance (not a decision):** the single response batch can answer everything at once, but if
the Human wishes to serialize: bind S-7 sub-choice 1 first (it is the root dependency), then S-2
(if B/C) and S-7 sub-choice 2, then S-9 (independent). `[MODEL INFERENCE]`

### L.6 Explicit Non-Decisions (this package decides nothing)

- S-2: NO option selected (A/B/C all open).
- S-7: NO block granularity selected (T1/T2/T3/T4 open); NO T_eff formula selected (F1/F2/F3/F4 open).
- S-9: NO option selected (Q-1..Q-4 open); NO numeric minimum invented.
- Alpha / significance level: NOT decided here — routed to ROUND 5 / D20.
- NO DSR/Holm/PBO/CPCV/effective-K machinery added.
- NO F-1 thresholds imported (`T_eff>=25` / `N_valid>=250`).
- NO Phase 6 gate criteria applied (S-11(b)).
- NO Round 4 entry, NO Round 5, NO anti-HARKing freeze, NO pre-registration freeze.
- NO data download, NO statistics, NO backtest, NO optimization.

### L.7 Human Response Template (single response — do not pre-fill)

```
S-2: [S2-A] | [S2-B] | [S2-C]
        (if S2-B or S2-C: depends on the S-7 calendar block chosen below)

S-7 calendar block: [T1 yearly] | [T2 quarterly] | [T3 monthly] | [T4 other - specify in words]
S-7 T_eff formula:  [F1 block-count] | [F2 variance-ratio] | [F3 T_eff = N_valid] | [F4 other - specify]

S-9 Q-1: [a none] | [b numeric minimum - state the number] | [c other rule - specify]
S-9 Q-2: [a FAIL] | [b INVALID] | [c deferred, census preserved]
S-9 Q-3: [a one shared rule] | [b per-family rules]
S-9 Q-4: [confirm: minimum/rule fixed before any empirical run]

Decision date: ______________
```

### L.8 STOP

```
[HUMAN DECISION REQUIRED]
[READY FOR HUMAN DECISION]
[ROUND 4 NOT ENTERED]
```

- ROUND 4 entry condition (S-2/S-7/S-9 fully derivable OR Human-bound, K.7) remains UNSATISFIED until the
  Human answers L.7. ROUND 4 is NOT entered. ROUND 5 is NOT reached. The pre-registration is NOT fully
  frozen. `[VERIFIED FACT — K.7; schedule §F]`
- After the Human responds, the agent records the answers in §J as new binding rounds, re-run the L.0
  consistency audit, and only then evaluate the ROUND 4 entry condition — all as a separate task.
- No commit, no push in this task (explicit Human instruction). `[VERIFIED FACT — this run]`

### Human Decision Package Verification Ledger
- Implementation Status: COMPLETE (documentation-only package appended to the live binding worksheet)
- Contract Enforcement: STRICT FAIL-CLOSED — no option selected; no value invented; no formula chosen; no threshold proposed
- Mathematical Authority: CANONICAL SPEC / RATIFIED RECORDS referenced; only the option sets already documented in §K.4/K.5/K.6 are surfaced
- Local Test Suite: NOT RUN (docs-only)
- Type Checker (MyPy): NOT RUN (docs-only)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: All option labels (S2-A/B/C, T1-T4, F1-F4, Q-1..Q-4) are identifier shorthand for options already present in §K; no new statistical machinery, no import of F-1 thresholds or Phase 6 gates, no empirical computation; the Human decision surface is complete and the agent waits for the one Human response.

---

## M. HUMAN RATIFICATION — S-2 / S-7 / S-9 (BOUND 2026-09-10)

**Authority:** HUMAN GOVERNANCE — Human provided the single-batch decision set for the Section L Human
Decision Package. The agent transcribes and binds these decisions verbatim; it does not reinterpret,
substitute, or extend them. `[VERIFIED FACT — Human instruction, this run]`

**Status classification:**
```
[DOCUMENTATION-ONLY]
[NON-EMPIRICAL]
[NON-AUTHORIZING]
[PARTIAL RATIFICATION]  (S-2, S-7 block, S-7 T_eff convention, S-9 fully bound;
                        S-7 F2 EXACT FORMULA remains a binding gap - see M.4)
[HUMAN DECISION REQUIRED]  (S-7 F2 exact estimator/formula)
[ROUND 4 NOT ENTERED]
```

### M.1 Exact Human Decisions — Bound

| Decision | Bound value | Status |
|----------|-------------|--------|
| S-2 reference distribution | **S2-B** — t reference with df = `G - 1`; `G` = relevant calendar-cluster count under the frozen S-7 calendar-block definition | **BOUND** |
| S-7 calendar block | **T2** — quarterly calendar block; S-5(c) family x calendar two-way clustering PRESERVED (family dimension unchanged; no one-way replacement) | **BOUND** |
| S-7 T_eff convention | **F2** — variance-ratio convention (convention-level choice) | **BOUND (convention)** / exact formula = Gap (M.4) |
| S-9 Q-1 | **Q-1a** — no new numeric minimum | **BOUND** |
| S-9 Q-2 | **Q-2c** — deferred, census preserved (D6 semantics retained) | **BOUND** |
| S-9 Q-3 | **Q-3a** — one shared readiness rule for all declared cells | **BOUND** |
| S-9 Q-4 | **Q-4** — rule fixed pre-run (anti-HARKing) | **BOUND** |

### M.2 Meaning / Rationale (recorded, not reinterpreted)

- **S2-B:** reject `H0: E[D]=0` when `|t| > t_(alpha/2, G-1)` where
  `t = mean(D) / SE_cluster_robust(mean(D))` (per declared cell, K=3, IS-based, S-10). G is a structural
  (not numeric-at-binding-time) quantity: the count of calendar clusters under T2 for the IS window that
  will be realized at run time; no df number is pre-set here. Alpha is NOT bound here — routed to ROUND 5
  / D20. `[MODEL INFERENCE — S-3/S-4/S-6/S-10 + S2-B]`
- **T2 quarterly:** one (family x quarter) cell is one cluster; events of the same family in the same
  quarter share a cluster; quarter boundaries split clusters; O-2 first, INVALID fail-closed logic per
  L.3/T2 row. Rationale (Human): quarterly balances calendar dependence capture against yearly
  (too coarse) and monthly (too noisy) blocks. `[VERIFIED HUMAN RATIONALE — this run]`
- **F2 variance-ratio:** T_eff shrinks toward the cluster count as within-cluster valid counts grow
  (inverse design effect); dependence-sensitive by construction. This is WHY F3 was rejected (F3 treats
  post-O-2 observations as independent, contradicting the cluster-robust rationale). `[MODEL INFERENCE]`
- **S-9 Q-1a/Q-2c/Q-3a/Q-4:** no new numeric minimum; below-minimum cells are deferred with census
  preserved under existing D6 semantics (INVALID is not negative evidence; FAILED/INVALID remain census
  members; mixed census fails closed); one shared rule across the three declared family cells; rule fixed
  in the pre-registration BEFORE any empirical run (registry §195-202). `[VERIFIED FACT — §K.6; D6]`

### M.3 Dependencies (as bound)

```
T2 (quarterly block)
  -> defines one (family x quarter) cluster
     -> G (calendar-cluster count, realized at run time on the IS window)
        -> S2-B: df = G - 1
  -> cluster sizes n_g and cluster count
     -> F2 variance-ratio inputs
S-9 (Q-1a/Q-2c/Q-3a/Q-4): independent of G/T_eff structure; governed by D6 census semantics (Q-2c)
  and anti-HARKing fix-pre-run (Q-4).
Alpha / D20: NOT bound here; remains ROUND 5.
```

### M.4 S-7 F2 EXACT FORMULA — BINDING GAP (STOP CONDITION #1 TRIGGERED)

The Human instruction requires the exact F2 estimator/formula to be used ONLY if it is already defined in
the canonical MACRO-001 documents, and to STOP otherwise. A full canonical-document inspection was
performed. `[VERIFIED FACT — this run]`

Findings:
1. The canonical MACRO-001 documents (`cand_free_macro_001_human_specification_decision_surface.md`
   §20.2; `cand_free_macro_001_validation_readiness.md` §9 row BA; `free_data_research_registry.md`;
   `research_doctrine.md` doctrine-7; worksheet §K.5) **name** the T_eff concept and the
   "block-count vs variance-ratio vs T_eff=N_valid" convention families, but **none defines an exact
   variance-ratio formula for MACRO-001**.
2. The only placed textual formula in the tree is the section L.3 F2 exposition row
   `T_eff = (sum_g n_g)^2 / sum_g n_g^2`, which was authored by the **agent** as `[MODEL INFERENCE]`
   in the HDP. It is NOT a canonical/frozen governance formula and must NOT be silently promoted to
   canonical status. `[VERIFIED FACT — provenance of that row]`
3. The only exact T_eff formula frozen anywhere is F-1's
   (`T_eff(leg)` = count of DISTINCT effective event dates per composite leg) — that is an F-1-specific
   rule and is **NOT importable** into MACRO-001 (F-1 isolation, per §K.5 and governance boundary).

**Conclusion: the exact F2 estimator/formula is NOT sufficiently defined by the existing canonical
specification. Per the Human's explicit STOP condition, the agent does NOT invent or impose a formula.**

```
[HUMAN DECISION REQUIRED]
S-7 F2 exact estimator/formula is not sufficiently defined by the existing canonical specification.
```

The convention label "variance-ratio (F2)" is bound; the exact mathematical expression must be supplied
by the Human (or by a canonical reference explicitly ratified by the Human) before T_eff can be computed
and before ROUND 4 may proceed.

### M.5 Explicit Non-Imported Thresholds / Machinery (re-confirmed at binding)

- NO F-1 `T_eff >= 25 / leg` and NO `N_valid >= 250` import. `[VERIFIED FACT — §K.5; Human instruction]`
- NO replacement numeric minimum anywhere (S-9 = structural rules only). `[VERIFIED FACT]`
- NO Phase 6 gate minima (DSR>=0.95, MinTRL, Holm FWER, PBO<0.25, OOS retention) as an S-9 substitute
  (S-11(b) excludes gate-6 machinery). `[VERIFIED FACT]`
- NO DSR / Holm / PBO / CPCV / effective-K / Satterthwaite / alternative-df / new correction introduced. `[VERIFIED FACT]`

### M.6 Effective Date & Frozen Status

- Effective date of binding: **2026-09-10** (environment date).
- The bound values in M.1 are **frozen for subsequent specification work** (ROUNDS 4-5, anti-HARKing,
  pre-registration) unless a Human later revises them via a documented governance action.
- Freeze checklist status remains `0/26 FROZEN` in the aggregate sense — this ratification removes the
  S-2/S-7/S-9 Human-bound blockers at the structural level, but the two remaining substantive gaps
  (M.4 F2 exact formula, and ROUND-4 IS/OOS/blind Human choices) keep PRE-REGISTRATION NOT FULLY FROZEN. `[MODEL INFERENCE]`
- Historical decision records (ROUNDS 0-3B, Section K, Section L) are preserved unmodified. `[VERIFIED FACT]`

### M.7 Round 4 / Round 5 / Anti-HARKing / Freeze — Entry Evaluation

- ROUND 4 entry condition (per §K.7: S-2/S-7/S-9 fully derivable OR Human-bound): **NOT SATISFIED** —
  S-7 is bound at convention level but its exact F2 formula (an S-7 binding element) is unresolved (M.4).
  The agent therefore does NOT enter ROUND 4 in this run. `[VERIFIED FACT — this run]`
- ROUND 5: NOT reached. Anti-HARKing audit: NOT performed (a full Draft Freeze Candidate is required).
  Freeze: NOT declared. `[VERIFIED FACT — this run]`
- Independent of M.4, ROUND 4 itself contains new Human choices (D14 IS dates, D15 OOS dates, D16 blind
  window boundaries), which the agent cannot select. `[VERIFIED FACT — worksheet §B ROUND 4]`

### M.8 STOP

```
[HUMAN DECISION REQUIRED]
S-7 F2 exact estimator/formula is not sufficiently defined by the existing canonical specification.
[ROUND 4 NOT ENTERED]
```

Next required input from Human (compact):

```
S-7 F2 exact formula: [provide the exact variance-ratio formula to freeze, OR
                      name/ratify a canonical reference that defines it]
```

Only after M.4 is closed may the agent proceed to ROUND 4 derivation (and then ROUND 5 / anti-HARKing /
freeze readiness), where IS/OOS/blind boundaries (D14/D15/D16) will again require explicit Human choices.

### Ratification Verification Ledger
- Implementation Status: COMPLETE (documentation-only ratification appended; decisions bound verbatim)
- Contract Enforcement: STRICT FAIL-CLOSED — decisions bound without reinterpretation; F2 exact formula NOT invented; STOP condition honored
- Mathematical Authority: CANONICAL SPEC / RATIFIED RECORDS referenced; F2 formula verified-as-absent rather than assumed
- Local Test Suite: NOT RUN (docs-only)
- Type Checker (MyPy): NOT RUN (docs-only)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: S-2/S-7-block/S-7-T_eff-convention/S-9 are BOUND; the exact F2 estimator/formula is an open binding item that the Human must supply or ratify; ROUND 4 not entered because S-7 is incomplete at the formal binding level; no threshold, no F-1 / Phase-6 / DSR-family import; no empirical step.

---

## N. HUMAN RATIFICATION — S-7 F2 EXACT FORMULA (2026-09-10)

**Authority:** HUMAN GOVERNANCE — the Human reviewed the M.4 STOP condition and ratified the exact
S-7 F2 definition below. The agent transcribes it verbatim; it does not reinterpret, substitute, or
extend it. `[VERIFIED FACT — Human instruction, this run]`

**Status classification:**
```
[DOCUMENTATION-ONLY]
[NON-EMPIRICAL]
[NON-AUTHORIZING]
[HUMAN-RATIFIED]
[S-2 / S-7 / S-9 FULLY BOUND]
[ROUND 4 ENTRY CONDITION MET]
```

### N.1 Ratified S-7 F2 Definition (verbatim)

```
T_eff = min(
    N_valid,
    s_D^2 / Var_CR(D_bar)
)
```

where:

- `N_valid` = number of valid observations after all frozen O-2 overlap handling, purge handling,
  and INVALID exclusion.
- `s_D^2` = ordinary sample variance of the valid `D_i` observations
  (`D_i = R_EC(i) - mu_baseline(cell)`, per frozen S-1/D4/D7).
- `Var_CR(D_bar)` = two-way cluster-robust variance estimate of the mean `D_bar` under the already
  frozen family x quarterly-calendar clustering structure (S-5(c) + T2).
- `T_eff` is capped at `N_valid` to preserve the invariant:
  `realized >= valid >= T_eff`.
- If the variance-ratio denominator is non-finite or non-positive, the computation is **FAIL-CLOSED**.
- No imputation.
- No additional numerical threshold.
- No F-1 threshold is imported.
- No Phase 6 minimum is imported.
- No DSR/Holm/PBO/CPCV/effective-K machinery is introduced.

### N.2 Statistical Separation (preserved)

- `T_eff` is an **effective-sample-size diagnostic** only.
- It must NOT replace S-2: the inferential reference distribution remains `t(G - 1)` under the frozen
  S-2 decision (df = G - 1, G = relevant calendar-cluster count under T2).
- It must NOT create a second reference distribution, and must NOT become Satterthwaite df,
  effective df, adjusted K, or any multiple-testing correction.
- Consistency note: `Var_CR(D_bar) = [SE_cluster_robust(mean(D))]^2` (the S-6(a) variance estimator
  squared). The t-statistic (S-2) and T_eff (S-7 F2) therefore share ONE variance authority; no dual
  estimator is introduced. `[MODEL INFERENCE — consistency of the ratified formula with frozen S-6(a)/S-2]`

### N.3 Binding Status After Ratification

| Item | Bound value | Status |
|------|-------------|--------|
| S-2 | S2-B — t reference, df = G - 1 | **BOUND** (M.1) |
| S-7 calendar block | T2 — quarterly; two-way family x calendar preserved | **BOUND** (M.1) |
| S-7 T_eff | F2 variance-ratio, exact formula per N.1 | **BOUND** (this section) |
| S-9 | Q-1a / Q-2c / Q-3a / Q-4 | **BOUND** (M.1) |

The S-2 / S-7 / S-9 Human boundary (worldsheet Section K.8 / L / M) is now **fully resolved**.
The ROUND 4 entry condition (K.7: S-2/S-7/S-9 fully derivable OR Human-bound) is **MET**. `[VERIFIED FACT]`

### N.4 Dependencies (as bound)

```
T2 (quarterly block)
  -> one (family x quarter) cluster
     -> G (calendar-cluster count, realized at run time)
        -> S2-B: df = G - 1
  -> cluster sizes n_g / cluster count
     -> F2: s_D^2 / Var_CR(D_bar), capped at N_valid
S-9 (Q-1a/Q-2c/Q-3a/Q-4): independent of G/T_eff structure; D6 census + anti-HARKing governed.
Alpha / D20: NOT bound — remains ROUND 5.
```

### N.5 Explicit Non-Imported Thresholds / Machinery (re-confirmed)

- NO F-1 `T_eff>=25` / `N_valid>=250` import. NO replacement numeric threshold.
- NO Phase 6 gate minima as any substitute (S-11(b)).
- NO DSR / Holm / PBO / CPCV / effective-K / Satterthwaite / alternative-df / new correction.
- NO imputation; FAIL-CLOSED on non-finite or non-positive denominator.

### N.6 Effective Date & Frozen Status

- Effective date of ratification: **2026-09-10** (environment date).
- The ratified definition is **frozen for subsequent specification work** (ROUNDS 4-5, anti-HARKing,
  pre-registration) unless revised by a documented Human governance action.
- M.6 status superseded: S-7 is now bound at BOTH the convention and the exact-formula level.
- Freeze-checklist aggregate status remains `0/26 FROZEN` — ROUNDS 4-5 binding is still required.
  `[MODEL INFERENCE]`

### N.7 Forward Pointer

- ROUND 4 derivation (all derivable items resolved; genuine Human choices surfaced and NOT selected) is
  documented in the dedicated Round 4 record:
  `./cand_free_macro_001_round4_specification.md`.

### N.8 STOP

```
[HUMAN DECISION REQUIRED]       <- next boundary: ROUND 4 IS/OOS/blind (D14/D15/D16) and
                                   the contiguous Round-4 Human-dependent items (see Round 4 record)
[ROUND 4 ENTERED - DERIVABLE ITEMS RESOLVED]
[ROUND 5 NOT REACHED]
```

### S-7 F2 Ratification Verification Ledger
- Implementation Status: COMPLETE (documentation-only ratification appended; formula bound verbatim)
- Contract Enforcement: STRICT FAIL-CLOSED — formula transcribed exactly; no estimator invented; no threshold; separation from S-2 preserved
- Mathematical Authority: HUMAN-RATIFIED EXACT DEFINITION (N.1); consistency vs frozen S-6(a)/S-2 verified as `[MODEL INFERENCE]`
- Local Test Suite: NOT RUN (docs-only)
- Type Checker (MyPy): NOT RUN (docs-only)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: T_eff is a diagnostic and does not alter the t(G-1) inference (S-2); variance authority shared with S-6(a) via Var_CR(D_bar)=SE_CR^2; no import of F-1/Phase-6/DSR-family items; no empirical step.

---

## O. HUMAN RATIFICATION — ROUND 4 (D14/D15/D16 + TR/EX/CA/CO) (2026-09-10)

**Authority:** HUMAN GOVERNANCE — the Human provided the Round-4 decisions below in one batch. The
agent verifies each decision against the frozen canonical corpus, transcribes the Human rule verbatim,
and applies it ONLY where no canonical definition is missing. Where the Human's own guarded conditional
fires (canonical definition absent), the agent STOPS and surfaces `[HUMAN DECISION REQUIRED]` rather than
inventing. `[VERIFIED FACT — Human instruction, this run]`

**Status classification:**
```
[DOCUMENTATION-ONLY]
[NON-EMPIRICAL]
[NON-AUTHORIZING]
[HUMAN-RATIFIED]
[TR-1 BOUND · CA-1 HUMAN-RATIFIED (DECISION) · CA-1 SOURCE-BINDING ARCHITECTURE HUMAN-RATIFIED
     — 2026 artifact pinned (SHA-256 recorded); CA-1 HISTORICAL COVERAGE 2013–2026 = HUMAN-RATIFIED /
     COMPLETE (2026-09-10 Human ratification): 15 artifacts (13 official press-release PDFs for
     2014–2027 + 2 official HTML artifacts for 2013) retrieved, content-verified, hash-pinned]
[CA-1 HISTORICAL COVERAGE = HUMAN-RATIFIED / COMPLETE — 2013 = EXPLICIT PRE-PDF-ERA HISTORICAL
     ARTIFACT EXCEPTION (official BusinessWire NYSE Euronext release + archived nyx.com page, accepted
     by Human 2026-09-10); 2014–2025 = OFFICIAL NYSE ANNUAL CALENDAR ARTIFACT PRIMARY MODEL]
[ROUND 4 = COMPLETE (Human-closed 2026-09-10) — all Round-4 Human decisions bound/ratified; CA-1
     coverage Human-ratified; no genuine Round-4 blocker remains (closure audit §O.7)]
[ROUND 5 ENTERED — D19/D20 HUMAN DECISION SURFACE PREPARED ONLY; D19 HUMAN-RATIFIED/BOUND 2026-09-10
     (O.10); D20 HUMAN-RATIFIED/BOUND 2026-09-10 (O.11) — alpha = 0.05; ROUND 5 COMPLETE]
```

### O.1 Ratified Decisions (transcribed verbatim)

**D14 — IS window:** `2013-12-01 through 2021-12-31` — calendar-date boundaries exactly as written.
Human rationale recorded: aligned with the already Human-accepted constrained feasibility window
beginning approximately 2013-12; fixed calendar boundary; not selected using observed results; not
selected using expected performance; never optimized. Status: **BOUND**.

**D15 — OOS window:** `2022-01-01 through 2024-12-31` — calendar-date boundaries exactly as written.
Human D15 additions (all recorded): NO new per-family numeric minimum; do NOT import F-1
`N_valid >= 250`; do NOT import F-1 `T_eff >= 25`; do NOT import Phase 6 gate minima; existing D6
SUCCESS/FAILED/INVALID semantics remain authoritative; existing validity/fail-closed rules remain
authoritative; existing purge semantics remain authoritative; do NOT invent a new embargo duration.
Boundary handling uses the already-frozen O-2/purge rules. Status: **BOUND**.

**D16 — Blind window:** `2025-01-01 through 2026-09-10 = BLIND HOLDOUT`. Before specification freeze,
PROHIBITED INFORMATION: blind-window returns; event outcomes; realized deviations; performance metrics;
parameter tuning information; threshold selection information; model/strategy selection information;
calendar selection information; candidate selection information. The blind window must not influence
specification. If data for part of the blind window is unavailable under the authorized
data/provenance rules: do NOT impute; do NOT substitute another source silently; do NOT backfill from an
unauthorized source; do NOT alter D16. Status: **BOUND** (availability resolved at run time only under
frozen PIT/provenance rules; D16 dates immutable).

**SPLIT RULE (bound):** the split is fixed before empirical execution and must not be optimized or
revised after observing results: IS `2013-12-01 -> 2021-12-31`; OOS `2022-01-01 -> 2024-12-31`; BLIND
`2025-01-01 -> 2026-09-10`.

### O.2 Consistency with the frozen ROUND 4 requirement list (unchanged, preserved)

| Requirement | State |
|-------------|-------|
| K = 3 (FOMC/CPI/NFP x W-B x B-A x SPX) | PRESERVED |
| S-2 t reference, df = G - 1 | PRESERVED |
| S-7 quarterly calendar block (T2) | PRESERVED |
| S-7 F2 `T_eff = min(N_valid, s_D^2 / Var_CR(D_bar))`, diagnostic only | PRESERVED |
| S-9 Q-1a / Q-2c / Q-3a / Q-4 | PRESERVED |
| D3 event-day close -> next trading-day close; D4 `R_EC = Close(next)/Close(event) - 1` | PRESERVED |
| D7 B-A baseline; D8 O-2 overlap dropping; G-3a purge (event-day + next trading day) | PRESERVED |
| S-5 family x quarterly two-way clustering; S-8 W-B shift + INVALID fail-closed | PRESERVED |
| S-10 IS-based inference; S-11(b) no DSR/Holm/PBO/CPCV/effective-K | PRESERVED |

### O.3 TR — equal-timestamp tie-break → **[HUMAN DECISION REQUIRED — TR]** (STOP)

**Human instruction:** for equal event timestamps, use a deterministic secondary key derived from the
canonical event ordering/source identifier already available in the specification; the tie-break must
be deterministic and reproducible and must NOT permit manual selection; if the existing canonical
documents do not define an adequate secondary key, STOP and surface `[HUMAN DECISION REQUIRED — TR]`;
do not invent a source identifier.

**Fail-closed verification:** the canonical MACRO-001 corpus defines NO adequate secondary key for equal
timestamps. Worksheet ROUND 2/D8 mandates only that a tie-break MUST be pre-registered before validation
and must NOT be chosen after seeing data — it defines no key. The "canonical tie-break/order semantics"
referenced by `phase14_evidence_bridge_ratification_D1_D9.md` binds the F-1 / Phase 5/6 canonical series
domain and is NOT importable into MACRO-001's O-2 rule (isolation boundary). No event-ordering key,
source-identifier key, or tie-symmetric secondary rule exists in the MACRO-001 spec. Per the Human
guarded conditional, the agent does NOT invent a secondary key.

**Result — HUMAN RATIFICATION (2026-09-10):** the Human ratified **TR-1**; the fail-closed STOP is
CLOSED. O-2 continues by chronological event timestamp (A2); equal timestamps are then ordered by the
ratified deterministic secondary key: **secondary key = (scheduled-calendar date ASC, family order ASC)**
applied AFTER the official release timestamp (A2); **family order = CPI < NFP < FOMC**.
Ratified TR-1 requirements (recorded verbatim from the Human, not reinterpreted):
- Strict deterministic secondary key; tie-symmetric; pre-registered before validation.
- NO outcome-dependent selection; NO manual classification.
- SAME ordering for event-census ordering and the D18 manifest ordering record.
- NO import of F-1 / Phase 5 / Phase 6 ordering semantics.
- Structural condition at census construction: AT MOST ONE admitted release per family per
  scheduled-calendar date; if violated → FAIL-CLOSED under existing D6 semantics (no invented tie-break
  extension, no silent order-by-row).
Status: TR-1 = **BOUND** (HUMAN-RATIFIED). `[VERIFIED FACT — Human instruction, this run]`

### O.4 EX — unscheduled/emergency exclusion → **BOUND** (derivable, no STOP)

**Human instruction:** primary event universe remains FOMC + CPI + NFP; unscheduled/emergency events are
NOT automatically admitted into the scheduled-event census; exclude an event unless it satisfies the
already-frozen event-family definition and official-calendar requirements; do NOT create a new event
family; do NOT manually classify by outcome; if the canonical definition requires a more precise
exclusion rule that cannot be derived, STOP at `[HUMAN DECISION REQUIRED — EX]`.

**Derivation (fully canonical, nothing invented):**
- Frozen family definition: A1 = FOMC + CPI + NFP, one shared protocol (registry §100/§102; surface §9.1).
- Frozen source mapping: FOMC -> S-08 (official Fed FOMC calendar & statements); CPI/NFP -> S-05
  (official BLS CPI / Employment Situation release calendar + values) (surface §9.1; registry §102).
- Frozen schedule authority: Q1 calendars = pre-announced, versioned official schedules S-05/S-08
  `[ACCEPT]` (readiness §11.1).

**Operational EX rule (derived):** an event is admitted into the census IFF it is a scheduled official
release of exactly one of the three frozen families and appears on the official pre-announced release
calendar of its authority (S-08 Fed calendar for FOMC; S-05 BLS calendar for CPI/NFP). Unscheduled /
emergency announcements (e.g., an unscheduled FOMC statement not on the official FOMC calendar) are
excluded. No new event family; no outcome-based or manual classification. Scheduled-but-delayed releases
remain census events and use the official actual release timestamp (A2); as-published vintage rules
apply (readiness §11). `[MODEL INFERENCE — A1/A2 + readiness §11.1 applied consistently]`

**Result:** EX — **BOUND** (derivable). No STOP.

### O.5 CA — session / half-day / early-close → **[HUMAN DECISION REQUIRED — CA]** (STOP)

**Human instruction:** use the official US trading calendar/session definition "already required by A2";
for an event day use the official close associated with that trading date (do not move the event merely
because the session is shortened); next trading day = next valid trading session under the authoritative
calendar; do not invent a special half-day adjustment; if the canonical calendar source/session semantics
are insufficiently defined, STOP at `[HUMAN DECISION REQUIRED — CA]`.

**Fail-closed verification:** A2 (worksheet ROUND 0; surface §10.1) defines event timestamp semantics
(official release timestamp; primary official source; US ET; archive release times at retrieval) and does
NOT require or define a US trading calendar/session. readiness §AX: "Session/calendar (half-days,
holidays) Not specified; CPI/NFP 08:30 ET vs index open 09:30 ET timing interplay undefined —
SPECIFICATION GAP — HUMAN DECISION REQUIRED." readiness §Z: "Missing-data / halted sessions rule Not
specified — SPECIFICATION GAP — HUMAN DECISION REQUIRED." The only frozen session-validity rule ("an
early-close with a valid official close IS a valid session; deterministic valid-session calendar; no
manual shifting") exists in the F-1 candidate review — F-1 is isolated and NOT importable. MACRO-001 has
NO canonical authoritative US trading-calendar source or session-validity semantics. Per the Human
guarded conditional, the agent does NOT name a calendar source or extend session semantics.

**Result — HUMAN RATIFICATION (2026-09-10):** the Human ratified **CA-1** (NYSE official US trading
calendar = valid-session authority for the SPX close series) and confirmed the session-semantics
checklist. The decision-level STOP is CLOSED; a separate provenance field REMAINS OPEN (see
**CA-1 CRITICAL SOURCE RULE** below).

Ratified CA-1 session semantics (recorded verbatim from the Human, not reinterpreted):
1. Half-day / official early close IS a valid session: the official close of that trading date is VALID
   for D4; the event is NOT moved to another date.
2. Event day is NOT a valid trading session: W-B maps the event to the next valid trading session.
3. Missing / halted required observation: the observation is INVALID → fail-closed per S-8(b+c)/D6; NO
   imputation, substitution, backfill, or synthetic value.
4. CPI/NFP 08:30 ET vs regular cash open 09:30 ET: at daily granularity NO special intraday rule; the
   event-day close → next-close return is unchanged.
5. Event timestamp semantics (A2) remain separate from trading-session validity.

**CA-1 CRITICAL SOURCE RULE (FIRED):** the authorized binding criterion is that the repository/canonical
sources must ALREADY contain an authoritative NYSE calendar URL/archive identifier sufficient to bind
CA-1. Repo-wide search on 2026-09-10 (incl. `free_data_source_registry.md`, `src/`, all phase-14 docs)
found NO such URL/versioning/archive identifier — only descriptive mentions (e.g., "NYSE-listed",
"16:00 ET", "NASDAQ/NYSE", exchange-distribution counts). Per the Human's rule, the agent does NOT
invent a URL, provider, or archive rule. The exact missing source-binding field is recorded verbatim as
an UNRESOLVED PROVENANCE FIELD:

```
CA-1 SOURCE-BINDING FIELD — FOUR REQUIRED COMPONENTS (all must be supplied by the Human):

  a. authoritative NYSE trading/market-holiday calendar URL
     (exact URL of the official source; no guessed or paraphrased URL)

  b. version / effective-version identifier
     (the specific version or effective-date range of the calendar used)

  c. archive identifier or reproducible archived snapshot
     (e.g., Wayback Machine capture URL, archived file hash, versioned release tag)

  d. retrieval rule
     (the reproducible procedure for obtaining the exact archived version at future retrieval)

All four components MUST be supplied BY THE HUMAN.
The agent will NOT guess, invent, or silently substitute any component.
EMPIRICAL WORK REMAINS STOPPED until all four fields are bound.
```

> **HISTORIC RECORD (pre-ratification gap).** The four-component gap block above is the prior recorded
> state of the CRITICAL SOURCE RULE. It is **SUPERSEDED** by the Human's ratification in **O.5a** below:
> the source-binding ARCHITECTURE (per-year NYSE annual Trading Calendar PDF model + 9-step retrieval
> rule) is now ratified, the 2026 artifact is pinned, and the annual artifact coverage for 2013–2025
> is now COMPLETE per the 2026-09-10 coverage audit (CA-1 HISTORICAL COVERAGE = COMPLETE).
> CAVEAT: the 2013 coverage uses official HTML-form artifacts (BusinessWire release + archived
> nyx.com page), not a standalone PDF (pre-PDF press era) — Human form-acceptance required before
> Round 4 close.

### O.5a CA-1 SOURCE-BINDING ARCHITECTURE — HUMAN RATIFIED (2026-09-10, home continuation)

**The Human has ratified the CA-1 SOURCE-BINDING ARCHITECTURE.** This is the architecture-level
binding (per-year artifact model + retrieval rule). It does NOT declare Round 4 complete and does
NOT authorize empirical validation.

```
CA-1 AUTHORITY
==============
Authority:                    NYSE official
Primary artifact model:       Annual NYSE official Trading Calendar PDF, pinned separately for
                              every calendar year required by the MACRO-001 research window
Coverage:                     2013-01-01 through 2026-09-10
Version / effective-version:  Use the "Dates are correct as of [date]" statement printed in each
                              official annual NYSE Trading Calendar PDF as the document's
                              effective-version identifier
Archive / reproducibility:    Preserve the exact retrieved PDF bytes and SHA-256 digest for every
                              annual calendar artifact used by MACRO-001

RETRIEVAL RULE (Human-ratified)
===============================
1. Retrieve the official NYSE annual Trading Calendar PDF for the required calendar year.
2. Record the exact official NYSE URL.
3. Record the PDF's printed "as of" date.
4. Compute and record SHA-256 of the exact retrieved bytes.
5. Preserve the exact bytes in the canonical repository archive according to the
   project's existing archival convention (archive-at-retrieval + manifest; readiness AL/§20).
6. On future retrieval, require SHA-256 equality with the pinned artifact before accepting
   the calendar.
7. If the official live URL becomes unavailable, use the already pinned archived artifact /
   reproducible snapshot.
8. Never substitute a generic US holiday calendar, vendor calendar, NASDAQ calendar, or
   another exchange calendar.
9. If an annual artifact required for the research window cannot be obtained or provenance
   cannot be established, FAIL CLOSED — do not infer the missing calendar.
```

**2026 artifact (first pinned artifact — actually retrieved this session, hash computed on the
exact bytes):**

| Field | Value |
|---|---|
| URL | `https://www.nyse.com/publicdocs/nyse/ICE_NYSE_2026_Yearly_Trading_Calendar.pdf` |
| Bytes | 232,670 |
| SHA-256 | `70F5577EB43E60A9DBBECAAE3CEC23D0F02028C05C7F175013BB3E97816D394F` |
| Printed as-of date | Dec. 10 2025 (footer inside PDF) |
| PDF /CreationDate | 2025-12-19 10:32 ET |
| Archive status | exact bytes preserved for repo archive (archived per convention on archival commit) |

**Supporting authority (NOT the immutable primary artifact):**
`https://www.nyse.com/trade/hours-calendars` — official NYSE Holidays & Trading Hours page
(mutable; 2026–2028 holiday table + early-close annotations; Wayback snapshots exist).

[CA-1 = HUMAN-RATIFIED / SOURCE-BOUND at the ARCHITECTURE level]
[Do NOT claim the 2026 PDF alone covers 2013–2026 — per-year coverage is mandatory]
[CA-1 HISTORICAL COVERAGE 2013–2025 = COMPLETE (2026-09-10 audit) — 15 artifacts hash-pinned:
   13 official press-release PDFs (2014–2027) + 2 official HTML artifacts for 2013]

Status: CA-1 = **HUMAN-RATIFIED at the DECISION level** (authority + session semantics BOUND); CA-1
**SOURCE-BINDING ARCHITECTURE HUMAN-RATIFIED (O.5a)** with the 2026 artifact pinned; annual coverage
2013–2025 **COMPLETE per the 2026-09-10 coverage audit** (13 official press-release PDFs + 2 official
HTML artifacts for 2013).

**CA-1 HISTORICAL COVERAGE — HUMAN RATIFIED (2026-09-10).** The Human explicitly ratified the proposed
CA-1 historical provenance manifest and the complete 2013–2025 coverage determination:
```
CA-1 HISTORICAL COVERAGE = HUMAN-RATIFIED / COMPLETE
2013 = EXPLICIT PRE-PDF-ERA HISTORICAL ARTIFACT EXCEPTION (2013 only)
       1. NYSE Euronext / NYX official-era holiday-calendar content
       2. BusinessWire syndicated official NYSE Euronext release
       3. Archived official nyx.com NYSE holidays-and-hours page
       4. Cross-checked calendar dates
       5. Exact retrieved bytes + SHA-256
       6. Wayback capture identifiers recorded
Later years (2014–2025) = OFFICIAL NYSE ANNUAL CALENDAR ARTIFACT PRIMARY MODEL (unchanged)
```
The 2013 exception does NOT change the CA-1 architecture for later years: official NYSE annual
calendar artifacts remain the primary provenance model where such artifacts exist. All existing
provenance hashes and identifiers are preserved. `[HUMAN-RATIFIED 2026-09-10]`

CA-1 is now **operationally bound for the full research window.** `[VERIFIED FACT — Human
ratification 2026-09-10; coverage audit 2026-09-10]`

### O.6 CO — SPY cost model → **BOUND** (DEFERRED — ROBUSTNESS/IMPLEMENTATION LAYER)

**Human instruction:** SPY remains robustness/implementation proxy OUTSIDE the K=3 statistical census;
exact SPY executable cost values remain DEFERRED; do NOT invent cost values; SPY cost modeling must not
block the SPX statistical specification unless governance explicitly requires it. Record CO as
`DEFERRED — ROBUSTNESS/IMPLEMENTATION LAYER`. Status: **BOUND** (no cost value introduced; SPY outside K
confirms decision surface §17 / registry §109 unchanged).

### O.7 ROUND 4 RESULT — COMPLETE (Human-closed 2026-09-10; closure audit no genuine blocker)

- D14 / D15 / D16: **BOUND** (O.1). Split fixed; no embargo invented; D6/purge/O-2 authoritative.
- EX: **BOUND** (O.4). CO: **BOUND** (O.6).
- TR: **BOUND — TR-1** (family order CPI < NFP < FOMC) (O.3).
- CA: **HUMAN-RATIFIED at the DECISION level — CA-1** (NYSE official calendar + confirmed session
  semantics) (O.5); **CA-1 SOURCE-BINDING ARCHITECTURE HUMAN-RATIFIED (O.5a)** with the 2026 artifact
  pinned; **CA-1 HISTORICAL COVERAGE = HUMAN-RATIFIED / COMPLETE (O.5a, Human 2026-09-10)** — 2026-09-10
  coverage audit: 13 official press-release PDFs covering 2014–2027 + 2 official HTML artifacts covering
  2013, all retrieved, content-verified, hash-pinned; 2013 accepted as an explicit pre-PDF-era
  historical-artifact exception.
- ROUND 4 = **COMPLETE**. The Round-4 blocker **CA-1 HISTORICAL COVERAGE** is resolved AND the manifest
  + 2013 artifact-form caveat were Human-accepted (2026-09-10). Annual NYSE calendar coverage for
  calendar years 2013–2025 within the research window (IS 2013-12-01→2021-12-31, OOS 2022-01-01→2024-12-31,
  BLIND 2025-01-01→2026-09-10) is Human-ratified. Round-4 closure audit (round4 spec §7) confirmed no
  genuine unresolved Round-4 Human decision remains.
- Dependency note: D17/SPX close-series pin is NOT treated as solved merely because CA-1 is ratified —
  it remains a separate Group C / D17 decision (surface 66 S-10/S-18 vs readiness 49 "S-04 primary"
  inconsistency), not a Round-4 item; recorded **D17 = OPEN / NON-BLOCKING FOR ROUND 4** per the existing
  Group C sequencing (worksheet F: Round 4 → Round 5 → Group C (D17/D18) → Draft Freeze).
  `[VERIFIED FACT — Human instruction, this run]`

### O.8 ROUND 5 — ENTERED (D19/D20 HUMAN DECISION SURFACE PREPARED ONLY)

- ROUND 5 entry condition is satisfied: no genuine Human decision/provenance blocker remains and ROUND 4
  is Human-closed. **ROUND 5 ENTERED** for the sole purpose of exposing the **D19/D20 HUMAN DECISION
  SURFACE** (see round4 spec §8). At entry, **NO** D19/D20/alpha/threshold/kill condition is selected.
`[VERIFIED FACT — Human instruction: enter ROUND 5 iff no genuine blocker remains]` **This entry record
   is HISTORICAL; current ROUND 5 state is superseded by O.10 (D19 HUMAN-RATIFIED/BOUND) and O.11 (D20
   HUMAN-RATIFIED/BOUND); ROUND 5 = COMPLETE.**
- ROUND 5 content per worksheet §C D19/D20; §N.4; decision surface §20.2/§26/§27: **D19** kill
  conditions (trigger × threshold × scope (global/family) × result status (FAIL/INVALID per D6) ×
  eval window (IS/OOS/both) × pre/post-all-trials × part-of-K) and **D20** PASS/FAIL/INVALID candidate-
  specific acceptance thresholds (semantics canonical/class C, unchanged; alpha is a D20/D12-controlled
  choice). D19 was HUMAN-RATIFIED/BOUND on 2026-09-10 (O.10); D20 was HUMAN-RATIFIED/BOUND on
  2026-09-10 (O.11). **ROUND 5 = COMPLETE (2026-09-10).** `[VERIFIED FACT]`
- Anti-HARKing: NOT PERFORMED (pre-requisites unmet). Draft Freeze: NOT PREPARED. Maximum state
  reachable later: SPECIFICATION FROZEN (never validated / qualified / paper / live on that basis alone).

### O.9 STOP

```
[CA-1 SOURCE-BINDING ARCHITECTURE HUMAN-RATIFIED (2026-09-10) — per-year NYSE annual Trading Calendar
 PDF model; retrieval rule of 9 steps ratified; supporting page = Holidays & Trading Hours]
[2026 ARTIFACT PINNED — URL recorded; as-of Dec. 10 2025; SHA-256 70F5577E...16D394F (bytes 232,670)]
[CA-1 HISTORICAL COVERAGE = HUMAN-RATIFIED / COMPLETE (2026-09-10) — 2013 = EXPLICIT PRE-PDF-ERA
   HISTORICAL ARTIFACT EXCEPTION (BusinessWire release 20110107005513 + archived nyx.com page capture
   20130708145321, accepted by Human); 2014–2027 covered by 13 official press-release PDFs; all
   content-verified, SHA-256 on exact bytes; no hashes fabricated]
[TR-1 BOUND — family order CPI < NFP < FOMC]
[CA-1 HUMAN-RATIFIED — DECISION level: authority + session semantics BOUND; SOURCE-BINDING architecture
   RATIFIED at architecture level; coverage for full window COMPLETE + HUMAN-RATIFIED]
[ROUND 4 = COMPLETE (2026-09-10) — closure audit §O.7: no genuine Round-4 Human decision remains]
[ROUND 5 ENTERED — D19/D20 HUMAN DECISION SURFACE PREPARED ONLY (round4 spec §8); historical record]
[D19 = HUMAN-RATIFIED / BOUND (2026-09-10) — INTEGRITY/PROTOCOL KILL SET ONLY]
[D20 = HUMAN-RATIFIED / BOUND (2026-09-10) — PASS/FAIL/INVALID acceptance criteria (O.11)]
[ROUND 5 = COMPLETE (2026-09-10) — D19 + D20 BOUND; no advance beyond Round 5]
[FREEZE NOT DECLARED]
```

---

## O.10 HUMAN RATIFICATION — D19 KILL CONDITIONS (2026-09-10) — **BOUND**

**Authority:** HUMAN GOVERNANCE — the Human ratified D19 as an **INTEGRITY / PROTOCOL KILL SET ONLY**,
verifying it against the pre-binding audit (Round 5 D19/D20 review, delivered prior to this ratification).
The agent transcribes the Human decision verbatim; it does not reinterpret, substitute, or extend it.
`[VERIFIED FACT — Human instruction, 2026-09-10]`

**Status classification:**
```
[DOCUMENTATION-ONLY]
[NON-EMPIRICAL]
[NON-AUTHORIZING]
[HUMAN-RATIFIED]
[D19 = HUMAN-RATIFIED / BOUND]
[D20 = HUMAN-RATIFIED / BOUND (2026-09-10, O.11)]
[ROUND 5 = COMPLETE — D19 + D20 BOUND]
```

**Ratified D19 decision (verbatim Human ratification):**

```text
D19 = INTEGRITY / PROTOCOL KILL SET ONLY.

D19 does NOT contain performance-based kill conditions.
Performance, effect size, alpha, p-values, t-statistics, returns, or
empirical weakness are D20 matters, not D19 matters.

D19 fields:

1. Trigger
   Pre-specified data, provenance, protocol, or governance integrity
   violations that make the experiment uninterpretable.

2. Threshold
   Deterministic zero-tolerance: any prohibited violation (>0).

3. Scope
   Global for experiment-level invariants.

4. Result status
   INVALID.

5. Evaluation window
   Pre-run and/or during IS/OOS validation according to the
   pre-specified invariant. No outcome-dependent evaluation.

6. Timing
   Preconditions before execution; deterministic checks during
   execution; global integrity checks before final verdict.
   No kill rule may be selected or activated after observing outcomes.

7. K-membership
   D19 kill conditions are NOT members of K.
   K remains the frozen declared census K = 3.

D19 trigger catalog:

1. Duplicate admitted event > 0.
2. Required provenance/source-binding integrity violation > 0.
3. Calendar/session authority mapping violation > 0.
4. Required observation or required statistical input becomes
   non-finite or structurally invalid > 0.
5. Violation of a frozen protocol invariant that makes the
   experiment uninterpretable > 0.

The following frozen rules remain authoritative and are NOT redefined
by D19:

- O-2 overlap handling
- G-3a purge
- TR-1 deterministic event ordering
- CA-1 session/calendar validity
- T_eff INVALID/fail-closed handling
- D6 census semantics

D19 must not silently amend any of those rules.

Where a violation of an existing frozen rule makes the experiment
uninterpretable, the violation may be classified as an integrity
failure under D19, without changing the underlying rule.

D19 kill conditions are not trials and do not change K.
```

**Binding effects (verified, this run):**
- D19 = a pre-registered integrity/protocol kill set. Result status of a D19 kill = **INVALID** (per D6
  semantics: integrity failure, NOT negative evidence). `[VERIFIED FACT — decision surface §27; D6]`
- **No performance/effect-size/alpha/t-stat/p-value/return trigger enters D19.** Those remain D20
  (acceptance threshold) decisions. `[VERIFIED FACT — ratification; decision surface §26.2]`
- **Frozen rules preserved, not redefined:** O-2 (worksheet J ROUND 2), G-3a (worksheet J ROUND 3A),
  TR-1 (O.3), CA-1 (O.5/O.5a), T_eff N.1, D6 census semantics (§C/A5) remain the authoritative
  semantics of their own rules. D19 only classifies a violation that makes the experiment uninterpretable
  as an integrity failure; it does not amend the underlying rule. `[VERIFIED FACT — ratification]`
- **K unchanged:** K remains the frozen declared census = 3 (FOMC/W-B/B-A/SPX · CPI/W-B/B-A/SPX ·
  NFP/W-B/B-A/SPX). D19 kill conditions are not trials; they do not enter K. `[VERIFIED FACT — round4
  spec §3.6; ratification]`
- D19 kill conditions bind into the future frozen manifest (D18 binding set, decision surface §25.1);
  D18 remains Group C / OUT OF SCOPE here. `[VERIFIED FACT — decision surface §25.1]`
- Anti-HARKing: NOT PERFORMED. Draft Freeze: NOT PREPARED. ROUND 5 remains **NOT COMPLETE** at entry
  (historical); **ROUND 5 is now COMPLETE (2026-09-10)** — D20 ratified and bound in O.11. `[VERIFIED
  FACT — O.11]`

### O.10 STOP

```
[D19 = HUMAN-RATIFIED / BOUND (2026-09-10) — INTEGRITY/PROTOCOL KILL SET ONLY; zero-tolerance >0;
 global scope; result INVALID; pre-run + during + pre-verdict; NOT part of K; 5-trigger catalog;
 frozen O-2/G-3a/TR-1/CA-1/T_eff/D6 rules NOT redefined]
[D20 = HUMAN-RATIFIED / BOUND (2026-09-10, O.11) — superseded by O.11; this line is a historical
 D19-record entry]
[ALPHA = 0.05 (HUMAN-RATIFIED, O.11)]
[K = 3 (UNCHANGED)]
[D6 = HUMAN-ACCEPTED / UNCHANGED]
[D17 = OPEN (Group C) — NOT RESOLVED HERE]
[ROUND 5 = COMPLETE (2026-09-10) — D19 AND D20 BOTH BOUND; no advance beyond Round 5]
[SUCCESS/FAILED/INVALID semantics remain canonical (D6)]
[FREEZE NOT DECLARED]
```

---

## O.11 HUMAN RATIFICATION — D20 PASS/FAIL/INVALID ACCEPTANCE CRITERIA (2026-09-10) — **BOUND**

**Authority:** HUMAN GOVERNANCE — the Human ratified D20 as the candidate-specific acceptance criteria
for MACRO-001, verifying it against the pre-binding audit (Round 5 D19/D20 review). The agent
transcribes the Human decision verbatim; it does not reinterpret, substitute, or extend it.
`[VERIFIED FACT — Human instruction, 2026-09-10]`

**Status classification:**
```
[DOCUMENTATION-ONLY]
[NON-EMPIRICAL]
[NON-AUTHORIZING]
[HUMAN-RATIFIED]
[D19 = HUMAN-RATIFIED / BOUND (unchanged)]
[D20 = HUMAN-RATIFIED / BOUND]
[ROUND 5 = COMPLETE]
```

**Ratified D20 decision (verbatim Human ratification):**

```text
D20 = HUMAN-RATIFIED.

1. Canonical D6 semantics remain unchanged:

   PASS  = valid execution + complete evidence + acceptance criteria satisfied.
   FAIL  = valid execution + complete evidence + acceptance criteria not satisfied.
   INVALID = integrity/data/protocol failure; not negative empirical evidence.

2. Statistical hypothesis:

   H0: E[D] = 0
   H1: E[D] != 0

3. Test:

   Two-sided t-test.

4. Reference degrees of freedom:

   df = G - 1

   where G is the realized number of frozen T2 family x quarterly clusters
   used by the canonical variance authority.

5. Significance level:

   alpha = 0.05

6. Primary acceptance criterion:

   p < 0.05  => PASS
   p >= 0.05 => FAIL

7. Effect magnitude:

   Descriptive only.
   No additional numeric effect-size acceptance threshold is imposed.

8. D19 interaction:

   Any valid D19 integrity/protocol kill results in INVALID according to the
   already-ratified D19 and D6 semantics.
   D19 is not redefined by D20.

9. Frozen K:

   K remains exactly 3 declared census cells.
   D20 does not change K or multiplicity semantics.

10. No automatic import:

    Do NOT import PBO < 0.25, DSR >= 0.95, OOS minimum = 4, T_eff >= 25,
    N_valid >= 250, Holm, effective-K reinterpretation, F-1 thresholds, or
    any other Phase-6/F-1 acceptance threshold.

11. No additional candidate-specific numeric criterion:

    No additional performance, return, effect-size, Sharpe, or magnitude
    cutoff is required for PASS beyond the predefined statistical acceptance
    criterion above.
```

**Binding effects (verified, this run):**
- **D20 = HUMAN-RATIFIED / BOUND**: H0: E[D]=0 vs H1: E[D]!=0, two-sided t-test, df = G-1 (frozen
  T2 family × quarterly clusters, canonical variance authority), alpha = 0.05, p < 0.05 => PASS,
  p >= 0.05 => FAIL. `[VERIFIED FACT — ratification; round4 spec §3.5; worksheet M S2-B]`
- **PASS/FAIL/INVALID semantics unchanged (canonical D6):** PASS = executed + accepted; FAIL = executed
  + not accepted (valid negative evidence); INVALID = integrity/data/protocol failure (NOT negative
  evidence). `[VERIFIED FACT — decision surface §27]`
- **Effect magnitude = descriptive only**; no additional numeric effect-size / performance / return /
  Sharpe / magnitude cutoff. `[VERIFIED FACT — ratification]`
- **Nothing auto-imported:** PBO < 0.25, DSR >= 0.95, OOS minimum 4, T_eff >= 25, N_valid >= 250,
  Holm, effective-K reinterpretation, F-1 thresholds, Phase-6 thresholds — NOT bound by this decision.
  `[VERIFIED FACT — ratification]`
- **D19 unchanged:** D19 remains the INTEGRITY/PROTOCOL KILL SET ONLY; D19 kills => INVALID under
  ratified D19/D6 semantics. `[VERIFIED FACT — ratification; O.10]`
- **K unchanged:** K remains exactly 3 declared census cells; D20 does not change K or multiplicity
  semantics. `[VERIFIED FACT — ratification; round4 spec §3.6]`
- MOOD concern: ROUND 5 is COMPLETE (D19 + D20 both bound). Draft Freeze, Anti-HARKing, Group C
  (D17/D18), pre-registration, and empirical validation are NOT entered. `[VERIFIED FACT]`

### O.11 STOP

```
[D20 = HUMAN-RATIFIED / BOUND (2026-09-10) — H0: E[D]=0; H1: E[D]!=0; two-sided t-test; df = G-1;
 alpha = 0.05; p < 0.05 => PASS; p >= 0.05 => FAIL; INVALID = D6/D19 integrity semantics;
 effect magnitude descriptive only; no extra numeric/effect-size cutoff; no auto-import of
 PBO/DSR/OOS-min/T_eff/N_valid/Holm/effective-K/F-1/Phase-6 thresholds]
[D19 = HUMAN-RATIFIED / BOUND (UNCHANGED)]
[D6 = HUMAN-ACCEPTED / UNCHANGED]
[K = 3 (UNCHANGED)]
[ALPHA = 0.05 (RATIFIED)]
[D17 = OPEN (Group C) — NOT RESOLVED HERE]
[D18 = OUT OF SCOPE (Group C) — NOT RESOLVED HERE]
[ROUND 5 = COMPLETE (2026-09-10) — D19 + D20 BOUND; NO ADVANCE BEYOND ROUND 5]
[DRAFT FREEZE NOT ENTERED]
[ANTI-HARKING NOT ENTERED]
[PRE-REGISTRATION NOT ENTERED]
[EMPIRICAL VALIDATION NOT AUTHORIZED]
[HYP_003 NOT CREATED / R1 NOT STARTED / TRADING NOT AUTHORIZED]
[FREEZE NOT DECLARED]
```

---

## CA-1 SOURCE-BINDING — RATIFIED ARCHITECTURE + COVERAGE (COMPLETE)

> **Status:** ARCHITECTURE HUMAN-RATIFIED (2026-09-10) · 2026 artifact pinned · **CA-1 HISTORICAL
> COVERAGE = HUMAN-RATIFIED / COMPLETE (2026-09-10)** — every required annual artifact (2013–2025) is
> actually retrieved, content-verified and hash-pinned (per the 2026-09-10 coverage audit) and the
> complete coverage determination + proposed archive manifest were accepted by the Human. No hashes
> were fabricated; no vendor/other-exchange/generic calendar substituted. The archival commit is a
> separate Human-authorized step.

```
CA-1 SOURCE-BINDING — ANNUAL ARTIFACT COVERAGE (research window 2013-01-01 -> 2026-09-10)
========================================================================================
YEAR | PATH-PERIOD | OFFICIAL URL (retrieved)                      | RETRIEVED? | AS-OF/PUB    | SHA-256          | ARCHIVE
-----|-------------|----------------------------------------------|------------|--------------|------------------|--------
2013 | IS          | BusinessWire news/home/20110107005513/en/NYSE-Euronext-NYX-Announces-2012-2013-Holiday (official NYSE Euronext US release, lists 2012+2013) + archived nyx.com/holidays-and-hours/nyse (capture 20130708145321; official 2013+2014 table) | YES | 2011-01-07 / 2013-07-08 | 220999AF...26256 (HTML) / 0DE65D39...82A3A (HTML) | WAYBACK
2014 | IS          | s2.q4cdn.com/154085107/files/doc_news/archive/b97d77df-0ecb-4db0-9ced-75bdb9b218ba.pdf (2015 release; 2014 set out below) + nyx page above | YES | Dec. 20 2013 | 6628B038...44FEE | ICE IR CDN
2015 | IS          | same b97d77df PDF + archive/442a7c75-b606-4b5d-9853-2efa7d6634c3.pdf (2016 release) | YES | Dec. 20 2013 / Dec. 08 2014 | 6628B038...44FEE + 27C9870E...E357 | ICE IR CDN
2016 | IS          | 442a7c75 PDF + archive/b273f2b1-f4f0-46ae-b6ec-a64e35cd6b7e.pdf (2017 release) | YES | Dec. 08 2014 / Feb. 02 2016 | 27C9870E...E357 + AAC47989...52B | ICE IR CDN
2017 | IS          | b273f2b1 PDF + archive/313c9417-c6e3-46d3-b820-dbc7d9961ebd.pdf (2018+2019 release) | YES | Feb. 02 2016 / Dec. 12 2016 | AAC47989...52B + B76374B1...305F | ICE IR CDN
2018 | IS          | 313c9417 PDF + archive/27aaa58b-ebcb-4f53-b505-aee992f54968.pdf (2018-2020 release) | YES | Dec. 12 2016 / Nov. 27 2017 | B76374B1...305F + B13C0181...9812 | ICE IR CDN
2019 | IS          | 27aaa58b PDF + archive/15638cee-2935-4422-bcb4-a3733587eb8b.pdf (2019-2021 release) | YES | Nov. 27 2017 / Dec. 04 2018 | B13C0181...9812 + BFC91FF0...B58A | ICE IR CDN
2020 | IS          | 15638cee PDF + archive/91a5230f-7233-4a93-b30a-79c9411ebdbe.pdf (2020-2022 release) | YES | Dec. 04 2018 / Dec. 09 2019 | BFC91FF0...B58A + 685A189E...AC9C2 | ICE IR CDN
2021 | IS          | 91a5230f PDF + 2021-2022-and-2023 press PDF (release 2020-12-28) | YES | Dec. 09 2019 / Dec. 28 2020 | 685A189E...AC9C2 + 4419CB78...EEB49 | ICE IR CDN
2022 | OOS         | 2021-2022-and-2023 PDF + 2022-2023-and-2024 press PDF (release 2021-12-27) | YES | Dec. 28 2020 / Dec. 27 2021 | 4419CB78...EEB49 + B8537E45...049E90 | ICE IR CDN
2023 | OOS         | 2022-2023-and-2024 PDF + 2023-2024-and-2025 press PDF (release 2022-12-21) | YES | Dec. 27 2021 / Dec. 21 2022 | B8537E45...049E90 + 8092099C...67186 | ICE IR CDN
2024 | OOS         | 2023-2024-and-2025 PDF + 2024-2025-and-2026 press PDF (release 2023-11-10) | YES | Dec. 21 2022 / Nov. 10 2023 | 8092099C...67186 + A379433B...BD64F | ICE IR CDN
2025 | BLIND       | 2024-2025-and-2026 PDF + 2025-2026-and-2027 press PDF (release 2024-11-08) | YES | Nov. 10 2023 / Nov. 08 2024 | A379433B...BD64F + 6D719AAA...FE3355 | ICE IR CDN
2026 | BLIND       | 2025-2026-and-2027 PDF + 2026-2027-and-2028 press PDF (release 2025-12-23) + https://www.nyse.com/publicdocs/nyse/ICE_NYSE_2026_Yearly_Trading_Calendar.pdf | YES | Nov. 08 2024 / Dec. 23 2025 / Dec. 10 2025 | 6D719AAA...FE3355 + 76775C27...E1D23 + 70F5577E...16D394F | ICE IR CDN / NYSE.COM
```

CA-1 HISTORICAL COVERAGE = **HUMAN-RATIFIED / COMPLETE (2026-09-10).** Every calendar year 2013–2025
within the research window (plus pinned 2026) is covered by at least one actually retrieved official
NYSE artifact: 13 official NYSE Group / NYSE Euronext press-release PDFs from the ICE IR Q4 CDN
(2014–2027 coverage) plus the official 2013 data via two artifacts — (i) the official BusinessWire
distributed NYSE Euronext release "NYSE Euronext (NYX) Announces its 2012 and 2013 Holiday Calendar
and Early Closings" (story 20110107005513) and (ii) the archived official nyx.com "Holidays and
Hours — NYSE" page (Wayback capture 2013-07-08), both listing the full 2013 (+2014) holiday calendar
and matching the press dates. All artifacts content-verified (pypdf text extraction for PDFs; direct
text check for HTML) and SHA-256 computed on exact retrieved bytes. No hashes fabricated; no
generic/vendor/other-exchange calendar substituted. Round 4 blocker (CA-1 HISTORICAL COVERAGE) is
RESOLVED; the manifest + 2013 form were Human-accepted (2026-09-10); ROUND 4 = COMPLETE.

> [!IMPORTANT]
> **2013 artifact-form exception (Human-accepted 2026-09-10):** 2013 predates the PDF-era press artifacts;
> its official coverage is via HTML renderings of official releases/pages (BusinessWire +
> archived nyx.com), NOT a standalone per-year PDF. The Human explicitly accepted this HTML-form
> coverage for 2013 as an **explicit pre-PDF-era historical-artifact exception (2013 only)**; later
> years keep the official NYSE annual-artifact primary model. The exact official URLs for 2013–2025
> were NOT assumed to follow the 2026 filename pattern (verified:
> ICE_NYSE_{2024/2025/2027}_Yearly_Trading_Calendar.pdf return 404); per-year coverage was built from
> the actually retrieved per-year official press-release artifacts instead. No inference from the
> 2026 artifact or from a generic holiday rule was used.
> Round 5 was **ENTERED — D19/D20 HUMAN DECISION SURFACE PREPARED ONLY** (round4 spec §8). On 2026-09-10
> the Human ratified **D19** (INTEGRITY/PROTOCOL KILL SET ONLY, O.10) and **D20** (acceptance criteria
> incl. alpha = 0.05, O.11); **ROUND 5 = COMPLETE (2026-09-10)**.
> No empirical, data, or backtest work is authorized.

---

### Round-4 Ratification Verification Ledger (updated after Round 4 close)
- Implementation Status: COMPLETE (documentation-only; D14/D15/D16/EX/CO/TR bound; CA-1 decision ratified; CA-1 source-binding ARCHITECTURE Human-ratified with 2026 artifact pinned; CA-1 HISTORICAL COVERAGE (2013–2025) = HUMAN-RATIFIED / COMPLETE per 2026-09-10 coverage audit + Human ratification — 15 artifacts retrieved/verified/hash-pinned; 2013 accepted as explicit pre-PDF-era HTML exception; ROUND 4 = COMPLETE; ROUND 5 ENTERED — D19/D20 surface prepared (historical); D19 HUMAN-RATIFIED/BOUND 2026-09-10 (O.10); D20 STILL OPEN)
- Contract Enforcement: STRICT FAIL-CLOSED — TR-1 bound verbatim with family order; CA-1 CRITICAL SOURCE RULE honored (no URL/provider/archive invented; 2026 artifact actually retrieved and hash-computed; no hashes fabricated; per-year coverage mandate preserved; no inference from generic holiday rules; no vendor/other-exchange substitution); session semantics transcribed; no empirical step; D17/SPX pin not silently resolved (recorded D17 = OPEN / NON-BLOCKING FOR ROUND 4, Group C)
- Mathematical Authority: HUMAN-RATIFIED DECISIONS (TR-1 with explicit family order; CA-1 with session-semantics checklist and source-binding architecture) on canonical sources (worksheet J ROUND 2; surface 11.2; readiness AX/Z/11.1; registry 60/77); all 15 coverage-artifact SHA-256 digests computed on exact retrieved bytes
- Local Test Suite: NOT RUN (docs-only; retrieval artifacts kept in temp dir, not staged)
- Type Checker (MyPy): NOT RUN (docs-only)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: Round 4 is now COMPLETE — the sole provenance blocker (CA-1 HISTORICAL COVERAGE) was resolved by the 2026-09-10 coverage audit and the manifest + 2013 artifact-form caveat were Human-accepted (2026-09-10). 2013 (pre-PDF press era) is covered via official HTML-form artifacts (BusinessWire release 20110107005513 + archived nyx.com/holidays-and-hours/nyse capture 20130708145321) as an explicit 2013-only historical-artifact exception; this does not change the later-year official-artifact primary model. Proposed archive manifest (15 artifacts: 13 PDF + 2 HTML) accepted as the provenance record; artifact files remain in the temp dir (never staged/committed without separate Human authorization). TR-1 fully bound. ROUND 5 was ENTERED for surface preparation ONLY — no decisions were selected at that time (historical); D19 is now HUMAN-RATIFIED/BOUND (O.10, 2026-09-10). **SUPERSESSION NOTE (2026-09-10): this Round-4 ledger is a historical record; D20 is now HUMAN-RATIFIED/BOUND (O.11, alpha = 0.05) and ROUND 5 = COMPLETE.** D17/SPX close-series pin remains a separate Group C decision (OPEN / NON-BLOCKING FOR ROUND 4). No empirical action, no data, no backtest, no commit, no push.

---

### D19 Ratification Verification Ledger (2026-09-10)
- Implementation Status: COMPLETE (documentation-only binding; D19 INTEGRITY/PROTOCOL KILL SET HUMAN-RATIFIED/BOUND verbatim in O.10; D20 STILL OPEN)
- Contract Enforcement: STRICT FAIL-CLOSED — D19 transcribed verbatim; zero-tolerance (>0); global scope; result INVALID; NOT part of K; no performance/alpha/effect-size trigger added; frozen rules O-2/G-3a/TR-1/CA-1/T_eff/D6 preserved and NOT redefined; no silent amending; no inference of any D20 value
- Mathematical Authority: HUMAN-RATIFIED DECISION (D19 kill set) transcribed against decision surface §26/§27 + D6 semantics; no statistics computed
- Local Test Suite: NOT RUN (docs-only)
- Type Checker (MyPy): NOT RUN (docs-only)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: D19 = validity/integrity boundary only; D20 (acceptance thresholds incl. alpha) is the empirical acceptance boundary. **SUPERSESSION NOTE (2026-09-10): this D19 ledger is a historical record; D20 has since been HUMAN-RATIFIED/BOUND (O.11, alpha = 0.05) and ROUND 5 = COMPLETE.** The two ratification points were intentionally separate per Human instruction. Kill conditions bind into the future D18 manifest (Group C). K unchanged = 3. D6 unchanged. D17 OPEN. No empirical/backtest/HYP_003/R1/trading/commit/push.

---

### D20 Ratification Verification Ledger (2026-09-10)
- Implementation Status: COMPLETE (documentation-only binding; D20 PASS/FAIL/INVALID acceptance criteria HUMAN-RATIFIED/BOUND verbatim in O.11; ROUND 5 = COMPLETE)
- Contract Enforcement: STRICT FAIL-CLOSED — D20 transcribed verbatim: H0 E[D]=0 / H1 E[D]!=0; two-sided t-test; df = G-1; alpha = 0.05; p < 0.05 => PASS; p >= 0.05 => FAIL; INVALID = D6/D19 integrity semantics (not negative evidence); effect magnitude descriptive only; no additional numeric/effect-size criterion; no auto-import of PBO/DSR/OOS-min/T_eff/N_valid/Holm/effective-K/F-1/Phase-6 thresholds; D19/D6/K preserved and NOT redefined; no value invented or inferred
- Mathematical Authority: HUMAN-RATIFIED DECISION (D20 acceptance criteria) transcribed against decision surface §27 + D6 semantics + frozen S-2 (S2-B df = G-1) / S-3 / S-4(b); no statistics computed
- Local Test Suite: NOT RUN (docs-only)
- Type Checker (MyPy): NOT RUN (docs-only)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: D20 = empirical acceptance boundary (PASS/FAIL/INVALID) only; D19 = validity/integrity boundary (kill set), unchanged; K = 3 unchanged; D6 unchanged. D20 does not enter K and does not change multiplicity semantics. Draft Freeze / Anti-HARKing / Group C (D17/D18) / pre-registration / empirical validation NOT entered. D17 = OPEN (Group C). No empirical/backtest/HYP_003/R1/trading/commit/push.