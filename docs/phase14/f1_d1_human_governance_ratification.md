# ACASH V5 — D1 HUMAN GOVERNANCE RATIFICATION (D1-A / D1-B)

**Document ID:** `docs/phase14/f1_d1_human_governance_ratification.md`
**Object:** Human Governance ratification of the two remaining F-1 D1 specification questions — **D1-A Constrained Research Window** and **D1-B Filter Semantics**
**Status:** `[DOCUMENTATION-ONLY]` · `[GOVERNANCE RECORD]` · `[NOT HYP_003]` · `[NOT R1]` · `[NOT D2]`
**Date:** 2026-09-10
**Authority:** explicit Human Governance instruction transmitted 2026-09-10 (ratifying D1-A, D1-B). Decisions in this document are **HUMAN-ACCEPTED** per that instruction; no decision is taken by the document itself.

**Evidence baseline (terminology preserved, no evidence invented):**
- `docs/phase14/candidate_f1_flow_calendar_rebalance_review.md` (F-1 specification freeze, 2026-09-09)
- `docs/phase14/f1_d1_free_data_feasibility.md` (D1 free-first audit, 2026-09-10)
- `docs/phase14/f1_d1_blocker_resolution.md` (D1 blocker-resolution research, 2026-09-10)
- `docs/phase14/f1_d1_final_feasibility_reassessment.md` (final D1 re-assessment + D1-A/D1-B proposed registers, 2026-09-10)

**Classification labels (unchanged):** `[ACCEPT]` `[CONDITIONAL]` `[UNVERIFIED]` `[NOT SUFFICIENT AT $0]` `[REJECT]` · `READY` / `NOT READY` / `CONDITIONAL` · `[PIT PROVEN]` / `[PIT UNPROVEN]` · `[PROPOSED / PENDING HUMAN RATIFICATION]` · `[HUMAN-ACCEPTED]`

**Constraint on this record:** nothing below promotes `CONDITIONAL → ACCEPT`, `UNVERIFIED → CONDITIONAL`, or `NOT SUFFICIENT AT $0 → anything else`. All B1–B6 statuses are carried verbatim from the evidence baseline.

---

## 1. PURPOSE

Record the Human Governance decisions on the **two remaining D1 specification questions**:

- **D1-A — Constrained Research Window**: `ACCEPT AS CONDITIONAL FEASIBILITY WINDOW`
  (~2013-12 → present, S&P Composite 1500, quarterly reconstitution only).
- **D1-B — Filter Semantics**: `RETAIN FROZEN F-1 PROXY` (`ADV ≥ $5M/day`, `Free Float ≥ 20%`).

This task **does NOT** authorize (beyond what is already frozen): D2 · HYP_003 · R1 · ReInceptionGate ·
backtesting · optimization · parameter search · paper trading · live trading · broker connection ·
capital deployment · any paid data subscription · any vendor contact. [FROZEN — all]

---

## 2. CURRENT CANONICAL STATE

Unchanged; this record does not alter any of the following. [FROZEN — all] [VERIFIED FACT — baseline docs]

- **Candidate:** F-1 `CAND-FLOW-CALENDAR-REBALANCE-001` — RESEARCH CANDIDATE ONLY. [FROZEN]
- **Mechanism:** passive index/ETF forced rebalancing flow around the effective-date close; defined, truth NOT PROVEN. [FROZEN definition]
- **Direction:** SHORT composite reversal (positive flow → SHORT; negative flow → LONG). [FROZEN]
- **Horizons:** {1, 5, 10}, PRIMARY = 5 ⇒ and `R(h) = Close(T0+h)/Close(T0) − 1`. [FROZEN]
- **Universe:** S&P Composite 1500 family (S&P 500 / MidCap 400 / SmallCap 600). [FROZEN]
- **Filter proxies:** ADV ≥ US$5M/day (60-day pre-event); Free Float ≥ 20% (PIT by effective date). [FROZEN — human-frozen 2026-09-07, re-affirmed below by D1-B]
- **Event family:** quarterly reconstitution only; month-end/periodic separate; special/mid-stream excluded. [FROZEN]
- **Anchor:** effective date T0; entry/exit = official close of T0 / T0+h. [FROZEN]
- **Minimum sample:** `T_eff ≥ 25/leg`; canonical `N_valid ≥ 250` (not overridden). [FROZEN]
- **Prior human decision:** OPTION A — RETAIN COMPOSITE 1500 (no downgrade, no S&P 600 removal, no F-1-Free). [FROZEN] [VERIFIED FACT]
- **Current D1 status:** `NOT READY / CONDITIONAL` — **re-affirmed and retained by this record.** [FROZEN]
- **LOCKED unless explicitly authorized:** D2 · HYP_003 · ReInceptionGate · R1 · Phase 6 qualification · trading · paper/live trading · broker · capital (= `$0.00`) · backtest · optimization · parameter search · empirical performance/alpha/profitability claims. [FROZEN — all]
- **Cost rule:** DATA COST = `$0.00`; no paid subscription, no charge, no paid account. [FROZEN]
- **Repository state (2026-09-10):** `git status --short --branch` → `## main...origin/main`; HEAD = `origin/main` = `7d71223fb8e275cc9ee981f3754fe45483b18dcf`; tree clean apart from untracked documentation (`f1_d1_final_feasibility_reassessment.md`). No divergence; history intact; no git mutation will be performed by this task. [VERIFIED FACT]

