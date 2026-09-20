# MEC-0015: Profitability-First Intraday Momentum Strategy Research Intake

**Mechanism ID:** `MEC-0015`
**Mechanism Name:** Noise-Area Intraday Momentum Strategy Replication
**Target Instrument:** `SPY` (SPDR S&P 500 ETF Trust)
**Target Timeframe:** 1-minute Regular Trading Hours (RTH) OHLCV (`America/New_York` / ET)
**Strategic Research Objective:** `NET_ECONOMIC_PERFORMANCE_AFTER_REALISTIC_FRICTION`
**Classification:** `STRATEGY_NATIVE_EXECUTABLE_REPLICATION_CANDIDATE`
**Current Governance State:** `INTAKE_COMPLETE_CONTRACTS_AUDITED`

> [!IMPORTANT]
> **Governance & Authority Boundary:**
> - `MEC-0015` is an external literature intake and strategy-native specification candidate ONLY.
> - `HYP_005` is **NOT CREATED**.
> - `ResearchReInceptionGate` is **NOT INVOKED**.
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

Unlike econometric predictive lines (such as `MEC-0014A` / `HYP_004`), which evaluated whether the slope coefficient $\beta$ in a predictive return regression was statistically distinguishable from zero ($p < 0.05$), `MEC-0015` is formulated as a **strategy-native executable mechanism**. A candidate hypothesis within this family can only be qualified by proving tradeable economic profitability after deducting all explicit commissions, bid-ask spread crossing, market impact, slippage, borrow fees, and execution latencies.

---

## 2. External Evidence Record (Literature Layer & Authority Hierarchy)

All statements in this section represent external literature claims and author reference implementations, **NOT** empirical facts verified or reproduced by ACASH.

### 2.1. Authority Hierarchy
1. **Primary Academic Paper:**
   Zarattini, Carlo; Aziz, Andrew; Barbon, Andrea.
   *"Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)"*
   SSRN Working Paper 4824172 / Swiss Finance Institute Research Paper Series No. 24-97.
   - **Originally Posted:** 14 May 2024.
   - **Current SSRN Revision:** 22 September 2025.
2. **Author Reference Implementation:**
   Concretum Group technical publications and reference implementations:
   - *"Backtesting Riding Intraday Trends in US Markets Using MATLAB"* (Concretum Group).
   - *"Backtesting 7 Years of Free Data: Beat the Market — An Effective Intraday Momentum Strategy for the S&P500 ETF (SPY)"* (Concretum Group).
   *Authority Rule:* Primary operational authority for implementation details omitted from the paper text.
3. **Independent External Replications:**
   - Delgado, M. (2026). *"Replicating Intraday Momentum in US Equities: Implementation Sensitivity and Regime Dynamics"*, SSRN 7323419.
   - Paz Sheimy (2024–2026). Public Python replication repository.
   *Authority Rule:* Ambiguity detection and cross-checking only; cannot override author reference implementation.
4. **ACASH Operationalization:**
   Applies strictly where literature and reference code are silent (e.g., realistic broker friction, borrow locate fees, regulatory fee schedules, feed qualification).

### 2.2. Reported Strategy Core Mechanics (Author Reference Specification)
1. **Underlying Asset:** SPDR S&P 500 ETF Trust (`SPY`).
2. **Source Data:** 1-minute regular-session OHLCV bars sourced from IQFeed (May 2007 through April 2024).
3. **Noise Area Boundaries:** Calculated for each minute of the regular session using the trailing 14-day rolling average of absolute open-to-timestamp percentage moves.
4. **Dividend-Adjusted Gap Anchor:** Overnight gap adjusted using prior 16:00 close minus current-day dividend: $\text{prev\_close\_adjusted} = \text{Close}[t-1] - \text{dividend}[t]$.
5. **Rebalance Epochs:** Evaluated strictly at 30-minute discrete intervals ($\text{min\_from\_open} \pmod{30} == 0$, $10:00, 10:30, \dots, 15:30$ ET).
6. **Entry Condition:** Requires joint confirmation of Noise Band breach AND session VWAP:
   - **Long:** $\text{Close}_t > \text{UpperBand}_t \quad \mathbf{AND} \quad \text{Close}_t > \text{VWAP}_t$
   - **Short:** $\text{Close}_t < \text{LowerBand}_t \quad \mathbf{AND} \quad \text{Close}_t < \text{VWAP}_t$
