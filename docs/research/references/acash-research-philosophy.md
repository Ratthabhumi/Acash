# Unified ACASH Research Philosophy & Architecture

**Status:** METHODOLOGY REFERENCE — Architectural Framework & Core Principles  
**Canonical Governance Authority:** Non-Executable Research Reference. Does NOT authorize backtest, paper trading, or live execution. Does NOT create HYP_003. Preserves Canonical Capital = $0.00 and NO_REAL_ORDERS = true.

---

## 1. The Unified ACASH Research Lifecycle

The fundamental research doctrine of ACASH dictates an unbroken chain of scientific validation from raw reality to human governance:

```text
                    MARKET REALITY (Ticks, Order Books, Quotes)
                          ↓
                    INFORMATION (Validated Raw Ingestion)
                          ↓
                  MARKET FEATURES (Multi-Scale Deterministic Transforms)
                          ↓
                  SIMPLE HYPOTHESIS (Economic Mechanism Grounding)
                          ↓
                        MODEL (Parsimonious Mathematical Form)
                          ↓
                     BACKTEST (In-Sample Historical Evaluation)
                          ↓
                 COST / SLIPPAGE (Full Friction Deductions)
                          ↓
                        OOS (Out-of-Sample Empirical Testing)
                          ↓
                  ROBUSTNESS TEST (Walk-Forward & Permutation Tests)
                          ↓
                     RISK ENGINE (Autonomous Exposure Ceilings)
                          ↓
                  POSITION SIZING (Fractional Sizing Under Uncertainty)
                          ↓
                  PAPER / OBSERVE (Non-Capital Production Soak)
                          ↓
                   DECAY MONITOR (Continuous Edge Degradation Tracking)
                          ↓
                HUMAN AUTHORIZATION (Sovereign Human Ratification Gate)
```

---

## 2. Unified Market-Data Architecture

The conceptual architecture for systematic multi-asset data flow decouples market ingestion, feature transformation, hypothesis testing, and risk-managed execution:

```text
                    REAL MARKET DATA
                           │
          ┌────────────────┼────────────────┐
          │                │                │
        OHLCV          ORDER FLOW       ORDER BOOK
     (Time-Based)    (Tick / Delta)   (L2 / L3 Depth)
          │                │                │
          └────────────────┼────────────────┘
                           │
                     FEATURE ENGINE
                           │
               ┌───────────┼───────────┐
               │           │           │
              HTF         MTF         LTF
            Context      Context     Execution
          (Daily/H4)    (H1/M15)     (M5/M1)
               │           │           │
               └───────────┼───────────┘
                           │
                    HYPOTHESIS ENGINE
                           │
                       BACKTEST
                           │
                      VALIDATION
                           │
                     RISK ENGINE
                           │
                    POSITION SIZE
                           │
                     EXECUTION
```

---

## 3. Future Feature Family Taxonomy

A comprehensive map of candidate feature domains for future authorized research:

1. **Price Features:** Log-returns, rolling realized volatility, ATR, Parkinson volatility, multi-scale trend indicators.
2. **Volume Features:** Volume moving averages, relative volume (RVOL), volume concentration, volume surprise metrics.
3. **Factor Features:** Systematic market beta, value metrics, size metrics, momentum scores, factor attribution loadings.
4. **Order Flow Features:** Aggressive buy/sell volume, volume delta ($\Delta V$), Cumulative Volume Delta (CVD), order count imbalance.
5. **Order Book Features:** L2/L3 bid-ask depth, book imbalance ($I_{OB}$), micro-price, depth concentration, quote cancellation rates.
6. **Options & Derivatives:** Implied volatility (IV), IV skew, volatility surface slope, open interest (OI) concentration, put/call ratios.
7. **Macro Features:** Interest rate differentials, sovereign yield spreads, central bank policy regime indicators (strictly when authorized).
8. **Multi-Timeframe Features:** Macro trend filters (Daily), intermediate structure (H4/H1), tactical setup context (M15/M5).
9. **Execution Features:** Effective spread, realized spread, implementation shortfall, market impact estimates, fill latency.

---

## 4. The 10 Important ACASH Epistemic Principles

1. **INFORMATION != EDGE**
   - Accumulating more data or complex feeds does not automatically create statistical alpha. Most market data is noise.
2. **SIGNAL != POSITION**
   - A signal provides directional conviction; it never determines position size. The sovereign Risk Engine unilaterally dictates exposure.
3. **RETURN != SKILL**
   - Raw performance in a bull market is typically unhedged market beta, factor exposure, or excessive leverage, not active skill.
4. **BACKTEST != FUTURE PROFITABILITY**
   - A backtest demonstrates only what happened in a past sample. It is a tool for falsifying bad ideas, not a guarantee of future gains.
5. **COMPLEXITY HAS A COST**
   - Every additional parameter, filter, or rule exponentially increases overfitting risk. Simple mechanisms survive; complex contraptions fail.
6. **REAL-WORLD EXECUTION MATTERS**
   - Net performance is the only metric that matters:
     $$	ext{Net} = 	ext{Gross} - 	ext{Exchange Fees} - 	ext{Bid/Ask Spread} - 	ext{Slippage} - 	ext{Market Impact} - 	ext{Latency}$$
7. **RISK COMES BEFORE CAPITAL DEPLOYMENT**
   - Survival precedes growth. Every opportunity must pass strict risk constraints before a single dollar of capital is risked.
8. **EDGE HAS A LIFECYCLE**
   - Systematic edges inevitably decay. Systems must monitor for degradation and gracefully quarantine and retire underperforming models.
9. **CORRELATION DOES NOT GUARANTEE DIVERSIFICATION**
   - During liquidity panics, asset and strategy correlations spike to 1.0. Diversification must be measured across non-linear stress regimes.
10. **OBSERVABLE VARIABLES ARE PREFERRED OVER STORIES**
    - Prefer measurable quantities (`AGGRESSIVE_BUY_VOLUME = X`) over psychological narratives (`SMART_MONEY_IS_BUYING`).

---

## 5. Research Prioritization & Tiering Matrix

ACASH organizes future research into three distinct tiers:

### TIER 1 — High Value Quantitative Foundations
- Modern Portfolio Theory & Covariance Engines (Markowitz)
- Optimal Growth & Fractional Sizing Frameworks (Kelly)
- Market Efficiency & Joint-Hypothesis Falsification Controls (Fama)
- Information Value Economics & Anti-Bloat Controls (Grossman–Stiglitz)
- Multi-Factor Decomposition & Attribution (Fama–French)
- Optimal Execution Modeling & Market Impact (Almgren–Chriss)

### TIER 2 — Future Data & Feature Exploration
- Deterministic Multi-Timeframe Bar Aggregation (M1 to Daily)
- Quantitative Order Book Imbalance & Depth Dynamics
- Aggressive Volume Delta & Tape Cluster Analytics
- Derivatives Implied Volatility Surface & Open Interest Conditioning

### TIER 3 — Unverified Candidate Ideas (Strict Falsification Queue)
- Engulfing Candle & Fibonacci Quadrant Patterns
- Discretionary Liquidity Sweeps / "Manipulation" Claims
- Narrative-Based Order Flow Indicators

> **Governance Invariant:** Tier 3 items must NEVER be represented as validated alpha or active strategies. They are quarantined candidate ideas subject to formal mathematical decomposition and empirical falsification.
