# ACASH — Phase 3B: Canonical Order Book Subsystem Design Proposal & Data Contract

**Document:** `docs/PHASE_3B_DESIGN_PROPOSAL.md`  
**Version:** 1.5.0  
**Date:** 2026-08-28  
**Status:** **PROPOSED — FINAL ARCHITECTURAL LOCK (Awaiting Formal Sign-off)**  

---

## 1. Executive Summary & Problem Statement

In market microstructure research (e.g. CME ES/NQ futures), the **Order Book** represents the stateful supply and demand queue across price levels.

Unlike **Trades (Phase 3A)**, which are discrete completed matching events (point process), the **Order Book (Phase 3B)** is a **dynamic stateful priority ladder**:
1. It is communicated via two complementary feed channels:
   - **L2 Depth Snapshots (MBP - Market By Price):** Periodic full state captures of depth price levels across bid and ask sides.
   - **L2/L3 Incremental Deltas:** Mutation events (`ADD`, `MODIFY`, `CANCEL`, `DELETE`, `CLEAR`) carrying adapter-defined ordering tokens.
2. An analytical research query requesting *"What was the exact Top-10 Depth Ladder at time $T_{\text{target}}$ as observed at or before $T_{\text{knowledge}}$?"* requires a **deterministic Book State Reconstruction Engine** that:
   - Operates strictly within an **immutable Stream Scope** `(source_id, channel_id, symbol, trading_date)`.
   - Selects the latest complete **Snapshot Frame** prior to $T_{\text{target}}$ knowable at $T_{\text{knowledge}}$, with deterministic tie-breaking.
   - Applies subsequent incremental deltas strictly following the snapshot ordering boundary up to $T_{\text{target}}$ knowable at $T_{\text{knowledge}}$ using adapter-defined `SourceOrderingPolicy` and normalized resulting quantities.

