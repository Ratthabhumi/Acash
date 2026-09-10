# CAND-FREE-MACRO-001 — Empirical Validation Readiness & Pre-Registration Package

**Document ID:** `docs/phase14/cand_free_macro_001_validation_readiness.md`

**Status:** `[PRE-AUTHORIZATION]` · `[NON-EMPIRICAL]` · `[NON-NORMATIVE]` · `[NO IMPLEMENTATION AUTHORITY]`

**Disposition under this package:** `CONDITIONALLY READY`

**Generated:** 2026-09-10 (local date), repo HEAD `fff20b9dcaec5e9eedcd56245d170f62ea402fc5`, `origin/main` identical.

---

## PREAMBLE — SCOPE, AUTHORITY, AND PROHIBITION

1. **PURPOSE.** This document is a **pre-authorization, non-empirical** audit of whether the CAND-FREE-MACRO-001
   specification, as frozen in the research registry (§ `free_data_research_registry.md`, item `CAND-FREE-MACRO-001-REG`),
   is **deterministic, auditable, and governance-clean enough** to be handed to a Human Governance body for a single,
   bounded, empirical-validation authorization decision. It is a **readiness & pre-registration package**, NOT a test.
2. **NON-EMPIRICAL CONTRACT.** No backtest, no market-data download for testing, no returns/Sharpe/CAGR/volatility/
   drawdown/win-rate/IC/t-stat/p-value computation, no event study, no regression, no parameter search/optimization,
   no portfolio simulation is performed anywhere in this document. No such computation appears in any section below.
   This document contains **zero** empirical results. `[VERIFIED FACT — this repository / this run]`
3. **GOVERNANCE PROHIBITION.** This document does NOT, and MUST NOT be read to: create or modify `HYP_003`; modify or
   start `R1`; invoke `ResearchReInceptionGate` / `ValidationGate` / `AlphaQualificationGate`; modify any `D1`–`D9`,
   `D5` / `D6` / `D8-B`, or registry semantics; modify `ROADMAP.md`; modify research doctrine; modify any gate
   mathematics or thresholds; modify the F-1 candidate; modify `CAND-FREE-MACRO-001` itself; authorize empirical
   validation, paper trading, live trading, or capital. Any governance gap discovered is recorded as a
   `SPECIFICATION GAP / HUMAN DECISION REQUIRED`, never silently filled. `[VERIFIED FACT — this document's contract]`
4. **AUTHORITY LEVEL.** This document is information for a Human Governance decision only. It is `NON-NORMATIVE` and
   confers **no** approval. No approval may be inferred from the existence of this document.
5. **EVIDENCE LABELS USED.** `[VERIFIED FACT]` (observed/confirmed in this repo or raw source), `[SOURCE CLAIM]`
   (reported in literature/vendor/authoritative source, not independently verified here), `[MODEL INFERENCE]`
   (reasoning/derivation), `[UNVERIFIED]` (not yet confirmed). Every readiness verdict is based ONLY on whether the
   frozen spec is sufficiently specified — NOT on any expected returns/edge expectation.

---

## 1. Header

| Field | Value |
|-------|-------|
| Candidate ID | `CAND-FREE-MACRO-001` |
| Registrar row | `free_data_research_registry.md` § CAND-FREE-MACRO-001 `[VERIFIED FACT]`|
| Research family | 1 — Public event/calendar effects `[VERIFIED FACT — registry]` |
| Mechanism reference | MEC-0001 — Scheduled Macro-Announcement Premium Conditioning (ssrn_mechanism_research.md §224 `[ACCEPT]`) `[VERIFIED FACT — registry & ssrn]` |
| Concept | M-V1 `[VERIFIED FACT — bootstrap governance review §104]` |
| Lane | FREE-DATA BOOTSTRAP `[VERIFIED FACT — registry classification]` |
| F-1 relation | **NOT F-1 / NOT HYP_003 / NOT R1** — belongs to FREE-DATA lane, kept fully isolated from F-1 `[VERIFIED FACT — registry & bootstrap review]` |
| Universe (frozen) | Index-level: SPX index values (S-04 primary); SPY (S-10/S-18) robustness cross-check `[VERIFIED FACT — registry]` |
| Governance status (as recorded) | PROPOSED → SPEC_FREEZING → **HUMAN_REVIEW_REQUIRED** (empirical authorization) `[VERIFIED FACT — registry §114]` |
| Empirical validation authorization | **NOT AUTHORIZED** (all five candidates) `[VERIFIED FACT — registry §209]` |
| Data feasibility status | `[ACCEPT]` `[VERIFIED FACT — registry §113]` |
| **Package disposition** | **CONDITIONALLY READY** — spec is concept-complete and data-clean, but several execution-level dimensions are a `SPECIFICATION GAP` requiring Human binding before any authorized empirical run `[MODEL INFERENCE — this audit]` |

---

## 2. Document Control / Authoring

| Field | Value |
|-------|-------|
| Author | ACASH automated agent (pre-authorization audit lane) |
| Authority | No authority beyond drafting this pre-authorization package `[VERIFIED FACT — this document's contract]` |
| Status (this doc) | `[PRE-AUTHORIZATION] [NON-EMPIRICAL] [NON-NORMATIVE]` |
| Review required | Human Governance (binding decision via OPTION A–E surface, §26) `[MODEL INFERENCE]` |
| Classification | Readiness & pre-registration artifact; NOT a spec change, NOT a test, NOT a governance mutation `[MODEL INFERENCE]` |

