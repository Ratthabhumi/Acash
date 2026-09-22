# HYP_007 Pre-R3 Economic Metric Binding 001
## Simulated Starting AUM & Performance Metric Semantics Additive Governance Binding

```text
[AMENDMENT IDENTIFIER: HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_001]
[AMENDMENT TYPE: ADDITIVE_PRE_R3_GOVERNANCE_BINDING]
[UPSTREAM_CANONICAL_HEAD: 86675074559e3f64bd488a84317c226d31deaaf6]
[TARGET_HYPOTHESIS_ID: HYP_007]
[TARGET_MECHANISM_ID: MEC-0017]
[HUMAN_AUTHORIZATION: AUTHORIZE_HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING]
[R1_R2_ARTIFACTS_STATUS: PRESERVED_BYTE_FOR_BYTE_IMMUTABLE]
[PRE_R3_METRIC_BINDING: SEALED_PASS]
[R3_READINESS: READY_FOR_SEPARATE_HUMAN_AUTHORIZATION]
[CAPITAL_AUTHORITY: $0.00 / NO_REAL_ORDERS=true]
[STRATEGY_RESULTS_STATUS: UNOBSERVED / SIGNALS=0 / TRADES=0 / PNL=0]
```

- **Document ID:** `docs/phase14/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_001.md`
- **Governing Standard:** ACASH `AGENTS.md` (Strict Fail-Closed Contract, Single Canonical Authority, Literature Alignment, Zero Unverified Claims).

---

## 1. Executive Summary & Purpose

Prior to authorizing Step R3 empirical strategy execution on the M1 direct-SIP dataset, all remaining economically material metric semantics and accounting normalization parameters must be permanently frozen. 

While HYP_007 R1 and MEC-0015 freeze the sizing relation `AUM_REFERENCE = PRIOR_DAY_ENDING_AUM`, the exact initial simulated portfolio equity ($\text{AUM}_0$) for Day 1 of M1 was not explicitly declared. Because the literature execution cost model incorporates a fixed minimum ticket charge:
$$\text{Commission} = \max(\$0.35, \$0.0035 \times \text{shares})$$
the net economic return is not strictly scale-invariant. To prevent post-hoc optimization or arbitrary selection by backtest engine defaults, this document additively binds $\text{AUM}_0$ and all performance metric formulas **BEFORE** observing any strategy signal, trade, fill, or P&L.

---

## 2. Canonical Audit of Starting AUM Authority

A strict hierarchical audit across primary literature, author codebases, and historical ACASH research was conducted:

1. **Zarattini / Concretum Group Author Code:** The published SSRN 4824172 paper and Concretum MATLAB reference scripts calculate returns on normalized equity series without explicitly parameterizing a physical initial dollar fund.
2. **MEC-0015 Contract Audit & Intake:** Audits confirmed dynamic sizing targets 2% daily volatility with 4× leverage cap and `AUM_REFERENCE = PRIOR_DAY_ENDING_AUM`, but left initial fund size open.
3. **HYP_005 / HYP_006 / HYP_007 Preregistrations:** Zero explicit initial cash was bound in R1 specifications.
4. **Generic Engine Defaults:** `BacktestEngineConfig.initial_cash = Decimal("100000.00")` exists in generic test harnesses, but cannot be treated as scientific authority without explicit human ratification.

### Resolution: Outcome C — No Prior Value Established
Pursuant to human authorization `AUTHORIZE_HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING`, the starting simulated AUM is frozen under:
- **Decision Outcome:** `C_NO_PRIOR_VALUE_ESTABLISHED`
- **Classification:** `HUMAN_RATIFIED_PRE_RESULT_ACCOUNTING_NORMALIZATION`
- **Frozen Amount:**
  $$\mathbf{SIMULATED\_STARTING\_AUM\_USD = \$100,000.00}$$

