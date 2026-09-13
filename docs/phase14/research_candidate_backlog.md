# ACASH Phase 14 Research Candidate Backlog

**Document ID:** `docs/phase14/research_candidate_backlog.md`
**Status:** NON-GOVERNING RESEARCH BACKLOG
**Authority:** NONE
**Empirical Authorization:** NONE
**Hypothesis Registration:** NONE
**Backtest Authorization:** NONE
**Paper Authorization:** NONE
**Live Authorization:** NONE
**Canonical Context:** `AGENTS.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/architecture/strategy_admission_standard.md`, `docs/architecture/research_architecture.md`, `docs/phase14/research_doctrine.md`, `docs/phase14/research_candidates.md`

---

> [!CAUTION]
> ### RESEARCH GOVERNANCE & EPISTEMIC BOUNDARIES
> - **THIS IS NOT A STRATEGY CATALOG OR FORMAL HYPOTHESIS REGISTRY:** Inclusion in this backlog confers **zero** authority to execute backtests, optimize parameters, compute PnL, or register formal trials.
> - **HYP_003 REMAINS ABSENT:** No backlog item here constitutes `HYP_003`. Formal hypothesis registration requires explicit human authorization through the canonical governance gate.
> - **PRE-EMPIRICAL PLANNING ONLY:** This document exists solely to formulate disciplined, falsifiable scientific research questions *before* historical data is queried or models are fitted.
> - **ACTIVE G7 SOAK UNTOUCHED:** Homelab runtime, soak harnesses, and Docker containers are completely outside the scope of this document.
> - **ZERO CAPITAL / NO TRADING:** Canonical capital is **$0.00**; `NO_REAL_ORDERS=true`.

---

## 1. Backlog Charter & Methodology

### 1.1 Core Purpose
The primary failure mode in quantitative finance is **HARKing** (Hypothesizing After Results are Known) and data snooping: calculating hundreds of indicators, running combinatorial grid searches over parameters, sorting by historical Sharpe ratio or PnL, and back-fitting an economic story to the winning curve.

The ACASH Research Candidate Backlog exists to enforce the exact inverse discipline:
```text
Economic / Behavioral / Structural Question
    ↓
Proposed Mechanism & Plausible Non-Existence Arguments
    ↓
Falsifiable Prediction & Pre-Declared Invalidation Concept
    ↓
Data Requirements & Provenance Verification
    ↓
Baseline Model Definition (Complexity Ladder)
    ↓
[HUMAN PRIORITIZATION & RATIFICATION]
    ↓
Formal Hypothesis Registration (e.g. HYP_###)
    ↓
Sealed Empirical Trial in SearchTrialLedger
```

This document answers: **"What questions are scientifically worth investigating next?"**
It does **NOT** answer: *"What strategy should ACASH trade?"*

### 1.2 Anti-HARKing Invariants
1. **No Numerical Optimization in the Backlog:** Thresholds, entry levels, indicator periods, and stop distances are explicitly omitted from backlog definitions.
2. **Mandatory Mechanism-First Requirement:** A statistical anomaly without a plausible economic, structural, or behavioral mechanism is treated as data mining noise.
3. **Plausibility of Non-Existence:** Every candidate must document why the proposed edge might be an illusion, an artifact of data errors, or already arbitraged away.
4. **Namespace Isolation:** All backlog items are assigned the prefix `RQ-BACKLOG-###`. The formal hypothesis namespace `HYP_###` is strictly protected and cannot be assigned without canonical human governance.

---

## 2. Research Families

Candidates are categorized into disciplined research families:

- **Family A: Time-Series Trend / Momentum:** Persistence of directional price movement across medium to long horizons driven by slow information diffusion, capital re-allocation, or structural flows.
- **Family B: Mean Reversion:** Tendency of asset prices to revert toward local equilibriums after extreme short-term dislocations, forced liquidations, or liquidity voids.
- **Family C: Volatility / Regime Conditioning:** Conditioning baseline signals upon observable macro, volatility, or liquidity states to reduce drawdown during hostile market environments.
- **Family D: Cross-Sectional Relative Strength:** Cross-asset or intra-asset relative ranking based on relative momentum or value, evaluated under strict point-in-time universe controls.
- **Family E: Cross-Asset / Systematic Macro:** Structural state variables derived across multiple asset classes (rates, equity risk, currencies, commodities) to classify broad macro regimes.
- **Family F: Market Microstructure & Liquidity (Future Only):** Order book imbalance, queue dynamics, and spread effects.
  *Infrastructure Note:* High-frequency trading (HFT) and co-located market making are marked **NOT NEAR-TERM PRIORITY** due to homelab hardware and non-colocated network constraints.
- **Family G: Portfolio Construction & Risk Sizing (Future Only):** Risk parity, volatility targeting, and multi-factor allocation methods.

---

## 3. Standard Backlog Item Schema

Each candidate in this backlog must strictly provide:

