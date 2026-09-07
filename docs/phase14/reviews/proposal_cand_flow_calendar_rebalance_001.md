# PHASE14 F-1 PRE-REGISTRATION PROPOSAL DRAFT

**Document ID:** `docs/phase14/reviews/proposal_cand_flow_calendar_rebalance_001.md`
**Object:** Candidate `CAND-FLOW-CALENDAR-REBALANCE-001` (Structural / Forced Flow)
**Type:** DRAFT formal pre-registration proposal - documentation artifact only
**Status:** NOT REGISTERED, NOT SEALED, NOT SUBMITTED to any gate
**Date:** 2026-09-07
**Companion review:** `./review_cand_flow_calendar_rebalance_001.md` (NOT overwritten)
**Authority:** `../AGENTS.md`, `./research_doctrine.md`, `./research_candidates.md`,
`docs/proposals/phase_4_alpha_engine.md`, `../src/acash/research/reinception.py`,
`../src/acash/research/schema.py`

> [!CAUTION]
> ### HARD GOVERNANCE & SAFETY INVARIANTS
> - **THIS DOCUMENT CREATES NO HYPOTHESIS. HYP_003 REMAINS ABSENT.**
> - **GATE NOT INVOKED.** `ResearchReInceptionGate` is NOT called. R1 NOT started. Nothing sealed.
> - **NO DATA / NO EXPERIMENT:** zero market data access, download, generation; zero backtests,
>   statistical tests, parameter optimization, or OOS inspection.
> - **NO IMPLEMENTATION:** Slice 1-4, frozen core, governance gates, ExecutionCoordinator unchanged.
> - **CAPITAL & TRADING HARD-LOCKED:** Capital = **$0.00**; Trading = **LOCKED**.
> - **NO EMPIRICAL CLAIM IS ESTABLISHED BY THIS DOCUMENT.**
>
> Classification legend: **V**=VERIFIED (canonical source)  |  **R**=REPORTED  |  **I**=INFERRED  | 
> **P**=PROPOSED (candidate-level proposal)  |  **NP**=NOT PROVEN  |  **HF**=REQUIRES HUMAN FREEZE.

---

## 1. Candidate identity

- Provisional Candidate ID: `CAND-FLOW-CALENDAR-REBALANCE-001` - NOT HYP_003. [I]
- Family: Structural / Forced-Flow (calendar-forced rebalancing) per `./research_candidates.md` F-1. [I]
- This draft is the first-principles specification of the candidate; the formal hypothesis ID for any
  future R1 would be minted ONLY through the canonical pre-registration path, never by this
  document. [V]

## 2. Research question

"For scheduled US equity-index reconstitution/rebalance events, do additions and deletions exhibit a
temporary price dislocation that (i) shows a reversal pattern over the following 1-10 business days
and (ii) yields a post-cost net edge that is economically meaningful?" [I/P]

- The question is a hypothesis to be tested, not a finding. Reversal/dislocation existence is
  **NP** until ACASH evidence validates it. [NP]

## 3. Mechanism / causal chain

Passive index funds and ETFs must transact on constituent add/delete at a published effective date to
minimize tracking error; the binding constraint is a timestamp, not a price. Timestamp-constrained,
price-insensitive demand (additions) and supply (deletions) cluster near the effective close, creating
temporary dislocation that partially reverses once the forced flow clears, bounded by shorting
frictions. [I/R; mechanism is a research hypothesis, not established alpha]

- Report as causal hypothesis; do not state as demonstrated dislocation/reversal. [NP]

## 4. Null hypothesis (H0)

The pre-registered flow-pressure indicator has no economically meaningful net-of-cost predictive
relationship with forward returns in the declared in-sample window; post-cost cumulative reversal
<= 0. Operationally: in-sample rank IC / HAC t below pre-registered bounds, or cost-adjusted spread
ratio below the pre-registered threshold. [P]

