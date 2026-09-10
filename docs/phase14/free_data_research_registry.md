# ACASH V5 — FREE-DATA RESEARCH REGISTRY

**Document ID:** `docs/phase14/free_data_research_registry.md`
**Object:** Research-candidate register + family feasibility analysis for the Free-Data Capital
Bootstrap Program (F-1-separate lane)
**Status:** `[DOCUMENTATION-ONLY]` · `[NOT HYP_003]` · `[NOT R1]` · `[NOT D2]` · `[NOT F-1]`
**Date:** 2026-09-10

**Read this first:**
- This registry contains **research candidate proposals only**. None is a strategy, an authorized
  hypothesis, or a tradeable plan. Candidate statuses are governed as defined in the program charter
  (§21): `PROPOSED` · `DATA_FEASIBILITY_REVIEW` · `SPEC_FREEZING` · `PRE_REGISTERED` ·
  `VALIDATION_PENDING` · `VALIDATION_COMPLETE` · `HUMAN_REVIEW_REQUIRED` · `REJECTED` · `TERMINATED`.
- **No performance numbers appear in this registry** (no Sharpe, no CAGR, no win rate, no backtest,
  no PnL). Feasibility ≠ profitability (§15 of charter).
- **No candidate may proceed to empirical validation without Human Governance authorization** (§8 of
  program prompt; §19/§22 of charter). All five proposed candidates below are therefore frozen at the
  PROPOSAL boundary and await that authorization — none is currently authorized to run any empirical
  test, backtest, or optimization.

---

## 1. RESEARCH FAMILY FEASIBILITY MATRIX

Feasibility uses the scorecard (§14 of charter): Price data · Universe · PIT · Delisted coverage ·
CA coverage · Event timestamp · Provenance · License · Reproducibility · Cost · Survivorship risk ·
Leakage risk → `[ACCEPT]` / `[CONDITIONAL]` / `[UNVERIFIED]` / `[NOT SUFFICIENT AT $0]` / `[REJECT]`.
Source registrations: S-XX refer to `free_data_source_registry.md`.

| # | Family | Feasibility (headline) | Key $0 sources | PIT / Survivorship / License | Verdict |
|---|--------|------------------------|----------------|------------------------------|---------|
| 1 | Public event/calendar effects | Strong | S-05 (BLS calendar), S-08 (FOMC), S-06 (Treasury); SPX/SPY via S-10/S-18 | PIT `[ACCEPT]` (pre-announced schedules); Survivorship N/A; License `[ACCEPT]` | `[ACCEPT]` | 
| 2 | Price cross-sectional effects | Weak at $0 for equal footing | S-10 (active), S-11 (delisted metadata) | PIT `[UNPROVEN]`; Survivorship `[LIMITED]`; License `[CONDITIONAL]` | `[CONDITIONAL]` (later intake) |
| 3 | Simple momentum | Viable w/ constraints | S-10/S-18 active OHLCV + S-13/S-14 pinnable universes, S-01/S-02 delisting identities | PIT `[UNPROVEN]` (retro lookbacks); Survivorship `[LIMITED]`; License `[CONDITIONAL]` | `[CONDITIONAL]` |
| 4 | Simple mean reversion | Viable w/ hard cost constraints | S-10/S-18 active OHLCV | PIT `[UNPROVEN]`; Survivorship `[LIMITED]`; License `[CONDITIONAL]` | `[CONDITIONAL]` (high cost-sensitivity) |
| 5 | Volatility/regime | Strong | S-04 (VIXCLS), S-07 (CBOE daily), SPX S-10 | PIT `[ACCEPT]` (daily official index); Survivorship N/A; License `[CONDITIONAL]` | `[ACCEPT]` |
| 6 | Public corporate-event effects | Strong for event PIT; constrained for price | S-01/S-02 (filings/Form 25), S-03 (N-PORT rosters); delisted price leg `[NOT SUFFICIENT AT $0]` | PIT `[ACCEPT]` (filing timestamps); Survivorship `[LIMITED]` (price leg); License `[ACCEPT]` | `[CONDITIONAL]` |
| 7 | Index/rebalance effects | `[VERIFIED]` viable — **RESERVED TO F-1 LANE** | S-09 (S&P DJI), S-13/S-14/S-15/S-16/S-17 | PIT `[CONDITIONAL]`; survivor-clean; License `[CONDITIONAL]` | **EXCLUDED from this track** (charter §2 lane separation) |
| 8 | Market-wide statistical properties | `[ACCEPT]` as cross-checks/context, NOT standalone tradeable candidate | S-04 (index level), S-10 (SPX) | PIT `[ACCEPT]`; Survivorship N/A; License `[ACCEPT]` | `[ACCEPT]` (context only) |

