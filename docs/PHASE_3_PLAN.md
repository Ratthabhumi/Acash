# ACASH — Phase 3: Market Microstructure & Point-in-Time Feature Subsystem Plan

**Document:** `docs/PHASE_3_PLAN.md`  
**Version:** 1.0.0  
**Date:** 2026-08-27  
**Status:** **PROPOSED — AWAITING ARCHITECTURAL REVIEW & APPROVAL**  

---

## 1. Executive Summary & Sub-Phase Architecture

Phase 3 expands ACASH from a bar-level OHLCV engine into a comprehensive **Futures Market Microstructure & Feature Research Infrastructure** (with CME ES/NQ reference architecture), while strictly preserving:
1. **Domain Decoupling:** OHLCV (Phase 2), Trades (Phase 3A), and Order Book (Phase 3B) remain completely independent canonical domains with separate Arrow schemas, partition layouts, and point-in-time qualification queries.
2. **Observation vs Interpretation:** Canonical layers preserve exchange matching observations faithfully. All aggregations, Order Flow analytics, Volume Profiles, and VWAP calculations belong downstream in **Phase 3C (Microstructure Research Engine)**.
3. **Zero Strategy Logic:** Phase 3 implements mathematical feature transformations only. Zero BUY/SELL trading strategies or signal generators are created in Phase 3 (deferred strictly to Phase 4).

```
                                    ACASH DATA & RESEARCH HIERARCHY
                                                   │
                  ┌────────────────────────────────┴────────────────────────────────┐
                  ▼                                                                 ▼
         CANONICAL DATA LAYER                                              RESEARCH LAYER (Downstream)
       (Source-Faithful Events)                                           (Derived Features & Signals)
                  │                                                                 │
    ┌─────────────┼─────────────┐                                                   │
    ▼             ▼             ▼                                                   │
  Domain 1:    Domain 2:     Domain 3:                                              │
  OHLCV Bars   Trades        Order Book                                             │
  (Phase 2)    (Phase 3A)    (Phase 3B)                                             │
    │             │             │                                                   │
    └─────────────┴──────┬──────┴───────────────────────────────────────────────────┘
                         │
                         ▼
          ┌───────────────────────────────┐
          │  Phase 3C: FEATURE ENGINE     │
          │  - Anchored & Rolling VWAP    │
          │  - Volume & TPO Profile       │
          │  - Footprint / Delta Cluster  │
          │  - Imbalance & Absorption     │
          │  - Anti-Leakage PIT Pipeline  │
          └──────────────┬────────────────┘
                         ▼
                 Phase 4: Alpha Engine
```

---

## 2. Temporal Semantics & Clock Domain Boundaries

### 2.1 The Three Timestamps
Microstructure events distinguish between three temporal coordinate systems:

| Timestamp Field | Precision / Type | Semantic Definition | Authoritative Role |
| :--- | :--- | :--- | :--- |
| **`exchange_time_utc`** | `timestamp[ns, tz=UTC]` (Required) | Nanosecond matching engine timestamp assigned by exchange (e.g. CME Globex MDP 3.0 match event). | **Chronological Order of Market Reality** |
| **`feed_time_utc`** | `timestamp[ns, tz=UTC]` (Optional / Nullable) | Nanosecond timestamp assigned by feed gateway / packet multicast router upon network egress. | **Feed Latency & Network Jitter Analysis** |
| **`knowledge_time_utc`** | `timestamp[us, tz=UTC]` (Required) | Microsecond UTC timestamp when ACASH ingestion pipeline observed and persisted the record. | **ACASH Point-in-Time (P-I-T) Qualification** |

### 2.2 Clock Domain & Invariant Boundary
> [!IMPORTANT]
> **No Universal Ordering Assumption:**
> ACASH does **NOT** assume $T_{\text{knowledge}} \ge T_{\text{feed}} \ge T_{\text{exchange}}$ as an unconditional fatal validation invariant, because:
> 1. Clocks across disparate network domains (CME Chicago matching engine vs AWS/Cloud ingestion gateway vs Local clock) experience non-zero clock drift and NTP synchronization skew.
> 2. Historical backfills and replayed tick feeds may be ingested hours or months after live matching.
>
> **Validation Rule:**
> - $T_{\text{exchange}}$ is the authoritative timeline for market chronology and queue reconstruction.
> - $T_{\text{knowledge}}$ is the authoritative timeline for ACASH backtesting Point-in-Time as-of qualification.
> - For live/direct feeds with synchronized PTP/NTP clocks, a configurable sanity threshold ($T_{\text{exchange}} - T_{\text{knowledge}} > \Delta_{\text{max\_skew}}$, e.g. 5000ms) emits a `CLOCK_SKEW_WARNING` without corrupting or dropping raw trades.