## 5. Alternative hypothesis (H1)

Forced-flow dislocation partially reverses: the pre-registered indicator negatively predicts forward
returns (fade the dislocation), with net-of-cost edge > 0 meeting pre-registered thresholds. [P]

## 6. Expected direction

**SHORT** on the composite flow-pressure indicator (defined in section 10). [P - PROPOSED / NOT YET
SEALED; pre-registered sign, no sign flipping post-hoc]

## 7. Instrument / universe definition

- Universe: US equity index constituents; PROPOSED large/mid-cap index membership, with a frozen
  min-ADV / min free-float filter; micro-caps excluded. [P/HF]
- No instrument/window overlapping the EURUSD quarantined windows (see section 23). [V]
- Exact index spin, size-band filter, and min-ADV threshold: **HF** (must be frozen before R1). [HF]

## 8. Event-family definition

- One event family only. PROPOSED primary: published index reconstitution / quarterly rebalance
  **effective dates** where the constituent change is officially announced in advance and a mandated
  effective close constrains flow. [P]
- Reconstitution and month-end/window-close flows are DISTINCT families and MUST remain separate;
  neither merging nor post-hoc splitting is permitted. [P/HF]

## 9. Event inclusion / exclusion rules

- Include: constituents added/deleted per the official as-announced list for the frozen universe, on
  the published effective date. [P]
- Exclude: (a) mid-stream special rebalances (unless the frozen family explicitly includes them),
  (b) names with corporate actions/earnings coinciding with the effective close (pre-registered
  coincidence rule), (c) names below the liquidity floor. [P/HF]
- The exclusion rule set is part of the frozen grid; no exclusion pattern discovered after data
  inspection may be added. [P]

## 10. Feature definition

Composite flow-pressure indicator (primary, deterministic, pre-announceable):

```text
+1 = addition at effective date
-1 = deletion at effective date
 0 = otherwise
```

- Canonical `feature_dependencies` (design-level) would include the composite indicator plus a
  close-price series; exact canonical names frozen at R1. [P]
- Secondary observables (abnormal volume, dollar-flow, index-relative pre-event return) are for
  mechanism confirmation only, NOT for candidate selection. [P]
- The composite indicator encoding above is PROPOSED / NOT YET SEALED. [P]

## 11. Forward-return definition

Discrete close-to-close return of the constituent from the effective-date reference price (official
close/auction print) to close at horizon h, over h in {1, 5, 10} business days. Denominator and
reference-print selection are part of the frozen definition. [P]

## 12. Candidate horizons

- Expected holding horizon: business days. Candidate set **{1, 5, 10}**. Primary horizon: 5
  (PROPOSED). [P/HF]
- No horizon switching after inspection. [P]

## 13. Cost model

- Reuse canonical `CostModelConfig` (quoted_spread_bps, roundtrip_broker_fee_bps, fixed_slippage_bps,
  latency_delay_ms) - V (schema exists). Values for F-1 at-event equity execution:
  PROPOSED spread ~1-2 bps, fee ~1.0 bps, slippage/impact ~5-20 bps. [P]
- Sensitivity runs at 1x / 2x / 5x cost multiples are pre-registered. [P]
- Exact bps values: **HF** (frozen at R1). [HF]

## 14. Borrow / shorting assumptions

- The deletion leg requires a short position; a pre-registered locate/borrow cost assumption must be
  included (PROPOSED as an explicit bps-per-day or flat fee line). [P]
- Names projected as Hard-to-Borrow on the published date are handled by the pre-registered
  exclusion rule; borrow assumption values: **HF**. [HF]

## 15. Economic significance threshold

- Net-of-cost cumulative reversal must exceed a pre-registered economically meaningful level
  (PROPOSED: positive after the full cost stack; exact bps bar set at freeze). [P/HF]
- Economic significance is a statement about the frozen threshold, NOT about any observed value. [NP]

## 16. Statistical thresholds