```text
Candidate ID:               RQ-BACKLOG-###
Working Title:              Descriptive label
Status:                     PROPOSED_RESEARCH_QUESTION
Research Family:            [A / B / C / D / E / F / G]
Research Question:          Precise, falsifiable scientific question
Economic/Behavioral/        Plausible reason the phenomenon occurs in real markets
Structural Mechanism:
Why It Might Exist:         Drivers supporting statistical persistence
Why It Might NOT Exist:     Counter-arguments (arbitrage, data artifact, mining noise)
Primary Market(s):          Target asset(s)
Secondary Market(s):        Cross-market verification assets
Time Horizon:               Intraday (M15-H1) / Multi-Day (H4-D1) / Weekly
Required Data:              Minimum data types
Minimum Data Fields:        OHLCV, Funding, Macro, etc.
Market-Specific Data Risks: Specific failure modes of the asset's data feed
Expected Signal Frequency:  Estimated signal generation rate
Expected Trade Frequency:   Estimated portfolio turnover rate
Potential Cost Sensitivity: Susceptibility to bid-ask spread, slippage, and fees
Known Confounders:          Overlapping factors that could create a false appearance of edge
Likely Failure Modes:       How the candidate is expected to fail empirically
Regimes Where It Might Fail: Hostile market environments
Pre-Empirical Falsification  Conditions under which the hypothesis is rejected before deployment
Concept:
Required Controls:          Mandatory benchmark baselines and statistical splits
Dependencies:               Prerequisite data qualification or architectural milestones
Governance State:           UNRATIFIED_BACKLOG
Human Decisions Needed:     Decisions requiring human approval prior to promotion
```

---

## 4. Core Research Candidates (8 Primary Questions)

### RQ-BACKLOG-001: BTC Medium-Horizon Trend Persistence Following Volatility Expansion
- **Candidate ID:** `RQ-BACKLOG-001`
- **Working Title:** BTC Medium-Horizon Trend Persistence Following Volatility Expansion
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Research Family:** Family A (Time-Series Trend / Momentum)
- **Research Question:** *Does Bitcoin exhibit statistically persistent directional price momentum over medium horizons (e.g. multi-hour to multi-day) following a statistically significant expansion in local volatility, beyond what is explained by drift or broad crypto beta?*
- **Economic / Behavioral / Structural Mechanism:** In crypto asset markets, large volatility expansions frequently reflect institutional capital repositioning, major regulatory/macro developments, or large-scale liquidations. Due to fragmented liquidity, retail FOMO/panic, and slow capital rebalancing, information diffusion is non-instantaneous, creating trending autocorrelations.
- **Why It Might Exist:** Volatility clustering creates persistent trending states; leveraged liquidations cascade sequentially through margin platforms.
- **Why It Might NOT Exist:** Crypto market efficiency has increased dramatically with institutional market makers; volatility expansions often mark local exhaustion (blow-off tops or capitulation bottoms) that revert violently rather than trend.
- **Primary Market(s):** `BTC` (Spot and Perpetual).
- **Secondary Market(s):** `ETH`.
- **Time Horizon:** Medium-Horizon (e.g., 4-hour to daily bar aggregation).
- **Required Data:** Qualified historical M1/M5 OHLCV aggregated to H1/H4; historical funding rates if perpetuals are studied.
- **Minimum Data Fields:** `timestamp_utc`, `open`, `high`, `low`, `close`, `volume`.
- **Market-Specific Data Risks:** Exchange outage spikes during high-volatility events; historical liquidation wick distortion across different venues.
- **Expected Signal Frequency:** Low to Moderate (2 to 6 signals per month).
- **Expected Trade Frequency:** Low (holding periods spanning days to weeks).
- **Potential Cost Sensitivity:** Low to Moderate (longer holding horizons dilute transaction friction).
- **Known Confounders:** Long-term upward crypto beta (2015–2025 structural drift); single-regime bull market dominance; lookback parameter selection bias.
- **Likely Failure Modes:** Severe whipsaws during prolonged sideways/choppy regimes; failure to overcome taker fees during false volatility breakouts.
- **Regimes Where It Might Fail:** Extended range-bound consolidation; low-liquidity summer doldrums; sudden central bank liquidity reversals.
- **Pre-Empirical Falsification Concept:** If post-breakout forward returns exhibit zero positive autocorrelation relative to an unconditioned drift baseline across rolling 6-month windows, reject the mechanism.
- **Required Controls:** Unconditioned simple trend baseline; buy-and-hold benchmark; volatility-regime split; transaction fee stress test.
- **Dependencies:** Qualified historical crypto dataset (`DS-CRYPTO-BTC-M1`).
- **Governance State:** `UNRATIFIED_BACKLOG`
- **Human Decisions Needed:** Minimum holding period definition; venue authority selection.

---