---

## 3. Sequence Number Scoping, Channel IDs & Session Resets

### 3.1 CME Sequence Scoping
In centralized futures markets (e.g. CME Globex MDP 3.0), sequence numbers operate within explicit communication channels and reset across sessions:
- **Channel ID (`channel_id`):** CME multicast channel identifier (e.g. Channel 310 for ES, Channel 311 for NQ).
- **Session / Trading Date (`trading_date`):** YYYY-MM-DD representing the CME trading session (Sunday 17:00 CT $\to$ Friday 16:00 CT).
- **Source Sequence (`source_seq_num`):** Monotonic integer message sequence number assigned by the exchange feed within `(channel_id, trading_date)`. Resets to 1 upon weekly session start or channel failover.

### 3.2 Global Uniqueness Guarantee (Compound Identity)
To guarantee 100% deterministic uniqueness across session sequence resets, ACASH constructs compound identities:

$$\text{Trade Scope Key} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date})$$

---

## 4. Message Identity vs. Canonical Row Identity

Exchange protocols (e.g. CME MDP 3.0 SBE, NASDAQ ITCH) frequently emit single network packet messages containing multiple book updates or multiple trade matches.

ACASH explicitly decouples **Message Identity** from **Canonical Row Identity**:

```
[Exchange Network Message / Packet] ──► Message Identity = (source_id, channel_id, trading_date, message_seq_num)
                 │
                 ├──► Row 1: Level 0 Bid Update ──► Row Identity = (Message Identity, "BID", level=0)
                 ├──► Row 2: Level 1 Bid Update ──► Row Identity = (Message Identity, "BID", level=1)
                 └──► Row 3: Level 0 Ask Update ──► Row Identity = (Message Identity, "ASK", level=0)
```

### Row Identity Definitions:

1. **Trades Domain (Phase 3A):**
   $$\text{Trade Row Identity} = (\text{source\_id}, \text{symbol}, \text{trading\_date}, \text{sequence\_num}, \text{trade\_id}, \text{match\_sub\_idx})$$
2. **Order Book Snapshots (Phase 3B):**
   $$\text{Book Snapshot Row Identity} = (\text{source\_id}, \text{symbol}, \text{trading\_date}, \text{sequence\_num}, \text{side}, \text{level\_idx})$$
3. **Order Book Incremental Deltas (Phase 3B):**
   $$\text{Book Delta Row Identity} = (\text{source\_id}, \text{symbol}, \text{trading\_date}, \text{sequence\_num}, \text{action\_sub\_idx})$$

---

## 5. Canonical Schemas & Data Contracts

### 5.1 Phase 3A: Canonical Trades Schema (`CANONICAL_TRADES_SCHEMA`)

```python
import pyarrow as pa

CANONICAL_TRADES_SCHEMA = pa.schema([
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("channel_id", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("exchange_time_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("feed_time_utc", pa.timestamp("ns", tz="UTC"), nullable=True),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("sequence_num", pa.int64(), nullable=False),
    pa.field("trade_id", pa.string(), nullable=False),
    pa.field("match_sub_idx", pa.int32(), nullable=False),
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size", pa.decimal128(38, 18), nullable=False),
    pa.field("aggressor_side", pa.string(), nullable=False),  # "BUY", "SELL", "UNKNOWN"
    pa.field("trade_condition", pa.string(), nullable=False), # "REGULAR", "SPREAD", "BLOCK", "AUCTION"
])
```

### 5.2 Phase 3B: Canonical Order Book Depth Snapshots (`CANONICAL_BOOK_SNAPSHOT_SCHEMA`)

