# PHASE14 F-1 PRE-REGISTRATION READINESS REVIEW

**Document ID:** `docs/phase14/reviews/review_cand_flow_calendar_rebalance_001.md`
**Review Object:** Candidate `CAND-FLOW-CALENDAR-REBALANCE-001` (Structural / Forced Flow)
**Status:** FIRST-PRINCIPLES SPECIFICATION REVIEW - design preparation only
**Date:** 2026-09-07
**Authority:** `../AGENTS.md`, `../research_doctrine.md`, `../research_candidates.md`,
Phase 14 Master Architecture, `../../src/acash/research/reinception.py`
(`./phase14_master_research_architecture_plan.md`, `./research_doctrine.md`,
`./research_candidates.md`)

> [!CAUTION]
> ### HARD GOVERNANCE & SAFETY INVARIANTS
> - **THIS REVIEW CREATES NO HYPOTHESIS. HYP_003 REMAINS ABSENT.**
> - **NO GATE INVOCATION:** `ResearchReInceptionGate` is NOT invoked. No R1. No sealing.
> - **NO DATA / NO EXPERIMENT:** Zero market data accessed, downloaded, or generated; zero backtests,
>   statistical tests, parameter optimization, or OOS inspection.
> - **NO IMPLEMENTATION:** Slice 1-4, frozen core, governance gates, ExecutionCoordinator unchanged.
> - **CAPITAL & TRADING HARD-LOCKED:** Capital = **$0.00**; Trading = **LOCKED**.
> - All mechanism claims in this review are **REPORTED / INFERRED / NOT PROVEN**.
> - Every proposed numeric value is **PROPOSED / NOT YET SEALED** and must be frozen at R1; nothing is
>   tuned here.

---

## Mechanism-First Causal Chain (doctrine 4/5/6/7; not indicator-first)

1. **Who is structurally forced to trade?**
   Index-tracking funds and ETFs (passive/mandated) that must transact on index constituent changes at
   the scheduled **effective date** to minimize tracking error. Primary: index reconstitution /
   quarterly rebalance flows. Secondary: month-end balance-sheet / contribution flows. The forced
   trader acts because the constraint is a **timestamp**, not a price.
2. **What recurring constraint causes the flow?**
   A fixed, published index-methodology calendar (e.g., annual reconstitution effective date, quarterly
   rebalance effective after third-Friday close). The mandate makes demand/supply price-insensitive at
   the deadline; ETF creation/redemption and tracking-error discipline propagate it.
3. **When should the flow occur?**
   Clustered in the closing period of the effective date and the surrounding days (anticipatory
   trading partially front-runs it).
4. **Which observable market variable should reflect it?**
   (a) a deterministic event indicator (constituent added/deleted at effective date); (b) abnormal
   volume / shares-implied flow at the effective close; (c) the effective-close price move; (d) the
   post-event cumulative return in the reversal window.
5. **What price/return effect should occur?**
   Additions: temporary positive pressure at the effective close that partially reverts; deletions:
   temporary negative pressure that partially reverts. Net: a short-horizon mean-reversion of
   flow-driven dislocation around the effective date.
6. **Over what horizon?**
   Days. Primary reversal window H = 5 business days; secondary 1 and 10 days.
   (PROPOSED / NOT YET SEALED.)
7. **Why should the effect persist long enough to trade?**
   Forced prints occur regardless of price; residual inventory is unwound over subsequent days;
   arbitrage capacity is bounded by shorting frictions (deletions), borrow costs, and execution risk.
8. **What costs could eliminate it?**
   Bid/ask + slippage + impact at the effective close; deletions require locate/short-borrow; both-leg
   two-sided friction; latency of reacting to published lists; crowding. Net edge must be evaluated
   against the canonical cost model.
9. **What observation would falsify the mechanism?**
   A pre-registered test showing the dislocation produces no economically meaningful **post-cost** net
   edge over the declared in-sample window at pre-registered thresholds (rank IC, HAC t, cost-adjusted
   spread ratio), or that the effect is not stable across declared sub-periods.

---

## Required Review Outputs

### 1. Candidate identity
- Provisional Candidate ID: `CAND-FLOW-CALENDAR-REBALANCE-001` (NOT HYP_003).
- Family: Structural / Forced-Flow (calendar-forced rebalancing). Registered in
  `./research_candidates.md` (F-1).

### 2. Economic / behavioral mechanism
Index rebalancing / reconstitution forces price-insensitive, timestamp-constrained demand (additions)
and supply (deletions) from passive indexers and ETFs. The resulting temporary price dislocation is a
candidate for a short-horizon mean-reversion effect after the flow clears (doctrine 5: structural
flow is researchable).

### 3. Causal chain
As in the Mechanism-First section above: forced institution -> published event calendar -> clustered
timestamp-constrained flow -> observable event indicator / volume / close move -> temporary dislocation
-> bounded-by-shorting-arbitrage reversal over days.

