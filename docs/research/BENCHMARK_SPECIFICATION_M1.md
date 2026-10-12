# ACASH — Benchmark Specification & Research Safeguards (Milestone M1)

**Document ID:** `DOC-ACASH-BENCHMARK-SPEC-20261012`  
**Classification:** Quantitative Benchmark Formulation & Statistical Protocol  
**Governing Authority:** `AGENTS.md` (Single Canonical Authority, Strict Fail-Closed, Units & Space Discipline)  
**Effective Date:** 2026-10-12  
**Outcome Testing Status:** `NO_STRATEGY_OUTCOME_TESTING = true`; Zero historical backtests executed in this milestone.  

---

## 1. Objective & Sovereign Benchmark Hierarchy

To prevent self-deceptive quantitative research, any proposed investment strategy—whether passive core or active trend-following—must be evaluated against a strict hierarchy of transparent, reproducible baselines.

```text
┌────────────────────────────────────────────────────────┐
│                   SOVEREIGN HURDLES                    │
├──────────────────────────┬─────────────────────────────┤
│ 1. Zero Cash (Nominal)   │ BM-ZERO-CASH: 0.00% nominal return, cash idle in account │
│ 2. Theoretical T-Bill    │ BM-TBILL-THEORETICAL: DTB3 discount-converted accrual   │
│ 3. Traded T-Bill ETF     │ BM-BIL-ETF: Traded ETF, secondary market price/yield   │
│ 4. S&P 500 Buy-and-Hold  │ Broad-market equity beta (VOO Total Return)             │
│ 5. 60/40 Balanced Core   │ 60% Equity / 40% Bond (VOO/BND) quarterly rebalanced    │
│ 6. Naive Equal Weight    │ 1/N across universe; zero estimation error              │
│ 7. Inverse Volatility    │ 1/σ heuristic; covariance-free risk balance             │
└──────────────────────────┴─────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│       ACTIVE RESEARCH CANDIDATE (MULTI-ASSET TREND)    │
│  - Evaluated on PRE-REGISTERED PRIMARY ENDPOINT        │
│  - Not forced to beat every metric simultaneously      │
│  - Friction-adjusted with small-order minimum fees     │
│  - All risk thresholds tagged PROPOSED_FOR_RESEARCH    │
└────────────────────────────────────────────────────────┘
```

---

## 2. Benchmark Definitions & Total Return Conventions

### 2.1 Cash & Risk-Free Benchmarks (Strictly Disaggregated)

Prior documentation loosely conflated cash, Treasury yield quotes, and traded T-Bill ETFs. In Milestone M1.5, they are strictly separated into three distinct benchmarks:

#### A. Zero-Yield Nominal Cash (`BM-ZERO-CASH`)
- **Definition**: Uninvested base currency (USD) held as idle broker cash earning zero interest ($r_t = 0.00\%$).
- **Role**: Represents the purest capital-preservation floor. An investment strategy must beat uninvested cash net of transaction friction and exchange fees.
- **Drawdown**: Exactly 0.00% nominal drawdown in base currency (USD).

#### B. Theoretical Treasury Bill Accrual (`BM-TBILL-THEORETICAL`)
- **Instrument**: U.S. 3-Month Treasury Bill Secondary Market Rate (`DTB3` via FRED).
- **Mathematical Transformation (Strict Fail-Closed)**:
  - `DTB3` is quoted as an annualized bank discount rate $d$ on an ACT/360 day-count basis:
    $$d = \frac{\text{Discount}}{\text{Face Value}} \times \frac{360}{t}$$
  - It is **NOT** a daily compounding deposit rate and must **NOT** be compounded directly.
  - To convert to an annualized Bond Equivalent Yield (BEY) on an ACT/365 basis for period $t \le 182$ days:
    $$y_{\text{BEY}} = \frac{365 \times d}{360 - d \times t}$$
  - Daily accrual factor is derived canonically from the converted bond yield.
- **Role**: Economic opportunity cost of risk-free lending to the sovereign government.

