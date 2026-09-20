# MEC-0015: Profitability-First Intraday Momentum Strategy Research Intake

**Mechanism ID:** `MEC-0015`  
**Mechanism Name:** Noise-Area Intraday Momentum Strategy Replication  
**Target Instrument:** `SPY` (SPDR S&P 500 ETF Trust)  
**Target Timeframe:** 1-minute Regular Trading Hours (RTH) OHLCV  
**Strategic Research Objective:** `NET_ECONOMIC_PERFORMANCE_AFTER_REALISTIC_FRICTION`  
**Classification:** `STRATEGY_NATIVE_EXECUTABLE_REPLICATION_CANDIDATE`  
**Current Governance State:** `RESEARCH_INTAKE_ONLY`  

> [!IMPORTANT]
> **Governance & Authority Boundary:**
> - `MEC-0015` is an external literature intake and strategy-native specification candidate ONLY.
> - `HYP_005` is **NOT CREATED**.
> - Empirical candidate backtesting is **NOT STARTED**.
> - New market data access is **ZERO** (No Alpaca queries, no historical tick/bar fetching).
> - 2023–2026 market observations remain **NOT ACCESSED** and strictly sealed.
> - Paper trading authority is **NOT AUTHORIZED** (`false`).
> - Live trading authority is **LOCKED** (`false`).
> - Capital allocation authority remains **$0.00**.
> - Execution invariant: `NO_REAL_ORDERS = true`.
> - This intake does NOT classify the strategy as accepted, qualified, profitable, or investable.

---

## 1. Mechanism Identity & Strategic Objective

The overarching objective of the ACASH Phase 15 research line is:
$$\mathbf{DISCOVER\_AND\_VALIDATE\_A\_TRADING\_MECHANISM\_WITH\_POSITIVE\_NET\_ECONOMIC\_PERFORMANCE\_AFTER\_REALISTIC\_FRICTION}$$

Unlike econometric predictive lines (such as `MEC-0014A` / `HYP_004`), which evaluated whether the slope coefficient $\beta$ in a predictive return regression was statistically distinguishable from zero ($p < 0.05$), `MEC-0015` is formulated as a **strategy-native executable mechanism**. A candidate hypothesis within this family can only be qualified by proving tradeable economic profitability after deducting all explicit commissions, bid-ask spread crossing, market impact, slippage, and execution latencies.

---

## 2. External Evidence Record (Literature Layer)

All statements in this section represent external literature claims, **NOT** empirical facts verified or reproduced by ACASH.

- **Primary Source:**  
  Zarattini, Carlo; Aziz, Andrew; Barbon, Andrea.  
  *"Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)"*  
  SSRN Working Paper 4824172 / Swiss Finance Institute Research Paper Series No. 24-97 (May 2024).
- **Reported Underlying Asset:** SPDR S&P 500 ETF Trust (`SPY`).
- **Reported Source Data:** 1-minute regular-session OHLCV bars sourced from IQFeed over the sample period May 2007 through April 2024.
- **Core Concept (Noise Area):**
  The authors define an intraday "Noise Area" representing the typical price variation of SPY during the trading day, measured as the trailing 14-day rolling average of absolute open-to-timestamp percentage moves.
- **Reported Strategy Mechanics:**
  1. Calculate intraday Noise Area boundaries dynamically for each minute using a 14-day trailing lookback of same-time-of-day moves.
  2. Adjust upper and lower boundaries for overnight gap behavior between prior 16:00 close and today's 09:30 open.
  3. Restrict trading entry/reversal decisions to 30-minute discrete epochs ($HH:00$ and $HH:30$).
  4. Establish long exposure when price exceeds the upper Noise Area boundary; establish short exposure when price falls below the lower boundary.
  5. Employ an intraday trailing stop using the combination of the Noise Area boundary and the session Volume-Weighted Average Price (VWAP).
  6. Force liquidation of all open positions at market close (16:00 EST); strictly zero overnight exposure.
  7. Apply dynamic volatility sizing targeting 2% daily volatility, capped at a maximum leverage of 4.0×.
- **Reported Literature Friction Model:**
  - Broker Commission: $\$0.0035$ per share.
  - Slippage: $\$0.0010$ per share.
- **Reported Full Strategy Performance (May 2007 – April 2024):**
  - Total Cumulative Return: $\approx 1,985\%$
  - Annualized Return (CAGR): $\approx 19.6\%$
  - Annualized Volatility: $\approx 14.3\%$
  - Sharpe Ratio: $\approx 1.33$
  - Maximum Drawdown: $\approx 25.0\%$
- **Classification:** `LITERATURE_REPORTED_RESULTS`.

---

