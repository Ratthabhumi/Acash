# VIX Daily Volatility Context — Research Note (2026-10-13)

```text
RESEARCH_BRANCH_ID = VOL-CONTEXT-001
STATE = RESEARCH_ONLY
CLASSIFICATION = DESCRIPTIVE_VOLATILITY_CONTEXT_CANDIDATE
HYPOTHESIS_ID = NONE
PREREGISTRATION = NONE
BACKTEST_AUTHORIZATION = NONE
DATA_ACCESS_AUTHORIZATION = NONE
STRATEGY_VALIDATED = NO
AUTHORIZED_FOR_TRADING = NO
REAL_CAPITAL_AUTHORITY = USD 0.00
NO_REAL_ORDERS = true
```

- **Document ID:** `docs/research/volatility/VIX_DAILY_VOLATILITY_CONTEXT_RESEARCH_NOTE_20261013.md`
- **Canonical HEAD at note creation:** `04f6911` (branch `feat/m1.7-offline-data-admission`)
- **Role:** additive documentation-only research intake. No hypothesis created, no
  preregistration, no backtest, no data fetch, no production code change, no
  roadmap change. This note does NOT alter M1.7 priorities.

Verification markers used throughout:

- `[VERIFIED]` — statement confirmed against a source actually retrieved during
  the 2026-10-13 session, or derived by explicit arithmetic shown in this note.
- `[ASSUMPTION]` — standard quantitative convention or modeling assumption.
- `[PROPOSAL]` — future work; nothing in this section has been executed.

---

## 1. Executive Summary

The claim "expected daily volatility ≈ VIX / 16" is a widely used shortcut for
VIX / sqrt(252). It is **arithmetically sound as a heuristic** `[VERIFIED]`
(Section 3) and is even echoed by Cboe's own educational material: "the VIX
Index at 16 means an expected +/- 16% annual move for the S&P 500, which would
equal a daily range of +/- ~1%." `[VERIFIED]`

It is **not** a calibrated one-day forecast. VIX measures a constant 30-calendar-
day implied volatility horizon, not a single session; it is risk-neutral
(implied, not realized) and carries a variance risk premium `[VERIFIED]`.
Converting it to a per-session figure requires assumptions (flat volatility term
structure, constant vol path, normal-ish distribution) that markets routinely
violate `[ASSUMPTION]`.

This note preserves the concept as **descriptive market-risk context** only,
registers it for future evaluation alongside ACASH's existing evidence and
admission contracts, and records exactly what would have to be verified before
any prospective use. No experiment has been run.

---

## 2. Original Claim

The incoming claim (preserved as received, unmodified in substance):

- Approximation: `Expected Daily Volatility ≈ VIX / sqrt(252)` ≈ `VIX / 16`.
- Examples: VIX 16 → ~1.0% daily vol; VIX 24 → ~1.5%; VIX 32 → ~2.0%.
- Use: compare actual S&P 500 price movement to the estimate to flag unusually
  large moves. Example given: VIX = 16, estimated daily vol ≈ 1%, SPX return =
  −2% → |move| / estimated vol ≈ 2×.
- Purpose: descriptive market-risk context.

Explicitly stated by the claim itself, and re-affirmed here: the claim does
**not** establish a guaranteed daily trading range, tomorrow's return, market
direction, a statistically confirmed regime change, a profitable trading
signal, or authority to change portfolio allocations.

Proposed descriptive statistic name (registered, not computed anywhere):

```text
Volatility Surprise Ratio = abs(SPX Return) / Estimated Daily Volatility
Estimated Daily Volatility = VIX / sqrt(252)      [or VIX1D / sqrt(252)]
```

---

## 3. Mathematical Verification

### 3.1 What VIX measures `[VERIFIED]`

Source: Cboe Insights, "What the VIX and VIX1D Indices Attempt to Measure and
How They Differ" (Spencer Doar, 2023-04-24).

- VIX "provides a reading of constant, 30-day expected volatility of the S&P
  500 Index."
- It "is derived from real-time, mid-quote prices of a strip of S&P 500 options
  (SPX), whose expiries land between 23 and 37 days from the current trading
  day."
- Output is "a non-directional, annualized expectation for the standard
  deviation of the S&P 500."
- Cboe's own quick reference: "the VIX Index at 16 means an expected +/- 16%
  annual move for the S&P 500, which would equal a daily range of +/- ~1%."

So VIX is an **annualized standard deviation (volatility)** quoted in percent
units — not a variance, not a price move, not a range in index points.