7. **VWAP Definition:** Cumulative regular-session VWAP using Typical Price $(H+L+C)/3$.
8. **Execution Lag:** Signal evaluated at 1-minute Close of epoch $t$; exposure lagged by 1 minute; P&L accrues starting at minute $t+1$.
9. **Position State & Trailing Exit:** Evaluated at 30-minute epochs; flat signal closes exposure; opposite signal flips exposure.
10. **Forced EOD Flat:** Forced liquidation of all open positions at market close (16:00 ET); strictly zero overnight exposure.
11. **Dynamic Sizing:** Sizing at session Open targeting 2% daily volatility, capped at 4.0× leverage, rounded to nearest integer shares.
12. **Reported Literature Friction:** Commission of $\$0.0035$/share with a minimum ticket charge of $\$0.35$/order ($\max(\$0.35, \$0.0035 \times \text{shares})$). Text mentions $\$0.0010$/share slippage, though standalone slippage is not implemented in the author reference backtest code.

### 2.3. Reported Performance (May 2007 – April 2024)
- Total Cumulative Return: $\approx 1,985\%$
- Annualized Return (CAGR): $\approx 19.6\%$
- Annualized Volatility: $\approx 14.3\%$
- Sharpe Ratio: $\approx 1.33$
- Maximum Drawdown: $\approx 25.0\%$
- **Classification:** `LITERATURE_REPORTED_RESULTS`.

---

## 3. Independent Replication & Edge-Decay Evidence

Audit of independent post-publication replications reveals critical nuances regarding edge persistence:

- **Replication A (Public Independent Python Replication, Paz Sheimy, 2024–2026):**
  - Reproduced historical in-sample performance (May 2007 – April 2024) with a reported Sharpe ratio of $\approx 1.34$.
  - Extended evaluation out-of-sample (OOS) from May 2024 to March 2026: annualized Sharpe ratio dropped to $\approx 0.39$.
- **Replication B (Delgado 2026, SSRN 7323419):**
  - Replicated strategy with granular attention to implementation details: confirmed that **Typical Price VWAP** and **VWAP entry confirmation** are material determinants of reproduction accuracy.
  - Observed that out-of-sample performance remained **strong through roughly August 2025**, before deteriorating sharply thereafter.
  - Concluded that the evidence is more consistent with **regime-specific recent degradation** (e.g. shifts in opening gap distribution and intraday volatility clustering) than immediate post-publication market arbitrage collapse.
- **Replication C (Cross-Asset SPY/ES Evaluation, 2025–2026):**
  - Confirmed historical Sharpe $\approx 1.11$ to $1.15$ on SPY and ES.
  - Observed compression around 2025, with walk-forward parameter re-tuning failing to rescue performance.
- **Classification:**
  - `CURRENT_EDGE_PERSISTENCE = NOT_ESTABLISHED`
  - `RECENT_EDGE_DEGRADATION_EVIDENCE = MATERIAL`
  - `IMMEDIATE_POST_PUBLICATION_DECAY = NOT_ESTABLISHED`

> [!WARNING]
> **Scientific Implication:**
> The presence of material recent edge degradation does NOT justify unprincipled parameter curve-fitting. Rather, it mandates that any future ACASH test protocol enforce strict out-of-sample partitioning, rigorous friction stress-testing, and fail-closed termination criteria.

---

## 4. Noise Area Mathematical Contract (Audited)

For trading day $t$ and regular-session minute $m$ (where $m \in [09:30, 16:00]$ ET):

### 4.1. Historical Move Magnitude
For each completed trading day $t-i$ ($i = 1, \dots, 14$):
$$\text{move\_open}[t-i, m] = \left| \frac{\text{Close}[t-i, m]}{\text{Open}[t-i, 09:30]} - 1 \right|$$

