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
- Exact index spin, size-band filter: **HF** (must be frozen before R1). min-ADV threshold:
  **RESOLVED** (Item 1/17, 2026-09-07: US$5,000,000/day). Free-float floor: **RESOLVED**
  (Item 2/17, 2026-09-07: FREE-FLOAT >= 20%, latest PIT/as-announced free-float known by the
  reconstitution effective date, no look-ahead; fixed eligibility rule; NOT a trial-grid
  dimension).

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

Simple close-to-close return of the constituent from the official closing price on the published
reconstitution effective date to the official closing price on the h-th valid trading session after
the effective date, over h in {1, 5, 10} business days:

    R(h) = Close(T0+h) / Close(T0) - 1

- T0 = the published reconstitution effective date. [HF — resolved Item 3/17]
- Reference print = **official closing price on T0** (no next-day open; no arbitrary intraday
  print; no auction print as a separate methodology; no post-hoc selected print). [HF — resolved
  Item 3/17]
- Denominator = `Close(T0)`; endpoint = official closing price on the h-th valid trading session
  after T0; h in {1, 5, 10} as already defined (6A). [HF — resolved Item 3/17]
- Session validity: an early-close session with a valid official closing print IS a valid trading
  session; if no valid official close exists, the observation is invalid/excluded (Items 3/6).
- Event-day return kept separate — monitoring/diagnostic only, NOT the h=1/5/10 forward-return
  observation (4C).
- Simple returns only; do NOT switch to log returns.

[HF — resolved Item 3/17, 2026-09-07; return-convention freeze, NOT `[V]` / NOT empirical]

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
  exclusion rule. **HTB measurement-date rule (published-date / PIT), unavailable-information
  exclusion, and the single deterministic shortability-eligibility rule are HUMAN-FROZEN (Item
  9/17, 2026-09-07)** — see §27F. HTB source / version / field remain unresolved. Borrow
  assumption values remain **HF**. [HF — partially resolved Item 9]

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
  addressed: cluster-robust inference by effective event date is **HUMAN-FROZEN (Item 8/17,
  2026-09-07)** — cluster unit = effective event date, canonical HAC `FIXED_HORIZON_MINUS_ONE`
  (no override), inference effective sample = `T_eff` (see §27D). [HF — resolved; NOT `[V]`]
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
- The sample-size methodology for F-1 is **HUMAN-FROZEN** (Item 7/17, 2026-09-07; see §27C).
  Inference effective sample = `T_eff` (Item 8/17, 2026-09-07) with cluster unit = effective
  event date and canonical HAC `FIXED_HORIZON_MINUS_ONE` (see §27D). The canonical
  `N_valid >= 250` rule remains **ACTIVE** with **NO override**. R1 must NOT alter the frozen
  methodology after seeing data. [HF — resolved by Items 7/8 freezes]

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

- Handling for missing bars/prints on the effective date (e.g., suspended names, early-close days)
  is **HUMAN-FROZEN (Item 6/17, 2026-09-07)**: a missing / stale / unavailable required official
  closing observation makes the constituent observation invalid and excluded from the date×leg
  composite; no imputation, no zero-fill, no neutral return, no carry-forward, no synthetic
  observation; early close follows Item 3 session validity; name-level missingness does not
  redefine market-level session validity; deterministic calendar handling per 4DA. [HF — resolved
  Item 6; NOT `[V]`]

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

## 27B. Governance Lock — Revision Date & Authority

**Revision status:** READ-ONLY REVISION applied to the F-1 draft per audit output
(`F-1 GOVERNANCE AUDIT`, Recommendation B). This revision **only documents unresolved
governance gaps** for subsequent HUMAN FREEZE. It does **NOT** select, seal, or freeze any
methodological value. No hypothesis is created. HYP_003 remains absent.

**Canonical sources re-read for this revision (read-only):**
- `src/acash/research/reinception.py` — gate floors, cardinality, quarantine (unchanged)
- `src/acash/research/schema.py` — `CostModelConfig`, `InvalidationCriteria` (unchanged)
- `src/acash/research/quarantine.py` — quarantine enforcement (unchanged)
- `docs/phase14/research_candidates.md` — F-1 registry (unchanged)
- `docs/phase14/phase14_human_approval_readiness_review.md` — Phase 14 non-ownership (unchanged)
- `docs/phase14/reviews/review_cand_flow_calendar_rebalance_001.md` — prior review (unchanged)

**No canonical implementation code was modified by this revision.**

---

## 27C. Effective-Sample Authority (Item 7 — HUMAN-FROZEN 2026-09-07)

F-1 is **event-sparse** (~1/year) and its constituent observations are **same-date clustered**
(all added/deleted names move on the same published effective date). [V — structural fact]

The canonical gate (`reinception.py`) does **NOT** itself provide a deterministic event-count /
`T_eff` methodology for this design. The canonical `N_valid >= 250` rule
(`phase_4_alpha_engine.md` §4.3.4) is a valid-observation rule and **MUST NOT be silently
reinterpreted as an event-count rule**. [V]

