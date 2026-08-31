# ACASH — Phase 3B: Canonical Order Book Subsystem Design Proposal & Data Contract

**Document:** `docs/proposals/phase_3b_orderbook.md`  
**Version:** 1.8.0  
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
   - Selects the latest complete **Snapshot Frame** prior to $T_{\text{target}}$ knowable at $T_{\text{knowledge}}$, with collision-safe replay-stable deterministic tie-breaking.
   - Applies subsequent incremental deltas strictly following the snapshot boundary via a unified **Canonical Reconstruction Ordering Key** up to $T_{\text{target}}$ knowable at $T_{\text{knowledge}}$, using normalized resulting quantities.

```
                                      PHASE 3B ORDER BOOK TOPOLOGY
                                                    │
                 ┌──────────────────────────────────┴──────────────────────────────────┐
                 ▼                                                                     ▼
    CANONICAL SNAPSHOTS (MBP)                                             CANONICAL DELTAS (MBP/MBO)
  - Multi-row atomic snapshot frames                                    - Incremental Atomic Mutations
  - Contract-driven shape completeness                                  - Normalized resulting quantity semantics
  - Collision-safe canonical snapshot_id                                - Shared ASCII-only source_order_key
  - Scoped to (source, channel, symbol, date)                           - Nullable control fields for CLEAR
                 │                                                                     │
                 └──────────────────────────────────┬──────────────────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  BOOK STATE RECONSTRUCTION ENGINE       │
                               │  - Immutable Stream Scope               │
                               │  - Multi-Row Frame Compound Root        │
                               │  - Collision-Safe Final Tie-Breaker     │
                               │  - Unified Reconstruction Ordering Key  │
                               │  - Strict Unsigned Byte/ASCII Ordering  │
                               │  - Zero Magic Number Tuple Mapping      │
                               │  - Zero source_seq_num Inferences       │
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

## 3. Collision-Safe Snapshot Frame Identity & Contract-Driven Shape Completeness

> [!IMPORTANT]
> **Snapshot Frame Compound Identity & Collision-Safe Derivation:**
> A snapshot is **NOT a single row**; it is an **atomic multi-row frame** representing a full price ladder across bid and ask sides.
>
> 1. **Collision-Safe Canonical `snapshot_id` Derivation:**  
>    To eliminate string delimiter collision hazards, `snapshot_id` is derived deterministically via length-prefixed binary serialization and cryptographic hashing:
>    $$\text{payload} = \text{serialize\_binary}([\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date}, \text{source\_order\_key}])$$
>    $$\text{snapshot\_id} = \text{"snap\_"} + \text{SHA-256}(\text{payload})[:32]$$
>    - `snapshot_id` is **immutable, deterministic, replay-stable, and computationally collision-resistant**.
>    - Compound Frame Identity:
>      $$\text{Compound Frame Identity} = (\text{source\_id}, \text{channel\_id}, \text{symbol}, \text{trading\_date}, \text{source\_seq\_num}, \text{snapshot\_id})$$
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

## 4. Shared `source_order_key` Ordering Domain & Unsigned Byte-Wise Comparison

> [!IMPORTANT]
> **1. Shared Ordering Domain & ASCII Byte-Wise Lexicographical Contract:**
> For any given stream `(source_id, channel_id, symbol, trading_date)`, Snapshot and Delta records **MUST use `source_order_key` values from the same adapter-defined ordering domain**.
> - `source_order_key` **MUST consist strictly of ASCII characters (`0x00` to `0x7F`)**.
> - Comparison **MUST operate on the canonical encoded byte sequence using unsigned lexicographical ordering** (e.g. `"00000000000000000009" < "00000000000000000010"`).
> - Database locale and collation settings **MUST NOT** influence reconstruction ordering (SQL queries strictly enforce binary collation).
>
> **2. Hard Boundary: Zero `source_seq_num` Inferences:**
> - `source_seq_num` is an upstream opaque identifier and **IS NOT a reconstruction ordering primitive**.
> - The ACASH Core Reconstruction Engine **MUST NEVER compare `source_seq_num` arithmetically or lexicographically**.
> - `source_order_key` is the **SOLE** canonical cross-record ordering primitive for reconstruction.
>
> **3. `SourceOrderingPolicy`:**  
> ```python
> class SourceOrderingPolicy(str, Enum):
>     OPAQUE = "OPAQUE"                     # Ordered strictly by (exchange_time_utc, source_order_key, message_type_rank, side_rank, level_or_action_idx)
>     MONOTONIC_INTEGER = "MONOTONIC_INTEGER" # Monotonically increasing sequence within channel/session
>     CONTIGUOUS_PACKET = "CONTIGUOUS_PACKET" # Strict arithmetic contiguity guaranteed by source feed
>     RESET_AWARE = "RESET_AWARE"           # Declared session rollover / channel reconnect reset support
> ```
>
> **4. Unorderable Fallback (`STATE_UNORDERABLE`):**  
> If the source adapter cannot provide a trustworthy total ordering guarantee for a stream, the Reconstructor marks state as `STATE_UNORDERABLE` and refuses reconstruction rather than guessing order.

---

## 5. Unified Canonical Reconstruction Ordering Key (Zero Magic Numbers)

> [!IMPORTANT]
> **Unified 5-Tuple Reconstruction Ordering Model:**
> To eliminate magic numbers, prevent numeric overflow, and resolve coincidence cases between snapshots and deltas, ACASH defines a formal **Canonical Reconstruction Ordering Tuple**:
>
> $$\text{ReconstructionOrder} = (\text{exchange\_time\_utc}, \text{source\_order\_key}, \text{message\_type\_rank}, \text{side\_rank}, \text{level\_or\_action\_idx})$$
>
> ### 5.1 Formal Tuple Field Definitions
> 1. **`exchange_time_utc`**: `timestamp[ns, tz=UTC]` (lossless nanoseconds)
> 2. **`source_order_key`**: `string` (ASCII-only, compared via unsigned byte-wise lexicographical order)
> 3. **`message_type_rank`**: `int` (Precedence rank):
>    - `0` for **`SNAPSHOT_FRAME`** (Root State Snapshot Frame)
>    - `1` for **`INCREMENTAL_DELTA`** (Incremental Mutation)
> 4. **`side_rank`**: `int`:
>    - For `SNAPSHOT_FRAME`: `0` for `"BID"`, `1` for `"ASK"`
>    - For `INCREMENTAL_DELTA`: `0` (constant)
> 5. **`level_or_action_idx`**: `int`:
>    - For `SNAPSHOT_FRAME`: `level_idx` ($0, 1, 2 \dots$)
>    - For `INCREMENTAL_DELTA`: `action_sub_idx` ($0, 1, 2 \dots$)
>
> ### 5.2 Snapshot Boundary & Single Eligibility Rule
> The Root Snapshot Boundary is defined as the snapshot frame's maximum possible ordering coordinate:
> $$\text{Snapshot Boundary} = (\text{snapshot.exchange\_time\_utc}, \text{snapshot.source\_order\_key}, 0, \infty, \infty)$$
>
> A Delta is eligible to be applied to the Root Snapshot if and only if:
> $$\text{delta.ReconstructionOrder} > \text{snapshot.SnapshotBoundary}$$
>
> ### 5.3 Deterministic Coincidence Resolution
> In the exact coincidence case where $\text{delta.exchange\_time\_utc} == \text{snapshot.exchange\_time\_utc}$ AND $\text{delta.source\_order\_key} == \text{snapshot.source\_order\_key}$:
> - The snapshot frame has `message_type_rank = 0`.
> - The incremental delta has `message_type_rank = 1`.
> - Since $\text{rank } 1 > \text{rank } 0$, the delta's ordering key evaluates to **strictly greater** than the snapshot boundary. The delta is deterministically applied after the snapshot frame without ambiguity or double application.

---

## 6. Normalized Canonical Delta Action Payload & Quantity Semantics

> [!IMPORTANT]
> **Strict Resulting Quantity Normalization & Domain Invariants:**
> Source adapters normalize upstream message variants (e.g. CME SBE relative size changes vs remaining sizes) into canonical resulting quantities before emitting records. The core reconstruction engine operates strictly on **Resulting Quantities**:

### 6.1 MBP (Market By Price — L2 Price-Level Deltas)
- **`ADD`**: `price` ($> 0$), `size` ($> 0$), `level_idx` required. `size` represents the **initial aggregated level quantity**. `order_id` **MUST be NULL**.
- **`MODIFY`**: `price` ($> 0$), `size` ($> 0$), `level_idx` required. `size` represents the **resulting new absolute aggregated quantity** at this price level. `order_id` **MUST be NULL**.
- **`CANCEL`**: `price` ($> 0$), `size` ($\ge 0$). `size` represents the **resulting remaining aggregated quantity**; if remaining size is `0`, the level is deleted from the ladder. `order_id` **MUST be NULL**.
- **`DELETE`**: `price` ($> 0$), `size = Decimal("0")`. Price level is immediately purged from the ladder. `order_id` **MUST be NULL**.
- **`CLEAR`**: Control action.
  $$\text{CLEAR Payload Invariants}: \quad \text{price} = \text{None}, \; \text{size} = \text{None}, \; \text{level\_idx} = \text{None}, \; \text{order\_id} = \text{None}, \; \text{side} \in \{\text{"BID"}, \text{"ASK"}, \text{"ALL"}\}$$
  `CLEAR` is classified as a control action and is **strictly excluded from positive price/size validation**.

### 6.2 MBO (Market By Order — L3 Order-Level Deltas)
- **`ADD`**: `order_id` (non-null, non-empty string required: `order_id != None and len(order_id) > 0`), `price` ($> 0$), `size` ($> 0$). `size` represents the **initial order quantity** with FIFO queue priority.
- **`MODIFY`**: `order_id` (non-null, non-empty string required), `price` ($> 0$), `size` ($> 0$). `size` represents the **resulting remaining order quantity**; price modification resets FIFO queue priority.
- **`CANCEL`**: `order_id` (non-null, non-empty string required), `size` ($\ge 0$). `size` represents the **resulting remaining order quantity**; if `0`, the order is purged from the queue.
- **`DELETE`**: `order_id` (non-null, non-empty string required), `size = Decimal("0")`. Order is immediately purged from the queue.
- **L2 Aggregation:** MBO Reconstructor maintains discrete order queues and aggregates active orders by price level to project the canonical L2 depth view.

---

## 7. Canonical PyArrow Schemas

### 7.1 Canonical Order Book Snapshot Schema (`CANONICAL_BOOK_SNAPSHOT_SCHEMA`)

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
    pa.field("source_order_key", pa.string(), nullable=False),    # ASCII-only total-ordered token
    pa.field("snapshot_id", pa.string(), nullable=False),         # Collision-safe Frame Identifier
    pa.field("is_snapshot_complete", pa.bool_(), nullable=False), # Contract-certified completeness
    pa.field("side", pa.string(), nullable=False),               # "BID", "ASK"
    pa.field("level_idx", pa.int32(), nullable=False),           # 0 = Top of Book (BBO), 1..N Depth
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size", pa.decimal128(38, 18), nullable=False),     # Absolute aggregated size at level
    pa.field("order_count", pa.int32(), nullable=True),          # Queue order count if provided
])
```