### 4.2. Time-Specific Expected Volatility ($\sigma_{\text{open}}$)
$$\sigma_{\text{open}}[t, m] = \frac{1}{14} \sum_{i=1}^{14} \text{move\_open}[t-i, m]$$
- `NOISE_AREA_LOOKBACK = 14_PRIOR_SESSIONS`
- `NOISE_AREA_CURRENT_SESSION_LEAKAGE = PROHIBITED` (Strictly enforced via `.shift(1)`).
- `NOISE_AREA_WARMUP_POLICY = REQUIRE_FULL_14_PRIOR_COMPLETED_SESSIONS` (Author Python `min_periods=13` variant documented as `AUTHOR_CODE_WARMUP_VARIANT = MIN_PERIODS_13` and excluded from baseline).

### 4.3. Dividend-Adjusted Gap Anchor & Boundaries
Author reference code explicitly adjusts the prior regular close for current-day cash dividends:
$$\text{prev\_close\_adjusted} = \text{Close}[t-1, 16:00] - \text{dividend}[t]$$
$$\text{UpperAnchor}[t] = \max(\text{Open}[t, 09:30], \text{prev\_close\_adjusted})$$
$$\text{LowerAnchor}[t] = \min(\text{Open}[t, 09:30], \text{prev\_close\_adjusted})$$

The upper and lower boundaries at minute $m$ are:
$$\text{UpperBand}[t, m] = \text{UpperAnchor}[t] \cdot (1 + \sigma_{\text{open}}[t, m])$$
$$\text{LowerBand}[t, m] = \text{LowerAnchor}[t] \cdot (1 - \sigma_{\text{open}}[t, m])$$
- `BAND_PREVIOUS_CLOSE_DIVIDEND_TREATMENT = RESOLVED_AUTHOR_IMPLEMENTATION`.
- Intraday bars remain unadjusted.

---

## 5. Entry Contract & Signal Semantics (Audited)

1. **Observation Epochs:**
   Evaluated strictly at 30-minute intervals: $\text{min\_from\_open} \pmod{30} == 0$
   $$\{10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30\} \text{ America/New_York (ET)}$$
   The first eligible evaluation occurs at 10:00 ET.
2. **Directional Condition (Joint Confirmation):**
   - $\mathbf{LONG}: \quad \text{Close}_t > \text{UpperBand}_t \quad \mathbf{AND} \quad \text{Close}_t > \text{VWAP}_t \implies \text{Signal}_t = +1$
   - $\mathbf{SHORT}: \quad \text{Close}_t < \text{LowerBand}_t \quad \mathbf{AND} \quad \text{Close}_t < \text{VWAP}_t \implies \text{Signal}_t = -1$
   - $\mathbf{FLAT / NEUTRAL}: \quad \text{otherwise} \implies \text{Signal}_t = 0$
3. **Classifications:**
   - `SIGNAL_PRICE_FIELD = RESOLVED_AUTHOR_REFERENCE_IMPLEMENTATION` (1-minute Close).
   - `ENTRY_REQUIRES_VWAP_CONFIRMATION = RESOLVED_TRUE`.
4. **Execution Exposure Lag & Real Fill Model:**
   - `SIGNAL_OBSERVATION = ONE_MINUTE_CLOSE_AT_DECISION_EPOCH`.
   - `REFERENCE_BACKTEST_EXPOSURE_LAG = RESOLVED_1_MINUTE`.
   - `PRIMARY_EXECUTION_MODEL = FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY` (BUY at Ask, SELL at Bid).

---

## 6. Exit & Trailing Stop Contract (Audited)

1. **Stop & Rebalance Evaluation Frequency:**
   Because position states are sampled every 30 minutes and forward-filled:
   - `STOP_EVALUATION_FREQUENCY = RESOLVED_30_MINUTE_DECISION_EPOCHS`.
   - `INTRAEPOCH_CONTINUOUS_STOP = NOT_BASELINE`.
2. **Flat & Flip Transitions:**
   - If price violates the joint condition at an epoch: $\text{Signal}_t = 0 \implies$ `FLAT_SIGNAL_AT_REBALANCE_CLOSES_POSITION = RESOLVED_AUTHOR_IMPLEMENTATION`.
   - If price satisfies the opposite condition: $\text{Signal}_t = -\text{Signal}_{t-1} \implies$ `OPPOSITE_SIGNAL_FLIPS_POSITION = RESOLVED_AUTHOR_IMPLEMENTATION`.
