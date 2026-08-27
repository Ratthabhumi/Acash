# ACASH — Phase 3B: Canonical Order Book Subsystem Design Proposal & Data Contract

**Document:** `docs/PHASE_3B_DESIGN_PROPOSAL.md`  
**Version:** 1.1.0  
**Date:** 2026-08-27  
**Status:** **PROPOSED — AWAITING ARCHITECTURAL REVIEW & CONTRACT SIGN-OFF**  

---

## 1. Executive Summary & Problem Statement

In market microstructure research (e.g. CME ES/NQ futures), the **Order Book** represents the stateful supply and demand queue across price levels.

Unlike **Trades (Phase 3A)**, which are discrete completed matching events (point process), the **Order Book (Phase 3B)** is a **dynamic stateful priority ladder**:
1. It is communicated via two complementary feed channels:
   - **L2 Depth Snapshots (MBP - Market By Price):** Periodic full state captures of the top $N$ price levels (e.g. Top 10 Bids and Top 10 Asks).
   - **L2/L3 Incremental Deltas:** High-frequency mutation events (`ADD`, `MODIFY`, `CANCEL`, `CLEAR`) with monotonic message sequence numbers.
2. An analytical research query requesting *"What was the exact Top-10 Depth Ladder at time $T_{\text{target}}$ as observed at or before $T_{\text{knowledge}}$?"* requires a **deterministic Book State Reconstruction Engine** that selects the latest complete snapshot prior to $T_{\text{target}}$ knowable at $T_{\text{knowledge}}$ and applies all contiguous incremental deltas up to $T_{\text{target}}$.

```
                                      PHASE 3B ORDER BOOK TOPOLOGY
                                                    │
                 ┌──────────────────────────────────┴──────────────────────────────────┐
                 ▼                                                                     ▼
    CANONICAL SNAPSHOTS (MBP)                                             CANONICAL DELTAS (MBP/MBO)
  - Top-N Depth State Frames                                            - Incremental Atomic Mutations
  - Explicit snapshot completeness                                      - Explicit MBP vs MBO semantics
  - Daily Parquet Partition                                             - Daily Parquet Partition
                 │                                                                     │
                 └──────────────────────────────────┬──────────────────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  BOOK STATE RECONSTRUCTION ENGINE       │
                               │  - Selects valid Root Snapshot          │
                               │  - Sequentially applies Deltas          │
                               │  - Adapter-configured sequence checks   │
                               │  - Classifies Crossed States            │
                               │  - Emits Reconstructed Top-N Ladder     │
                               └────────────────────┬────────────────────┘
                                                    ▼
                                      Phase 3C: Feature Engine
                                      (Order Book Imbalance, Micro-Price)
```

---

## 2. Decoupling Message Identity vs. Canonical Row Identity

Exchange market data protocols (e.g. CME MDP 3.0 SBE, NASDAQ ITCH) emit single UDP multicast packets containing multiple book levels (in snapshots) or multiple price updates (in deltas).

ACASH strictly decouples **Network Message Identity** from **Canonical Row Identity**:

```
[Exchange Snapshot Packet] ──► Message Identity = (source_id, channel_id, symbol, trading_date, source_seq_num)
             │
             ├──► Row 0: Bid Level 0 (BBO) ──► Row Identity = (Message Identity, "BID", level_idx=0)
             ├──► Row 1: Bid Level 1       ──► Row Identity = (Message Identity, "BID", level_idx=1)
             └──► Row N: Ask Level 0 (BBO) ──► Row Identity = (Message Identity, "ASK", level_idx=0)

[Exchange Delta Packet] ──► Message Identity = (source_id, channel_id, symbol, trading_date, source_seq_num)
             │
             ├──► Action 0: Modify Level 0 Size ──► Row Identity = (Message Identity, action_sub_idx=0)
             └──► Action 1: Add Level 5 Price   ──► Row Identity = (Message Identity, action_sub_idx=1)
```

### 2.1 Canonical Row Identity Definitions