### Governance Constraints on Starting AUM:
1. **Simulation Accounting Only:** This value is strictly an accounting normalization for share sizing and fixed-ticket commission amortization. It confers **ZERO** real or paper trading capital authority. Capital authority remains `$0.00`, and `NO_REAL_ORDERS = true`.
2. **No Sensitivity Search ($K=1$):** Exactly one baseline value is tested ($100k). No sensitivity exploration across $10k, $50k, or $1M is permitted.
3. **Parity Between Baseline and Stress:** Both baseline and 2× stress simulations begin with the exact same initial equity of `$100,000.00`.

---

## 3. Performance Return & Total Return Semantics

### 3.1. Daily Net Portfolio Return
For each trading session $t \in [1, T]$:
$$r_t = \frac{\text{EndingAUM}_t}{\text{EndingAUM}_{t-1}} - 1$$
where:
- $\text{EndingAUM}_0 = \text{SIMULATED\_STARTING\_AUM\_USD} = \$100,000.00$.
- $\text{EndingAUM}_t = \text{EndingAUM}_{t-1} + \text{NetIntradayPnL}_t$.
- $\text{NetIntradayPnL}_t = \text{GrossTradingPnL}_t - \text{Commissions}_t - \text{Slippage}_t - \text{SEC31}_t - \text{FINRATAF}_t - \text{BorrowFee}_t$.
- Zero cash flows, zero deposits, zero withdrawals.

### 3.2. Net Total Return
The overall net return across the entire evaluation horizon is:
$$\text{NET\_TOTAL\_RETURN} = \frac{\text{FinalAUM}}{\text{InitialAUM}} - 1$$
Compounded net accounting equity is strictly used. Summing daily returns is prohibited.

---

## 4. Annualized Sharpe Ratio Authority (G2 & G7)

Both baseline Gate G2 ($\text{SR} \ge 1.00$) and 2× friction stress Gate G7 ($\text{SR} \ge 0.50$) must follow the exact same statistical convention:

- **Canonical Authority:** `acash.validation.deflated_sharpe.calculate_annualized_sharpe`
- **Return Input:** Daily net portfolio return series $\{r_t\}_{t=1}^T$. Intraday trade return annualization is strictly prohibited.
- **Formulation:**
  $$\text{Sharpe} = \frac{\bar{r}}{\hat{\sigma}_r} \times \sqrt{252}$$
  where:
  - $\bar{r} = \frac{1}{T}\sum_{t=1}^T r_t$ (arithmetic sample mean)
  - $\hat{\sigma}_r = \sqrt{\frac{1}{T-1}\sum_{t=1}^T (r_t - \bar{r})^2}$ (sample standard deviation, `ddof=1`)
  - Annualization multiplier: $\sqrt{252}$ (`PERIODS_PER_YEAR = 252`)
  - Risk-free rate: $R_f = 0.0$ (standard ACASH null governance policy)
- **Zero Variance Contract:** If $\hat{\sigma}_r \le 10^{-12}$, the engine must fail closed with `DataContractError`. Silent artificial floors (`max(1e-12, val)`) or artificial outputs ($SR=0.0$) are strictly prohibited.

---

## 5. Maximum Peak-to-Trough Drawdown (G3)

Gate G3 requires $\text{Max Drawdown} \le 20.0\%$:
- **Equity Curve Anchor:** $\text{Equity}_0 = \text{SIMULATED\_STARTING\_AUM\_USD} = \$100,000.00$.
- **End-of-Day Equity:** $\text{Equity}_t = \text{EndingAUM}_t$ for session $t$.
- **Running Peak:** $\text{Peak}_t = \max_{0 \le s \le t} \text{Equity}_s$.
- **Drawdown at Session $t$:**
  $$DD_t = \frac{\text{Peak}_t - \text{Equity}_t}{\text{Peak}_t} = 1 - \frac{\text{Equity}_t}{\text{Peak}_t}$$
- **Maximum Drawdown:**
  $$\text{MAX\_DRAWDOWN} = \max_{0 \le t \le T} DD_t$$
- Intraday mark-to-market drawdown is not evaluated; canonical literature contract relies on the net end-of-day equity curve.

---

## 6. Trade Counting & Position Flip Semantics (G4)

Gate G4 requires $\text{Completed Trades} \ge 100$:

### 6.1. Completed Trade Definition
A completed trade is defined as one round-trip position episode from entry to exit:
$$\text{FLAT} \to \text{NONZERO POSITION} \to \text{FLAT}$$

### 6.2. Direct Directional Flip (LONG $\leftrightarrow$ SHORT)
When an opposing signal occurs while holding inventory:
1. **Closing Leg:** Selling `current_shares` to reach FLAT terminates the active position episode and counts as **1 completed trade**.
2. **Opening Leg:** Selling `target_shares` to establish the new opposite position initiates a new trade episode.
- **Trade Count Increment:** At the moment of the flip, exactly **1 trade completes**. The newly opened position will complete when it is subsequently closed (at a stop/exit signal or at 16:00 forced flat).
- **Execution Accounting:** Each leg bears its independent transaction friction pursuant to the frozen MEC-0017 execution contract.
- Individual order legs, signal evaluation intervals, and unexecuted signals are strictly prohibited from being counted as completed trades.

---

## 7. Intraday Sizing & Same-Direction Signal Invariants

1. **Fixed Daily Target Shares:** Target share count for session $t$ is calculated once prior to first entry:
   $$\text{Shares}_t = \text{round}\left( \frac{\text{EndingAUM}_{t-1}}{\text{Open}_{t,09:30}} \cdot \min\left(4.0, \frac{0.02}{\sigma_{\text{realized}, t}}\right) \right)$$
   Because $\text{Open}_{t, 09:30}$, $\text{EndingAUM}_{t-1}$, and $\sigma_{\text{realized}, t}$ are constant throughout the trading day, $\text{Shares}_t$ is invariant across all 13 decision boundaries.
2. **No Same-Direction Churn:** If an existing position is already held in the signal direction (e.g. LONG and signal evaluates to LONG), **NO** additional order is generated. Position is held without transaction costs.
3. **No Intraday Compounding:** Intraday unrealized or realized gains cannot increase position sizing on the same day.

---

## 8. Baseline vs. 2× Stress Compounding Paths

1. **Independent Equity Paths:** Baseline and 2× Stress maintain **independent compounding equity curves**:
   - Baseline sizing on day $t$ uses $\text{EndingAUM}_{t-1}^{\text{baseline}}$.
   - 2× Stress sizing on day $t$ uses $\text{EndingAUM}_{t-1}^{\text{stress}}$.
   Because 2× stress suffers higher friction drag, its capital base evolves independently, providing a realistic assessment of stressed compounding capacity.
2. **Identical Signals & Fills:** Both paths execute against identical strategy signals and identical direct-SIP NBBO quotes. Only friction charges differ.

---

## 9. Benchmark Reporting Semantics

SPY buy-and-hold total return is secondary contextual evidence only:
- It does not substitute for, nor does it block, primary G1–G7 gate evaluation.
- Total return calculation incorporates raw SIP closing prices and sovereign SSGA cash dividend distributions.
- If benchmark return is not finalized, R3 may report `BENCHMARK = NOT_COMPUTED` without impairing hypothesis qualification.

---

## 10. Excluded Session Verification

The integrity audit finding for session `2023-06-05` (CTA outage, 386/390 bars) is preserved:
- `strategy_eligible = false`
- `signal_eligible = false`
- `trade_eligible = false`
- `performance_eligible = false`
- Intraday bars: absent from `m1_bars_qualified.parquet`.
- Noise Area lookback: 14 prior eligible sessions strictly skip `2023-06-05`.
- Volatility Lineage (Outcome V1): validated 15:59 close (`$427.10`) enters continuous market daily return lineage.
- Contract enforcement: `SESSION_EXCLUDED => NO_SIGNAL => NO_EXECUTION`.

---

## 11. Ratification & Next Steps

All pre-R3 economic metric definitions and accounting parameters are permanently sealed.

- `PRE_R3_METRIC_BINDING = SEALED_PASS`
- `R3_READINESS = READY_FOR_SEPARATE_HUMAN_AUTHORIZATION`
- `NEXT_REQUIRED_ACTION = AUTHORIZE_HYP_007_R3_M1_EXECUTION`