**Feasibility notes (evidence-bound):**
- Family 1: FOMC/CPI/NFP publication is pre-announced, timestamped, and free (S-05/S-08/S-06). Strongest
  PIT economics at $0. Directional/vol-dated variants both plausible; risk-based interpretations
  multiple.
- Family 6 PEAD: earnings-date PIT from SEC filing acceptance (S-01) is clean, but (a) filing
  acceptance ≠ press-release first public dissemination, (b) standardized-surprise (SUE) requires
  analyst-consensus history = `[NOT SUFFICIENT AT $0]` (future-queue); therefore the $0-variant is
  price/announcement-drift on "filing dates" only (event-time drift), marked `SURVIVORSHIP_LIMITED`
  (delisted return leg via S-03 roster + S-10 active names; delisted OHLCV `[NOT SUFFICIENT AT $0]`).
- Family 3 momentum: free OHLCV covers active names; pinned universe snapshots (S-13/S-14) give
  as-of membership; survivors for the return leg until delisted, whose absence biases returns
  upward — must be declared `SURVIVORSHIP_LIMITED`. License: personal-use (S-10) / Yahoo-ToS risk
  (S-18); redistribution constrained.
- Family 4 reversal: same survivorship envelope as family 3, PLUS extreme cost/half-life sensitivity:
  at short horizons the fee/impact/cost model can exceed edge; cost realism becomes a falsifier at
  $0 (no realistic execution cost model is free). Marked high-risk of `REJECT` at validation.
- Family 5: VIXCLS official series (S-04) and CBOE daily (S-07) give PIT-daily vol-state data.
  Regime/VRP candidates are mechanism-clear and data-cheap; the primary non-performing risk is
  model/parameter overfit across regimes (shared data across sequential tests ⇒ dependence, doctrine 8).
- Family 2: deprioritized at intake because price cross-section at $0 is dominated by
  active-name/survivorship issues; revisit only after B2-queue territory or as `SPEC_FREEZING` later.

---

## 2. CANDIDATE REGISTER (MAX 5 PROPOSALS)

Naming: `CAND-FREE-<DESCRIPTOR>-NNN`. Status of all five: `DATA_FEASIBILITY_REVIEW → SPEC_FREEZING`
completed on paper; **stopped at `HUMAN_REVIEW_REQUIRED`** for the EMPIRICAL VALIDATION boundary.

---

### CAND-FREE-PEAD-001 — Earnings-announcement (filing-date) drift

| Field | Value |
|-------|-------|
| Research family | 6 — Public corporate-event effects |
| Mechanism | Trading around / shortly after corporate earnings disclosure shows post-announcement drift — a documented market-inefficiency mechanism (initial reaction is incomplete; prices drift in the same direction; conference proceeds from academic literature). |
| Why it should exist | Information is costly to process; retail+institutional under-reaction to periodic disclosure is a replicated, economically-motivated phenomenon — but this candidate FREES the mechanism from any specific parameter and specifies it BEFORE seeing results. |
| Observable data | SEC EDGAR filing acceptance timestamps (S-01); Form 25 delisting IDs (S-02); N-PORT roster anchors & delistings for membership (S-03); daily OHLCV for ACTIVE names (S-10 Tier-2 license) — delisted OHLCV leg `[NOT SUFFICIENT AT $0]`. |
| Expected market behavior | Post-disclosure continuation (direction: continuation of the initial filing-window move), at a bounded horizon. |
| Direction | Drift continuation (sign-matched to filing-window move). |
| Horizon | FILED: 10 trading days (primary); alternatives documented but NOT changeable post-result. |
| Universe | S&P 500 roster as-of (pinned via S-13/S-14; S&P 500 only), filtered to active-name price leg. |
| Data requirements | Filing-date PIT (S-01 accession timestamps); daily OHLCV (S-10); universe snapshots (S-13/S-14). |
| PIT requirements | Filing acceptance timestamps are PIT PROVEN; roster snapshots pinned as-of. |
| Cost requirements | $0; fee/impact assumptions modeled from public fee schedules (no fill realism claim). |
| Main falsification risk | No post-announcement continuation beyond noise at $0-cost universe; drift is a small-effect phenomena that may not survive realistic costs. |
| Main leakage risk | Filing acceptance ≈ 15:30–24:00 ET lag vs press-release dissemination — "filing-date drift" ≠ press-release PIT; timing misalignment can look like leakage. |
| Main survivorship risk | `SURVIVORSHIP_LIMITED` — delisted (bankrupt/acquired) names absent from the return leg. |
| Data feasibility status | `[CONDITIONAL]` (event-time PIT `[ACCEPT]`; price leg survivorship-limited). |
| Governance status | PROPOSED → SPEC_FREEZING (paper) → **HUMAN_REVIEW_REQUIRED** (empirical authorization). |

