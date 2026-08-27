# ACASH — Phase 3B: Canonical Order Book Subsystem Design Proposal & Data Contract

**Document:** `docs/PHASE_3B_DESIGN_PROPOSAL.md`  
**Version:** 1.2.0  
**Date:** 2026-08-27  
**Status:** **PROPOSED — AWAITING ARCHITECTURAL REVIEW & CONTRACT SIGN-OFF**  

---

## 1. Executive Summary & Problem Statement

In market microstructure research (e.g. CME ES/NQ futures), the **Order Book** represents the stateful supply and demand queue across price levels.

Unlike **Trades (Phase 3A)**, which are discrete completed matching events (point process), the **Order Book (Phase 3B)** is a **dynamic stateful priority ladder**:
1. It is communicated via two complementary feed channels:
   - **L2 Depth Snapshots (MBP - Market By Price):** Periodic full state captures of the top $N$ price levels (e.g. Top 10 Bids and Top 10 Asks).
   - **L2/L3 Incremental Deltas:** High-frequency mutation events (`ADD`, `MODIFY`, `DELETE`, `CLEAR`) with monotonic message sequence numbers.
2. An analytical research query requesting *"What was the exact Top-10 Depth Ladder at time $T_{\text{target}}$ as observed at or before $T_{\text{knowledge}}$?"* requires a **deterministic Book State Reconstruction Engine** that:
   - Selects the latest complete **Snapshot Frame** (all multi-level rows sharing the frame's `snapshot_id`) prior to $T_{\text{target}}$ knowable at $T_{\text{knowledge}}$.
   - Applies all subsequent incremental deltas up to $T_{\text{target}}$ knowable at $T_{\text{knowledge}}$ using adapter-defined source ordering semantics.

```
                                      PHASE 3B ORDER BOOK TOPOLOGY
                                                    │
                 ┌──────────────────────────────────┴──────────────────────────────────┐
                 ▼                                                                     ▼
    CANONICAL SNAPSHOTS (MBP)                                             CANONICAL DELTAS (MBP/MBO)
  - Multi-row atomic snapshot frames                                    - Incremental Atomic Mutations
  - Explicit frame completeness & shape                                 - Explicit MBP vs MBO semantics
  - Daily Parquet Partition                                             - Daily Parquet Partition
                 │                                                                     │
                 └──────────────────────────────────┬──────────────────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  BOOK STATE RECONSTRUCTION ENGINE       │
                               │  - Selects Full Multi-Row Frame Root    │
                               │  - Sequentially applies Deltas          │
                               │  - Adapter-defined SourceOrderingPolicy │
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

## 3. Snapshot Frame Identity, Completeness & Shape Consistency

> [!IMPORTANT]
> **Snapshot Frame & Multi-Row Completeness Principle:**
> A snapshot is **NOT a single row**; it is an **atomic multi-row frame** representing a full price ladder across both sides.
>
> 1. **Snapshot Frame Identity (`snapshot_id`):**  
>    Globally unique frame identifier scoped to:
>    $$\text{snapshot\_id} = \text{snap\_}\{\text{source\_id}\}\_\{\text{channel\_id}\}\_\{\text{symbol}\}\_\{\text{trading\_date}\}\_\{\text{source\_seq\_num}\}$$
> 2. **Completeness & Shape Verification:**  
>    `is_snapshot_complete` is **NOT an arbitrary boolean**; it is established by the source adapter via explicit contract checks:
>    - Verification that all expected depth levels ($0 \dots N-1$) for both `BID` and `ASK` sides are present in the frame.
>    - Verification of source-provided end-of-snapshot / completion message markers.
>    - **Frame Metadata Consistency:** All rows sharing the same `snapshot_id` **MUST** share identical `exchange_time_utc`, `feed_time_utc`, `knowledge_time_utc`, `trading_date`, `source_seq_num`, and `is_snapshot_complete` flags. Differing metadata within the same `snapshot_id` is rejected as `FRAME_METADATA_INCONSISTENCY`.
> 3. **Reconstructor Rule:**  
>    The Reconstructor **strictly rejects** partial or incomplete snapshots as state roots (`PARTIAL_SNAPSHOT_REJECTED`).

---

## 4. Adapter-Defined Source Ordering Policy (`SourceOrderingPolicy`)

> [!IMPORTANT]
> **Decoupling Sequence Number from Reconstruction Ordering Primitives:**
> In accordance with ADR-020, `source_seq_num` is an opaque upstream identifier. The core engine **MUST NOT** assume that $seq_{i+1} > seq_i$ implies temporal succession or that $seq_{i+1} == seq_i + 1$ implies contiguity across all feeds.
>
> Ordering and gap semantics are defined by the **Source Adapter** via explicit policies:
>
> ```python
> class SourceOrderingPolicy(str, Enum):
>     OPAQUE = "OPAQUE"                     # No arithmetic ordering assumed; ordered strictly by (exchange_time_utc, source_order_key)
>     MONOTONIC_INTEGER = "MONOTONIC_INTEGER" # Monotonically increasing sequence within channel/session
>     CONTIGUOUS_PACKET = "CONTIGUOUS_PACKET" # Strict arithmetic contiguity (seq_{i+1} == seq_i + 1) guaranteed by source feed
>     RESET_AWARE = "RESET_AWARE"           # Declared session rollover / channel reconnect reset support
> ```
>
> **Ordering Key:** The Reconstructor orders incoming events by `(exchange_time_utc, source_order_key, action_sub_idx)` where `source_order_key` is supplied by the adapter contract.

---

## 5. Explicit MBP (Price-Level) vs. MBO (Order-Level) Action Payload Semantics

> [!IMPORTANT]
> **No Generic Delta Conflation:**
> L2 Market By Price (MBP) and L3 Market By Order (MBO) operate on fundamentally different entities with distinct payload semantics.

### 5.1 MBP (Market By Price — L2 Price-Level Deltas)
- **Target Entity:** Aggregated Price Level (`price`, `side`, `level_idx`).
- **Action Payloads:**
  - `ADD`: Insert new price level. `size` represents the **initial aggregated quantity** at this price level.
  - `MODIFY`: Update price level. `size` represents the **resulting new absolute aggregated quantity** at this price level (not a relative delta).
  - `DELETE`: Remove price level from the depth ladder (equivalent to resulting quantity = 0).
  - `CLEAR`: Clear entire side (e.g. market pause or session reset).

### 5.2 MBO (Market By Order — L3 Order-Level Deltas)
- **Target Entity:** Discrete Individual Order (`order_id`, `price`, `side`, `priority`).
- **Action Payloads:**
  - `ADD`: Insert new order. `order_id` is required; `size` represents the **initial order quantity** with FIFO priority at `price`.
  - `MODIFY`: Change existing order. `size` represents the **resulting remaining order quantity**; if `price` changes, the order loses queue priority.
  - `CANCEL`: Cancel/reduce order. `size` represents the **cancelled quantity** or reduction in order size; if remaining size is 0, the order is removed.
- **L2 Projection:** The MBO Reconstructor maintains discrete order queues and aggregates active orders by price level to emit the canonical L2 depth view.

---

## 6. Canonical PyArrow Schemas

### 6.1 Canonical Order Book Snapshot Schema (`CANONICAL_BOOK_SNAPSHOT_SCHEMA`)

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
    pa.field("snapshot_id", pa.string(), nullable=False),         # Frame group identifier
    pa.field("is_snapshot_complete", pa.bool_(), nullable=False), # Valid complete frame flag
    pa.field("side", pa.string(), nullable=False),               # "BID", "ASK"
    pa.field("level_idx", pa.int32(), nullable=False),           # 0 = Top of Book (BBO), 1..N Depth
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size", pa.decimal128(38, 18), nullable=False),     # Absolute aggregated size at level
    pa.field("order_count", pa.int32(), nullable=True),          # Queue order count if provided
])
```

### 6.2 Canonical Order Book Incremental Delta Schema (`CANONICAL_BOOK_DELTA_SCHEMA`)

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
    pa.field("action_sub_idx", pa.int32(), nullable=False),       # 0, 1, 2... within packet
    pa.field("delta_type", pa.string(), nullable=False),         # "MBP" or "MBO"
    pa.field("action", pa.string(), nullable=False),             # "ADD", "MODIFY", "DELETE", "CANCEL", "CLEAR"
    pa.field("side", pa.string(), nullable=False),               # "BID", "ASK"
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size", pa.decimal128(38, 18), nullable=False),     # Resulting size (MBP) or Order size (MBO)
    pa.field("order_id", pa.string(), nullable=True),            # Required for MBO, Null for MBP
    pa.field("level_idx", pa.int32(), nullable=True),            # Level index for MBP, Null for MBO
    pa.field("order_count", pa.int32(), nullable=True),          # Resulting order count at level (MBP)
])
```

---

## 7. Crossed-State Anomaly Classification

> [!IMPORTANT]
> **Granular Crossed Book State Classification:**
> When $P_{\text{bid}, 0} \ge P_{\text{ask}, 0}$ occurs during reconstruction, the engine classifies the event into one of four distinct states rather than assuming generic market abnormality:
> 1. **`CROSSED_TRANSIENT`:** Crossed quotes that resolve/uncross within $N$ consecutive deltas or within the same packet / sub-millisecond burst.
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

## 9. Storage Layout & Multi-Row Snapshot Frame PIT Reconstruction Queries

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

### 9.2 Rigorous Two-Stage Multi-Row Point-in-Time (PIT) Queries
To reconstruct the Order Book state at target exchange time $T_{\text{target}}$ as observed at or before $T_{\text{knowledge}}$:

#### Stage 1: Select Candidate Snapshot Frame & Retrieve ALL Frame Rows
```sql
WITH candidate_frame AS (
    SELECT
        snapshot_id,
        exchange_time_utc,
        source_seq_num
    FROM read_parquet('data/parquet/orderbook/snapshots/{symbol}/**/*.parquet')
    WHERE knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
      AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ)
      AND is_snapshot_complete = TRUE
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY source_id, channel_id, symbol, trading_date
        ORDER BY exchange_time_utc DESC, source_seq_num DESC, knowledge_time_utc DESC
    ) = 1
)
SELECT s.*
FROM read_parquet('data/parquet/orderbook/snapshots/{symbol}/**/*.parquet') s
JOIN candidate_frame c
  ON s.snapshot_id = c.snapshot_id