```
                                      PHASE 3B ORDER BOOK TOPOLOGY
                                                    │
                 ┌──────────────────────────────────┴──────────────────────────────────┐
                 ▼                                                                     ▼
    CANONICAL SNAPSHOTS (MBP)                                             CANONICAL DELTAS (MBP/MBO)
  - Multi-row atomic snapshot frames                                    - Incremental Atomic Mutations
  - Contract-driven shape completeness                                  - Normalized resulting quantity semantics
  - Explicit snapshot_order_key anchor                                  - Explicit source_order_key token
  - Scoped to (source, channel, symbol, date)                           - Nullable control fields for CLEAR
                 │                                                                     │
                 └──────────────────────────────────┬──────────────────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  BOOK STATE RECONSTRUCTION ENGINE       │
                               │  - Immutable Stream Scope               │
                               │  - Multi-Row Frame Compound Root        │
                               │  - Deterministic Final Tie-Breaker      │
                               │  - Strict Ordering Tuple Boundary       │
                               │  - Normalized Resulting Size Semantics  │
                               │  - Adapter SourceOrderingPolicy         │
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

## 3. Snapshot Frame Identity, Uniqueness & Contract-Driven Shape Completeness

> [!IMPORTANT]
> **Snapshot Frame Compound Identity & Completeness Principle:**
> A snapshot is **NOT a single row**; it is an **atomic multi-row frame** representing a full price ladder across bid and ask sides.
>
> 1. **Snapshot Frame Identity & Uniqueness Scope:**  
>    The `snapshot_id` string is unique within the compound frame scope:
>    $$\text{Compound Frame Identity} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date}, \text{source\_seq\_num}, \text{snapshot\_id})$$
>
> 2. **Contract-Driven Snapshot Shape Policy:**  
>    ACASH core does **NOT universally assume** a fixed $N$ levels on both sides. Shape completeness is declared by the source/adapter contract:
>    - `FIXED_DEPTH_N`: Source guarantees exactly $N$ depth levels for both Bid and Ask (e.g. Top 10 BBO).
>    - `VARIABLE_DEPTH`: Source emits dynamic or sparse depth levels according to active market liquidity.
>    - `SOURCE_DECLARED_COMPLETE`: Completeness is certified by source-provided completion markers or packet flags.
>
> 3. **Frame Metadata Consistency:**  
>    All rows sharing the same Compound Frame Identity **MUST** share identical `exchange_time_utc`, `feed_time_utc`, `knowledge_time_utc`, `trading_date`, `source_seq_num`, `source_order_key`, and `is_snapshot_complete` flags. Differing metadata within the same frame is rejected as `FRAME_METADATA_INCONSISTENCY`.
>
> 4. **Reconstructor Rule:**  
>    The Reconstructor **strictly rejects** incomplete snapshots as state roots (`PARTIAL_SNAPSHOT_REJECTED`).

---

## 4. Adapter-Defined Source Ordering Policy & `source_order_key`

> [!IMPORTANT]
> **Opaque Ordering Token Contract:**
> `source_seq_num` is an opaque upstream sequence identifier whose ordering and contiguity are source-specific and are never assumed by the canonical core unless explicitly guaranteed by the adapter contract.
>
> 1. **`source_order_key` Specification:**  
>    - Type: `pa.string()` (non-null string).
>    - An adapter-supplied reconstruction order token.
>    - The core engine treats it as an **opaque string token** and **MUST NOT perform arithmetic or infer contiguity from it**.
>    - For feeds where upstream `source_seq_num` is authoritative for ordering, the adapter normalizes/derives `source_order_key` (e.g. zero-padded string `f"{seq:020d}"`) to guarantee lexicographical compatibility.
>
> 2. **`SourceOrderingPolicy`:**  
>    ```python
>    class SourceOrderingPolicy(str, Enum):
>        OPAQUE = "OPAQUE"                     # Ordered strictly by (exchange_time_utc, source_order_key, action_sub_idx)
>        MONOTONIC_INTEGER = "MONOTONIC_INTEGER" # Monotonically increasing sequence within channel/session
>        CONTIGUOUS_PACKET = "CONTIGUOUS_PACKET" # Strict arithmetic contiguity guaranteed by source feed
>        RESET_AWARE = "RESET_AWARE"           # Declared session rollover / channel reconnect reset support
>    ```
>
> 3. **Unorderable Fallback (`STATE_UNORDERABLE`):**  
>    If the source adapter cannot guarantee trustworthy event ordering for a feed, the Reconstructor marks the state as `STATE_UNORDERABLE` and refuses reconstruction rather than guessing order.

---

## 5. Normalized Canonical Delta Action Payload & Quantity Semantics

> [!IMPORTANT]
> **Strict Resulting Quantity Normalization (Zero Core Ambiguity):**
> Source adapters normalize upstream message variants (e.g. CME SBE relative size changes vs remaining sizes) into canonical resulting quantities before emitting records. The core reconstruction engine operates strictly on **Resulting Quantities**:

### 5.1 MBP (Market By Price — L2 Price-Level Deltas)
- **`ADD`**: `price` ($> 0$), `size` ($> 0$), `level_idx` required. `size` represents the **initial aggregated level quantity**.
- **`MODIFY`**: `price` ($> 0$), `size` ($> 0$), `level_idx` required. `size` represents the **resulting new absolute aggregated quantity** at this price level.
- **`CANCEL`**: `price` ($> 0$), `size` ($\ge 0$). `size` represents the **resulting remaining aggregated quantity**; if remaining size is `0`, the level is deleted from the ladder.
- **`DELETE`**: `price` ($> 0$), `size = Decimal("0")`. Price level is immediately purged from the ladder.
- **`CLEAR`**: Control action.
  $$\text{CLEAR Payload Invariants}: \quad \text{price} = \text{None}, \; \text{size} = \text{None}, \; \text{level\_idx} = \text{None}, \; \text{order\_id} = \text{None}, \; \text{side} \in \{\text{"BID"}, \text{"ASK"}, \text{"ALL"}\}$$
  `CLEAR` is classified as a control action and is **strictly excluded from positive price/size validation**.

### 5.2 MBO (Market By Order — L3 Order-Level Deltas)
- **`ADD`**: `order_id` (non-null, non-empty string), `price` ($> 0$), `size` ($> 0$). `size` represents the **initial order quantity** with FIFO queue priority.
- **`MODIFY`**: `order_id` (non-null, non-empty string), `price` ($> 0$), `size` ($> 0$). `size` represents the **resulting remaining order quantity**; price modification resets FIFO queue priority.
- **`CANCEL`**: `order_id` (non-null, non-empty string), `size` ($\ge 0$). `size` represents the **resulting remaining order quantity**; if `0`, the order is purged from the queue.
- **`DELETE`**: `order_id` (non-null, non-empty string), `size = Decimal("0")`. Order is immediately purged from the queue.
- **L2 Aggregation:** MBO Reconstructor maintains discrete order queues and aggregates active orders by price level to project the canonical L2 depth view.

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
    pa.field("source_order_key", pa.string(), nullable=False),    # Adapter ordering anchor token
    pa.field("snapshot_id", pa.string(), nullable=False),         # Compound Frame Group Identifier
    pa.field("is_snapshot_complete", pa.bool_(), nullable=False), # Contract-certified completeness
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
    pa.field("source_order_key", pa.string(), nullable=False),    # Adapter ordering token
    pa.field("action_sub_idx", pa.int32(), nullable=False),       # 0, 1, 2... within packet
    pa.field("delta_type", pa.string(), nullable=False),         # "MBP" or "MBO"
    pa.field("action", pa.string(), nullable=False),             # "ADD", "MODIFY", "CANCEL", "DELETE", "CLEAR"
    pa.field("side", pa.string(), nullable=False),               # "BID", "ASK", "ALL" (for CLEAR)
    pa.field("price", pa.decimal128(38, 18), nullable=True),     # Nullable ONLY for CLEAR control actions
    pa.field("size", pa.decimal128(38, 18), nullable=True),      # Nullable ONLY for CLEAR control actions
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

## 9. Storage Layout, Stream Scope & Strict Ordering Tuple Boundary PIT Queries

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

### 9.2 Scoped Two-Stage Multi-Row Point-in-Time (PIT) Queries

To reconstruct the Order Book state for stream `($source_id, $channel_id, $symbol, $trading_date)` at target exchange time $T_{\text{target}}$ as observed at or before $T_{\text{knowledge}}$:

#### Stage 1: Select Candidate Snapshot Frame with Deterministic Tie-Breaker & Retrieve ALL Frame Rows
```sql
WITH candidate_frame AS (
    SELECT
        source_id,
        channel_id,
        symbol,
        trading_date,
        source_seq_num,
        source_order_key,
        snapshot_id,
        exchange_time_utc
    FROM read_parquet('data/parquet/orderbook/snapshots/{symbol}/**/*.parquet')
    WHERE source_id = ?
      AND channel_id = ?
      AND symbol = ?
      AND trading_date = CAST(? AS DATE)
      AND knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
      AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ)
      AND is_snapshot_complete = TRUE
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY source_id, channel_id, symbol, trading_date
        ORDER BY
            exchange_time_utc DESC,
            source_order_key DESC,
            knowledge_time_utc DESC,
            snapshot_id ASC  -- Final deterministic tie-breaker
    ) = 1
)
SELECT s.*
FROM read_parquet('data/parquet/orderbook/snapshots/{symbol}/**/*.parquet') s
JOIN candidate_frame c
  ON s.source_id = c.source_id
 AND s.channel_id = c.channel_id
 AND s.symbol = c.symbol
 AND s.trading_date = c.trading_date
 AND s.source_seq_num = c.source_seq_num
 AND s.snapshot_id = c.snapshot_id
