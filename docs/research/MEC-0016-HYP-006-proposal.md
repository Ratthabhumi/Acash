# MEC-0016 / HYP_006: Research Proposal

```text
[RESEARCH PROPOSAL: STRATEGY-NATIVE ECONOMIC REPLICATION]
[MECHANISM_ID: MEC-0016]
[CANDIDATE_HYPOTHESIS_ID: HYP_006]
[WORKING_TITLE: HYP_006 — SPY Noise-Area Intraday Momentum Post-2016 Free-Data Net-Profitability Replication]
[RESEARCH_CLASS: STRATEGY_NATIVE_EXECUTABLE_ECONOMIC_HYPOTHESIS]
[PRIMARY_OBJECTIVE: NET_ECONOMIC_PERFORMANCE_AFTER_REALISTIC_FRICTION]
[PRIMARY_DATA_PROVIDER: ALPACA_HISTORICAL_SIP]
[SECONDARY_BAR_CROSS_CHECK: HF_DATA_LIBRARY]
[DIVIDEND_AUTHORITY: STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS]
[SEARCH_SPACE_CARDINALITY: K = 1]
[PROPOSED_M1: 2016-01-01 THROUGH 2024-04-30]
[PROPOSED_M2: 2024-05-01 ONWARD (LOCKED / STRICTLY FORBIDDEN)]
[FEASIBILITY_STATUS: FREE_DATA_FEASIBILITY_PASS]
[GOVERNANCE_STATE: HYP_006_PREINCEPTION_READY_FOR_HUMAN_REVIEW (R1 NOT CREATED)]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/research/MEC-0016-HYP-006-proposal.md`
- **Governing Standard:** ACASH `AGENTS.md` (Implementation Correctness $\neq$ Contract Correctness, Single Canonical Authority, Strict Fail-Closed).
- **Target Asset:** SPDR S&P 500 ETF Trust (`SPY`, CUSIP: `78462F103`).

---

## 1. Scientific Objective & Formal Research Question

### 1.1 Formal Research Question
$$\begin{aligned}
\text{Research Question: } & \text{Does the noise-area intraday momentum mechanism of Zarattini, Aziz, and Barbon (2024)} \\
& \text{generate positive, statistically defensible net economic returns on SPY after deducting all} \\
& \text{realistic market frictions (NBBO spread crossing, \$0.001/share adverse slippage, SEC Section 31 fees,} \\
& \text{FINRA TAF fees, and } 2\times \text{ friction stress) over the publication-exposed post-2016 sample} \\
& \text{(2016-01-01 through 2024-04-30) accessible under zero-cost data constraints?}
\end{aligned}$$

### 1.2 Distinction from HYP_005
- **HYP_005:** Evaluated full academic publication replication (`2007-05-01` to `2024-04-30`, 17.0 years). Blocked operationally due to commercial data entitlement cost (~$199/month for Massive Stocks Advanced).
- **HYP_006:** Evaluates the post-2016 replication sample (`2016-01-01` to `2024-04-30`, ~8.3 years, 2,096 trading days) using accessible free-data infrastructure (Alpaca SIP + HF Data Library + SSGA).
- **Scientific Independence & Prior Integrity:** HYP_006 inherits its mathematical strategy mechanics and realistic friction stack strictly **before** any empirical results, signals, or backtests have been computed. Zero result-driven parameter tuning has occurred ($K = 1$).

---

## 2. Partition Architecture

| Partition | Date Range | Role & Boundary Definition | Access Rule |
| :--- | :--- | :--- | :--- |
| **M1** | `2016-01-01` to `2024-04-30` | Publication-exposed post-2016 replication sample (~8.3 years, 2,096 trading days) | Authorized for qualification & replication upon human approval |
| **M2** | `2024-05-01` onward | Prospective post-publication out-of-sample partition | **STRICTLY FORBIDDEN / ZERO ACCESS** |
| **M3** | Prospective future | Live forward-testing / paper execution | Sealed until M1 & M2 qualify |

---

## 3. Mathematical Strategy Specification ($K = 1$, Inherited from HYP_005)

### 3.1 Daily Gap Anchors
$$\text{prev\_close\_adjusted} = \text{close}_{d-1} - \text{dividend}_d$$
$$\text{UpperAnchor}_d = \max(\text{open}_d, \text{prev\_close\_adjusted})$$
$$\text{LowerAnchor}_d = \min(\text{open}_d, \text{prev\_close\_adjusted})$$

### 3.2 Canonical Noise Area & Multiplicative Bands
For session $t$ and minute $m \in [09:30, 16:00)$, define the relative move from open `move_open`:
$$\text{move\_open}_{t,m} = \left| \frac{\text{Close}_{t,m}}{\text{Open}_{t,09:30}} - 1 \right|$$
Noise estimate `sigma_open` is the mean of same-minute moves across the preceding 14 completed eligible sessions:
$$\sigma\_open_{t,m} = \frac{1}{14} \sum_{k=1}^{14} \text{move\_open}_{t-k,m}$$
- **Warmup Policy:** `REQUIRE_FULL_14_PRIOR_COMPLETED_SESSIONS`
- **Current Session Leakage:** `PROHIBITED`
- **Noise Multiplier:** $1.0$ (frozen canonical parameter)

