# ACASH Data Contract Specification

**Document:** `docs/DATA_CONTRACT.md`  
**Version:** 1.0.0  
**Status:** Canonical Source of Truth for ACASH Market Datasets  
**Phase:** Phase 2 Data Ingestion & Integrity Engine  

---

## 1. Core Principles & Philosophy

The ACASH Data Subsystem operates on one fundamental principle:
$$\text{Source} \to \text{Validation} \to \text{Bi-Temporal Normalization} \to \text{Provenance Hashing} \to \text{Canonical Storage} \to \text{P-I-T Query}$$

> [!CRITICAL]
> **Zero Historical Distortion:** The data validator's objective is to certify dataset trustworthiness, **NOT to make historical data look artificially smooth or clean**. Anomalies are flagged, never silently deleted or mutated.

---

## 2. Canonical Physical Schema & Data Types

Datasets stored in the ACASH analytical layer adhere strictly to the following PyArrow / Parquet schema:

| Column Name | Arrow Data Type | Canonical Description |
| :--- | :--- | :--- |
| `symbol` | `string` | Normalized instrument identifier (e.g. `BTC/USDT`, `EUR/USD`, `AAPL`) |
| `timeframe` | `string` | Bar resolution string (`M1`, `M5`, `M15`, `H1`, `H4`, `D1`) |
| `event_start_utc` | `timestamp[us, tz=UTC]` | Exact bar opening timestamp in UTC (Microsecond precision) |
| `event_end_utc` | `timestamp[us, tz=UTC]` | Exact bar closing timestamp in UTC (Microsecond precision) |
| `knowledge_time_utc`| `timestamp[us, tz=UTC]` | System knowledge/ingestion timestamp in UTC (Microsecond precision) |
| `revision_seq` | `int64` | Monotonically increasing revision number for same event observation (starts at 1) |
| `open` | `decimal128(28, 10)` | Opening price with exact fixed-point precision |
| `high` | `decimal128(28, 10)` | Highest traded price during the bar interval |
| `low` | `decimal128(28, 10)` | Lowest traded price during the bar interval |
| `close` | `decimal128(28, 10)` | Closing traded price during the bar interval |
| `volume` | `decimal128(28, 10)` | Total base volume traded |
| `quote_volume` | `decimal128(28, 10)` | Total quote volume traded |
| `trade_count` | `int64` | Total discrete trade count (-1 if unavailable from source) |
| `source_id` | `string` | Provenance source identifier (e.g. `binance_public`, `dukascopy`, `synthetic_mock`) |
| `provenance_hash` | `string` | SHA-256 hash hex digest of the raw source ingestion payload |

> [!NOTE]
> **Timestamp Precision Selection:** UTC Microseconds (`timestamp[us, tz=UTC]`) is the canonical Phase 2 bar timestamp representation to match DuckDB native `TIMESTAMPTZ` engine constraints and prevent nanosecond truncation / loss.

> [!NOTE]
> **Canonical Numeric Representation:** Financial numbers are stored canonically as `Decimal128(28, 10)`. Downstream statistical and machine learning engines must explicitly convert to floating point when performing vectorized arithmetic.

---

## 3. Bi-Temporal & Point-in-Time Revision Semantics

ACASH explicitly decouples **Event Time** ($t_{\text{event}}$) from **Knowledge Time** ($t_{\text{knowledge}}$).

### 3.1 Temporal Ordering Invariants:
1. **Intra-Bar Interval:** $t_{\text{event\_start}} < t_{\text{event\_end}}$
2. **Knowledge Invariant:** $t_{\text{knowledge}} \ge t_{\text{event\_end}}$ (No observation can be known before its bar interval closes)
3. **Sequential Monotonicity:** For sequential bars $i$ and $i+1$, $t_{\text{event\_start}, i+1} \ge t_{\text{event\_end}, i}$

### 3.2 Authoritative Revision Semantics:
When market data is restated, revised, or late-delivered:
- Multiple records may exist for the same `(symbol, timeframe, event_start_utc)` with different `knowledge_time_utc` and `revision_seq`.
- **Uniqueness Invariant:** `(symbol, timeframe, event_start_utc, knowledge_time_utc, revision_seq)` is strictly unique.
- **As-Of Invariant:** At any query reference timestamp $T_{\text{as\_of}}$, there is **at most one authoritative revision** for each event observation.

### 3.3 Point-in-Time (P-I-T) Query Specification:
DuckDB queries against the canonical Parquet dataset must execute deduplication over historical revisions:

```sql
WITH eligible_revisions AS (
    SELECT *
    FROM read_parquet('data/parquet/{symbol}/{timeframe}/**/*.parquet')
    WHERE knowledge_time_utc <= $as_of_knowledge_time_utc
      AND event_start_utc >= $start_utc
      AND event_end_utc <= $end_utc
)
SELECT *
FROM eligible_revisions
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY symbol, timeframe, event_start_utc
    ORDER BY knowledge_time_utc DESC, revision_seq DESC
) = 1
ORDER BY event_start_utc ASC;
```

---

## 4. Integrity & Anomaly Boundaries

The validator enforces a strict separation between **fatal data corruption** and **empirical market anomalies**:

```
                              VALIDATION ENGINE
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
         ERROR / INVALID                           WARNING / ANOMALY
   (Rejects Ingest / Fatal Issue)            (Preserves Observation & Flags)
   - Impossible Prices (<= 0)                - Extreme Price Return Spike (|r| > threshold)
   - Negative Volume (< 0)                   - Volume Anomaly (> 10x rolling median)
   - OHLC Geometry Violations                - Unexpected Cadence Gap
   - Non-finite (NaN / Inf)                  - High-Low Spread Expansion
   - Invalid / Future Timestamps             - Missing Secondary Fields (quote_vol, trade_count)
   - Duplicate Authoritative Revisions
   - Schema / Type Mismatch
```

> [!WARNING]
> **No Silent Cleaning:** Anomalous bars are flagged in `ValidationReport.warnings` and stored with full integrity. They must **never** be silently removed or altered to artificially inflate backtest performance.

---

## 5. Market Session & Missingness Policy

Cadence gap evaluation accounts for the underlying market operating schedule:

| Market Regime / Policy | Expected Cadence | Gap Evaluation Semantics |
| :--- | :--- | :--- |
| **`CRYPTO_24_7`** | Continuous 24/7 | Any missing bar interval is flagged as an **Unexpected Data Gap**. |
| **`FX_24_5`** | Sunday 21:00 UTC $\to$ Friday 21:00 UTC | Weekend intervals (Fri 21:00 $\to$ Sun 21:00) are **Expected Closed-Market Gaps**. Weekday gaps are flagged as **Unexpected Data Gaps**. |
| **`EQUITY_SESSION`** | Exchange Regular Trading Hours (RTH) | Off-hours, weekends, and declared market holidays are **Expected Gaps**. In-session missing bars are flagged as **Unexpected Data Gaps**. |

---

## 6. Provenance & Cryptographic Lineage

Every ingestion batch generates an immutable audit record:
1. **Canonical Payload Hash:** SHA-256 computed over normalized input batch bytes.
2. **Metadata Envelope:**
   - `source_id`: Origin identifier.
   - `ingested_at_utc`: System UTC timestamp of ingestion.
   - `symbol`, `timeframe`, `row_count`, `min_event_start_utc`, `max_event_end_utc`.
   - `provenance_hash`: SHA-256 hex digest.
   - `validation_report`: Summary of all error checks and anomaly flags.
3. **Storage Ledger:** Stored in `data/provenance_ledger.jsonl`.
