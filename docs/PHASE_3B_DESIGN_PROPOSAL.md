# ACASH — Phase 3B: Canonical Order Book Subsystem Design Proposal & Data Contract

**Document:** `docs/PHASE_3B_DESIGN_PROPOSAL.md`  
**Version:** 1.0.0  
**Date:** 2026-08-27  
**Status:** **PROPOSED — AWAITING ARCHITECTURAL REVIEW & CONTRACT SIGN-OFF**  

---

## 1. Executive Summary & Problem Statement

In market microstructure research (e.g. CME ES/NQ futures), the **Order Book** represents the stateful supply and demand queue across price levels.

Unlike **Trades (Phase 3A)**, which are discrete completed matching events (point process), the **Order Book (Phase 3B)** is a **dynamic stateful priority ladder**:
1. It is communicated via two complementary feed channels:
   - **L2 Depth Snapshots (MBP - Market By Price):** Periodic full state captures of the top $N$ price levels (e.g. Top 10 Bids and Top 10 Asks).
   - **L2/L3 Incremental Deltas:** High-frequency mutation events (`ADD`, `MODIFY`, `CANCEL`, `CLEAR`) with monotonic message sequence numbers.
2. An analytical research query requesting *"What was the exact Top-10 Depth Ladder at time $T$ as observed at $T_{\text{knowledge}}$?"* requires a **deterministic Book State Reconstruction Engine** that loads the latest snapshot prior to $T$ and applies all contiguous incremental deltas up to $T$.

```
                                      PHASE 3B ORDER BOOK TOPOLOGY
                                                    │
                 ┌──────────────────────────────────┴──────────────────────────────────┐
                 ▼                                                                     ▼
    CANONICAL SNAPSHOTS (MBP)                                             CANONICAL DELTAS (MBP/MBO)
  - Top-N Depth State Frames                                            - Incremental Atomic Mutations
  - Opaque source_seq_num anchor                                        - Opaque source_seq_num stream
  - Daily Parquet Partition                                             - Daily Parquet Partition
                 │                                                                     │
                 └──────────────────────────────────┬──────────────────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  BOOK STATE RECONSTRUCTION ENGINE       │
                               │  (Deterministic In-Memory State Ladder) │
                               │  - Applies Snapshot at seq_0            │
                               │  - Sequentially applies Deltas seq_1..N │
                               │  - Validates sequence contiguity        │
                               │  - Detects Crossed Book / Gaps          │
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

## 3. Canonical PyArrow Schemas

### 3.1 Canonical Order Book Snapshot Schema (`CANONICAL_BOOK_SNAPSHOT_SCHEMA`)

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
    pa.field("side", pa.string(), nullable=False),            # "BID", "ASK"
    pa.field("level_idx", pa.int32(), nullable=False),        # 0 = Top of Book (BBO), 1..N Depth Level
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size", pa.decimal128(38, 18), nullable=False),
    pa.field("order_count", pa.int32(), nullable=True),       # Queue order count if provided
])
```

### 3.2 Canonical Order Book Incremental Delta Schema (`CANONICAL_BOOK_DELTA_SCHEMA`)

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
    pa.field("action", pa.string(), nullable=False),          # "ADD", "MODIFY", "CANCEL", "CLEAR"
    pa.field("side", pa.string(), nullable=False),            # "BID", "ASK"
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size_delta", pa.decimal128(38, 18), nullable=False),
    pa.field("order_id", pa.string(), nullable=True),         # Null for L2 MBP; populated for L3 MBO
    pa.field("level_idx", pa.int32(), nullable=True),         # Target depth level index if provided
])
```

---

## 4. Length-Prefixed Binary Serialization & Logical Provenance Hashes

To guarantee that provenance hashes are **deterministic and computationally collision-resistant under the specified canonical serialization protocol**, invariant to Parquet physical chunking, row group layouts, or compression codecs:

### 4.1 Field Binary Encoding Specifications

| Arrow Type | Binary Encoding Protocol | Null Representation |
| :--- | :--- | :--- |
| **`pa.string()`** | `[uint32_be(len)][utf8_bytes]` | `uint32_be(0xFFFFFFFF)` (4-byte null tag, 0 payload bytes) |
| **`pa.decimal128(38, 18)`** | ASCII `f"{dec:.18f}"` $\to$ `[uint32_be(len)][ascii_bytes]` | `uint32_be(0xFFFFFFFF)` |
| **`pa.timestamp("ns", tz="UTC")`** | `[int64_be(epoch_nanoseconds)]` (8 bytes, lossless nanoseconds) | `[int64_be(-9223372036854775808)]` (`0x8000000000000000`) |
| **`pa.timestamp("us", tz="UTC")`** | `[int64_be(epoch_microseconds)]` (8 bytes, lossless microseconds) | `[int64_be(-9223372036854775808)]` |
| **`pa.date32()`** | `[int32_be(epoch_days)]` (4 bytes, signed integer) | `[int32_be(-2147483648)]` (`0x80000000`) |
| **`pa.int64()`** | `[int64_be(val)]` (8 bytes, signed big-endian) | `[int64_be(-9223372036854775808)]` |
| **`pa.int32()`** | `[int32_be(val)]` (4 bytes, signed big-endian) | `[int32_be(-2147483648)]` |
| **Record Separator** | Single byte `0x1E` between records | N/A |

### 4.2 Hashing Execution Protocols

1. **`calculate_canonical_book_snapshot_sha256(table: pa.Table) -> str`**:
   - Check schema completeness.
   - Sort table strictly by Snapshot Row Identity ASC: `(source_id, channel_id, symbol, trading_date, source_seq_num, side, level_idx)`.
   - Stream rows using length-prefixed binary encoding into `hashlib.sha256()`.

2. **`calculate_canonical_book_delta_sha256(table: pa.Table) -> str`**:
   - Check schema completeness.
   - Sort table strictly by Delta Row Identity ASC: `(source_id, channel_id, symbol, trading_date, source_seq_num, action_sub_idx)`.
   - Stream rows using length-prefixed binary encoding into `hashlib.sha256()`.

---

## 5. Order Book State Reconstruction Engine (`OrderBookReconstructor`)

The Book State Reconstruction Engine is an in-memory, deterministic state machine responsible for taking raw canonical Snapshots and Deltas and reconstructing the exact price depth ladder:

```
[Snapshot at seq_0] ──► Initialize Bids (Desc) & Asks (Asc)
                              │
                              ▼