---

## 3. Introduction & Scope

3.1 CAND-FREE-MACRO-001 tests the mechanism that **scheduled macroeconomic announcements (FOMC, CPI, NFP)
concentrate information / re-price risk at known, pre-announced timestamps**, producing a conditional return/vol
realization that deviates from unconditioned behavior in a *direction discoverable only post-spec*. `[VERIFIED FACT — registry §100, §103]`

3.2 The **specified observable object** is the *event-conditioned time series* (conditional return / conditional
volatility behavior around scheduled releases) — **NOT a Sharpe ratio and NOT a promised return**. `[VERIFIED FACT — registry §103]`

3.3 DIRECTION IS EXPLICITLY PENDING: **"event-conditioned deviation, no ex-ante sign asserted."** `[VERIFIED FACT — registry §104]`

3.4 This package's job: (a) confirm the frozen spec is deterministic enough for a pre-registered replication;
(b) enumerate every dimension that is NOT yet deterministic (SPECIFICATION GAP / HUMAN DECISION REQUIRED);
(c) present a decision surface, without choosing on behalf of Human.

---

## 4. Methodology of this Audit (Readiness / Pre-Registration Only)

4.1 Approach: dimension-by-dimension audit of the frozen spec against a Bayesian-style pre-registration checklist
(67 audit dimensions, §9) modeled on ACASH research doctrine and FREE-DATA BOOTSTRAP charter §12 / §16 / §21 / §22 / §29.

4.2 Each dimension is classified `FROZEN` (deterministic from the frozen spec), `PROVISIONAL` (documented but not
binding), or `SPECIFICATION GAP` (not deterministically specified → `HUMAN DECISION REQUIRED`; never silently filled).

4.3 No experiment, no data, no numbers. All assertions sourced with epistemic labels.

4.4 The existence of a `SPECIFICATION GAP` is **not** a defect in the candidate's concept; it is a statement that the
frozen proposal is a *concept-level specification* rather than a *line-level executable pre-registration*. The registry
itself says the proposal is frozen "at the proposal boundary"; the governance review's "No `SPECIFICATION GAP`" claim
(§282) was made in the context of **governance friction / data feasibility**, not execution-level pre-registration
determinism. This package makes that distinction explicit. `[MODEL INFERENCE — reconciliation of registry §195-214, §105 and bootstrap review §282]`

---

## 5. Readiness Classification & Basis

**CLASSIFICATION: `CONDITIONALLY READY`**

| Sub-dimension | Status | Basis `[label]` |
|---------------|--------|-----------------|
| F-1 isolation | PASS — candidate is NOT F-1; lane isolation preserved | `[VERIFIED FACT — registry classification; F-1 docs]` |
| Governance legality (PIT / survivorship / cost / license) | PASS — PIT SECURE, survivorship CLEAN, cost defensible $0, feasibility `[ACCEPT]` | `[VERIFIED FACT — registry §108-113; bootstrap review §312]` |
| Spec determinism (execution-level) | **FAIL (SPECIFICATION GAP)** — window math, direction target object, universe-holder, event-timestamp rule, sampling/window, statistical semantics, IS/OOS, kill-conditions not deterministically frozen | `[MODEL INFERENCE — §9]` |
| Pre-registration completeness (§24) | **PARTIAL** — many items FROZEN, many `SPECIFICATION GAP` | `[MODEL INFERENCE — §24]` |
| Empirical results required for authorization | NONE (this is non-empirical) | `[VERIFIED FACT — §PREAMBLE]` |

**Verbatim readiness statement:** The candidate's **concept, data path, PIT, survivorship, cost, and governance
legality** are ready for a Human authorization **consideration**, BUT the frozen proposal does not yet declare a
single deterministic, executable, pre-registered protocol for the window/object/sign/statistics/trial-count/kill
conditions. Per §PREAMBLE-3 and the fail-closed doctrine, these are recorded as `SPECIFICATION GAP / HUMAN DECISION
REQUIRED`, NOT silently filled. Therefore: **CONDITIONALLY READY — a Human must bind the gaps before any authorized
empirical run.** `[MODEL INFERENCE — this audit's synthesis]`

---

## 6. Glossary / Reference Key

- **Event window** — the set of trading timestamps around an announcement over which the conditional object is measured.
- **Event-day ± opened** — registry's filed window phrase (§105). `[VERIFIED FACT — registry]`
- **Held window** — the durable exposure/measurement interval used by the governance review's "exact data path." `[VERIFIED FACT — bootstrap review §310]`
- **SPX (S-04)** — official SP500 (S&P 500) index daily values via FRED. `[VERIFIED FACT — source registry §53-54]`
- **SPY (S-10/S-18)** — SPDR S&P 500 ETF daily OHLCV; robustness cross-check (personal-use terms). `[VERIFIED FACT — source registry §89, §119]`
- **FOMC (S-08)** — Federal Reserve FOMC meeting calendar & statements (2011+; press-conference 2019+). `[VERIFIED FACT — bootstrap review §310]`
- **BLS (S-05)** — CPI/NFP release calendar + values (as-published vintage). `[VERIFIED FACT — source registry §59-61]`
- **Treasury (S-06)** — U.S. Treasury schedule (secondary). `[VERIFIED FACT — bootstrap review §310]`

---

## 7. Audit Trail (What Was Read in this Package)

