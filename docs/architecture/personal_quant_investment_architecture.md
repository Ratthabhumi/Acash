# ACASH Personal Quant Investment Architecture & Strategy Admission Specification

**Document ID:** `DOC-ACASH-PERSONAL-QUANT-ARCHITECTURE-20261012`  
**Classification:** System Architecture, Investment Mandate & Research Admission (Personal Quant System)  
**Authoritative Context:** Follows successful completion of PR #21 (PPDS Multi-Account Correctness & Consolidation)  
**Governing Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Single Canonical Authority)  
**Capital Authority:** `REAL_CAPITAL_AUTHORITY = $0.00`; `NO_REAL_ORDERS = true`  

---

## 1. System Mission & Paradigm Shift

ACASH is a **Personal Systematic Investment System** owned and operated by an individual to compound long-term personal capital with mathematical rigor. It is **NOT** a commercial SaaS platform, a hedge fund, or a sub-millisecond execution engine.

### Core Strategic Shift
| Legacy Approach | Personal Quant Paradigm |
| :--- | :--- |
| Chasing numerous short-horizon intraday hypotheses (e.g. SPY 1-minute) | Focusing on liquid multi-asset systematic investment (Equities, Bonds, Gold, Cash) |
| Feature-bloat in multi-account/accounting dashboards | Pure read-only decision support with exact Decimal valuation and provenance |
| Premature automated broker execution and high-frequency order placement | Read-only decision proposals (`BUY` / `HOLD` / `REDUCE` / `NO TRADE`) requiring manual human review |
| Comparing optimizer performance on in-sample returns | Measuring net performance against passive buy-and-hold and cash hurdles after all costs and currency friction |

---

## 2. Institutional Benchmark Assessment (Reality for an Individual Investor)

| Institution / Figure | Core Strength | Transferable Principles to ACASH | Non-Transferable Elements (Forbidden to Mimic) | Feasibility Rating (1–10) |
| :--- | :--- | :--- | :--- | :---: |
| **Warren Buffett** (Berkshire Hathaway) | Long-term compounding, low cost, cash discipline | **Sovereign Hurdle**: Low-cost broad-market indexing + cash reserve optionality | Discretionary deep-dive fundamental balance sheet forensic team | **9.5 / 10** |
| **Man AHL** | Systematic Multi-Asset Trend Following, Risk Budgeting | Daily/monthly time-series momentum, volatility scaling ($1/\sigma$), holding periods 1–12 months | Global multi-exchange futures exchange memberships and leverage desks | **9.0 / 10** |
| **AQR Capital** | Factor Investing (Value, Momentum, Quality, Defensive) | Factor attribution; testing whether "alpha" is simply disguised common factor beta | Institutional long/short single-stock portfolios with high borrow fees | **8.5 / 10** |
| **Two Sigma** | Data science & scientific research discipline | Hypothesis registry, strict train/test isolation, trial accounting, Deflated Sharpe Ratio | Petabyte-scale data infrastructure and massive distributed computing clusters | **8.0 / 10** |
| **Bridgewater** | All Weather Asset Allocation, Risk Parity | Economic regime diversification (Growth vs Inflation axes) across structural asset classes | Bond leverage via repo markets (unacceptable debt risk for retail accounts) | **8.0 / 10** |
| **D. E. Shaw** | Hybrid quantitative screening and fundamental risk overlay | Hard capital preservation gates, drawdown circuit breakers, disciplined rebalancing | Large human analyst teams covering individual industry verticals | **5.0 / 10** |
| **Jim Simons** (Renaissance) | Statistical Arbitrage, massive weak-signal combination | Scientific mindset, extreme cost awareness, zero emotional discretion | Medallion proprietary signal library, microsecond DMA, multi-billion dollar borrow lines | **2.0 / 10** |
| **Jane Street / Citadel** | Market making, liquidity provision, options pricing | Execution friction modeling (spread, slippage, market impact) | High-frequency market making, co-location, order internalization | **1.0 / 10** |

---

## 3. Two-Tier Personal Quant Investment Architecture

