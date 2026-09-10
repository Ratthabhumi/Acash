# ACASH V5 — FREE-DATA CAPITAL BOOTSTRAP PROGRAM (GOVERNANCE CHARTER)

**Document ID:** `docs/phase14/free_data_capital_bootstrap_program.md`
**Object:** Establishment of a SEPARATE long-run research track — free-data-first candidate discovery and validation governance, `$0` data budget, capital-bootstrap aspiration
**Status:** `[DOCUMENTATION-ONLY]` · `[GOVERNANCE CHARTER]` · `[NOT HYP_003]` · `[NOT R1]` · `[NOT D2]` · `[NOT F-1]`
**Date:** 2026-09-10
**Authority:** `AGENTS.md` · `docs/phase14/research_doctrine.md` · `docs/phase14/research_candidates.md` · F-1 D1 evidence baseline (`candidate_f1_flow_calendar_rebalance_review.md`, `f1_d1_free_data_feasibility.md`, `f1_d1_blocker_resolution.md`, `f1_d1_final_feasibility_reassessment.md`, `f1_d1_human_governance_ratification.md`)
**Companion registries:** `docs/phase14/free_data_source_registry.md` · `docs/phase14/free_data_research_registry.md`

> [!CAUTION]
> **This program does NOT authorize:** trading · paper trading · live trading · broker connection ·
> capital deployment · D2 · HYP_003 · R1 · ReInceptionGate · backtest · optimization · parameter
> search · paid data · vendor contact. Nothing here weakens F-1 or silently changes any frozen
> specification. **F-1 is UNCHANGED: D1 = NOT READY / CONDITIONAL.**

**Epistemic discipline (§16 of doctrine):** all external claims (literature, videos, public claims)
are `REPORTED` / `INFERRED` / `NOT PROVEN`; nothing becomes `VERIFIED` without ACASH's own validated
evidence. No performance number appears in these governance documents.

---

## 1. MISSION

F-1 (`CAND-FLOW-CALENDAR-REBALANCE-001`) remains:
- Research candidate only; S&P Composite 1500; D1 = `NOT READY / CONDITIONAL`; window ~2013-12 →
  present **accepted for feasibility only**; frozen proxy `ADV ≥ $5M/day`, `Free Float ≥ 20%`. [FROZEN]
- Primary blockers: **B2** historical delisted prices = `NOT SUFFICIENT AT $0`; **B5** historical PIT
  free-float = `UNVERIFIED`. [FROZEN — evidence-recorded]

ACASH currently has a strategic constraint: `capital = $0`; paid data subscriptions not affordable.
This program establishes a **separate track** that finds, specifies and validates research candidates
whose information needs are genuinely available at `$0`, WITHOUT weakening the research standard —
and, under strict governance, gives promising validated candidates a route toward legitimate trading
authorization, potential capital generation, and (with capital) premium data acquisition that resolves
B2/B5 so F-1 can be re-advanced. [USER-RATIFIED OBJECTIVE — 2026-09-10]

**Non-goal (explicit):** the system does NOT hunt for attractive backtests. No profit is guaranteed.
The program optimizes for research integrity, reproducibility, anti-overfitting, survivorship-bias
control, cost realism, provenance and governance — NOT for backtest aesthetics. [FROZEN — doctrine 1–11]

---

## 2. F-1 SEPARATION (NON-NEGOTIABLE)

The Free-Data Capital Bootstrap Program is a **completely separate research lane**. [FROZEN]

- F-1 is not altered, weakened, merged, or silently changed: universe (S&P Composite 1500), frozen
  proxy filters, mechanism, event family (quarterly reconstitution only), horizons {1,5,10}, direction
  (SHORT composite), sample rules (`T_eff ≥ 25/leg`, `N_valid ≥ 250`), kill conditions — all remain
  exactly as frozen in the candidate review. [FROZEN]
