# RESEARCH-INTAKE-ATRAIN-IV-WALLS-001

Date: 2026-10-28. Documentation-only intake from the owner's supplied review.
Verified base/main: `499a3a751e22c46d0a2ac22bf7d8a35247630512`.

```text
CLASSIFICATION = RESEARCH_INTAKE_ONLY
CONCEPT_CLASS = RESEARCH_CANDIDATE_CONCEPT
PARENT_CONTEXT = SAT-OPTIONS-001
RELATED_CANDIDATE = SATELLITE_C_STRIKE_LOCAL_PINNING_OR_WALL_EFFECTS
HYPOTHESIS_ID = NONE
MECHANISM_ID = NONE
EMPIRICAL_ADMISSION = NONE
```

FACT (document scope): this intake identifier is not a newly registered Candidate
ID. It preserves a concept for possible future review; it authorizes no research
execution. Existing [candidate conventions](../phase14/research_candidates.md)
and [market-structure intake](RESEARCH-INTAKE-MARKET-STRUCTURE-001.md) provide
organization, not new authority. The historical
[SAT-OPTIONS-001 archive](SAT-OPTIONS-001-dealer-gamma-intraday-regime-research.md)
and its [sealed manifest](manifests/SAT-OPTIONS-001-research-archive.json)
remain unchanged. Historical statements in those documents are not silently
promoted to current governance status by this intake.

## Source and provenance limitations

SOURCE CLAIM: the owner identifies the source as KEONE x ATRAIN TRADES K /
KEONEHUB, "UNDERSTANDING IMPLIED VOLATILITY (IV) WALLS", an educational guide
to ATrain Trades' proprietary Fractal Software. Keone identifies as an ATrain
student and affiliate, according to the supplied account; this potential
commercial interest must remain visible.

UNVERIFIED: the original guide, stable URL, edition, publication date, file hash
and original screenshots were not supplied with this task and were not accessed.
The statements below are preserved from the owner's description, not represented
as an independently inspected primary source or a verified vendor track record.
No new literature search, options-data acquisition or empirical test was performed.

## Original claims to preserve

All items in this section are SOURCE CLAIM, not independently verified facts:

- IV Walls are option-derived price reaction zones; implied volatility and
  option-contract pricing contribute to their calculation.
- Historical volatility and proprietary Fractal Software identify significant levels.
- Levels are prepared daily between 4:30 PM and 6:00 PM, labelled EST in the guide,
  and intended for the next trading session.
- Options inputs include SPY, QQQ and GLD; levels are mapped to ES, NQ and GC futures.
- Walls are reaction zones rather than standalone entry signals.
- Stops, market-structure confluence and illustrative 5R profit targets are discussed.
- Usefulness around macroeconomic news and across times of day is claimed.

UNVERIFIED: EST versus EDT usage is ambiguous. There is no independently verified
historical publication timestamp or revision record. Illustrative 5R targets are
not realized expectancy, win-rate evidence, a loss distribution or net profitability.

## Assessment and non-equivalence

FACT (financial concept retained from archive section 6, not vendor validation):
implied volatility is the volatility parameter implied by option prices under a
specified pricing model. A model-dependent, small-return expected-move scale is:

```text
Expected Move approximately Spot * IV * sqrt(Time in years)
```

HEURISTIC / INFERENCE: IV must be expressed as an annualized decimal and the time
convention must be compatible. This describes movement magnitude under assumptions,
not directional support/resistance, guaranteed coverage, or a canonical wall formula.
No executable formula or numerical threshold is introduced here.

INFERENCE / PLAUSIBLE MECHANISM: options positioning and dealer hedging may affect
conditional intraday volatility and momentum/reversal. The archive treats regime
relationships as a more defensible research direction than generic strike walls.

UNVERIFIED / UNPROVEN VENDOR CLAIM: ATrain IV Walls provide high-probability reactions
or profitable signals. ATrain's proprietary IV Walls are NOT established as the same
calculation as dealer Gamma Exposure (GEX) walls. Similar terminology is not formula
equivalence, and evidence about one does not automatically transfer to the other.

UNVERIFIED / UNKNOWN: proprietary formula, expirations and strikes used, OI weighting,
quote selection and cleaning, timing, dealer-sign inference, confluence definition,
and historical publication record.