```python
CANONICAL_BOOK_SNAPSHOT_SCHEMA = pa.schema([
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("channel_id", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("exchange_time_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("feed_time_utc", pa.timestamp("ns", tz="UTC"), nullable=True),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("sequence_num", pa.int64(), nullable=False),
    pa.field("side", pa.string(), nullable=False),            # "BID", "ASK"
    pa.field("level_idx", pa.int32(), nullable=False),        # 0 = Top of Book (BBO), 1..N Depth
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size", pa.decimal128(38, 18), nullable=False),
    pa.field("order_count", pa.int32(), nullable=True),       # Queue order count if provided
])
```

### 5.3 Phase 3B: Canonical Order Book Incremental Deltas (`CANONICAL_BOOK_DELTA_SCHEMA`)

```python
CANONICAL_BOOK_DELTA_SCHEMA = pa.schema([
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("channel_id", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("exchange_time_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("feed_time_utc", pa.timestamp("ns", tz="UTC"), nullable=True),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("sequence_num", pa.int64(), nullable=False),
    pa.field("action_sub_idx", pa.int32(), nullable=False),
    pa.field("action", pa.string(), nullable=False),          # "ADD", "MODIFY", "CANCEL", "CLEAR"
    pa.field("side", pa.string(), nullable=False),            # "BID", "ASK"
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size_delta", pa.decimal128(38, 18), nullable=False),
    pa.field("order_id", pa.string(), nullable=True),         # Null for L2 MBP; populated for L3 MBO
])
```

---

## 6. Deterministic Logical Serialization & Provenance Hashes

To guarantee that provenance hashes are **100% deterministic, file-layout invariant, and codec invariant**, ACASH establishes an exact byte serialization protocol:

### 6.1 Binary Field Serialization Protocol
1. **Strings (`source_id`, `symbol`, `aggressor_side`, etc.):** Encoded as UTF-8 bytes.
2. **Decimals (`Decimal128(38, 18)`):** Fixed-point 18-decimal precision string `f"{dec:.18f}"` encoded in UTF-8 bytes.
3. **Timestamps (`timestamp[ns/us, tz=UTC]`):** Formatted in canonical ISO-8601 UTC string:
   - Nanoseconds: `"%Y-%m-%dT%H:%M:%S.%09fZ"`
   - Microseconds: `"%Y-%m-%dT%H:%M:%S.%06fZ"`
4. **Dates (`trading_date`):** Formatted as `"%Y-%m-%d"`.
5. **Integers (`sequence_num`, `match_sub_idx`, `level_idx`):** String representation of decimal integer in UTF-8 bytes.
6. **Null Values:** Represented as literal bytes `b"NULL"`.
7. **Delimiters:**
   - Field delimiter: `b"|"`
   - Row delimiter: `b"\n"`

### 6.2 Serialization & Hashing Execution Order
$$\text{Filter required columns} \to \text{Sort by Canonical Row Identity ASC} \to \text{Stream row-by-row binary serialization} \to \text{SHA-256 Digest}$$

```python
# Exact Logical Canonical Trades SHA-256 Protocol
# 1. Sort Table by:
#    (source_id ASC, channel_id ASC, symbol ASC, trading_date ASC, sequence_num ASC, trade_id ASC, match_sub_idx ASC)
# 2. Serialize fields with '|' delimiter:
#    source_id | channel_id | symbol | trading_date | exchange_time_utc | feed_time_utc | knowledge_time_utc | sequence_num | trade_id | match_sub_idx | price | size | aggressor_side | trade_condition
# 3. Terminate row with '\n'
# 4. Hash full stream via hashlib.sha256()
```

---

## 7. Storage Layout & Partitioning Strategy

Because high-frequency futures microstructure generates $10^5$ to $10^7$ events daily, storage partitions are organized at **Daily granularity**:

```
data/
└── parquet/
    ├── ohlcv/                               # Phase 2 (Annual partition)
    │   └── {symbol}/{timeframe}/year={YYYY}/part-{batch_id}.parquet
    ├── trades/                              # Phase 3A (Daily partition)
    │   └── {symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
    ├── orderbook/                           # Phase 3B (Daily partition)
    │   ├── snapshots/{symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
    │   └── deltas/{symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
    └── features/                            # Phase 3C (Precomputed research features)
        └── {symbol}/{feature_set}/year={YYYY}/date={YYYY-MM-DD}/part-{feature_hash}.parquet
```

- **Compression & Encoding:** PyArrow writes using `zstd` (compression level 3) with Dictionary Encoding on categorical string columns (`source_id`, `aggressor_side`, `action`), achieving 75–85% storage reduction.