The `T_eff >= 25 per composite leg` numeric threshold AND the exact deterministic methodology
below are **HUMAN-FROZEN** (Item 7/17, 2026-09-07) from explicit human decisions
(Q7.1–Q7.10). This is a **deterministic methodological freeze only** — it is **NOT** an
empirical/canonical validation claim (NOT `[V]`), is **NOT** attributed to observed data or
backtest performance, and **no data has been inspected**. [HF — resolved by human freeze]

**Composite leg** = one direction side of the event-level composite flow (additions `+1` /
deletions `−1`, per 3BA/3CA; cf. the deletion leg of §14); `T_eff` is evaluated per composite
leg.

Frozen Item 7 decisions (recorded verbatim):

- **Q7.1 / Status:** `T_eff >= 25 per composite leg` per in-sample evaluation window =
  **HUMAN-FROZEN** numeric threshold; the exact methodology below is likewise HUMAN-FROZEN.
  Neither is an empirical `[V]` claim.
- **Q7.2 / Observation unit:** ONE effective event date × ONE composite leg = ONE `T_eff`
  observation. Constituent-level observations remain preserved inside the event-date cluster
  for audit and for inference/clustering purposes.
- **Q7.3 / Same-date multiplicity:** Multiple qualifying constituents on the same effective
  event date produce ONE composite observation for that event date × composite leg; they are
  **NOT** counted individually toward `T_eff`. Constituent-level observations remain preserved
  within the event-date cluster.
- **Q7.4 / Return aggregation:** `CompositeReturn(event_date, leg)` = **arithmetic mean
  (equal weighting)** of all eligible constituent-level returns that are valid for that event
  date and leg. No market-cap / free-float / liquidity / magnitude weighting or any other
  weighting scheme. Deterministic aggregation rule; **not a trial-grid dimension**. Consistent
  with Decision 3 ("no magnitude weighting unless separately frozen", [HF]): an equal-weight
  arithmetic mean gives every constituent equal weight, so it is not magnitude weighting.
- **Q7.5 / Valid composite observation:** an event date × composite-leg composite is VALID iff:
  1. the constituent is eligible under all previously frozen eligibility rules;
  2. the constituent has a valid return under the frozen Item 3 price/return convention;
  3. the constituent return is not missing, suspended, stale, or otherwise invalid under the
     frozen deterministic missing-data rules;
  4. after applying the no-imputation rule, at least ONE eligible valid constituent return
     remains for that event date × leg;
  5. the arithmetic mean is therefore deterministically computable.
  No minimum constituent-count threshold beyond this; no coverage percentage.
- **Q7.6 / One valid constituent:** exactly ONE eligible valid constituent return → the
  event-date composite is VALID and counts as ONE `T_eff` observation (not zero, not discarded).
- **Q7.7 / Missing constituents:** NO IMPUTATION. Missing / suspended-without-valid-return /
  missing-print / unavailable / stale-failing-validity constituent return → constituent is
  EXCLUDED from that event-date × leg composite. No zero-fill, no neutral contribution, no
  carry-forward, no synthetic return. If zero eligible valid constituents remain after
  exclusion, the event-date × leg composite is INVALID and does NOT count toward `T_eff`.
  **Early-close sessions:** no special exclusion is invented here; early-close follows the frozen
  valid-session / Item 3 convention (Item 3 session semantics now HUMAN-FROZEN in Item 3/17).
- **Q7.8 / `N_valid >= 250`:** canonical `N_valid >= 250` remains **ACTIVE**; there is **NO
  override**; `T_eff` does **NOT** replace `N_valid`; `N_valid >= 250` is **NOT** reinterpreted
  as an event-count rule. `N_valid` = canonical valid-observation rule; `T_eff` = effective
  event-date × composite-leg sample measure.
- **Q7.9 / Exact formula:** `T_eff(leg)` = number of **DISTINCT effective event dates** for
  which a VALID event-date × composite-leg composite return exists. Each effective event date
  contributes at most ONE observation per composite leg; it contributes ONE iff at least one
  eligible valid constituent return exists, the valid returns are aggregated by the frozen
  arithmetic-mean rule, and the resulting composite is valid; otherwise ZERO. Constituents are
  never counted separately; no multiple observations from the same effective date.
- **Q7.10 / Heuristic:** because Q7.9 is an exact deterministic formula (no approximation), no
  named approximation heuristic is required under AGR Rule 6 and **no heuristic name is
  fabricated**. [HF — resolved]

**[HF — resolved]** — Human decisions recorded verbatim; classifications preserved; no empirical
claim is established by this document.

---

## 27D. Same-Date Cluster Inference (RESOLVED — Item 8/17 2026-09-07)

Same-date constituent observations are **cross-sectionally correlated** by construction
(all names on the same effective date share the index event). [V — structural fact]

The cluster inference policy is **HUMAN-FROZEN** (Item 8/17, 2026-09-07):
- **cluster-robust inference** with **cluster unit = effective event date** (aligned with the
  frozen `T_eff` observation unit);
- canonical HAC specification **`FIXED_HORIZON_MINUS_ONE`** (canonical documented default, **no
  override**);
- **inference effective sample = `T_eff`** (Item 7 frozen definition, used exactly);
- standard-error procedure = the canonical cluster/HAC inference procedure consistent with the
  framework's fixed-horizon HAC rule; **no new/unsupported estimator name**.