- Recommended F-1 R1 criteria (PROPOSED / NOT YET SEALED): rank IC >= 0.025; HAC t >= 2.00; cost
  ratio >= 1.50; autocorrelation <= 0.98. [P]
- Canonical gate FLOORS (distinct from the F-1 proposal): gate enforces in-sample rank IC strictly
  positive and HAC t >= 1.50 in `ResearchInceptionProposal` validation (`reinception.py`). The
  proposed >= 0.025 / >= 2.00 are STRICTER candidate-level criteria and must not be conflated with
  the gate floor. [V - gate floor]
- A proposal may choose stronger criteria; the gate floor is a minimum, not a recommendation. [V]

## 17. Autocorrelation / dependence treatment

- Overlapping forward labels are permitted but NOT treated as independent; serial dependence is
  handled by the configured HAC procedure (canonical, `phase_4_alpha_engine.md` 4.3 / `HAC`
  `FIXED_HORIZON_MINUS_ONE` default). [V]
- Cross-sectional same-date clustering (all names moving on the same effective date) MUST be
  addressed: cluster inference by event date is pre-registered (event-cluster handling). [P/HF]
- max_feature_autocorrelation <= 0.98 proposed bound applies to the indicator series. [P]

## 18. Effective sample-size requirement

- Canonical rule: `N_valid >= 250 valid observations per evaluation window`; overlapping forward
  labels permitted and not treated as independent (`phase_4_alpha_engine.md` 4.3.4). [V]
- F-1 reconstitution events are sparse (~1/year). Direct application of the >= 250 rule is
  ambiguous for event-count-based inference:
  - minimum **effective event count** (distinct events) and
  - definition of `T_eff` (independent-equivalent observations, clustered by event date)
  are NOT deterministically derivable from existing canonical sources for an event-sparse design.
  [NP]
- Therefore the sample-size methodology for F-1, including any human governance override of the
  N >= 250 requirement or an event-count alternative, is **HF**. R1 must NOT resolve this by
  selecting a method after seeing data. [HF]

## 19. Trial-grid definition

- Complete pre-registered grid = Cartesian product of the frozen dimensions (event family, universe
  filter, horizons, cost stack, borrow assumption, thresholds as applicable) declared at R1. [P]
- **Invariant preserved:** `planned_trial_count == grid_cardinality` (canonical anti-HARKing gate
  invariant). [V]
- No post-hoc trial additions, threshold changes, or horizon switches. [P]

## 20. Anti-HARKing rule

- Zero parameter search, zero "best threshold" selection, zero in-sample tuning, zero inspection of
  held-out/OOS performance before R1 sealing. [P]
- `planned_trial_count == grid_cardinality` strictly enforced at the gate. [V]
- Nothing in this document was optimized against data (no data accessed). [V]

## 21. Missing-data rules

- Pre-registered handling for missing bars/prints on the effective date (e.g., suspended names,
  early-close days): freeze a single deterministic policy at R1; no imputation invented later. [P/HF]

## 22. Corporate-action / survivorship handling

- Price series must be corporate-action-adjusted (adj close) with a pre-registered survivorship/no
  look-ahead policy; names added/deleted historically must be represented as-of the announcement,
  not reweighted with hindsight. [P/HF]
- Survivor-bias treatment: the constituent list must be point-in-time (as-announced), not
  end-of-sample survivor lists. [P]

## 23. Quarantine / contamination boundary

- HYP_001 (EURUSD M5, bars 6060-9999, `2026-08-18`..`2026-09-04`) and HYP_002 (EURUSD H4, bars
  3751-6230, `2023-05-29`..`2024-12-31`) are permanently quarantined; no reuse. [V]
- F-1 universe is US equity index: disjoint from EURUSD by construction; must remain disjoint for any
  future instrument choice. [P]
