# ACASH — Phase 3C: Microstructure Feature Engine Design Proposal & Reproducibility Contract

**Document:** `docs/proposals/phase_3c_feature_engine.md`  
**Version:** 1.1.0  
**Date:** 2026-08-28  
**Status:** **PROPOSED — FINAL HARDENING (Awaiting Formal Sign-off)**  

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
                       │   - Temporal Lineage Manifests    │
                       │   - 4-Way Anti-Leakage Invariants │
                       └─────────────────┬─────────────────┘
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 ▼                       ▼                       ▼
           VOLUME ANALYTICS       ORDER FLOW & CVD        BOOK MICROSTRUCTURE
        - Session VWAP & Bands  - Bar Delta & CVD       - Top-N Book Imbalance (OBI)
        - Volume Profile (POC)  - Diagonal Imbalance    - Top-N Depth-Weighted BBO
        - Value Area (VAH/VAL)  - Absorption Detector     Micro-Price & Spread
                 │                       │                       │
                 └───────────────────────┼───────────────────────┘
                                         │
                                         ▼
                            PARQUET FEATURE STORAGE &
                           DETERMINISTIC MANIFEST REPLAY
```

> [!IMPORTANT]
> **Strict Separation of Concerns & Downstream Principles:**
> 1. **Downstream Interpretation Only:** Features do NOT modify or replace canonical trades or order book events.
> 2. **Configurable Research Conventions:** Analytical thresholds (e.g. `value_area_pct = 0.70`, `imbalance_ratio = 3.0`, `min_imbalance_volume_diff = 10`) are research conventions, NOT universal market truths.
> 3. **Zero Strategy Logic:** Phase 3C strictly computes quantitative features and statistics; it contains **ZERO BUY/SELL recommendations, trade signals, or execution decisions** (which are reserved for Phase 4+).

---

## 2. Mathematical Feature Specifications & Deterministic Invariants

### 2.1 Volume Weighted Average Price (VWAP) & Volume-Weighted Dispersion
For a sequence of trade events $i \in \{1 \dots K\}$ within a trading session up to target exchange time $T_{\text{target}}$ as known at $T_{\text{knowledge}} \le T_{\text{as\_of}}$:

$$\text{VWAP}(t) = \begin{cases} \frac{\sum_{i: t_i \le t} P_i \cdot V_i}{\sum_{i: t_i \le t} V_i} & \text{if } \sum V_i > 0 \\ \text{None} & \text{if } \sum V_i = 0 \end{cases}$$

$$\sigma_{\text{volume\_weighted}}(t) = \begin{cases} \sqrt{\frac{\sum_{i: t_i \le t} (P_i - \text{VWAP}(t))^2 \cdot V_i}{\sum_{i: t_i \le t} V_i}} & \text{if } \sum V_i > 0 \\ \text{None} & \text{if } \sum V_i = 0 \end{cases}$$

$$\text{Band}_{k\sigma}^{\pm}(t) = \text{VWAP}(t) \pm k \cdot \sigma_{\text{volume\_weighted}}(t), \quad k \in \{1, 2, 3\}$$

- **Population & Calendar:** Trade population is determined strictly by the session window defined in the session profile (`trading_date` calendar).
- **Zero Volume Handling:** When total volume is 0, $\text{VWAP}$ and dispersion evaluate to `None` (or null in Parquet) with status `NO_VOLUME`.

---

### 2.2 Volume Profile & Value Area Deterministic Algorithm
Given discrete price ticks $P \in \mathcal{P}$ aggregated from trade matches:
1. **Price Level Volume Aggregation:**
   $$V(P) = \sum_{i: P_i = P} V_i, \quad V_{\text{buy}}(P) = \sum_{i: P_i = P, \text{aggressor}=\text{"BUY"}} V_i, \quad V_{\text{sell}}(P) = \sum_{i: P_i = P, \text{aggressor}=\text{"SELL"}} V_i$$
2. **Point of Control (POC):**
   $$P_{\text{POC}} = \arg\max_{P} V(P)$$
   *Deterministic Tie-Breaker:* If multiple price levels share the exact same maximum volume, $P_{\text{POC}}$ selects the **lowest price** among the maxima.
3. **Value Area Algorithm ($P_{\text{VAL}}, P_{\text{VAH}}$):**
   - Let total session volume be $V_{\text{total}} = \sum_P V(P)$. If $V_{\text{total}} == 0$, $P_{\text{POC}}, P_{\text{VAH}}, P_{\text{VAL}} = \text{None}$.
   - Initialize Value Area with POC: $\mathcal{V} = \{P_{\text{POC}}\}, \; V_{\text{acc}} = V(P_{\text{POC}})$. Target volume is $\text{target\_volume} = \gamma \times V_{\text{total}}$ (default $\gamma = 0.70$).
   - Iteratively inspect adjacent upper tick $P_{\text{up}}$ and lower tick $P_{\text{down}}$:
     - If $V(P_{\text{up}}) > V(P_{\text{down}})$: add $P_{\text{up}}$ to $\mathcal{V}$, $V_{\text{acc}} \mathrel{+}= V(P_{\text{up}})$.
     - If $V(P_{\text{down}}) > V(P_{\text{up}})$: add $P_{\text{down}}$ to $\mathcal{V}$, $V_{\text{acc}} \mathrel{+}= V(P_{\text{down}})$.
     - **Deterministic Equal Volume Tie-Breaker:** If $V(P_{\text{down}}) == V(P_{\text{up}})$, add the **lower price level $P_{\text{down}}$ first**.
   - **Boundary Inclusion:** The price level whose addition causes $V_{\text{acc}} \ge \text{target\_volume}$ is **fully included** in $\mathcal{V}$.
   - $P_{\text{VAL}} = \min(\mathcal{V}), \quad P_{\text{VAH}} = \max(\mathcal{V})$.
   - Sparse price levels with zero volume are treated as $V(P) = 0$ without breaking iteration.

---

### 2.3 Order Flow, Footprint & Diagonal Imbalance Semantics
For a bar window $B = [T_{\text{start}}, T_{\text{end}}]$:
1. **Bar Volume Delta & Cumulative Volume Delta (CVD):**
   $$\Delta_B = V_{\text{buy}, B} - V_{\text{sell}, B} = \sum_{i \in B, \text{aggressor}=\text{"BUY"}} V_i - \sum_{i \in B, \text{aggressor}=\text{"SELL"}} V_i$$
   $$\text{CVD}_k = \sum_{j=1}^k \Delta_j$$
2. **Explicit Diagonal Imbalance Formulas & Zero-Volume Semantics:**
   Comparing buying aggressive volume at price $P + \text{tick}$ against selling aggressive volume at price $P$:
   - **Buy Diagonal Imbalance at Price $P + \text{tick}$:**
     $$\text{IsBuyImbalance}(P + \text{tick}) = \begin{cases} 
     \text{True} & \text{if } V_{\text{sell}}(P) == 0 \land V_{\text{buy}}(P + \text{tick}) \ge V_{\text{min\_diff}} \\
     \text{True} & \text{if } V_{\text{sell}}(P) > 0 \land V_{\text{buy}}(P + \text{tick}) \ge R_{\text{imb}} \cdot V_{\text{sell}}(P) \land (V_{\text{buy}}(P + \text{tick}) - V_{\text{sell}}(P)) \ge V_{\text{min\_diff}} \\
     \text{False} & \text{otherwise}
     \end{cases}$$
   - **Sell Diagonal Imbalance at Price $P$:**
     $$\text{IsSellImbalance}(P) = \begin{cases} 
     \text{True} & \text{if } V_{\text{buy}}(P + \text{tick}) == 0 \land V_{\text{sell}}(P) \ge V_{\text{min\_diff}} \\
     \text{True} & \text{if } V_{\text{buy}}(P + \text{tick}) > 0 \land V_{\text{sell}}(P) \ge R_{\text{imb}} \cdot V_{\text{buy}}(P + \text{tick}) \land (V_{\text{sell}}(P) - V_{\text{buy}}(P + \text{tick})) \ge V_{\text{min\_diff}} \\
     \text{False} & \text{otherwise}
     \end{cases}$$
   *(Default research baseline: $R_{\text{imb}} = 3.0$, $V_{\text{min\_diff}} = 10$). Division by zero is completely eliminated.*
3. **Stacked Imbalances:**
   $N \ge 3$ consecutive price levels with unidirectional diagonal imbalance.
4. **Absorption Detection:**
   A volume spike ($V(P) \ge \mu_V + k \cdot \sigma_V$) occurring at bar extremes (Bar High or Bar Low) where aggressive market orders fail to produce price progression.

---

### 2.4 Order Book Microstructure Signals
Given the reconstructed Top-$N$ Depth Ladder $(P_{\text{bid}, j}, Q_{\text{bid}, j})$ and $(P_{\text{ask}, j}, Q_{\text{ask}, j})$ for $j \in \{0 \dots N-1\}$:
1. **Top-$N$ Order Book Imbalance (OBI):**
   $$\text{OBI}_N = \frac{\sum_{j=0}^{N-1} w_j \cdot Q_{\text{bid}, j} - \sum_{j=0}^{N-1} w_j \cdot Q_{\text{ask}, j}}{\sum_{j=0}^{N-1} w_j \cdot Q_{\text{bid}, j} + \sum_{j=0}^{N-1} w_j \cdot Q_{\text{ask}, j}}, \quad \text{where } w_j = \frac{1}{j + 1} \text{ or uniform } 1$$
   *(If total depth is 0, $\text{OBI}_N = \text{Decimal('0')}$).*
2. **BBO Micro-Price & Top-$N$ Depth-Weighted BBO Micro-Price:**
   - **BBO Micro-Price (Level 0):**
     $$P_{\text{micro, BBO}} = \frac{Q_{\text{bid}, 0} \cdot P_{\text{ask}, 0} + Q_{\text{ask}, 0} \cdot P_{\text{bid}, 0}}{Q_{\text{bid}, 0} + Q_{\text{ask}, 0}}$$
   - **Top-$N$ Depth-Weighted BBO Micro-Price (Anchored to BBO Quotes with Depth Weights):**
     $$P_{\text{micro, Top-}N} = \frac{\left(\sum_{j=0}^{N-1} w_j Q_{\text{bid}, j}\right) P_{\text{ask}, 0} + \left(\sum_{j=0}^{N-1} w_j Q_{\text{ask}, j}\right) P_{\text{bid}, 0}}{\sum_{j=0}^{N-1} w_j Q_{\text{bid}, j} + \sum_{j=0}^{N-1} w_j Q_{\text{ask}, j}}$$
3. **Quoted Spread & Total Depth:**
   $$\text{Spread} = P_{\text{ask}, 0} - P_{\text{bid}, 0}, \quad \text{Depth}_{\text{total}} = \sum_{j=0}^{N-1} (Q_{\text{bid}, j} + Q_{\text{ask}, j})$$

---

## 3. Explicit Temporal Lineage Contract & `FeatureManifest`

> [!IMPORTANT]
> **Complete Temporal Lineage Contract:**
> Every computed feature dataset is accompanied by a cryptographically verified **`FeatureManifest`** containing complete execution and temporal coordinates:

```python
class FeatureManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str
    feature_set_name: str           # e.g. "session_trade_microstructure_v1"
    feature_definition_version: str # e.g. "1.1.0"
    symbol: str
    trading_date: str               # ISO "YYYY-MM-DD"
    
    # Explicit Temporal Coordinates
    decision_time_utc: str          # Target evaluation timestamp T_decision
    knowledge_cutoff_utc: str       # Maximum knowable timestamp T_knowledge
    input_event_start_utc: str      # Min event timestamp included in window
    input_event_end_utc: str        # Max event timestamp included in window
    
    # Cryptographic Provenance Hashes
    input_trades_sha256: Optional[str]
    input_book_sha256: Optional[str]
    parameter_config_sha256: str    # Hash of JSON-serialized parameter values
    parameter_config_json: str      # Full canonical parameter dictionary
    software_version: str           # e.g. "0.3.0"
    feature_output_sha256: str      # Binary SHA-256 fingerprint of output feature table
    
    row_count: int
    computed_at_utc: str