- No bootstrap-strategy candidate is named HYP_003, and HYP_003 remains absent. [FROZEN]
- No bootstrap-strategy result may be used to claim F-1 has passed D1. [FROZEN]
- Index/rebaluencing event family (research family #7 of the §25 list) is **reserved to the F-1
  lane**: a separate free-track candidate on the same quarterly-reconstitution event family would
  duplicate F-1's thesis and is therefore EXCLUDED by default from this program's candidate intake
  (§16 of this charter, and Step-6 note in the research registry). [FROZEN — lane separation]

---

## 3. CAPITAL CONSTRAINT — GENUINELY FREE ONLY

- Data budget = `$0.00`. No purchase, no paid plan, no payment details, no paid trial requiring
  currency, no hidden premium endpoints, no licensing circumvention, no paywall bypass, no scraping of
  restricted data against terms. "Free" = genuinely accessible at `$0` under applicable terms. [FROZEN]
- For every source record the required fields are: source · owner · URL · access date · data type ·
  historical depth · PIT capability · survivorship characteristics · license/terms · reproducibility ·
  known limitations. Unknown fields are classified `[UNVERIFIED]` — **"free" ≠ "research-safe"** (§25
  license rule inherited). [FROZEN]

---

## 4. OBJECTIVE

Investigate whether ACASH can discover research candidates from free/public data without weakening the
standard. Candidate families allowed, subject to evidence: price-based · cross-sectional · momentum ·
mean reversion · volatility/regime · event-driven · expiration/flow · calendar effects · market
microstructure · liquidity · statistical market properties · public corporate events. [CHARTED]

**Rule:** no candidate exists merely because a strategy is easy to backtest. Every candidate begins as
a `RESEARCH CANDIDATE` and passes a governance/specification process before any hypothesis framing —
and HYP_003 minting remains separately governed (§19). [FROZEN]

---

## 5. PROHIBITED: PERFORMANCE SEARCH ("FIND ME A WINNER")

The program **never** performs unrestricted strategy/parameter/indicator/feature mining, massive grid
search, or random strategy generation. The question is NOT "highest Sharpe"; it is:

> _Identify economically motivated mechanisms that can be specified BEFORE seeing any result._

Every candidate needs: mechanism · causal rationale · observable input · event/time definition ·
signal definition · expected direction · holding horizon · universe · cost assumptions · data
requirements · falsification conditions · known leakage risks. [FROZEN — doctrine 1/4/7]

---

## 6. RESEARCH PIPELINE (CONCEPTUAL; NO STAGE MAY SKIP AHEAD)

```text
DATA DISCOVERY → DATA FEASIBILITY → MECHANISM DISCOVERY → CANDIDATE SPECIFICATION →
PRE-SPECIFICATION (freeze) → DATA AUDIT → IS/OOS DESIGN → VALIDATION →
GOVERNANCE REVIEW → ONLY IF AUTHORIZED → NEXT STAGE
```
Each stage terminates at its governance boundary. Empirical stages require explicit Human Governance
authorization; **until then they are NOT performed.** [FROZEN]

---

## 7. FREE-DATA SOURCE FAMILIES

Structured investigation only (per-family bounded search budget, §24). Categories: SEC EDGAR · public
exchange data · public index publications · public corporate filings · free historical OHLCV · public
macroeconomic datasets · public rates data · public economic indicators · public futures/reference
data where legally accessible · public event calendars · open-source historical datasets · genuinely
free APIs. No vendor is presumed acceptable; every source is independently evaluated in
`free_data_source_registry.md`. [CHARTED]

---

## 8. SOURCE QUALITY TIERS

- **TIER 1 — Primary authoritative source** (e.g., SEC EDGAR, Federal Reserve/FRED official series,
  BLS/BEA official releases, CBOE official index data, exchange/official schedules, S&P DJI
  announcements).
- **TIER 2 — High-quality public secondary source** (e.g., credentialed vendor daily history with
  documented terms: Stooq, Alpha Vantage free tier — with limitations; OpenFIGI symbology).
- **TIER 3 — Community-maintained dataset with provenance** (e.g., fja05680/sp500, pitindex — pinned
  commits; Wikipedia `oldid`; NYU Wurgler file; yfinance — with ToS caveat).
- **TIER 4 — Unverified aggregation / convenience dataset** (e.g., securitiesdb CA API, Kaggle
  delisted archive, FMP free tier). **TIER 4 may be used for exploratory feasibility only; it is NOT
  auto-evidence for a production-quality candidate.** [FROZEN]

---

## 9. SURVIVORSHIP BIAS — MANDATORY CONCERN

For every equity candidate: delisted securities, ticker changes, mergers, bankruptcies, symbol
changes, historical membership must be treated explicitly. **Never use a current ticker list as
historical universe membership.** If survivorship-free data cannot be obtained, the candidate is
marked **`SURVIVORSHIP_LIMITED`** and that limitation is never concealed. [FROZEN]

---

## 10. POINT-IN-TIME (PIT) REQUIREMENT

Any time-varying information (index membership, company status, fundamentals, free float, corporate
actions, events, eligibility) is PIT-sensitive. Current info must NOT be backdated. If PIT provenance
cannot be established → `PIT = UNVERIFIED`. [FROZEN — F-1 PIT hard rule extended to this track]

---

## 11. CANDIDATE GENERATION RULE

Mechanism-first, never backtest-first. Each proposal records: Candidate ID · Research family ·
Mechanism · Why the mechanism should exist · Observable data · Expected market behavior · Direction ·
Horizon · Universe · Data requirements · PIT requirements · Cost requirements · Main falsification risk
· Main leakage risk · Main survivorship risk. **No performance numbers at proposal stage.** [FROZEN]

---

## 12. ANTI-HARKING FREEZE RULE

Once a candidate is proposed, its specification is frozen BEFORE empirical tests. Signal, threshold,
horizon, universe, direction, event definition may NOT be changed because a result looks bad. A change
requires a NEW candidate/version plus a documented reason. [FROZEN — mirrors F-1 §18 anti-HARKing]

---

## 13. FREE-DATA-FIRST STRATEGY

Prefer candidates whose information requirements naturally exist free: public event dates, public
filings, calendar events, price/volume anomalies, broad market regime data, publicly observable index
changes, scheduled macro events. Avoid candidates whose validity depends fundamentally on proprietary
order flow, expensive tick data, premium fundamentals, proprietary alt-data, or institutional borrow
data — unless the objective is explicitly to document why they are currently infeasible ($30 queue).
[FROZEN]

---

## 14. DATA FEASIBILITY SCORECARD (NON-PERFORMANCE)

Per candidate: Price data availability · Universe availability · PIT availability · Delisted coverage ·
Corporate-action coverage · Event timestamp quality · Provenance · License · Reproducibility · Data
cost · Survivorship risk · Leakage risk. Values: `ACCEPT` · `CONDITIONAL` · `UNVERIFIED` ·
`NOT SUFFICIENT AT $0` · `REJECT`. Feasibility is NEVER converted into profitability. [FROZEN]

---

## 15. RESEARCH CANDIDATE PRIORITY

Rank candidates ONLY by: data feasibility · governance quality · mechanism clarity · PIT quality ·
reproducibility · implementation simplicity · expected cost realism. **NOT** by Sharpe/CAGR/win
rate/PnL/return until the appropriate governance stage authorizes empirical validation. [FROZEN]

---

## 16. STOP CONDITIONS FOR A CANDIDATE → `TERMINATED / BLOCKED`

Stop when: required data cannot be lawfully obtained at $0 · PIT cannot be established · survivorship
bias cannot be controlled · mechanism cannot be specified objectively · provenance cannot be
established · license unacceptable/unverified · hidden assumptions required · post-result
specification changes become necessary. Mark `TERMINATED / BLOCKED` with reason. [FROZEN]

---

## 17. BOUNDED RESEARCH — PREVENT RUNAWAY WORK

Per research family: define a bounded source-search budget (e.g., **10–20 high-quality source checks**).
If no credible path emerges → STOP, document, move to the next family. **Never increase the search
budget because results are unfavorable.** [FROZEN]

---

## 18. FIRST RESEARCH FAMILIES (start point; not all tested now)

1. Public event/calendar effects
2. Price-based cross-sectional effects
3. Simple momentum
4. Simple mean reversion
5. Volatility/regime
6. Public corporate-event effects
7. Index/rebalance effects → **RESERVED TO F-1 LANE** (excluded from this program's intake per §2)
8. Market-wide statistical properties

ORDER: data feasibility → mechanism specification → STOP for governance if empirical validation needs
new authorization. [CHARTED]

---

## 19. CAPITAL BOOTSTRAP PRINCIPLE

Capital generation is an OUTCOME, not an assumption. Language stays conditional: "_candidate may be
viable if validation criteria are met_" — never "_this will make money_". [FROZEN]

Capital path (aspiration, NOT guarantee):
`$0 → free data → research candidate → governance → validation → authorized paper/live stage →
capital (if successful) → premium data → stronger research`. [CHARTED]

---

## 20. F-1 PARALLEL TRACK & BOUNDED BLOCKER QUEUE

F-1 stays alive with a **bounded blocker queue: B2, B5**. Only genuinely NEW evidence is investigated;
repeated searches of the same sources are prohibited. If no credible $0 solution emerges after bounded
effort → document the blocker; never redefine the problem to make it pass. [FROZEN]

---

## 21. FREE-DATA TRACK GOVERNANCE / RESEARCH REGISTRY

Separate registry (`free_data_research_registry.md`). Every candidate has: unique ID · status · source
set · specification digest · data-feasibility status · governance status. Statuses:
`PROPOSED` · `DATA_FEASIBILITY_REVIEW` · `SPEC_FREEZING` · `PRE_REGISTERED` · `VALIDATION_PENDING` ·
`VALIDATION_COMPLETE` · `HUMAN_REVIEW_REQUIRED` · `REJECTED` · `TERMINATED`. **`HYP_003` is never used
for this track without explicit Human Governance authorization.** [FROZEN]

---

## 22. NO AUTOMATIC HYPOTHESIS CREATION

A promising free-data candidate ≠ HYP_003. HYP_003 creation remains separately governed (canonical
pre-registration path). A mature candidate gets a decision surface prepared, then **STOP for Human
Governance**. [FROZEN]

---

## 23. ENGINEERING TRACK (GENERIC INFRASTRUCTURE ONLY)

Improving generic research infrastructure is acceptable IF it does not encode a specific unapproved
strategy: data provenance model · source registry · PIT metadata · dataset manifest · data-quality
checks · survivorship checks · corporate-action normalization · deterministic experiment manifests ·
research candidate registry · reproducibility checks · audit reports · evidence hashing · blind-window
support · OOS isolation · cost-model interfaces · telemetry · failure reporting. Implementing a
specific strategy is NOT acceptable merely because it is interesting. [FROZEN]

---

## 24. RESEARCH FACTORY DESIGN

Lifecycle gate shape (future candidates enter here):
`CandidateProposal → DataFeasibilityReview → SpecificationFreeze → PreRegistration → Validation →
HumanDecision`. Design must make it hard to: alter frozen parameters · mix IS/OOS · reuse OOS · hide
failed trials · silently change universe · silently change cost assumptions · backdate current metadata
· use survivorship-biased universes. [FROZEN]

---

## 25. FAILURE IS VALID OUTPUT

Record why a candidate failed (data/PIT/mechanism/cost/survivorship/reproducibility limitation).
Maintain a research census; never delete failed candidates because they are unattractive. [FROZEN]

---

## 26. REPORTING — PROCESS METRICS ONLY

Dashboard reports PROCESS metrics only: active/proposed/blocked/rejected candidate counts ·
free-data-feasible count · PIT-ready count · license-ready count. **No profit/Sharpe/CAGR/win-rate**
until the relevant stage authorizes empirical validation. **Every report must show the F-1 line:**
`F-1 · D1 = NOT READY / CONDITIONAL · B2 = BLOCKED · B5 = UNVERIFIED` — the Free-Data Track must never
make F-1 look passed. [FROZEN]

---

## 27. PAID-DATA FUTURE — ACQUISITION QUEUE (NO PURCHASE NOW)

Maintain `FUTURE DATA ACQUISITION QUEUE`; prioritize by which blocker they solve · historical depth ·
PIT quality · delisted coverage · corporate actions · free-float history · reproducibility · expected
research value. Current likely high-value targets (capability names only; **NO vendor is selected**):
- B2 — delisted/security-master history
- B5 — historical free-float / IWF-quality data
- (PEAD SUE variant) — historical analyst-consensus expectations (candidate `CAND-FREE-PEAD-001`, see registry)

No vendor is named as selected unless Human Governance explicitly selects it. Purchases require prior
budget authorization. [FROZEN — not authorized to buy]

---

## 28. GIT POLICY

Initial setup is READ-ONLY Git inspection followed by documentation-only file creation. **No
automatic commit/push**; the three program documents remain UNTRACKED unless Human Governance
explicitly authorizes commit/push. Never mutate existing history. [FROZEN]

---

## 29. LOCKS

The following remain LOCKED unless explicitly authorized by Human Governance — **no matter how
promising any free-data candidate appears**: D2 · HYP_003 · R1 · ReInceptionGate · Phase 6
qualification · paper trading · live trading · broker connection · capital deployment · backtest ·
optimization · parameter search · empirical performance claims. [FROZEN]

---

## 30. CANONICAL FINAL STATE (UNCHANGED BY THIS PROGRAM)

```text
F-1 = S&P Composite 1500
D1  = NOT READY / CONDITIONAL
D2  = LOCKED
HYP_003 = NOT AUTHORIZED
R1  = NOT AUTHORIZED
GATE = NOT AUTHORIZED
TRADING = LOCKED
CAPITAL = $0.00
Free-Data Capital Bootstrap Program = ACTIVE (research program only)
```

### Verification Ledger (this charter)
- Implementation Status: NONE (documentation-only; `src/` untouched; new untracked document).
- Contract Enforcement: STRICT FAIL-CLOSED — no strategy encoded, no performance claim, no paid-data
  authorization, no status promotion.
- Mathematical Authority: N/A; canonical gates untouched.
- Local Test Suite: NOT RUN (documentation-only convention).
- Remote CI Status: NOT AVAILABLE.
- Methodological Caveats: this track is separate from F-1; empirical work requires explicit Human
  authorization per candidate; all external mechanism claims are REPORTED/INFERRED/NOT PROVEN.

STOP — FREE-DATA CAPITAL BOOTSTRAP PROGRAM INITIALIZATION COMPLETE (charter). F-1 UNCHANGED. D1 NOT READY. NO HYP_003 / R1 / GATE / TRADING AUTHORIZATION.