WHERE s.knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
ORDER BY s.side ASC, s.level_idx ASC;
```

#### Stage 2: Select Subsequent Incremental Deltas Strictly After Snapshot Boundary
The canonical boundary evaluates the adapter ordering tuple $(\text{exchange\_time\_utc}, \text{source\_order\_key})$. A delta is eligible strictly when its tuple is after the snapshot's boundary:
```sql
SELECT * FROM read_parquet('data/parquet/orderbook/deltas/{symbol}/**/*.parquet')
WHERE source_id = ?
  AND channel_id = ?
  AND symbol = ?
  AND trading_date = CAST(? AS DATE)
  AND knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
  AND (
    (exchange_time_utc = CAST(? AS TIMESTAMPTZ) AND source_order_key > ?) -- Strictly AFTER snapshot order token
    OR (exchange_time_utc > CAST(? AS TIMESTAMPTZ) AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ))
  )
ORDER BY exchange_time_utc ASC, source_order_key ASC, action_sub_idx ASC;
```

#### Stage 3: In-Memory State Ladder Execution
The Reconstructor initializes the depth ladder with the complete Snapshot Frame rows and applies subsequent deltas according to the adapter's `SourceOrderingPolicy`, emitting the exact Top-$N$ Depth Ladder at $T_{\text{target}}$.

---

## 10. Gate 3B Acceptance Criteria & Comprehensive Test Matrix

Phase 3B completion is governed by the following test matrix:

- [ ] **Schema Conformance:** Both `CANONICAL_BOOK_SNAPSHOT_SCHEMA` and `CANONICAL_BOOK_DELTA_SCHEMA` strictly enforced, including `source_order_key: pa.string()`, `is_snapshot_complete: pa.bool_()`, and nullable price/size for `CLEAR`.
- [ ] **Deterministic Snapshot Frame Selection:** Stage 1 PIT query selects the full multi-level snapshot frame and uses `snapshot_id ASC` as a deterministic tie-breaker when timestamps and ordering keys match.
- [ ] **Compound Join Scope:** Stage 1 PIT retrieval joins on `(source_id, channel_id, symbol, trading_date, source_seq_num, snapshot_id)`, preventing cross-stream collision.
- [ ] **Contract-Driven Snapshot Completeness:** Reconstructor validates shape completeness according to declared policy (`FIXED_DEPTH_N`, `VARIABLE_DEPTH`, `SOURCE_DECLARED_COMPLETE`) and rejects incomplete frames (`PARTIAL_SNAPSHOT_REJECTED`).
- [ ] **Frame Metadata Consistency:** Validator rejects snapshot tables where rows with the same Compound Frame Identity contain conflicting timestamp/sequence/order-key metadata.
- [ ] **Normalized MBP Action Payload Semantics:** Verifies accurate ladder state transitions for `ADD` ($>0$), `MODIFY` (resulting absolute size), `CANCEL` (remaining size), `DELETE` (size 0), and `CLEAR` (`price=None, size=None, side in {BID, ASK, ALL}`).
- [ ] **Normalized MBO Order Queue Semantics:** Verifies discrete order queue tracking with non-empty `order_id`, FIFO priority, priority reset on price modification, and L2 depth projection.
- [ ] **Stream Scope & Strict Ordering Tuple Boundary:** Verifies that deltas from a different stream are rejected and deltas preceding or equal to the snapshot ordering tuple `(exchange_time_utc, source_order_key)` are not double-applied.
- [ ] **Adapter SourceOrderingPolicy Compliance:** Reconstructor obeys adapter-defined ordering without imposing generic sequence contiguity on opaque feeds, marking `STATE_UNORDERABLE` if untrustworthy.
- [ ] **Crossed State Granularity:** Reconstructor distinguishes `CROSSED_TRANSIENT`, `CROSSED_AUCTION_OR_HALT`, and `CROSSED_DUE_TO_INVALID_RECONSTRUCTION`.
- [ ] **Permutation & Codec Invariance:** Permuting snapshot/delta rows or changing compression codec produces identical hashes.
- [ ] **Hash Modification Sensitivity:** Any field modification alters the cryptographic hash.
- [ ] **Idempotent Ingestion & Batch Collision:** Replaying identical snapshot/delta batches returns existing part files; modified payloads raise `BatchCollisionError`.
- [ ] **Duplicate Row Identity Rejection:** Duplicate Snapshot/Delta Row Identities raise `IntegrityViolationError`.
- [ ] **Dual-Temporal PIT Query Test:** Verifies that historical replay strictly respects both $T_{\text{target}}$ and $T_{\text{knowledge}}$ with zero lookahead.