**[HF — resolved Item 8/17]** — Human freeze; deterministic policy; NOT `[V]`, NOT empirical.

---

## 27E. Borrow / Shorting Cost — Canonical Schema Gap (HUMAN FREEZE REQUIRED)

`src/acash/research/schema.py::CostModelConfig` currently does **NOT** contain a dedicated
borrow-cost field. [V]

This revision does **NOT** modify `schema.py` and does **NOT** invent a new canonical field.
[V — constraint]

The canonical representation of borrow/locate cost is an **unresolved governance decision**.
Possible representations are documented **only as unresolved alternatives** — none is selected:

- **A.** Fold borrow into the existing conservative cost representation;
- **B.** Introduce borrow as an explicit parameter-grid dimension through a separately approved
  schema / governance change;
- **C.** Another explicitly human-approved frozen convention.

Explicit statements (canonical-governance constraints): [V]
- whichever convention is chosen **affects the final trial grid** if it becomes a parameter dimension;
- the final choice must be **frozen before Gate**;
- **no post-hoc borrow assumption** is permitted.

**[P/HF]** — A human approves the borrow/locate canonical representation. Not decided here.

---

## 27F. Hard-to-Borrow (HTB) Exclusion (PARTIALLY RESOLVED — Item 9/17 2026-09-07)

HTB exclusion decisions **HUMAN-FROZEN** (Item 9/17, 2026-09-07): [HF — resolved]
- **measurement date:** published-date / PIT HTB information available at the frozen measurement
  date (no future information);
- **unavailable-information handling:** unavailable HTB information → the security is excluded
  from the shortable sample;
- **deterministic exclusion rule:** ONE shortability-eligibility rule combining the frozen
  measurement-date rule, the future-information prohibition, and the unavailable-information
  exclusion.

**MUST REMAIN UNRESOLVED (`HF / REQUIRED` / `NOT YET SPECIFIED`):**
- HTB **source** (no vendor authorized);
- HTB **source version**;
- HTB **data field**.

**[HF / REQUIRED] — Do NOT invent a vendor / version / field. Source/version binding remains a
separate later data-source decision.**

---

## 27G. Survivorship / Corporate-Action Conventions (RESOLVED — Item 5/17 2026-09-07)

Corporate-action / continuity conventions are **HUMAN-FROZEN** (Item 5/17, 2026-09-07): [HF]
- **delisting:** no synthetic delisting return; if the security cannot provide a valid forward
  price observation required by the frozen return definition, the return observation is
  unavailable and excluded from the composite;
- **merger / acquisition:** deterministic point-in-time corporate-action treatment from the
  canonical CA source once that source is bound; if an unambiguous valid return cannot be
  constructed under that treatment, exclude; do NOT make post-hoc successor mappings based on
  observed returns;
- **ticker changes:** ticker is NOT the security identity; use the stable security identifier
  supplied by the canonical dataset; a ticker change alone does not break continuity;
- **index rename / rebrand:** naming/rebranding alone does not break constituent/security
  identity continuity;
- **CA effective-date ordering:** use the effective date/time supplied by the canonical PIT CA
  source and the deterministic ordering rule; preserve the §9(b) coincidence/exclusion rule; do
  NOT introduce post-hoc date ordering;
- **adjusted close:** PIT adjusted-close information with no look-ahead, per the canonical price
  source's deterministic methodology;
- **historical list versioning:** PIT / as-announced constituent snapshots; NO end-of-sample
  survivor list; no look-ahead.

**Exact CA source / version binding remains a separate unresolved item (`HF / REQUIRED`) —
NOT authorized here, NOT a vendor selection.** No vendor is chosen by this document.

---

## 27H. Missing / Suspended Data (RESOLVED — Item 6/17 2026-09-07)

Missing / suspension handling is **HUMAN-FROZEN** (Item 6/17, 2026-09-07): [HF]
- **suspension:** a suspended security without a valid required closing observation is invalid
  and excluded from the date×leg composite;
- **missing print:** absent/unavailable required price print → the observation is invalid and
  excluded;
- **missing OHLC component:** a valid official closing price is required for the relevant
  reference/endpoint observation; if that required close is unavailable → invalid and excluded;
  no imputation;
- **early close:** follows Item 3 exactly (early-close session with a valid official closing
  print IS a valid session; otherwise the observation is invalid/excluded);
- **stale:** NO arbitrary numeric stale threshold; staleness determined by canonical
  price-source/session semantics once the source is bound; a stale observation failing the valid
  current-session closing requirement is invalid/excluded;
- **unavailable return / source outage:** if the required return cannot be deterministically
  constructed from the frozen price/session rules, or the canonical source is unavailable and the
  required observation cannot be obtained, classify it as unavailable and exclude it; do NOT
  silently substitute a different source after observing results;
- **no imputation:** zero valid constituents → composite INVALID, NOT counted toward `T_eff`
  (Item 7 preserved); no zero-fill, no neutral return, no carry-forward, no synthetic
  observation; no composite value is fabricated for a date×leg with no valid constituent;
- **next-tradable interaction:** name-level missingness does NOT redefine market-level session
  validity; apply Item 3 session validity first, then security-level observation validity;
  deterministic calendar handling per 4DA.

---

