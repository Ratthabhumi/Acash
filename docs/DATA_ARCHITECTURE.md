# ACASH — Data & Storage Architecture Specification (Phase 0)

**Document:** `docs/DATA_ARCHITECTURE.md`  
**Version:** 3.1.0 (Micro-Corrections Applied)  
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

## 4. Bi-Temporal Schema Specification

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `symbol` | `VARCHAR` | Unique standard symbol (e.g. `BTC/USDT`, `AAPL`, `EUR/USD`) |
| `timeframe` | `VARCHAR` | Bar resolution (e.g. `1m`, `5m`, `1h`, `1d`) |
| `event_start_utc` | `TIMESTAMP_NS` | Exact bar opening timestamp in UTC |
| `event_end_utc` | `TIMESTAMP_NS` | Exact bar closing timestamp in UTC |
| `knowledge_time_utc`| `TIMESTAMP_NS` | System timestamp when bar was fully ingested |
| `open` | `DOUBLE` | Opening price |
| `high` | `DOUBLE` | Highest traded price during bar interval |
| `low` | `DOUBLE` | Lowest traded price during bar interval |
| `close` | `DOUBLE` | Closing traded price during bar interval |
| `volume` | `DOUBLE` | Total base asset volume traded |
| `quote_volume` | `DOUBLE` | Total quote currency volume traded |
| `trade_count` | `INTEGER` | Total discrete trades within the bar |
| `source_id` | `VARCHAR` | Identifier of data provider (e.g. `yfinance`, `mt5_demo`) |
| `provenance_hash` | `VARCHAR` | SHA-256 hash of original raw ingest batch |