### RQ-BACKLOG-002: Conditional Mean Reversion After Short-Horizon BTC Dislocation
- **Candidate ID:** `RQ-BACKLOG-002`
- **Working Title:** Conditional Mean Reversion After Short-Horizon BTC Dislocation
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Research Family:** Family B (Mean Reversion)
- **Research Question:** *Following extreme short-horizon (e.g. 5-minute to 15-minute) price displacements in Bitcoin, is there statistically significant conditional price reversion after explicitly controlling for prevailing trend direction, volatility regime, and bid-ask spread friction?*
- **Economic / Behavioral / Structural Mechanism:** Extreme short-term price spikes often arise from temporary liquidity vacuums, stop-loss cascades, or forced margin liquidations that temporarily drive the order book far beyond fundamental equilibrium. Once liquidation orders clear, market maker inventory rebalancing and patient resting limit orders absorb the flow, causing prices to mean-revert.
- **Why It Might Exist:** Mechanical market structure limits; forced liquidation market orders consume all top-of-book depth, creating sharp artificial price wicks.
- **Why It Might NOT Exist:** Large price shocks are frequently authentic information events (e.g. ETF approvals, exchange insolvency news, regulatory enforcement); attempting to fade them results in catastrophic run-away trend losses ("catching a falling knife").
- **Primary Market(s):** `BTC` (Perpetual / Spot).
- **Secondary Market(s):** `ETH`.
- **Time Horizon:** Short to Intraday (M5 to M15 bars, holding horizon 15 minutes to 4 hours).
- **Required Data:** High-resolution qualified M1 OHLCV; tick/quote data if available.
- **Minimum Data Fields:** `timestamp_utc`, `open`, `high`, `low`, `close`, `volume`.
- **Market-Specific Data Risks:** Exchange downtime during violent wicks; bid-ask spread blowout during flash crashes preventing realistic execution.
- **Expected Signal Frequency:** Moderate to High (10 to 30 events per month).
- **Expected Trade Frequency:** High.
- **Potential Cost Sensitivity:** Extremely High (vulnerable to spread, taker fees, and adverse slippage).
- **Known Confounders:** Apparent reversion in mid-price that cannot be captured after accounting for bid-ask spread; survivorship of trades that did not blow up.
- **Likely Failure Modes:** Consecutive trend extensions causing catastrophic drawdown; friction consumes entire gross statistical edge.
- **Regimes Where It Might Fail:** Strong macro trend regimes; systemic credit events (e.g., FTX/Luna-style collapse cascades).
- **Pre-Empirical Falsification Concept:** If gross returns fail to cover 2x conservative round-turn fee + spread friction, or if conditional mean reversion vanishes when excluding overnight/weekend hours, reject immediately.
- **Required Controls:** Baseline unconditioned fade; execution lag model (at least 1 bar delay); realistic taker fee and slippage stress tiers.
- **Dependencies:** Qualified high-resolution data foundation with verified execution assumptions.
- **Governance State:** `UNRATIFIED_BACKLOG`
- **Human Decisions Needed:** Minimum dislocation threshold standard; stop-loss boundary governance.

---

### RQ-BACKLOG-003: Volatility & Liquidity Regime-Conditioned Trend vs. Unconditioned Trend Baseline
- **Candidate ID:** `RQ-BACKLOG-003`
- **Working Title:** Volatility & Liquidity Regime-Conditioned Trend vs. Unconditioned Trend Baseline
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Research Family:** Family C (Volatility / Regime Conditioning)
- **Research Question:** *Does conditioning a standard time-series trend model on an objective, pre-declared volatility or volume regime filter yield statistically superior risk-adjusted out-of-sample performance relative to an identical unconditioned trend baseline, after penalizing for additional model complexity?*
- **Economic / Behavioral / Structural Mechanism:** Trend strategies typically incur the majority of their drawdowns during choppy, mean-reverting, low-volatility regimes or during sudden volatility spike reversals. Filtering out hostile regimes or scaling exposure inversely to volatility aims to preserve capital for high-conviction trending environments.
- **Why It Might Exist:** Volatility regimes exhibit strong clustering (Mandelbrot, Engle ARCH); trends operate with higher signal-to-noise ratios during moderate, sustained volatility than in stagnant or chaotic regimes.
- **Why It Might NOT Exist:** Regime classifiers suffer from significant lag (identifying a regime after it has largely played out); filtering frequently eliminates the most profitable early phase of major trends, degrading net terminal wealth.
- **Primary Market(s):** `BTC`, `ES` (Equity Index Futures).
- **Secondary Market(s):** `EURUSD`, `XAU`.
- **Time Horizon:** Multi-Hour to Daily (H1, H4, D1).
- **Required Data:** Qualified historical OHLCV across target markets.
- **Minimum Data Fields:** `timestamp_utc`, `open`, `high`, `low`, `close`, `volume`.
- **Market-Specific Data Risks:** Look-ahead bias in volatility estimator (e.g., using centered rolling windows or unshifted normalization).
- **Expected Signal Frequency:** Low (regime switches occur over weeks or months).
- **Expected Trade Frequency:** Low.
- **Potential Cost Sensitivity:** Low.
- **Known Confounders:** Overfitting regime threshold parameters on in-sample data; regime classifier acting as a disguised post-hoc curve fit.
- **Likely Failure Modes:** False regime transitions generating excessive turnover; missing the single largest trend run of the cycle due to a false "hostile" regime classification.
- **Regimes Where It Might Fail:** Rapid, violent V-shaped market recoveries.
- **Pre-Empirical Falsification Concept:** If the regime-conditioned model fails to achieve a statistically significant improvement in Deflated Sharpe Ratio (DSR) or Minimum Track Record Length (MinTRL) over the unconditioned baseline, the hypothesis is rejected.
- **Required Controls:** **MANDATORY EXPLICIT UNCONDITIONED BASELINE;** ablation test isolating the regime filter; multiple testing haircut.
- **Dependencies:** Canonical Phase 6 DSR/PBO statistical engine; frozen dataset.
- **Governance State:** `UNRATIFIED_BACKLOG`
- **Human Decisions Needed:** Selection of candidate baseline trend formulation (e.g., Simple Moving Average vs. Time-Series Momentum).

---

