# ACASH Data Contract Specification

**Document:** `docs/DATA_CONTRACT.md`  
**Version:** 1.4.0 (Global Revision Uniqueness, Deterministic Canonical Hash & Multi-Part Testing Locked)  
**Status:** Canonical Source of Truth for ACASH Market Datasets  
**Phase:** Phase 2 Data Ingestion & Integrity Engine  

---

## 1. Core Principles & Philosophy

The ACASH Data Subsystem operates on one fundamental principle:
$$\text{Raw Source} \xrightarrow{\text{raw SHA-256}} \text{Per-Stream Validation} \xrightarrow{\text{Normalize \& Sort}} \text{Canonical Batch} \xrightarrow{\text{canonical batch SHA-256}} \text{Immutable Part File} \to \text{P-I-T Query}$$

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
| `open` | `decimal128(38, 18)` | Opening price within explicit precision/scale limits |
| `high` | `decimal128(38, 18)` | Highest traded price during the bar interval |
| `low` | `decimal128(38, 18)` | Lowest traded price during the bar interval |
| `close` | `decimal128(38, 18)` | Closing traded price during the bar interval |
| `volume` | `decimal128(38, 18)` | Total base volume traded |
| `quote_volume` | `decimal128(38, 18)` | Total quote volume traded |
| `trade_count` | `int64` | Total discrete trade count (-1 if unavailable from source) |

### 2.1 Numeric Precision Policy (`Decimal128(38, 18)`):
- `Decimal128(38, 18)` is the canonical Phase 2 representation within explicit precision/scale limits (up to 20 integer digits and 18 decimal scale places).
- Values outside these bounds or attempting non-finite representation are rejected with `DomainValidationError`.
- Statistical/ML engines explicitly convert to floating-point (`float64`) when performing vectorized analytics.

### 2.2 Timestamp Precision Policy (`timestamp[us, tz=UTC]`):
- Canonical bar timestamps use UTC microsecond precision (`timestamp[us, tz=UTC]`) matching DuckDB native `TIMESTAMPTZ` engine constraints to eliminate precision loss.

---

## 3. Storage Layout: Immutable Append-Only Part Files

Parquet files are organized in partitioned directories as **immutable append-only parts**:

```
data/parquet/{symbol}/{timeframe}/year={YYYY}/
├── part-000001-{batch_id}.parquet
├── part-000002-{batch_id}.parquet
└── ...
```

### Storage Invariants:
1. **Append-Only Parts:** Each successful batch ingestion writes a new, uniquely identified immutable part file.
2. **Never Overwrite Existing Parts:** Normal ingestion never overwrites, truncates, or replaces existing part files.
3. **Partition Scanning:** DuckDB reads the full historical dataset across all parts using parquet file globs:
   `read_parquet('data/parquet/{symbol}/{timeframe}/**/*.parquet')`
4. **Atomic Staging Pattern:**
   $$\text{Write Temp (.tmp\_part\_*.parquet)} \to \text{Flush/Close} \to \text{Validate Staged File} \to \text{os.replace into Canonical Part Path}$$
   Under supported filesystem semantics, readers will not observe the final path as a partially written staging file, and a failed write leaves existing parts completely intact.

---

## 4. Bi-Temporal & Point-in-Time Revision Semantics

ACASH explicitly decouples **Event Time** ($t_{\text{event}}$) from **Knowledge Time** ($t_{\text{knowledge}}$).

### 4.1 Temporal Ordering Invariants:
1. **Intra-Bar Interval:** $t_{\text{event\_start}} < t_{\text{event\_end}}$
2. **Knowledge Invariant:** $t_{\text{knowledge}} \ge t_{\text{event\_end}}$ (No observation can be known before its bar interval closes)
3. **Stream-Isolated Monotonicity:** For sequential bars $i$ and $i+1$ within the **same stream** `(source_id, symbol, timeframe)`, $t_{\text{event\_start}, i+1} \ge t_{\text{event\_end}, i}$.

### 4.2 Global Observation Identity & Deterministic Uniqueness:
- A single observation is uniquely identified by:
  $$\text{Observation Identity} = (\text{source\_id}, \text{symbol}, \text{timeframe}, \text{event\_start\_utc}, \text{knowledge\_time\_utc}, \text{revision\_seq})$$