## 27I. Trial-Grid Accounting (Anti-HARKing — remains mandatory)

`planned_trial_count == grid_cardinality` is **mandatory**. [V]

However, the **final cardinality cannot be sealed until all parameter dimensions are
human-frozen**. Borrow is included as a grid dimension **only if** the human-approved borrow
convention makes it a parameter dimension (see §27E). No post-hoc additions, removals, merging,
splitting, or selective reporting of grid cells. [P/HF]

**No final cardinality is claimed here** because unresolved dimensions remain. [NP]

---

## 27J. Economic-Significance Alignment (HUMAN FREEZE REQUIRED)

The proposal contains two related but **distinct** metrics unless canonical governance specifies
otherwise: [P]
- **cumulative reversal** (must have a stated horizon/window and a pre-registered interpretation);
- **cost-adjusted spread ratio** (subject to its own frozen threshold).

**[P/HF]** — Final threshold / horizon for each metric is NOT chosen here if not already
human-frozen.

---

## 27K. HUMAN-FROZEN DECISIONS (Recorded — user-selected recommendations)

> **Authority:** The human has explicitly selected the recommendations below (via
> "all recommendations"). This section **RECORDS** the human's decisions. It does
> **NOT** invent, optimize, infer, or substitute values, and does NOT add any value not
> explicitly specified below.
>
> Legend: **HF** = Human Freeze Required (unresolved numeric/operational value) | **V** =
> canonical | **P** = proposed | **NP** = not proven.

### Decision 1 — Event Family
- **Reconstitution.** [HF — event family frozen at rule level]
- Reconstitution events only; no post-hoc merging/splitting with other families.

### Decision 2 — Universe Framework
- **Broad US Equity Index + Minimal Pre-specified Filters.** [HF]
- **2A. Index Family:** S&P Composite 1500; S&P 500; S&P MidCap 400; S&P SmallCap 600. [HF]
- **2B. Size Policy:** No explicit size exclusion; retain eligible sizes within the selected
  index family; tradability controlled through pre-specified liquidity/free-float safeguards.
  [HF]
- **2C. Liquidity Filter:** Fixed-dollar minimum ADV filter. **HUMAN-FROZEN (Item 1/17,
  2026-09-07): US$5,000,000 per day** — fixed pre-specified threshold; NOT a trial-grid
  dimension; no percentile/rank-based replacement; no post-hoc threshold adjustment; no
  additional ADV thresholds. [HF — value recorded from explicit human decision; NOT attributed
  to prior empirical evidence; NOT claimed optimal or validated]
- **2D. ADV Lookback:** 60 trading days, using only information available before the event.
  [HF — human-frozen]
- **2E. Free-Float Filter:** Fixed minimum free-float floor = **FREE-FLOAT >= 20%** — **HUMAN-
  FROZEN (Item 2/17, 2026-09-07)**: measured using the latest PIT/as-announced free-float
  information known by the reconstitution effective date; no look-ahead; later revised
  information must NOT be used to determine historical eligibility. Fixed eligibility rule;
  **NOT a trial-grid dimension**; no additional free-float thresholds. [HF — value recorded from
  explicit human decision; NOT empirical/`[V]`; NOT claimed optimal or validated]
- **2F. Multiple / Overlapping Events:** Keep distinct qualifying events; do not double-count
  the same event; no post-hoc event selection. [HF — frozen at rule level]
- **2G. Multiple Records Within One Event:** Aggregate records by event identity + effective
  date; preserve constituent-level observations within the event cluster; do not duplicate the
  same event. [HF]

### Decision 3 — Signal
- Addition = `+1`; Deletion = `-1`; Otherwise = `0`. [HF]
- Composite flow is constructed at the **event level**. [HF]
- Do not introduce magnitude weighting unless separately frozen. [HF]

### Decision 4 — Timing & Return
- **4A. Event Anchor:** Effective date. [HF]
- **4B. Forward Return Start:** Next tradable observation after the effective event. **EXACT
  return convention is HUMAN-FROZEN (Item 3/17, 2026-09-07):** `R(h) = Close(T0+h) /
  Close(T0) - 1`; reference print = official closing price on T0 (no next-day open, no auction-
  as-separate-methodology, no post-hoc selected print); endpoint = official closing price on the
  h-th valid trading session after T0, h in {1, 5, 10}; simple-return only. Source-specific
  terminology must preserve the methodological meaning of "official closing price"; source
  binding is a later data-source decision and must not alter the freeze. [HF — resolved Item
  3/17; NOT `[V]`]
- **4C. Event-Day Return:** Keep event-day return separate from the primary forward-reversal
  measurement. **Item 3/17 freeze:** treatment = monitoring/diagnostic information only; it is
  NOT the h=1/5/10 forward-return observation. [HF — resolved Item 3/17]
- **4D. Calendar / Early Close:** Use the next valid trading session according to a deterministic
  calendar; no manual date shifting. **Item 3/17 freeze:** an early-close session with a valid
  official closing print IS a valid trading session; if no valid official close exists, the
  observation is invalid/excluded. [HF — resolved Item 3/17]

### Decision 5 — Direction
- **SHORT.** [HF — sign frozen]

