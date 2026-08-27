# ACASH — Phase 3C: Microstructure Feature Engine Design Proposal & Reproducibility Contract

**Document:** `docs/PHASE_3C_DESIGN_PROPOSAL.md`  
**Version:** 1.0.0  
**Date:** 2026-08-28  
**Status:** **PROPOSED — AWAITING REVIEW & SIGN-OFF**  

---

## 1. Executive Summary & Architectural Separation

In quantitative market microstructure research, **Features** are **downstream mathematical interpretations and analytical aggregates**, strictly decoupled from **Canonical Market Observations (Trades in Phase 3A, Order Books in Phase 3B)**.

```
                           CANONICAL MARKET DATA LAYER
              ┌──────────────────────────┴──────────────────────────┐
              ▼                                                     ▼
     CANONICAL TRADES (3A)                                 RECONSTRUCTED BOOK (3B)
  (Price, Size, Aggressor Side)                        (Top-N Bids/Asks Price & Size)
              │                                                     │
              └──────────────────────────┬──────────────────────────┘
                                         │
                                         ▼ (Dual-Temporal PIT Stream)
                       ┌───────────────────────────────────┐
                       │   MICROSTRUCTURE FEATURE ENGINE   │
                       │   - Pure Mathematical Functions   │
                       │   - Configurable Research Params  │
                       │   - Versioned Feature Manifests   │
                       │   - Anti-Lookahead Guarantees     │
                       └─────────────────┬─────────────────┘
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 ▼                       ▼                       ▼
           VOLUME ANALYTICS       ORDER FLOW & CVD        BOOK MICROSTRUCTURE
        - Session VWAP & Bands  - Bar Delta & CVD       - Top-N Book Imbalance (OBI)
        - Volume Profile (POC)  - Diagonal Imbalance    - Depth Weighted Micro-Price
        - Value Area (VAH/VAL)  - Absorption Detector   - Effective Spread Dynamics
                 │                       │                       │
                 └───────────────────────┼───────────────────────┘
                                         │
                                         ▼
                            PARQUET FEATURE STORAGE &
                           DETERMINISTIC MANIFEST REPLAY
```

> [!IMPORTANT]
> **Strict Separation of Concerns:**
> 1. **Downstream Interpretation Only:** Features do NOT modify or replace canonical trades or order book events.
> 2. **Configurable Research Conventions:** Analytical thresholds (e.g. `value_area_pct = 0.70`, `imbalance_ratio = 3.0`, `absorption_volume_multiplier = 2.5`) are research parameters, NOT universal market truths.
> 3. **Zero Strategy Logic:** Phase 3C strictly computes quantitative features and statistics; it contains **ZERO BUY/SELL recommendations, trade signals, or execution decisions** (which are reserved for Phase 4+).

---

## 2. Mathematical Feature Specifications

### 2.1 Volume Weighted Average Price (VWAP) & Dispersion Bands
For a sequence of trade events $i \in \{1 \dots K\}$ within a trading session up to target exchange time $T_{\text{target}}$:

$$\text{VWAP}(t) = \frac{\sum_{i: t_i \le t} P_i \cdot V_i}{\sum_{i: t_i \le t} V_i}$$

$$\sigma_{\text{VWAP}}(t) = \sqrt{\frac{\sum_{i: t_i \le t} (P_i - \text{VWAP}(t))^2 \cdot V_i}{\sum_{i: t_i \le t} V_i}}$$

$$\text{Band}_{k\sigma}^{\pm}(t) = \text{VWAP}(t) \pm k \cdot \sigma_{\text{VWAP}}(t), \quad k \in \{1, 2, 3\}$$

---

### 2.2 Volume Profile & Auction Market Theory
Given discrete price ticks $P \in \mathcal{P}$:
1. **Price Level Volume Aggregation:**
   $$V(P) = \sum_{i: P_i = P} V_i, \quad V_{\text{buy}}(P) = \sum_{i: P_i = P, \text{aggressor}=\text{"BUY"}} V_i, \quad V_{\text{sell}}(P) = \sum_{i: P_i = P, \text{aggressor}=\text{"SELL"}} V_i$$
2. **Point of Control (POC):**
   $$P_{\text{POC}} = \arg\max_{P} V(P)$$
   *(Deterministic tie-breaker: Lowest price among maxima if identical).*
3. **Value Area (VAH & VAL):**
   The continuous range $[P_{\text{VAL}}, P_{\text{VAH}}]$ containing a configurable fraction $\gamma$ (default $\gamma = 0.70$) of total session volume $\sum V(P)$, expanded iteratively from $P_{\text{POC}}$ comparing upper and lower adjacent volume pairs.
4. **Volume Nodes:**
   - **High Volume Nodes (HVN):** Local maxima in the smoothed volume profile exceeding configurable percentile threshold $\theta_{\text{hvn}}$.
   - **Low Volume Nodes (LVN):** Local minima in the smoothed volume profile below configurable percentile threshold $\theta_{\text{lvn}}$.