```

---

## 4. PyArrow Feature Storage Schemas

### 4.1 Trade Flow Features Schema (`CANONICAL_TRADE_FEATURES_SCHEMA`)
```python
import pyarrow as pa

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
    pa.field("vwap", pa.decimal128(38, 18), nullable=True),
    pa.field("vwap_std", pa.decimal128(38, 18), nullable=True),
    pa.field("poc_price", pa.decimal128(38, 18), nullable=True),
    pa.field("vah_price", pa.decimal128(38, 18), nullable=True),
    pa.field("val_price", pa.decimal128(38, 18), nullable=True),
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

## 5. 4-Way Anti-Lookahead Leakage Invariants

> [!IMPORTANT]
> **Comprehensive 4-Way Anti-Leakage Verification:**
> Feature computation for evaluation time $T_{\text{decision}}$ under knowledge cutoff $T_{\text{knowledge}}$ MUST produce **ZERO change** in output when any of the following 4 future events occur:
> 1. **Future Trade Inflow:** A trade event occurring at $T_{\text{event}} > T_{\text{decision}}$.
> 2. **Future Book Delta Inflow:** An order book mutation occurring at $T_{\text{event}} > T_{\text{decision}}$.
> 3. **Future Event Revision:** A revision to an older event published after knowledge cutoff ($T_{\text{published}} > T_{\text{knowledge}}$).
> 4. **Historical Backfill After Knowledge Cutoff:** Retrospective data arrived after knowledge cutoff ($T_{\text{ingested}} > T_{\text{knowledge}}$).

