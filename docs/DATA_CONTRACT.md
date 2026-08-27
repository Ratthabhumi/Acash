# ACASH Data Contract Specification

**Document:** `docs/DATA_CONTRACT.md`  
**Version:** 1.1.0 (Integrity & Provenance Locked)  
**Status:** Canonical Source of Truth for ACASH Market Datasets  
**Phase:** Phase 2 Data Ingestion & Integrity Engine  

---

## 1. Core Principles & Philosophy

The ACASH Data Subsystem operates on one fundamental principle:
$$\text{Raw Source} \xrightarrow{\text{raw SHA-256}} \text{Validation} \xrightarrow{\text{Normalize}} \text{Canonical Dataset} \xrightarrow{\text{canonical SHA-256}} \text{Atomic Parquet Write} \to \text{P-I-T Query}$$

> [!CRITICAL]
> **Zero Historical Distortion:** The data validator's objective is to certify dataset trustworthiness, **NOT to make historical data look artificially smooth or clean**. Anomalies are flagged, never silently deleted or mutated.

---

## 2. Canonical Physical Schema & Data Types

Datasets stored in the ACASH analytical layer adhere strictly to the following PyArrow / Parquet schema:

| Column Name | Arrow Data Type | Canonical Description |
| :--- | :--- | :--- |
| `source_id` | `string` | Provenance source identifier (e.g. `binance_public`, `dukascopy`, `synthetic_mock`) |
| `symbol` | `string` | Normalized instrument identifier (e.g. `BTC/USDT`, `EUR/USD`, `AAPL`) |
| `timeframe` | `string` | Bar resolution string (`M1`, `M5`, `M15`, `H1`, `H4`, `D1`) |
| `event_start_utc` | `timestamp[us, tz=UTC]` | Exact bar opening timestamp in UTC (Microsecond precision) |
| `event_end_utc` | `timestamp[us, tz=UTC]` | Exact bar closing timestamp in UTC (Microsecond precision) |
| `knowledge_time_utc`| `timestamp[us, tz=UTC]` | System knowledge/ingestion timestamp in UTC (Microsecond precision) |
| `revision_seq` | `int64` | Deterministic revision sequence scoped to `(source_id, symbol, timeframe, event_start_utc)` |
| `open` | `decimal128(28, 10)` | Opening price with exact fixed-point precision |
| `high` | `decimal128(28, 10)` | Highest traded price during the bar interval |
| `low` | `decimal128(28, 10)` | Lowest traded price during the bar interval |
| `close` | `decimal128(28, 10)` | Closing traded price during the bar interval |
| `volume` | `decimal128(28, 10)` | Total base volume traded |
| `quote_volume` | `decimal128(28, 10)` | Total quote volume traded |
| `trade_count` | `int64` | Total discrete trade count (-1 if unavailable from source) |
| `raw_source_sha256` | `string` | SHA-256 hex digest of the raw ingest source payload |
| `canonical_dataset_sha256` | `string` | SHA-256 hex digest of the normalized canonical dataset partition |

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

### 3.2 Provenance-Aware Revision Identity:
- A single observation is uniquely identified by:
  $$\text{Observation Identity} = (\text{source\_id}, \text{symbol}, \text{timeframe}, \text{event\_start\_utc}, \text{knowledge\_time\_utc}, \text{revision\_seq})$$
- `revision_seq` is a deterministic, strictly increasing integer scoped to $(\text{source\_id}, \text{symbol}, \text{timeframe}, \text{event\_start\_utc})$.
- **As-Of Invariant:** At any query reference timestamp $T_{\text{as\_of}}$, there is **at most one authoritative revision** for each event observation.

### 3.3 Point-in-Time (P-I-T) Query Specification:
DuckDB queries against the canonical Parquet dataset execute revision deduplication:

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
    ORDER BY knowledge_time_utc DESC, revision_seq DESC, canonical_dataset_sha256 DESC
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
   - Duplicate Authoritative Revisions       - Statistically unusual observations
   - Schema / Type Mismatch
```

> [!IMPORTANT]
> **Deterministic Rule Testing:** Every explicitly defined integrity rule must have deterministic positive and negative test coverage.

---

## 5. Session Policies as Configurable Profiles

Session calendars are configurable profiles rather than universal hard-coded truths:

| Profile Name | Default Cadence Assumptions | Description / Policy |
| :--- | :--- | :--- |
| **`CRYPTO_24_7`** | Continuous 24/7 | Every missing bar interval is flagged as an **Unexpected Data Gap**. |
| **`FX_24_5_DEFAULT`** | Sunday 21:00 UTC $\to$ Friday 21:00 UTC | Weekend intervals (Fri 21:00 $\to$ Sun 21:00) are **Expected Closed-Market Gaps**. Weekday gaps are flagged. |
| **`EQUITY_SESSION_DEFAULT`** | Exchange Regular Hours (RTH) | Off-hours, weekends, and holidays are **Expected Gaps**. In-session missing bars are flagged. |
| **`CUSTOM`** | Explicit Active Windows Table | User/source-defined operating windows and maintenance schedules. |

---

## 6. Atomic Parquet Write Semantics

To guarantee that readers never observe partially written or corrupt final files:
1. **Stage to Temp Path:** Write Parquet output to a hidden staging path (`.tmp_{uuid}_{partition}.parquet`).
2. **Flush & Sync:** Complete all PyArrow Parquet writer buffers and fsync to disk.
3. **Verify Integrity:** Run checksum and row count validation against the temporary file.
4. **Atomic Rename/Replace:** Atomically move/replace the staged file into its canonical partition location (`os.replace` on POSIX/Windows).

---

## 7. Extended Provenance Ledger Record

Every ingestion run records an immutable audit entry in `data/provenance_ledger.jsonl`:

```json
{
  "provenance_id": "prov_20260827_001",
  "source_id": "binance_public",
  "source_uri_or_path": "s3://raw-market-data/btc_usdt_1m.csv",
  "ingest_time_utc": "2026-08-27T21:30:00.000000Z",
  "raw_source_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "canonical_dataset_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
  "schema_version": "1.1.0",
  "transform_version": "normalize_ohlcv_v1",
  "symbol": "BTC/USDT",
  "timeframe": "M1",
  "row_count": 1440,
  "min_event_time_utc": "2026-08-27T00:00:00.000000Z",
  "max_event_time_utc": "2026-08-27T23:59:00.000000Z",
  "validation_status": "VALID_WITH_WARNINGS",
  "error_count": 0,
  "warning_count": 2
}
```
