# CAND-FREE-MACRO-001 — Human Specification Decision Surface

**Document ID:** `docs/phase14/cand_free_macro_001_human_specification_decision_surface.md`

**Document status:**
```
[DECISION SURFACE]
[NON-IMPLEMENTING]
[HUMAN GOVERNANCE REQUIRED]
[EMPIRICAL VALIDATION NOT AUTHORIZED]
```

**Grounding HEAD:** `3e3d918854600a7c0ab526d9b1a008d186610694` (= `origin/main`)
**Date:** 2026-09-10
**Authority:** ACASH AGENTS.md fail-closed doctrine; FREE-DATA BOOTSTRAP program charter; ratified D5/D6
records (`./phase14_d5_d6_ratification_record.md`); registry `./free_data_research_registry.md`;
readiness package `./cand_free_macro_001_validation_readiness.md`.

> **Read this first:** This document is a **decision surface only**. It converts the concept-level
> CAND-FREE-MACRO-001 specification into a set of explicit Human governance decisions. It does **NOT**
> freeze the specification. It does **NOT** authorize anything. It does **NOT** perform any empirical work.
> Where the agent had a reasonable starting position it is labeled `PROPOSED DEFAULT — HUMAN CONFIRMATION
> REQUIRED`. Every substantive unresolved choice is labeled `HUMAN DECISION REQUIRED`. Nothing in this
> document substitutes for Human Governance authority.

---

## 1. Executive Status

| Item | Status |
|------|--------|
| CAND-FREE-MACRO-001 readiness (from readiness package) | `CONDITIONALLY READY` `[VERIFIED FACT — ./cand_free_macro_001_validation_readiness.md §5]` |
| Pre-registration | `NOT FULLY FROZEN` `[VERIFIED FACT — this surface; 4/26 freeze-checklist items bound (Kill conditions = D19, PASS/FAIL/INVALID = D20, worksheets O.10/O.11); remaining items pending Human decisions]` |
| Empirical validation | `NOT AUTHORIZED` `[VERIFIED FACT — ./free_data_research_registry.md §206-214]` |
| Backtest | `NOT AUTHORIZED` `[VERIFIED FACT — registry §202]` |
| Candidate registry status | `HUMAN_REVIEW_REQUIRED` (unchanged) `[VERIFIED FACT — registry §114]` |
| Data feasibility | `[ACCEPT]` `[VERIFIED FACT — registry §113]` |
| F-1 / HYP_003 / R1 / Gate | UNCHANGED / ABSENT / NOT STARTED / NOT INVOKED `[VERIFIED FACT — ROADMAP.md]` |
| **This document's authority** | **NONE beyond presenting the decision surface.** Does not bind any decision. `[VERIFIED FACT — preamble contract]` |

---

## 2. Purpose

The purpose of this surface is to give Human Governance an explicit, auditable set of specification
decisions for CAND-FREE-MACRO-001, so that a later Human decision can either (a) bind all substantive
gaps into ONE frozen pre-registration, or (b) choose any other option, or (c) stop. It surfaces:

1. Every specification gap identified by the readiness review.
2. The existing canonical state (from frozen registry + ratified records) for each dimension.
3. A proposed default where a reasonable starting position already exists in governance material.
4. The alternatives and the governance risk of each.
5. The explicit `HUMAN DECISION REQUIRED` entries — never silently resolved here.

---

## 3. Current Candidate State

Source of truth: `./free_data_research_registry.md` §95-114 `[VERIFIED FACT]`.

| Field | Current canonical value | Status in registry |
|-------|------------------------|--------------------|
| Candidate ID | CAND-FREE-MACRO-001 | §95 |
| Family | 1 — Public event/calendar effects | §99 |
| Mechanism | Scheduled announcements (FOMC, CPI, NFP) concentrate information / re-price risk at known timestamps | §100 |
| Observable data | S-08 FOMC statements; S-05 BLS CPI/NFP; S-04 VIXCLS; S-10/S-18 SPX/SPY daily | §102 |
| Expected behavior | Conditional return/vol deviation vs unconditioned; object = event-conditioned time series, NOT a Sharpe | §103 |
| Direction | PENDING — "event-conditioned deviation, no ex-ante sign asserted" | §104 |
| Horizon | FILED: "1 trading day centered on the announcement (event-day ± opened)" | §105 |
| Universe | Index-level (SPX index values; SPY robustness cross-check) | §106 |
| PIT | full (schedules pre-announced) | §108 |
| Cost | $0 | §109 |
| Survivorship | NONE (index-level) | §112 |
| Data feasibility | `[ACCEPT]` | §113 |
| Governance | PROPOSED → SPEC_FREEZING → **HUMAN_REVIEW_REQUIRED** | §114 |

**Conflicts between documents are recorded, not silently resolved (§6).**

---

## 4. Authorization Boundary

This task and this document:
- Do **NOT** authorize empirical validation, backtest, event study, statistical test, signal generation,
  parameter search, optimization, data-driven parameter selection, OOS validation, Phase 6 gate
  execution, HYP_003 creation, ResearchReInceptionGate invocation, R1, paper trading, live trading,
  broker connectivity, order generation, or capital deployment. `[VERIFIED FACT — task mandate]`
- Do **NOT** modify F-1 governance or F-1 candidate status. `[VERIFIED FACT — task mandate; ROADMAP Phase 14]`
- Do **NOT** modify `src/`, `tests/`, schemas, gates, registry, ROADMAP, trading/broker/Phase-6/Phase-5
  implementation. `[VERIFIED FACT — task mandate §32]`
- Do **NOT** convert CAND-FREE-MACRO-001 into HYP_003. `[VERIFIED FACT — task mandate §3]`
- Do **NOT** change the candidate's statuses: remains `CONDITIONALLY READY`; pre-registration remains
  `NOT FULLY FROZEN`; empirical validation remains `NOT AUTHORIZED`; backtest remains `NOT AUTHORIZED`.
  `[VERIFIED FACT — task mandate §3; registry §206-214]`

---

## 5. Source Documents Inspected

`[VERIFIED FACT — this run]`

| # | Document | Path |
|---|----------|------|
| 1 | Readiness / pre-registration package | `./cand_free_macro_001_validation_readiness.md` |
| 2 | Bootstrap mechanism governance review | `./bootstrap_mechanism_governance_review.md` |
| 3 | SSRN mechanism research (MEC-0001) | `./ssrn_mechanism_research.md` |
| 4 | Free-data research registry (candidate census) | `./free_data_research_registry.md` |
| 5 | Free-data source registry (S-IDs / tiers) | `./free_data_source_registry.md` |
| 6 | Free-data capital bootstrap program (charter) | `./free_data_capital_bootstrap_program.md` |
| 7 | D5/D6 decision surface (read-only audit) | `./phase14_d5_d6_decision_surface.md` |
| 8 | D5/D6 human-ratified freeze & implementation record | `./phase14_d5_d6_ratification_record.md` |
| 9 | D6 statistical semantics decision surface | `./d6_statistical_semantics_decision_surface.md` |
| 10 | Phase 5 production orchestration readiness | `./phase5_production_orchestration_readiness.md` |
| 11 | Research doctrine | `./research_doctrine.md` |
| 12 | Research candidates / ontology | `./research_candidates.md`, `./acash_market_research_ontology_v1.md` |
| 13 | ROADMAP (authorization boundaries, Phase 6 gate criteria) | `../ROADMAP.md` |
| 14 | F-1 boundary docs (isolation reference only) | `./candidate_f1_flow_calendar_rebalance_review.md`, `./f1_d1_*.md` |