1. **Book Snapshots Row Identity:**
   $$\text{Snapshot Row Identity} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date}, \text{source\_seq\_num}, \text{side}, \text{level\_idx})$$
2. **Book Deltas Row Identity:**
   $$\text{Delta Row Identity} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date}, \text{source\_seq\_num}, \text{action\_sub\_idx})$$

---

## 3. Snapshot Grouping & Completeness Semantics

> [!IMPORTANT]
> **Atomic Snapshot Completeness Principle:**
> A snapshot represents an atomic multi-level state frame. The Reconstructor **MUST NOT** accept partial or incomplete snapshots as valid state roots.
>
> 1. **Snapshot Group Key:**  
>    $$\text{Snapshot Group Key} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date}, \text{source\_seq\_num})$$
> 2. **Completeness Flag (`is_snapshot_complete`):**  
>    A boolean indicator in the schema certifying that the full Top-$N$ depth ladder across both sides was received atomically. Incomplete frames are rejected as state roots (`PARTIAL_SNAPSHOT_REJECTED`).

---

## 4. Separation of MBP (Price-Level) vs. MBO (Order-Level) Delta Semantics

> [!IMPORTANT]
> **Explicit Delta Architecture Separation:**
> L2 Market By Price (MBP) and L3 Market By Order (MBO) represent distinct physical market-data domains and **MUST NOT** be conflated into a single generic handler.

### 4.1 MBP (Market By Price — L2 Price-Level Deltas)
- **Target Entity:** Aggregated Price Level (`price`, `side`, `level_idx`).
- **Actions:**
  - `ADD`: Insert a new price level into the depth ladder.
  - `MODIFY`: Update the aggregated size / order count at an existing price level.
  - `CANCEL` / `DELETE`: Remove a price level from the depth ladder.
  - `CLEAR`: Clear an entire side (e.g. during market pause or session reset).

### 4.2 MBO (Market By Order — L3 Order-Level Deltas)
- **Target Entity:** Discrete Individual Order (`order_id`, `price`, `side`, `priority`).
- **Actions:**
  - `ADD`: Insert a specific new order with FIFO priority into the price queue.
  - `MODIFY`: Change the remaining size or price of a specific `order_id` (price change causes priority loss).
  - `CANCEL`: Cancel or reduce the size of a specific `order_id`.
- **L2 Aggregation:** The MBO reconstructor maintains discrete order queues and aggregates active orders by price level to project the canonical L2 depth view.

---

## 5. Canonical PyArrow Schemas

### 5.1 Canonical Order Book Snapshot Schema (`CANONICAL_BOOK_SNAPSHOT_SCHEMA`)

```python
import pyarrow as pa

CANONICAL_BOOK_SNAPSHOT_SCHEMA = pa.schema([
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("channel_id", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("exchange_time_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("feed_time_utc", pa.timestamp("ns", tz="UTC"), nullable=True),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("source_seq_num", pa.int64(), nullable=False),
    pa.field("snapshot_id", pa.string(), nullable=False),      # Unique snapshot frame identifier
    pa.field("is_snapshot_complete", pa.bool_(), nullable=False), # Atomic completeness flag
    pa.field("side", pa.string(), nullable=False),            # "BID", "ASK"
    pa.field("level_idx", pa.int32(), nullable=False),        # 0 = Top of Book (BBO), 1..N Depth Level
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size", pa.decimal128(38, 18), nullable=False),
    pa.field("order_count", pa.int32(), nullable=True),       # Queue order count if provided
])
```