### 7.2 Canonical Order Book Incremental Delta Schema (`CANONICAL_BOOK_DELTA_SCHEMA`)

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
    pa.field("source_order_key", pa.string(), nullable=False),    # ASCII-only total-ordered token
    pa.field("action_sub_idx", pa.int32(), nullable=False),       # 0, 1, 2... within packet
    pa.field("delta_type", pa.string(), nullable=False),         # "MBP" or "MBO"
    pa.field("action", pa.string(), nullable=False),             # "ADD", "MODIFY", "CANCEL", "DELETE", "CLEAR"
    pa.field("side", pa.string(), nullable=False),               # "BID", "ASK", "ALL" (for CLEAR)
    pa.field("price", pa.decimal128(38, 18), nullable=True),     # Nullable ONLY for CLEAR control actions
    pa.field("size", pa.decimal128(38, 18), nullable=True),      # Nullable ONLY for CLEAR control actions
    pa.field("order_id", pa.string(), nullable=True),            # Required for MBO, MUST be NULL for MBP
    pa.field("level_idx", pa.int32(), nullable=True),            # Level index for MBP, Null for MBO
    pa.field("order_count", pa.int32(), nullable=True),          # Resulting order count at level (MBP)
])
```

---

## 8. Crossed-State Anomaly Classification

> [!IMPORTANT]
> **Granular Crossed Book State Classification:**
> When $P_{\text{bid}, 0} \ge P_{\text{ask}, 0}$ occurs during reconstruction, the engine classifies the event into one of four distinct states rather than assuming generic market abnormality:
> 1. **`CROSSED_TRANSIENT`:** Crossed quotes that resolve/uncross within $N$ consecutive deltas or within the same packet / sub-millisecond burst.
> 2. **`CROSSED_AUCTION_OR_HALT`:** Crossed quotes occurring during designated auction matching or market halt sessions.
> 3. **`CROSSED_DUE_TO_INVALID_RECONSTRUCTION`:** Crossed quotes caused by missing deltas, packet gaps, or out-of-order mutations.
> 4. **`CROSSED_PERSISTENT_ANOMALY`:** True persistent crossed book in normal continuous trading.

---

## 9. Length-Prefixed Binary Serialization & Logical Provenance Hashes

To guarantee that provenance hashes are **deterministic and computationally collision-resistant under the specified canonical serialization protocol**, invariant to Parquet physical chunking, row group layouts, or compression codecs:

### 9.1 Field Binary Encoding Specifications

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

### 9.2 Hashing Execution Protocols

1. **`calculate_canonical_book_snapshot_sha256(table: pa.Table) -> str`**:
   - Check schema completeness.
   - Sort table strictly by Snapshot Row Identity ASC: `(source_id, channel_id, symbol, trading_date, source_seq_num, side, level_idx)`.
   - Stream rows using length-prefixed binary encoding into `hashlib.sha256()`.

2. **`calculate_canonical_book_delta_sha256(table: pa.Table) -> str`**:
   - Check schema completeness.
   - Sort table strictly by Delta Row Identity ASC: `(source_id, channel_id, symbol, trading_date, source_seq_num, action_sub_idx)`.
   - Stream rows using length-prefixed binary encoding into `hashlib.sha256()`.

---

## 10. Storage Layout, Stream Scope & Strict Ordering Tuple Boundary PIT Queries

### 10.1 Storage Layout

```
data/
└── parquet/
    └── orderbook/
        ├── snapshots/
        │   └── {symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
        └── deltas/
            └── {symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
```

### 10.2 Scoped Two-Stage Multi-Row Point-in-Time (PIT) Queries

To reconstruct the Order Book state for stream `($source_id, $channel_id, $symbol, $trading_date)` at target exchange time $T_{\text{target}}$ as observed at or before $T_{\text{knowledge}}$:

#### Stage 1: Select Candidate Snapshot Frame with Collision-Safe Tie-Breaker & Retrieve ALL Frame Rows
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
            snapshot_id ASC  -- Collision-safe deterministic tie-breaker
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
    (exchange_time_utc = CAST(? AS TIMESTAMPTZ) AND source_order_key >= ?) -- Evaluated in memory via ReconstructionOrder > boundary
    OR (exchange_time_utc > CAST(? AS TIMESTAMPTZ) AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ))
  )
ORDER BY exchange_time_utc ASC, source_order_key ASC, action_sub_idx ASC;
```

#### Stage 3: In-Memory State Ladder Execution
The Reconstructor initializes the depth ladder with the complete Snapshot Frame rows and applies subsequent deltas according to the Unified Reconstruction Ordering rule:
$$\text{delta.ReconstructionOrder} > \text{snapshot.SnapshotBoundary}$$
emitting the exact Top-$N$ Depth Ladder at $T_{\text{target}}$.

---

## 11. Gate 3B Acceptance Criteria & Comprehensive Test Matrix

Phase 3B completion is governed by the following test matrix:

- [ ] **Schema Conformance:** Both `CANONICAL_BOOK_SNAPSHOT_SCHEMA` and `CANONICAL_BOOK_DELTA_SCHEMA` strictly enforced, including `source_order_key: pa.string()`, `is_snapshot_complete: pa.bool_()`, and nullable price/size for `CLEAR`.
- [ ] **ASCII-Only & Unsigned Byte-Wise Comparability:** Verifies that `source_order_key` consists strictly of ASCII characters and compares deterministically using unsigned byte-wise lexicographical order (e.g. `"00000000000000000009" < "00000000000000000010"`), independent of database locale/collation.
- [ ] **Collision-Safe `snapshot_id` Derivation:** Verifies that `snapshot_id` is derived via length-prefixed binary serialization and SHA-256, proving immunity to string delimiter collisions.
- [ ] **Deterministic Snapshot Frame Selection & Stability:** Stage 1 PIT query selects the full multi-level snapshot frame and uses replay-stable `snapshot_id ASC` as a deterministic tie-breaker.
- [ ] **Compound Join Scope:** Stage 1 PIT retrieval joins on `(source_id, channel_id, symbol, trading_date, source_seq_num, snapshot_id)`, preventing cross-stream collision.
- [ ] **Contract-Driven Snapshot Completeness:** Reconstructor validates shape completeness according to declared policy (`FIXED_DEPTH_N`, `VARIABLE_DEPTH`, `SOURCE_DECLARED_COMPLETE`) and rejects incomplete frames (`PARTIAL_SNAPSHOT_REJECTED`).
- [ ] **Frame Metadata Consistency:** Validator rejects snapshot tables where rows with the same Compound Frame Identity contain conflicting timestamp/sequence/order-key metadata.
- [ ] **Clean Tuple Mapping (Zero Magic Numbers):** Verifies that `ReconstructionOrder` correctly evaluates `(side_rank, level_or_action_idx)` without arbitrary offsets.
- [ ] **Proof of Zero `source_seq_num` Ordering Dependency:** Verifies that modifying or reversing `source_seq_num` values has zero effect on reconstruction order when `source_order_key` is preserved.
- [ ] **Same Timestamp & Same Order Key Coincidence Test:** Verifies that when $\text{snapshot.time} == \text{delta.time}$ and $\text{snapshot.key} == \text{delta.key}$, the delta is deterministically applied via $\text{rank } 1 > \text{rank } 0$.
- [ ] **Normalized MBP Action Payload Semantics:** Verifies accurate ladder state transitions for `ADD` ($>0$), `MODIFY` (resulting absolute size), `CANCEL` (remaining size), `DELETE` (size 0), and `CLEAR` (`price=None, size=None, side in {BID, ASK, ALL}`).
- [ ] **MBP order_id Null Invariant:** Validator strictly enforces `order_id is None` for all MBP actions.
- [ ] **Normalized MBO Order Queue Semantics:** Verifies discrete order queue tracking with non-null, non-empty `order_id`, FIFO priority, priority reset on price modification, and L2 depth projection.
- [ ] **Stream Scope & Strict Ordering Tuple Boundary:** Verifies that deltas from a different stream are rejected and deltas preceding or equal to the snapshot ordering boundary are not double-applied.
- [ ] **Adapter SourceOrderingPolicy Compliance:** Reconstructor obeys adapter-defined ordering without imposing generic sequence contiguity on opaque feeds, marking `STATE_UNORDERABLE` if untrustworthy.
- [ ] **Crossed State Granularity:** Reconstructor distinguishes `CROSSED_TRANSIENT`, `CROSSED_AUCTION_OR_HALT`, and `CROSSED_DUE_TO_INVALID_RECONSTRUCTION`.
- [ ] **Permutation & Codec Invariance:** Permuting snapshot/delta rows or changing compression codec produces identical hashes.
- [ ] **Hash Modification Sensitivity:** Any field modification alters the cryptographic hash.
- [x] **Duplicate Row Identity Rejection:** Duplicate Snapshot/Delta Row Identities raise `IntegrityViolationError`.
- [x] **Dual-Temporal PIT Query Test:** Verifies that historical replay strictly respects both $T_{\text{target}}$ and $T_{\text{knowledge}}$ with zero lookahead.

---

## 12. Evidence Boundary & Production Feed Conformance Scope

> [!IMPORTANT]
> **Scientific Evidence Boundary & Limitation:**
> Gate 3B establishes **deterministic correctness against the ACASH canonical contract and synthetic/reference test vectors**. It does not establish equivalence to every idiosyncratic production exchange/feed behavior across all live market regimes.
>
> 1. **Feed Adapter Normalization Role:**  
>    Specific exchange mechanics (e.g. MBO queue priority preservation during partial cancel vs price modification) are normalized by the upstream Feed Adapter before emitting canonical events. ACASH Core operates strictly on the normalized canonical contract.
> 2. **Production Verification Pathway:**  
>    Production-feed equivalence requires future golden-dataset replay, tick-by-tick comparison with primary exchange PCAP captures, and independent reference validation during Phase 4/5 pipeline hardening.