```text
[ Personal Portfolio & Cash: บัญชีและเงินสดทั้งหมด (ตรวจสอบยอดผ่าน PPDS) ]
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
 ┌────────────────────────┐              ┌────────────────────────┐
 │   Core Investment      │              │    Research Sleeve     │
 │       (70% - 90%)      │              │      (10% - 30%)       │
 ├────────────────────────┤              ├────────────────────────┤
 │ - Low-Cost Global Beta │              │ - Systematic Strategy  │
 │ - All Weather Baseline │              │   (Multi-Asset Trend)  │
 │ - Periodic Rebalance   │              │ - Rule-Based Timing    │
 │ - Defensive Cash Yield │              │ - Risk-Off to Cash     │
 └────────────────────────┘              └────────────────────────┘
         │                                       │
         └───────────────────┬───────────────────┘
                             ▼
     ┌───────────────────────────────────────────────┐
     │      Portfolio Governance & Risk Engine       │
     │  - ตรวจ Drawdown / Volatility / FX Exposure   │
     │  - คำนวณต้นทุนการเทรด (Friction Parameters)   │
     │  - กฎเด็ดขาด: Ranking != Approval             │
     │  - หากไม่มี Edge ที่มีนัยสำคัญ -> 100% CASH    │
     └───────────────────────────────────────────────┘
                             │
                             ▼
     ┌───────────────────────────────────────────────┐
     │             Read-Only Decision Gate           │
     │  - ผลลัพธ์: BUY / HOLD / REDUCE / NO TRADE    │
     │  - ข้อเสนอพร้อมหลักฐาน (Decision Ledger)      │
     │  - มนุษย์เป็นผู้อนุมัติการเทรด (Zero Auto-Order)│
     └───────────────────────────────────────────────┘
```

1. **Core Investment Tier (70%–90%)**:
   - Generates the structural macroeconomic risk premium via low-cost global equity index exposure, investment-grade fixed income, gold, and cash equivalents.
   - Disciplined scheduled rebalancing (quarterly or threshold-based).
2. **Research Sleeve Tier (10%–30%)**:
   - Houses systematically qualified alpha/timing candidates (e.g. Multi-Asset Time-Series Trend Following).
   - Rotates into Cash or Short-Term Treasuries when trend is negative, mitigating deep drawdowns.
3. **Portfolio Governance & Risk Engine (`src/acash/portfolio/governance.py`)**:
   - Evaluates proposals against sovereign risk budgets.
   - Enforces the core invariant: **`Ranking != Approval`**. If market regimes breach risk thresholds or no allocator beats cash hurdle, defaults to 100% Cash.
4. **Read-Only Decision Gate (`src/acash/ppds/surface.py`)**:
   - Emits structured, explainable decision ledgers (`BUY`, `HOLD`, `REDUCE`, `NO TRADE`).
   - Zero automated order execution. The human operator retains full sovereign trading authority.

---

## 4. Parameterized Personal Investment Mandate Template

The operator completes this mandate before any strategy research or data acquisition is authorized:

```yaml
personal_investment_mandate:
  reporting_currency: "THB"                 # Primary personal accounting currency (e.g. THB or USD)
  investable_capital: 0.00                  # Capital dedicated to ACASH systematic allocation
  emergency_cash_reserve: 0.00              # Separate liquid cash buffer (isolated from ACASH)
  
  risk_tolerance:
    max_acceptable_drawdown_pct: 20.0       # Maximum tolerated portfolio peak-to-trough drop (%)
    volatility_target_annual_pct: 10.0      # Annualized portfolio volatility target (%)
    hard_risk_off_threshold_pct: 15.0       # Drawdown level triggering mandatory Cash defensive posture
    
  investment_horizon:
    time_horizon_years: 10                  # Investment horizon
    rebalance_frequency: "MONTHLY"          # Rebalance frequency (MONTHLY or QUARTERLY)
    
  universe_and_instruments:
    allowed_asset_classes:
      - "GLOBAL_EQUITY_ETFS"                # e.g., VOO, VT, QQQ
      - "FIXED_INCOME_ETFS"                 # e.g., BND, TLT, SHY
      - "COMMODITIES_GOLD_ETFS"             # e.g., GLD, IAU
      - "CASH_EQUIVALENTS"                  # e.g., BIL, US T-Bills, Thai Money Market
    long_only: true                         # Strictly Long-Only (No margin borrowing, no shorting)
    leverage_allowed: false                 # Strictly 1.0x gross exposure maximum
    
  execution_policy:
    authority_mode: "READ_ONLY_OPERATOR_APPROVAL" # Human manually reviews and submits orders
    authorized_broker_targets: ["Dime", "InnovestX", "IBKR"]
```