---

## 6. Gate 3C Acceptance Criteria & Comprehensive Test Matrix

- [ ] **Deterministic Parameter Hashing:** Configurations are validated and hashed into `parameter_config_sha256`. Modifying any parameter alters the hash.
- [ ] **Deterministic Value Area Tie-Breaking & Boundary:** Verifies symmetric tie-breaker selects lower price first and includes boundary level when $V_{\text{acc}} \ge 0.70 \times V_{\text{total}}$.
- [ ] **Zero-Volume Handling:** Verifies VWAP, Volume Profile, and Imbalance handle $V_{\text{total}} = 0$ safely without division-by-zero or $\infty$.
- [ ] **Diagonal & Stacked Imbalance Correctness:** Verifies Buy and Sell diagonal imbalances under $V_{\text{opposing}} = 0$ and $V_{\text{opposing}} > 0$.
- [ ] **Micro-Price & OBI Top-N:** Verifies BBO micro-price and Top-$N$ depth-weighted BBO micro-price against manual reference values.
- [ ] **4-Way Automated Anti-Leakage Test:** Injected future trades, future book deltas, future revisions, and late backfills strictly produce 0 output difference for $T \le T_{\text{decision}}$.
- [ ] **FeatureManifest Temporal Lineage:** Verifies `decision_time_utc`, `knowledge_cutoff_utc`, `input_event_start_utc`, `input_event_end_utc`, and `feature_definition_version` are populated and immutable.
- [ ] **Zero Strategy / Signal Logic Audit:** Confirms complete absence of BUY/SELL signals or trade triggers.
- [ ] **Full Regression Suite:** 100% pytest pass rate (all previous 109 tests + Phase 3C tests), 0 mypy errors across all source files.
