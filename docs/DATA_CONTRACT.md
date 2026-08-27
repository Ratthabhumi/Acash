# ACASH Data Contract Specification

**Document:** `docs/DATA_CONTRACT.md`  
**Version:** 1.2.0 (Source-Aware PIT, Hash Scope & Precision Finalized)  
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
| `open` | `decimal128(38, 18)` | Opening price with exact fixed-point precision |
| `high` | `decimal128(38, 18)` | Highest traded price during the bar interval |
| `low` | `decimal128(38, 18)` | Lowest traded price during the bar interval |
| `close` | `decimal128(38, 18)` | Closing traded price during the bar interval |
| `volume` | `decimal128(38, 18)` | Total base volume traded |
| `quote_volume` | `decimal128(38, 18)` | Total quote volume traded |
| `trade_count` | `int64` | Total discrete trade count (-1 if unavailable from source) |
| `raw_source_sha256` | `string` | SHA-256 hex digest of the raw ingest source payload |

### 2.1 Numeric Precision & Scale Decision (`Decimal128(38, 18)`):
- **Scale (18 decimal places):** Supports extreme micro-pricing and base asset quantities down to $10^{-18}$ (e.g., crypto satoshi/wei units, sub-pip FX micro-spreads, fractional equities).
- **Precision (38 total digits):** Provides 20 digits of integer headroom up to $10^{20}$ (e.g., hundreds of trillions in quote volume or market cap).
- **Engine Compatibility:** Natively supported with exact precision across DuckDB (`DECIMAL(38, 18)`), PyArrow (`pa.decimal128(38, 18)`), and Python `decimal.Decimal`.
- **Downstream Analytics:** Machine learning and statistical engines explicitly cast to IEEE 754 floating-point (`float64`) when performing vectorized matrix math.

### 2.2 Timestamp Precision Decision (`timestamp[us, tz=UTC]`):
- Canonical bar timestamps use UTC microsecond precision (`timestamp[us, tz=UTC]`).
- DuckDB's native `TIMESTAMPTZ` operates at microsecond precision; storing microsecond timestamps avoids nanosecond-to-microsecond truncation warnings and precision artifacts when querying Parquet partitions.

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
- **Zero Premature Source Merging:** Multiple data sources observing the same symbol and timestamp remain distinct independent observations. Phase 2 does NOT merge or prioritize sources without an explicit reconciliation layer.

### 3.3 Source-Aware Point-in-Time (P-I-T) Query Standard:
DuckDB queries against the canonical Parquet dataset execute revision deduplication partitioned by `source_id`:

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
    PARTITION BY source_id, symbol, timeframe, event_start_utc
    ORDER BY knowledge_time_utc DESC, revision_seq DESC
) = 1
ORDER BY source_id ASC, event_start_utc ASC;
```

---

## 4. Provenance Hashing & Non-Circular Hash Scope

To eliminate circular self-referencing in canonical dataset hashing:
1. **Raw Source Hash (`raw_source_sha256`):**
   - SHA-256 computed over the exact raw input payload bytes / files prior to parsing.
2. **Canonical Dataset Hash (`canonical_dataset_sha256`):**
   - Computed strictly over the deterministic binary serialization of the **canonical data columns**:
     `[source_id, symbol, timeframe, event_start_utc, event_end_utc, knowledge_time_utc, revision_seq, open, high, low, close, volume, quote_volume, trade_count]`
   - The digest fields themselves are **strictly excluded** from the byte payload being hashed.
   - The resulting `canonical_dataset_sha256` is recorded in the immutable Provenance Ledger (`data/provenance_ledger.jsonl`) and Parquet metadata key-value store.

---

## 5. Integrity & Anomaly Boundaries

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
> **Deterministic Rule Test Coverage:** Every explicitly defined integrity rule must have deterministic positive and negative test coverage.

---

## 6. Session Policies as Configurable Profiles

Session calendars are configurable profiles rather than universal hard-coded truths:

| Profile Name | Default Cadence Assumptions | Description / Policy |
| :--- | :--- | :--- |
| **`CRYPTO_24_7`** | Continuous 24/7 | Every missing bar interval is flagged as an **Unexpected Data Gap**. |
| **`FX_24_5_DEFAULT`** | Sunday 21:00 UTC $\to$ Friday 21:00 UTC | Weekend intervals (Fri 21:00 $\to$ Sun 21:00) are **Expected Closed-Market Gaps**. Weekday gaps are flagged. |
| **`EQUITY_SESSION_DEFAULT`** | Exchange Regular Hours (RTH) | Off-hours, weekends, and holidays are **Expected Gaps**. In-session missing bars are flagged. |
| **`CUSTOM`** | Explicit Active Windows Table | User/source-defined operating windows and maintenance schedules. |

---

## 7. Atomic Parquet Write Semantics

To guarantee that readers under supported filesystem semantics never observe partially written staging files:
1. **Stage to Temp Path:** Write Parquet output to a hidden staging path (`.tmp_{uuid}_{partition}.parquet`).
2. **Flush & Sync:** Complete all PyArrow Parquet writer buffers and flush to disk.
3. **Verify Integrity:** Run row count and schema validation against the temporary staging file.
4. **Atomic Replace:** Atomically move/replace the staged file into its canonical partition location (`os.replace`).
5. **Failure Safety:** Any failure during staging immediately deletes the temporary file without touching the existing canonical file.

---

## 8. Extended Provenance Ledger Record

Every ingestion run records an immutable audit entry in `data/provenance_ledger.jsonl`:

```json
{
  "provenance_id": "prov_20260827_001",
  "source_id": "binance_public",
  "source_uri_or_path": "data/raw/btc_usdt_1m.csv",
  "ingest_time_utc": "2026-08-27T21:30:00.000000Z",
  "raw_source_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "canonical_dataset_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
  "schema_version": "1.2.0",
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