---

## 8. Phase 3C: Microstructure Research Engine & Feature Reproducibility Contract

### 8.1 Mathematical Feature Scope
Phase 3C operates strictly downstream from canonical events, computing derived microstructure features:

1. **Volume Weighted Average Price (VWAP):**
   $$VWAP_{\text{session}}(t) = \frac{\sum_{i: t_i \le t} P_i \cdot V_i}{\sum_{i: t_i \le t} V_i}, \quad \sigma(t) = \sqrt{\frac{\sum (P_i - VWAP)^2 \cdot V_i}{\sum V_i}}$$
2. **Volume Profile & Auction Market Theory:**
   - Point of Control (POC), Value Area High (VAH), Value Area Low (VAL, 70% volume threshold).
   - High Volume Nodes (HVN) / Low Volume Nodes (LVN).
3. **Footprint & Order Flow Analytics:**
   - Price Tick Bid/Ask Volume Clusters.
   - Bar Delta ($\Delta = V_{\text{ask}} - V_{\text{bid}}$) & Cumulative Volume Delta (CVD).
   - Diagonal Imbalance ($V_{\text{ask}, P+1} \ge 3 \times V_{\text{bid}, P}$) & Stacked Imbalance.
   - Absorption Detection (Large trade volume at extreme price with zero price progression).
4. **Order Book Microstructure Signals:**
   - Order Book Imbalance ($OBI = \frac{Q_{\text{bid}} - Q_{\text{ask}}}{Q_{\text{bid}} + Q_{\text{ask}}}$).
   - Micro-Price ($P_{\text{micro}} = \frac{Q_{\text{bid}} \cdot P_{\text{ask}} + Q_{\text{ask}} \cdot P_{\text{bid}}}{Q_{\text{bid}} + Q_{\text{ask}}}$).

### 8.2 Deterministic Reproducibility Contract
> [!IMPORTANT]
> **Deterministic Reproducibility Definition:**
> ACASH features guarantee **deterministic reproducibility under a pinned software environment, dependency specification, input canonical dataset, and parameter configuration**.
>
> Reproducibility is guaranteed via a **Feature Manifest**:
> ```json
> {
>   "feature_set_name": "session_vwap_bands_v1",
>   "symbol": "ES.FUT",
>   "trading_date": "2026-01-15",
>   "input_trades_sha256": "4b22...c777",
>   "parameter_config_sha256": "e3b0...b855",
>   "software_version": "0.3.0",
>   "feature_output_sha256": "a1c9...881f"
> }
> ```

---

## 9. Gate 3 Acceptance Criteria & Test Plan

Phase 3 completion is governed by 3 sequential quality gates:

### Gate 3A Criteria (Trades Subsystem):
- [ ] PyArrow canonical trades schema strictly enforced (`timestamp[ns, tz=UTC]`, `Decimal128(38,18)`).
- [ ] Trade data integrity validator enforces positive price, positive size, valid aggressor side (`BUY`/`SELL`/`UNKNOWN`), and session sequence checks.
- [ ] Deterministic `canonical_trades_sha256` hashing verified (invariant to row permutations and Parquet codecs).
- [ ] Recoverable Batch Commit Protocol & Daily Parquet partition storage verified for trades.
- [ ] DuckDB As-Of PIT Query retrieves trades $\le T_{\text{as\_of}}$ with zero look-ahead leakage.

### Gate 3B Criteria (Order Book Subsystem):
- [ ] PyArrow canonical schemas for L2 Depth Snapshots and Deltas enforced.
- [ ] Message Identity decoupled from Row Identity across multi-level depth packets.
- [ ] Order book state reconstruction engine reconstructs exact Top-N depth ladder from snapshot + deltas.
- [ ] Monotonic sequence validation flags missing packet gaps (`GAP_DETECTED`).

### Gate 3C Criteria (Microstructure Research Engine):
- [ ] VWAP, Volume Profile, Footprint Delta, and Imbalance calculations implemented as pure mathematical functions.
- [ ] **Automated Anti-Leakage Test:** Injected future trades/book updates strictly do not alter feature values for $T \le T_{\text{decision}}$.
- [ ] Zero trading strategy / BUY-SELL logic present in codebase.
- [ ] All unit and integration tests pass (100% pass rate) with zero `mypy` type errors.
