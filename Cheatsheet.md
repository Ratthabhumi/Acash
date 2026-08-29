# ACASH — Developer & Quant Quick Reference Cheatsheet

**Project:** ACASH (Automated Capital Allocation System)  
**Version:** 1.6.0 (Phases 0–6 Complete & Hardened)  
**Operating Philosophy:** *"DO NOT ASSUME AN EDGE. PROVE IT."*

$$\text{DATA} \to \text{EVIDENCE} \to \text{HYPOTHESIS} \to \text{RESEARCH} \to \text{ALPHA} \to \text{VALIDATION} \to \text{PORTFOLIO} \to \text{RISK} \to \text{EXECUTION} \to \text{OUTCOME} \to \text{FEEDBACK}$$

---

## 1. North Star & First Principles

1. **The North Star Question:**
   > *"Given the current market state, available opportunities, portfolio state, uncertainty, liquidity, and risk constraints, where should capital be allocated?"*
   - Valid, supported answer: **"NOWHERE"** (100% Cash Allocation).
2. **Deterministic Risk Boundary:**
   - The Risk Engine is a non-negotiable hard boundary. If AI/Strategy says `BUY` and Risk Engine says `REJECT` $\implies$ **`REJECT`** (Always).
3. **Statistical Significance $\neq$ Tradeable Alpha:**
   - Statistical significance proves non-randomness under the null hypothesis.
   - Tradeable Alpha requires positive post-friction return, flat parameter curvature, low PBO ($< 0.25$), and un-retuned out-of-sample survival ($\text{SR}_{\text{OOS}} \ge 0.50 \cdot \text{SR}_{\text{IS}}$).
4. **No Speculative AI Trading Bots:**
   - AI is strictly an analytical component, never the final execution authority.

---

## 2. 7-Layer Modular Monolith Architecture

```
                               ACASH SYSTEM CORE
                                      │
                      ┌───────────────┴───────────────┐
                      │                               │
             1. RESEARCH DATA LAYER          2. ANALYTICS & RESEARCH
           (Parquet + DuckDB + yfinance)    (pandas + NumPy + vectorbt + Plotly)
                      │                               │
                      └───────────────┬───────────────┘
                                      │
                                      ▼
                                3. ALPHA ENGINE
                         (Signals & Expected Returns)
                                      │
                                      ▼
                             4. VALIDATION ENGINE
                        (Purged CPCV & DSR/OOS Gate)
                                      │
                                      ▼
                             5. PORTFOLIO ENGINE
                     (skfolio + Baselines: EW/InvVol/Cash)
                                      │
                                      ▼
                               6. RISK ENGINE
                      (Hard Deterministic Boundary)
                                      │
                                      ▼
                             7. EXECUTION ENGINE
                             (IExecutionEngine)
                                /           \
                          MT5 Adapter      NautilusTrader Substrate
                          (Phase 12)       (Phase 5 Gate Passed)
                                │
                                ▼
                   LOCAL TRANSACTIONAL CONTROL PLANE
                      (SQLite Append-Only Ledger)
```

### Technology Decision Matrix
| Technology | Role in ACASH | Status | Architectural Invariant |
| :--- | :--- | :--- | :--- |
| **ACASH Core** | Sovereign Domain Logic | **ADOPT** | Strict Decimal finite arithmetic, immutable state transitions. |
| **Parquet + DuckDB** | Analytical Storage | **ADOPT** | Partitioned immutable parts, DuckDB Point-in-Time qualification SQL. |
| **SQLite** | Operational Control Plane | **ADOPT** | Local ACID transactional state, append-only decision audit ledger. |
| **NautilusTrader** | Simulation Substrate | **ADOPT** | Unmocked event backtest substrate, Level-2 depth sweeps, order lifecycle. |
| **skfolio** | Portfolio Optimization | **ADOPT** | HRP, ERC, CVaR evaluated strictly against Equal Weight & Cash baselines. |
| **vectorbt (OSS)** | Rapid Factor Screening | **ADAPT** | Tier-1 Numba-accelerated fast parameter sweeps and screening. |
| **Plotly** | Visualization | **ADOPT** | Interactive research tear sheets and Reality Gap visualizers. |
| **PostgreSQL** | Enterprise Control Plane| **DEFERRED**| Reconsidered only when multi-user/concurrent network needs arise. |
| **MetaTrader 5** | Execution Gateway | **ADAPT** | Thin Windows IPC broker gateway; zero strategy logic in MQL5. |

---

## 3. Domain Flow & Lifecycle Hierarchy