---

### 2.3 Footprint Analytics, Delta & CVD
For a time-bar or range-bar window $B = [T_{\text{start}}, T_{\text{end}}]$:
1. **Bar Volume Delta & Cumulative Volume Delta (CVD):**
   $$\Delta_B = V_{\text{buy}, B} - V_{\text{sell}, B} = \sum_{i \in B, \text{aggressor}=\text{"BUY"}} V_i - \sum_{i \in B, \text{aggressor}=\text{"SELL"}} V_i$$
   $$\text{CVD}_k = \sum_{j=1}^k \Delta_j$$
2. **Price-Level Diagonal Bid/Ask Imbalance:**
   Comparing buying aggressive volume at price $P + \text{tick\_size}$ against selling aggressive volume at price $P$:
   $$\text{Imbalance}_{\text{bid}}(P) = \left( V_{\text{sell}}(P) \ge R_{\text{imb}} \cdot V_{\text{buy}}(P + \text{tick}) \right) \land \left( V_{\text{sell}}(P) - V_{\text{buy}}(P + \text{tick}) \ge V_{\text{min\_diff}} \right)$$
   $$\text{Imbalance}_{\text{ask}}(P + \text{tick}) = \left( V_{\text{buy}}(P + \text{tick}) \ge R_{\text{imb}} \cdot V_{\text{sell}}(P) \right) \land \left( V_{\text{buy}}(P + \text{tick}) - V_{\text{sell}}(P) \ge V_{\text{min\_diff}} \right)$$
   *(Configurable parameters: $R_{\text{imb}} = 3.0$, $V_{\text{min\_diff}} = 10$).*
3. **Stacked Imbalances:**
   A sequence of $N \ge 3$ contiguous price levels exhibiting unidirectional diagonal imbalance.
4. **Absorption Detection:**
   High volume cluster ($V(P) \ge \mu_V + k \cdot \sigma_V$) occurring at bar high/low where aggressive market orders fail to push price further (zero price continuation).

---

### 2.4 Order Book Microstructure Signals
Given the reconstructed Top-$N$ Depth Ladder $(P_{\text{bid}, j}, Q_{\text{bid}, j})$ and $(P_{\text{ask}, j}, Q_{\text{ask}, j})$ for $j \in \{0 \dots N-1\}$:
1. **Top-$N$ Order Book Imbalance (OBI):**
   $$\text{OBI}_N = \frac{\sum_{j=0}^{N-1} w_j \cdot Q_{\text{bid}, j} - \sum_{j=0}^{N-1} w_j \cdot Q_{\text{ask}, j}}{\sum_{j=0}^{N-1} w_j \cdot Q_{\text{bid}, j} + \sum_{j=0}^{N-1} w_j \cdot Q_{\text{ask}, j}}, \quad \text{where } w_j = \frac{1}{j + 1} \text{ or uniform } 1$$
2. **Depth-Weighted Micro-Price:**
   $$P_{\text{micro}} = \frac{Q_{\text{bid}, 0} \cdot P_{\text{ask}, 0} + Q_{\text{ask}, 0} \cdot P_{\text{bid}, 0}}{Q_{\text{bid}, 0} + Q_{\text{ask}, 0}}$$
   $$P_{\text{micro}, N} = \frac{\left(\sum w_j Q_{\text{bid}, j}\right) P_{\text{ask}, 0} + \left(\sum w_j Q_{\text{ask}, j}\right) P_{\text{bid}, 0}}{\sum w_j Q_{\text{bid}, j} + \sum w_j Q_{\text{ask}, j}}$$
3. **Quoted Spread & Depth Liquidity:**
   $$\text{Spread} = P_{\text{ask}, 0} - P_{\text{bid}, 0}, \quad \text{Depth}_{\text{total}} = \sum_{j=0}^{N-1} (Q_{\text{bid}, j} + Q_{\text{ask}, j})$$

---

## 3. Deterministic Feature Reproducibility Contract & Feature Manifest

> [!IMPORTANT]
> **Deterministic Feature Lineage:**
> Every computed feature dataset is accompanied by a cryptographically signed **`FeatureManifest`** that uniquely links:
> 1. Canonical Trades batch fingerprint (`input_trades_sha256`).
> 2. Canonical Order Book snapshot/delta fingerprint (`input_book_sha256`).
> 3. Parameter configuration cryptographic hash (`parameter_config_sha256`).
> 4. Software version (`software_version`).
> 5. Output feature Parquet logical fingerprint (`feature_output_sha256`).

```python
class FeatureManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    feature_set_name: str           # e.g. "session_microstructure_v1"
    symbol: str
    trading_date: str               # ISO "YYYY-MM-DD"
    input_trades_sha256: Optional[str]
    input_book_sha256: Optional[str]
    parameter_config_sha256: str    # Hash of JSON-serialized parameter values
    parameter_config_json: str      # Exact parameters used
    software_version: str           # Package version
    feature_output_sha256: str      # Deterministic binary hash of output table
    row_count: int
    min_event_time_utc: str
    max_event_time_utc: str
    computed_at_utc: str
```