---

## 3. DECISION D1-A — CONSTRAINED RESEARCH WINDOW

**Decision:** `HUMAN-ACCEPTED` — **ACCEPT AS CONDITIONAL FEASIBILITY WINDOW**. [2026-09-10]

- **Window:** approximately **2013-12 → present**. Anchor: earliest quarterly reconstitution
  announcement artifact verified archived = 2013-12-11 (`67155_fbshuf252426100.pdf`, 3 Wayback
  captures 2021-02-25 → 2026-06-01). CDX floor 2013-04-16 observed (floor, not coverage). [VERIFIED FACT — capture presence; per-document content verification for 2013–2022 remains outstanding]
- **Universe:** S&P Composite 1500 (all three legs retained). [FROZEN]
- **Event family:** quarterly reconstitution only. [FROZEN]
- **Interpretation:** a **temporal feasibility constraint only**. It constrains TEMPORAL COVERAGE; it
  does NOT change the candidate ID, universe, mechanism, signal definition, return definition,
  horizons, cost model, or kill conditions. [FROZEN — no drift]
- **Explicitly recorded [this record]:**
  ```
  WINDOW ACCEPTED FOR FEASIBILITY  !=  D1 READY
  ```
- It does **NOT**: authorize empirical testing · authorize HYP_003 · authorize R1 · make the dataset
  complete · prove PIT for the full corpus · resolve delisted prices · resolve free-float PIT.
  [FROZEN — clear]
- **Boundary of acceptance:** D1-A admits the window for **further DATA-FEASIBILITY validation only**
  (corpus-completeness reconciliation, roster-parity validation, provenance plan). It does NOT
  authorize data construction/build; any build additionally requires the B6 license gate, source
  binding, and separate human authorization. [NON-NORMATIVE — scope statement]

---

## 4. DECISION D1-B — FILTER SEMANTICS

**Decision:** `HUMAN-ACCEPTED` — **RETAIN FROZEN F-1 PROXY**. [2026-09-10; proxy itself frozen since 2026-09-07]

- **Filters remain unchanged:**
  - `ADV ≥ US$5,000,000/day` (60-day pre-event lookback)
  - `Free Float ≥ 20%` (latest PIT by effective date, no look-ahead)
  [FROZEN — human-frozen 2026-09-07]
- **NOT replaced by:** FALR · IWF · or any other official S&P methodology variable. [FROZEN]
- **Recorded as a `KNOWN METHODOLOGICAL CAVEAT`:** the frozen F-1 proxy differs from the official
  S&P U.S. Indices Methodology (FALR ≥ 0.1, IWF/float gates, composite-pricing evaluation window).
  This is a documented methodological distinction — **NOT a specification rewrite.** Replacing the
  proxy with exact S&P methodology would be creating a NEW specification, not validating the frozen
  candidate; it therefore requires a separate, explicit Human Governance specification change. [FROZEN — no drift]

---

## 5. WHAT THESE DECISIONS DO NOT RESOLVE

D1-A and D1-B resolve the *specification* questions only. They do **NOT** resolve the *data* blockers:

- **B2 — Delisted OHLC:** remains `NOT SUFFICIENT AT $0` (certifiable). Frozen §27G exclude-rule
  mitigation exists but coverage certification is absent; Kaggle license `[UNVERIFIED]` (not promoted).
- **B5 — Free-Float PIT:** remains `UNVERIFIED`. No free historical PIT float; current float is NOT
  usable for historical eligibility.

**Therefore:**
```
D1 MUST REMAIN  NOT READY / CONDITIONAL
```
**Do NOT upgrade D1.** D1-A/B provide no basis for a readiness upgrade; the 18-item readiness checklist
(§13 of the final re-assessment) still has critical open items — most decisively free-float PIT (item 10)
and delisted-price coverage (item 7). A future `READY` would, in any case, not itself authorize D2. [FROZEN]
[VERIFIED FACT — re-assessment §13/§15]

---

## 6. CURRENT B1–B6 STATUS (recorded verbatim from the evidence baseline)