FACT (archived limitation): previous-night official options OI is not live dealer
inventory, and OI alone does not identify dealer sign. Future historical evidence
must be point-in-time qualified; do not conflate 0DTE flow with non-0DTE OI proxies.

INFERENCE / CROSS-MARKET LIMITATION: SPY-to-ES, QQQ-to-NQ and GLD-to-GC mappings require
appropriate basis, futures expiration, contract roll and timestamp treatment. No
constant conversion ratio or equivalent instrument exposure is assumed.

## Scientific context and evidence quality

SOURCE CLAIM (existing archive): literature addresses dealer hedging/gamma effects
and option-expiry strike clustering or pinning. These topic-level references are
support for investigating mechanisms, not proof of a vendor strategy.

SOURCE CLAIM (owner's ChatGPT review): preliminary 2026 research reportedly found
weak or statistically inconclusive GEX-wall outperformance against placebo levels.
CITATION_DETAILS_UNVERIFIED: no accessible primary record was supplied or checked
here. No paper names, authors, DOI, sample sizes, p-values or publication dates are
invented. This account is not established consensus or an independently verified
negative result. Neither those studies nor general pinning literature directly
validate or falsify ATrain's undisclosed formula.

## Future design, not execution

PROPOSAL: retain the archived ordering, without registering new candidates:

1. Satellite A: gamma regime versus future realized intraday volatility.
2. Satellite B: gamma regime versus intraday momentum/reversal.
3. Satellite C: strike-local wall effects, lowest priority in the archive.

HYPOTHESIS (informal question only, no HYP ID): do pre-session walls add incremental
predictive value relative to appropriately matched control levels after costs?

PROPOSAL: a future, separately authorized Satellite C design could consider:

- Timestamped pre-session wall levels with immutable revision history; no retrospectively
  selected levels or edited winners.
- Placebo levels matched by distance from spot; prior highs/lows and ATR bands as controls.
- Predefined touch, reaction and breakout rules, including repeated touches and ambiguous bars.
- Separate 0DTE/non-0DTE populations; CPI/FOMC and session-time controls.
- Explicit SPY/QQQ/GLD scope and futures basis, expiration and roll treatment.
- Actual bid/ask, fees, slippage and feasible fills rather than illustrative target outcomes.
- Chronological train/validation/holdout boundaries; multiple-testing and selection-bias controls.
- Falsification if no incremental predictive value remains after costs, using a prespecified
  criterion and uncertainty treatment rather than tuning rules after seeing outcomes.

All are proposed considerations, not approved parameters, frozen acceptance criteria,
a preregistration, data-access approval or permission to backtest.

## Vendor due diligence before any future purchase

PROPOSAL: require at least an operational definition or sufficiently timestamped
black-box output; unedited historical pre-session levels; publication timestamps
and revisions; PIT data provenance; independent placebo-based validation; full
losing-trade distribution and post-cost results; market/instrument/time-zone scope;
and explicit data-retention, research-use and redistribution rights.

PROPOSAL / OWNER REVIEW STANCE: DO NOT BUY SOFTWARE based only on educational or
affiliate claims. This intake grants no subscription or purchase authority.

## Governance and verification

No canonical registry, HYP/MEC status, trust anchor, admission, strategy, D6/V37A,
feed or broker connection is changed. PR68 and the ongoing Research Sprint are
separate. The owner's required boundaries are preserved, not newly ratified here:

```text
HYP_003 = TERMINALLY_FALSIFIED
D5 = NOT_ADMITTED
LANE_A/B = UNISSUED
REAL_CAPITAL_AUTHORITY = USD 0.00
NO_REAL_ORDERS = true
```

Only this Markdown intake is added. No new index, manifest or duplicate archive is
created. A future Candidate Registry entry requires a separate governance review.
Merge requires separate owner authorization.

### Verification Ledger

- Implementation Status: COMPLETE (documentation intake only).
- Contract Enforcement: N/A (no runtime mutation).
- Mathematical Authority: HEURISTIC SPEC for expected-move illustration; no new implementation.
- Local Test Suite: NOT RUN (documentation-only); relative links and diff checked separately.
- Type Checker (MyPy): NOT RUN (documentation-only).
- Remote CI Status: PENDING at document creation; inspect the PR exact-head checks.
- Methodological Caveats: secondary owner-provided source account; primary guide and
  citation details unverified; no empirical, dataset, hypothesis or trading authority.