Multiplicative bands around daily anchors:
$$\text{UpperBand}_{t,m} = \text{UpperAnchor}_t \times (1 + \sigma\_open_{t,m})$$
$$\text{LowerBand}_{t,m} = \text{LowerAnchor}_t \times (1 - \sigma\_open_{t,m})$$

### 3.3 Independent Volume-Weighted Average Price (VWAP)
$$\text{TypicalPrice}_{t,m} = \frac{\text{High}_{t,m} + \text{Low}_{t,m} + \text{Close}_{t,m}}{3}$$
$$\text{VWAP}_{t,m} = \frac{\sum_{i=09:30}^m (\text{TypicalPrice}_{t,i} \times \text{Volume}_{t,i})}{\sum_{i=09:30}^m \text{Volume}_{t,i}}$$
- Cumulative intraday calculation over RTH, reset at `09:30 ET` daily.
- Provider-supplied VWAP is strictly `REJECTED_FOR_BASELINE_SIGNAL_LOGIC`.

### 3.4 Intraday Decision Epochs & Signals
- Decision evaluation epochs (12 per session): `10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30 ET`.
- Evaluation reads the completed minute bar ending at the epoch ($T \to T - 1\text{min}$, e.g. $10:00 \to 09:59$).
- **LONG Signal:** $\text{Close}_{t,m} > \text{UpperBand}_{t,m}$ AND $\text{Close}_{t,m} > \text{VWAP}_{t,m}$.
- **SHORT Signal:** $\text{Close}_{t,m} < \text{LowerBand}_{t,m}$ AND $\text{Close}_{t,m} < \text{VWAP}_{t,m}$.
- **FLAT:** Otherwise.
- **Position State Policy:** Position may change only at designated 30-minute decision epochs. No intraminute stops.

### 3.5 End-of-Day (EOD) Flat Invariant
- **Policy:** `ZERO_OVERNIGHT_EXPOSURE`. All positions must be flat by end of regular trading hours.
- **Implementation Detail:** `EOD_EXECUTION_DETAIL = INHERITED_OPEN_IMPLEMENTATION_DETAIL_REQUIRING_PRE_R2_BINDING`. (No arbitrary 15:59 fill rule is invented at pre-inception).

### 3.6 Volatility Targeting & Position Sizing
- Volatility estimated from 15 prior completed daily simple close-to-close returns of unadjusted closes:
  $$\sigma_{d} = \text{std\_dev}(\text{returns}_{d-15 \dots d-1}, \text{ddof}=1)$$
- Shift: `shift = 1` (current session strictly excluded).
- Target **Daily** Volatility: $0.02$ ($2.0\%$ daily target volatility; daily return space without annualization).
- Maximum Leverage: $4.0\times$.
  $$\text{Leverage}_d = \min\left(4.0, \frac{0.02}{\sigma_d}\right)$$
- Denominator: Current session Open price ($\text{Open}_{d,09:30}$).
- Position Sizing Semantics:
  $$\text{Shares}_d = \text{round}\left( \frac{\text{PriorDayEndingAUM} \times \text{Leverage}_d}{\text{Open}_{d,09:30}} \right)$$
  (Nearest integer under frozen HYP_005 semantics, **not floor**).

---

## 4. Realistic Friction Stack

1. **Spread Crossing:** Mandatory fill at observed NBBO (BUY at Ask, SELL at Bid).
2. **Adverse Slippage:** Standalone $\$0.001/\text{share}$ adverse penalty per side.
3. **Regulatory Fees:**
   - SEC Section 31 fee (covered sales only, `ROUND_CEILING_TO_CENT`).
   - FINRA TAF fee (covered sales only, 7 historical rate tiers).
4. **Stress Testing Gate:** Must pass $2\times$ friction stress (doubled explicit costs + adverse 1 full half-spread stress).

---

## 5. Economic Acceptance Gates

The candidate hypothesis must satisfy all 7 acceptance criteria simultaneously:
1. **G1 (Net Return):** Total net return $> 0$.
2. **G2 (Net Sharpe):** Annualized Net Sharpe ratio $\ge 1.00$.
3. **G3 (Max Drawdown):** Maximum peak-to-trough net drawdown $\le 30.0\%$.
4. **G4 (Sample Size):** Minimum completed trades $N \ge 100$ (preserved unchanged from HYP_005 to prevent small-sample relaxation).
5. **G5 (Contract Integrity):** Zero unhandled exceptions or data contract failures.
6. **G6 (2× Friction Stress Return):** $2\times$ stress net total return $> 0$.
7. **G7 (2× Friction Stress Sharpe):** $2\times$ stress Net Sharpe ratio $\ge 0.75$.

---

## 6. Pre-Inception Status

`HYP_006` is in **pre-inception state**. It has NOT been registered, NOT sealed in hypothesis registry, and NO strategy data, signals, or backtests have been executed.