### RQ-BACKLOG-004: Cross-Asset Macro Risk Regime Identification
- **Candidate ID:** `RQ-BACKLOG-004`
- **Working Title:** Cross-Asset Macro Risk Regime Identification
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Research Family:** Family E (Cross-Asset / Systematic Macro)
- **Research Question:** *Can an orthogonal set of observable cross-asset state variables (spanning equity index momentum, US dollar strength, interest rate slope, and gold relative performance) reliably identify macro risk-on / risk-off regimes that condition the forward return distribution of risk assets?*
- **Economic / Behavioral / Structural Mechanism:** Global asset markets are tightly bound through international balance sheets, institutional risk budgets, and central bank monetary liquidity. Global liquidity contractions typically manifest contemporaneously across the US dollar, sovereign yield curves, and commodities before impacting speculative risk assets.
- **Why It Might Exist:** Institutional risk parity and multi-asset asset managers systematically de-risk across asset classes based on macro volatility triggers, creating transmission spillovers.
- **Why It Might NOT Exist:** Macro relationships are notoriously non-stationary (e.g., equity-bond correlations shift from negative to positive during inflation shocks); macro indicators are often contemporaneous rather than forward-predictive.
- **Primary Market(s):** Multi-Asset (`ES`, `EURUSD`, `XAU`, `BTC`, US Treasury yields).
- **Secondary Market(s):** Broad commodity and sector ETF universe.
- **Time Horizon:** Daily to Weekly (D1, W1).
- **Required Data:** Multi-asset synchronized daily historical price and yield series.
- **Minimum Data Fields:** Synchronous daily close prices, standardized UTC cutoff times.
- **Market-Specific Data Risks:** Non-synchronous closing times across global markets (Tokyo vs. London vs. New York closes creating artificial leads/lags).
- **Expected Signal Frequency:** Very Low (1 to 4 macro state transitions per year).
- **Expected Trade Frequency:** Very Low.
- **Potential Cost Sensitivity:** Negligible.
- **Known Confounders:** Macro regime classification merely acts as a contemporaneous description of past crisis events rather than an ex-ante predictive signal.
- **Likely Failure Modes:** Regime indicator triggers after 80% of the market drawdown has already occurred; regime signals whipsaw during stagflationary periods.
- **Regimes Where It Might Fail:** Structural breaks in monetary policy regimes (e.g. transition from ZIRP to rapid inflation hikes).
- **Pre-Empirical Falsification Concept:** If conditional forward returns across identified risk-on vs. risk-off regimes exhibit overlapping confidence intervals under block bootstrap testing, reject predictive validity.
- **Required Controls:** Static equal-weight benchmark; cash benchmark; strict point-in-time timestamp alignment across global markets.
- **Dependencies:** Cross-asset data ingestion foundation; calendar synchronization engine.
- **Governance State:** `UNRATIFIED_BACKLOG`
- **Human Decisions Needed:** Selection of canonical proxy assets for USD (`DXY` vs. `EURUSD`) and Rates (`10Y Yield` vs. `TLT`).

---