No document was assumed by filename; glob + grep were used. No candidate-specific spec file beyond the
registry row exists (`glob **/*macro*`). `[VERIFIED FACT]`

---

## 6. Existing Canonical Specification & Recorded Conflicts

### 6.1 Canonical spec (registry §95-114) — cited verbatim in §3 where applicable.

### 6.2 Recorded document conflicts (`HUMAN DECISION REQUIRED` — not silently reconciled)

| Conflict ID | Dimension | Document A | Document B | Conflict |
|---|---|---|---|---|
| C1 | Event window | registry §105 "1 trading day centered on the announcement (event-day ± opened)" | bootstrap review §310 "event-day ± 1 trading day; 1-day held window" | Two window phrasings; neither is a deterministic start/end algorithm. |
| C2 | Event window (third source) | registry §105 / review §310 | ssrn MEC-0001 "{24h–trading-day windows}" | A third phrasing appears in the mechanism research doc. |
| C3 | Direction object | registry §104 "no ex-ante sign asserted" | ssrn §178-179 pre-FOMC drift direction in the corpus | Corpus literature discusses directional pre-FOMC drift; the candidate's frozen direction is PENDING — the difference must be declared (statistical-descriptive vs directional-trade). |
| C4 | Universe | registry §106 index-level SPX/SPY | F-1 lane (= S&P Composite 1500) | Confirmed different universes; candidate belongs to FREE-DATA lane. No conflation. |
| C5 | Post-2015 persistence | bootstrap review §282 "EVIDENCE = MIXED"; ssrn §531 post-2015 attenuation | — | Persistence question recorded as a risk, NOT a decision; no empirical adjudication here. |

Each conflict above is a **Class B** substantive choice for Human (see §7), surfaced explicitly, never
chosen by the agent.

---

## 7. Decision Classification Methodology

Decisions are separated into THREE classes per the task mandate:

### CLASS A — PROPOSED DEFAULT GOVERNANCE CHOICES
Reasonable starting positions already established by the governance material. **They still require explicit
Human confirmation before becoming frozen.** In the decision table they are written as
`PROPOSED DEFAULT — HUMAN CONFIRMATION REQUIRED`.

### CLASS B — HUMAN DECISION REQUIRED
Any substantive research choice without a canonical frozen value. The agent presents the decision with
alternatives and implications, and MUST NOT select the final value. Written as `HUMAN DECISION REQUIRED`.

### CLASS C — NON-NEGOTIABLE GOVERNANCE / ENGINEERING CONSTRAINTS
Not candidate alpha choices; not open for selection; enforced. Presented for the record, marked
`NON-NEGOTIABLE (GOVERNANCE)`. Examples (already canonical, cited where applicable):
- No post-hoc parameter optimization (registry §195-202). `[VERIFIED FACT]`
- No changing the specification after seeing results (registry §195-202). `[VERIFIED FACT]`
- FAILED/INVALID cannot be silently removed from census; K never silently shrinks
  (ratification record §10; D6 surface §A5). `[VERIFIED FACT]`
- K must be frozen before empirical execution (ratification record §3; D6 surface). `[VERIFIED FACT]`
- Exact pre-registration required before any authorized empirical run (charter §12/§22). `[VERIFIED FACT]`
- OOS independently identified before execution (D5-A; ratification record §2; readiness §17). `[VERIFIED FACT]`
- No data imputation unless explicitly authorized (ratification record §10; readiness §24.10). `[VERIFIED FACT]`
- PIT provenance must be recorded (D5-in-scope PIT; ratification record §2; readiness §11). `[VERIFIED FACT]`
- Empirical authorization must be explicit (registry §206-214). `[VERIFIED FACT]`
- No unauthorized gate/R1/trading activity (This surface §4). `[VERIFIED FACT]`
- Mixed census → statistical evaluation FAILS CLOSED (D6; ratification record §10; D6 surface §A5). `[VERIFIED FACT]`

---

## 8. Human Decision Table

Columns: `ID | Dimension | Current Canonical State | Proposed Default | Alternatives | Governance Risk | Human Decision | Freeze Requirement`.