```
        CAPITAL & PORTFOLIO STATE FLOW                DECISION & EXECUTION FLOW
        ──────────────────────────────                ─────────────────────────
                 AccountState                                   Signal
                      │                                           │
                      ▼                                           ▼
                PortfolioState                             TargetAllocation
                      │                                           │
                      ▼                                           ▼
                  Positions                                RiskAssessment
                      │                                           │
                      ▼                                           ▼
        State Transition (NEW Snapshots)                  OrderIntent / Order
        ├── NEW Position                                          │
        ├── NEW PortfolioState                                    ▼
        └── NEW AccountState                                     Fill
                                                                  │
                                            ──────────────────────┘
                      CROSS-CUTTING AUDIT LINEAGE
                      ───────────────────────────
                             DecisionRecord
                (Append-Only: never overwritten or deleted)
```

---

## 4. Mathematical & Statistical Formulas (Phases 1–6)

### 4.1 Accounting & Balance Sheet Invariants (Phase 1 & 5)
- **Balance Sheet Equity Conservation:**
  $$\text{Equity} = \text{Cash Balance} + \sum_{i} (\text{Unrealized PnL}_i)$$
- **Performance Attribution Equity:**
  $$\text{Equity}_{\text{attr}} = \text{Initial Cash} + \text{Realized PnL} + \text{Unrealized PnL} - \text{Total Fees}$$
- **Double-Entry Conservation Invariant:**
  $$|\text{Equity}_{\text{balance\_sheet}} - \text{Equity}_{\text{attribution}}| \le 10^{-10}$$
- **Contract Multiplier Scaling:**
  $$\text{Realized PnL} = (\text{Exit Price} - \text{Entry Price}) \times \text{Closed Qty} \times \text{Multiplier} - \text{Fees}$$

### 4.2 Bi-Temporal Point-in-Time Qualification (Phase 2 & 3)
- **Dual-Temporal Query Constraint:**
  $$T_{\text{event}} \le T_{\text{decision}} \quad \land \quad T_{\text{knowledge}} \le T_{\text{as\_of}}$$
- **DuckDB PIT Qualification Query:**
  ```sql
  QUALIFY ROW_NUMBER() OVER (
      PARTITION BY source_id, symbol, timeframe, event_start_utc
      ORDER BY knowledge_time_utc DESC, revision_seq DESC
  ) = 1
  ```

### 4.3 Market Microstructure & Features (Phase 3)
- **Session VWAP & Dispersion:**
  $$\text{VWAP}_t = \frac{\sum_{i=1}^t P_i \cdot V_i}{\sum_{i=1}^t V_i}, \quad \sigma_t = \sqrt{\frac{\sum_{i=1}^t V_i (P_i - \text{VWAP}_t)^2}{\sum_{i=1}^t V_i}}$$
- **Order Book Imbalance (OBI) & Micro-Price:**
  $$\text{OBI}_t = \frac{V_t^b - V_t^a}{V_t^b + V_t^a}, \quad P_t^{\text{micro}} = \frac{V_t^b \cdot P_t^a + V_t^a \cdot P_t^b}{V_t^b + V_t^a}$$

### 4.4 Alpha Econometric Inference & HAC (Phase 4)
- **Discrete Forward Return:**
  $$R(t, H) = \frac{P_{\text{close}, t+H} - P_{\text{open}, t+1}}{P_{\text{open}, t+1}}$$
- **OLS Slope & Regression Score Process:**
  $$\hat{\beta}_H = \frac{\sum (X_t - \bar{X})(Y_t - \bar{Y})}{\sum (X_t - \bar{X})^2}, \quad g_t = (X_t - \bar{X})\hat{\epsilon}_t$$
- **Andrews (1991) AR(1) Bartlett Kernel Plug-in:**
  $$S_T = \left\lfloor 1.1447 \cdot (\hat{\alpha}(1) \cdot T)^{1/3} \right\rfloor \quad \text{where} \quad \hat{\alpha}(1) = \frac{4\hat{\rho}^2}{(1 - \hat{\rho}^2)^2}$$

### 4.5 Reality Gap Decomposition (Phase 5)
$$\text{Reality Gap} = \text{Analytical Edge} - \text{Simulated Realized Return}$$
$$\text{Reality Gap} = \Delta_{\text{spread}} + \Delta_{\text{slippage}} + \Delta_{\text{latency}} + \Delta_{\text{fee}} + \Delta_{\text{maker\_adverse\_selection}} + \text{Unmodelled Residual}$$

### 4.6 Statistical Validation & Overfitting Controls (Phase 6)
- **Combinatorial Purged Cross-Validation (CPCV):**
  - $N$ groups, $k$ test groups $\implies C = \binom{N}{k}$ combinations.
  - Generates $\phi = \frac{k}{N}\binom{N}{k}$ continuous, non-overlapping pseudo-OOS backtest paths.
  - Purging: Training $t$ purged if $(t+1 < g_{\text{end}}) \land (t+H \ge g_{\text{start}})$.
  - Embargoing: Training $t$ embargoed if $g_{\text{end}} \le t < g_{\text{end}} + \text{embargo\_bars}$.