#### C. Traded Short-Term T-Bill ETF (`BM-BIL-ETF`)
- **Instrument**: SPDR Bloomberg 1-3 Month T-Bill ETF (`BIL`).
- **Empirical Reality**:
  - `BIL` is an exchange-traded fund trading on the secondary market.
  - It is **NOT** guaranteed zero drawdown or risk-free.
  - Subject to secondary-market bid-ask spread, intraday price fluctuations, broker commission, expense ratio (0.135% gross / 0.135% net as of 2026), and cash distribution schedule.
  - Monthly dividend payouts cause ex-dividend price drops followed by cash settlement on payable date.
- **Role**: Practical, investable short-term cash vehicle achievable by retail accounts on an exchange without direct Treasury auction access.

> **CRITICAL INVARIANT**: Never use `BM-ZERO-CASH`, `BM-TBILL-THEORETICAL`, and `BM-BIL-ETF` interchangeably in reporting, Sharpe calculations, or gate assessments.

### 2.2 Broad Equity Market Buy-and-Hold (`BM-SP500`)
- **Instrument**: Vanguard S&P 500 ETF (`VOO`).
- **Inception Boundary**: September 7, 2010. Observations prior to this date require explicit `SPX_SYNTHETIC_PROXY` notation and must not be passed off as authentic ETF market prints.
- **Return Space**: Total Return with dividend reinvestment on ex-date net of applicable withholding tax (see Section 2.6).
- **Role**: Evaluates whether active timing generates positive value beyond passive market risk premium.

### 2.3 Classical Balanced Core (`BM-6040`)
- **Allocation**: 60% VOO / 40% BND (Vanguard Total Bond Market ETF).
- **Rebalance Schedule**: Calendar quarterly with frictionless target resetting for baseline comparison, and friction-adjusted modeling for retail implementation.
- **Role**: Standard benchmark for retail wealth compounding.

### 2.4 Naive Equal Weight (`BM-EW`)
- **Allocation**: $w_i = \frac{1}{N}$ across the eligible investable universe (`VOO`, `BND`, `GLD`, `BIL`).
- **Rebalance Schedule**: Monthly rebalancing.
- **Role**: Benchmark with zero parameter estimation risk.

### 2.5 Inverse Volatility Heuristic (`BM-INVVOL`)
- **Allocation**: $w_{i,t} \propto \frac{1}{\sigma_{i,t}}$, where $\sigma_{i,t}$ is the 60-day rolling sample return standard deviation.
- **Role**: Robust risk-budgeting heuristic avoiding inverted covariance matrix instability.

### 2.6 Execution Timing, Taxes, and Data Conventions
- **Decision vs. Execution Timing**:
  - Allocation signals computed on daily close $P_{t}$ cannot be executed at $P_{t}$ without lookahead bias.
  - Realistic modeling must execute at next-session open $O_{t+1}$ or volume-weighted average price $\text{VWAP}_{t+1}$.
- **Dividend Withholding Tax**:
  - For Thai tax resident individuals holding US-domiciled ETFs (`VOO`, `BND`, `GLD`, `BIL`) via W-8BEN, the statutory withholding tax rate on distributions is **15.0%** under the US-Thailand Double Tax Agreement (DTA).
  - Net dividend received: $D_{\text{net}} = D_{\text{gross}} \times (1 - 0.15)$.
  - (Optional Future Architecture): UCITS ETFs domiciled in Ireland (e.g., `CSPX`, `AGGU`) experience 15% internal US withholding on equities and 0% outbound withholding, avoiding US estate tax exposure ($60,000 threshold for non-resident aliens).
- **Exchange Fees & Currency**:
  - Base currency: USD.
  - Cross-currency reporting: THB via Bank of Thailand (BOT) official fixing rate, preserving bid/offer spread when simulating repatriations.

---

## 3. Active Candidate Formulation: Multi-Asset Trend Following

