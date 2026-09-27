# RI-07 — Intraday Option Flow

## 1. Intake Status
- Intake status: PROMISING_UNVERIFIED
- Candidate role: Research watchlist
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Signed intraday aggressive option transaction volume (order flow imbalance in options) contains timely informed-flow information that leads price formation in the underlying security.

## 3. Economic / Microstructure Rationale
Informed market participants with short-lived private information often trade in the option market to obtain leverage or conceal intent. Market makers who fill these orders must immediately hedge in the underlying market, creating mechanical price pressure.

## 4. Null Hypothesis
$H_0$: Intraday signed option volume provides zero incremental forecast power for underlying asset price movements beyond underlying equity order flow.

## 5. Alternative Hypothesis
$H_1$: Aggressive call volume buying relative to put volume buying significantly predicts short-horizon underlying price drift over horizons from 5 minutes to end-of-day.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Academic literature on informed option trading and lead-lag dynamics between option order flow and underlying stocks.
- **Preprint / Preliminary**: 2026 preprints analyzing high-frequency OPRA trade imbalances and underlying price impact.
- **Source Claim Only**: Claims by retail services that scanning for "unusual option sweeps" produces instant high-probability directional edges.

## 7. What Existing Evidence Does NOT Support
Literature does NOT support the claim that every large option trade represents directional "smart money". A large fraction of option block volume consists of delta-neutral hedging, volatility trading, or synthetic financing.

## 8. Source Claims That Motivated This Intake
- `SR-17`: MTraders intraday option flow and market-maker reaction narratives.

## 9. Data Requirements
- **Instrument**: Complete OPRA option feeds for US Equities and Index Options.
- **Frequency**: Tick-level trade and quote events.
- **Data Types**: Microsecond timestamps, strike, expiration, premium, trade size, NBBO quotes.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: Direct OPRA feed.
- **Historical Coverage**: Minimum 2 years.
- **Authority Requirements**: Full OPRA consolidated tape data.

## 10. Data Provenance Contract Required Before Empirical Work
Trade-to-quote matching algorithms (e.g., Lee-Ready applied to option quotes) must be formally validated and locked.

## 11. Execution / Friction Requirements
- Executable underlying transaction costs and market impact.
- OPRA data infrastructure costs (massive data volume constraint).

## 12. Confounders
- Complex multi-leg spread trades misclassified as outright directional sweeps.
- Hedging activity by market makers in competing venues.

## 13. Required Negative / Placebo Controls
- Randomly signed option volume control.
- Time-permuted option flow series.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: Completely unresearched within ACASH historical archives.

## 15. Falsification Concept
Falsified if out-of-sample forward underlying returns conditional on signed option flow fail to exceed underlying bid/ask spread costs.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No trade size filters, premium thresholds, or expiration filters are authorized at R0.

## 17. Metrics
Information Coefficient (IC), cumulative trading PnL net of spread, Sharpe Ratio.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Research watchlist.

## 19. Open Questions
- What is the computational and data storage cost of storing and processing tick-level OPRA data?
- Does option flow offer information beyond what is already visible in cash market order flow?

## 20. Next Permitted Action
remain on hold.