### RQ-BACKLOG-005: Cross-Sectional Relative Strength Persistence in Liquid Universes
- **Candidate ID:** `RQ-BACKLOG-005`
- **Working Title:** Cross-Sectional Relative Strength Persistence in Liquid Universes
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Research Family:** Family D (Cross-Sectional Relative Strength)
- **Research Question:** *Does a point-in-time cross-sectional relative strength ranking across a liquid asset universe exhibit persistent out-of-sample return dispersion between top-quantile and bottom-quantile assets, after eliminating survivorship bias, look-ahead bias, and rebalancing turnover costs?*
- **Economic / Behavioral / Structural Mechanism:** Institutional mandate constraints, benchmark tracking, and capital allocation inertia cause winning assets to receive persistent institutional inflows, while underperforming assets face redemptions, leading to cross-sectional momentum anomalies (Jegadeesh & Titman 1993).
- **Why It Might Exist:** Capital allocation cycles operate over monthly and quarterly timeframes; slow price discovery across cross-sectional peers.
- **Why It Might NOT Exist:** Cross-sectional momentum suffers from severe periodic momentum crashes when beaten-down assets violently rebound; high turnover costs eliminate theoretical paper alpha.
- **Primary Market(s):** Liquid US Sector ETFs or Liquid Crypto Top-20 universe.
- **Secondary Market(s):** Liquid global equity indices.
- **Time Horizon:** Intermediate (Weekly rebalancing, D1 bar inputs).
- **Required Data:** Point-in-time cross-sectional universe data including delistings and constituent changes.
- **Minimum Data Fields:** `timestamp_utc`, `symbol`, `close`, `volume`, `tradable_flag`.
- **Market-Specific Data Risks:** Survivorship bias (evaluating today's winning universe backward in time); illiquid asset inclusion skewing theoretical performance.
- **Expected Signal Frequency:** Weekly / Bi-weekly rebalancing.
- **Expected Trade Frequency:** Moderate.
- **Potential Cost Sensitivity:** High (portfolio rebalancing across multiple assets incurs continuous transaction fees and bid-ask friction).
- **Known Confounders:** Implicit exposure to market beta, size factor, or industry concentration masquerading as idiosyncratic relative strength.
- **Likely Failure Modes:** Severe momentum crash during sudden market inflections; excessive turnover destroying net returns.
- **Regimes Where It Might Fail:** Broad market trend reversals; high-volatility liquidity shocks.
- **Pre-Empirical Falsification Concept:** If the long-short quantile spread is statistically indistinguishable from zero after factoring in conservative turnover friction, reject immediately.
- **Required Controls:** Naive equal-weight universe baseline; market-cap weighted benchmark; point-in-time survivorship bias audit.
- **Dependencies:** Point-in-time cross-sectional data management architecture.
- **Governance State:** `UNRATIFIED_BACKLOG`
- **Human Decisions Needed:** Universe definition criteria (e.g. minimum 30-day median dollar volume threshold).

---

### RQ-BACKLOG-006: Intraday Session Transition & Market Open Dynamics
- **Candidate ID:** `RQ-BACKLOG-006`
- **Working Title:** Intraday Session Transition & Market Open Dynamics
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Research Family:** Family A / F (Market Structure / Session Dynamics)
- **Research Question:** *Are price discovery and volatility expansion behaviors during the initial 30 minutes of major electronic market session opens (e.g. US Cash Open 09:30 EST, London Open 08:00 GMT) structurally distinct from overnight sessions, and can directional persistence be extracted out-of-sample?*
- **Economic / Behavioral / Structural Mechanism:** Market opens represent concentrated periods of inventory rebalancing, overnight order matching, and institutional flow execution. The transition from low-liquidity overnight trading to high-liquidity cash trading forces rapid price adjustment.
- **Why It Might Exist:** Concentrated participation by institutional floor traders and algorithmic market makers during fixed opening auctions.
- **Why It Might NOT Exist:** Market opens are characterized by maximum noise, widest spreads, and high manipulation risk; apparent opening trends frequently reverse completely once morning flows clear.
- **Primary Market(s):** `ES`, `NQ` (Index Futures), `BTC`.
- **Secondary Market(s):** `EURUSD`.
- **Time Horizon:** Intraday (M1 to M5 bars; trades executed within first 60 minutes of session open).
- **Required Data:** Qualified historical M1 bar data with verified exchange timezone normalization.
- **Minimum Data Fields:** `timestamp_utc`, `open`, `high`, `low`, `close`, `volume`.
- **Market-Specific Data Risks:** Daylight Saving Time (DST) misalignments causing 1-hour shifts in session open timestamps; vendor bar timestamp conventions (bar-start vs. bar-end).
- **Expected Signal Frequency:** High (1 signal per trading day per asset).
- **Expected Trade Frequency:** High (daily intraday trading).
- **Potential Cost Sensitivity:** Very High (intraday trades are highly vulnerable to opening spread widening and slippage).
- **Known Confounders:** Data snooping around specific opening minute cutoffs (e.g. optimizing 5-min vs. 15-min open range); single-year regime artifacts.
- **Likely Failure Modes:** Spread widening at the open destroys paper edge; stop-outs from erratic opening auction volatility.
- **Regimes Where It Might Fail:** Non-trending, range-bound macro days with heavy economic releases occurring mid-morning.
- **Pre-Empirical Falsification Concept:** If performance degrades to zero when execution is delayed by 1 bar or when bid-ask spread is widened to 2x historical median opening spread, reject.
- **Required Controls:** Random-entry null model; strict calendar session normalization; fee/spread stress modeling.
- **Dependencies:** Session-aware calendar specification; verified M1 historical data.
- **Governance State:** `UNRATIFIED_BACKLOG`
- **Human Decisions Needed:** Definitive selection of target exchange sessions and calendar definitions.

---

### RQ-BACKLOG-007: Volatility-State Risk Sizing & Signal Gating Utility
- **Candidate ID:** `RQ-BACKLOG-007`
- **Working Title:** Volatility-State Risk Sizing & Signal Gating Utility
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Research Family:** Family C / G (Risk Management / Conditioning)
- **Research Question:** *Does dynamic position sizing scaled inversely to forecasted volatility (e.g., ATR or Parkinson/Garman-Klass volatility estimates) improve long-run risk-adjusted stability and reduce maximum drawdown relative to fixed-notional sizing, without degrading capital efficiency?*
- **Economic / Behavioral / Structural Mechanism:** Asset returns exhibit heteroskedasticity (volatility changes over time, while mean returns are relatively stable). Holding constant dollar positions during high-volatility regimes causes risk exposure and portfolio variance to be dominated by a small number of volatile days.
- **Why It Might Exist:** Volatility clustering allows reliable short-term variance forecasting; equalizing risk contribution per trade prevents single-event catastrophic losses.
- **Why It Might NOT Exist:** Scaling down position size during high-volatility regimes can cause an algorithm to miss the most explosive, highly profitable trending moves; volatility spikes often mark market bottoms where aggressive sizing is rewarded.
- **Primary Market(s):** Cross-Asset (`BTC`, `ES`, `EURUSD`, `XAU`).
- **Secondary Market(s):** Broad portfolio universe.
- **Time Horizon:** All Horizons (M15 to D1).
- **Required Data:** Historical OHLCV series.
- **Minimum Data Fields:** `timestamp_utc`, `open`, `high`, `low`, `close`.
- **Market-Specific Data Risks:** Extreme spikes in illiquid historical data generating artificially tiny position sizes (denominator explosion).
- **Expected Signal Frequency:** Continuous position scaling.
- **Expected Trade Frequency:** Depends on re-sizing tolerance threshold.
- **Potential Cost Sensitivity:** Low to Moderate (frequent rebalancing to target volatility incurs incremental rebalancing costs).
- **Known Confounders:** Testing volatility sizing on in-sample return series where future volatility is implicitly known.
- **Likely Failure Modes:** High turnover from continuous sizing adjustments; whipsawed into tiny positions at the start of major market recoveries.
- **Regimes Where It Might Fail:** Rapid regime transitions from low volatility directly into structural breakouts.
- **Pre-Empirical Falsification Concept:** If volatility-scaled sizing produces higher maximum drawdown or lower Sharpe ratio than fixed-notional sizing across an untouched OOS dataset, reject the sizing rule.
- **Required Controls:** Fixed-notional baseline sizing; unscaled baseline strategy; transaction turnover penalty.
- **Dependencies:** Portfolio architecture and position sizing engine.
- **Governance State:** `UNRATIFIED_BACKLOG`
- **Human Decisions Needed:** Ratification of candidate volatility estimators (e.g. ATR vs. Realized Volatility vs. Parkinson).

---

### RQ-BACKLOG-008: Multi-Horizon Trend Agreement Incremental Information Value
- **Candidate ID:** `RQ-BACKLOG-008`
- **Working Title:** Multi-Horizon Trend Agreement Incremental Information Value
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Research Family:** Family A (Time-Series Trend / Multi-Timeframe)
- **Research Question:** *Does requiring directional trend agreement across multiple distinct time horizons (e.g., H1, H4, D1) provide statistically significant incremental risk-adjusted return over the single strongest standalone horizon baseline, after penalizing for additional parameter degrees of freedom?*
- **Economic / Behavioral / Structural Mechanism:** Market participants operate across distinct investment horizons (intraday market makers, swing traders, institutional asset allocators). When trend direction aligns across short, medium, and long horizons, selling pressure is minimized, creating lower-friction trending paths.
- **Why It Might Exist:** Alignment of diverse participant classes creates unidirectional order flow imbalances.
- **Why It Might NOT Exist:** Multi-horizon filtering introduces severe lag; by the time the longest horizon confirms the trend, the move is often mature and prone to reversal. It frequently acts as a redundant parameter multiplier without adding genuine orthogonal information.
- **Primary Market(s):** `BTC`, `ES`.
- **Secondary Market(s):** `EURUSD`, `XAU`.
- **Time Horizon:** Multi-Horizon (combining intraday and daily).
- **Required Data:** Synchronous multi-timeframe OHLCV data.
- **Minimum Data Fields:** Multi-timeframe OHLCV series.
- **Market-Specific Data Risks:** Look-ahead leakage across timeframe boundaries (e.g., referencing a daily bar close before the day has officially closed).
- **Expected Signal Frequency:** Low to Moderate.
- **Expected Trade Frequency:** Low.
- **Potential Cost Sensitivity:** Low.
- **Known Confounders:** Multiple testing bias across timeframe combinations (testing 10 combinations and selecting the best performing); redundant collinear signals.
- **Likely Failure Modes:** Entering trends at the exact exhaustion point; missing fast-moving trades due to sluggish higher-timeframe confirmation.
- **Regimes Where It Might Fail:** Mean-reverting, oscillating sideways markets.
- **Pre-Empirical Falsification Concept:** If an incremental complexity test (Ablation testing & MinTRL comparison) shows that multi-horizon agreement does not significantly exceed the standalone single-horizon baseline, reject the multi-horizon requirement.
- **Required Controls:** **MANDATORY SINGLE-HORIZON BASELINE;** strict point-in-time bar completion enforcement; multiple testing penalty (Deflated Sharpe Ratio).
- **Dependencies:** Multi-timeframe bar synchronization engine.
- **Governance State:** `UNRATIFIED_BACKLOG`
- **Human Decisions Needed:** Authorization of permissible timeframe combinations.

---

## 5. Grounded Candidate Extensions (Optional 4 Questions)

Grounded directly in existing repository research references (`docs/phase14/research_candidates.md`, `candidate_f1_flow_calendar_rebalance_review.md`, `mec_0011_gold_dxy_relative_movement_intake.md`):

### RQ-BACKLOG-009: Perpetual Futures Funding Rate Carry & Basis Dislocation
- **Candidate ID:** `RQ-BACKLOG-009`
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Family:** Family B / E (Carry / Relative Value)
- **Research Question:** *Do extreme positive or negative deviations in perpetual futures funding rates predict forward spot-perpetual basis mean reversion, and can a market-neutral carry position capture this spread net of borrowing and transaction friction?*
- **Mechanism:** Leveraged speculators pay funding premiums to maintain long exposure during euphoric bull phases; structural carry arbitrageurs harvest this premium until basis contracts.
- **Confounder:** Sudden exchange insolvency risk, margin liquidation risk, basis widening during panic events.
- **Dependencies:** Synchronized historical funding rate and spot-perp historical database.

### RQ-BACKLOG-010: Month-End / Quarter-End Calendar Forced Rebalancing Flows
- **Candidate ID:** `RQ-BACKLOG-010` (Directly grounded in candidate `F-1`)
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Family:** Family A (Structural / Forced Flow)
- **Research Question:** *Do predictable fixed-date institutional portfolio rebalancing flows (e.g. month-end equity/bond rebalancing or benchmark index reconstitutions) generate statistically observable directional price drift in benchmark equity index futures (`ES`) prior to market close?*
- **Mechanism:** Defined-benefit pension funds and target-date retirement funds must mechanically rebalance to fixed asset-allocation weights (e.g. 60/40) at month-end.
- **Confounder:** Algorithmic front-running by market makers eroding price drift days in advance; calendar artifacts.
- **Dependencies:** CME equity index historical data; calendar flow schedule.

### RQ-BACKLOG-011: Intermarket Gold vs. Currency Real Yield Dislocation
- **Candidate ID:** `RQ-BACKLOG-011` (Directly grounded in candidate `MEC-0011`)
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Family:** Family E (Cross-Asset Relative Value)
- **Research Question:** *Does the relative rate-of-change between Gold (`XAU`) and the US Dollar index (`DXY`/`EURUSD`) predict forward macro trend regime changes when conditioned on real interest rate shifts?*
- **Mechanism:** Gold represents a non-yielding monetary asset whose opportunity cost is governed by US real yields; divergence between gold and the dollar reflects shifts in global sovereign risk sentiment.
- **Confounder:** Structural shifts in central bank gold purchasing independent of FX markets.
- **Dependencies:** Synchronized gold, FX, and US Treasury yield historical series.

### RQ-BACKLOG-012: Macro Yield Curve Slope Conditioning on Broad Market Returns
- **Candidate ID:** `RQ-BACKLOG-012`
- **Status:** `PROPOSED_RESEARCH_QUESTION`
- **Family:** Family E (Macro / Rates Conditioning)
- **Research Question:** *Does the slope and curvature of the US Treasury yield curve (e.g. 10Y minus 2Y spread) provide robust forward conditioning on the drawdown risk and volatility regime of equity index futures?*
- **Mechanism:** Yield curve inversions reflect tight monetary conditions and future economic deceleration, reducing corporate earnings growth and expanding equity risk premia.
- **Confounder:** Prolonged lead times (12 to 24 months) making statistical sample sizes extremely small ($N < 5$ recessions in modern data).
- **Dependencies:** FRED daily interest rate series (`DGS10`, `DGS2`).

---

## 6. Prioritization Framework & Proposed Queue

Candidates must be prioritized qualitatively rather than via fabricated quantitative scores.

### 6.1 Evaluation Dimensions (Qualitative Scale: HIGH / MEDIUM / LOW / UNKNOWN)
- **Data Availability:** Can qualified, high-integrity historical data be acquired readily without prohibitive commercial licensing costs?
- **Data Authority Clarity:** Are venue, timezone, adjustment, and roll semantics unambiguous?
- **Economic Mechanism Clarity:** Is there a credible, documented structural or behavioral reason for edge existence?
- **Implementation Simplicity:** Can the baseline model be formulated cleanly with minimal parameters?
- **Cost Observability:** Are fees, spreads, and execution frictions directly observable from market structure?
- **Falsifiability:** Can the hypothesis be rejected with clear, objective statistical hurdles?
- **Sample Availability:** Does historical data span multiple distinct regimes with sufficient degrees of freedom?
- **Overfitting Risk:** How vulnerable is the model to parameter tuning and multiple testing bias?

### 6.2 Proposed Queue Tiers

```text
TIER 1 (Immediate Research Pipeline Following Data Qualification)
├── RQ-BACKLOG-001: BTC Medium-Horizon Trend Persistence (High data availability, clear baseline)
├── RQ-BACKLOG-002: Conditional Mean Reversion After Short-Horizon Moves (Structural flow, highly falsifiable)
└── RQ-BACKLOG-003: Volatility/Regime Conditioned Trend vs. Baseline (Tests core regime thesis against simple baseline)

TIER 2 (Secondary Cross-Asset & Risk Management Queue)
├── RQ-BACKLOG-007: Volatility-State Risk Sizing & Signal Gating (Infrastructure reusability, essential risk architecture)
├── RQ-BACKLOG-004: Cross-Asset Macro Risk Regime Identification (Foundational macro understanding)
└── RQ-BACKLOG-005: Cross-Sectional Relative Strength Persistence (Requires point-in-time universe controls)

TIER 3 (Advanced / Data-Intensive & Complex Flow Queue)
├── RQ-BACKLOG-008: Multi-Horizon Trend Agreement (High risk of redundancy; requires strict baseline controls)
├── RQ-BACKLOG-009: Perpetual Funding Carry & Basis Dislocation (Requires specialized synchronous funding data)
├── RQ-BACKLOG-010: Month-End Calendar Forced Rebalancing (Requires deep futures calendar data)
├── RQ-BACKLOG-011: Intermarket Gold vs. Dollar Relative Value (Requires multi-asset synchronization)
└── RQ-BACKLOG-012: Macro Yield Curve Slope Conditioning (Long horizons, very low sample degrees of freedom)
```

> [!IMPORTANT]
> **GOVERNANCE STATUS: PROPOSED PRIORITIZATION ONLY.**
> Promotion of any candidate from this backlog into a formal research plan requires explicit human governance approval.

---

## 7. Baseline-First Complexity Ladder

A core doctrine of ACASH research is that **complexity must earn its admission**:

| Candidate Family | Mandatory Benchmark Baseline | Requirement for Complexity Admission |
| :--- | :--- | :--- |
| **Regime-Conditioned Model** | Identical unconditioned baseline model (e.g. plain SMA or raw momentum). | Must prove statistically significant increase in DSR and lower MaxDD after complexity penalty. |
| **Multi-Horizon Model** | Standalone single-horizon baseline model. | Must prove incremental information value beyond the single dominant horizon. |
| **Cross-Sectional Model** | Naive equal-weight universe portfolio / simple median-split benchmark. | Must demonstrate net outperformance after accounting for rebalancing turnover drag. |
| **Intraday Session Model** | 24-hour unconditioned baseline / random-entry timing benchmark. | Must prove opening 30-minute window yields higher Sharpe net of opening spread widening. |
| **Directional Alpha Model** | Passive Buy-and-Hold / Cash Risk-Free rate ($0.00$). | Must outperform cash after all transaction costs, slippage, and drawdown stress. |

---

## 8. Pre-Empirical Failure Taxonomy

When research candidates are eventually authorized and tested, empirical outcomes must be classified into authoritative failure categories. Research failure is valid scientific progress:

1. **`NO_EFFECT`:** In-sample return distribution shows zero statistical divergence from null hypothesis.
2. **`FAILED_OOS`:** Strategy demonstrates positive performance in-sample but fails completely on untouched out-of-sample partition.
3. **`FAILED_UNDER_COSTS`:** Gross statistical edge exists, but net returns turn negative under realistic transaction fees, spread, and slippage.
4. **`REGIME_CONCENTRATED`:** Apparent performance is entirely concentrated in a single historical regime (e.g., 2017 crypto bull run) and fails in all other periods.
5. **`PARAMETER_FRAGILE`:** Small perturbations in lookback periods or entry thresholds cause severe performance collapse (cliff-edge overfitting).
6. **`DATA_INADEQUATE`:** Dataset lacks sufficient resolution, historical depth, or degrees of freedom ($T_{\text{eff}} < \text{MinTRL}$) to draw statistically valid conclusions.
7. **`MECHANISM_UNSUPPORTED`:** Empirical evidence directly contradicts the hypothesized behavioral or economic mechanism.
8. **`DUPLICATE_OF_EXISTING_FACTOR`:** Strategy adds zero incremental Sharpe ratio over a simple, known market factor (beta or basic momentum).
9. **`INSUFFICIENT_SAMPLE`:** Total independent trades or opportunity events are too sparse to reject the null hypothesis at target significance levels.

---

## 9. Data Dependency Matrix

| Candidate ID | Target Market | Timeframe | OHLCV | Bid/Ask | Tick Trades | Order Book | Macro / Yields | Corporate Actions | Futures Rolls | Funding Rates | Calendar Sched. | Target Coverage |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **RQ-BACKLOG-001** | `BTC` | H1/H4 | **REQUIRED** | OPTIONAL | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | OPTIONAL | NOT_REQ | 2 to 4 Years |
| **RQ-BACKLOG-002** | `BTC` | M1/M5 | **REQUIRED** | **REQUIRED** | OPTIONAL | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | 1 to 2 Years |
| **RQ-BACKLOG-003** | `BTC`, `ES` | H1/D1 | **REQUIRED** | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | OPTIONAL | NOT_REQ | NOT_REQ | 4+ Years |
| **RQ-BACKLOG-004** | Cross-Asset | D1 | **REQUIRED** | NOT_REQ | NOT_REQ | NOT_REQ | **REQUIRED** | NOT_REQ | OPTIONAL | NOT_REQ | **REQUIRED** | 5 to 10 Years |
| **RQ-BACKLOG-005** | Equities/Crypto | D1 | **REQUIRED** | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | **REQUIRED** | NOT_REQ | NOT_REQ | **REQUIRED** | 5+ Years |
| **RQ-BACKLOG-006** | `ES`, `BTC` | M1/M5 | **REQUIRED** | **REQUIRED** | OPTIONAL | NOT_REQ | NOT_REQ | NOT_REQ | OPTIONAL | NOT_REQ | **REQUIRED** | 2+ Years |
| **RQ-BACKLOG-007** | Cross-Asset | M15 to D1 | **REQUIRED** | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | OPTIONAL | NOT_REQ | NOT_REQ | 4+ Years |
| **RQ-BACKLOG-008** | `BTC`, `ES` | M15/H1/D1 | **REQUIRED** | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | OPTIONAL | NOT_REQ | NOT_REQ | 3+ Years |
| **RQ-BACKLOG-009** | `BTC-PERP` | H1/H8 | **REQUIRED** | OPTIONAL | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | **REQUIRED** | NOT_REQ | 2 to 4 Years |
| **RQ-BACKLOG-010** | `ES` | M5/M15 | **REQUIRED** | OPTIONAL | NOT_REQ | NOT_REQ | NOT_REQ | NOT_REQ | **REQUIRED** | NOT_REQ | **REQUIRED** | 5+ Years |
| **RQ-BACKLOG-011** | `XAU`, `EURUSD` | D1 | **REQUIRED** | NOT_REQ | NOT_REQ | NOT_REQ | **REQUIRED** | NOT_REQ | OPTIONAL | NOT_REQ | **REQUIRED** | 5 to 10 Years |
| **RQ-BACKLOG-012** | `ES`, Yields | D1/W1 | **REQUIRED** | NOT_REQ | NOT_REQ | NOT_REQ | **REQUIRED** | NOT_REQ | OPTIONAL | NOT_REQ | **REQUIRED** | 10+ Years |

---

## 10. Open Human Decisions Register (Research Backlog)

| Decision ID | Decision Subject | Context | Candidate Alternatives | Status | Human Ratification Required? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RES-DEC-001** | First Research Candidate for Formal Promotion | Select which single candidate from Tier 1 should be formulated for formal hypothesis intake after data qualification. | `RQ-BACKLOG-001` (BTC Trend) vs. `RQ-BACKLOG-002` (BTC Reversion) vs. `RQ-BACKLOG-003` (Regime Trend). | **UNRESOLVED** | **YES** |
| **RES-DEC-002** | Initial Historical Research Universe Boundary | Define the initial empirical testing universe scope. | Crypto-only (`BTC`, `ETH`) vs. Multi-Asset Core (`BTC`, `ES`, `EURUSD`, `XAU`). | **UNRESOLVED** | **YES** |
| **RES-DEC-003** | Minimum Trade Count Guidance for Backlog Feasibility | Set qualitative heuristic for exploratory feasibility screening. | 100 trades vs. 300 trades vs. 500 trades minimum sample. | **UNRESOLVED** | **YES** |
| **RES-DEC-004** | Benchmark Asset Authority for Crypto Beta | Select standard buy-and-hold benchmark against which crypto excess returns are measured. | Spot BTC-USDT vs. Equal-Weight Top 10 Index. | **UNRESOLVED** | **YES** |

---

## 11. Governance Verification Ledger

- **Implementation Status:** DOCUMENTATION & RESEARCH PLANNING ONLY (NO CODE MUTATIONS).
- **Hypothesis Creation:** `HYP_003` IS ABSENT / NOT CREATED.
- **Backtest / Empirical Execution:** STRICTLY PROHIBITED / NONE EXECUTED.
- **Active G7 Soak Interaction:** ZERO TOUCH / 100% UNTOUCHED.
- **Existing Candidates Altered:** NO (`F-1`, `MEC-0011`, `MEC-0013` preserved intact).
- **Canonical Capital:** $0.00 (`NO_REAL_ORDERS=true`).
