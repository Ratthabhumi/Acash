# ACASH — Phase 3: Market Microstructure & Point-in-Time Feature Subsystem Plan

**Document:** `docs/PHASE_3_PLAN.md`  
**Version:** 1.1.0  
**Date:** 2026-08-27  
**Status:** **PROPOSED (Pre-Signoff Corrective Review Pass Completed)**  

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

## 3. Session Labeling, Sequence Scoping & Resets

### 3.1 CME Trading Session Labeling (`trading_date`)
In centralized futures markets (e.g. CME Globex), trading sessions span across calendar day boundaries.
- **Session Definition:** `trading_date` is the **CME Trading Session Label** determined in `America/Chicago` (CT) timezone, **NOT simply the UTC calendar date**.
- **Session Boundaries:**
  - Sunday 17:00 CT $\to$ Monday 16:00 CT is assigned `trading_date = Monday` (YYYY-MM-DD).
  - Monday 17:00 CT $\to$ Tuesday 16:00 CT is assigned `trading_date = Tuesday` (YYYY-MM-DD).
  - *Example:* An event occurring at `2026-01-18 23:30:00 UTC` (which is Sunday 17:30 CT) is labeled with `trading_date = 2026-01-19` (Monday session).

### 3.2 Sequence Number Scoping (`source_seq_num`)
- **Semantic Definition:** `source_seq_num` represents the raw monotonic integer message/packet sequence number assigned by the exchange feed within `(source_id, channel_id, trading_date)`.
- **Reset Semantics:** In CME MDP 3.0, message sequence numbers reset to `1` upon weekly session open (Sunday 17:00 CT) or upon channel connection restart/failover.
- **Gap Detection:** If an incoming message has $\text{source\_seq\_num}_{i+1} > \text{source\_seq\_num}_i + 1$ on the same channel, a `PACKET_GAP_DETECTED` warning is emitted to flag dropped multicast packets.

### 3.3 Global Uniqueness Scope Key
To guarantee global uniqueness across weekly sequence resets and multiple multicast channels, ACASH constructs compound identity scopes:

$$\text{Stream Channel Scope Key} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date})$$

---

## 4. Message Identity vs. Canonical Row Identity

Exchange protocols (e.g. CME MDP 3.0 SBE, NASDAQ ITCH) frequently emit single network packet messages containing multiple book updates or multiple trade matches.

ACASH explicitly decouples **Message Identity** from **Canonical Row Identity**:

```
[Exchange Network Message / Packet] ──► Message Identity = (source_id, channel_id, trading_date, source_seq_num)
                 │
                 ├──► Row 1: Level 0 Bid Update ──► Row Identity = (Message Identity, "BID", level=0)
                 ├──► Row 2: Level 1 Bid Update ──► Row Identity = (Message Identity, "BID", level=1)
                 └──► Row 3: Level 0 Ask Update ──► Row Identity = (Message Identity, "ASK", level=0)
```

### Row Identity Definitions:

1. **Trades Domain (Phase 3A):**
   $$\text{Trade Row Identity} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date}, \text{source\_seq\_num}, \text{trade\_id}, \text{match\_sub\_idx})$$
2. **Order Book Snapshots (Phase 3B):**
   $$\text{Book Snapshot Row Identity} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date}, \text{source\_seq\_num}, \text{side}, \text{level\_idx})$$