WHERE s.knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
ORDER BY s.side ASC, s.level_idx ASC;
```

#### Stage 2: Select Subsequent Incremental Deltas
```sql
SELECT * FROM read_parquet('data/parquet/orderbook/deltas/{symbol}/**/*.parquet')
WHERE knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
  AND exchange_time_utc >= CAST(? AS TIMESTAMPTZ)
  AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ)
  AND (
    (exchange_time_utc = CAST(? AS TIMESTAMPTZ) AND source_seq_num >= ?)
    OR exchange_time_utc > CAST(? AS TIMESTAMPTZ)
  )
ORDER BY exchange_time_utc ASC, source_seq_num ASC, action_sub_idx ASC;
```

#### Stage 3: In-Memory State Ladder Execution
The Reconstructor initializes the depth ladder with the complete Snapshot Frame rows and applies subsequent deltas according to the adapter's `SourceOrderingPolicy`, emitting the exact Top-$N$ Depth Ladder at $T_{\text{target}}$.

---

## 10. Gate 3B Acceptance Criteria & Comprehensive Test Matrix

Phase 3B completion is governed by the following test matrix:

- [ ] **Schema Conformance:** Both `CANONICAL_BOOK_SNAPSHOT_SCHEMA` and `CANONICAL_BOOK_DELTA_SCHEMA` strictly enforced.
- [ ] **Multi-Row Snapshot Frame Selection:** Verifies that Stage 1 PIT query selects the full multi-level snapshot frame (not a single level row).
- [ ] **Snapshot Completeness Validation:** Reconstructor strictly rejects incomplete snapshot frames (`PARTIAL_SNAPSHOT_REJECTED`).
- [ ] **Frame Metadata Consistency:** Validator rejects snapshot tables where rows with the same `snapshot_id` contain conflicting timestamp/sequence metadata.
- [ ] **MBP Price-Level Reconstruction:** Accurate state transitions for price-level `ADD`, `MODIFY` (resulting absolute quantity), and `DELETE`.
- [ ] **MBO Order-Level Reconstruction:** Accurate order queue tracking by `order_id` and L2 depth aggregation.
- [ ] **Adapter SourceOrderingPolicy Compliance:** Reconstructor obeys adapter-defined ordering without imposing generic sequence contiguity on opaque feeds.
- [ ] **Crossed State Granularity:** Reconstructor distinguishes `CROSSED_TRANSIENT`, `CROSSED_AUCTION_OR_HALT`, and `CROSSED_DUE_TO_INVALID_RECONSTRUCTION`.
- [ ] **Permutation & Codec Invariance:** Permuting snapshot/delta rows or changing compression codec produces identical hashes.
- [ ] **Hash Modification Sensitivity:** Any field modification alters the cryptographic hash.
- [ ] **Idempotent Ingestion & Batch Collision:** Replaying identical snapshot/delta batches returns existing part files; modified payloads raise `BatchCollisionError`.
- [ ] **Duplicate Row Identity Rejection:** Duplicate Snapshot/Delta Row Identities raise `IntegrityViolationError`.
- [ ] **Dual-Temporal PIT Query Test:** Verifies that historical replay strictly respects both $T_{\text{target}}$ and $T_{\text{knowledge}}$ with zero lookahead.