### Decision 6 — Horizons
- `{1, 5, 10}` business days; **Primary horizon = 5** business days. [HF]

### Decision 7 — Candidate Thresholds (preserved; distinct from gate floors)
- Rank IC >= 0.025; HAC t-stat >= 2.00; cost-adjusted spread ratio >= 1.50; autocorrelation
  <= 0.98. [P — candidate-level]
- **Canonical Gate floors (distinct):** Rank IC > 0; HAC t-stat >= 1.50. [V]
- Do NOT confuse the two.

### Decision 8 — Sample & Inference
- **8A. Observation Unit:** Constituent-event observations with event-date clustering. [HF]
- **8B. Effective Sample:** Event-level effective sample concept. [HF]
- **8C. Minimum Effective Events:** `T_eff >= 25 per composite leg` — **HUMAN-FROZEN** (Item
  7/17, 2026-09-07) together with the exact deterministic methodology (observation unit,
  aggregation, validity, missing treatment, exact formula — see §27C). [HF — resolved;
  deterministic methodology; NOT an empirical `[V]` claim]
- **8D. Same-Date Clustering:** Cluster by effective event date. **The estimator/inference
  implementation is HUMAN-FROZEN (Item 8/17, 2026-09-07):** cluster-robust inference with cluster
  unit = effective event date (aligned with the frozen `T_eff` observation unit); canonical HAC
  `FIXED_HORIZON_MINUS_ONE` (canonical default, **no override**); inference effective sample =
  `T_eff` (Item 7 definition used exactly); standard-error procedure = the canonical cluster/HAC
  inference procedure consistent with the fixed-horizon HAC rule; no new/unsupported estimator
  name. [HF — resolved Item 8/17; NOT `[V]`]

### Decision 9 — Cost Model
- **9A. Spread Cost:** Fixed pre-registered spread cost. **EXACT bps value NOT yet frozen** —
  mark `HF / REQUIRED`; do NOT invent a number.
- **9B. Broker Fee:** Fixed pre-registered broker fee. **EXACT bps value NOT yet frozen** —
  mark `HF / REQUIRED`; do NOT invent a number.
- **9C. Slippage:** Pre-registered slippage grid. **EXACT grid values NOT yet frozen** — mark
  `HF / REQUIRED`; do NOT invent values. Once frozen, every value must be included in the trial
  grid.

### Decision 10 — Borrow / Locate Cost (human-selected)
- **Fold borrow/locate cost into the conservative fixed-slippage representation.** [HF]
- Do NOT modify `src/acash/research/schema.py`. Do NOT add a borrow parameter dimension.
- **The exact conservative borrow-cost assumption remains `HF / REQUIRED`** — do NOT invent the
  bps value.

### Decision 11 — HTB
- Deterministically exclude names that cannot satisfy the frozen shortability/HTB rule. [HF]
- **Measurement date:** **HUMAN-FROZEN (Item 9/17, 2026-09-07)** — published-date / PIT HTB
  information available at the frozen measurement date (no future information).
- **Unavailable-information handling:** **HUMAN-FROZEN (Item 9/17, 2026-09-07)** — unavailable
  HTB information → security excluded from the shortable sample.
- **Deterministic rule:** ONE shortability-eligibility rule combining the frozen measurement-date
  rule, the future-information prohibition, and the unavailable-information exclusion. [HF —
  resolved Item 9/17]
- **Exact HTB data source, source version, and data field remain `HF / REQUIRED` — NOT YET
  SPECIFIED.** Do NOT invent a vendor/version/field.

### Decision 12 — Survivorship / Corporate Actions
- Point-in-time / as-announced constituent methodology. Deterministic corporate-action
  treatment. [HF]
- **Operational conventions HUMAN-FROZEN (Item 5/17, 2026-09-07):** delisting → no synthetic
  delisting return (exclude when the required forward price cannot be observed); M&A →
  deterministic PIT CA treatment from the bound CA source, otherwise exclude (no post-hoc
  successor mappings from observed returns); ticker is NOT security identity (stable identifier);
  index rebrand does not break continuity; CA effective-date ordering = canonical PIT CA source
  effective date/time + the deterministic ordering rule, preserving §9(b); adjusted close = PIT
  with no look-ahead per the bound price source's methodology; list versioning = PIT /
  as-announced, NO survivor lists (see §27G).
- **Exact source/version remains `HF / REQUIRED`** — source binding is a separate later data-
  source decision. Do NOT invent a vendor.

### Decision 13 — Missing / Suspension
- **No imputation.** [HF]
- **Operational policy HUMAN-FROZEN (Item 6/17, 2026-09-07):** suspended (no valid required
  close) / missing print / missing required OHLC close / stale failing valid-session closing
  requirement / unavailable return / source outage → invalid and EXCLUDED from the date×leg
  composite; no imputation, no zero-fill, no neutral return, no carry-forward, no synthetic
  observation; early-close session validity follows Item 3 exactly; NO arbitrary numeric stale
  threshold (staleness per canonical price-source/session semantics once bound); name-level
  missingness does NOT redefine market-level session validity; deterministic calendar per 4DA.
  (see §27H) [HF — resolved Item 6/17; NOT `[V]`]

### Decision 14 — Fresh Blind Window
- Fresh post-freeze research window, disjoint from all quarantined windows, not inspected
  before sealing. [HF]