### 3.2 Variance vs. volatility vs. expected absolute movement `[VERIFIED]`

| Object | Symbol | Meaning |
|---|---|---|
| Variance | σ² | Squared-dispersion rate (VIX computes a variance first, then takes its square root) |
| Volatility (std. dev.) | σ | Same units as returns; VIX output |
| Expected absolute move (1 session) | E[|r|] | Under normality: σ_daily × sqrt(2/π) ≈ 0.798 × σ_daily |

A "±1σ daily range" is a **standard-deviation band**, not an expectation of
the absolute move and not a guaranteed range. Under a normal distribution
P(|r| > 1σ) ≈ 31.7%, P(|r| > 2σ) ≈ 4.55%, P(|r| > 3σ) ≈ 0.27% — even in the
idealized model, moves beyond the band are common, not exceptional.

### 3.3 Why sqrt(252) `[ASSUMPTION + VERIFIED ARITHMETIC]`

- Markets trade ≈ 252 US sessions per year; annualization by σ_annual =
  σ_daily × sqrt(252) assumes independent (or at least uncorrelated) daily
  increments `[ASSUMPTION]`.
- Arithmetic `[VERIFIED]`: sqrt(252) = 15.8745…, so "VIX / 16" is a rounded
  VIX / sqrt(252). Using 16 instead of 15.8745 underestimates daily vol by
  ≈ 0.79% relative — negligible versus the modeling error.
- Unit caveat: VIX's own time argument uses **calendar** time (30 calendar days
  ≈ 21 trading days) while sqrt(252) converts in **trading-day** time. Under a
  constant-volatility, no-gap model the two roughly reconcile; overnight gaps
  are precisely where the conventions disagree in practice `[ASSUMPTION]`.

### 3.4 The horizon-translation limitation `[VERIFIED + ASSUMPTION]`

- The 30-day implied volatility is an **average-rate estimate over the next
  month**, not a rate for any single day inside it `[VERIFIED: Cboe]`.
- Dividing by sqrt(252) silently assumes variance is **evenly distributed**
  across sessions — flat term structure, no event concentration `[ASSUMPTION]`.
  Known-unknown events (FOMC, CPI, elections) load variance onto specific days;
  Cboe reports VIX1D rose ~61.4% on average the day before CPI/FOMC
  announcements vs +1.9% for VIX `[VERIFIED]`.
- Therefore VIX/16 is a **heuristic central estimate for a typical session in an
  evenly-diffused regime**, not a precisely calibrated one-day options-implied
  expected move. A calibrated one-day figure requires single-day options
  pricing (which VIX1D approximates).

---

### 3.5 Implied vs. realized volatility `[VERIFIED]`

- VIX is **implied** volatility: extracted from option mid-quotes, a
  risk-neutral measure embedding a variance risk premium.
- Cboe reports: "In 2022, the VIX Index averaged ~23, while the market realized
  ~24. This 1% difference – the risk premium – is lower than historical
  averages of 3-4%" `[VERIFIED]`.
- Consequence: VIX/16 will typically **overestimate** realized daily vol in
  calm regimes (premium decay) and can **underestimate** it during realized
  stress. The bias direction is regime-dependent `[ASSUMPTION]`.

### 3.6 Normal approximation and fat tails `[ASSUMPTION: standard stylized fact]`

- The ±1σ-band picture implicitly uses a Gaussian. Equity index returns exhibit
  excess kurtosis, volatility clustering, skewness, and jump risk; tails are
  heavier than normal `[ASSUMPTION — not empirically tested in ACASH]`.
- Frequency statements like "moves > 2σ occur 4.55% of the time" are
  **model-implied**, not empirically guaranteed. Any frequency claim must be
  measured against qualified data before use.
- Standard deviation ≠ guaranteed price range, at any horizon.

---

## 4. VIX vs. VIX1D

### 4.1 Verified comparison `[VERIFIED]`

Sources: Cboe Insights (2023-04-24, 2023-05-15), Cboe launch press release
(2023-04-24), tastylive explainer (2023-04-24).

| Property | VIX | VIX1D |
|---|---|---|
| Horizon | Constant 30 calendar days | Current (one) trading day |
| Option expiries used | SPX expiring 23–37 days out | Zero-day and one-day P.M.-settled SPX weekly expirations (dynamic mix of today's and next session's expiries) |
| Units | Annualized expected std. dev. (%) | Annualized expected std. dev. (%) |
| Launch | 1993 (calculation/dissemination) | 2023-04-24 (daily history backfilled to 2022-05-13) |
| Tradable? | Index itself not tradable (VIX futures since 2004, options since 2006) | Not tradable; Cboe stated no plans for VIX1D derivatives (as of 2023) |
| Intended read | Next-month sentiment | Current-session sentiment |