### 4. Testable research question
"For scheduled US equity-index reconstitution/rebalance events, do additions and deletions exhibit a
temporary price dislocation that (i) shows a reversal pattern over the following 1-10 business days
and (ii) yields a post-cost net edge that is economically meaningful?"

### 5. Null hypothesis (H0)
The pre-registered dislocation indicator has no economically meaningful net-of-cost predictive
relationship with forward returns in the declared in-sample window; post-cost cumulative reversal <= 0.
Formally: in-sample rank IC and HAC t-stat below pre-registered thresholds; cost-adjusted spread ratio
below 1.50.

### 6. Alternative hypothesis (H1)
Forced-flow dislocation partially reverses: the pre-registered indicator negatively predicts forward
returns (fade the dislocation), with net-of-cost edge > 0 meeting the pre-registered statistical and
economic thresholds.

### 7. Expected direction
**SHORT** on the pre-registered flow-pressure indicator (feature = +1 stale additions / -1 deletions;
expected forward-return correlation negative). Pre-registered sign; no sign flipping.

### 8. Target variable
Forward discrete return of the constituent from the effective-date reference price (official
close/auction print) to close at horizon h, over h in {1, 5, 10} business days
(PROPOSED / NOT YET SEALED).

### 9. Candidate observable features
- `rebalance_flow_pressure_indicator` (+1 additions / -1 deletions / 0 otherwise) - the primary,
  deterministic, pre-announceable feature.
- Abnormal volume and dollar-flow at the effective close (secondary, for mechanism confirmation only -
  NOT for candidate selection).
- Pre-event period return and index-relative move (control/confounder covariates).
Canonical `feature_dependencies` would contain the primary indicator and close-price series
(design-level only; frozen at R1).

### 10. Time horizon
Calendar-events measured in business days; expected holding horizon = days (primary 5d, secondary
1d/10d). Time-horizon treated as an empirical research variable (doctrine 6).

### 11. Universe / market scope
US equity index constituents (PROPOSED: large/mid-cap index) with sufficient liquidity; explicitly
exclude micro-caps, and exclude any instrument/window overlapping the EURUSD quarantined windows.
Final universe, size-band filter, and min-ADV threshold must be frozen at R1 (PROPOSED / NOT YET
SEALED).

### 12. Event definition
One family only. PROPOSED primary: published index reconstitution/rebalance **effective date** where
the constituent list change is officially announced in advance and the effective close is the mandated
trading constraint. A SEASONAL alternative (month-end window flows) may be prepared as a separate
pre-registration, but the two families MUST NOT be combined or switched post-hoc.

### 13. Entry / measurement semantics
Feature value is measured at the event (date known from published lists, pre-specified sign). Forward
return measured close-to-close from the effective-date close reference price to horizon h. No
intraday conditioning is required for the primary test. All semantics frozen at R1.

### 14. Exit / measurement semantics
Horizon-h close exit; returns cost-adjusted using the canonical `CostModelConfig` friction model;
no trailing/adaptive modification (keeps degrees of freedom zero).

### 15. Cost / friction model requirements
Reuse canonical `CostModelConfig` (quoted_spread_bps, roundtrip_broker_fee_bps, fixed_slippage_bps,
latency). PROPOSED per-leg values for equity at-event execution (e.g., spread ~1-2 bps, fee ~1.0 bps,
slippage/impact ~5-20 bps) - PROPOSED / NOT YET SEALED; deletions additionally require a pre-registered
short-borrow/locate cost assumption. Sensitivity to at least a 2x cost multiplier must be reported.

### 16. Liquidity requirements
Constituents must exceed a frozen min-ADV / min free-float threshold to be tradeable at the effective
close; universe cap by index membership; exclude names with no practical short market for the
deletion leg. Frozen at R1.

### 17. Potential confounders
Coincident earnings announcements (list announcement window), sector rotation, macro events
(FOMC/CPI near month-end), same-day cross-sectional flow correlation (event clustering), anticipatory
trading partially embedding the expected flow, and crowding (doctrine 7) must be enumerated and
controlled in pre-registered robustness sets.

### 18. Falsification conditions
Pre-registered: (a) in-sample rank IC fails (>= 0.025 PROPOSED, gate floor > 0); (b) HAC t-stat
below pre-registered minimum (>= 2.00 PROPOSED, gate floor >= 1.50); (c) min_cost_adjusted_spread_ratio
< 1.50; (d) max_feature_autocorrelation above 0.98; (e) net-of-cost cumulative reversal <= 0 over the
declared window; (f) placebo-date permutation test (shuffled event calendar) shows no dislocation.
Any one failing = hypothesis falsified.

### 19. Robustness requirements
Sub-period splits (pre-registered break points), drop-coincident-earnings exclusion, alternate size
bands, alternate cost assumptions (1x/2x/5x), and placebo-date permutations. All must be declared
before touching data.