## 3. Independent Replication & Decay Evidence

A critical prerequisite for ACASH intake is auditing independent post-publication replication attempts. The literature family for Zarattini et al. presents compelling initial historical replication alongside notable recent decay signals:

- **Replication A (Public Independent Python Replication / GitHub, Paz Sheimy, 2024–2026):**
  - Successfully reproduced historical in-sample performance (May 2007 – April 2024) with a reported Sharpe ratio of $\approx 1.34$, closely corroborating the paper's primary findings.
  - Extended the evaluation out-of-sample (OOS) from May 2024 to March 2026.
  - **OOS Result:** Annualized Sharpe ratio dropped precipitously to $\approx 0.39$, underperforming SPY buy-and-hold over the same window.
  - Concluded that the edge decayed substantially post-publication.
- **Replication B (Cross-Asset & Parameter Stability Evaluation, 2025–2026):**
  - Replicated the strategy on SPY ETF and E-mini S&P 500 futures (`ES`).
  - Corroborated historical in-sample Sharpe around $\approx 1.11$ to $1.15$ with standard execution assumptions.
  - Observed severe edge compression starting around 2025.
  - Demonstrated that simple walk-forward parameter optimization or re-tuning did not robustly restore the decaying edge.
- **Classification:** `EXTERNAL_REPLICATION_EVIDENCE_MIXED_WITH_RECENT_EDGE_DECAY`.

> [!WARNING]
> **Scientific Implication:**  
> The presence of published edge degradation does NOT mean the mechanism should be rejected ex-ante without testing. Rather, it serves as explicit evidence that **the mechanism is vulnerable to post-publication alpha decay**. This requires any future ACASH test protocol to enforce strict out-of-sample partitioning, rigorous friction stress-testing, and zero data leakage.

---

## 4. Noise Area Mathematical Contract (Literature Layer)

For trading day $t$ and regular-session time $HH:MM$ (where $HH:MM \in [09:30, 16:00]$):

### 4.1. Historical Move Magnitude
For each of the preceding $i = 1, \dots, 14$ completed trading days:
$$\text{move}[t-i, HH:MM] = \left| \frac{\text{Close}[t-i, HH:MM]}{\text{Open}[t-i, 09:30]} - 1 \right|$$

### 4.2. Time-Specific Expected Volatility ($\sigma$)
$$\sigma[t, HH:MM] = \frac{1}{14} \sum_{i=1}^{14} \text{move}[t-i, HH:MM]$$

### 4.3. Gap-Aware Price Anchor & Boundaries
The anchor price adjusts for the direction and magnitude of the overnight gap:
$$\text{UpperAnchor}[t] = \max(\text{Open}[t, 09:30], \text{Close}[t-1, 16:00])$$
$$\text{LowerAnchor}[t] = \min(\text{Open}[t, 09:30], \text{Close}[t-1, 16:00])$$

The upper and lower boundaries of the Noise Area at timestamp $HH:MM$ are:
$$\text{UpperBand}[t, HH:MM] = \text{UpperAnchor}[t] \cdot (1 + \sigma[t, HH:MM])$$
$$\text{LowerBand}[t, HH:MM] = \text{LowerAnchor}[t] \cdot (1 - \sigma[t, HH:MM])$$

- **Lookback Parameter:** 14 trading days.
- **Band Multiplier:** $1.0$.
- **Classification:** `LITERATURE_EXPLICIT_OR_DIRECTLY_RECONSTRUCTED_FROM_METHODOLOGY_TEXT`.

---

## 5. Entry Contract (Literature Layer)

1. **Observation Epochs:**  
   Trading decisions are evaluated strictly at 30-minute intervals:
   $$\{10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30\}$$
   The first eligible evaluation occurs at 10:00 EST (after the initial 30-minute opening range).
2. **Directional Condition:**
   - If $\text{Price}[t, HH:MM] > \text{UpperBand}[t, HH:MM] \implies \mathbf{LONG}$
   - If $\text{Price}[t, HH:MM] < \text{LowerBand}[t, HH:MM] \implies \mathbf{SHORT}$
   - If $\text{LowerBand}[t, HH:MM] \le \text{Price}[t, HH:MM] \le \text{UpperBand}[t, HH:MM] \implies \mathbf{FLAT / NEUTRAL}$
3. **Open Semantic Items:**
   - `ENTRY_PRICE_FIELD`: Literature references the 30-minute interval, but does not explicitly distinguish between the 30-minute bar's Close vs. the subsequent bar's Open vs. the prevailing midpoint quote.
   - Status: `OPEN_BLOCKER` (must be frozen ex-ante before hypothesis registration).

---