Key Cboe quotes:

- "The VIX1D Index seeks to measure the expected volatility of the S&P 500
  Index over the current trading day and has been designed to account for the
  compressed measurement of expected volatility over a single day."
- "The VIX Index does not, nor is it intended to, offer insight into tomorrow's
  market movement."
- "The VIX1D Index is intended provide a real-time look at market sentiment over
  the current trading day (today)." [sic]


### 4.2 Why VIX1D may be better suited to same-session context `[VERIFIED REASONING / PROPOSAL EMPIRICAL]`

- Horizon match: a one-session estimate built from options priced at the
  one-day horizon should, in principle, beat a 30-day estimate divided by a
  constant.
- Event sensitivity: VIX1D is far more responsive to same-day known-unknown
  events (Cboe: pre-CPI/FOMC dates averaged +61.4% VIX1D vs +1.9% VIX;
  largest one-day VIX1D jump over the prior year was +153.2% vs +22.6% VIX)
  `[VERIFIED]`.
- Whether that responsiveness translates into **better calibration against
  realized same-day volatility** is an open empirical question — see Section 9.

### 4.3 Remaining uncertainty and model limitations `[MIXED — see flags]`

- **Publication cadence / pre-market availability — NOT VERIFIED this session.**
  The official VIX1D methodology PDF was retrieved (cdn.cboe.com, ~1.3 MB) but
  could not be text-extracted with available tooling; calculation timestamps,
  15-second cadence, and pre-market behavior could not be confirmed from the
  primary document. Secondary source (Six Figure Investing, 2023-04-30)
  describes two whitepaper details: variance interpolation in **business time**
  during regular hours, and **freezing the current-day contribution after
  15:00 ET** to dampen end-of-session distortions — treat as secondary until
  re-verified against the primary document.
- **Known structural bias `[VERIFIED: peer-reviewed]`**: Albers & Kestner
  (2024, *Finance Research Letters* 62, article 105186) identify an **overnight
  bias** — VIX1D consistently rises during trading hours and falls overnight,
  attributed to business-time and dynamic next-term weighting that embed
  overnight variance risk premia. Any intraday VIX1D path must be interpreted
  with this bias in mind; proposed fixes (forward-starting variance) are
  untested here.
- **Microstructure**: 0DTE/one-day option mid-quotes are sensitive to wide
  spreads, discrete strikes, and pinning (secondary sources; Cboe counters that
  short-tenor bid/ask spreads are comparable to those used for VIX).
- **Calendar artifacts**: day-of-week normalization effects are expected
  (the weekend effect shifts to Fridays for VIX1D, per secondary analysis).
- **Entitlement `[ASSUMPTION — NOT ESTABLISHED]`**: availability of VIX or
  VIX1D under current ACASH data entitlements is unknown. ACASH inventory
  registers FRED `VIXCLS` (daily close) as `DS-08 SOURCE_DOCUMENTED` but
  **NOT QUALIFIED FOR BENCHMARK**
  (`./docs/research/REUSE_FIRST_DATA_SOURCE_AUDIT_20261012.md`).
  Real-time Cboe index data must not be assumed accessible.

---

## 5. Correct Interpretation

What the VIX/16 heuristic **is**:

1. A quick mental conversion of an annualized 30-day implied volatility into a
   per-session **standard-deviation scale**.
2. A **descriptive yardstick** for "was today's move large relative to the
   currently priced volatility climate?"
3. A **context label** (calm / normal / elevated / stressed) that is
   forward-looking only in the sense that implied vol reflects option-market
   sentiment today.

What it **is not**:

1. Not a guaranteed trading range, floor, or ceiling for the session.
2. Not a prediction of tomorrow's return, sign, open-to-close direction.
3. Not a statistically confirmed regime change detector (a regime claim needs
   a preregistered test, not a single ratio).
4. Not a trading signal, and not authority for allocation changes.
5. Not a substitute for realized-volatility measures already standard in risk
   reporting (e.g., EWMA/GARCH, Parkinson/Garman-Klass on intraday data).

### 5.1 The same-day look-ahead boundary `[GOVERNANCE]`