---

### CAND-FREE-MACRO-001 — Scheduled macroeconomic-announcement effects

| Field | Value |
|-------|-------|
| Research family | 1 — Public event/calendar effects |
| Mechanism | Scheduled announcements (FOMC, CPI, NFP) concentrate information / re-price risk at known timestamps; option-implied vs realized behavior around such events is recurrent. |
| Why it should exist | Calendars are pre-announced, costless, and economically meaningful; the mechanism is mechanism-first (event-time conditioning), not a number hunt. |
| Observable data | FOMC statement release (S-08); BLS CPI/NFP schedule + values (S-05); SPX/SPY daily (S-10/S-18); VIXCLS (S-04). |
| Expected market behavior | Conditional return/vol realization around scheduled releases deviates from unconditioned behavior in a direction discoverable only post-spec; the SPECIFIED object is the event-conditioned time series, NOT a Sharpe. |
| Direction | PENDING (frozen at proposal: "event-conditioned deviation", no ex-ante sign asserted). |
| Horizon | FILED: 1 trading day centered on the announcement (event-day ± opened); alternatives documented, not changeable post-result. |
| Universe | Index-level (SPX index values; SPY as robustness cross-check under terms). |
| Data requirements | Schedules (PIT proven), index/data series (S-04/S-10), archive-at-retrieval. |
| PIT requirements | Full — schedules pre-announced; index values official daily. |
| Cost requirements | $0. Single-name easing not required ($0 single-name PIT schedule data only via S-05 aggregate). |
| Main falsification risk | No measurable conditional effect vs. unconditioned baseline at $0 dataset granularity. |
| Main leakage risk | Calendar times published well in advance — no leakage if release times archived at retrieval (pre-announced). |
| Main survivorship risk | None (index-level). |
| Data feasibility status | `[ACCEPT]`. |
| Governance status | PROPOSED → SPEC_FREEZING (paper) → **HUMAN_REVIEW_REQUIRED** (empirical authorization). |

---

### CAND-FREE-VOL-001 — Volatility-regime / variance-premium characteristics

| Field | Value |
|-------|-------|
| Research family | 5 — Volatility/regime |
| Mechanism | Volatility states are persistent and priced; the variance-risk-premium (VIX vs realized) is one documented mechanism. Candidate specifies regime-conditioning behavior, NOT a "sell vol" strategy. |
| Why it should exist | VIX/realized relationship is a documented empirical regularity with economic interpretation (premium for uncertainty); regime identification is mechanism-first. |
| Observable data | VIXCLS (S-04), VIX daily (S-07), SPX daily (S-10), realized vol construction from daily returns. |
| Expected market behavior | Conditional behavior of realized vs implied vol by regime; regime conditional return characteristics (direction and magnitude NOT promised ex-ante). |
| Direction | Unspecified (regime-contingent observation object; not a directional bet). |
| Horizon | 21 trading days (vol estimation window), 1–10 day conditional window; frozen. |
| Universe | Index-level (VIX/SPX). |
| Data requirements | S-04/S-07/S-10 series with archive-at-retrieval; vintage discipline for VIXCLS. |
| PIT requirements | Daily official index values = PIT-proven modulo official vintage (vintage `[CONDITIONAL]`). |
| Cost requirements | $0. |
| Main falsification risk | No persistent regime structure at daily frequency; premium not distinguishable from noise in sample. |
| Main leakage risk | Minimal for daily index values; revision can change realized-vol — use as-published. |
| Main survivorship risk | None (index-level). |
| Data feasibility status | `[ACCEPT]` (with vintage conditional). |
| Governance status | PROPOSED → SPEC_FREEZING (paper) → **HUMAN_REVIEW_REQUIRED** (empirical authorization). |