3. **Forced EOD Flat:**
   All open positions must be fully closed by 16:00 ET. Strictly zero overnight exposure.

---

## 7. VWAP Contract (Audited)

1. **Session Scope:** Cumulative regular session (09:30–16:00 ET), resetting daily.
2. **Mathematical Definition:**
   $$\text{TypicalPrice}_i = \frac{\text{High}_i + \text{Low}_i + \text{Close}_i}{3}$$
   $$\text{VWAP}_t = \frac{\sum_{i=1}^t \text{TypicalPrice}_i \cdot \text{Volume}_i}{\sum_{i=1}^t \text{Volume}_i}$$
3. **Classifications:**
   - `VWAP_NUMERATOR = RESOLVED_TYPICAL_PRICE_HLC3`.
   - `VWAP_SESSION = RESOLVED_REGULAR_SESSION_CUMULATIVE`.
   - `VWAP_REFERENCE_IMPLEMENTATION_AUTHORITY = AUTHOR_CODE`.
4. **Prohibition:** Close-only VWAP, provider-native synthesized VWAP, and tick SIP VWAP are prohibited for baseline replication.

---

## 8. Dynamic Volatility Sizing Contract (Audited)

1. **Formula & Parameters:**
   $$\text{Shares}_t = \text{round}\left(\frac{\text{AUM}_{t-1}}{\text{Open}[t, 09:30]} \cdot \min\left(4.0, \frac{\sigma_{\text{target}}}{\sigma_{\text{realized}, t}}\right), 0\right)$$
   - `TARGET_DAILY_VOL = 0.02` (2.0% daily volatility)
   - `MAX_LEVERAGE_MULTIPLIER = 4` (4.0× leverage cap)
   - `SIZING_PRICE = SESSION_OPEN` (`Open[t, 09:30]`)
   - `SHARE_ROUNDING = NEAREST_INTEGER_AUTHOR_IMPLEMENTATION` (`round(..., 0)`)
   - `AUM_REFERENCE = PRIOR_DAY_ENDING_AUM`
2. **Daily Volatility Window Status:**
   - `DAILY_VOL_RETURN_TYPE = SIMPLE_CLOSE_TO_CLOSE` ($\text{Close}_t / \text{Close}_{t-1} - 1$).
   - `CURRENT_DAY_RETURN_IN_VOL = PROHIBITED` (Completed prior sessions only).
   - `DAILY_VOL_WINDOW_RETURNS_COUNT = 15` (Canonical MATLAB authority: 15 simple returns ending at $t-1$, `ddof=1`, shift 1).

---

## 9. Friction & Transaction Cost Contract (Audited & Corrected)

### 9.1. Literature Friction Model
- Commission: $\max(\$0.35, \$0.0035 \times \text{shares})$ per order side.
- Standalone slippage: `PAPER_REPORTED_SLIPPAGE = 0.0010`, but `AUTHOR_REFERENCE_CODE_APPLIED_SLIPPAGE = NONE_STANDALONE`.

### 9.2. Spread & Slippage Contract
- `ACASH_SPREAD_MODEL = EMBEDDED_IN_NBBO_FILL` (BUY at Ask, SELL at Bid).
- `EXPLICIT_HALF_SPREAD_DEDUCTION_WITH_NBBO = PROHIBITED` (No double-counting).
- `BASELINE_STANDALONE_SLIPPAGE = $0.001/share` per executed side (adverse direction: BUY at $\text{Ask} + \$0.001$, SELL at $\text{Bid} - \$0.001$).
- 2× Friction Stress: Retain NBBO fill + $2\times$ non-spread explicit costs + half-spread adverse slippage + short borrow stress.