Computing `abs(SPX return of day T) / (VIX of day T)` and calling the result a
"surprise" is a **descriptive summary of a completed day**, not a prediction.
If VIX is sampled at the close of day T, both numerator and denominator refer
to the same completed interval — this cannot be used as evidence that the
ratio has any pre-market or intraday forecasting power.

Any **prospective** study must specify, at minimum:

- Observation cutoff and as-of timestamp for every input (e.g., VIX quote at
  09:30:00 ET, never the close).
- Decision timestamp strictly after the information cutoff.
- Execution timing model (next bar, close, VWAP window) declared in advance.
- Point-in-time (PIT) safeguards preventing post-hoc data revisions from
  leaking into the input series.

---

## 6. Misleading Claims and Limitations

Misleading framings this note rejects:

| Misleading claim | Why it is wrong |
|---|---|
| "VIX 16 → market will move ±1% today" | VIX is a 30-day average expectation; any single day can deviate arbitrarily (fat tails, event concentration) |
| "2× surprise ⇒ mean reversion trade" | Ratio thresholds have no validated distributional or predictive status in ACASH; no test has been run |
| "VIX jumped ⇒ regime change confirmed" | A regime claim requires a preregistered change-point/statistical test with trial accounting |
| "Implied vol is the market's best forecast of realized vol" | IV is risk-neutral and embeds a variance risk premium (Cboe-verified 3–4% historical gap); it is a sentiment/pricing input, not an unbiased forecast |
| "VIX/16 is calibrated to one-day options" | It is a division of a 30-day measure by an annualization constant; no one-day option enters the calculation |
| "VIX1D gives a guaranteed daily range" | Same standard-deviation semantics, same tail and model risks, plus documented overnight-bias artifacts |
| "This works for position sizing" | Allocation authority requires strategy validation, cost analysis, and explicit human authorization — none exist |

Additional limitations:

- **Non-tradability**: neither VIX nor VIX1D is directly tradable; both are
  statistics computed from other instruments' quotes.
- **Staleness**: without entitlement confirmation, only delayed/daily data
  (e.g., FRED `VIXCLS` daily close) may be available — enough for retrospective
  description, not for intraday context.
- **Survivorship of the heuristic**: "VIX/16 ≈ 1%" holds because sqrt(252) ≈ 16;
  presenting it as a market law rather than a unit conversion is a common
  rhetorical error.

---

## 7. Worked Numerical Examples

All arithmetic in this section is unit-consistent and `[VERIFIED]` by
calculation; the inputs are illustrative, not historical records. Convention:
`daily_sigma_pct = VIX / sqrt(252) = VIX / 15.8745`.

| VIX | VIX/16 (headline) | VIX/sqrt(252) (precise) | Abs-move for 1σ | For 2σ |
|---|---|---|---|---|
| 16 | 1.000% | 1.008% | ≈ ±1.01% | ≈ ±2.02% |
| 24 | 1.500% | 1.512% | ≈ ±1.51% | ≈ ±3.02% |
| 32 | 2.000% | 2.016% | ≈ ±2.02% | ≈ ±4.03% |

**Original claim's example (Volatility Surprise Ratio):**

```text
VIX = 16 → daily_sigma ≈ 1.008%
SPX return (completed session) = -2.0%
Volatility Surprise Ratio = |-2.0%| / 1.008% ≈ 1.98×
```

Interpretation allowed: "the session's move was ~2 estimated daily standard
deviations — a large-but-not-exotic move (under a Gaussian, |r| > 2σ occurs
≈ 4.55% of sessions; real fat tails make this more frequent)."

Interpretation forbidden: "the market will move ±1% tomorrow", "volatility
regime has changed", "expect reversion", or any allocation change.

**Reverse sanity check**: VIX 32 over a full month implies ≈ 32%/sqrt(252) ≈
2.02% per session; a −4% session would be ≈ 1.98× that estimate — the ratio
scale behaves linearly in VIX by construction `[VERIFIED: linear in numerator]`.

---


## 8. Potential ACASH Use Cases

All items below are **prospective, read-only, non-authoritative** candidates.
Nothing here is implemented.

1. **Risk monitoring context**: display `VIX / sqrt(252)` alongside realized
   daily vol as a descriptive dual-column readout (implied vs. realized).
2. **Volatility dashboard**: trend of estimated daily vol, with VIX1D overlay
   if/when entitlement exists; annotate the documented VIX1D overnight bias.
3. **Market context reports**: include the Volatility Surprise Ratio in
   end-of-session descriptive summaries (clearly labeled retrospective).
