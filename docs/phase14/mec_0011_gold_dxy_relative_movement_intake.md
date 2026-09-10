# MEC-0011 - Cross-Asset Gold / DXY Relative-Movement & Volume Divergence (Research Intake)

## 0. Document Status

- Classification: **RESEARCH INTAKE ONLY / NOT AUTHORIZED FOR EMPIRICAL VALIDATION**
- Nature: documentation-only mechanism discovery record. No authorizations are granted by this document.
- Status vocabulary (per free_data_research_registry.md convention): **PROPOSED**.
- Registry status: this record is a standalone intake document. It does NOT register a candidate or
  a mechanism in any canonical registry, and it does NOT create HYP_003 or R1.
- Effective date: 2026-09-10 (environment date).
- Non-ASCII: none (ASCII-only file).
- Review requirement (AGENTS.md #1 Zero Unverified Claims): every claim below carries an explicit
  evidence label. No walkthrough or anecdote is treated as evidence.

## 1. Identifiers & Provenance

- Mechanism candidate ID: MEC-0011 (following the MEC-XXXX numbering sequence; MEC-0001..MEC-0010
  are recorded in ssrn_mechanism_research.md Section 5; MEC-0011 is introduced here as a standalone
  intake so that the read-only ssrn_mechanism_research.md is not mutated).
- Working title: Cross-Asset Gold / DXY Relative-Movement & Volume Divergence.
- Source of observation: a video presentation (informal / practitioner source) claiming that
  (a) a small DXY pullback is followed by a massive gold push, and
  (b) an appropriately constructed "volume mismatch" / divergence between gold and DXY
  reveals the direction of gold "every day".
- Provenance note: The video is a chart anecdote plus narrative. It is NOT an empirical study, and
  does not establish predictive validity (see Section 3 and Section 4).
- Origin marker: this intake is a documentation-only research intake created from a human-assigned
  research question. It is owned by the human operator; the agent authors the neutral record.

## 2. Source Claim (Quoted / Paraphrased, Non-Normative)

- Claim C1: "When DXY pulls back (small pullback), gold pushes massively."
- Claim C2: "By watching the volume mismatch / relative-movement divergence between gold and DXY,
  you can know the gold direction every day."
- Claim C3 (implicit): the divergence is a repeatable, tradeable predictive signal.
- These are source claims. They are recorded verbatim-in-spirit for auditability and are **NOT
  endorsed, verified, or authorized** here.

## 3. Source Observation vs. Predictive Mechanism (Separation)

Per the intake doctrine, an OBSERVED PATTERN is distinct from a PREDICTIVE MECHANISM:

- Observed pattern (anecdotal): a chart window in the video shows a DXY pullback coinciding with a
  gold advance alongside a described volume divergence.
- Predictive mechanism (asserted by source, unproven): the divergence has incremental information
  for the SUBSEQUENT gold return.
- Boundary statement: the chart example is not empirical evidence of a repeatable edge; it is a
  single ex-post-selected instance. Any forward claim requires a pre-registered, falsifiable test.

## 4. Evidence Classification

Evidence labels used throughout this intake (per convention):

- `[VERIFIED BACKGROUND]` - supported by independent (Canonical / literature) evidence.
- `[UNVERIFIED CLAIM]` - asserted somewhere but not independently verified; no canonical support.
- `[RESEARCH QUESTION]` - an open question; mixed or insufficient evidence.
- `[MODEL INFERENCE]` - an agent/human model-level inference, not a documented fact; must never be
  presented as verified evidence.

## 5. Verified Background (Literature)

### 5.1 Gold / DXY inverse relationship - `[VERIFIED BACKGROUND]`

Literature consistently documents an inverse gold / US-dollar relationship (the traditional
"gold is the anti-dollar" heuristic), with important non-linearities and regime dependence:

- Threshold / non-linear models: "Nonlinear Dynamics of Gold and the Dollar" (IMI / RUC working
  material) documents a threshold VECM; under extreme market conditions the short-run correlation
  between gold and the dollar can become POSITIVE, indicating a regime-dependent hedge behaviour.
- Structural-change DCC evidence: Dong, Chen, Lee & Sriboonchitta (Computational Economics, 2019)
  document a negative gold-dollar correlation in almost all sub-periods, with the absolute
  correlation rising in crisis regimes and with asymmetry (US-dollar DOWN-side moves influencing
  gold more than US-dollar upside moves - a leverage/volatility-feedback pattern).
- Reduced-form dollar channel: MDPI (2026) "The U.S. Dollar as a Dollar-Channel Proxy in Gold
  Return Dynamics 2000-2025" finds strong incremental explanatory power of DXY for gold returns,
  consistent with a dollar-channel transmission - i.e., DXY moves carry information about gold
  returns on average.
- COVID-era studies (Johansen cointegration style, e.g., archived preprints) and several academic
  spillover studies similarly support a time-varying, crisis-intensified gold-dollar linkage.

Net verified background: (1) inverse relationship - yes, on average; (2) nonlinear / regime /
time-varying - yes; (3) crisis intensification - yes; (4) asymmetry - documented magnitude.

### 5.2 Non-linear / regime-dependent behaviour - `[VERIFIED BACKGROUND]`

- Threshold VECM (RUC), Markov-switching analyses (e.g., Herley et al., 2024-type studies), and
  DCC-MGARCH time-varying correlation studies all support regime-dependent gold-dollar behaviour.
- "Hug phenomenon" and crisis-spike correlations are documented in spillover / hedge-ratio
  literatures.

### 5.3 Time-varying causality / lead-lag - `[RESEARCH QUESTION]`

Evidence is MIXED and horizon-dependent:

- Some VAR-based studies report that DXY (or the USD) Granger-causes gold over short horizons
  (e.g., 2015-2020 6-month-ish windows, in-sample only).
- Other studies find that foreign-exchange variables predict gold VOLATILITY but NOT gold
  returns (e.g., postgraduate/UP-style theses reporting volatility predictability, and
  gold-producer studies); direction of causality can switch by sub-period and frequency.
- Conclusion: the presence, direction, and stability of a DXY->gold lead-lag for RETURNS is an
  open research question, not an established fact.

### 5.4 Liquidity/volume cross-linkage - `[PARTIAL: VERIFIED BACKGROUND for liquidity linkage only]`

- Studies such as "Does gold liquidity learn from the greenback or the equity?" document that
  liquidity proxies of the dollar and equities predict gold liquidity, non-linearly, with gold
  liquidity responding to dollar liquidity especially in high-volatility states.
- IMPORTANT: this is a liquidity-LINKAGE result (one dependent liquidity series vs. another), NOT
  evidence that a gold/DXY "volume mismatch" predicts subsequent gold PRICE direction.

### 5.5 Net verified background statement

The gold-dollar inverse relationship is real, regime-dependent, and crisis-intensified, and DXY
has on-average incremental explanatory power for gold returns. However, none of this verifies
(a) a repeatable "volume mismatch" predictor, (b) the specific DXY-pullback-to-gold-push timing
rule, or (c) tradeable profitability after costs. Itemized:

- Inverse relationship - `[VERIFIED BACKGROUND]`.
- Non-linear/regime dependence - `[VERIFIED BACKGROUND]`.
- Dollar-channel incremental explanatory power for gold returns - `[VERIFIED BACKGROUND]`.
- "Small DXY pullback -> massive gold push" as a repeatable rule - `[UNVERIFIED CLAIM]`.
- "Volume mismatch" predictive of gold DIRECTION - `[UNVERIFIED CLAIM]`.
- Any tradeable profitability - `[UNVERIFIED CLAIM]`.
- Direction/lead-lag stability - `[RESEARCH QUESTION]`.

## 6. Neutral Mechanism Statement (Hypothesis Form, Non-Committing)

Mechanism candidate (neutral, direction-free until proven):

"When the relative movement between gold and the US dollar index deviates from its normal
(regime-conditional) relationship - and/or when that deviation is accompanied by a divergence in
volume/liquidity across the two complexes - the deviation may contain incremental information for
the subsequent gold return."

Precise research question (the one the human operator stated they like and wish to falsify or
promote):

"Does a deviation in the Gold / DXY relative movement from its normal relationship carry
incremental information for the SUBSEQUENT Gold return?"

Formalized basis (for a future pre-registration, NOT authorized now):

- Null (exemplative, NOT yet ratified): incremental information for the subsequent Gold return
  equals zero, conditional on the normal relationship.
- Alternative (exemplative): incremental information is non-zero in a direction and horizon to be
  specified only in a later, authorized, pre-registered stage.

NOT AUTHORIZED: direction, horizon, thresholds, entry/exit, stops, leverage, or position sizing. NO
such parameters appear in this intake.

## 7. Candidate Variables (Inventory Only - NOT Operationalized)

The following are candidate inputs for the future research question. Their precise operational
definitions, lags, and windows are deliberately left UNDEFINED here by instruction. They are listed
only to name the research surface.

- Gold price series (daily, time-series consistent): e.g., spot/COMEX gold (candidate source
  families: Stooq-style OHLCV gold series).
- US dollar index (DXY) series: e.g., a USD index series (candidate source family: FRED-style
  index series).
- Gold / DXY relative movement: a ratio or paired-return construct (unspecified).
- Normal-relationship residual: deviation of the observed relative movement from a regime-
  conditional "normal" model (the residual model is unspecified).
- Volume semantics: gold volume (exchange-based) vs. DXY volume (index-based; may not exist as a
  canonical exchange volume series - see Section 8).
- Divergence construct: any combination of the above (open research surface).

Boundary: this list is an inventory. No formula, no threshold, no lookback, no holding period
appears in this intake. Any later operationalization requires a fully pre-registered specification
and Human authorization.

## 8. Data Feasibility Assessment (Resources NOT Downloaded)

Objective: feasibility is assessed in principle only. NO data was downloaded; NO empirical work was
performed.

- Gold OHLCV: free daily gold OHLCV history is generally attainable from $0 sources (e.g., Stooq
  family). Feasibility in-principle: YES, subject to a future source audit.
- DXY OHLCV: a dollar-index time series is generally attainable from $0 sources (e.g., FRED
  family). Feasibility in principle: YES, subject to a future source audit.
- Note: ffree_data_source_registry.md currently documents S-01..S-28 and does NOT yet contain a
  registered, audited Gold or DXY series. Potential future audit candidates (S-10 Stooq; S-04 FRED)
  are UNVERIFIED placeholders, not registered sources.
- Synchronized timestamps: gold and DXY history must be synchronized on a shared trading calendar.
  Feasibility in principle: YES, but calendar/session alignment is an audit item.
- VOLUME SEMANTICS CAUTION - CRITICAL:
    - Gold volume from an exchange-traded/OHLCV feed is a volume in the exchange/market sense.
    - DXY (dollar index) is a PRICE INDEX; its "volume" series, where published at all, is derived
      or comes from a derivative (e.g., DXY futures) - it is NOT canonical exchange volume for the
      index itself.
    - Therefore "volume mismatch between gold and DXY" cannot be operationalized until the volume
      semantics of BOTH legs are defined and matched. This is a blocking feasibility caveat.
- Cost of data: target $0. Feasibility in principle for $0: PARTIAL (high for gold and DXY prices;
  UNVERIFIED for matched volume semantics and for any intraday granularity).

## 9. PIT (Point-In-Time) Assessment

- Not yet audited. In principle: price data (gold, DXY) is largely non-revised, so PIT risk is
  LOW-to-MODERATE for price levels; but the "normal relationship" model and any index-composition
  changes of DXY (re-basing / constituent changes) introduce PIT complexity that must be audited in
  a future stage.
- No claim of PIT-cleanliness is made in this intake.

## 10. Survivorship & Universe Bias Assessment

- Gold price index and DXY are aggregate instruments; survive-and-forget bias is LOW in principle
  for the headline series.
- However: if any future operationalization selects sub-periods (crisis windows, high-volatility
  states), regime selection can act like a survivorship-like post-hoc filter. This is an explicit
  risk, NOT an approved design.
- No backfill of delisted or re-based series is assumed.

## 11. Leakage & Information-Flow Assessment

- DXY and gold are both widely-watched, highly liquid, continuously-priced complexes. The
  "subsequent gold return" object is observable forward-looking; if the divergence is constructed
  with lookahead (e.g., using end-of-day DXY close to time an intraday gold position), leakage is
  structural. No intraday construct is defined, and none is authorized.
- Timestamp alignment between gold price time and DXY price time must be treated as a leakage
  surface in any future pre-registration.

## 12. HARKing / Research-Flexibility Risks

The following degrees of freedom must be FROZEN before any empirical work (list is non-exhaustive;
mirrors the 13 risk items assigned to this intake):

1. Definition of "DXY pullback" (magnitude, window, time-of-day).
2. Definition of "gold push" (return horizon, measurement close-to-close vs. intraday).
3. Definition of "normal relationship" (model class, estimation window, regime variable).
4. Definition of "deviation" (residual of the normal model; one-step vs. recursive).
5. Definition of "volume mismatch" (which volume series, normalization, window).
6. Direction of the hypothesized effect.
7. Holding period and rebalance frequency.
8. Universe / instrument selection (gold spot, futures, gold ETF) and any filtering.
9. Horizon (event-horizon vs. fixed-horizon) and the dependent-variable construction.
10. Sample period selection and any sub-period exclusions (crisis windows!).
11. Cost model (spreads, commissions, borrow) and the cost accounting convention.
12. Multiple-testing and trial-count semantics (K) - must follow the CAND-FREE-MACRO-001 K doctrine
    if promoted to a candidate.
13. Stopping rule and PASS/FAIL/INVALID semantics - must be pre-registered, fail-closed.

Rule: NO empirical validation may begin until every item above is resolved by a pre-registered
specification and approved by the human operator.

## 13. Falsification Tests (Proposed, NOT Authorized)

The following are candidate falsification designs for future consideration only:

- Pre-registered deviation -> subsequent-gold-return association tests with a fixed K and a
  specified multiple-testing doctrine (if any later promotion follows the MACRO-001/K lineage).
- In-sample vs. out-of-sample contrast per the CAND-FREE-MACRO-001 validation-readiness doctrine
  (IS evidence is not enough to qualify; the design must specify IS/OOS/Blind per the canonical
  pipeline).
- Regime-robustness: re-run across calm and crisis regimes to test the "works only in a crisis
  window" survivorship-like objection.
- Volume-semantics null: if DXY volume cannot be given exchange-consistent semantics, the
  "volume mismatch" leg is unfalsifiable as stated and the hypothesis must be narrowed (price-ratio
  alone) or dropped.
- Cost sensitivity: any promoted tradeable version must pass the cost layer before PASS/FAIL is
  ever reported.

NONE of these tests are authorized by this intake.

## 14. Blockers (Items That Must Be Resolved Before ANY Authorized Work)

- B1: DXY volume semantics (Section 8) - "volume mismatch" is currently under-operationalizable.
- B2: No registered/audited Gold or DXY data source in free_data_source_registry.md.
- B3: No pre-registered definition of the "normal relationship" residual.
- B4: Direction, horizon, thresholds, entry/exit/stops/leverage/size - all deliberately undefined
  and unauthorized at this point.
- B5: Any promotion to a candidate would require alignment with the CAND-FREE-MACRO-001 K / gating /
  statistical-protocol lineage or an explicitly separate pre-registered doctrine (per the human
  operator: MEC-0011 is a different research family from CAND-FREE-MACRO-001 and must NOT be merged
  into it).
- B6: Vote and charter *not applicable* here - this is a mechanism intake, not a candidate gate.

## 15. Governance Relation & Non-Authorizations

- This intake does NOT modify: ssrn_mechanism_research.md, free_data_research_registry.md,
  free_data_source_registry.md, any candidate file, any F-1 file, or any source/tests code.
  (Verified by git diff --stat / git status after creation.)
- This intake does NOT create HYP_003 or R1.
- This intake does NOT authorize: data download, empirical validation, backtesting, live/eval
  trading, or the assignment of thresholds/lookbacks/holding periods/direction/entry/exit/stops/
  leverage/position sizing.
- CAND-FREE-MACRO-001 governance state is UNCHANGED: CONDITIONALLY READY; PRE-REGISTRATION NOT
  FULLY FROZEN; EMPIRICAL VALIDATION NOT AUTHORIZED; BACKTEST NOT AUTHORIZED.
- MEC-0011 is a SEPARATE research family. Any future promotion must be human-authorized.

## 16. Next Stage (Proposed Litigation Path, Human-Authorized Only)

Stage Gating is human-authorized only. The agent-recommended path, for human consideration:

1. Human review of this intake and explicit decision to (a) keep as a research question,
   (b) request a data-feasibility audit of candidate $0 Gold + DXY sources, or (c) park.
2. If feasible: pre-register the "normal relationship" residual definition and the falsification
   design (deviation -> subsequent gold return), with K and statistical protocol per a canonical
   doctrine.
3. ONLY THEN: any empirical validation, under a frozen manifest.

This record is submitted as a documentation-only intake and stops here. No further action is taken
without explicit human instruction.

### Verification Ledger
- Implementation Status: COMPLETE (intake record only)
- Contract Enforcement: N/A (no empirical contract opened)
- Mathematical Authority: N/A (no formulation claimed; all formulas deliberately undefined)
- Local Test Suite: NOT RUN (no code touched)
- Type Checker (MyPy): NOT RUN (no code touched)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: All predictive/tradeable claims are [UNVERIFIED CLAIM]; only the gold-
  dollar inverse/regime/dollar-channel relationship is [VERIFIED BACKGROUND]; lead-lag direction
  is [RESEARCH QUESTION]; data feasibility is in-principle only and B1-B6 remain open.