- `revision_seq` is a deterministic, strictly increasing integer scoped to $(\text{source\_id}, \text{symbol}, \text{timeframe}, \text{event\_start\_utc})$.
- **Global Uniqueness Enforcement:** An exact observation identity must be globally unique across the entire canonical dataset. If an incoming record matches an identity already present in:
  1. The current incoming batch (intra-batch collision), OR
  2. Any existing canonical Parquet part in the partition (existing-dataset collision)
  it is rejected as a **fatal deterministic ingestion error (`ERROR / INVALID`)**.
- **Zero Premature Source Merging:** Multiple data sources observing the same symbol and timestamp remain distinct independent observations.

### 4.3 Source-Aware Point-in-Time (P-I-T) Query Standard:
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

## 5. Provenance Hashes & Deterministic Canonical Ordering

Provenance is tracked at the batch and source level without circular row-level self-referencing:
1. **Raw Source Hash (`raw_source_sha256`):**
   - SHA-256 computed over the exact raw input payload bytes prior to parsing.
2. **Canonical Batch Hash (`canonical_batch_sha256`):**
   - Computed over the deterministic binary serialization of the normalized batch columns:
     `[source_id, symbol, timeframe, event_start_utc, event_end_utc, knowledge_time_utc, revision_seq, open, high, low, close, volume, quote_volume, trade_count]`
   - **Deterministic Canonical Ordering:** Rows must be sorted by `(source_id, symbol, timeframe, event_start_utc, knowledge_time_utc, revision_seq)` prior to binary serialization, guaranteeing that `canonical_batch_sha256` is completely invariant to incidental input row ordering.
   - Stored in the Provenance Ledger (`data/provenance_ledger.jsonl`) alongside the resulting Parquet part file path.

---

## 6. Per-Stream Integrity & Anomaly Boundaries

Integrity validation operates strictly per independent data stream: `(source_id, symbol, timeframe)`.

```
                              PER-STREAM VALIDATION ENGINE
                                           │
                 ┌─────────────────────────┴─────────────────────────┐
                 ▼                                                   ▼
         ERROR / INVALID                                     WARNING / ANOMALY
   (Rejects Ingest / Fatal Issue)                      (Preserves Observation & Flags)
   - Impossible Prices (<= 0)                          - Extreme Price Return Spike (|r| > threshold)
   - Negative Volume (< 0)                             - Volume Anomaly (> 10x rolling median)
   - OHLC Geometry Violations                          - Unexpected Cadence Gap
   - Non-finite (NaN / Inf)                            - High-Low Spread Expansion
   - Invalid / Future Timestamps                       - Missing Secondary Fields (quote_vol, trade_count)
   - Duplicate Global Revision Identities              - Statistically unusual observations
   - Schema / Type / Precision Boundary Mismatch
```

> [!IMPORTANT]
> **Deterministic Rule Test Coverage:** Every explicitly defined integrity rule must have deterministic positive and negative test coverage.

---

## 7. Configurable Session Profiles

Session calendars are configurable profiles per data stream:

| Profile Name | Default Cadence Assumptions | Description / Policy |
| :--- | :--- | :--- |
| **`CRYPTO_24_7`** | Continuous 24/7 | Every missing bar interval in the stream is flagged as an **Unexpected Data Gap**. |
| **`FX_24_5_DEFAULT`** | Sunday 21:00 UTC $\to$ Friday 21:00 UTC | Weekend intervals (Fri 21:00 $\to$ Sun 21:00) are **Expected Closed-Market Gaps**. Weekday gaps are flagged. |
| **`EQUITY_SESSION_DEFAULT`** | Exchange Regular Hours (RTH) | Off-hours, weekends, and holidays are **Expected Gaps**. In-session missing bars are flagged. |
| **`CUSTOM`** | Explicit Active Windows Table | Stream-specific operating windows and maintenance schedules. |

---

## 8. Provenance Ledger & Audit Semantics

Every ingestion run records an entry in the **append-only application audit log** (`data/provenance_ledger.jsonl`):

```json
{
  "provenance_id": "prov_20260827_001",
  "source_id": "binance_public",
  "source_uri_or_path": "data/raw/btc_usdt_1m.csv",
  "part_file_path": "data/parquet/BTC-USDT/M1/year=2026/part-000001-a1b2c3d4.parquet",
  "ingest_time_utc": "2026-08-27T21:30:00.000000Z",
  "raw_source_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "canonical_batch_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
  "schema_version": "1.4.0",
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

> [!NOTE]
> **Audit Log Security Boundaries:** The JSONL provenance ledger is an append-only application audit log, not a cryptographically tamper-evident or chained ledger. The embedded SHA-256 hashes provide dataset integrity verification. Cryptographic hash chaining or WORM storage may be evaluated in future enterprise security phases.