## 6. Exit & Trailing Stop Contract (Literature Layer)

1. **Trailing Stop Mechanics (Refined Model):**  
   The refined strategy incorporating session VWAP establishes dynamic trailing barriers:
   - For an existing **Long** position:
     $$\text{LongStopLevel}[t, HH:MM] = \max(\text{UpperBand}[t, HH:MM], \text{VWAP}[t, HH:MM])$$
     A long position exits if $\text{Price}[t, HH:MM] < \text{LongStopLevel}[t, HH:MM]$.
   - For an existing **Short** position:
     $$\text{ShortStopLevel}[t, HH:MM] = \min(\text{LowerBand}[t, HH:MM], \text{VWAP}[t, HH:MM])$$
     A short position exits if $\text{Price}[t, HH:MM] > \text{ShortStopLevel}[t, HH:MM]$.
2. **Position Reversal (Flip):**  
   If an exit condition is met and the price simultaneously satisfies the opposite directional entry rule, a position reversal occurs.
3. **Forced End-of-Day (EOD) Flat:**  
   All open positions must be fully closed by 16:00 EST. No overnight inventory is permitted.
4. **Open Semantic Items:**
   - Stop evaluation frequency: Methodology text specifies semi-hourly checks; continuous 1-minute stop monitoring was not the primary canonical paper specification.
   - Auction vs. Continuous Exit: Exact timestamp for EOD liquidation (e.g. 15:59 continuous vs 16:00 closing cross).
   - Status: `OPEN_BLOCKER`.

---

## 7. VWAP Contract & Provider Sensitivity

1. **Session Scope:**  
   $$\text{VWAP\_SESSION} = \text{REGULAR\_TRADING\_HOURS\_ONLY (09:30–16:00 EST)}$$
2. **Mathematical Definition:**
   $$\text{VWAP}[t, \tau] = \frac{\sum_{k=1}^{\tau} P_k \cdot V_k}{\sum_{k=1}^{\tau} V_k}$$
   where $P_k$ is the bar representative price and $V_k$ is the bar trading volume.
3. **Sensitivity & Open Items:**  
   External replication audits demonstrate that differences in VWAP computation (e.g., bar Close vs. Typical Price $(H+L+C)/3$ vs. tick-level SIP VWAP) materially alter trade execution and trailing stop triggers.
4. **Status:** `VWAP_EXACT_PROVIDER_MAPPING = OPEN_BLOCKER`.

---

## 8. Dynamic Volatility Sizing Contract

1. **Target Volatility:**
   $$\text{DAILY\_VOL\_TARGET} = 2.0\% \quad (\sigma_{\text{target}} = 0.02)$$
2. **Historical Realized Volatility ($\sigma_{\text{SPY}, t}$):**
   Calculated from the sample standard deviation of SPY daily returns over the preceding 14 trading days:
   $$\sigma_{\text{SPY}, t} = \sqrt{\frac{1}{13} \sum_{j=1}^{14} (R_{t-j} - \bar{R}_t)^2}$$
3. **Exposure Multiplier ($L_t$):**
   $$L_t = \min\left(4.0, \frac{\sigma_{\text{target}}}{\sigma_{\text{SPY}, t}}\right)$$
   Maximum allowable strategy leverage is strictly capped at $4.0\times$.
4. **Nominal Share Allocation:**
   $$\text{Shares}_t = \frac{\text{AUM}_{t-1} \cdot L_t}{\text{Price}_t}$$
5. **ACASH Invariant Notice:**  
   This formula represents an abstract replication specification. ACASH sovereign capital authority remains `$0.00` and `NO_REAL_ORDERS = true`.
6. **Open Semantic Items:** Simple vs. log daily returns; dividend/split adjustment of historical returns; share rounding policy; portfolio cash buffer.

---

## 9. Friction & Transaction Cost Contract

1. **Literature Model:**
   - Broker Commission: $\$0.0035$ / share
   - Execution Slippage: $\$0.0010$ / share
2. **ACASH Realistic Friction Requirement:**  
   The literature friction model assumes extremely low execution drag that may not reflect real retail or institutional prime-brokerage conditions. ACASH requires an independent, conservative friction contract:
   - Commission schedule (per-share or per-dollar).
   - Full bid-ask spread crossing penalty.
   - SEC section 31 fees & FINRA TAF on sell legs.
   - Short borrowing cost / locate fees for short legs.
   - Market-impact / liquidity-tier degradation for sizing.
3. **Status:** `ACASH_REALISTIC_FRICTION_MODEL = OPEN_BLOCKER`.

---

## 10. Data Contract Requirements

