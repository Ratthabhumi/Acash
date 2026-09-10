# CAND-FREE-MACRO-001 - ROUND 4 SPECIFICATION (DERIVED ITEMS + HUMAN-DEPENDENT SURFACE)

## 0. Document Status

- Classification: **[ROUND 4 SPECIFICATION PARTIAL - UPDATED POST-RATIFICATION]** - documentation-only
  derivation of all structurally derivable Round 4 items. D14/D15/D16 + EX + CO are Human-BOUND via
  worksheet Section O; TR and CA remain genuinely Human-open (canonical definitions absent).
- Nature: pre-registration-preservation work. No authorization is granted by this document.
- Effective date: 2026-09-10 (environment date).
- Non-ASCII: none (ASCII-only file).
- Ancestry: this record is the dedicated Round 4 derivation referenced by the live binding worksheet
  (Sections N.7 and O.9). The worksheet remains the single designated live binding document.
- Review requirement (AGENTS.md #1 Zero Unverified Claims): every claim below carries an explicit
  evidence label. No value is invented; no Human choice is taken.

```
[DOCUMENTATION-ONLY]
[NON-EMPIRICAL]
[NON-AUTHORIZING]
[D14/D15/D16 BOUND - IS 2013-12-01->2021-12-31 / OOS 2022-01-01->2024-12-31 / BLIND 2025-01-01->2026-09-10]
[EX BOUND] [CO BOUND (SPY cost DEFERRED)]
[HUMAN DECISION REQUIRED - TR (tie-break secondary key)]
[HUMAN DECISION REQUIRED - CA (authoritative trading-calendar/session source)]
[ROUND 5 NOT REACHED]
```

## 1. Entry Audit (ROUND 4 entry condition - MET)

- S-2 (S2-B, t reference df = G-1, G = calendar-cluster count under T2): **BOUND**.
- S-7 calendar block (T2 quarterly, two-way family x calendar preserved): **BOUND**.
- S-7 T_eff (F2 variance-ratio with exact formula, ratified): **BOUND**.
- S-9 (Q-1a/Q-2c/Q-3a/Q-4): **BOUND**.
- K = 3 declared grid cells; Round 3B protocol intact; D6 census semantics intact. `[VERIFIED FACT -
  worksheet Section M/N]`
- ROUND 4 entry condition per worksheet K.7 ("S-2/S-7/S-9 fully derivable OR Human-bound"):
  **SATISFIED** by Section N. `[VERIFIED FACT - this record]`

## 2. Round 4 Inventory - Classification per Item

| Item | Classification | Basis |
|------|----------------|-------|
| IS window (D14) | **BOUND 2013-12-01 -> 2021-12-31** | worksheet O.1 |
| OOS window (D15) | **BOUND 2022-01-01 -> 2024-12-31** (no new min; no embargo) | worksheet O.1 |
| Blind window (D16) | **BOUND 2025-01-01 -> 2026-09-10** (BLIND HOLDOUT) | worksheet O.1 |
| Calendar boundaries | DERIVED (T2 quarterly) | S-5(c)/S-7 ratified |
| Event inclusion/exclusion | PRESERVED (A1); EX edge rule **BOUND** (official-calendar admission) | worksheet O.4; readiness 11.1 |
| Event timestamps / timezone | PRESERVED (A2: official release timestamp, primary official source, US ET, archived) | worksheet J ROUND 0 |
| Event collision handling | PRESERVED (D8 = O-2: drop later event by chronological event timestamp) | worksheet J ROUND 2 |
| Deterministic ordering / tie-break | **HUMAN CHOICE - TR OPEN** [HUMAN DECISION REQUIRED] | worksheet O.3; canonical secondary key absent |
| Purge | PRESERVED (G-3a: event-day + next trading day) | worksheet J ROUND 3A |
| Return construction | PRESERVED (D4 = R-EC) | worksheet J ROUND 1 |
| Baseline | PRESERVED (D7 = B-A) | worksheet J ROUND 2 |
| Valid/INVALID semantics | PRESERVED (S-8(b+c); D6; no imputation) | worksheet J ROUND 3B |
| Two-way clustering | PRESERVED (S-5(c): family x calendar) | worksheet J ROUND 3B |
| Quarterly calendar blocks | PRESERVED (T2) | Section M/N |
| T_eff formula | PRESERVED (F2 ratified formula) | Section N.1 |
| K / trial census | PRESERVED (K = 3) | worksheet J ROUND 3A |
| SUCCESS/FAILED/INVALID | PRESERVED (D6: census members; mixed census fails closed) | worksheet J ROUND 0 |
| D9 primary cost | DERIVED (SPX primary = $0, no executable cost claim) | 17.1 preserved; registry 109 |
| D9 SPY robustness cost model | **BOUND - DEFERRED** (CO: DEFERRED - ROBUSTNESS/IMPLEMENTATION LAYER; outside formal census; no cost values invented) | worksheet O.6; readiness 13; decision surface 17.2 |
| Manifest identity (D18) | DERIVED structurally (binding set per surface 25.1); schema assembled after rounds 1-5 complete | decision surface 25.1; worksheet C |
| Run identity | DERIVED structurally (candidate ID + spec version + manifest hash + retrieval timestamps) | decision surface 25.1; registry 107 |
| Data/version provenance (D17) | DERIVED structurally (archive-at-retrieval + digest manifest; S-04/S-08/S-05 primary, S-10/S-18 SPY-conditional) | worksheet C; registry 107 |
| Reproducibility | DERIVED structurally (archive-at-retrieval, digest, manifest, config_sha256/return_sha256 binding points) | readiness 20; registry 107 |
| Pre-registration structure | PRESERVED (process: all B rounds + Group C + anti-HARKing, then Draft Freeze) | worksheet F |
| Anti-HARKing | PRESERVED (process: K frozen, no grid expansion, no post-result selection) | registry 195-202; worksheet D |

## 3. Derived / Preserved Round-4 Items (bound for the draft specification)

### 3.1 Calendar boundaries

- Calendar cluster = one (family x calendar-quarter) cell (T2). Quarter boundaries split clusters even
  within one calendar year. `[VERIFIED FACT - worksheet Section L.3/T2; M.1]`
- O-2 operates first (drop later overlapping event by chronological event timestamp); surviving valid
  events are re-assigned to their (family x quarter) cluster; no cluster spans two quarters. `[MODEL
  INFERENCE - T2 definition applied to O-2]`

### 3.2 Event inclusion / exclusion (core)

- Event universe = FOMC + CPI + NFP, one shared protocol (A1). `[VERIFIED FACT - worksheet J ROUND 0]`
- Overlap = D8/O-2 (later event dropped by deterministic event timestamp). No double-counting without
  a pre-registered rule. `[VERIFIED FACT - worksheet J ROUND 2]`
- Edge rule for unscheduled/emergency events: **EX BOUND** (worksheet O.4) - an event is admitted into
  the census IFF it is a scheduled official release of exactly one of the three frozen families that
  appears on the official pre-announced release calendar (S-08 Fed calendar for FOMC; S-05 BLS calendar
  for CPI/NFP); unscheduled/emergency announcements excluded; no new family; no outcome-based/manual
  classification; scheduled-but-delayed releases remain census events with A2 actual-release timestamps
  and as-published vintage. `[VERIFIED FACT - A1/content readiness 11.1; MODEL INFERENCE - application]`

### 3.3 Timestamps / timezone / ordering

- Timestamp = official release timestamp; primary official source; US Eastern Time; archive release
  times at retrieval (A2). `[VERIFIED FACT - worksheet J ROUND 0]`
- O-2 drop rule = deterministic chronological event-timestamp ordering (no post-hoc ordering). `[VERIFIED
  FACT - worksheet J ROUND 2]`
- Equal-timestamp tie-break rule: **TR OPEN - [HUMAN DECISION REQUIRED]** (worksheet O.3). Must be
  pre-registered before validation, never chosen after seeing data; the canonical corpus defines NO
  adequate secondary key, so the agent does not invent one (Human guarded conditional fired). `[VERIFIED
  FACT - worksheet J ROUND 2; worksheet O.3]`

### 3.4 Purge / return / baseline

- Purge = event-day + next trading day excluded from baseline (G-3a). `[VERIFIED FACT]`
- Return = `R_EC(i) = Close(next trading day) / Close(event day) - 1` (D4). `[VERIFIED FACT]`
- Baseline = B-A: all non-event, non-purged trading days, same 1-trading-day horizon. `[VERIFIED FACT]`
- Deviation object: `D_i = R_EC(i) - mu_baseline(cell)` per declared cell. `[MODEL INFERENCE - S-1/D4/D7]`

### 3.5 Statistical protocol (as frozen, re-affirmed)

- Null: `H0: E[D] = 0` vs `H1: E[D] != 0`, two-sided (S-3/S-4(b)); sign descriptive only. `[VERIFIED FACT]`
- Test statistic: `t = mean(D) / SE_cluster_robust(mean(D))`; two-way cluster (family x quarter, T2);
  cluster-robust SE (S-6(a)). `[VERIFIED FACT]`
- Reference distribution: `t(G - 1)`, G = relevant calendar-cluster count under T2 for the IS window
  (realized at run time; not numerically preset). `[VERIFIED FACT - S2-B]`
- T_eff: `min(N_valid, s_D^2 / Var_CR(D_bar))` per ratified N.1; FAIL-CLOSED on non-finite/non-positive
  denominator; diagnostic only; does not alter inference. `[VERIFIED FACT - Section N.1]`
- Inference sample: IS-based (S-10); IS/OOS dates now BOUND (worksheet O.1):
  IS 2013-12-01 -> 2021-12-31; OOS 2022-01-01 -> 2024-12-31; BLIND 2025-01-01 -> 2026-09-10. `[VERIFIED FACT]`

### 3.6 Census & costing

- Census: `FOMC/W-B/B-A/SPX`, `CPI/W-B/B-A/SPX`, `NFP/W-B/B-A/SPX` = 3 declared cells. `[VERIFIED FACT]`
- SUCCESS + FAILED + INVALID all remain census members; no imputation; mixed census fails closed
  (D6). `[VERIFIED FACT]`
- Primary cost: SPX = research series at $0, NO executable trading-cost claim (preserved canon 17.1;
  registry 109). Cost does NOT enter the primary test. `[VERIFIED FACT]`
- SPY = robustness/implementation proxy OUTSIDE formal census (G-4b/G-6b); CO BOUND (worksheet O.6):
  `DEFERRED - ROBUSTNESS/IMPLEMENTATION LAYER`; SPY must not block the SPX statistical specification;
  no cost value introduced. `[VERIFIED FACT]`

### 3.7 Identity / provenance / reproducibility (structural, Group C memberships)

- D17 data vintage/archive/PIT: primary S-04 (SPX official), S-08 (FOMC), S-05 (CPI/NFP), S-06
  (support); SPY-conditional S-10/S-18; archive-at-retrieval + digest + manifest schema; as-published
  vintage. `[VERIFIED FACT - worksheet C; readiness 19]`
- D18 manifest binding set (future frozen, structural): candidate ID, spec version, source IDs +
  retrieval timestamps, event universe, timestamp convention, event window, return formula, baseline,
  instrument, cost, grid, K, IS/OOS/blind, statistical protocol, kill, PASS/FAIL/INVALID. Schema
  assembled AFTER all rounds 1-5 complete. `[VERIFIED FACT - decision surface 25.1]`
- Run identity: candidate ID + frozen spec version + manifest digest + retrieval timestamps; hashing
  points (config_sha256 / return_sha256 / K ledger) per readiness AL/20. `[MODEL INFERENCE - surface 25]
- Reproducibility: archive-at-retrieval frozen (registry 107); manifest + digest binding; ABSOLUTELY no
  silent replacement of archived data. `[VERIFIED FACT - registry 107]`

### 3.8 Pre-registration / anti-HARKing structure

- Sequence preserved: ROUND 4 dates (Human) -> ROUND 5 kill/PASS/FAIL/INVALID + alpha (Human) ->
  Group C (D17/D18) -> Draft Freeze -> anti-HARKing review -> Human authorization -> empirical run.
  `[VERIFIED FACT - worksheet F]`
- No parameter search, no optimization, no empirical step in this record. `[VERIFIED FACT - this record]`

## 4. Genuine Human Choices (Round 4) - RESOLVED vs REMAINING

| ID | Item | Resolution (post worksheet O) |
|----|------|-------------------------------|
| D14 | IS window dates | **BOUND** - 2013-12-01 -> 2021-12-31 (worksheet O.1) |
| D15 | OOS window dates | **BOUND** - 2022-01-01 -> 2024-12-31; no new per-family min; no embargo; no SplitPolicy embargo import (worksheet O.1) |
| D16 | Blind window | **BOUND** - 2025-01-01 -> 2026-09-10 BLIND HOLDOUT; prohibited information list fixed (worksheet O.1) |
| EX | Event exclusion edge rule | **BOUND** - official-calendar admission rule (worksheet O.4) |
| CO | SPY robustness cost model | **BOUND** - DEFERRED - ROBUSTNESS/IMPLEMENTATION LAYER (worksheet O.6) |
| TR | Tie-break rule (equal event timestamps) | **REMAINING - [HUMAN DECISION REQUIRED - TR]** - canonical secondary key absent; must not be invented (worksheet O.3) |
| CA | Session/calendar rule (half-days, holidays) | **REMAINING - [HUMAN DECISION REQUIRED - CA]** - authoritative US trading-calendar/session source absent; must not be invented (worksheet O.5) |

Note: D14/D15/D16/EX/CO are Human-BOUND. TR and CA remain open genuine Human decisions; each must be
bound before any authorized empirical run. Round 4 is therefore PARTIAL. `[VERIFIED FACT - worksheet O.1/O.3/O.4/O.5/O.6]`

### 4.1 TR Decision Surface (prepared - NOT decided)

**Evidence search (this run).**
- Canonical MACRO-001 corpus: no adequate secondary key exists. Worksheet ROUND 2/D8 mandates only
  that a tie-break MUST be pre-registered before validation and never chosen after data. `[VERIFIED
  FACT - worksheet J ROUND 2; worksheet O.3]`
- Repository-wide search incl. `src/`: no domain-general secondary-key / tie-break contract declared
  applicable to MACRO-001. `src/acash/backtest/equity_returns.py:68` ("equal timestamps are preserved in
  row order") and `src/acash/backtest/adapter.py:135` (Phase 3B 5-tuple total ordering) are
  Phase-5/6 execution-domain semantics - NOT declared domain-general. `phase14_evidence_bridge_
  ratification_D1_D9.md` "canonical tie-break/order semantics" binds the F-1 / Phase 5/6 series domain
  only. `[VERIFIED FACT - source inspection, this run]`
- Conclusion: `TR = HUMAN DECISION REQUIRED`.

**Canonical inputs available as components of a Human-chosen key (already bound, nothing invented).**
- Event family (A1), 3-valued: FOMC / CPI / NFP. `[VERIFIED FACT]`
- Official release timestamp (A2) - primary sort key; equal timestamps are the tie case. `[VERIFIED FACT]`
- Source authority ID (source registry): S-08 (FOMC), S-05 (CPI and NFP) - note S-05 is SHARED by
  CPI/NFP, so a source ID alone cannot separate two BLS-released families. `[VERIFIED FACT]`
- Official scheduled-calendar entry (readiness 11.1): pre-announced versioned schedules S-05 (BLS,
  8:30am ET convention) / S-08 (Fed, 2:00pm ET). `[VERIFIED FACT - source registry 60/77]`
- Archive-at-retrieval timestamps (A2) - NOT recommended as a key component (retrieval-order
  dependent; violates determinism). `[MODEL INFERENCE]`

**Minimum Human decisions - select one rule (the agent will NOT select).**

| ID | Candidate rule | What the Human must supply |
|----|----------------|----------------------------|
| TR-1 | Secondary key = scheduled-calendar date, then a Human-defined family order | the family order (e.g., CPI < NFP < FOMC) |
| TR-2 | Composite key = (source ID, scheduled-calendar date, family) | ordering across all three fields |
| TR-3 | Family-order-only key over the Frozen family set (no date component) | the family order |
| TR-4 | Adopt an explicit existing repository ordering contract for MACRO-001 | name exact file/line + declare applicability (agent cannot) |
| TR-5 | Human-defined composite, stated in words | full rule text |

**Constraints regardless of choice (Class C).**
- Pre-registered before validation; never chosen after seeing data (worksheet ROUND 2). `[VERIFIED FACT]`
- Deterministic, tie-symmetric, reproducible; no row-order / retrieval-order dependence (doctrine-10;
  perm & tie invariance). `[VERIFIED FACT]`
- No manual or outcome-based selection. `[VERIFIED FACT]`
- Use the SAME ordering for event-census ordering and the D18 manifest ordering record.
  `[MODEL INFERENCE - D18 manifest binding set, surface 25.1]`

### 4.2 CA Decision Surface (prepared - NOT decided)

**Evidence search (this run).**
- Canonical MACRO-001 corpus: NO authoritative US trading-calendar/session rule. A2 (worksheet ROUND 0;
  surface 10.1) is event-timestamp semantics only - it does NOT define a trading calendar/session.
  readiness AX: "Session/calendar (half-days, holidays) Not specified ... SPECIFICATION GAP - HUMAN
  DECISION REQUIRED". readiness Z: "Missing-data / halted sessions rule Not specified ... SPECIFICATION
  GAP - HUMAN DECISION REQUIRED". `[VERIFIED FACT]`
- Repository-wide search incl. `src/`: zero matches for holiday / half-day / valid session / trading
  calendar / market calendar / exchange calendar. No canonical calendar utility exists. `[VERIFIED
  FACT - source inspection, this run]`
- F-1 candidate frozen session-validity rule ("early-close with a valid official close IS a valid
  session; deterministic valid-session calendar; no manual shifting") is F-1-isolated and NOT
  importable. `[VERIFIED FACT - isolation boundary; worksheet C]`
- Conclusion: `CA = HUMAN DECISION REQUIRED`.

**Canonical inputs (bound) relevant to CA.**
- Event calendars are pre-announced official schedules (S-05 BLS 8:30am ET convention; S-08 FOMC
  statement 2:00pm ET) - they define event dates/times, they are NOT trading calendars. `[VERIFIED
  FACT - source registry 60/77]`
- D3 = W-B, D4 = R-EC: event-day close -> next trading-day close; trading-day basis; "shift forward"
  holiday ruling in the window definitions (surface 11.2). `[VERIFIED FACT]`
- Audit note: surface 66 lists SPX/SPY daily from S-10/S-18 and S-04 = VIXCLS; readiness 49 text reads
  "SPX index values (S-04 primary)". This inconsistency must be resolved in Group C / D17 so that the
  CA "official close" has ONE pinned close series. `[MODEL INFERENCE - audit note; NOT a TR/CA decision]`

**Minimum Human decisions - select one calendar authority (the agent will NOT select).**

| ID | Candidate authority | What the Human must supply |
|----|--------------------|----------------------------|
| CA-1 | NYSE official trading/market-holiday calendar as the valid-session authority for the SPX close series | confirm the calendar provider/source URL + versioning/archive |
| CA-2 | Session validity aligned with the frozen close-series provider's own published trading dates | pin the authoritative SPX close series first (Group C/D17) |
| CA-3 | Human-defined deterministic calendar rule | full rule text |
| CA-4 | Explicitly authorize adoption of a named repo calendar/primer contract for MACRO-001 | name exact file/line + declare applicability |

**Session semantics to confirm once a calendar authority is named (worksheet O.5 instruction + gaps).**
- Half-day / early-close: official close of that trading date is VALID for D4; no special half-day
  adjustment; event not moved to another date. `[VERIFIED FACT - worksheet O.5]`
- Event day not a trading day: map to next valid trading day (W-B "shift forward"). `[VERIFIED FACT -
  surface 11.2 W-B]`
- Missing / halted session (readiness Z): close unavailable -> observation INVALID / fail-closed per
  S-8(b+c)/D6; no imputation. `[MODEL INFERENCE - S-8(b+c)/D6 applied to readiness Z]`
- CPI/NFP 08:30 ET vs index open 09:30 ET: release precedes the regular session; at daily granularity
  the event-day close -> next-close return is unchanged; confirm no intraday special rule at $0 daily
  (readiness AX). `[MODEL INFERENCE - D4 at daily granularity]`

## 5. IS/OOS/Blind Decision Surface (reproduced for the record - D14/D15/D16 now BOUND)

The TR and CA decision surfaces are prepared at Section 4.1 and Section 4.2 above (NOT decided).
The IS/OOS/blind surface reproduced below is included for the archival record only.

> - exact IS start; exact IS end; exact OOS start; exact OOS end
> - OOS completely untouched (never participates in any parameter/grid choice)
> - min event counts per family in IS and OOS separately
> - quarantine/embargo overlap rules; required gap/embargo
> - whether the canonical SplitPolicy percentages (train 0.60 / val 0.20 / oos 0.20, embargo 5) apply
>   to an event-driven calendar or a Human-defined equivalent

> - exact blind start; exact blind end
> - information prohibited during blind period (no OOS event-outcome inspection)
> - whether source data may be retrieved during blind; whether event metadata may be inspected
> - whether aggregate diagnostics may be inspected
> - who/what is permitted to access OOS data (OosExposureState UNEXPOSED -> EVALUATED_LOCKED)

State that must hold regardless of date choice (Class C):

```
OOS dates MUST be fixed before empirical validation.
```

`[VERIFIED FACT - decision surface 22/23; readiness 17]`

## 6. STOP

```
[HUMAN DECISION REQUIRED - TR]   <- equal-timestamp tie-break: canonical secondary key absent (O.3)
[HUMAN DECISION REQUIRED - CA]   <- authoritative US trading-calendar/session source absent (O.5)
[ROUND 4 PARTIAL]
[ROUND 5 NOT REACHED]
[FREEZE NOT DECLARED]
```

D14/D15/D16/EX/CO are BOUND (worksheet O.1/O.4/O.6). The TR/CA Human Decision Surfaces are prepared at
Section 4.1 / 4.2 above - candidate options TR-1..TR-5 and CA-1..CA-4, plus the session-semantics
confirmation list. Next required Human response:

```
TR tie-break (equal event timestamps): select TR-1..TR-5 (or state a rule in words); supply the
  ordering/key components exactly as requested in the chosen row. Do not expect the agent to invent one.
CA authoritative US trading-calendar/session: select CA-1..CA-4 (or state a rule in words); then
  confirm the session-semantics list (half-day/early-close, event-not-a-trading-day, halted/missing,
  CPI/NFP 8:30 ET vs 9:30 ET open) from Section 4.2.
Decision date: ______________
```

## 7. Ledger

- Implementation Status: COMPLETE (Round 4 derivation record updated; TR/CA Human Decision Surfaces prepared at 4.1/4.2; document-only)
- Contract Enforcement: STRICT FAIL-CLOSED - nothing invented; D14/D15/D16/EX/CO bound via worksheet O; TR/CA surfaced as open with prepared decision surfaces (Human guarded conditionals honored); repo-wide + src/ search performed; no domain-general key/calendar contract declared applicable to MACRO-001
- Mathematical Authority: CANONICAL SPEC / HUMAN-RATIFIED RECORDS referenced; no statistics computed
- Local Test Suite: NOT RUN (docs-only)
- Type Checker (MyPy): NOT RUN (docs-only)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: Round 4 is PARTIAL - all derivable structural items resolved; D14/D15/D16 are the primary blocking Human choices with TR/EX/CA/CO contiguous items to be bound pre-run; Round 5, anti-HARKing, and draft freeze are deferred until the Human responds; no empirical step, no data, no backtest, no commit, no push.