| ID | Dimension | Current Canonical State | Proposed Default | Alternatives | Governance Risk | Human Decision | Freeze Requirement |
|----|-----------|------------------------|------------------|--------------|----------------|----------------|-------------------|
| D1 | Event universe (FOMC/CPI/NFP) | Named in registry §100/§102 (no rule for inclusion/exclusion) | `PROPOSED DEFAULT — HUMAN CONFIRMATION REQUIRED`: FOMC + CPI + NFP, one protocol | broader/narrower set; per-family protocols; any exclusion | MED — expansion would breach scope; exclusion could bias census | **HUMAN DECISION REQUIRED** | Event set + inclusion/exclusion rule frozen pre-run |
| D2 | Event timestamp / timezone | Not deterministically defined (ET implied only) | `PROPOSED DEFAULT — HUMAN CONFIRMATION REQUIRED`: official release timestamp; primary official source; US Eastern Time | published vs effective vs scheduled; UTC storage | HIGH — timestamp ambiguity breaks PIT + window math | **HUMAN DECISION REQUIRED** | One deterministic timestamp convention frozen |
| D3 | Event window | CONFLICT C1/C2 — registry §105 vs review §310 vs ssrn | No default selected (agent MUST NOT choose) | A–D candidate definitions (§9) | HIGH — primary decision; drives every downstream measure | **HUMAN DECISION REQUIRED** | Single PRIMARY window frozen; any robustness window pre-declared |
| D4 | Return definition | Return-space ambiguity (readiness §24.10) | No default selected | close-to-close / prev-close→event-close / event-close→next / window-return (§10) | HIGH — return formula is the dependent variable | **HUMAN DECISION REQUIRED** | Exact `R = formula` + denominator/treatment frozen |
| D5 | Direction / hypothesis | PENDING — "no ex-ante sign asserted" (registry §104) | `PROPOSED DEFAULT — HUMAN CONFIRMATION REQUIRED`: TWO-SIDED DEVIATION primary (descriptive/statistical), no directional-trade claim | directional hypothesis; other source-supported formulation | HIGH — direction-after-results = data snooping (C3) | **HUMAN DECISION REQUIRED** | Null + alternative + sign-reporting rule frozen pre-run |
| D6 | Instrument / SPX vs SPY role | SPX primary research series; SPY robustness (registry §106) | `PROPOSED DEFAULT — HUMAN CONFIRMATION REQUIRED`: SPX = primary statistical evidence; SPY = robustness/implantation proxy only | SPY primary; exclude SPY; SPY inside K | HIGH — K ambiguity if SPY counted inside vs outside K | **HUMAN DECISION REQUIRED** | SPX/SPY role + K membership frozen |
| D7 | Baseline | "unconditioned behavior" referenced; not defined (registry §103) | No default selected | all non-event days; matched weekday; matched calendar-date; family-specific; other source-supported (§13) | HIGH — baseline IS the counterfactual | **HUMAN DECISION REQUIRED** | Baseline selection+exclusion+overlap rule frozen pre-run |
| D8 | Event overlap / dependence | Not defined | `PROPOSED DEFAULT — HUMAN CONFIRMATION REQUIRED (principle)`: no double-counting without an explicit pre-registered rule | allow overlap with rule; drop-overlapping; cluster-by-family | MED-HIGH — double-counting inflates effective sample | **HUMAN DECISION REQUIRED** | Overlap/clustering unit rule frozen |
| D9 | Cost / execution interpretation | $0 (registry §109); SPY costs not modeled | `PROPOSED DEFAULT — HUMAN CONFIRMATION REQUIRED`: SPX = research series (no executable cost claim); SPY = fixed deterministic cost model if included | cost enters primary test; cost only robustness; excluded SPY | MED — hidden cost assumption would masquerade as performance | **HUMAN DECISION REQUIRED** (no invented bps) | Cost entering scope + exact formula frozen |
| D10 | Parameter grid / Cartesian product | No grid declared (readiness AB/BD) | No default selected | dimensions exhaustive: event-family × window × baseline × instrument × cost × robustness; any sensitivity test outside formal census | HIGH — K derives from grid; post-hoc grid = snooping | **HUMAN DECISION REQUIRED** | Grid dimensions + values frozen; K derivable |
| D11 | K (trial count) | Not declared (readiness §15) | No default (K = |grid| once grid frozen) | K family vs K robustness | HIGH — K is the multiplicity anchor (D6) | **K = UNRESOLVED / HUMAN DECISION REQUIRED** | K frozen & sealed BEFORE evaluation |
| D12 | Statistical protocol | Canonical Phase-6/D6 primitives exist (ratified) | `PROPOSED DEFAULT — CANONICAL REFERENCE (NOT NEW)`: reuse ratified D5/D6/OOS/gate semantics; do NOT invent candidate-specific stats | any statistical deviation requires explicit Human ratification | HIGH — invented stats break canonical lineage | **HUMAN DECISION REQUIRED** (scope of adoption) | Statistical protocol frozen per canonical refs |
| D13 | Multiple-testing semantics | D6 FAIL-CLOSED on mixed census; DSR uses declared_k; no DSR/Holm for mixed (ratified) | `PROPOSED DEFAULT — CANONICAL REFERENCE`: no new corrections; frozen census K governs; mixed census → fail-closed | full DSR/Holm/Bonferroni/FDR/effective-K selection for mixed census (separate ratification) | HIGH — silent correction choice alters acceptance | **HUMAN DECISION REQUIRED** | Multiple-testing scope frozen |
| D14 | IS dates | Not declared | No default selected | IS start/end proposed by Human only | MED-HIGH — retroactive IS = snooping | **HUMAN DECISION REQUIRED** | Exact IS dates frozen before validation |
| D15 | OOS dates | Not declared; D5-A requires separate held-out run | No default selected | OOS = clean untouched segment; minimum event counts | HIGH — OOS integrity is the core validity claim | **HUMAN DECISION REQUIRED** | Exact OOS dates frozen & sealed before validation |
| D16 | Blind period | Not declared (readiness §17) | No default selected | blind start/end; data retrieval allowed/denied; who accesses OOS | HIGH — blindness prevents OOS contamination | **HUMAN DECISION REQUIRED** | Blind window + access rule frozen |
| D17 | Data vintage / archive / PIT | PIT SECURE (calendars); index vintage CONDITIONAL (readiness §11) | `PROPOSED DEFAULT — CANONICAL`: as-published archive + manifest + digest + retrieval timestamp | add second source; reconcile variants | MED — vintage leaks would bias the conditional object | **HUMAN DECISION REQUIRED** (binding details) | Archive/PIT rules + manifest schema frozen |
| D18 | Reproducibility / manifest | Manifest+archive required (registry §107); candidate schema not bound | `PROPOSED DEFAULT`: full manifest binding set (§23) | reduced scope requires explicit reason | MED | **HUMAN DECISION REQUIRED** (binding set) | Manifest binding set frozen |
| D19 | Kill conditions | **HUMAN-RATIFIED / BOUND (2026-09-10)** — INTEGRITY/PROTOCOL KILL SET ONLY; zero-tolerance (>0); global scope; result INVALID; pre-run + during + pre-verdict; NOT part of K; 5-trigger catalog; frozen O-2/G-3a/TR-1/CA-1/T_eff/D6 rules NOT redefined (binding: worksheet O.10) | trigger × threshold × scope (global/family) × IS/OOS/both × pre/post-all-trials | HIGH — kill rules change census meaning if post-hoc | **BOUND** — no longer Human-open; D20 also bound (O.11) | Kill condition set frozen pre-run |
| D20 | PASS / FAIL / INVALID criteria | **HUMAN-RATIFIED / BOUND (2026-09-10, worksheet O.11)** — H0: E[D]=0 vs H1: E[D]!=0; two-sided t-test; df = G-1; alpha = 0.05; p < 0.05 => PASS; p >= 0.05 => FAIL; INVALID = D6/D19 integrity semantics; effect magnitude descriptive only; no additional numeric/effect-size cutoff; no auto-import of PBO/DSR/OOS-min/T_eff/N_valid/Holm/effective-K/F-1/Phase-6 thresholds | canonical D6 PASS/FAIL/INVALID semantics preserved; **test + threshold = ratified** | D12 stats; D18 manifest | Acceptance thresholds must exist before any run |
| D21 | Pre-registration freeze checklist | 4/26 bound (Kill conditions = D19, PASS/FAIL/INVALID = D20, worksheets O.10/O.11) | `PROPOSED DEFAULT — PROCESS`: checklist (§26) fully bound = pre-registration frozen | partial freeze requires explicit exception | HIGH | **HUMAN DECISION REQUIRED** (tracked by Human) | Checklist completion recorded in governance record |
| D22 | Governance option (A–E) | Not decided | No default | OPTION A–E (§28) | HIGH | **HUMAN DECISION REQUIRED** | Decision recorded; no option auto-selected |

**NOTE ON CURRENT CANONICAL STATE:** several rows show a `PROPOSED DEFAULT` even though the registry
records "FROZEN at proposal boundary." The registry freeze is a *scope* freeze (proposal cannot be changed
to chase results), NOT an *execution* determinism freeze. The readiness package (§4.CAVEAT) and this table
distinguish the two. `[MODEL INFERENCE — reconciliation of registry §195-214 + readiness §4]`

### 8.1 Gap-Coverage Map (every readiness §9 gap surfaced → decision-table ID → section)

Readiness package `./cand_free_macro_001_validation_readiness.md` §9 flagged 22 SPECIFICATION GAP
dimensions. All 22 are surfaced in THIS surface as follows (traceability requirement §33-1):