- **Deflated Sharpe Ratio (DSR):**
  $$DSR = \Phi \left( \frac{(\widehat{SR} - SR_0)\sqrt{T-1}}{\sqrt{1 - g_1 \widehat{SR} + \frac{g_2 - 1}{4}\widehat{SR}^2}} \right)$$
  - Expected maximum null Sharpe ($SR_0$) for $K$ trials with Euler-Mascheroni constant $\gamma_E \approx 0.5772$:
    $$SR_0 = \sqrt{V} \left( (1 - \gamma_E) Z^{-1}\left(1 - \frac{1}{K}\right) + \gamma_E Z^{-1}\left(1 - \frac{1}{K \cdot e}\right) \right)$$
  - Minimum Track Record Length (MinTRL):
    $$\text{MinTRL} = 1 + \left(1 - g_1 \widehat{SR} + \frac{g_2 - 1}{4}\widehat{SR}^2\right) \left(\frac{Z_\alpha}{\widehat{SR} - SR_0}\right)^2$$
- **Multiple Testing Corrections:**
  - Holm-Bonferroni (FWER): $p_{\text{adj},(i)} = \min(1.0, \max(p_{\text{adj},(i-1)}, (K - i + 1) p_{(i)}))$.
  - Harvey-Liu-Zhu Haircut Sharpe: $\text{Haircut\_SR} = \max\left(0, \widehat{SR} - \frac{\sqrt{2 \ln K}}{\sqrt{T}}\right)$.
- **Probability of Backtest Overfitting (PBO):**
  - Mid-Rank Relative OOS Score: $\omega_k = \frac{\text{MidRank}(x_k)}{M + 1} \implies \lambda = \ln\left(\frac{\omega}{1-\omega}\right) \implies \text{PBO} = \mathbb{P}(\lambda < 0)$.
- **Parameter Sensitivity Curvature:**
  - Evaluated on strict $[\theta_0 \cdot 0.75, \theta_0, \theta_0 \cdot 1.25]$ grid:
    $$\kappa = \left| \frac{SR(1.25\theta_0) - 2SR(\theta_0) + SR(0.75\theta_0)}{(0.25\theta_0)^2} \right|, \quad \text{Degradation} \le 30\%$$

---

## 5. Completed Quality Gates Matrix (Phases 0–6)

| Phase | Subsystem | Key Output | Verification Metric | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Discovery & Architecture | ADR-001 to ADR-019 | 17 technologies evaluated | ✅ **PASSED** |
| **Phase 1** | Foundation & Domain Core | Domain entities, pure state transitions | 27/27 unit tests, mypy clean | ✅ **GATE 1** |
| **Phase 2** | Ingestion & Storage Engine | Arrow schema, Parquet parts, DuckDB PIT | 57/57 unit tests, mypy clean | ✅ **GATE 2** |
| **Phase 3** | Microstructure & Features | Trades, L2/L3 Book, VWAP, OBI, Footprint | 122/122 unit tests, mypy clean | ✅ **GATE 3** |
| **Phase 4** | Alpha Engine & Hypotheses | Pre-registered hypotheses, HAC $\hat{\beta}_H$, Blind OOS | 139/139 unit tests, mypy clean | ✅ **GATE 4** |
| **Phase 5** | Backtesting & Simulation | Nautilus substrate, Reality Gap drag telemetry | 200/200 unit tests, mypy clean | ✅ **GATE 5** |
| **Phase 6** | Statistical Validation Gate | CPCV, DSR, MinTRL, PBO, Search Ledger | 235/235 unit tests, mypy clean | ✅ **GATE 6** |



---

## 6. Quant Research & Engineering Rules of Engagement

1. **Append-Only Immutability:** Historical `DecisionRecord` and `ProvenanceManifest` records are immutable. Never update or mutate past records to attach future execution outcomes.
2. **Search Intensity Invariance:** Every parameter variation, feature candidate, and model exploration MUST be recorded in the `SearchTrialLedger` ($K_{\text{ledger}} \equiv K_{\text{DSR}} \equiv K_{\text{Holm}} \equiv K_{\text{BH}}$).
3. **Fail-Closed Out-of-Sample Gate:** No strategy can be marked `PASS_TRADEABLE_ALPHA` without verified Out-of-Sample execution data ($\text{SR}_{\text{OOS}} \ge 0.50 \cdot \text{SR}_{\text{IS}}$).
4. **Dual Cryptographic Lineage:**
   - `evidence_digest`: Hash of underlying mathematical return series and computed statistics.
   - `decision_digest`: Hash of evidence digest + governance verdict + gating thresholds.
   - `created_timestamp_utc`: Preserved strictly as auxiliary runtime metadata.

---

## 7. Core Engineering Execution Loop

$$\text{INSPECT} \to \text{UNDERSTAND} \to \text{PLAN} \to \text{APPROVE} \to \text{IMPLEMENT} \to \text{TEST} \to \text{SELF-REVIEW} \to \text{DOCUMENT}$$