---

## 4. PyArrow Feature Storage Schemas

### 4.1 Trade Flow Features Schema (`CANONICAL_TRADE_FEATURES_SCHEMA`)
```python
CANONICAL_TRADE_FEATURES_SCHEMA = pa.schema([
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("bar_start_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("bar_end_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("open", pa.decimal128(38, 18), nullable=False),
    pa.field("high", pa.decimal128(38, 18), nullable=False),
    pa.field("low", pa.decimal128(38, 18), nullable=False),
    pa.field("close", pa.decimal128(38, 18), nullable=False),
    pa.field("volume", pa.decimal128(38, 18), nullable=False),
    pa.field("buy_volume", pa.decimal128(38, 18), nullable=False),
    pa.field("sell_volume", pa.decimal128(38, 18), nullable=False),
    pa.field("delta", pa.decimal128(38, 18), nullable=False),
    pa.field("cvd", pa.decimal128(38, 18), nullable=False),
    pa.field("vwap", pa.decimal128(38, 18), nullable=False),
    pa.field("vwap_std", pa.decimal128(38, 18), nullable=False),
    pa.field("poc_price", pa.decimal128(38, 18), nullable=False),
    pa.field("vah_price", pa.decimal128(38, 18), nullable=False),
    pa.field("val_price", pa.decimal128(38, 18), nullable=False),
    pa.field("has_stacked_buy_imbalance", pa.bool_(), nullable=False),
    pa.field("has_stacked_sell_imbalance", pa.bool_(), nullable=False),
    pa.field("is_absorption_bar", pa.bool_(), nullable=False),
])
```

### 4.2 Book Microstructure Features Schema (`CANONICAL_BOOK_FEATURES_SCHEMA`)
```python
CANONICAL_BOOK_FEATURES_SCHEMA = pa.schema([
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("exchange_time_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("spread", pa.decimal128(38, 18), nullable=False),
    pa.field("micro_price", pa.decimal128(38, 18), nullable=False),
    pa.field("obi_top1", pa.decimal128(38, 18), nullable=False),
    pa.field("obi_top5", pa.decimal128(38, 18), nullable=False),
    pa.field("obi_top10", pa.decimal128(38, 18), nullable=False),
    pa.field("total_bid_depth", pa.decimal128(38, 18), nullable=False),
    pa.field("total_ask_depth", pa.decimal128(38, 18), nullable=False),
    pa.field("is_crossed", pa.bool_(), nullable=False),
])
```

---

## 5. Anti-Leakage & Dual-Temporal PIT Invariants

> [!IMPORTANT]
> **Zero Future Information Leakage Invariant:**
> Feature computation for decision time $T_{\text{decision}}$ with knowledge cutoff $T_{\text{knowledge}}$:
> 1. **Temporal Query Boundary:** Consumes strictly trades/books with:
>    $$\text{exchange\_time\_utc} \le T_{\text{decision}} \quad \land \quad \text{knowledge\_time\_utc} \le T_{\text{knowledge}}$$
> 2. **Injected Future Event Test:** Injected future trades ($T_{\text{event}} > T_{\text{decision}}$) or future revisions ($T_{\text{knowledge}} > T_{\text{as\_of}}$) MUST produce zero change in the computed feature values for $T \le T_{\text{decision}}$.

---

## 6. Gate 3C Acceptance Criteria & Test Matrix

- [ ] **Configurable Parameter Hashing:** Parameter configurations are strictly validated, JSON-serialized, and hashed into `parameter_config_sha256`.
- [ ] **VWAP & Bands Correctness:** Mathematical unit test verifies exact VWAP and $\pm 1\sigma, \pm 2\sigma, \pm 3\sigma$ values against manual reference calculations.
- [ ] **Volume Profile & Value Area:** Verifies POC, VAH, VAL calculations across symmetric, skewed, and multi-modal volume distributions.
- [ ] **Footprint, Delta & CVD:** Verifies Price-level clusters, Bar Delta, CVD monotonicity, and Stacked Imbalance detection.
- [ ] **Order Book Microstructure (OBI & Micro-Price):** Verifies OBI top-1/top-5/top-10 and depth-weighted micro-price calculations against known book states.
- [ ] **Automated Anti-Leakage Test:** Injecting future trades and deltas strictly does not alter past feature outputs.
- [ ] **Feature Manifest Provenance & Deterministic Replay:** Recomputing features with identical inputs and configuration yields identical `feature_output_sha256`.
- [ ] **Zero Strategy / Zero Signal Logic:** Codebase audit confirms absence of BUY/SELL signals or trade triggers.
- [ ] **Full Regression Suite:** 100% pytest pass rate (all previous 109 tests + Phase 3C tests), 0 mypy errors.