- **Exact dates are NOT yet frozen** — mark `HF / REQUIRED`; do NOT choose dates.

### Decision 15 — Trial Grid
- Full Cartesian product of all intentionally varied frozen parameter dimensions.
  `planned_trial_count == grid_cardinality` is mandatory. No post-hoc removal/addition/merging/
  splitting/selective reporting. [V]
- **Final cardinality is NOT yet frozen** because unresolved dimensions remain.

### Decision 16 — Economic Significance
- **Cost-adjusted spread ratio** is the primary economic criterion. **Cumulative reversal** is a
  secondary metric. [HF]
- Cumulative reversal must have an explicitly frozen horizon/window. **Do NOT invent the final
  cumulative-reversal window** — mark `HF / REQUIRED`.

### Decision 17 — Formal Hypothesis / Gate Path (no shortcut)
1. Final deterministic proposal;
2. Human Freeze (all unresolved items);
3. Formal pre-registration;
4. HYP_003;
5. ResearchReInceptionGate;
6. R1.
[V — governance ordering; no shortcut]

---

## 27L. UNRESOLVED HUMAN FREEZES (MUST STAY `HF / REQUIRED` — do NOT guess)

The following are **NOT human-frozen** and must remain explicitly marked `HF / REQUIRED`. They
were NOT invented, inferred, or optimized by this document:

1. Exact ADV dollar threshold; — **RESOLVED** (Item 1/17, 2026-09-07: US$5,000,000/day, pre-event 60-day ADV, human freeze)
2. Exact free-float threshold; — **RESOLVED** (Item 2/17, 2026-09-07: FREE-FLOAT >= 20%, latest
   PIT/as-announced free-float known by the reconstitution effective date, no look-ahead; fixed
   eligibility rule, NOT a trial-grid dimension)
3. Exact return OHLC convention (if not already canonical); — **RESOLVED** (Item 3/17,
   2026-09-07: `R(h) = Close(T0+h) / Close(T0) - 1`; reference = official closing price on T0;
   endpoint = official close on the h-th valid trading session after T0; simple returns; no
   next-day open)
4. Exact spread bps;
5. Exact broker-fee bps;
6. Exact slippage grid values;
7. Exact borrow-cost bps / conservative assumption;
8. Exact HTB source;
9. Exact HTB measurement date; — **RESOLVED** (Item 9/17, 2026-09-07: published-date / PIT HTB
   information available at the frozen measurement date; no future information)
10. Exact HTB unavailable-data rule; — **RESOLVED** (Item 9/17, 2026-09-07: unavailable HTB
    information → exclude from the shortable sample)
11. Exact `T_eff` mathematical definition; — **RESOLVED** (Item 7/17, 2026-09-07: `T_eff(leg)`
    = count of DISTINCT effective event dates with a valid composite observation per leg;
    numeric floor 25 per leg; see §27C)
12. Exact clustering estimator / inference implementation; — **RESOLVED** (Item 8/17, 2026-09-07:
    cluster-robust inference by effective event date; canonical HAC `FIXED_HORIZON_MINUS_ONE`
    (no override); inference sample = `T_eff`; see §27D)
13. Exact survivorship / corporate-action source/version;
14. Exact delisting / merger / ticker / CA handling (where not already canonical); — **RESOLVED**
    (Item 5/17, 2026-09-07; see §27G)
15. Exact missing / suspension policy; — **RESOLVED** (Item 6/17, 2026-09-07; see §27H)
16. Exact fresh blind-window dates;
17. Exact cumulative-reversal evaluation window.

---

## 27M. HUMAN-SELECTED F-1 DECISION SET (Recorded verbatim from human-authorized mapping)

> **Authority:** The human explicitly authorized the following 34-code decision set to be recorded.
> This section records those decisions EXACTLY. It does NOT search, redesign, optimize, infer, or
> add methodology. Values that are explicitly stated are recorded deterministically. Values that
> are required for operational execution but NOT specified below remain
> `HUMAN-FREEZE REQUIRED / UNRESOLVED` — never guessed.
>
> **Classification legend:** `V` = canonical/verified | `R` = reported | `I` = inferred |
> `P` = proposed | `NP` = not proven | `HF` = human-freeze required (unresolved numeric/operational).

