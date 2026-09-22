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
[STATUS: PREINCEPTION_READY_FOR_HUMAN_REVIEW]
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
- **HYP_005:** Evaluated full academic publication replication (`2007-05-01` to `2024-04-30`, 17 years). Blocked operationally due to data entitlement cost (~$199/month).
- **HYP_006:** Evaluates the post-2016 subperiod (`2016-01-01` to `2024-04-30`, 8.3 years) using accessible free-data infrastructure (Alpaca SIP + HF Data Library + SSGA).
- **Independence & Prior Integrity:** HYP_006 inherits its mathematical strategy rules and friction model strictly **before** any empirical results, signals, or backtests have been computed. Zero result-driven parameter tuning has occurred ($K = 1$).

---

## 2. Partition Architecture

| Partition | Date Range | Role & Boundary Definition | Access Rule |
| :--- | :--- | :--- | :--- |
| **M1** | `2016-01-01` to `2024-04-30` | Publication-exposed post-2016 replication sample (~8.3 years, 2,096 trading days) | Authorized for qualification & replication upon human approval |
| **M2** | `2024-05-01` onward | Prospective post-publication out-of-sample partition | **STRICTLY FORBIDDEN / ZERO ACCESS** |
| **M3** | Prospective future | Live forward-testing / paper execution | Sealed until M1 & M2 qualify |

---

## 3. Mathematical Strategy Specification ($K = 1$)

### 3.1 Daily Gap Anchor
$$\text{prev\_close\_adjusted} = \text{close}_{d-1} - \text{dividend}_d$$
$$\text{UpperAnchor}_d = \max(\text{open}_d, \text{prev\_close\_adjusted})$$
$$\text{LowerAnchor}_d = \min(\text{open}_d, \text{prev\_close\_adjusted})$$

### 3.2 Noise Area Definition
$$\text{NoiseArea}_d = \frac{1}{14} \sum_{i=1}^{14} (\text{high}_{d-i} - \text{low}_{d-i})$$
$$\text{UpperBand}_{d,t} = \text{UpperAnchor}_d + \text{NoiseArea}_d$$
$$\text{LowerBand}_{d,t} = \text{LowerAnchor}_d - \text{NoiseArea}_d$$

### 3.3 Intraday Decision Rules
- Decisions evaluated at 30-minute intervals: `10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30 ET`.
- **Long Signal:** If completed minute bar Close $> \text{UpperBand}_{d,t}$ AND Close $> \text{VWAP}_{d,t}$.
- **Short Signal:** If completed minute bar Close $< \text{LowerBand}_{d,t}$ AND Close $< \text{VWAP}_{d,t}$.
- **Exit / Flatten:** Mandatory exit at `15:59 ET` (no overnight equity exposure).

### 3.4 Volatility Targeting & Position Sizing
$$\sigma_d = \text{std\_dev}(\text{daily\_returns}_{d-15 \dots d-1}, \text{ddof}=1)$$
$$\text{Leverage}_d = \min\left(4.0, \frac{0.02}{\sigma_d \times \sqrt{252}}\right)$$
$$\text{Shares}_d = \left\lfloor \frac{\text{PortfolioEquity} \times \text{Leverage}_d}{\text{open}_d} \right\rfloor$$

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
4. **G4 (Sample Size):** Minimum completed trades $N \ge 100$.
5. **G5 (Contract Integrity):** Zero unhandled exceptions or data contract failures.
6. **G6 (2× Friction Stress Return):** $2\times$ stress net total return $> 0$.
7. **G7 (2× Friction Stress Sharpe):** $2\times$ stress Net Sharpe ratio $\ge 0.75$.

---

## 6. Pre-Inception Status

`HYP_006` is in **pre-inception state**. It has NOT been registered, NOT sealed in hypothesis registry, and NO strategy data, signals, or backtests have been executed.