| Blocker | Status | Evidence note |
|---------|--------|---------------|
| **B1** S&P 600 membership | `CONDITIONAL` | 2013+ reconstructable via archived announcements + EDGAR N-PORT/N-CSR rosters + page snapshots; **corpus completeness `[UNVERIFIED]`**, roster↔index parity `[UNVERIFIED]`; pre-2013 `[UNVERIFIED]`; NOT ACCEPT |
| **B2** Delisted OHLC | `NOT SUFFICIENT AT $0` | No certified free delisted-price history; Kaggle archive license `[UNVERIFIED]` (page unrenderable 2026-09-10, not promoted); EDGAR Form 25/AV delisted metadata `[ACCEPT]` events-only |
| **B3** Announcement PIT | `CONDITIONAL` | `announce < effective` `[PIT PROVEN]` for 2023/2026 sample artifacts; 2013–2022 per-event content/chronology verification outstanding; archive capture ≠ announcement time |
| **B4** Corporate actions | `CONDITIONAL` | EDGAR Form 25/25-NSE delistings `[ACCEPT]`; structured splits/dividends free = `[UNVERIFIED]` (securitiesdb `[CONDITIONAL]/[UNVERIFIED]`); adjustment provenance `[UNVERIFIED]` |
| **B5** Free-float / ADV PIT | `UNVERIFIED` | **No free historical PIT float**; ADV-proxy `[CONDITIONAL]` active names only; official S&P IWF ≠ `Free Float ≥ 20%` proxy (methodological caveat, §4) |
| **B6** Provenance / license / reproducibility | `CONDITIONAL` | Pinned artifacts + archive-at-retrieval `[CONDITIONAL]`; **two `[UNVERIFIED]` licenses (Kaggle, securitiesdb)**; S&P-derived publication/redistribution review required |

No status was promoted in this record. [VERIFIED]

---

## 7. PRIMARY REMAINING BLOCKERS

**Primary (decisive for D1 READY-ness):**
1. **B5 — Free-Float PIT = `UNVERIFIED`** — without a free historical PIT float the frozen universe
   filter cannot be reproduced, so the PIT hard rule invalidates eligibility. Decisive for READY.
2. **B2 — Delisted OHLC = `NOT SUFFICIENT AT $0`** — the deletion-leg `T0+h` price coverage cannot be
   certified at `$0`; survivorship-bias breach risk on the deletion leg remains open (the frozen §27G
   exclude rule mitigates but does not certify).

**Conditional-gated (block READY until cleared):**
3. B1 — announcement-corpus completeness 2013–2022 + roster↔index parity (`[VERIFIED]` as open).
4. B3 — per-event announcement→effective PIT proof for the full corpus.
5. B4 — structured split/dividend CA history with provenance.
6. B6 — Kaggle + securitiesdb license clearance; S&P-derived dataset publication review.
7. Cross-cutting (non-source): formal source binding + P-IT ingestion contract; survivorship-bias
   audit report; `T_eff(leg) ≥ 25` achievability measurement on each composite leg.

All seven are carried from `f1_d1_final_feasibility_reassessment.md` §13/§15; no new blocker is
invented. [VERIFIED FACT — statuses identical]

---

## 8. HUMAN DECISION SURFACE

Prepared for the human. **Nothing here is selected, started, or authorized.**

| Path | Action | What it can resolve | Cost/spec impact | Status |
|------|--------|---------------------|------------------|--------|
| **PATH A** | Continue $0 investigation, **bounded and targeted to B2/B5 only** (verify Kaggle license/coverage; validate Wayback-scraper sample; one documented free historical-float search with hard stop) | Possibly B2 (license+coverage proof) and B5 (float discovery — deemed unlikely by current evidence) | `$0`; respects frozen budget | **Not selected** (human decision required to run) |
| **PATH B** | Authorize **paid data** (certified delisted OHLC; potentially float/fundamentals) | B2 (certifiable coverage); B5 (float) via fundamentals providers | Violates `$0`; **requires explicit human budget authorization** + license review | **Not selected**; not to be initiated by the agent |
| **PATH C** | **Modify research window** (temporal only) | Cannot resolve B2/B5; may relax pre-2013 depth gap | Spec change class | **Not selected** |
| **PATH D** | **Modify specification** (universe / filter semantics incl. float) | Would re-define requirements so B5's PIT-float is no longer required — a NEW specification, contradicts D1-B default | **Specification change** (explicitly excluded by D1-B unless separately ratified) | **Not selected** |
| **PATH E** | **Terminate / archive F-1** | Closes the line of inquiry entirely | N/A | **Not selected** |

Rules honored: no path auto-selected · no paid subscription initiated · **no vendor search unless
explicitly requested** · no specification rewrite · no readiness upgrade. [FROZEN]

