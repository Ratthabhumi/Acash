# ACASH — Data & Storage Architecture Specification (Phase 0)

**Document:** `docs/DATA_ARCHITECTURE.md`  
**Version:** 3.2.0 (Micro-Corrections & Storage Semantics Finalized)  
**Date:** 2026-08-27  

---

## 1. Principles of Financial Data & Storage

ACASH enforces a strict architectural separation between **Analytical Research Data** and **Transactional Operational State**:

1. **Analytical / Research Data Layer (`Parquet + DuckDB`):**
   - Partitioned immutable Parquet files provide high-compression columnar storage.
   - Embedded **DuckDB** acts as the high-throughput analytical query engine over Parquet datasets (vector aggregations, window functions, and time-series feature joins).
   - *Rule:* **DuckDB is NOT used as a general-purpose transactional control-plane database.**
2. **Transactional Operational State (`SQLite` in V1):**
   - **SQLite** handles local ACID operational state: order lifecycle states, active position tracking, trade execution logs, and decision ledger audit records.
3. **Future Enterprise Control Plane (`PostgreSQL` — DEFERRED):**
   - **PostgreSQL is DEFERRED** for early phases. It will only be introduced when concurrent multi-process writers, production durability, multi-user access, or distributed control-plane requirements justify it.
   - *Rule:* **Do NOT install PostgreSQL in Phase 1.**

---

## 2. Storage Subsystem Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ACASH STORAGE SYSTEM                            │
├────────────────────────────────────┬───────────────────────────────────┤
│    ANALYTICAL / RESEARCH DATA      │    TRANSACTIONAL OPERATIONAL      │
│  (Read-Heavy, Vectorized Queries)  │       (ACID State, Order Log)     │
├────────────────────────────────────┼───────────────────────────────────┤
│  - Partitioned Parquet files       │  - SQLite Local Database (V1)     │
│  - Embedded DuckDB Query Engine    │    - Order State Machine          │
│  - yfinance Research Adapter       │    - Position Reconciliation      │
│  - Bi-temporal point-in-time index │    - Decision Audit Ledger        │
│                                    │                                   │
│                                    │  - PostgreSQL (DEFERRED Future)   │
└────────────────────────────────────┴───────────────────────────────────┘
```

---

## 3. Evaluation & Role of `yfinance`

- **Role & Definition:** **Research-oriented market and fundamental data adapter with no paid subscription requirement for the intended research use case, subject to source availability, API limitations, and applicable terms.**
- **Boundaries:** Isolated strictly behind `IMarketDataProvider`. Prohibited from use as the production execution or institutional real-time data backbone.

---

## 4. Bi-Temporal Schema & Canonical Types

Datasets in the Parquet analytical layer adhere strictly to the **[docs/DATA_CONTRACT.md](file:///c:/Users/MewMew/Desktop/Co-op/Acash/docs/DATA_CONTRACT.md)** specification:

| Column Name | Physical Parquet Type | Description |
| :--- | :--- | :--- |
| `source_id` | `VARCHAR` | Identifier of data provider (e.g. `binance_public`, `dukascopy`) |
| `symbol` | `VARCHAR` | Unique standard symbol (e.g. `BTC/USDT`, `AAPL`, `EUR/USD`) |
| `timeframe` | `VARCHAR` | Bar resolution (`M1`, `M5`, `M15`, `H1`, `H4`, `D1`) |
| `event_start_utc` | `TIMESTAMP[us, tz=UTC]` | Exact bar opening timestamp in UTC (Microseconds) |
| `event_end_utc` | `TIMESTAMP[us, tz=UTC]` | Exact bar closing timestamp in UTC (Microseconds) |
| `knowledge_time_utc`| `TIMESTAMP[us, tz=UTC]` | System knowledge/ingestion timestamp in UTC (Microseconds) |
| `revision_seq` | `BIGINT` | Deterministic revision sequence scoped to `(source_id, symbol, timeframe, event_start_utc)` |
| `open` | `DECIMAL(38, 18)` | Opening price with exact fixed precision |
| `high` | `DECIMAL(38, 18)` | Highest traded price during bar interval |
| `low` | `DECIMAL(38, 18)` | Lowest traded price during bar interval |
| `close` | `DECIMAL(38, 18)` | Closing traded price during bar interval |
| `volume` | `DECIMAL(38, 18)` | Total base asset volume traded |
| `quote_volume` | `DECIMAL(38, 18)` | Total quote currency volume traded |
| `trade_count` | `BIGINT` | Total discrete trades within the bar (-1 if unavailable) |
| `raw_source_sha256` | `VARCHAR` | SHA-256 hash of original raw ingest batch |

---

## 5. Point-in-Time Revision Query Standard

DuckDB queries against Parquet partitions partition by **Event Observation Key** to select the authoritative revision as of $T_{\text{as\_of}}$:

```sql
WITH eligible AS (
    SELECT *
    FROM read_parquet('data/parquet/{symbol}/{timeframe}/**/*.parquet')
    WHERE knowledge_time_utc <= $as_of_knowledge_time_utc
      AND event_start_utc >= $start_utc
      AND event_end_utc <= $end_utc
)
SELECT *
FROM eligible
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY source_id, symbol, timeframe, event_start_utc
    ORDER BY knowledge_time_utc DESC, revision_seq DESC
) = 1
ORDER BY source_id ASC, event_start_utc ASC;
```

> [!NOTE]
> **Downstream Source Reconciliation:** The P-I-T layer preserves distinct observations from independent data sources without automatic merging or ranking. Source selection/reconciliation is a separate downstream research layer.

---

## 6. Immutable Append-Only Part Storage Layout

To guarantee that subsequent ingestions never overwrite previous data batches:

```
data/parquet/{symbol}/{timeframe}/year={YYYY}/
├── part-000001-{batch_id}.parquet
├── part-000002-{batch_id}.parquet
└── ...
```

- Each ingestion batch is written as a new immutable `.parquet` part file.
- Writing uses a staging file (`.tmp_part_*.parquet`) validated before atomic replacement (`os.replace`) into its unique canonical part name.
- DuckDB scans all historical parts concurrently via glob patterns (`**/*.parquet`).
- **Concurrency Scope:** Phase 2 assumes a single-writer ingestion process. Concurrent writers are out of scope.