3. **Order Book Incremental Deltas (Phase 3B):**
   $$\text{Book Delta Row Identity} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date}, \text{source\_seq\_num}, \text{action\_sub\_idx})$$

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
    pa.field("source_seq_num", pa.int64(), nullable=False),
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
    pa.field("source_seq_num", pa.int64(), nullable=False),
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
    pa.field("source_seq_num", pa.int64(), nullable=False),
    pa.field("action_sub_idx", pa.int32(), nullable=False),
    pa.field("action", pa.string(), nullable=False),          # "ADD", "MODIFY", "CANCEL", "CLEAR"
    pa.field("side", pa.string(), nullable=False),            # "BID", "ASK"
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size_delta", pa.decimal128(38, 18), nullable=False),
    pa.field("order_id", pa.string(), nullable=True),         # Null for L2 MBP; populated for L3 MBO
])
```

---

## 6. Unambiguous Length-Prefixed Binary Serialization & Logical Provenance Hashes

To guarantee that provenance hashes are **100% deterministic, collision-proof, file-layout invariant, and codec invariant**, ACASH establishes a strict **Length-Prefixed Binary Serialization Protocol** (avoiding ambiguous text delimiters):

### 6.1 Field-Level Binary Encoding Specifications

| Arrow Data Type | Binary Serialization Protocol | Null Representation |
| :--- | :--- | :--- |
| **`pa.string()`** | `[uint32_be(len)][utf8_bytes]` | `uint32_be(0xFFFFFFFF)` (4-byte null tag, 0 payload bytes) |
| **`pa.decimal128(38, 18)`** | ASCII string `f"{dec:.18f}"` $\to$ `[uint32_be(len)][ascii_bytes]` | `uint32_be(0xFFFFFFFF)` |
| **`pa.timestamp("ns", tz="UTC")`** | `[int64_be(epoch_nanoseconds)]` (8 bytes, lossless nanoseconds) | `[int64_be(-9223372036854775808)]` (`0x8000000000000000`) |
| **`pa.timestamp("us", tz="UTC")`** | `[int64_be(epoch_microseconds)]` (8 bytes, lossless microseconds) | `[int64_be(-9223372036854775808)]` |
| **`pa.date32()`** | `[int32_be(epoch_days)]` (4 bytes, signed integer) | `[int32_be(-2147483648)]` (`0x80000000`) |
| **`pa.int64()`** | `[int64_be(val)]` (8 bytes, signed big-endian) | `[int64_be(-9223372036854775808)]` |
| **`pa.int32()`** | `[int32_be(val)]` (4 bytes, signed big-endian) | `[int32_be(-2147483648)]` |

### 6.2 Row & Table Hashing Execution Order
1. **Schema Check:** Fail fast if any required canonical column is missing.
2. **Deterministic Sort:** Sort rows strictly by **Canonical Row Identity ASC**:
   - *Trades:* `(source_id, channel_id, symbol, trading_date, source_seq_num, trade_id, match_sub_idx)`
   - *Book Snapshots:* `(source_id, channel_id, symbol, trading_date, source_seq_num, side, level_idx)`
   - *Book Deltas:* `(source_id, channel_id, symbol, trading_date, source_seq_num, action_sub_idx)`
3. **Binary Streaming:** Stream each row's fields sequentially using the binary encoding specifications above, followed by a 1-byte row delimiter (`0x1E` Record Separator).
4. **SHA-256 Digest:** Feed the raw byte stream into `hashlib.sha256()` to produce `canonical_trades_sha256` or `canonical_book_sha256`.

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

- **Compression & Encoding:** PyArrow writes using `zstd` (compression level 3) with Dictionary Encoding on categorical string columns (`source_id`, `channel_id`, `aggressor_side`, `action`), achieving 75–85% storage reduction.

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

## 9. Gate 3 Acceptance Criteria & Comprehensive Test Matrix

Phase 3 completion is governed by 3 sequential quality gates:

### Gate 3A Criteria & Test Matrix (Trades Subsystem):
- [ ] **Schema & Types:** PyArrow canonical trades schema strictly enforced (`timestamp[ns, tz=UTC]`, `Decimal128(38,18)`).
- [ ] **Idempotent Replay Test:** Replaying the exact same trades payload is idempotent and creates zero duplicate Parquet files or ledger records (`test_trades_ingestion_replay_idempotent`).
- [ ] **Batch Collision Test:** Ingesting same `batch_id` with modified trade content raises `BatchCollisionError` (`test_trades_batch_collision_on_same_batch_id`).
- [ ] **Duplicate Identity Rejection Test:** Ingesting an already persisted Trade Row Identity under a different `batch_id` is rejected as `IntegrityViolationError` (`test_trades_global_duplicate_identity_rejected`).
- [ ] **Channel Isolation Test:** Identical `source_seq_num` occurring on different `channel_id` do NOT collide (`test_trades_different_channel_same_seq_no_collision`).
- [ ] **Multi-Trade Expansion Test:** Single exchange message containing multiple matches deterministically expands with unique `match_sub_idx` (`test_trades_multi_trade_message_expansion`).
- [ ] **Hash Row-Order Invariance Test:** Permuting trade rows produces identical `canonical_trades_sha256` (`test_canonical_trades_hash_row_order_invariance`).
- [ ] **Hash Layout Invariance Test:** Writing via different Parquet codecs (zstd vs snappy) produces identical `canonical_trades_sha256` (`test_canonical_trades_hash_codec_invariance`).
- [ ] **Hash Sensitivity Test:** Modifying any canonical field (price, size, aggressor side, condition) alters the hash (`test_canonical_trades_hash_detects_any_modification`).
- [ ] **Nanosecond Distinguishability Test:** Nanosecond timestamp differences in the last 3 digits (e.g. 100ns vs 200ns) produce distinct hashes (`test_canonical_trades_hash_nanosecond_distinguishability`).
- [ ] **Daily Partitioning & Storage:** Daily Parquet partition storage verified for trades (`data/parquet/trades/{symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet`).
- [ ] **DuckDB PIT Query:** Point-in-time qualification query retrieves trades $\le T_{\text{as\_of}}$ with zero look-ahead leakage.

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