### 9.3. Regulatory Fees & Short Borrow
- `ACASH_REGULATORY_FEE_MODEL = RESOLVED_HISTORICAL_SCHEDULES`: SEC Section 31 (25 tiers) and FINRA TAF (5 tiers) pinned to historical schedules (sales only).
- `SHORT_LOCATE_ASSUMPTION = SPY_AVAILABLE_UNLESS_PROVIDER_OR_BROKER_MARKS_UNAVAILABLE` (0 bps baseline + 50 bps annualized mandatory stress).

---

## 10. Data Contract Requirements

1. **1-Minute RTH OHLCV Bars:** Regular-session SPY bars (09:30–16:00 ET, 390 bars). `ALPACA_SIP_BAR_MAPPING = QUALIFIED` (manifest sealed).
2. **Historical SIP Quotes:** NBBO quotes qualified for execution boundaries. `MEC-0015-quote-provider-contract-manifest.json` sealed.
3. **Cash Dividends:** Corporate actions qualified. `MEC-0015-dividend-provider-contract-manifest.json` sealed.
4. **Missing Bar Policy:** `MISSING_REQUIRED_MINUTE_POLICY = FAIL_CLOSED_SESSION_EXCLUSION`. Zero silent imputation.

---

## 11. Early-Close Days Policy

- `EARLY_CLOSE_POLICY = EXCLUDE_NON_STANDARD_REGULAR_SESSIONS`.
- Non-standard sessions (closing at 13:00 ET, 210 minutes) are strictly excluded from baseline `HYP_005`.

---

## 12. Strategy Degrees of Freedom & Anti-HARKING

- Lookback: $N = 14$ days
- Noise Multiplier: $M = 1.0$
- Decision Interval: $\Delta t = 30$ minutes
- Volatility Target: $2.0\%$
- Leverage Cap: $4.0\times$
- Search Space Cardinality: $K = 1$ (Single fixed baseline replication).
- Post-publication parameter optimizations are strictly excluded.

---

## 13. Profitability-First Acceptance Dimensions (Future HYP_005)

When a hypothesis is registered, qualification requires satisfying economic criteria:
1. `NET_RETURN_POSITIVE`: Realized net return after all frictions $> 0$.
2. `NET_SHARPE`: Net annualized Sharpe $\ge 1.00$ (M1), $\ge 0.50$ (M2).
3. `MAX_DRAWDOWN`: Peak-to-trough drawdown $\le 30\%$ (M1), $\le 35\%$ (M2).
4. `COST_STRESS_SURVIVABILITY`: Positive net return under 2× friction stress.
5. `MINIMUM_TRADE_COUNT`: `MINIMUM_COMPLETED_TRADES = 100` (`HUMAN_RATIFIED_SAMPLE_ADEQUACY_FLOOR`).
6. `BENCHMARK_RELATIVE_PERFORMANCE`: Outperformance vs SPY buy-and-hold.

---

## 14. Partition Contamination Governance

- 2007–2024 is exposed in the original paper (SSRN revision Sept 2025).
- May 2024–March 2026 is exposed in public replications (Paz Sheimy, Delgado).
- 2017–2022 was exposed in ACASH `HYP_003` and `HYP_004`.
- **Conclusion:** 2023–2026 cannot be honestly claimed as a pristine external holdout.
- `MEC_0015_PARTITION_POLICY = RESOLVED` (M1: 2007-05 to 2024-04; M2: 2024-05 to exposed date; M3: prospective).

---

## 15. Summary of Governance States

- `HYP_005 = NOT_CREATED`
- `ResearchReInceptionGate = NOT_INVOKED`
- `BACKTEST = NOT_STARTED`
- `STRATEGY_PNL = NOT_COMPUTED`
- `MARKET_DATA_ACCESS = QUALIFICATION_PROBES_ONLY (< 2024-05-01)`
- `MAX_ACCESSED_DATE = 2024-03-01`
- `2024-05-01_ONWARD = NOT_ACCESSED`
- `PAPER = NOT_AUTHORIZED`
- `LIVE = LOCKED`
- `CAPITAL = $0.00`
- `NO_REAL_ORDERS = true`
- `PRE_INCEPTION_BLOCKERS_REMAINING = 0`
- `HYP_005_READINESS = READY_FOR_HUMAN_INCEPTION_AUTHORIZATION`