`[VERIFIED FACT — this run]` — the following were read to build this package (all paths repo-relative):
- `docs/phase14/free_data_research_registry.md` (candidate identity, §90-216, status matrix §206-214)
- `docs/phase14/free_data_source_registry.md` (tiers §22, source IDs S-04/S-05/S-06/S-08/S-10/S-18)
- `docs/phase14/free_data_capital_bootstrap_program.md` (charter; STOP boundary)
- `docs/phase14/ssrn_mechanism_research.md` (MEC-0001 §224; pre-FOMC drift; post-2015 attenuation §531)
- `docs/phase14/bootstrap_mechanism_governance_review.md` (MEC-0001 ranked #1; rubric A–V; OPTION A–E; exact data path §310)
- `docs/phase14/research_doctrine.md`, `research_candidates.md`, `acash_market_research_ontology_v1.md`
- `docs/phase14/candidate_f1_flow_calendar_rebalance_review.md`, `f1_d1_*` governance docs (F-1 boundary; NOT modified)
- `docs/phase14/d6_statistical_semantics_decision_surface.md` (PASS/FAIL/INVALID semantics; NOT altered)

**No candidate-specific spec file other than the registry row exists** (verified via `glob **/*macro*`). `[VERIFIED FACT]`

---

## 8. Not-in-Scope

- Any empirical work of any kind (§PREAMBLE-2).
- Any governance mutation (§PREAMBLE-3).
- Any F-1 modification, including HYP_003 / R1 / Gate / D1 / D2 / D6 / F-1 candidate.
- Any decision on behalf of Human (surface presented only, §26).
- Any future data acquisition decisions (only queued in FUTURE DATA ACQUISITION QUEUE, §28).
- Any other candidate (VOL-001 / MOM-001 / REV-001 / PEAD-001) beyond cross-references.

---

## 9. Detailed Audit Dimensions (A–BO, 67 dimensions)

Legend: `FROZEN` = deterministic & binding from frozen spec · `PROVISIONAL` = documented, not binding ·
`SPECIFICATION GAP` = not deterministically specified; **binding by Human** required · `HUMAN DECISION REQUIRED` = same as GAP, explicit.

| ID | Dimension | Audit line | Verdict | Note |
|----|-----------|-----------|---------|------|
| A | Research family | Public event/calendar effects (family 1) | FROZEN | registry §99 `[VERIFIED FACT]` |
| B | Mechanism definition | Scheduled announcements re-price risk at known timestamps | FROZEN | registry §100 |
| C | Why it exists | Pre-announced, costless, economically meaningful; mechanism-first | FROZEN | registry §101 |
| D | Observable data set | S-08 FOMC; S-05 CPI/NFP; S-04 VIXCLS; S-10/S-18 SPX/SPY | FROZEN | registry §102 |
| E | Expected behavior statement | Conditional return/vol deviation from unconditioned; object = event-conditioned series | FROZEN | registry §103 |
| F | Direction of the object | PENDING — "no ex-ante sign asserted" | FROZEN (as an explicit null-direction) | registry §104 |
| G | Horizon / window phrase | `event-day ± opened` (registry) | FROZEN-at-phrase, **GAP-as-executable** | registry §105 vs bootstrap review §310 `event-day ± 1 td / 1-day held`; two phrasings not reconciled → `HUMAN DECISION REQUIRED` |
| H | Universe selection | Index-level SPX (S-04 primary) + SPY (S-10/S-18 cross) | FROZEN | registry §106; **NOTE** not F-1 universe |
| I | Data requirements | Schedules PIT-proven; index series; archive-at-retrieval | FROZEN | registry §107 |
| J | PIT requirement | FULL — schedules pre-announced | FROZEN | registry §108; bootstrap review §145 PIT SECURE |
| K | Cost requirement | $0 | FROZEN | registry §109 |
| L | Main falsification risk | No measurable conditional effect vs unconditioned baseline at $0 granularity | FROZEN | registry §110 |
| M | Main leakage risk | Calendar times published in advance; archive release times | FROZEN (mitigation FROZEN) | registry §111; bootstrap review §221 LOW |
| N | Main survivorship risk | NONE (index-level) | FROZEN | registry §112 |
| O | Data feasibility status | `[ACCEPT]` | FROZEN | registry §113 |
| P | Governance status | PROPOSED→SPEC_FREEZING→HUMAN_REVIEW_REQUIRED | FROZEN | registry §114 |
| Q | Family-1 source mapping | S-05/S-08/S-06 (schedules, PIT `[ACCEPT]`); S-10/S-18 (prices) | FROZEN | registry §32 family table |
| R | Event set (WHICH announcements count) | FOMC, CPI, NFP named; **no explicit inclusion/exclusion rule, no joint vs separate conditioning** | **SPECIFICATION GAP** | registry names three; not deterministic which, and whether each is tested independently or jointly → `HUMAN DECISION REQUIRED` |
| S | Event timestamp/timezone rule | Not specified (release 08:30 ET CPI/NFP ~ 14:00 ET FOMC, press conf 14:30 ET) | **SPECIFICATION GAP** | not deterministically defined in frozen spec → `HUMAN DECISION REQUIRED` |
| T | Window start/end math | "event-day ± opened" and "event-day ± 1 td" differ across docs; no algorithm | **SPECIFICATION GAP** | see G; `HUMAN DECISION REQUIRED` |
| U | Conditioned OBJECT (return series definition) | "conditional return/vol realization" conceptual; **no exact return formula, no log-vs-simple, no settlement rule** | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| V | Baseline object | "unconditioned behavior" referenced but not defined (what unconditional sample / benchmark?) | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| W | Direction-as-object vs direction-as-trade | Sign explicitly PENDING; object = sample of deviations | PROVISIONAL | registry §103-104; acceptable for mechanism-first, but testing machinery must be defined |
| X | Conditioning granularity | Index-level daily only at $0 (SPX daily, VIXCLS daily) | FROZEN (granularity) | registry §106; daily frequency,
 no intraday at $0 (VIX intraday is CBOE premium) `[VERIFIED FACT — source registry §56]` |
| Y | Data price redistribution / license | S-10 personal-use; S-18 Yahoo-ToS risk; FRED/CBOE official | PROVISIONAL | source registry §89/§119; bootstrap review §310 mitigate with S-04 official primary |
| Z | Missing-data / halted sessions rule | Not specified | **SPECIFICATION GAP** | no rule for index non-trading dates vs event dates → `HUMAN DECISION REQUIRED` |
| AA | Announcement-schedule archive protocol | Archive release times + rare early-release-count adjustments | FROZEN (mitigation) | bootstrap review §221/§310 |
| AB | Parameter set (if any) | None declared beyond window | **SPECIFICATION GAP** | a one-window pre-reg has no param search; but window itself must be bound → `HUMAN DECISION REQUIRED` |
| AC | Parameter-freeze enforcement (anti-harking) | Registry §195-202 forbids post-result change; new config = new candidate | FROZEN | registry §195-202 |
| AD | Trial count K | K frozen census; **K for this candidate not declared** | **SPECIFICATION GAP** | D6 doc: K should be sealed ledger; not bound here → `HUMAN DECISION REQUIRED` |
| AE | Multiple-testing control (self) | Not declared whether FOMC/CPI/NFP are 1 test or 3 tests; effective-K semantics not bound | **SPECIFICATION GAP** | D6 doc; `HUMAN DECISION REQUIRED` |
| AF | Multiple-testing control (cross-candidate) | Dependence with future VOL-001 on shared SPX leg must be declared (doctrine 8) | PROVISIONAL | bootstrap review §312(c) |
| AG | Statistical methodology | Not declared (no pre-registered estimator/test for conditional deviation) | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| AH | Significance threshold | Not declared | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| AI | PASS vs FAIL vs INVALID semantics | D6 doc governs; not candidate-bound | PROVISIONAL | ref d6_statistical_semantics_decision_surface.md |
| AJ | IS/OOS / blind design | Not declared (no blind split, no holdout, no PIT-boundary) | **SPECIFICATION GAP** | bootstrap review §314 requires IS/OOS blind-window design before authorization → `HUMAN DECISION REQUIRED` |
| AK | Kill conditions (early-termination) | Not declared | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| AL | Reproducibility (manifest, config_sha256, return_sha256, data archive) | Data archive-at-retrieval + manifest FROZEN; hashes not candidate-bound | PROVISIONAL/Partial | registry §107; bootstrap review §310 |
| AM | Determinism / tie policy | Not applicable at event level (no ranking) but sort/join determinism should be stated | PROVISIONAL | doctrine-10 |
| AN | Non-stationarity / regime awareness | Post-2015 pre-FOMC attenuation `EVIDENCE=MIXED` (persistence question, not data blocker) | PROVISIONAL | bootstrap review §312(a); ssrn §531 |
| AO | Cross-asset / cross-information dependence | VIXCLS (S-04) as context only; not a separate traded object | PROVISIONAL | registry §102; ontology context |
| AP | Price-data universe holder | SPX official (S-04) primary; SPY (S-10/S-18) cross; NOT F-1 1500 | FROZEN | registry §106; bootstrap review §310 |
| AQ | Survivorship completeness | CLEAN (index-level) | FROZEN | registry §112; bootstrap review §159 |
| AR | Cost model at execution | $0 (no execution); index is not directly tradeable — cross via SPY has costs | **SPECIFICATION GAP** | if SPY used for robustness w/ costs, cost model not declared → `HUMAN DECISION REQUIRED` |
| AS | Data license & redistribution confirmation | S-04/S-08/S-05/S-06 `[ACCEPT]`; S-10/S-18 `[CONDITIONAL]` | FROZEN/PROVISIONAL | source registry |
| AT | Provenance lineage | source ID → series → archive manifest traceability required | PROVISIONAL | registry §107; source registry |
| AU | Drift / bug / rounding policy | Not declared | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| AV | Universe pinning vs rebalance | N/A (index level, recomputed daily) | FROZEN (N/A) | `[MODEL INFERENCE]` |
| AW | Event-time storage precision | Release times archived at retrieval | FROZEN (mitigation) | registry §111 |
| AX | Session/calendar (half-days, holidays) | Not specified; CPI/NFP 08:30 ET vs index open 09:30 ET timing interplay undefined | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| AY | Return space | period vs annualized, simple vs log — not defined for the object | **SPECIFICATION GAP** | doctrine-7; `HUMAN DECISION REQUIRED` |
| AZ | Variance/sample space | sample vs long-run vs trial variance — not defined | **SPECIFICATION GAP** | doctrine-7; `HUMAN DECISION REQUIRED` |
| BA | T vs T_eff | effective independent observations not bound | **SPECIFICATION GAP** | doctrine-7; `HUMAN DECISION REQUIRED` |
| BB | Announcement vs announcement-surprise | not distinguished (status-quo levels vs surprise); only scheduled releases named | PROVISIONAL | mechanism is scheduled-release conditioning; surprise not named → keep as-is |
| BC | Option-implied vs realized | mechanism mentions option-implied vs realized "recurrent" behavior but VIX is context only | PROVISIONAL | registry §100; §102 VIXCLS context |
| BD | Event clustering rule | FOMC/CPI near month-end, same-day clustering not defined | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| BE | Multi-candidate dependence declaration | Must declare dependence with other candidates sharing SPX leg | PROVISIONAL | doctrine-8; bootstrap review §312(c) |
| BF | Reporting standard | verification ledger, epistemic labels, `[SOURCE CLAIM]` discipline | PROVISIONAL | research doctrine; AGENTS.md |
| BG | Publication-decay acknowledgment | literature `EVIDENCE=MIXED`; persistence contested | PROVISIONAL | bootstrap review §205; ssrn |
| BH | Data-acquisition queue | any paid/extra leg → FUTURE DATA ACQUISITION QUEUE ($0 budget) | FROZEN | charter §16/§29; §28 here |
| BI | Audit & logging of abort/INVALID | not declared | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| BJ | Golden numerical reference | not applicable (no numerical computation in spec) | PROVISIONAL (N/A) | `[MODEL INFERENCE]` |
| BK | Environment / toolchain pin | not declared | **SPECIFICATION GAP** | `HUMAN DECISION REQUIRED` |
| BL | Permission & identity of executor | free-data lane; no trading/capital | FROZEN | charter |
| BM | Data-version pin | S-05/S-08 schedules + S-04 index archive pinned at retrieval | PROVISIONAL | registry §107 |
| BN | STANCE on direction after result | direction discoverable post-spec; **no direction-trade promise** | PROVISIONAL | registry §103-104 |
| BO | STOP/BOUNDARY audit | charter §16/§21/§22/§29 bounds; this package is pre-authorization only | FROZEN | charter; §PREAMBLE |

> **Summary of §9:** FROZEN = most data-PIT-survivorship-cost-governance dimensions (≈28); PROVISIONAL = ≈17;
> **SPECIFICATION GAP / HUMAN DECISION REQUIRED = ≈22 dimensions (R,S,T,U,V,Z,AB,AD,AE,AG,AH,AJ,AK,AR,AU,AX,AY,AZ,BA,BD,BI,BK)**.
> The candidate is governance- and data-ready but not yet an executable pre-registration. `[MODEL INFERENCE]`

---

## 10. Event Audit — FOMC / CPI / NFP

All `[SOURCE CLAIM]` unless marked — based on ssrn_mechanism_research.md and governance review (no empirical run here).

| # | Dimension | Finding | Determinism |
|---|-----------|---------|-------------|
| 10.1 | FOMC (S-08) | Scheduled FOMC statements; pre-FOMC equity drift documented (Lucca-Moench); FEDS survey notes post-2015 attenuation `[SOURCE CLAIM]` | Event date PTT-proven; time (14:00 ET, press conf 14:30 ET post-2019) archived at retrieval |
| 10.2 | CPI (S-05) | Scheduled monthly release 08:30 ET; value subject to revision — as-published vintage | date/time pre-announced; as-published values |
| 10.3 | NFP (S-05) | Employment Situation; 08:30 ET; revision-prone | as-published vintage |
| 10.4 | Counting/rule | THREE named event types; **no rule for overlap (e.g., no same-day joint events), no exclusions (e.g., unscheduled/emergency)** | **SPECIFICATION GAP → HUMAN DECISION REQUIRED** |
| 10.5 | Timezone base | US Eastern (ET) implied but never stated as a norm | **SPECIFICATION GAP → HUMAN DECISION REQUIRED** |

**Event-audit verdict:** Event *type set* is FROZEN (FOMC/CPI/NFP); event *rule set* (inclusion/exclusion, overlap, timezone,
timestamp precision, early-release protocol) is a SPECIFICATION GAP. `[MODEL INFERENCE]`

---

## 11. PIT (Point-In-Time) Audit

| # | Q | Finding | Determination |
|---|-----|---------|---------------|
| 11.1 | Q1 calendars | Pre-announced, versioned schedules (S-05/S-08) | `[ACCEPT]` `[VERIFIED FACT — source registry §61]` |
| 11.2 | Q2 release times | Archive release time at retrieval; rare early-release count adjustments to be archived | PROVISIONAL (mitigation FROZEN) `[VERIFIED FACT — bootstrap review §221]` |
| 11.3 | Q3 index closes | SPX official daily closes (S-04): dated | `[ACCEPT]` `[VERIFIED FACT]` |
| 11.4 | Q4 index vintage | as-published index values required; rebasing lookahead trap (S-10 `[PIT UNPROVEN]` unless archived) | **must archive** `[VERIFIED FACT — bootstrap review §147]` |
| 11.5 | Q5 roster | N/A (index-level) | N/A |
| 11.6 | Q6/Q7 dates | index closes dated; revisions to realized-vol use as-published | `[ACCEPT]` / PROVISIONAL |

**PIT verdict:** **PIT SECURE** for the event-time leg; index-vintage PIT is `[CONDITIONAL]` and requires as-published
archive. `[VERIFIED FACT — bootstrap review §145, §147]`

---

## 12. Survivorship Audit

- Index-level universe (S-04 SPX official primary). No delisting leg, no member roster → **CLEAN**, no survivorship bias. `[VERIFIED FACT — registry §112; bootstrap review §159]`
- SPY ETF robustness leg: ETF survives; the SPX index is the authoritative level → survivorship not applicable. `[VERIFIED FACT]`

---

## 13. Cost & Fee Audit

- Execution cost: **$0** — candidate is index/event-conditioning measurement; no trading, no capital. `[VERIFIED FACT — registry §109]`
- SPY robustness would incur costs if ever traded, but candidate measures index behavior, not an executed SPY strategy. Cost model only matters if the Human authorizes an SPY-carry leg / tradeable variant → deferred, recorded as `HUMAN DECISION REQUIRED` if scope extends. `[MODEL INFERENCE — AR §9]`

---

## 14. Parameter-Freeze Audit

- Registry §195-202: **FROZEN** — no parameter/design change post-result; any change = NEW candidate + documented reason + Human Governance review. `[VERIFIED FACT]`
- The only "parameter" surface is the event window/object/sign — all currently SPECIFICATION GAP; they must be bound **before** any authorized empirical run, and once bound may not be changed post-result. `[MODEL INFERENCE]`

---

## 15. Trial-Count (K) Audit

- D6 doc: K should be a **sealed ledger** count; effective-K governs multiple-testing semantics (separate governance decision). `[VERIFIED FACT — d6 doc]`
- For CAND-FREE-MACRO-001, K is **not declared** (is FOMC one test, CPI one, NFP one → K=3? Or K=1 joint?). **SPECIFICATION GAP → HUMAN DECISION REQUIRED.** `[MODEL INFERENCE — AD §9]`

---

## 16. Statistical Audit (methodology, null, thresholds)

- Null/baseline: "unconditioned behavior" — **not operationally defined** (which sample, which benchmark series, which window-to-baseline). **SPECIFICATION GAP → HUMAN DECISION REQUIRED.** `[MODEL INFERENCE — V §9]`
- Pre-registered estimator/test for "conditional deviation is non-zero" — **not declared**. **SPECIFICATION GAP → HUMAN DECISION REQUIRED.** `[MODEL INFERENCE — AG §9]`
- Significance/threshold — **not declared**. **SPECIFICATION GAP → HUMAN DECISION REQUIRED.** `[MODEL INFERENCE — AH §9]`

---

## 17. IS/OOS & Blind-Design Audit

- **Not declared.** The bootstrap review §314 explicitly requires an **IS/OOS blind-window design** to be presented to Human *before* authorization. `[VERIFIED FACT — bootstrap review §314]`
- Without a pre-registered IS/OOS blind split, holdout, and PIT boundary, the candidate is NOT execution-ready. **SPECIFICATION GAP → HUMAN DECISION REQUIRED.** `[MODEL INFERENCE — AJ §9]`

---

## 18. Multiple-Testing & Statistical-Dependence Audit

- Within-candidate: FOMC/CPI/NFP overlap and joint-vs-separate not bound → effective-K unresolved. **SPECIFICATION GAP.** `[MODEL INFERENCE — AE §9]`
- Cross-candidate: shared SPX leg with future VOL-001 (and other index-level candidates) → dependence must be **declared, not labeled independent** (doctrine 8). PROVISIONAL. `[VERIFIED FACT — doctrine 8; bootstrap review §312(c)]`
- D6 doc: FAILED/INVALID runs must NOT get fabricated stats; INVALID is an input/database condition, the natural result must be reported as such. `[VERIFIED FACT — d6 doc]` — such semantics must be candidate-bound before run → `HUMAN DECISION REQUIRED`.

---

## 19. Data-Source Audit (maps to source registry S-IDs)

| S-ID | Series | Tier / Status | License/limitation | Role for candidate |
|------|--------|--------------|--------------------|--------------------|
| S-04 | FRED SP500 index close + VIXCLS | TIER 1 `[ACCEPT]`; VIX vintage `[CONDITIONAL]` | official; VIX intraday = CBOE premium `[VERIFIED FACT — source registry §56]` | **SPX primary**; VIXCLS as context |
| S-05 | BLS CPI/NFP calendar + values | TIER 1; schedule `[ACCEPT]`, values revision-prone | as-published vintage | event set + values |
| S-06 | U.S. Treasury schedule | TIER 1 `[ACCEPT]` | official | secondary/support |
| S-08 | FOMC calendar & statements | TIER 1 `[ACCEPT]` | official | FOMC event set |
| S-10 | Stooq SPY daily OHLCV | TIER 2 `[CONDITIONAL]` | personal-use; redistribution constrained | SPY robustness cross-check |
| S-18 | yfinance SPY | TIER 4 `[CONDITIONAL]/[REJECT] deep delisted` | Yahoo-ToS bulk/redistribution risk; mutable | SPY robustness (secondary) |

**Data-path verdict:** primary path S-04/S-08/S-05 (+S-06) = `[ACCEPT]`; SPY leg = `[CONDITIONAL]` under personal-use terms and must be PIT-archived. `[VERIFIED FACT — seed from source registry & bootstrap review §310]`

---

## 20. Reproducibility Audit

- Archive-at-retrieval + execution manifest: FROZEN (registry §107; bootstrap review §310). `[VERIFIED FACT]`
- config_sha256 / return_sha256 / K sealed ledger, manifest hash binding: governance capabilities exist; **candidate-specific binding not yet declared** → `HUMAN DECISION REQUIRED` to pin exact manifest schema for this candidate. `[MODEL INFERENCE — AL §9]`

---

## 21. Documentation & Logging Audit

- Audit trail, verification ledger, epistemic labels: PROVISIONAL per research doctrine / AGENTS.md.
- Abort/INVALID logging rule: **not declared** → `HUMAN DECISION REQUIRED` (BI §9).

---

## 22. Pre-Authorization Checklist (holding-item gate)

| # | Item | Status |
|---|------|--------|
| 22.1 | Command/budget confirmation | $0 budget; no purchase → FUTURE DATA ACQUISITION QUEUE `[VERIFIED FACT]` |
| 22.2 | No empirical authorization | **NOT AUTHORIZED** `[VERIFIED FACT — registry §209]` |
| 22.3 | F-1 isolation | preserved `[VERIFIED FACT]` |
| 22.4 | Candidate spec frozen-as-proposal | yes, at proposal boundary `[VERIFIED FACT — registry §195]` |
| 22.5 | Execution-level determinism | **CONDITIONALLY READY — gaps remain** `[MODEL INFERENCE]` |

---

## 23. Limitations of this Readiness Package

1. This is a **readiness judgment**, not evidence of edge, alpha, or profitability (doctrine-1/5).
2. Verdicts rely only on the frozen proposal text + governance docs; no empirical data used.
3. `[SOURCE CLAIM]` items (e.g., pre-FOMC literature) are cited, not independently verified here.
4. "CONDITIONALLY READY" is a first-candidate-consideration statement, consistent with the governance review's
   ranking of CAND-FREE-MACRO-001 as recommended-first — but the **two claims are about different things**
   (their ranking = governance-friction/data-feasibility; this package's classification = execution determinism).
   `[MODEL INFERENCE — distinction made explicit to avoid overstating readiness]`

---

## 24. Pre-Registration Checklist (Y/N/NA + Note)

| # | Pre-registration element | Status (Y/N/NA) | Note |
|---|--------------------------|----------------|------|
| 24.1 | Hypothesis/object stated | Y | conditional-deviation object, sign PENDING `[VERIFIED FACT]` |
| 24.2 | Universe defined | Y (partial) | index-level SPX/SPY; not F-1 `[VERIFIED FACT]` |
| 24.3 | Data sources pinned | Y | S-04/S-08/S-05/(S-06)/S-10/S-18 `[VERIFIED FACT]` |
| 24.4 | PIT archive protocol | Y | as-published, archive-at-retrieval `[VERIFIED FACT]` |
| 24.5 | Survivorship policy | Y | none (index-level) `[VERIFIED FACT]` |
| 24.6 | Cost model | Y (NA-volunt.) | $0; SPY-carry deferred `[VERIFIED FACT]` |
| 24.7 | Window algorithm (start/end math) | N→GAP | ± opened vs ±1td unresolved `[MODEL INFERENCE]` |
| 24.8 | Event inclusion/exclusion rule | N→GAP | overlap/unscheduled undefined `[MODEL INFERENCE]` |
| 24.9 | Timestamp/timezone norm | N→GAP | ET implied only `[MODEL INFERENCE]` |
| 24.10 | Return-space definition (simple/log; annualized) | N→GAP | `[MODEL INFERENCE]` |
| 24.11 | Baseline (unconditioned) definition | N→GAP | `[MODEL INFERENCE]` |
| 24.12 | Statistical estimator & null | N→GAP | `[MODEL INFERENCE]` |
| 24.13 | Significance threshold | N→GAP | `[MODEL INFERENCE]` |
| 24.14 | Sample / T / T_eff | N→GAP | `[MODEL INFERENCE]` |
| 24.15 | IS/OOS / blind split | N→GAP | `[MODEL INFERENCE]` |
| 24.16 | Trial count K (sealed) | N→GAP | `[MODEL INFERENCE]` |
| 24.17 | Multiple-testing / effective-K semantics | N→GAP | `[MODEL INFERENCE]` |
| 24.18 | Kill conditions | N→GAP | `[MODEL INFERENCE]` |
| 24.19 | Reproducibility manifest/hashes | Y (proto) | execution-level schema N→GAP |
| 24.20 | PASS/FAIL/INVALID mapping | N→GAP | D6 default applies but not candidate-bound |
| 24.21 | Anti-harking / parameter freeze | Y | registry §195-202 `[VERIFIED FACT]` |
| 24.22 | Dependence declaration (shared SPX) | Y (policy) | doctrine-8; binding N→GAP |
| 24.23 | Reporting/epistemic-label standard | Y | doctrine / AGENTS.md |
| 24.24 | Data-acquisition queue routing | Y | FUTURE DATA ACQUISITION QUEUE only `[VERIFIED FACT]` |

**Checklist result: 12 items Y, 12 items N (SPECIFICATION GAP).** This confirms CONDITIONALLY READY. `[MODEL INFERENCE]`

---

## 25. Classification / Decision Summary

**Disposition: CONDITIONALLY READY (specification-gap condition).**

The candidate is a strong, governance-clean, data-`[ACCEPT]`, PIT-secure, survivor-clean, $0 first-candidate
**for a Human consideration** — consistent with the governance review's recommendation. It is **NOT** yet a
deterministic, pre-registered, executable protocol: ≈22 execution dimensions are `SPECIFICATION GAP`. Per the
fail-closed contract (§PREAMBLE-3), those gaps are surfaced as `HUMAN DECISION REQUIRED`, never silently filled.

**The gaps do NOT block a Human from choosing OPTION A (authorize a bounded empirical-validation under a**
**to-be-bound spec) — but Human must explicitly BIND the listed gaps (window, event-rule, object, stats, K,**
**IS/OOS, kill-conditions) in the same authorization, and the bound spec becomes the new frozen, unchangeable spec.**
`[MODEL INFERENCE — synthesis]`

---

## 26. Decision Surface (OPTION A–E) — for Human only; NOT decided here

| Option | Meaning | Precondition | This package's note |
|--------|---------|-------------|---------------------|
| **OPTION A** | Authorize bounded empirical validation of CAND-FREE-MACRO-001 **under its frozen concept spec**, pending Human binding of §9 gaps | Human binds N-frozen gaps (window, event-rule, object, statistics, K, IS/OOS, kill-conditions) into one frozen executable spec + data-audit + manifest + authorization note | Binding required; gap-free pre-registration not yet written |
| **OPTION B** | Additional data-feasibility/design research first (e.g., SPY price-leg terms resolution, early-release-count archival protocol, event-window reconciliation) | none blocking | Directly addresses the GAP-flagged window/event items |
| **OPTION C** | Reject/defer MACRO-001; take another candidate | none | e.g., CAND-FREE-VOL-001 runner-up `[VERIFIED FACT — bootstrap review]` |
| **OPTION D** | Mechanism intake for an unregistered concept WITHOUT validation | none | separate intake, not this candidate |
| **OPTION E** | STOP | none | full stop |

**NOT DECIDED.** This package presents the surface only and does not choose. `[VERIFIED FACT — this doc's contract]`

---

## 27. Non-Decisions (Explicitly NOT decided here)

- Not deciding OPTION A–E result.
- Not binding any §9 SPECIFICATION GAP (these are for Human).
- Not setting K, thresholds, stats, IS/OOS, window, event-rule, object, kill-conditions.
- Not authorizing empirical validation, data download, paper trading, live trading, or capital.
- Not modifying HYP_003 / R1 / Gate / D1/D2/D6 / F-1 / CAND-FREE-MACRO-001 / registry / doctrine / roadmap.

---

## 28. Future Data Acquisition Queue

Budget $0. No acquisition initiated in this package. Any paid/intraday/SPY-carry/S-07 CBOE intraday needs are
routed to the FUTURE DATA ACQUISITION QUEUE only, per charter §16/§29. `[VERIFIED FACT — charter]`:

1. CBOE **VIX intraday** (S-07 premium) — only if the validated mechanism ever needs intraday granularity.
2. **SPY price-leg terms resolution** (S-10/S-18 personal-use; official SPY license) — before any SPY-carry leg.
3. **Early-release-count archival service/protocol** — robustness of release-time audit.
4. Any **data license** easing for redistribution of the S-10/S-18 if a tradeable variant is later contemplated.

---

## 29. F-1 Isolation Statement

CAND-FREE-MACRO-001 is a FREE-DATA-BOOTSTRAP-lane candidate and is **NOT** F-1, **NOT** HYP_003, **NOT** R1.
Its universe (index-level SPX/SPY) differs from the F-1 S&P Composite 1500 universe. This package does NOT modify
F-1, its D1/D2/D6 decisions, F-1 statuses (D1 = NOT READY / CONDITIONAL; D2 = LOCKED; B2 = BLOCKED; B5 = UNVERIFIED),
or any F-1 governance record. Any F-1-aligned evidence (index/rebalance family) is EXCLUDED by lane separation
(registry §185-191). `[VERIFIED FACT — registry & F-1 docs]`

---

## 30. Final Governance State & STOP

**Final governance state (verbatim, unchanged by this package):**
- F-1 = S&P Composite 1500 (`D2 = LOCKED`). `[VERIFIED FACT]`
- D1 = **NOT READY / CONDITIONAL** (unchanged). `[VERIFIED FACT]`
- B2 = **BLOCKED** (unchanged). `[VERIFIED FACT]`
- B5 = **UNVERIFIED** (unchanged). `[VERIFIED FACT]`
- HYP_003 / R1 / GATE / TRADING = **NOT AUTHORIZED** (unchanged). `[VERIFIED FACT]`
- CAPITAL = **$0.00** (unchanged). `[VERIFIED FACT]`
- EMPIRICAL VALIDATION = **NOT AUTHORIZED** (unchanged; all five candidates NOT AUTHORIZED, registry §206-214). `[VERIFIED FACT]`

**STOP — CAND-FREE-MACRO-001 VALIDATION READINESS PACKAGE COMPLETE. NO EMPIRICAL VALIDATION AUTHORIZED. NO BACKTEST PERFORMED. F-1 UNCHANGED. NO HYP_003 / R1 / GATE / TRADING AUTHORIZATION.**

---

### Verification Ledger
- Implementation Status: **COMPLETE** (single readiness doc produced; no code/test changes).
- Contract Enforcement: **STRICT FAIL-CLOSED** — all gaps recorded as SPECIFICATION GAP / HUMAN DECISION REQUIRED; zero empirical results; zero out-of-scope modifications.
- Mathematical Authority: **CANONICAL SPEC (as recorded in registry)** — HEURISTIC not applicable; no numbers computed.
- Local Test Suite: **NOT RUN** (no code change; documentation-only artifact).
- Type Checker (MyPy): **NOT RUN** (no Python changed).
- Remote CI Status: **NOT APPLICABLE** (docs-only; no CI-defined behavior for markdown).
- Methodological Caveats: Readiness judged on specification determinism only; literature `[SOURCE CLAIM]` items not independently verified; CONDITIONALLY READY does NOT imply edge existence.