[Delta seq_1] ──► Apply Action (ADD / MODIFY / CANCEL / CLEAR)
                              │
                              ▼
[Delta seq_2] ──► Apply Action ...
                              │
                              ▼
[State Verification] ──► Check Crossed Book (Bid_0 >= Ask_0)
                              │
                              ▼
[Output] ──► Top-N Depth Ladder Snapshot at Time T
```

### 5.1 Ladder Invariants & State Rules
1. **Sorted Price Levels:**
   - Bids are maintained in strict descending price order: $P_{\text{bid}, 0} > P_{\text{bid}, 1} > \dots > P_{\text{bid}, k}$.
   - Asks are maintained in strict ascending price order: $P_{\text{ask}, 0} < P_{\text{ask}, 1} < \dots < P_{\text{ask}, k}$.
2. **Action Transition Mechanics:**
   - `ADD`: Insert new price level. If price already exists, update size.
   - `MODIFY`: Update size of existing price level.
   - `CANCEL`: If size reduces to $\le 0$, remove price level from ladder.
   - `CLEAR`: Clear entire side or book ladder.
3. **Crossed Book Anomaly Handling:**
   - If $P_{\text{bid}, 0} \ge P_{\text{ask}, 0}$ occurs during normal matching or auction transitions, the engine flags `CROSSED_BOOK_ANOMALY` in telemetry without throwing an unrecoverable crash or mutating raw data.
4. **Sequence Discontinuity & State Invalidation:**
   - If an undeclared sequence gap occurs ($\text{seq}_{i+1} > \text{seq}_i + 1$) without a preceding snapshot, the book state transitions to `STATE_INVALID_GAP` until the next valid snapshot is applied.

---

## 6. Storage Layout & DuckDB Point-in-Time Qualification

### 6.1 Partition Layout

```
data/
└── parquet/
    └── orderbook/
        ├── snapshots/
        │   └── {symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
        └── deltas/
            └── {symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
```

### 6.2 DuckDB Point-in-Time Ladder Query
To reconstruct the Order Book state at target exchange time $T_{\text{target}}$ as observed at or before $T_{\text{knowledge}}$:
1. **Query Latest Snapshot:**
   ```sql
   SELECT * FROM read_parquet('data/parquet/orderbook/snapshots/{symbol}/**/*.parquet')
   WHERE knowledge_time_utc <= $as_of_knowledge_time_utc
     AND exchange_time_utc <= $target_exchange_time_utc
   ORDER BY exchange_time_utc DESC, source_seq_num DESC
   LIMIT 1
   ```
2. **Query Subsequent Deltas:**
   ```sql
   SELECT * FROM read_parquet('data/parquet/orderbook/deltas/{symbol}/**/*.parquet')
   WHERE knowledge_time_utc <= $as_of_knowledge_time_utc
     AND exchange_time_utc >= $snapshot_exchange_time_utc
     AND exchange_time_utc <= $target_exchange_time_utc
     AND source_seq_num >= $snapshot_source_seq_num
   ORDER BY exchange_time_utc ASC, source_seq_num ASC, action_sub_idx ASC
   ```
3. Feed Snapshot + Deltas into `OrderBookReconstructor` to obtain the exact Top-N Depth Ladder.

---

## 7. Gate 3B Acceptance Criteria & Test Matrix

Phase 3B completion is governed by the following test matrix:

- [ ] **Schema Conformance:** Both `CANONICAL_BOOK_SNAPSHOT_SCHEMA` and `CANONICAL_BOOK_DELTA_SCHEMA` strictly enforced.
- [ ] **Permutation Invariance:** Permuting snapshot/delta rows produces identical cryptographic hashes.
- [ ] **Codec Invariance:** Writing via `zstd` vs `snappy` produces identical hashes.
- [ ] **Hash Modification Sensitivity:** Any change to price, size, side, action, or timestamp alters the hash.
- [ ] **Length-Prefixed Delimiter Safety:** Escapes special characters without delimiter collisions.
- [ ] **Ladder Reconstruction Match:** State reconstructor accurately reflects Top-N Bids and Asks across complex sequence of additions, modifications, and cancellations.
- [ ] **Crossed Book Detection:** Crossed quotes ($P_{\text{bid}} \ge P_{\text{ask}}$) emit `CROSSED_BOOK_ANOMALY`.
- [ ] **Sequence Gap Invalidation:** Skipped sequence numbers invalidate ladder state until next snapshot.
- [ ] **Idempotent Ingestion:** Replaying identical snapshot/delta batches returns existing part files.
- [ ] **Batch Collision Detection:** Modifying content under same `batch_id` raises `BatchCollisionError`.
- [ ] **Duplicate Row Identity Rejection:** Duplicate Snapshot/Delta Row Identities raise `IntegrityViolationError`.
- [ ] **DuckDB Point-in-Time Query:** Verifies zero look-ahead leakage when reconstructing historical depth.
