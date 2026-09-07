# ACASH Phase 14 Research Candidate Registry / Discovery Report

**Document ID:** `docs/phase14/research_candidates.md`
**Status:** RESEARCH CANDIDATE PREPARATION — registry + discovery report
**Date:** 2026-09-07
**Authority:** `AGENTS.md`, `./research_doctrine.md`, Phase 14 Master Research Architecture
(`./phase14_master_research_architecture_plan.md`)

> [!CAUTION]
> ### HARD GOVERNANCE & SAFETY INVARIANTS
> - **THIS DOCUMENT CREATES NO HYPOTHESIS. HYP_003 REMAINS ABSENT.**
> - **NO HYPOTHESIS REGISTRATION:** No `ResearchReInceptionGate` invocation, no R1, no sealing.
> - **NO DATA:** Zero market data accessed, downloaded, or generated.
> - **NO EXECUTION:** Zero backtests, simulations, numerical validation, or trades.
> - **NO CONNECTORS:** Zero broker / MT5 / prediction-market / market-data connector activity.
> - **NO IMPLEMENTATION:** Slice 1-4, frozen core, governance gates, and ExecutionCoordinator are
>   unchanged. No Slice 5.
> - **CAPITAL & TRADING HARD-LOCKED:** Capital = **$0.00**; Trading = **LOCKED**.
> - Epistemic classification of every candidate here is **REPORTED / INFERRED / NOT PROVEN**.

---

## 1. Objective

Produce a structured set of potential **research candidates** (not hypotheses) that can be reviewed
and explicitly approved by a human before entering `ResearchReInceptionGate`. This is mechanism and
hypothesis-design preparation only. No candidate is assumed to be good.

## 2. Methodology

- Use `./research_doctrine.md` as methodology guidance (mechanism before model, simple before complex,
  edge after friction, falsification before qualification, time horizon empirical, alpha decays,
  AI proposes / deterministic system verifies).
- Source only ideas already present in repository research/reference material and human-provided
  context. No new external sources.
- Do NOT tune parameters on unseen data (no HARKing). Any numerical parameter is labeled
  **PROPOSED / NOT YET SEALED**.
- Do NOT rank by claimed historical returns. Rank by research quality.

## 3. Candidate Shortlist

| # | Family | Provisional Direction | Existing Note? | Status |
|---|--------|----------------------|----------------|--------|
| F-1 | A. Structural / Forced Flow | Calendar-forced rebalancing & block-trade dislocation (equity index) | No | NEW DIRECTION |
| F-2 | B. Relative Value / Spread | Temporary two-asset spread dislocation / mean reversion | No | NEW DIRECTION |
| F-3 | C. Momentum / Continuation | Session-open EMA momentum (NASDAQ-100 M5) | `candidates/candidate_ny_open_ema_momentum_nasdaq_m5.md` | UNVALIDATED PROPOSAL |
| F-4 | C. Momentum / Continuation | NY-open first 5-min bar / EMA12 (NASDAQ-100 M5) | `candidates/candidate_ny_open_first5_ema12.md` | UNVALIDATED PROPOSAL |
| F-5 | D. Regime Filtering | MA / volatility regime risk filter (single asset) | No | NEW DIRECTION |
| F-6 | E. Cross-Market / Global Arbitrage | Prediction-market AI forecasting + cross-venue arbitrage | `candidates/candidate_prediction_market_ai_forecasting_kalshi_polymarket.md` | UNVALIDATED RESEARCH DIRECTION |

Existing per-candidate notes are NOT duplicated here; they remain the full detail authority for F-3,
F-4, and F-6. Their unresolved gaps are summarized in Section 4.

## 4. Candidate-by-Candidate Analysis

Common classification for ALL candidates below:
**REPORTED / INFERRED** mechanism; **NOT PROVEN** profitability / predictive power / persistence.

### F-1 Structural / Forced-Flow Calendar Effects (equity/ETF index)

| # | Quality-Standard Field | Content |
|---|------------------------|---------|
| 1 | Candidate ID | `CAND-FLOW-CALENDAR-REBALANCE-001` (NOT HYP_003) |
| 2 | Name | Calendar-forced rebalancing & month-end/quarter-end flow effects |
| 3 | Research family | A. Structural / Forced Flow |
| 4 | Economic mechanism | Index/ETF rebalancing and month-end/quarter-end portfolio flows force
      price-insensitive volume; participants trade for balance-sheet, mandate, or calendar reasons,
      not fundamental value (doctrine 5). |
| 5 | Why an edge could exist | Temporary price distortion created by forced demand/supply that others can
      absorb only at a premium/discount; distortion should mean-revert when the forced flow clears. |