---

### CAND-FREE-MOM-001 — Simple historical momentum (price)

| Field | Value |
|-------|-------|
| Research family | 3 — Simple momentum |
| Mechanism | Persistent relative price trends are a documented cross-sectional regularity (academic); candidate specifies a SIMPLE 12-1 / 6-1 momentum construct over ACTIVE large-cap names. |
| Why it should exist | Momentum is among the best-replicated cross-sectional phenomena; the intent is to measure/characterise an economically-motivated regularity, not to promise returns. |
| Observable data | Active-name daily OHLCV (S-10/S-18); pinned S&P membership snapshots (S-13/S-14) as-of; delisting identity list (S-01/S-02). |
| Expected market behavior | Continuation of relative past-return ranking over the specified horizon (direction: long top / short bottom of ranking). |
| Direction | LONG relative leaders / SHORT relative laggards (symmetric, tie-symmetric policy required — doctrine 10). |
| Horizon | 12-1 month (primary), 6-1 month (secondary) — both frozen; ranking at holding-period ends. |
| Universe | S&P 500 (pinned as-of; survivorship limited to active names for the return leg). |
| Data requirements | OHLCV; as-of roster snapshots; delisted identity leg for honest de-listing disclosure. |
| PIT requirements | `[UNPROVEN]` retro lookback (past-12 price series unchanged on later dates — lookback constructs use only past data: PIT-safe computationally; roster pinning is the load-bearing item). |
| Cost requirements | $0; rebalance fee/impact modeled from public schedules, conservative. |
| Main falsification risk | Momentum premia vanish at realistic costs, or rank effect below noise within sample. |
| Main leakage risk | Survivorship (delisted names excluded inflate leader returns); must disclose and quantify. |
| Main survivorship risk | PRIMARY — `SURVIVORSHIP_LIMITED` (delisted names absent: category-5 doctrine concern). |
| Data feasibility status | `[CONDITIONAL]` (survivorship-limited; personal-use license; redistribution constrained). |
| Governance status | PROPOSED → SPEC_FREEZING (paper) → **HUMAN_REVIEW_REQUIRED** (empirical authorization). |

---

### CAND-FREE-REV-001 — Short-horizon mean reversion

| Field | Value |
|-------|-------|
| Research family | 4 — Simple mean reversion |
| Mechanism | Short-horizon reversal is a documented microstructure/liquidity phenomenon; candidate specifies a simple reversal construct with hard cost realism. |
| Why it should exist | Academic evidence of short-horizon return reversal tied to liquidity provision; mechanism-first. |
| Observable data | Active-name daily OHLCV (S-10/S-18); S&P 500 roster as-of (S-13/S-14). |
| Expected market behavior | Fade of short-horizon extreme moves (direction: LONG recent losers / SHORT recent winners over the hold window). |
| Direction | LONG short-term losers / SHORT short-term winners. |
| Horizon | 5-trading-day formation / 5-day hold (frozen); longer alternatives documented, not changeable post-result. |
| Universe | S&P 500 (pinned as-of; survivor-limited to active names). |
| Data requirements | OHLCV; roster as-of; delisted identity leg (S-01/S-02) for disclosure. |
| PIT requirements | Same construct-discipline as momentum candidate (lookback PIT-safe; universes pinned). |
| Cost requirements | $0 — but reversal edge is small; conservative modeled costs can exceed edge → `REJECT`-likely at validation unless the mechanism holds at costs. |
| Main falsification risk | Edge below modeled cost at any horizon; regime-dependent effect absent in modern sample. |
| Main leakage risk | Survivorship (delisted losses excluded) again inflates the reversion leg. |
| Main survivorship risk | PRIMARY — `SURVIVORSHIP_LIMITED`. |
| Data feasibility status | `[CONDITIONAL]` (survivorship + cost). |
| Governance status | PROPOSED → SPEC_FREEZING (paper) → **HUMAN_REVIEW_REQUIRED** (empirical authorization). |