### 20. Multiple-testing risks
Degrees of freedom: event-family choice (reconstitution vs month-end vs both), legs (single composite
indicator vs separate add/delete), horizon set, universe filter, cost assumptions. ALL cardinality must
be collapsed into `planned_trial_count == grid_cardinality` at R1 (anti-HARKing gate invariant,
`reinception.py`). No post-hoc selection among families, horizons, or universes.

### 21. HARKing risks
Every numeric in this review is PROPOSED / NOT YET SEALED. The R1 parameter grid must be declared as
the Cartesian product frozen at registration; no parameter search, minimax, or "best model" selection
on in-sample data is permitted. This review performs zero optimization.

### 22. Required data fields
- Official event calendar: effective dates + constituent add/delete lists (as-announced, prior to
  effective date).
- Per-name daily close / adjusted returns, weights, shares/volume (ADV), free float/market cap,
  sector (GICS), earnings calendar.
- Short-locate / borrow flags for deletions (optional but required for cost realism).
- Bar frame: daily (PROPOSED); intraday NOT required for the primary H0 test.
- Dataset window must be declared de novo and blind (fresh independent window, disjoint from all
  quarantined windows) before any return inspection.

### 23. Required sample size principles
- Reconstitution events are sparse (~1/year); single-index samples may be small. Pre-register a
  minimum usable **effective** event count in-sample (PROPOSED >= 25 per composite leg) before
  acceptance.
- Account for overlapping horizons and same-date clustering: compute HAC inference (fixed
  horizon-minus-one/declared policy) and cluster by event date; use `T_eff` (independent effective
  observations) explicitly, never raw bar count alone.
- Minimum usable bars window (e.g., multi-year daily history) must be frozen at R1; this review
  cannot verify availability (data access not authorized) - **NOT PROVEN**.

---

## Quarantine / Independence Assessment

- HYP_001 (EURUSD M5, bars 6060-9999, `2026-08-18`..`2026-09-04`) and HYP_002 (EURUSD H4, bars
  3751-6230, `2023-05-29`..`2024-12-31`) windows are permanently quarantined and are NOT used here.
- F-1 is a different universe (US equity index) and mechanism (forced rebalancing) vs the terminally
  falsified unconditional FX momentum hypotheses. This is a family-level independence claim, NOT a
  validity claim.
- No HYP_001/HYP_002 evidence, optimized parameters, or sealed artifacts are, or will be, inherited.
- Prior-failure knowledge (e.g., cost discipline, grid rigidity) informs only the design style -
  never new-hypothesis evidence (epistemic contamination is acceptable and documented, not
  code-eliminable).

## What Must Be Frozen Before R1

For this candidate to become a pre-registrable hypothesis WITHOUT HARKing, exactly these choices must
be frozen at registration time (each currently PROPOSED / NOT YET SEALED):

1. Event family: reconstitution/rebalance effective-date events (one family only).
2. Universe, size-band filter, min-ADV threshold.
3. Horizons {1,5,10} business days and the primary horizon.
4. Direction: SHORT on the composite flow-pressure indicator.
5. Invalidation thresholds (rank IC >= 0.025, HAC t >= 2.00, cost ratio >= 1.50, autocorr <= 0.98).
6. Cost model parameters + deletion borrow assumption.
7. Fresh independent dataset window declared blind.
8. Full parameter grid (Cartesian) with `planned_trial_count == grid_cardinality`.
9. Hypothesis ID minted ONLY through the formal pre-registration path (ordinal `HYP_003` - never by
   this review).

## Conclusion / Readiness Assessment

**STRUCTURALLY PRE-REGISTRABLE (provisional):** the calendar-forced-flow mechanism maps cleanly onto
the canonical feature->forward-return pre-registration pipeline (deterministic event feature,
`ExpectedDirection.SHORT`, closed-form thresholds, canonical cost model, anti-HARKing cardinality).
No new infrastructure slice and no governance change are required.

**Condition:** the 9 free choices above must be frozen at R1. Until a human approves both this
candidate AND the frozen specification, no gate invocation occurs.

**Epistemic classification:** mechanism = REPORTED (established literature regularity) / INFERRED
(family research direction); every empirical claim in this review = **NOT PROVEN** (no ACASH evidence
exists; data not accessed; profitability, predictive power, and persistence are unestablished).

---

## VALIDATION SUMMARY

- HYP_003 exists: **NO** ; Gate invoked: **NO** ; R1 started: **NO** ; Hypothesis sealed: **NO**
- Market data accessed: **NO** ; Broker/MT5: **NO** ; Backtest/statistical test/optimization: **NONE**
- Slice 1-4 / governance / frozen core / ExecutionCoordinator: **UNCHANGED**
- Files changed by this review: **ONE** (this document) ; Commit: **NONE (awaiting instruction)**
- Capital: `$0.00` ; Trading: **LOCKED**
- All numerics: **PROPOSED / NOT YET SEALED**