| Code | Decision dimension | Human-selected value / rule | Record / unresolved |
|------|--------------------|------------------------------|---------------------|
| 1A | Event Family | Reconstitution | HF (rule frozen) |
| 2A | Universe | Broad US Equity | HF (rule frozen) |
| 2AB | Index Family | S&P Composite 1500; S&P 500; S&P MidCap 400; S&P SmallCap 600 | HF (rule frozen) |
| 2BB | Size Policy | No size exclusion (tradability via liquidity/free-float safeguards) | HF (rule frozen) |
| 2CB | Liquidity Filter | ADV filter (fixed-dollar minimum); **HUMAN-FROZEN US$5,000,000/day** | **RESOLVED** (Item 1/17, 2026-09-07) — fixed pre-specified threshold; not a trial-grid dimension; no percentile/rank replacement; no post-hoc adjustment |
| 2DB | ADV Lookback | 60 trading days, pre-event only | HF (rule frozen) |
| 2EB | Free-Float | Fixed minimum free-float floor = FREE-FLOAT >= 20%; latest PIT/as-announced free-float known by the reconstitution effective date (no look-ahead) | **RESOLVED** (Item 2/17, 2026-09-07) — fixed eligibility rule, NOT a trial-grid dimension; no additional free-float thresholds |
| 2FA | Multiple qualifying events | Keep distinct qualifying events (no double-count, no post-hoc selection) | HF (rule frozen) |
| 2GA | Multiple records within event | Aggregate by event identity + effective date (preserve constituent-level) | HF (rule frozen) |
| 3AA | Signal | +1 / -1 / 0 | HF (rule frozen) |
| 3BA | Signal construction | Event-level composite | HF (rule frozen) |
| 3CA | Signal direction convention | +1 additions / -1 deletions | HF (rule frozen) |
| 4AB | Timing anchor | Effective date | HF (rule frozen) |
| 4BB | Return start | Next tradable observation; forward return = Close(T0+h) / Close(T0) - 1; T0 = effective date; endpoint = official close on the h-th valid trading session, h in {1,5,10} | **RESOLVED** (Item 3/17, 2026-09-07) — simple return; no next-day open; no log returns; source semantics must preserve "official closing price" meaning |
| 4CA | Event-day treatment | Event-day observation kept separate (monitoring/diagnostic only; NOT the h=1/5/10 forward-return observation) | **RESOLVED** (Item 3/17, 2026-09-07) — rule + status frozen; NOT empirical/[V] |
| 4DA | Calendar | Next valid trading session / deterministic calendar (no manual shifting); early-close with a valid official closing print IS a valid session; otherwise the observation is invalid/excluded | **RESOLVED** (Item 3/17, 2026-09-07) — session-validity rule recorded; NOT [V] |
| 5A | Direction | SHORT | HF (rule frozen) |
| 6A | Forward horizons | {1, 5, 10} business days; primary = 5 | HF (rule frozen) |
| 7A | Candidate thresholds | Candidate thresholds: IC ≥ 0.025; HAC t ≥ 2.00; cost ratio ≥ 1.50; autocorrelation ≤ 0.98 | P (candidate-level) |
|   | &nbsp;· Distinct canonical gate floors (subordinate to 7A, not a separate decision code) | Gate floors remain IC > 0 and HAC t ≥ 1.50 | V (canonical) |
| 8AB | Observation unit | Constituent-event observation | HF (rule frozen) |
| 8BB | Effective sample | Event-level effective sample | HF (rule frozen) |
| 8CA | Minimum effective events | T_eff ≥ 25 per composite leg; exact formula = count of DISTINCT effective event dates with a valid composite observation per leg | **RESOLVED** (Item 7/17, 2026-09-07) — HUMAN-FROZEN numeric threshold + deterministic methodology (see §27C); NOT empirical/[V] |
| 8DA | Clustering / inference | Cluster-robust inference by effective event date; cluster unit = effective event date; canonical HAC FIXED_HORIZON_MINUS_ONE (no override); inference effective sample = T_eff | **RESOLVED** (Item 8/17, 2026-09-07) — deterministic methodology (see §27D); NOT empirical/[V] |
| 9AA | Spread cost | Fixed quoted spread assumption | **HF / REQUIRED** — exact spread bps NOT specified; do not invent |
| 9BA | Broker cost | Fixed broker fee assumption | **HF / REQUIRED** — exact broker bps NOT specified; do not invent |
| 9CB | Slippage | Pre-registered slippage grid | **HF / REQUIRED** — exact grid values NOT specified; do not invent; once frozen, all values enter trial grid |
| 10A | Borrow / shorting cost | Fold into conservative fixed-slippage allowance; NO new borrow dimension in canonical CostModelConfig | HF (rule frozen); exact conservative borrow bps **HF / REQUIRED** — do not invent |
| 11A | HTB | Deterministic HTB exclusion; measurement date = published-date / PIT HTB info (no future information); unavailable HTB info → excluded from shortable sample; one deterministic shortability-eligibility rule | **PARTIALLY RESOLVED** (Item 9/17, 2026-09-07) — rule subset frozen (§27F); HTB source/version/data-field remain **HF / REQUIRED** |
| 12A | Survivorship / corporate actions | Point-in-time / as-announced; deterministic corporate-action handling; delisting → no synthetic return (exclude if no valid forward price); CA ordering per canonical PIT CA source; PIT adj-close no look-ahead; ticker not identity | **PARTIALLY RESOLVED** (Item 5/17, 2026-09-07) — conventions frozen (§27G); exact CA source/version remains **HF / REQUIRED** |
| 13A | Missing / suspended data | No imputation; suspended / missing-print / missing-required-close / stale-failing-validity / unavailable-return / source-outage → invalid and excluded from date×leg composite; early-close per Item 3 | **RESOLVED** (Item 6/17, 2026-09-07) — see §27H; no arbitrary stale threshold; NOT [V] |
| 14A | Blind window | Fresh, disjoint, uninspected window | **HF / REQUIRED** — exact dates NOT specified; do not invent |
| 15A | Trial grid | Full Cartesian grid; planned_trial_count == grid_cardinality | V (canonical invariant); final cardinality unsealed until all dimensions frozen |
| 16A | Economic significance | Cost-adjusted spread ratio primary; cumulative reversal secondary | **HF / REQUIRED** — exact cumulative-reversal window NOT specified; do not invent |
| 17A | Governance path | proposal → human freeze → pre-registration → HYP_003 → ResearchReInceptionGate/Gate as applicable → R1 | V (governance ordering; no shortcut) |