---

## 9. RECOMMENDATION WITHOUT AUTHORIZATION

A recommendation only — it carries **no authority** and is binding on nothing:

1. Retain `D1 = NOT READY / CONDITIONAL` (ratified) and treat the F-1 **specification** as stable.
2. **Before any paid-data conversation**, run a **PATH A probe scoped strictly to B2/B5** with
   explicit kill criteria (e.g. Kaggle license/coverage verification; a Wayback-scraper sample
   check; one capped free float-source search round). Rationale: it is the only step consistent with
   the frozen `$0` rule, and it converts two currently-unknown blockers into either "resolved" or
   "proven unresolved at $0" at zero cost.
3. If PATH A terminates without resolving B2/B5 → raise **PATH B as a formal HUMAN DECISION**
   (budget + scope authorization). The agent will never decide paid vs. free on its own.
4. If B5 cannot be resolved by PATH A, PATH B (paid fundamentals) or PATH D (spec change) are the
   remaining technical resolvers at that point; PATH D contradicts the D1-B default and would
   require a separate human spec ratification.
5. HYP_003 creation remains gated behind the canonical sequence (Candidate → Specification Freeze →
   Data Feasibility → PIT/Provenance → Blind Window → Pre-registration → HYP_003). We remain at the
   **Data Feasibility** stage; no HYP_003 is minted now.

[NON-NORMATIVE — recommendation only]

---

## 10. GOVERNANCE BOUNDARY

- **No code / schema / gate / ROADMAP / registry / manifest / runtime change.** `src/`, `tests/`,
  `schemas/`, `gates/` untouched. [VERIFIED]
- **No gate invoked** (ReInceptionGate etc.); **no HYP_003**; **no R1**; **no D2**; **no backtest /
  optimization / parameter search**; **no empirical performance numbers**; **no trading of any kind**;
  **no capital** (`$0.00`). [VERIFIED]
- **D1-A acceptance ≠ data construction authorization.** Any future data build additionally requires:
  B6 license gate, formal source binding + P-IT ingestion contract, and separate human authorization. [FROZEN — scope]
- **D1-B retention ≠ acceptance of the official S&P methodology.** The proxy/methodology difference
  remains a `KNOWN METHODOLOGICAL CAVEAT` for future human acknowledgment. [FROZEN]
- **This record does not select a PATH (§8) and does not start PATH A work.** It only documents the
  ratified decisions, the unchanged blocker statuses, and the decision surface. [VERIFIED]
- All classification/status promotions are prohibited and none were performed. [VERIFIED]

**Canonical governance state at completion (unchanged):**
`F-1 = S&P Composite 1500 (CAND-FLOW-CALENDAR-REBALANCE-001) · D1 = NOT READY / CONDITIONAL ·
D2 = LOCKED · HYP_003 = NOT AUTHORIZED · R1 = NOT AUTHORIZED · GATE = NOT AUTHORIZED · TRADING =
LOCKED · CAPITAL = $0.00`

### Verification Ledger (this document)
- Implementation Status: NONE (documentation-only; single new untracked file; `src/` untouched).
- Ratification Authority: D1-A / D1-B = HUMAN-ACCEPTED per explicit human instruction 2026-09-10 (this message); no decision self-authored.
- Contract Enforcement: STRICT FAIL-CLOSED — no status promoted (`CONDITIONAL→ACCEPT`, `UNVERIFIED→CONDITIONAL`, `NOT SUFFICIENT AT $0 →` promoted) anywhere; no license inferred; no capability claimed.
- Mathematical Authority: N/A for data feasibility; canonical gate floors untouched.
- Evidence Baseline: identical statuses to `f1_d1_final_feasibility_reassessment.md` §13–§15 (verified, not re-derived).
- Local Test Suite: NOT RUN (documentation-only convention).
- Remote CI Status: NOT AVAILABLE.
- Git Policy: READ-ONLY — no add/commit/push/fetch/pull/merge/rebase/reset/revert/stash; file remains UNTRACKED (verified at completion).
- Methodological Caveats: window anchor 2013-12-11 is capture-verified with per-document content verification outstanding; B2/B5 are PRIMARY BLOCKERS and remain unresolved; PATH A-E surface prepared, none selected; agent holds no paid/free decision authority.

---

## 11. STOP

STOP — D1 HUMAN GOVERNANCE RATIFICATION (D1-A / D1-B) COMPLETE. F-1 SPECIFICATION STABLE · DATA LAYER NOT READY.
NO D2 / HYP_003 / R1 / GATE / TRADING / PAID-DATA AUTHORIZATION.
PRIMARY BLOCKERS (B2, B5) PENDING HUMAN PATH DECISION (A / B / C / D / E).