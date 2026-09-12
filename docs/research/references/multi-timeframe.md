# Multi-Timeframe (MTF) Context & Aggregation Architecture

**Status:** ARCHITECTURAL_CONCEPT — Timeframe Hierarchy & Aggregation Pipeline  
**Canonical Governance Authority:** Non-Executable Research Reference. Does NOT authorize backtest, paper trading, or live execution. Does NOT create HYP_003. Preserves Canonical Capital = $0.00 and NO_REAL_ORDERS = true.

---

## 1. Executive Summary & Epistemic Boundary

Multi-Timeframe (MTF) analysis is an established quantitative and discretionary methodology for structuring market data across multiple temporal horizons.

> [!IMPORTANT]
> **Epistemic Note:**
> - Specific timeframe combinations (e.g., Daily/H4/H1/M15/M5/M1) are **heuristic structuring methodologies**, NOT proven physical or mathematical truths.
> - Multi-timeframe structures are **contextual frameworks**, NOT active trading strategies.
> - Any MTF feature pipeline must prove incremental predictive value after transaction costs and execution slippage under rigorous out-of-sample statistical testing.

---

## 2. Conceptual Timeframe Hierarchies

### 2.1 Canonical Institutional Hierarchy
In systematic macro and quantitative trend frameworks, timeframes serve distinct functional roles:

```text
     DAILY (D)      → Macro Regime, Volatility Environment & Major Context
        ↓
    4-HOUR (H4)     → Structural Market Regime & Swing Trend Direction
        ↓
    1-HOUR (H1)     → Intermediate Setup Context & Local Range Constraints
        ↓
   15-MINUTE (M15)  → Entry Context & Intraday Liquidity Levels
        ↓
    5-MINUTE (M5)   → Setup Refinement & Microstructure Clustered Context
        ↓
    1-MINUTE (M1)   → Execution Level, Spread Minimization & Fill Urgency
```

### 2.2 Alternative Multi-Resolution Mapping
A common relative-scale framework maps timeframes in 4x to 6x compression ratios:
- **D $	o$ H1:** Macro trend contextualizes intraday cycles.
- **H4 $	o$ M15:** Structural swings contextualize local breakout attempts.
- **H1 $	o$ M5:** Intraday momentum contextualizes order flow imbalances.
- **M15 $	o$ M1:** Execution window contextualizes order placement and slippage.

---

## 3. Deterministic Bottom-Up Data Aggregation

To prevent lookahead bias and temporal synchronization errors, all multi-timeframe data must be synthesized strictly **bottom-up** from the lowest canonical stream (M1 bars or tick data):

```text
                  M1 CANONICAL FEED (Real-Time Ingestion)
                             │
                             ├──────────────────────┐
                             ↓                      ↓
                     M5 AGGREGATOR          Direct M1 Features
                             │
                             ├──────────────────────┐
                             ↓                      ↓
                    M15 AGGREGATOR          Direct M5 Features
                             │
                             ├──────────────────────┐
                             ↓                      ↓
                     H1 AGGREGATOR          Direct M15 Features
                             │
                             ├──────────────────────┐
                             ↓                      ↓
                     H4 AGGREGATOR          Direct H1 Features
                             │
                             ↓
                     DAILY AGGREGATOR
```

### Temporal Integrity Invariants:
1. **Zero Lookahead Leakage:** A higher timeframe bar (e.g., H1) is only marked as closed and made available for feature calculation when its final constituent M1 bar (e.g., minute 59) has closed and sealed.
2. **Session Alignment:** Bar boundaries must be strictly aligned to standard UTC boundaries (00:00 UTC) to avoid time-zone drifting.
3. **Point-in-Time Availability:** Features computed on higher timeframes must record explicit observation timestamps reflecting the exact moment they became available to the model.

---

## 4. Role of Order Flow within the MTF Hierarchy

Order flow must be positioned correctly within the architectural hierarchy:

```text
                  HIGH-TIMEFRAME CONTEXT (D / H4)
                    [Macro Regime & Trend State]
                                 ↓
                 INTERMEDIATE STRUCTURE (H1 / M15)
                     [Key Liquidity / Range Bounds]
                                 ↓
                   ORDER FLOW CONTEXT (M5 / M1)
                  [Aggressive Flow & Absorption]
                                 ↓
                     EXECUTION DECISION (M1)
                   [Limit / TWAP Order Routing]
```

**Key Architectural Rule:**  
Order flow is **contextual feature input** at the micro-horizon; it is **NOT** the sovereign strategy. High-timeframe structural regimes dictate whether a micro-horizon order flow imbalance warrants exposure or should be discarded as transient noise.