**NOT PROPOSED AT THIS INTAKE (recorded for the census):**
- Family 7 (index/rebalance) — EXCLUDED by lane separation (charter §2); all index-event evidence belongs
  to F-1. `[REJECTED - LANE SEPARATION]`.
- Family 2 price-cross-section — deferred to a later intake after the B2-queue/provenance lane matures.
  `[PROPOSED → REJECTED (DEFERRED, NOT TERMINATED)]`.
- Family 8 statistical-characterization — allowed only as provenance context/regime flags; never as a
  tradeable candidate at this stage. `[CONTEXT ONLY]`.

---

## 3. SPECIFICATION FREEZE (ANITI-HARKING) — applies to all five candidates

Per charter §12, each specification above is FROZEN at the proposal boundary:
- No parameter/design change post-result permitted; any change = NEW candidate + documented reason +
  Human Governance review.
- No empirical test, backtest, optimization, or parameter search may run until Human+Governance
  authorization per candidate (§8 / §19 / §22).
- All five carry the status `SPEC_FREEZING` (paper-frozen) and transition only upon authorization.

**Authorization decision surface (STEP 8 of the program prompt):**

| Candidate | Empirical validation authorized? | Who must authorize | Required before ANY empirical run |
|-----------|-------------------------------|-------------------|-----------------------------------|
| CAND-FREE-PEAD-001 | **NOT AUTHORIZED** | Human Governance | data-audit + manifest + authorization note |
| CAND-FREE-MACRO-001 | **NOT AUTHORIZED** | Human Governance | same |
| CAND-FREE-VOL-001 | **NOT AUTHORIZED** | Human Governance | same |
| CAND-FREE-MOM-001 | **NOT AUTHORIZED** | Human Governance | same |
| CAND-FREE-REV-001 | **NOT AUTHORIZED** | Human Governance | same |

NONE is `VALIDATION_PENDING`. This document establishes the STOP boundary only.

---

## 4. RESEARCH CENSUS (Process metrics only — dashboard per §26)

| Metric | Value |
|--------|-------|
| Candidates proposed (this intake) | 5 |
| Free-data-feasible (`[ACCEPT]`/`[CONDITIONAL]`) | 5 (2 `ACCEPT`, 3 `CONDITIONAL`) |
| PIT-ready | 5 (2 full, 3 with construct discipline) |
| License-ready | 3 | 
| Survivorship-limited declarations | 3 (PEAD, MOM, REV) |
| Blocked / Rejected / Terminated | 0 / 1 (family-7 lane separation) / 0 |
| Status distribution | 5 × `HUMAN_REVIEW_REQUIRED` (awaiting empirical authorization) |
| Performance metrics published | **0** (none permitted) |
| F-1 visibility line | `F-1 · D1 = NOT READY / CONDITIONAL · B2 = BLOCKED · B5 = UNVERIFIED` — UNCHANGED |

### Verification Ledger (this registry)
- Implementation Status: NONE (documentation-only; no empirical work, no `src/` changes).
- Contract Enforcement: STRICT FAIL-CLOSED — zero performance claims; zero unlicensed-data
  assumptions; zero status promotions; family-7 cleanly excluded from this lane.
- Mathematical Authority: mechanisms cited as academic-literature-motivated; all claims
  REPORTED/INFERRED/NOT PROVEN pending ACASH evidence (doctrine §16).
- Local Test Suite / Remote CI: NOT RUN / NOT AVAILABLE (documentation-only convention).
- Methodological Caveats: the three `SURVIVORSHIP_LIMITED` candidates can only be validated with full
  disclosure of the limitation; CAND-FREE-PEAD-001 uses filing-date (not press-release) event time;
  CAND-FREE-REV-001 may be REJECTED at validation on cost realism; candidates never equal HYP_003.

STOP — FREE-DATA RESEARCH REGISTRY INITIALIZED (5 PROPOSALS, ZERO PERFORMANCE CLAIMS). NO EMPIRICAL
VALIDATION AUTHORIZED. F-1 UNCHANGED. D1 NOT READY. NO HYP_003 / R1 / GATE / TRADING AUTHORIZATION.