4. **Portfolio risk diagnostics**: contextualize drawdown days ("−2.1% ≈
   2.1× current implied daily vol") as narrative text only.
5. **No-trade / attention alerts**: as a *human attention* flag (e.g., "today's
   move exceeded 2.5× implied daily vol — review"), never an automated action.
   Must fail-closed to `UNKNOWN` when VIX data is absent — no fabricated
   neutral values (ACASH fail-closed contract).
6. **Read-only personal investment decision support**: descriptive dashboard
   for the operator, outside ACASH execution authority.

Explicit non-recommendations:

- **No automatic rebalancing** based solely on VIX/VIX1D.
- No signal generation, no gate criteria, no position-sizing hooks.
- Prefer existing ACASH contracts (evidence plane, data qualification lanes,
  fail-closed data contracts) over new architecture. Any future ingestion of
  VIX data must enter through the same admission/authority path as other data
  (Lane A/B style: entitlement → provenance → byte/operation budget → redaction
  → fail-closed validation).

---

## 9. Scientific Falsification and Calibration Plan `[PROPOSAL — NOT EXECUTED]`

Registered research questions (each would need its own preregistration):

1. Is `VIX / sqrt(252)` a calibrated estimator of same-day realized volatility?
   Test: ratio `realized_daily_vol / (VIX_t / sqrt(252))` should center on 1
   with acceptable dispersion, evaluated out-of-sample with PIT inputs.
2. Does VIX1D improve calibration relative to VIX for the current session?
3. How frequently do daily |returns| exceed 1×, 2×, 3× the estimate, and how
   do those frequencies compare with Gaussian benchmarks (31.7% / 4.55% /
   0.27%) and with fat-tailed alternatives?
4. Does the Volatility Surprise Ratio identify risk-regime changes better than
   existing realized-vol measures (EWMA, GARCH, rolling std)? Baseline
   comparison mandatory.
5. Does conditioning on this statistic improve portfolio decisions **after
   transaction costs**, relative to a no-condition baseline?
6. Does it add information **beyond** existing realized-volatility measures
   (incremental-value test, not standalone correlation)?

Mandatory prerequisites for any future test (none satisfied today):

- Separate preregistration with fixed hypotheses, horizons, and metrics.
- Qualified, point-in-time historical data with documented entitlement.
- Trial accounting (K ledger) so question-shopping is counted.
- Sealed-holdout boundaries preserved; existing ACASH negative results and
  sealed decisions untouched.
- Explicit operator authorization before any empirical execution.

Falsification stance: the concept is **expected to be approximately right in
central tendency and systematically wrong in the tails**; the empirical
questions above are designed to measure, not confirm, that expectation.

---

## 10. Data and Licensing Requirements `[REQUIREMENTS — NOT ACQUIRED]`

| Need | Candidate | Status |
|---|---|---|
| Daily VIX close (retrospective studies) | FRED `VIXCLS` | Registered `DS-08 SOURCE_DOCUMENTED`, **NOT qualified for benchmark**; conversion/qualification outstanding |
| Real-time / intraday VIX | Cboe official distribution or licensed vendor | Entitlement NOT established; no access assumed |
| VIX1D history (back to 2022-05-13) | Cboe Global Indices site | Entitlement NOT established |
| Intraday SPX returns | Existing ACASH equity data path | Subject to current M1.7 qualification lanes |
| Options chain data (if replicating VIX) | Cboe options data | Far out of scope; separate qualification project |

Licensing notes: Cboe index data is proprietary and subject to redistribution
terms; any future ingestion must document permitted use, caching, and display
rights before acquisition. No provider API was contacted for this note.

---

## 11. Future Integration Dependencies

```text
[Human authorization]  (documentation only today — satisfied for this note)
        │
[Data entitlement: VIX/VIX1D source]   ← BLOCKED (not established)
        │
[Data qualification lane: provenance, budgets, redaction, fail-closed]
        │
[Calibration study preregistration + trial accounting]   ← NOT STARTED
        │
[Empirical execution → evidence plane]
        │
[Human review of results]
        │
[Any integration into dashboards / risk tooling]
        │
[Strategy or allocation use]  ← requires full strategy validation chain
```

- Milestone independence: none of the above gates or modifies M1.7 offline
  data qualification; this note is a parallel research-intake artifact.
- Reuse: prefer `LaneARequestLedger`-style budgets, `redact_secrets()`,
  evidence-lineage records, and `DataContractError` fail-closed semantics if
  ingestion is ever approved.

---

## 12. Official Sources and References

**Primary / official (retrieved 2026-10-13):**

1. Cboe Insights — Spencer Doar, "What the VIX and VIX1D Indices Attempt to
   Measure and How They Differ" (2023-04-24).
   `https://www.cboe.com/insights/posts/what-the-vix-and-vix-1-d-indices-attempt-to-measure-and-how-they-differ`
2. Cboe Insights — Matt Moran, "How the VIX1D Index Performance Compares to the
   VIX Index and Other Volatility Indices in 11 Charts" (2023-05-15).
   `https://www.cboe.com/insights/posts/how-the-vix-1-d-index-performance-compares-to-the-vix-index-and-other-volatility-indices-in-11-charts`
3. Cboe press release via PR Newswire, "Cboe Global Markets Launches 1-Day
   Volatility Index…" (2023-04-24).
4. Cboe VIX1D methodology PDF (retrieved, **text not extractable this
   session**):
   `https://cdn.cboe.com/api/global/us_indices/governance/Volatility_Index_Methodology_Cboe_1-Day_Volatility_Index.pdf`
5. Cboe VIX methodology PDF (retrieval returned HTTP 403):
   `https://cdn.cboe.com/api/global/us_indices/governance/VIX_Methodology.pdf`

**Secondary (retrieved 2026-10-13, flagged as secondary):**

6. tastylive, "What is the VIX1D & How Does it Work?" (2023-04-24).
7. Six Figure Investing — Vance Harwood, "How Does the Cboe's VIX1D Work?"
   (2023-04-30).
8. Cboe VIX FAQ page (©2025) — page loaded; answers are client-rendered and
   were not text-extractable this session.

**Peer-reviewed:**

9. Albers, S. & Kestner, L. N. (2024). "The daily rise and fall of the VIX1D:
   Causes and solutions of its overnight bias." *Finance Research Letters* 62,
   105186. DOI: 10.1016/j.frl.2024.105186 (abstract retrieved).

**ACASH internal:**

10. `./docs/research/REUSE_FIRST_DATA_SOURCE_AUDIT_20261012.md` (DS-08 FRED).
11. `./docs/research/LANE_B_SPEC_OFFLINE_QUALIFICATION.md` (data admission
    pattern for any future ingestion).

---


## 13. Current Research Classification

```text
CLASSIFICATION            = RESEARCH_ONLY
CANDIDATE_TYPE            = DESCRIPTIVE_VOLATILITY_CONTEXT_CANDIDATE
STRATEGY_VALIDATED        = NOT_STRATEGY_VALIDATED
TRADING_AUTHORITY         = NOT_AUTHORIZED_FOR_TRADING
HYPOTHESIS_ID             = NONE
PREREGISTRATION           = NONE
BACKTEST_RUN              = NONE
DATA_FETCHED              = NONE (web documentation only; no market/provider data)
PRODUCTION_CODE_CHANGED   = NONE
FINAL_STATUS              = DOCUMENTED_FOR_FUTURE_RESEARCH
EMPIRICAL_STATUS          = NOT_EMPIRICALLY_VALIDATED
EXECUTION_AUTHORITY       = NO_EXECUTION_AUTHORITY
```

Suggested future research priority: **LOW–MEDIUM / BACKLOG** — useful for Risk
Monitoring once M1.7-qualified data exists; subordinate to M1.7 Data
Qualification. Revisit after: (a) PR #26 merge decision, (b) Lane A/B data
admission, (c) an explicit operator request to run calibration question Q1.

---

## 14. Explicit Non-Goals

This note does **not**:

1. Implement any trading strategy, indicator, signal, gate, or dashboard.
2. Modify `src/`, production tests, portfolio allocations, or broker
   configuration.
3. Run backtests, fetch provider market-data APIs, or open sealed datasets.
4. Create a hypothesis, preregistration, or trial count.
5. Change ACASH development priorities or M1.7 milestone scope.
6. Grant or imply any trading, allocation, or capital authority.
7. Assert VIX/VIX1D data entitlement or availability.
8. Overwrite, supersede, or conflict with any prior ACASH research decision,
   negative result, or sealed holdout boundary.

```text
REAL_CAPITAL_AUTHORITY = USD 0.00
NO_REAL_ORDERS = true
No provider HTTP · No broker access · No paper/live orders
No Homelab deployment · No capital allocation
```

**STOP.** Research note preservation complete; the task does not expand into
implementation.