| 6 | Observable variables | Calendar flags (month/quarter end, expiry), intraday volume/flow proxies,
      return, spread, imbalance. |
| 7 | Expected holding horizon | Intraday-to-a-few-days (PROPOSED / NOT YET SEALED). |
| 8 | Expected direction | Mechanically ambiguous (depends on flow side); requires the direction to be
      pre-specified as a testable sign hypothesis, not mined. |
| 9 | Friction / cost | Turnover high; spread + slippage at rebalance time likely large; net edge questionable. |
| 10 | Main failure modes | No measurable distortion; effect already arbed out; cost > net edge (doctrine 3/6). |
| 11 | Falsification conditions | Calendar-day conditional test shows zero incremental net edge after costs vs.
      unconditional baseline at pre-specified significance. |
| 12 | Confounders | Macro announcements on same dates; volatility clustering; regime confounds. |
| 13 | Required data | High-quality intraday single-index bars with reliable timestamps + calendar metadata;
      no current connector exists. |
| 14 | Success | Pre-registered calendar-conditioned distortion means-reverts with net edge > 0 after costs. |
| 15 | Terminal failure | No post-cost net edge; effect not stable across sub-periods. |
| 16 | Complexity level | LOW-MEDIUM (single-asset, calendar conditioning, simple comparisons). |
| 17 | Why preferable to complex alternative | Distinct economic story testable with simple calendar splits;
      avoids exotic modeling before the mechanism is shown to exist. |
| 18 | Epistemic classification | REPORTED (behavioral literature) / INFERRED (research direction) / NOT PROVEN. |

### F-2 Relative Value / Temporary Spread Dislocation

| # | Quality-Standard Field | Content |
|---|------------------------|---------|
| 1 | Candidate ID | `CAND-RV-TEMPORARY-SPREAD-001` (NOT HYP_003) |
| 2 | Name | Two-asset relative-value spread dislocation mean reversion |
| 3 | Research family | B. Relative Value / Spread |
| 4 | Economic mechanism | Economically linked assets temporarily diverge (liquidity shock, block trade,
      flow) then converge (doctrine 4/5). |
| 5 | Why an edge could exist | Short-horizon dislocation precedes re-convergence; joint description is stable
      while the dislocation is transient. |
| 6 | Observable variables | Spread/difference of two price series, z-score of spread, volume/liquidity
      imbalance, order-flow proxies. |
| 7 | Expected holding horizon | Intraday-to-days (PROPOSED / NOT YET SEALED). |
| 8 | Expected direction | Fade the dislocation (short wide spread, long tight spread) — pre-specified sign. |
| 9 | Friction / cost | Two-legged costs, both-leg fills, spread + slippage + borrow constraints; very sensitive. |
| 10 | Main failure modes | Divergence is permanent (structural), not temporary; both-leg slippage overwhelms;
      crowding (doctrine 7). |
| 11 | Falsification conditions | Pre-registered co-movement/cointegration window shows dislocations do not
      revert with post-cost net edge > 0. |
| 12 | Confounders | Regime change in the joint relationship; correlated macro shocks. |
| 13 | Required data | Two synchronized asset series + liquidity proxies; no connector exists. |
| 14 | Success | Post-cost net edge > 0 on pre-registered dislocation definitions, stable across regimes. |
| 15 | Terminal failure | Permanent-divergence episodes dominate; net edge <= 0 after costs. |
| 16 | Complexity level | MEDIUM (two series, z-score, both-leg execution model). |
| 17 | Why preferable to complex alternative | Classic simple pair relationship first; no ML until the
      simple spread is shown to behave. |
| 18 | Epistemic classification | REPORTED / INFERRED / NOT PROVEN. |

### F-3 Session-Open EMA Momentum (NASDAQ-100 M5) — EXISTING NOTE

Referenced from `candidates/candidate_ny_open_ema_momentum_nasdaq_m5.md` and reviewed in
`reviews/review_ny_open_ema_momentum_nasdaq_m5.md`.

- **Mechanism:** directional momentum set by first qualifying 5-min candle beyond a fast EMA near the
  NY cash open; momentum continuation family.
- **Epistemic status:** REPORTED (video-sourced mechanics) / NOT PROVEN (no backtest accepted).
- **R1-blocking gaps (from the review):** primary parameters unstated in source — `FAST_EMA_PERIOD`,
  ATR/stop period, session exit rules, fill conventions. Review verdict: **NOT READY FOR R1**;
  candidate variants assessed `TERMINALLY FALSIFIED (0/9)` / `(0/12)` in the review's own
  counterfactual trials. Cannot advance until parameters are determined from first principles
  (no curve-fitting) and the pre-registration contract is met.
- Elements 1-18 of the quality standard are already written in the candidate note; do not duplicate
  here. Falsifiability and cost sensitivity are fully specified there.