### 3.1 Critical Literature Distinction
- **Academic Canon (Moskowitz, Ooi, Pedersen 2012 - "Time Series Momentum")**:
  - Examined 58 liquid futures and currency forward contracts.
  - Employed bidirectional exposure (both long and short), active leverage, and daily margin financing.
- **ACASH Retail Adaptation**:
  - **Long-Only ETF Universe**: `VOO`, `BND`, `GLD`, `BIL`.
  - **Zero Shorting / Zero Margin Borrowing**: Gross leverage capped at 1.00x.
  - **Defensive Mechanism**: When 12-month momentum is non-positive ($R_{i, 12M} \le 0$), capital rotates into Cash / T-Bills (`BIL`), rather than initiating short positions.
  - **Epistemic Standing**: This is an **asymmetric capital-preservation adaptation**, NOT an academic replication of Moskowitz et al. (2012).

### 3.2 Evaluation Protocol & Governance Classification

All target metrics and thresholds defined below are classified strictly as `PROPOSED_FOR_RESEARCH` until formally ratified by the human operator.

#### A. Candidate Primary Metric: Calmar Ratio
- **Formula**:
  $$\text{Calmar} = \frac{\text{CAGR}}{|\text{Max Drawdown}|}$$
- **Mathematical Edge Cases & Boundaries**:
  - **Zero Drawdown**: If $|\text{Max Drawdown}| = 0.00$, the Calmar ratio is mathematically undefined. In this case, the system must emit `CALMAR_UNDEFINED_ZERO_DRAWDOWN` rather than fabricating an artificial infinite ratio.
  - **Negative CAGR**: When $\text{CAGR} < 0$, a larger drawdown produces a less negative ratio, distorting rankings. The metric must be conditioned on $\text{CAGR} > 0$.
  - **Sample Sensitivity**: Calmar is heavily driven by single outlier drawdowns and sample endpoints. It must be paired with continuous drawdown diagnostics (Ulcer Index, CDaR).
- **Status**: `CANDIDATE_PRIMARY_ENDPOINT` (Pending scientific preregistration).

#### B. Risk Ceilings (Status: `PROPOSED_FOR_RESEARCH`)
The following parameters are engineering proposals and **NOT ratified personal mandate policies**:
- Maximum Peak-to-Trough Drawdown $\le 50.0\%$ (Aligned with personal tolerance profile).
- Maximum Annualized Volatility $\le 18.0\%$ (`PROPOSED_FOR_RESEARCH` — Not operator-ratified).
- Monthly rebalance frequency with threshold $\Delta w \ge 3.0\%$ (`PROPOSED_FOR_RESEARCH` — Not operator-ratified).
- Gross Leverage $\le 1.00$ (Architecturally enforced).

#### C. Candidate Pass/Fail Decision Rule (Status: `PROPOSED_FOR_RESEARCH`)
$$\text{Calmar}_{\text{OOS}}(\text{Trend}) > \text{Calmar}_{\text{OOS}}(\text{BM-6040})$$
$$\text{AND } \text{MaxDD}_{\text{OOS}}(\text{Trend}) \le 50.0\%$$
$$\text{AND Expected Return Net of Friction} > \text{Cash Hurdle}$$

---

## 4. Friction & Small-Account Reality Check ($1,000 Portfolio)

For a $1,000 portfolio:
- **Broker Tariff (Interactive Brokers LLC)**:
  - Pro Tiered: $0.0035/share, minimum $0.35/order, capped at **1.0% of trade value**.
  - Pro Fixed: $0.005/share, minimum $1.00/order, capped at **1.0% of trade value**.
  - Pass-through exchange, clearing (FINRA/SEC), and regulatory fees.
- **Impact on Small Orders**:
  - For a $10 micro-rebalance order, the 1.0% cap applies: commission = $0.10.
  - For a $50 rebalance order, the $0.35 floor applies: commission = $0.35 (0.70% one-way cost drag).
  - High-frequency daily or weekly rebalancing will rapidly destroy capital through ticket minimums.
- **Research Safeguard**:
  - Rebalance schedules must be evaluated net of actual broker friction tables across normal, conservative, and stress scenarios.