### Explicit NOT-specified operational details (remain HUMAN-FREEZE REQUIRED / UNRESOLVED)

Per the human directive, the following are **NOT frozen** and must remain unresolved (do NOT
invent): exact index spin / size-band filter; exact
spread bps; exact broker bps; exact slippage-grid values; exact conservative borrow bps; exact
HTB source / source version / HTB data field; exact
corporate-action source/version; exact fresh blind-window dates; exact
cumulative-reversal evaluation window.
(Items 2/3/5/6/7/8/9 return conventions, eligibility, missing-data, HTB measurement-date /
unavailable-data rule, free-float threshold, and cluster/HAC methodology are now **HUMAN-FROZEN**
— see Items 2/3/5/6/8/9 records in §27D/§27F/§27G/§27H/§27K/§27M.)

---

## 28. Explicit unresolved decisions requiring human freeze

The following MUST be explicitly frozen by the human before any `ResearchReInceptionGate`
invocation. None is chosen here:

1. **Event family** - reconstitution vs. quarterly rebalance vs. separable month-end; one family only.
2. **Universe / filters** - index spin, size band, free-float floor (min-ADV: **RESOLVED** Item 1/17 = US$5,000,000/day; free-float floor: **RESOLVED** Item 2/17 = >= 20%, latest PIT/as-announced free-float known by the reconstitution effective date, no look-ahead, fixed eligibility rule, NOT a trial-grid dimension).
3. **Horizons** - final set {1, 5, 10} or alternative; primary horizon.
4. **Direction** - SHORT on the composite indicator (sign frozen).
5. **Threshold set** - exact rank IC, HAC t, autocorrelation, cost-ratio values for F-1 R1.
6. **Cost + borrow model** - exact bps stack and locate/borrow assumption.
7. **Fresh blind window** - de novo dataset window declared before any returns inspection.
8. **Complete trial grid** - full Cartesian product matching `planned_trial_count == grid_cardinality`.
9. **Formal hypothesis ID minting path** - ordinal HYP_003 minted only through the formal
   pre-registration path; never by this document.

Expanded unresolved governance items added by the governance-locked revision (all HUMAN decisions,
none selected here):

10. **Effective-sample methodology / `T_eff`** - single explicit method: unit of effective
    observation, event cluster definition, `T_eff` computation, minimum effective-event count,
    same-date cross-sectional treatment, named approximation/heuristic (SSA §27C). —
    **RESOLVED** (Item 7/17, 2026-09-07: one effective date × one composite leg = one `T_eff`
    observation; equal-weight arithmetic-mean aggregation; validity rule; no-imputation
    exclusion; exact formula in §27C; no heuristic name required).
11. **Same-date cluster inference** - final HAC/cluster inference policy sealed before Gate/R1
    (§27D). — **RESOLVED** (Item 8/17, 2026-09-07: cluster-robust by effective event date;
    canonical HAC `FIXED_HORIZON_MINUS_ONE`; inference sample = `T_eff`).
12. **Borrow/locate canonical representation** - convention A / B / C resolved by human; affects
    trial grid if a parameter dimension; no post-hoc borrow assumption (§27E).
13. **HTB exclusion rule** - identification method, measurement date, deterministic rule,
    unavailable-borrow treatment (§27F). — **PARTIALLY RESOLVED** (Item 9/17, 2026-09-07:
    measurement date = published-date / PIT; unavailable info → exclude; single deterministic
    rule frozen, see §27F); HTB source/version/field remain unresolved.
14. **Survivorship / corporate-action conventions** - point-in-time source, delisting, M&A,
    ticker change, index rename, CA ordering, adj-close, list versioning (§27G). —
    **PARTIALLY RESOLVED** (Item 5/17, 2026-09-07: conventions frozen, see §27G); exact CA
    source/version binding remains unresolved.
15. **Missing / suspension policy** - suspended, missing prints, early-close, stale, unavailable
    returns, no-imputation rule (§27H). — **RESOLVED** (Item 6/17, 2026-09-07: §27H freeze
    applied; no arbitrary stale threshold).
16. **Economic-significance metric alignment** - cumulative reversal horizon/interpretation and
    cost-adjusted spread ratio threshold as distinct metrics (§27J).
17. **Complete trial grid** - full Cartesian product with
    `planned_trial_count == grid_cardinality`, sealable only once all parameter dimensions are
    human-frozen (§27I).

All items 1-17 above are **decisions reserved for the human**, not for the drafting or revision
agent.

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
- ASCII / byte hygiene: non-ASCII code points = **PRESENT** (whitelisted: §, ≥, ≤, →, —, ·, ×, −); no U+FFFD corruption detected
- All research claims: **PROPOSED / NOT PROVEN / REQUIRES HUMAN FREEZE** as classified above.