### F-4 NY-Open First 5-Min Bar / EMA(12) — EXISTING NOTE

Referenced from `candidates/candidate_ny_open_first5_ema12.md`.

- **Mechanism:** direction of the first 5-min bar after the NY cash open relative to EMA(12);
  event-conditioned intraday signal.
- **Epistemic status:** REPORTED / NOT PROVEN; `UNVALIDATED PROPOSAL — CANDIDATE INTAKE ONLY`.
- **R1-blocking gaps:** same class as F-3 (parameter definitions, exit rules, fill conventions
  unresolved); cannot advance to R1 without first-principles specification. Distinct family from
  HYP_001/HYP_002, but carries zero presumption of validity.
- Quality-standard fields 1-18 are in the existing note.

### F-5 MA / Volatility Regime Filter (single asset)

| # | Quality-Standard Field | Content |
|---|------------------------|---------|
| 1 | Candidate ID | `CAND-REGIME-MA-FILTER-001` (NOT HYP_003) |
| 2 | Name | MA / volatility regime risk filter as an overlay study |
| 3 | Research family | D. Regime Filtering |
| 4 | Economic mechanism | Trend/regime or volatility state conditions whether holding a risky position
      is desirable; framing H0 (no improvement after costs) vs H1 (downside/tail reduction without
      destroying upside), per doctrine 13. |
| 5 | Why an edge could exist | Only a research question, not an assumed edge. Historically asserted in
      REPORTED materials (e.g., MA200 reduces volatility ~60% — NOT INDEPENDENTLY VERIFIED, see
      doctrine 13). |
| 6 | Observable variables | Price (MA), realized/implied volatility, state indicator (trend vs range). |
| 7 | Expected holding horizon | Daily-to-weekly (PROPOSED / NOT YET SEALED). |
| 8 | Expected direction | Regime filter toggles exposure; no directional alpha claimed for the filter itself. |
| 9 | Friction / cost | Filter-induced turnover/whipsaw is a core cost; net edge = filter benefit - whipsaw cost. |
| 10 | Main failure modes | No tail-risk reduction after costs; filter merely delays/amplifies drawdowns;
      effect vanishes out-of-sample (doctrine 7). |
| 11 | Falsification conditions | Pre-registered risk-adjusted metrics show no economically meaningful
      improvement after costs vs. unconditional exposure (H0 retained). |
| 12 | Confounders | Trend persistence regime shifts; volatility clustering; overlapping market regimes. |
| 13 | Required data | Single liquid asset/index daily+ bars; lowest data barrier of all families; no
      connector needed at design stage. |
| 14 | Success | H1 supported: meaningful downside/tail reduction without excessive upside loss, post-cost. |
| 15 | Terminal failure | H0 retained under pre-registered criteria; no post-cost improvement. |
| 16 | Complexity level | LOW (single indicator, two states). |
| 17 | Why preferable to complex alternative | Simplest falsification experiment; matches doctrine
      "simple before complex"; low research difficulty. |
| 18 | Epistemic classification | INFERRED (research direction from REPORTED claims) / NOT PROVEN. |

### F-6 Prediction-Market AI Forecasting + Global Arbitrage — EXISTING NOTE

Referenced from `candidates/candidate_prediction_market_ai_forecasting_kalshi_polymarket.md`.

- **Central questions (kept as open questions, not claims):** can an AI agent identify probabilistic
  mispricing vs. prediction-market consensus; under what verified conditions do cross-market
  discrepancies constitute bounded-risk executable arbitrage.
- **Epistemic status:** UNVALIDATED RESEARCH CANDIDATE / DIRECTION; REPORTED / RESEARCH EVIDENCE;
  NOT PROVEN. **PRICE DISCREPANCY != ARBITRAGE** (doctrine 12).
- **R1-blocking gaps:** no data connector exists and none is authorized; latency / HFT risk noted;
  global arbitrage requires a deterministic referee. Not R1-ready and cannot be made so in this task.
- Quality-standard fields 1-18 are in the existing note.

## 5. Ranking Matrix

Ranking by RESEARCH QUALITY (not profit). `+` = favourable, `-` = unfavourable, `0` = neutral/unknown.