### 5.2 Canonical Order Book Incremental Delta Schema (`CANONICAL_BOOK_DELTA_SCHEMA`)

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
    pa.field("action_sub_idx", pa.int32(), nullable=False),    # 0, 1, 2... within the message
    pa.field("delta_type", pa.string(), nullable=False),      # "MBP" or "MBO"
    pa.field("action", pa.string(), nullable=False),          # "ADD", "MODIFY", "CANCEL", "CLEAR"
    pa.field("side", pa.string(), nullable=False),            # "BID", "ASK"
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size_delta", pa.decimal128(38, 18), nullable=False),
    pa.field("order_id", pa.string(), nullable=True),         # Required for MBO, Null for MBP
    pa.field("level_idx", pa.int32(), nullable=True),         # Level index for MBP, Null for MBO
])
```

---

## 6. Sequence Discontinuity & Gap Handling Boundary

> [!IMPORTANT]
> **Adapter-Configured Sequence Contiguity:**
> In accordance with ADR-020, `source_seq_num` is an opaque upstream sequence identifier.
> - **Arithmetic Gap Detection (`seq_{i+1} == seq_i + 1`):** Enabled **ONLY** when the source adapter explicitly guarantees that the stream operates as a contiguous integer sequence.
> - **Opaque Streams:** For streams without contiguous sequence guarantees, the Reconstructor relies on source-declared reset events, recovery frames, or adapter-supplied sequence policies.
> - **Gap Invalidation:** When a sequence gap is detected on a contiguous stream, the Reconstructor transitions to `STATE_INVALID_GAP` and suspends depth ladder output until the next complete snapshot is applied.

---

## 7. Crossed-State Anomaly Classification

> [!IMPORTANT]
> **Granular Crossed Book State Classification:**
> If $P_{\text{bid}, 0} \ge P_{\text{ask}, 0}$ occurs during reconstruction, the engine classifies the event into one of four distinct states rather than generic failure:
> 1. **`CROSSED_TRANSIENT`:** Crossed quotes that resolve within $N$ consecutive deltas or within the same packet / sub-millisecond burst.
> 2. **`CROSSED_AUCTION_OR_HALT`:** Crossed quotes occurring during designated auction matching or market halt sessions.
> 3. **`CROSSED_DUE_TO_INVALID_RECONSTRUCTION`:** Crossed quotes caused by missing deltas, packet gaps, or out-of-order mutations.
> 4. **`CROSSED_PERSISTENT_ANOMALY`:** True persistent crossed book in normal continuous trading.

---

## 8. Length-Prefixed Binary Serialization & Logical Provenance Hashes

To guarantee that provenance hashes are **deterministic and computationally collision-resistant under the specified canonical serialization protocol**, invariant to Parquet physical chunking, row group layouts, or compression codecs:

### 8.1 Field Binary Encoding Specifications

| Arrow Type | Binary Encoding Protocol | Null Representation |
| :--- | :--- | :--- |
| **`pa.string()`** | `[uint32_be(len)][utf8_bytes]` | `uint32_be(0xFFFFFFFF)` (4-byte null tag, 0 payload bytes) |
| **`pa.decimal128(38, 18)`** | ASCII `f"{dec:.18f}"` $\to$ `[uint32_be(len)][ascii_bytes]` | `uint32_be(0xFFFFFFFF)` |
| **`pa.timestamp("ns", tz="UTC")`** | `[int64_be(epoch_nanoseconds)]` (8 bytes, lossless nanoseconds) | `[int64_be(-9223372036854775808)]` (`0x8000000000000000`) |
| **`pa.timestamp("us", tz="UTC")`** | `[int64_be(epoch_microseconds)]` (8 bytes, lossless microseconds) | `[int64_be(-9223372036854775808)]` |
| **`pa.date32()`** | `[int32_be(epoch_days)]` (4 bytes, signed integer) | `[int32_be(-2147483648)]` (`0x80000000`) |
| **`pa.int64()`** | `[int64_be(val)]` (8 bytes, signed big-endian) | `[int64_be(-9223372036854775808)]` |
| **`pa.int32()`** | `[int32_be(val)]` (4 bytes, signed big-endian) | `[int32_be(-2147483648)]` |
| **`pa.bool_()`** | `[uint8(1 if True else 0)]` (1 byte) | `[uint8(0xFF)]` |
| **Record Separator** | Single byte `0x1E` between records | N/A |

### 8.2 Hashing Execution Protocols

1. **`calculate_canonical_book_snapshot_sha256(table: pa.Table) -> str`**:
   - Check schema completeness.
   - Sort table strictly by Snapshot Row Identity ASC: `(source_id, channel_id, symbol, trading_date, source_seq_num, side, level_idx)`.
   - Stream rows using length-prefixed binary encoding into `hashlib.sha256()`.

2. **`calculate_canonical_book_delta_sha256(table: pa.Table) -> str`**:
   - Check schema completeness.
   - Sort table strictly by Delta Row Identity ASC: `(source_id, channel_id, symbol, trading_date, source_seq_num, action_sub_idx)`.
   - Stream rows using length-prefixed binary encoding into `hashlib.sha256()`.

---

## 9. Storage Layout & Rigorous Dual-Temporal PIT Queries

### 9.1 Storage Layout

```
data/
└── parquet/
    └── orderbook/
        ├── snapshots/
        │   └── {symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
        └── deltas/
            └── {symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
```

### 9.2 Rigorous Point-in-Time (PIT) Dual-Temporal Reconstruction Queries
To reconstruct the Order Book state at target exchange time $T_{\text{target}}$ as observed at or before $T_{\text{knowledge}}$:

1. **Step 1: Select State Root Snapshot:**
   ```sql
   SELECT * FROM read_parquet('data/parquet/orderbook/snapshots/{symbol}/**/*.parquet')
   WHERE knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
     AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ)
     AND is_snapshot_complete = TRUE
   ORDER BY exchange_time_utc DESC, source_seq_num DESC, knowledge_time_utc DESC
   LIMIT 1
   ```
2. **Step 2: Select Subsequent Incremental Deltas:**
   ```sql
   SELECT * FROM read_parquet('data/parquet/orderbook/deltas/{symbol}/**/*.parquet')
   WHERE knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
     AND exchange_time_utc >= CAST(? AS TIMESTAMPTZ)
     AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ)
     AND (
       (exchange_time_utc = CAST(? AS TIMESTAMPTZ) AND source_seq_num >= ?)
       OR exchange_time_utc > CAST(? AS TIMESTAMPTZ)
     )
   ORDER BY exchange_time_utc ASC, source_seq_num ASC, action_sub_idx ASC
   ```
3. **Step 3: State Ladder Execution:**  
   Feed the selected Snapshot and Deltas into the Reconstructor to produce the exact Top-$N$ Depth Ladder at $T_{\text{target}}$.

---

## 10. Gate 3B Acceptance Criteria & Test Matrix

Phase 3B completion is governed by the following test matrix:

- [ ] **Schema Conformance:** Both `CANONICAL_BOOK_SNAPSHOT_SCHEMA` and `CANONICAL_BOOK_DELTA_SCHEMA` strictly enforced.
- [ ] **Snapshot Completeness Validation:** Reconstructor rejects incomplete snapshot frames (`PARTIAL_SNAPSHOT_REJECTED`).
- [ ] **MBP vs MBO Reconstruction Separation:** Independent state logic for MBP price-level ladder and MBO discrete order queue.
- [ ] **Sequence Discontinuity Boundary:** Adapter-configured sequence contiguity checks with state invalidation on gaps.
- [ ] **Crossed State Granularity:** Reconstructor distinguishes `CROSSED_TRANSIENT`, `CROSSED_AUCTION`, and `CROSSED_DUE_TO_INVALID_RECONSTRUCTION`.
- [ ] **Permutation & Codec Invariance:** Permuting snapshot/delta rows or changing compression codec produces identical hashes.
- [ ] **Hash Modification Sensitivity:** Any field modification alters the cryptographic hash.
- [ ] **Idempotent Ingestion & Batch Collision:** Replaying identical snapshot/delta batches returns existing part files; modified payloads raise `BatchCollisionError`.
- [ ] **Duplicate Row Identity Rejection:** Duplicate Snapshot/Delta Row Identities raise `IntegrityViolationError`.
- [ ] **Dual-Temporal PIT Query Test:** Verifies that historical replay strictly respects both $T_{\text{target}}$ and $T_{\text{knowledge}}$ with zero lookahead.