To execute a strategy-level backtest or paper simulation, the following data feeds must be formally qualified:
1. **1-Minute RTH OHLCV Bars:** Unadjusted and corporate-action-adjusted intraday bars for SPY from 09:30 to 16:00 EST.
2. **Daily Close / Open History:** At least 14 days of warmup data prior to any simulated trade date.
3. **Official Exchange Calendars:** Explicit identification of half-days, early closes, and holidays.
4. **Trade Execution Quotes:** National Best Bid and Offer (NBBO) or executable minute snapshots.
5. **Status:** `ALPACA_MAPPING = NOT_YET_QUALIFIED_FOR_MEC_0015`. No data may be queried during this phase.

---

## 11. Early-Close Days Policy

US equity markets operate shortened sessions (closing at 13:00 EST) on specific dates (e.g. day after Thanksgiving, Christmas Eve).
- The literature methodology is silent on early-close handling.
- ACASH Policy Options:
  1. Full exclusion of early-close sessions from evaluation.
  2. Shortened-session protocol (adjusting trailing stops and forced exit to 13:00 EST).
- **Status:** `EARLY_CLOSE_POLICY = OPEN_BLOCKER`.

---

## 12. Strategy Degrees of Freedom & Anti-HARKING

To prevent parameter overfitting, the baseline replication candidate fixes all degrees of freedom to the original literature specification:
- Lookback Period: $N = 14$ days
- Noise Multiplier: $M = 1.0$
- Decision Interval: $\Delta t = 30$ minutes
- Daily Volatility Target: $2.0\%$
- Leverage Cap: $4.0\times$
- Trailing Stop: Noise Band + VWAP
- Exit: Forced Flat at 16:00 EST
- Search Space Cardinality: $K = 1$ (Single baseline specification).

No parameter tuning, grid searches, or alternative thresholds are authorized.

---

## 13. Anti-Overfitting & Post-Publication Optimization Evidence

Subsequent academic and practitioner work (e.g. Maróy, 2025) has explored optimizing the Noise Area parameters, reporting Sharpe ratios exceeding $3.0$ on in-sample data. However, independent replications indicate that optimized parameter vectors suffer severe out-of-sample fragility.
- **ACASH Policy:** `POST_PUBLICATION_PARAMETER_OPTIMIZATION_EVIDENCE` is explicitly excluded from baseline intake. The baseline candidate must evaluate the original fixed literature configuration before any variant is considered.

---

## 14. Profitability-First Acceptance Dimensions (Future HYP_005)

When a hypothesis candidate is eventually registered, qualification must be governed by economic criteria rather than statistical regression metrics:
1. `NET_RETURN_POSITIVE`: Realized cumulative net return after all fees > 0.
2. `NET_SHARPE`: Net annualized Sharpe ratio exceeding hurdle threshold.
3. `MAX_DRAWDOWN`: Maximum peak-to-trough drawdown within risk tolerance.
4. `MINIMUM_TRADE_COUNT`: Statistically sufficient sample of trade executions.
5. `COST_STRESS_SURVIVABILITY`: Strategy remains net-positive when friction assumptions are doubled.
6. `BENCHMARK_RELATIVE_PERFORMANCE`: Outperformance vs. SPY buy-and-hold on risk-adjusted basis.
7. `INTERNAL_VALIDATION_STABILITY`: Positive net performance across independent validation folds.
8. `EXTERNAL_HOLDOUT_PRESERVATION`: Zero exposure to clean holdout partitions until final ratification.

---

## 15. Partition Contamination & Holdout Governance

1. **Contamination Audit:**
   - The 2017–2022 SPY historical path was extensively analyzed in `HYP_003` and `HYP_004`.
   - The external Zarattini et al. paper sampled data through April 2024.
   - Public replications have already exposed performance through March 2026.
2. **Implication:**  
   Treating 2023–2026 as a "pristine blind holdout" for an intraday SPY momentum strategy is scientifically compromised because external literature and replications have already published results over this period.
3. **Status:** `MEC_0015_PARTITION_POLICY = OPEN_MAJOR_GOVERNANCE_DECISION`.

---

## 16. Critical Recency Risk & Summary

- **Historical Evidence:** Robust and verified in literature (2007–2024, Sharpe $\approx 1.33$).
- **Current Evidence:** Significant performance decay documented post-publication (May 2024–March 2026, Sharpe $\approx 0.39$).
- **Conclusion:** `CURRENT_EDGE_PERSISTENCE = NOT_ESTABLISHED`.
- **Verdict:** `MEC-0015` represents a high-priority, strategy-native research candidate precisely because it possesses clear executable rules, documented historical profitability, and active real-world edge decay that ACASH's fail-closed empirical engine can rigorously test.