- No HYP_001/HYP_002 evidence, optimized parameters, or sealed artifacts may be inherited. [V]
- Prior-failure knowledge informs design style only, never new-hypothesis evidence (documented
  limitation; pristine data != pristine human knowledge). [I]

## 24. Fresh blind-window requirement

- The dataset window MUST be declared de novo and blind (uninspected for returns) at R1, disjoint
  from all quarantined windows, before any return inspection. [P]
- Exact window selection and data acquisition are outside this document and require
  authorization. [HF/NP]

## 25. R1 sealing requirements

- At R1: full `ResearchInceptionProposal` (economic_rationale >= 20 chars [V], non-empty
  `feature_dependencies` [V], non-empty horizons with primary in set [V], strictly positive
  in-sample rank IC floor [V], HAC t >= 1.50 [V], `planned_trial_count == grid_cardinality` [V]).
- Sealing at R1 makes the spec immutable; `validate_hypothesis_immutability` binds the digest.

## 26. Deterministic reproducibility requirements

- Canonical serialization (sorted keys, fixed separators) for the proposal and grid; SHA-256 binding
  of the sealed spec; no timestamps in the canonical identity besides registration metadata. [V]
- Deterministic feature encoding and event calendar parsing pre-registered at R1. [P]

## 27. Evidence classification

| Statement | Class |
|---|---|
| F-1 is a research candidate, not a hypothesis | V |
| Forced-flow index rebalancing mechanism | R/I |
| Dislocation/reversal exists (any magnitude) | NP |
| F-1 horizons {1,5,10}, direction SHORT, indicator +1/-1/0 | P (PROPOSED / NOT YET SEALED) |
| rank IC >= 0.025 / HAC t >= 2.00 / autocorr <= 0.98 / cost ratio >= 1.50 for F-1 | P (canonical-style values, PROPOSED for F-1) |
| Gate floor rank IC > 0, HAC t >= 1.50 | V (canonical) |
| N >= 250 valid-observations rule | V (canonical); applicability to sparse events: NP/HF |
| F-1 empirical alpha / predictive power / persistence | NP |

## 28. Explicit unresolved decisions requiring human freeze

The following MUST be explicitly frozen by the human before any `ResearchReInceptionGate`
invocation. None is chosen here:

1. **Event family** - reconstitution vs. quarterly rebalance vs. separable month-end; one family only.
2. **Universe / filters** - index spin, size band, min-ADV / free-float floor.
3. **Horizons** - final set {1, 5, 10} or alternative; primary horizon.
4. **Direction** - SHORT on the composite indicator (sign frozen).
5. **Threshold set** - exact rank IC, HAC t, autocorrelation, cost-ratio values for F-1 R1.
6. **Cost + borrow model** - exact bps stack and locate/borrow assumption.
7. **Fresh blind window** - de novo dataset window declared before any returns inspection.
8. **Complete trial grid** - full Cartesian product matching `planned_trial_count == grid_cardinality`.
9. **Formal hypothesis ID minting path** - ordinal HYP_003 minted only through the formal
   pre-registration path; never by this document.

---

## No empirical claim is established by this document.

## VALIDATION SUMMARY

- HYP_003 exists: **NO**  |  Gate invoked: **NO**  |  R1 started: **NO**  |  Hypothesis sealed: **NO**
- Market data accessed: **NO**  |  Broker/MT5: **NO**  |  Backtest / statistical test / optimization:
  **NONE**
- Slice 1-4 / governance / frozen core / ExecutionCoordinator: **UNCHANGED**
- Existing review `review_cand_flow_calendar_rebalance_001.md`: **UNTOUCHED**
- Files changed by this task: **ONE** (this proposal draft)  |  Commit: **NONE**
- Capital: `$0.00`  |  Trading: **LOCKED**
- ASCII / byte hygiene: non-ASCII code points = **NONE** (pure ASCII and decimal-escaped sequences)
- All research claims: **PROPOSED / NOT PROVEN / REQUIRES HUMAN FREEZE** as classified above.