| Dimension | F-1 Flow | F-2 RelVal | F-3 Mom(EMA) | F-4 Mom(5min) | F-5 Regime | F-6 PredMkt |
|---|---|---|---|---|---|---|
| Mechanism clarity | + | + | + | + | 0 | + |
| Testability | + | + | + | + | + | 0 (data blocked) |
| Falsifiability | + | + | + | + | + | + |
| Data availability (no connector now) | 0 | 0 | + | + | + | - |
| Cost realism | 0 | - | 0 | 0 | + | - |
| Parameter parsimony | + | + | - (gaps) | - (gaps) | + | + |
| Robustness potential | 0 | 0 | 0 | 0 | 0 | 0 |
| Leakage risk | 0 | 0 | + | + | + | 0 |
| Overfitting risk | + (calendar splits) | 0 | - (gap-driven) | - (gap-driven) | + | 0 |
| Orthogonality to HYP_001/002 | + | + | + | + | + | + |
| Fresh-inception suitability | + | + | - (blocked) | - (blocked) | ++ | - (blocked) |
| Research difficulty | LOW-MED | MED | LOW | LOW | LOW | HIGH (connectors) |

## 6. Quarantine / Independence Assessment

- **HYP_001 (`HYP_TSMOM_EURUSD_001`, M5):** EURUSD M5 holdout bars 6060-9999
  (window `2026-08-18`..`2026-09-04`) is permanently quarantined. None of F-1..F-6 targets EURUSD,
  and none may reuse that window.
- **HYP_002 (`HYP_TSMOM_EURUSD_HTF_002`, H4):** EURUSD H4 validation/OOS bars 3751-6230
  (window `2023-05-29`..`2024-12-31`) is permanently quarantined. Not reusable by any candidate.
- **No candidate may inherit HYP_001/HYP_002 empirical evidence or optimized parameters.** Prior
  failure knowledge may inform research design; prior empirical evidence may not become new-hypothesis
  evidence.
- All six candidates are conceptually orthogonal to the prior unconditional EURUSD time-series
  momentum families. Orthogonality is a claim of independence in family, **not** a claim of validity.
- Any future candidate that does touch EURUSD must select a data window disjoint from both
  quarantined windows or be rejected by `ResearchReInceptionGate` fail-closed.

## 7. Recommended Candidate(s) for HUMAN REVIEW

Rankings and recommendations here are research-quality judgments, not profit claims, and are
proposals for human decision — they are NOT authorization to register anything.

1. **F-1 (Structural / Forced-Flow calendar effects)** — strongest adherence to doctrine 4/5
   (who is forced, why, what distortion, how long, what observable, what falsifies); distinct
   mechanism; simple calendar splits; freshest inception.
2. **F-5 (MA / volatility regime filter)** — lowest research difficulty, highest falsifiability of a
   weak prior; cleanest H0/H1 framing from doctrine 13; suitable as the first falsification-focused
   experiment.
3. **F-2 (Relative-value spread dislocation)** — good mechanism but two-legged cost sensitivity
   makes it a second-tier first candidate.
4. **F-3 / F-4 (Momentum, existing)** — NOT R1-ready; blocked until first-principles parameter
   specification resolves the 13 reviewed gaps.
5. **F-6 (Prediction-market / global arbitrage)** — preserved as a research direction only; blocked by
   connector/data absence; would become latency/HFT territory.

**Recommended human action:** select exactly one candidate (F-1 and F-5 are the strongest from a
research-quality standpoint) and issue an explicit approval for that candidate before any
`ResearchReInceptionGate` consideration.

## 8. What Must NOT Be Inferred From This Report

- **No hypothesis exists.** HYP_003 remains absent.
- **No candidate is profitable, predictive, or persistent.** Every candidate = REPORTED / INFERRED
  / NOT PROVEN.
- **No parameters are fixed.** All numerics are PROPOSED / NOT YET SEALED and may not be tuned on
  unseen data.
- **No ranking score is a backtest result.** This report contains zero empirical evidence.
- **"Conceptually orthogonal" does not mean "valid",** and does not weaken HYP_001/HYP_002
  quarantine in any way.
- **Selection of a candidate is not authorization.** Only an explicit human decision can move a
  candidate toward the gate.

## 9. Next Governance Step

On explicit human approval of a single candidate:

1. Resolve any specification gaps from first principles (no curve-fitting).
2. Human authorizes invocation of `ResearchReInceptionGate` for that candidate.
3. Run the gate (quarantine intersection, anti-HARKing cardinality, pre-registration completeness).
4. Begin a **fresh independent R1** and only then may hypothesis registration / sealing proceed.

Until that approval, the system remains **RESEARCH STANDING BY**.

---

## VALIDATION SUMMARY

- HYP_003 exists: **NO** (this document creates no hypothesis)
- R1 started: **NO**
- Market data accessed: **NO**
- Broker / MT5 accessed: **NO**
- Backtest / numerical validation: **NONE**
- Slice 1-4 / governance / frozen core / ExecutionCoordinator changes: **NONE**
- Candidates registered/sealed: **NONE**
- Capital: `$0.00`; Trading: **LOCKED**
- This document is a methodology/reference artifact: **REPORTED / INFERRED / NOT PROVEN**