| Readiness §9 gap | Gap subject | This surface's decision table row | Where decided |
|------------------|-------------|-----------------------------------|---------------|
| R | Event set (inclusion/exclusion) | D1 | §9 |
| S | Timestamp / timezone rule | D2 | §10 |
| T | Window start/end math | D3 | §11 |
| U | Return-series definition | D4 | §12 |
| V | Baseline definition | D7 | §15 |
| Z | Missing / halted sessions rule | D4 (return treatment) | §12, §24.2 |
| AB | Parameter set / window binding | D10 | §11 (window), §18 (grid) |
| AD | Trial count K | D11 | §19 |
| AE | Multiple-testing self (K-count) | D13 | §21 |
| AG | Statistical methodology | D12 | §20 |
| AH | Significance threshold | D20 | §20.2, §27 |
| AJ | IS/OOS blind design | D14/D15 | §22 |
| AK | Kill conditions | D19 | §26 |
| AR | Cost model (SPY-carry) | D9 | §17 |
| AU | Drift / rounding / precision policy | D18 (extension) | §25.3 |
| AX | Session / calendar (holiday, half-day) | D2 / D4 | §10, §12 |
| AY | Return space (simple/log/annualized) | D4 | §12 |
| AZ | Sample variance vs long-run vs trial variance | D12 | §20.2 |
| BA | T vs T_eff (effective observations) | D12 | §20.2 |
| BD | Event clustering rule | D8 | §16 |
| BI | Abort / INVALID audit logging | D18 (extension) | §25.3 |
| BK | Environment / toolchain pin | D18 (extension) | §25.3 |

---

## 9. Event Universe

### 9.1 Named event families (registry §100/§102): `FOMC · CPI · NFP` `[VERIFIED FACT]`

Verified as actually present in the canonical documents:
- FOMC → S-08 (Fed FOMC calendar & statements) — registry §102, source registry §75-77. `[VERIFIED FACT]`
- CPI → S-05 (BLS CPI release) — registry §102, source registry §59-61. `[VERIFIED FACT]`
- NFP → S-05 (BLS Employment Situation) — registry §102, source registry §59-61. `[VERIFIED FACT]`

### 9.2 Decision surface for the event universe

| # | Question | Guidance |
|---|----------|----------|
| 9.2.1 | Are all three families included? | Proposed default: yes — but requires Human confirmation (D1). |
| 9.2.2 | One shared protocol for all three, or per-family protocol? | Proposed default: one protocol — requires confirmation. Per-family treatment permitted only if Human allows. |
| 9.2.3 | Is any family excluded? | Decision for Human. Exclusion after pre-registration changes the census → prohibited implicitly by registry §195-202 unless a new candidate is created. `[MODEL INFERENCE]` |
| 9.2.4 | May the event set change post-pre-registration? | No — registry §195-202 freezes the spec; any change = new candidate + Human review. `[VERIFIED FACT]` |

### 9.3 Scope guard (agent did NOT expand)

No event family beyond the named set is added — **PPI, GDP, jobless claims, ISM, retail sales, Fed
speeches are NOT in scope** unless a source document already contains them (none does). `[VERIFIED FACT — no such entries in registry/ssrn for this candidate]`

---

## 10. Event Timestamp / Timezone

### 10.1 Proposed default (Class A — confirmation required)

```
timestamp  = actual official release timestamp
source     = primary official source (S-08 FOMC / S-05 BLS)
timezone   = US Eastern Time (ET)
```

### 10.2 Unresolved details → all `HUMAN DECISION REQUIRED`

| Detail | Issue |
|--------|-------|
| Exact source per family | which precise source row; cross-source reconciliation rule if values differ |
| Timestamp field | which field carries the authoritative time |
| Publication vs effective timestamp | release effective time may differ from publication timestamp |
| Scheduled vs actual release | early/delayed releases protocol (readiness §10.4) |
| Revisions | as-published vintage rule (readiness §11) |
| Delayed / unscheduled releases | exclusion or special rule |
| Holiday / early-close handling | e.g., CPI/NFP 08:30 ET vs index open 09:30 ET; half-day sessions (readiness §AX) |
| DST / daylight saving | ET vs UTC conversion determinism; storage base |

The specification must eventually define **one** deterministic timestamp convention. Until Human binds it:
`HUMAN DECISION REQUIRED`. `[MODEL INFERENCE — readiness §10]`

---

## 11. Event Window — HIGH PRIORITY (PRIMARY HUMAN DECISION)

### 11.1 The ambiguity (recorded, not resolved)

Three phrasings exist in different documents (Conflict C1/C2):

| Source | Phrasing |
|--------|----------|
| registry §105 | "1 trading day centered on the announcement (event-day ± opened)" |
| bootstrap review §310 | "event-day ± 1 trading day; 1-day held window" |
| ssrn MEC-0001 | "24h–trading-day windows" |

`HUMAN DECISION REQUIRED` — the agent must NOT choose among these.

### 11.2 Candidate window definitions (for Human selection only)

| ID | Definition | Exact start → end | Timezone | Session | Out-of-RTH behavior | Holiday/weekend ruling | Window basis | Leakage risk |
|----|------------|-------------------|----------|---------|--------------------|------------------------|--------------|--------------|
| W-A | Previous close → event-day close | prev trading-day close → event-day close | ET | Regular | release before 09:30 ET inside window already | event maps to next trading day if holiday | trading-day | LOW (close-to-close only) |
| W-B | Event-day close → next trading-day close | event-day close → next trading-day close | ET | Regular | — | shift forward | trading-day | LOW |
| W-C | Previous close → next trading-day close | prev close → next trading-day close (2 closes) | ET | Regular | — | shift forward | trading-day | LOW (spans 2 sessions) |
| W-D | Intraday event-time window | event timestamp ± defined minutes (requires intraday data) | ET | intraday | out-of-RTH handling explicit | N/A | elapsed-time | intraday data NOT available at $0 daily granularity `[VERIFIED FACT — source registry §56]` |

For whichever Human selects, the following MUST be defined (existing source material supports the template
but does not bind the value): `[MODEL INFERENCE — task mandate §9]`
- exact start timestamp; exact end timestamp; timezone
- which market session is used; out-of-Regular-trading-hours handling
- holiday/weekend handling; whether window is event-day / trading-day / elapsed-time based
- leakage risk statement

### 11.3 Rules that apply regardless of choice (Class C)

- No empirical comparison of windows in THIS task. `[VERIFIED FACT — task mandate §9]`
- Human must choose the PRIMARY event window before validation. `[VERIFIED FACT — task mandate §9]`
- Any robustness window must be explicitly authorized and pre-declared. `[VERIFIED FACT — task mandate §9]`
- A window choice is a parameter; parameter-freeze regime applies (registry §195-202). `[VERIFIED FACT]`

---

## 12. Return-Space Decision

### 12.1 Current state

Return-space ambiguity exists (readiness §24.10): the object is "conditional return/vol realization"
(registry §103) with **no exact formula**, no simple/log or annualization decision, no denominator rule,
no missing-observation rule. `[VERIFIED FACT — readiness §9 AY/AZ/BA]`

### 12.2 Candidate formulations (for Human selection ONLY — agent invents nothing)