---

## 5. Investable Universe & Data Gap Audit

| Required Data Class | Required Properties | Current ACASH Status | Action Required Before Research |
| :--- | :--- | :--- | :--- |
| **Historical Daily ETF Prices** | 10–20+ years, split-adjusted, dividend-adjusted (Total Return) | **MISSING** (ACASH only has SPY 1-minute and synthetic fixtures) | Define Data Intake Protocol & verify license/terms |
| **Daily FX Fixing Series** | Daily official reference rates (e.g. BOT USD/THB) | **MISSING** (ACASH has only synthetic point fixtures) | Ingest authoritative daily historical fixing series |
| **Broker Fee Schedules** | Commission rates, platform fees, FX exchange spreads | **PARTIALLY MODELLED** (`FrictionParameters` in `portfolio/evaluation.py`) | Calibrate `FrictionParameters` with actual broker tariffs |
| **Corporate Action Lineage** | Dividend ex-dates, withholding taxes, currency conversion | **PARTIALLY MODELLED** in PPDS statement ingestion | Validate historical split/dividend timeline integrity |

---

## 6. Single Candidate for Research Admission: Multi-Asset Trend Following

ACASH admits exactly one candidate for structured research intake:

### **Candidate Specification: Multi-Asset Time-Series Trend Following (TSMOM / CTA)**
- **Economic Thesis**: Liquid macro asset classes exhibit return persistence over 1–12 month horizons due to gradual institutional information diffusion and behavioral momentum (Moskowitz, Ooi, Pedersen 2012).
- **Core Mechanism**:
  1. For each asset $i \in \{\text{Equities}, \text{Bonds}, \text{Gold}\}$, calculate 12-month trailing return sign: $S_{i,t} = \text{sign}(R_{i, t-12 \to t})$.
  2. If $S_{i,t} > 0$, allocate positive long weight scaled inversely to rolling asset volatility: $w_{i,t} \propto \frac{1}{\sigma_{i,t}}$.
  3. If $S_{i,t} \le 0$, allocate 0% to asset $i$ and route that capital to Cash / Short-Term Treasury bills (`BIL`).
  4. Rebalance monthly.
- **Falsification Invariant**: Must beat the **60/40 Equity/Bond Buy-and-Hold** and **100% Cash** benchmarks on net CAGR, Sharpe ratio, and Maximum Drawdown after deducting realistic commissions, bid-ask spreads, and FX conversion fees.

---

## 7. Phased Implementation Roadmap

```text
[M0: Personal Investment Mandate Definition] 
  └─ Human specifies capital, emergency reserve, reporting currency, and drawdown ceiling.
       │
[M1: Data Qualification & Benchmark Formulation]
  └─ Ingest and verify historical daily Total Return ETF series and FX reference rates.
       │
[M2: Candidate Inception & Preregistration]
  └─ Formally register Multi-Asset Trend Following hypothesis with frozen parameters and trial budget.
       │
[M3: Out-of-Sample CPCV Evaluation & DSR Verification]
  └─ Execute hermetic evaluation in `src/acash/portfolio/evaluation.py` net of friction; verify DSR > 0.95.
       │
[M4: Read-Only PPDS Decision Integration]
  └─ Connect PPDS consolidated valuation to Portfolio Governance Gate for monthly decision reporting.
```

---

## 8. Hard Governance Invariants
- `REAL_CAPITAL_AUTHORITY = $0.00`
- `NO_REAL_ORDERS = true`
- `NO_PAPER_OR_LIVE_AUTHORITY = true`
- `NO_NEW_PROVIDER_HTTP = true`
- `NO_NEW_OUTCOME_TESTING = true`
- `NO_HYPOTHESIS_REGISTRATION_WITHOUT_APPROVAL = true`
- `NO_SEALED_HOLDOUT_ACCESS = true`
- `NO_HOMELAB_DEPLOYMENT = true`