| ID | Formulation | Required exact expression |
|----|-------------|--------------------------|
| R-CC | close-to-close | `R_t = Close(t)/Close(t-1) - 1` (precise form subject to window choice §11) |
| R-PC | previous-close to event-day-close | `R_event = Close(event)/Close(event-1) - 1` |
| R-EC | event-day-close to next-close | `R_event = Close(event+1)/Close(event) - 1` |
| R-W | event-window return | depends on §11 choice (start/end values only) |

For every option the exact treatment of the following must be bound: `[MODEL INFERENCE — task mandate §10]`
- denominator; missing observations; non-trading days
- corporate actions if SPY is used (SPY is allowed to have distributions/splits)
- index (SPX) vs ETF (SPY) price semantics — these are NOT equivalent accounting objects (D6 §43; readiness §AR)

Until Human chooses: `RETURN DEFINITION = HUMAN DECISION REQUIRED`. `[VERIFIED FACT — task mandate §10]`

---

## 13. Direction / Hypothesis

### 13.1 Proposed conceptual default (Class A)

```
PRIMARY TEST = TWO-SIDED DEVIATION
```

Rationale (from governance material): registry §104 freezes direction as PENDING ("event-conditioned
deviation, no ex-ante sign asserted"). The mechanism establishes potential event-conditioned deviation,
NOT a proven LONG or SHORT direction. `[VERIFIED FACT — registry §103-104]`

### 13.2 Human must decide (D5)

| Option | Meaning |
|--------|---------|
| A | Two-sided deviation is primary (descriptive/statistical object). |
| B | Directional hypothesis is primary (would require a source-supported sign — registry does NOT provide one; ssrn corpus discusses pre-FOMC drift direction but the candidate's frozen direction is PENDING → C3 conflict declared). |
| C | Another source-supported formulation. |

### 13.3 Binding rules for EITHER selection (Class C)

- Null hypothesis + alternative hypothesis must be written before empirical runs.
- Sign reporting rule must be predefined (sign is descriptive; descriptive ≠ tradable).
- **Prohibited: selecting direction after observing results.** `[VERIFIED FACT — task mandate §11; doctrine-10]`
- Two-sided-deviation is a statistical object; it must NOT be converted into a directional strategy claim
  (readiness §5; roadmap Phase 17: Observed Profit ≠ Proven Skill ≠ Structural Edge). `[MODEL INFERENCE]`

---

## 14. Instrument Decision

### 14.1 Proposed default (Class A)

```
SPX = PRIMARY RESEARCH SERIES   (statistical / index-level evidence)
SPY = ROBUSTNESS / IMPLEMENTATION PROXY ONLY
```

Registry §106 lists SPX primary + SPY robustness cross-check; bootstrap review §310 matches. `[VERIFIED FACT]`

### 14.2 Separation (Class C — must not be conflated)

- Statistical evidence comes from the index series (SPX). `[MODEL INFERENCE]`
- Tradability/execution evidence would come from the ETF (SPY) — and only if separately cost-modeled. `[MODEL INFERENCE]`
- SPX evidence must NOT be claimed as executable SPY P&L (readiness §AR; roadmap Phase 8 ≥12bps friction; Phase 7 reality-gap discipline). `[MODEL INFERENCE]`

### 14.3 Human must decide (D6)

- Include SPY robustness? (proposed default: yes, robustness-only)
- SPY inside K or outside primary K? → directly affects K (§15/§17)
- Are SPY cost assumptions part of the formal candidate test? (proposed default: cost enters robustness only)

---

## 15. Baseline Decision

### 15.1 Current state

"Unconditioned behavior" is the referenced baseline (registry §103 line "deviates from unconditioned
behavior") but is **not operationally defined** — no sample rule, no exclusion rule, no overlap rule, no
fixed-before-results rule. `[VERIFIED FACT — readiness D7/V/Z]`

### 15.2 Candidate alternatives (for Human selection ONLY)

| ID | Baseline | Selection rule | Exclusion rule | Overlap rule | Fixed before results? |
|----|----------|----------------|----------------|--------------|-----------------------|
| B-A | All non-event trading days | all days not in event set | exclude event days + window-adjacent purged labels | must not overlap any event window | yes (pre-registered) |
| B-B | Matched weekday baseline | same weekday-of-week as event day | same as B-A | as B-A | yes |
| B-C | Matched calendar-date baseline | same calendar month/day | same as B-A | must not overlap an event in another year | yes |
| B-D | Event-family-specific baseline | per-family control set | per-family exclusion | per-family overlap rule | yes |
| B-E | Other explicitly source-supported baseline | as defined by Human | — | — | yes |

`HUMAN DECISION REQUIRED` — the agent does not choose (readiness §13; task mandate §13).

---

## 16. Event Overlap / Dependence

### 16.1 Unresolved questions (D8)

- Multiple events same day (readiness §BD; e.g., CPI + weekly claims weeks, near-month-end clusters). `[MODEL INFERENCE]`
- FOMC / CPI / NFP proximity (calendar clustering). `[MODEL INFERENCE]`
- Overlapping event windows / shared return intervals.
- May one calendar day contribute multiple observations?
- Clustering unit; is event family a cluster dimension? (readiness §AE)

### 16.2 Proposed governance principle (Class A — confirmation required)

```
No double-counting without an explicit pre-registered rule.
```

The final rule is `HUMAN DECISION REQUIRED` (D8). Whichever rule is chosen must be pre-registered and
count toward K determinism; it cannot be invented at run time.

---

## 17. Cost / Execution Interpretation

### 17.1 Preserved distinction (cannot be changed by the agent)

```
SPX primary    → research/statistical series; NO executable trading-cost claim
SPY robustness → fixed deterministic cost model IF included
```

Registry §109 cost = $0; readiness §13 (no SPY-carry cost model declared). `[VERIFIED FACT]`

### 17.2 Required Human choices (no invented bps)

- spread; slippage; brokerage; fees; borrow (if SPY-short ever relevant); market impact (if applicable)
- does cost enter the PRIMARY test? (proposed default: cost is research-only for SPX; SPY robustness gets a fixed model)
- is cost only robustness? (proposed default: yes)
- exact deterministic formula (proposed default: canonical Phase-5 friction primitives if SPY executed —
  but this is a candidate-level decision, `HUMAN DECISION REQUIRED`)

If exact values are not already governance-frozen: `HUMAN DECISION REQUIRED`. No empirical cost estimates
in this task. `[VERIFIED FACT — task mandate §15]`

---

## 18. Parameter / Grid Decision

### 18.1 Requirement (Class C)

The candidate MUST have an explicit parameter space BEFORE empirical testing. K derives from the declared
Cartesian grid (task mandate §16; D6 frozen-K). `[VERIFIED FACT — mandate §16; ratification §3]`

### 18.2 Grid document dimensions (`HUMAN DECISION REQUIRED` — no invented values)

| Dimension | Question | Default? |
|-----------|----------|----------|
| Event family | crossed (FOMC×CPI×NFP) or separate? | no default |
| Horizon/window | crossed per §11 candidate windows? robustness windows explicit? | no default |
| Baseline | crossed per §15 | no default |
| Instrument | SPX and/or SPY | D6 |
| Cost assumptions | crossed only for SPY | D9 |
| Robustness specs | count toward K or outside formal census? | D11/D14 |
| Sensitivity tests | outside the formal census explicitly? | Class C: must be declared pre-run |

### 18.3 Rule (Class C)

- A missing grid value → `HUMAN DECISION REQUIRED`, never invented.
- K MUST be computed from the frozen grid; it must NEVER be chosen after seeing the count of favorable
  results. `[VERIFIED FACT — task mandate §16; registry §195-202]`

---

## 19. K (Trial Count)

### 19.1 Canonical K semantics (ratified — Class C)

- K = **frozen declared/pre-registered census size**. `[VERIFIED FACT — ratification record §10; D6 surface §A5]`
- `EXECUTED_SUCCESSFULLY`, `FAILED`, `INVALID` all remain census members on the declared census. `[VERIFIED FACT — ratification record §10]`
- K must NOT silently become the successful count (`K=20 (16SUCC+2FAIL+2INV) => K=20, NOT 16`). `[VERIFIED FACT — ratification record §10]`
- FAILED/INVALID must not be represented as return=0 / Sharpe=0 / p=1 / neutral / synthetic / imputed / zero-filled. `[VERIFIED FACT — ratification record §10]`
- Mixed census → statistical evaluation FAILS CLOSED (D6). `[VERIFIED FACT — D6 surface §A5; ratification §10]`

### 19.2 This candidate's K

Because grid dimensions (§18) and the SPY-membership question (§14.3) are unresolved:

```
K = UNRESOLVED
HUMAN DECISION REQUIRED
```

The agent does NOT estimate or guess K. `[VERIFIED FACT — task mandate §17]`

---

## 20. Statistical Protocol

### 20.1 Canonical primitives that exist (ratified — Class C, referenced not reopened)

- D5-A OOS provenance + separate held-out Phase 5 run (ratification record §2; `./phase5_production_orchestration_readiness.md` §18). `[VERIFIED FACT]`
- D6 Option A frozen-census + status semantics + fail-closed mixed census (ratification §3/§10). `[VERIFIED FACT]`
- Phase 6 gate metrics (ROADMAP §Phase6): DSR ≥ 0.95, MinTRL, Holm-Bonferroni FWER, PBO < 0.25,
  flat parameter curvature, OOS retention SR_OOS ≥ 0.50·SR_IS — **gate criteria exist; applicability to a
  non-tradeable event-conditioning object is a Human decision (D12/D20).** `[VERIFIED FACT — ROADMAP Phase 6]`
- Canonical D3 returns / D7 Sharpe / D4 periods_per_year single-authority (readiness + orchestrator doc §7-8). `[VERIFIED FACT]`

### 20.2 Human must decide (D12, D20)

- Which canonical statistics are adopted for this candidate, and whether the candidate's "event-conditioned
  deviation" object maps onto return-series statistics (Phase-5-equity path) or requires an event-study
  statistical object (which does NOT exist in canonical gate infrastructure → `HUMAN DECISION REQUIRED`).
- test statistic; null hypothesis; one/two-sided; clustering; HAC; fixed-horizon treatment; effective
  sample size T_eff; event-level clustering; missing observations; minimum sample size; inference-sample
  definition.

Where a canonical mandate already fixes an item, it is referenced, not reopened. Where no canonical mandate
exists: `HUMAN DECISION REQUIRED`. No statistical computation occurred. `[VERIFIED FACT — task mandate §18]`

---

## 21. Multiple-Testing Decision

### 21.1 What canonical governance says (referenced, Class C)

- K = declared census (D6). `[VERIFIED FACT]`
- FAILED/INVALID remain in census; mixed census → NO complete statistical evidence → FAIL CLOSED. `[VERIFIED FACT — D6 surface §A5]`
- DSR uses `declared_k`; Holm p-value family = len(p_values); effective-K = census K in activated paths
  (D6 surface §A7). `[VERIFIED FACT]`
- The DSR/Holm/effective-K semantics for **mixed/incomplete censuses are NOT REQUIRED FOR CURRENT
  OPERATION and are deferred** unless a future requirement demands statistical evaluation of such a census
  (ratification record §10, verbatim). `[VERIFIED FACT]`

### 21.2 Human decision (D13)

Whether this candidate adopts the canonical gate-6 machinery (DSR/Holm/PBO/CPCV etc.) or a defined subset,
and whether a mixed census is even reachable for this candidate's design. **No new correction (DSR, Holm,
Bonferroni, FDR, effective-K) is introduced by this surface.** If unresolved: `HUMAN DECISION REQUIRED`.
`[VERIFIED FACT — task mandate §19]`

---

## 22. IS / OOS Decision

### 22.1 Current state

Exact IS/OOS dates are NOT declared for this candidate (readiness §17). The D5-A ratified model requires
OOS = canonical SplitPolicy OOS partition, executed via a **separate held-out Phase 5 run** with identity
binding at the OOS-evidence-record layer (ratification record §2; orchestrator §18.1-4). `[VERIFIED FACT]`

### 22.2 Decision surface (D14/D15 — agent does NOT select dates)

Human must specify:
- exact IS start; exact IS end; exact OOS start; exact OOS end
- OOS completely untouched (never participates in any parameter/grid choice)
- min event counts per family in IS and OOS separately
- quarantine/embargo overlap rules; required gap/embargo
- whether the canonical SplitPolicy percentages (train 0.60 / val 0.20 / oos 0.20, embargo 5) apply to an
  event-driven calendar (readiness §17; orchestrator §14) or a Human-defined equivalent

State that must hold regardless of date choice (Class C):
```
OOS dates MUST be fixed before empirical validation.
```
No backtest. `[VERIFIED FACT — task mandate §20]`

---

## 23. Blind-Period Decision

### 23.1 Decision surface (D16 — agent does NOT choose dates)

Human must define:
- exact blind start; exact blind end
- information prohibited during blind period (e.g., no OOS event outcomes inspection)
- whether source data may be retrieved during blind; whether event metadata may be inspected
- whether aggregate diagnostics may be inspected
- who/what is permitted to access OOS data (consistent with D5-A `OosExposureState` UNEXPOSED→EVALUATED_LOCKED;
  readiness §17; orchestrator §18.1-4)

The canonical concern is preserved from the orchestrator doc: OOS exposure is single-use and quarantined
(ROADMAP Phase 8.5 problem: `OOS Holdout: UNEXPOSED_PRISTINE`). `[VERIFIED FACT — ROADMAP §Phase8.5; D5 surface §1.2.10]`

---

## 24. Data Vintage / Archive / PIT Decision

### 24.1 Preserved findings (Class C — do not silently upgrade CONDITIONAL → SECURE)

- Macro calendar PIT is `[ACCEPT]` / SECURE where supported (pre-announced, versioned schedules; registry
  §108; bootstrap review §145). `[VERIFIED FACT]`
- Index vintage is `[CONDITIONAL]` and requires **as-published** archive + provenance (bootstrap review §147
  rebasing/lookahead trap; readiness §11). `[VERIFIED FACT]`

### 24.2 Required archive/PIT artifact set (D17 — binding details are Human choice)

For every source used, the frozen manifest must record at least:
- source identity (S-ID); retrieval timestamp; source version if available; raw archive; manifest; digest
- timezone normalization; event timestamp provenance; index data provenance; SPY data provenance if used;
  corporate-action provenance if SPY used
- no silent replacement of archived data (registry §107 archive-at-retrieval). `[VERIFIED FACT]`

If a source cannot establish the required PIT property: it must REMAIN `UNVERIFIED / CONDITIONAL`; the
candidate run cannot silently proceed on the weaker basis. `[VERIFIED FACT — doctrine-3; readiness §11]`

---

## 25. Reproducibility / Manifest Decision

### 25.1 Future frozen manifest binding set (D18 — binding set is Human choice; not implemented here)

The future frozen manifest SHOULD bind at least: candidate ID · specification version · source IDs ·
source retrieval timestamps · event universe · timestamp convention · event window · return formula ·
baseline · instrument · cost assumptions · parameter grid · K · IS/OOS/blind dates · statistical protocol ·
kill conditions · PASS/FAIL/INVALID semantics. `[MODEL INFERENCE — task mandate §23]`

### 25.2 No runtime implementation in this task

No manifest schema, hashing, or orchestrator change is made here. `[VERIFIED FACT — task mandate §23]`

### 25.3 Additional reproducibility decisions surfaced (readiness AU / BI / BK — `HUMAN DECISION REQUIRED`)

The readiness review flagged three further reproducibility-adjacent gaps that must be bound before any
authorized empirical run (they are Class B, not n/a):

- **AU — Drift / rounding / precision policy:** exact rounding/precision rule, float determinism, and the
  policy for numerical drift (e.g., tolerance constants) must be pre-declared; no silent `max(floor)`
  fallbacks (AGENTS.md fail-closed doctrine). `[VERIFIED FACT — readiness §9 AU]`
- **BI — Abort / INVALID audit logging:** how an aborted or INVALID trial is logged, who records it, and
  that it remains a census member with `failure_reason` (D6 Option A, ratification record §10) — no
  silent drop. `[VERIFIED FACT — readiness §9 BI; ratification record §10]`
- **BK — Environment / toolchain pin:** python/package/toolchain pinning and how it is bound into the
  manifest/lineage (orchestrator §6 requires `pyproject_toml_sha256` / `uv_lock_sha256` / `git_commit_hash`
  as explicit inputs). `[VERIFIED FACT — readiness §9 BK; phase5 production orchestration readiness §6]`

These three require explicit Human binding within the reproducibility decision (D18). `[MODEL INFERENCE]`

---

## 26. Kill Conditions

### 26.0 RATIFIED (2026-09-10)

**D19 = HUMAN-RATIFIED / BOUND** as an INTEGRITY / PROTOCOL KILL SET ONLY (worksheet O.10, verbatim).
- Trigger: pre-specified data, provenance, protocol, or governance integrity violations that make the
  experiment uninterpretable. Threshold: deterministic zero-tolerance (>0). Scope: global for
  experiment-level invariants. Result status: INVALID. Evaluation window: pre-run and/or during IS/OOS
  validation per the pre-specified invariant (no outcome-dependent evaluation). Timing: preconditions
  before execution; deterministic checks during execution; global integrity checks before final verdict;
  no kill rule selected/activated after observing outcomes. K-membership: NOT part of K; K remains the
  frozen declared census K = 3.
- Trigger catalog (5): (1) duplicate admitted event > 0; (2) required provenance/source-binding
  integrity violation > 0; (3) calendar/session authority mapping violation > 0; (4) required observation
  or required statistical input becomes non-finite or structurally invalid > 0; (5) violation of a frozen
  protocol invariant that makes the experiment uninterpretable > 0.
- Frozen rules preserved and NOT redefined by D19: O-2 overlap handling, G-3a purge, TR-1 deterministic
  event ordering, CA-1 session/calendar validity, T_eff INVALID/fail-closed handling, D6 census semantics.
  Where a violation of an existing frozen rule makes the experiment uninterpretable, the violation may be
  classified as an integrity failure under D19 without changing the underlying rule.
- Performance, effect size, alpha, p-values, t-statistics, returns, and empirical weakness are **D20
  matters, not D19 matters**. `[VERIFIED FACT — Human ratification 2026-09-10; worksheet O.10]`

### 26.1 Current state

Kill conditions are now **HUMAN-RATIFIED / BOUND** (2026-09-10, worksheet O.10). `[VERIFIED FACT]`

### 26.2 Human decision table (D19)

For each kill condition, Human must specify:
- exact trigger
- exact threshold
- evaluated globally or per event family
- results in FAIL or INVALID (per D6 semantics)
- evaluated in IS, OOS, or both
- checked before/after all trials
- whether the kill condition is itself part of K

`HUMAN DECISION REQUIRED` for any D19 change — the ratified set is BOUND; only a new Human governance
action may amend it. **D20 acceptance thresholds are also BOUND (2026-09-10, worksheet O.11).** No
thresholds are invented. Canonical thresholds (e.g., gate OOS minimum = 4 observations; PBO < 0.25;
DSR ≥ 0.95) exist ONLY where cited; they are distinguished from candidate-specific kill conditions and
are NOT auto-imported.
`[VERIFIED FACT — Human ratification 2026-09-10; worksheet O.10/O.11; ROADMAP Phase 6; D5 surface §D5-8]`

---

## 27. PASS / FAIL / INVALID Semantics — D20 RATIFIED (2026-09-10)

### 27.0 Canonical D6 semantics (preserved, unchanged)

Preserved verbatim from ratified D6 (Class C — semantics are canonical and NOT open to change):

| Status | Execution | Evidence | Meaning |
|--------|-----------|----------|---------|
| PASS | executed successfully | full evidence + acceptance criteria satisfied | acceptance met |
| FAIL | executed successfully | full evidence + acceptance criteria NOT satisfied | negative empirical evidence (valid) |
| INVALID | integrity/data/protocol/infrastructure failure | none (fails closed) | NOT negative empirical evidence; invalid interpretation |

- INVALID is NOT negative evidence. `[VERIFIED FACT — D6 surface §A5; readiness §25]`
- FAILED/INVALID remain in the census. `[VERIFIED FACT — ratification record §10]`
- No fabricated evidence (return=0 / Sharpe=0 / p=1 / neutral / imputed / zero-filled). `[VERIFIED FACT — ratification §10]`

### 27.1 D20 RATIFIED ACCEPTANCE CRITERIA (2026-09-10, worksheet O.11)

The Human has ratified the candidate-specific acceptance criteria for MACRO-001:

- **Statistical hypothesis:** H0: E[D] = 0; H1: E[D] != 0
- **Test:** Two-sided t-test
- **Reference degrees of freedom:** df = G - 1 (G = realized number of frozen T2 family × quarterly
  clusters used by the canonical variance authority)
- **Significance level:** α = 0.05
- **Primary acceptance criterion:** p < 0.05 => **PASS**; p ≥ 0.05 => **FAIL**
- **Effect magnitude:** descriptive only; no additional numeric effect-size acceptance threshold imposed
- **D19 interaction:** any valid D19 integrity/protocol kill results in INVALID per already-ratified
  D19/D6 semantics; D19 not redefined by D20
- **Frozen K:** K remains exactly 3 declared census cells; D20 does not change K or multiplicity
  semantics
- **No automatic import:** PBO < 0.25, DSR ≥ 0.95, OOS minimum = 4, T_eff ≥ 25, N_valid ≥ 250,
  Holm, effective-K reinterpretation, F-1 thresholds, Phase-6 thresholds — NOT imported
- **No additional criterion:** no additional performance/return/effect-size/Sharpe/magnitude cutoff
  required beyond the statistical acceptance criterion above

`[VERIFIED FACT — Human ratification 2026-09-10; worksheet O.11]`

ROUND 5 = **COMPLETE (2026-09-10)** — both D19 (§26.0) and D20 (this section) are bound and consistent.
No advance beyond Round 5 without separate authorization. `[VERIFIED FACT — worksheet O.11]`

---

## 28. Pre-Registration Freeze Checklist

HARD BLOCKING status — every unchecked substantive item keeps pre-registration NOT FROZEN.

```
[ ] Event universe frozen
[ ] Timestamp source frozen
[ ] Timezone frozen
[ ] Event window frozen
[ ] Return formula frozen
[ ] Direction/hypothesis frozen
[ ] Instrument role frozen
[ ] Baseline frozen
[ ] Overlap rule frozen
[ ] Cost model frozen
[ ] Parameter grid frozen
[ ] K computed and frozen
[ ] Statistical protocol frozen
[ ] Multiple-testing semantics frozen
[ ] IS dates frozen
[ ] OOS dates frozen
[ ] Blind dates frozen
[ ] PIT/data-vintage rules frozen
[ ] Data archive requirement frozen
[ ] Manifest schema frozen
[x] Kill conditions frozen                → D19 (worksheet O.10, HUMAN-RATIFIED 2026-09-10)
[x] PASS criteria frozen                   → D20 (worksheet O.11, HUMAN-RATIFIED 2026-09-10, p < 0.05 => PASS)
[x] FAIL criteria frozen                   → D20 (worksheet O.11, HUMAN-RATIFIED 2026-09-10, p >= 0.05 => FAIL)
[x] INVALID criteria frozen                → D20 (worksheet O.11, HUMAN-RATIFIED 2026-09-10, INVALID = D6/D19 integrity semantics)
[ ] Reproducibility requirements frozen
[ ] Human authorization recorded
```

```
Any unchecked substantive item ⇒  PRE-REGISTRATION NOT FROZEN
                                  EMPIRICAL VALIDATION NOT AUTHORIZED
```

Current status: **4/26 checked** (items: "Kill conditions frozen" = D19, HUMAN-RATIFIED/BOUND 2026-09-10;
"PASS criteria frozen" / "FAIL criteria frozen" / "INVALID criteria frozen" = D20, HUMAN-RATIFIED/BOUND
2026-09-10, worksheets O.10/O.11). The other 22 items remain unchecked; pre-registration is NOT fully
frozen. ROUND 5 = COMPLETE (D19 + D20 both bound). `[VERIFIED FACT — worksheets O.10/O.11; this surface]`

---

## 29. Human Decision Record

To be filled by Human Governance. Field templates (NOT pre-filled by the agent):

```
Decision ID:        D1 / D2 / ... / D22
Decision:           HUMAN DECISION REQUIRED
Rationale:          ______________________
Effective specification version:  ______________________
Decision date:      ______________________
Authority:          HUMAN GOVERNANCE
```

The agent does NOT fabricate signatures, names, dates, approvals, or authorization IDs. `[VERIFIED FACT — task mandate §27]`

---

## 30. Governance Options

**OPTION A** — Bind all substantive specification gaps and proceed toward pre-registration freeze.
This does NOT itself authorize empirical validation.

**OPTION B** — Conduct additional non-empirical feasibility/research work before binding.

**OPTION C** — Defer candidate.

**OPTION D** — Reject candidate.

**OPTION E** — Stop and preserve current state.

No option is selected here. Human decides. `[VERIFIED FACT — task mandate §28]`

---

## 31. Final Stop Condition

```
STOP — CAND-FREE-MACRO-001 HUMAN SPECIFICATION DECISION SURFACE COMPLETE.

Current status remains:
    CONDITIONALLY READY
    PRE-REGISTRATION NOT FULLY FROZEN
    EMPIRICAL VALIDATION NOT AUTHORIZED
    BACKTEST NOT AUTHORIZED
```

```
No HYP_003.
No ResearchReInceptionGate.
No R1.
No Phase 6 execution.
No trading.
No capital deployment.
Only Human Governance may convert the decision surface into a frozen pre-registration.
```

---

## 32. No Silent Decisions (manual, agent attestation)

The agent did NOT guess, infer, choose-the-most-convenient, choose-the-conventionally-statistical, or
choose-the-performance-likely value for any substantive parameter. Every unresolved substantive parameter
is recorded as `HUMAN DECISION REQUIRED` with alternatives and implications (see decision table §8, window
§11, return §12, baseline §15, grid §18, K §19, IS/OOS §22, blind §23, kill §26). The agent is an
auditor / specification-preparation role, NOT the final research governance authority. `[VERIFIED FACT — task mandate §30; governance doctrine]`

---

## 33. Final Governance Statement

CAND-FREE-MACRO-001 remains:
- **CONDITIONALLY READY** (status unchanged; readiness package §5).

Pre-registration remains:
- **NOT FULLY FROZEN** (4/26 freeze-checklist items bound — "Kill conditions frozen" = D19 (worksheet
  O.10), "PASS/FAIL/INVALID criteria frozen" = D20 (worksheet O.11), HUMAN-RATIFIED 2026-09-10;
  remaining 22 items pending Human decisions; this surface binds nothing directly). ROUND 5 = COMPLETE.

Empirical validation remains:
- **NOT AUTHORIZED**.

Backtest remains:
- **NOT AUTHORIZED**.

F-1 governance / F-1 candidate status: **UNCHANGED**.

Candidate registry semantics: **UNCHANGED** (status `HUMAN_REVIEW_REQUIRED`, unchanged).

HYP_003: **ABSENT**. R1: **NOT STARTED**. ResearchReInceptionGate: **NOT INVOKED**. Phase 6 gate:
**NOT EXECUTED**. Trading / broker / capital: **LOCKED / DISCONNECTED / $0.00**.

This document does not itself claim that CAND-FREE-MACRO-001 is READY-to-validate, VALIDATED, PROFITABLE,
or an HYP. It is a decision surface for Human Governance. `[VERIFIED FACT — this document's contract]`

---

### Verification Ledger
- Implementation Status: **COMPLETE** (documentation-only decision surface; no code/test change).
- Contract Enforcement: **STRICT FAIL-CLOSED** — all substantive gaps recorded `HUMAN DECISION REQUIRED`; no silent selection; no authorization claims.
- Mathematical Authority: **CANONICAL SPEC / RATIFIED RECORDS** referenced; no numbers computed; no statistical method invented.
- Local Test Suite: **NOT RUN** (docs-only).
- Type Checker (MyPy): **NOT RUN** (docs-only).
- Remote CI Status: **NOT APPLICABLE** (docs-only).
- Methodological Caveats: conflicts C1–C5 cited with paths and left for Human; Class-A defaults remain confirm-required; Class-C constraints are recorded from ratified governance, not invented here; no freeze executed by this document.