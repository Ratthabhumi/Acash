# ACASH Data Contract Specification

**Document:** `docs/DATA_CONTRACT.md`  
**Version:** 1.12.0 (Canonical Content Fingerprint Scope & First-Acceptance Tie-Breaker Finalized)  
**Status:** Canonical Source of Truth for ACASH Market Datasets  
**Phase:** Phase 2 Data Ingestion & Integrity Engine  

---

## 1. Core Principles & Philosophy

The ACASH Data Subsystem operates on one fundamental principle:
$$\text{Raw Source} \xrightarrow{\text{raw SHA-256}} \text{Per-Stream Validation} \xrightarrow{\text{Normalize \& Sort}} \text{Canonical Logical Batch} \xrightarrow{\text{logical batch SHA-256}} \text{Immutable Part File} \to \text{P-I-T Query}$$

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
| `event_end_utc` | `timestamp[us, tz=UTC]` | Exact bar closing timestamp in UTC (Microsecond precision, immutable per event) |
| `knowledge_time_utc`| `timestamp[us, tz=UTC]` | System knowledge/ingestion timestamp in UTC (Microsecond precision) |
| `revision_seq` | `int64` | Immutable revision sequence unique per `Event Observation Key` ($\ge 1$) |
| `open` | `decimal128(38, 18)` | Opening price within explicit precision/scale limits |
| `high` | `decimal128(38, 18)` | Highest traded price during the bar interval |
| `low` | `decimal128(38, 18)` | Lowest traded price during the bar interval |
| `close` | `decimal128(38, 18)` | Closing traded price during the bar interval |
| `volume` | `decimal128(38, 18)` | Total base volume traded |
| `quote_volume` | `decimal128(38, 18)` | Total quote volume traded |
| `trade_count` | `int64` | Total discrete trade count (-1 if unavailable from source) |

### 2.1 Numeric Precision Policy (`Decimal128(38, 18)`):
- `Decimal128(38, 18)` is the canonical Phase 2 representation supporting values requiring up to 18 fractional decimal places within the defined total precision and scale limits (e.g., fractional pricing, Satoshi = $10^{-8}$ BTC, Wei = $10^{-18}$ ETH).
- Values outside these bounds or attempting non-finite representation are rejected with `DomainValidationError`.
- Statistical/ML engines explicitly convert to floating-point (`float64`) when performing vectorized analytics.

### 2.2 Timestamp Precision Policy (`timestamp[us, tz=UTC]`):
- Canonical bar timestamps use UTC microsecond precision (`timestamp[us, tz=UTC]`) matching DuckDB native `TIMESTAMPTZ` engine constraints to eliminate precision loss.

---

## 3. Storage Layout, Global Batch Idempotency & Concurrency Boundaries

Parquet files are organized in partitioned directories as **immutable append-only parts**:

```
data/parquet/{symbol}/{timeframe}/year={YYYY}/
├── part-000001-{batch_id}.parquet
├── part-000002-{batch_id}.parquet
└── ...
```

### Storage & Ingestion Invariants:
1. **Append-Only Parts:** Each successful batch ingestion writes a new, uniquely identified immutable part file.
2. **Never Overwrite Existing Parts:** Normal ingestion never overwrites, truncates, or replaces existing part files.
3. **Partition Scanning:** DuckDB reads the full historical dataset across all parts using parquet file globs:
   `read_parquet('data/parquet/{symbol}/{timeframe}/**/*.parquet')`
4. **Atomic Staging Pattern:**
   $$\text{Write Temp (.tmp\_part\_*.parquet)} \to \text{Flush/Close} \to \text{Validate Staged File} \to \text{os.replace into Canonical Part Path}$$
   Under supported filesystem semantics, readers will not observe the final path as a partially written staging file, and a failed write leaves existing parts completely intact.
5. **Global Batch Idempotency Contract:**
   - `batch_id` is a **globally unique immutable ingestion identity across the entire ACASH canonical dataset**.
   - Retrying the exact same `batch_id` with identical canonical content is safely idempotent (no-op; returns the existing part path without creating duplicate parts).
   - Ingesting an existing `batch_id` with differing canonical content is rejected with a fatal `BatchCollisionError`.
   - `batch_id` is recorded in the provenance audit record.
6. **Single-Writer Concurrency Scope:** Phase 2 ingestion assumes a **single-writer ingestion process**. Concurrent/multi-process writers are explicitly out of scope for Phase 2. Global duplicate validation operates against the existing partition parts sequentially before writing.

---

## 4. Bi-Temporal & Point-in-Time Revision Semantics

ACASH explicitly decouples **Event Time** ($t_{\text{event}}$) from **Knowledge Time** ($t_{\text{knowledge}}$).

### 4.1 Temporal Ordering Invariants:
1. **Intra-Bar Interval:** $t_{\text{event\_start}} < t_{\text{event\_end}}$
2. **Knowledge Invariant:** $t_{\text{knowledge}} \ge t_{\text{event\_end}}$ (No observation can be known before its bar interval closes)
3. **Event End Consistency Across Revisions:** For every `Event Observation Key = (source_id, symbol, timeframe, event_start_utc)`, all historical revisions must have the **exact same `event_end_utc`**. If two revisions for the same Event Observation Key have differing `event_end_utc`, the ingestion is rejected as a **fatal error (`ERROR / INVALID`)**.
4. **Distinct Event Monotonicity:** For distinct event observation keys $j$ and $j+1$ within the **same stream** `(source_id, symbol, timeframe)`, $t_{\text{event\_start}, j+1} \ge t_{\text{event\_end}, j}$.
5. **Revision Ordering Within Event:** Multiple valid revisions sharing the **same** `event_start_utc` and `event_end_utc` are permitted. Revisions within an event are ordered and validated by strictly distinct `(knowledge_time_utc, revision_seq)`. They do **not** violate event-time monotonicity.

### 4.2 Event Observation Key, Revision Identity & `revision_seq` Contract:
ACASH makes a strict distinction between the **event being observed** and its **specific historical revision**:

$$\text{Event Observation Key} = (\text{source\_id}, \text{symbol}, \text{timeframe}, \text{event\_start\_utc})$$

$$\text{Revision Identity} = (\text{Event Observation Key}, \text{knowledge\_time\_utc}, \text{revision\_seq})$$

#### `revision_seq` Contract & First-Acceptance Scope:
- `revision_seq` is an **immutable persistence sequence value assigned once when a revision is first accepted into the canonical dataset**. It is a stable identifier, **NOT a globally recomputed chronological rank**.
- **Properties:**
  - Integer $\ge 1$.
  - Strictly unique within `Event Observation Key` (each sequence number occurs at most once per event).
  - **Immutable After Persistence:** Persisted revisions are **never renumbered**, re-ranked, or rewritten.
  - Never reused for another revision of the same Event Observation Key.
- **Assignment & Validation Rules:**
  1. **Source-Provided Sequence:** Validated for uniqueness ($\ge 1$, no duplicates within event) and preserved as-is.
  2. **ACASH Deterministic Initial Assignment (First Acceptance):**
     - Revisions are assigned the next available sequence number (`seq = max(existing_seq) + 1` or starting at 1 for new events).
     - **Same Knowledge Time Intra-Batch Tie-Breaker:** `canonical_content_fingerprint` is used as a deterministic tie-breaker **ONLY among unpersisted revisions being newly accepted together in the SAME acceptance operation/batch** that share the same `knowledge_time_utc`. It is **never** used to re-rank or renumber previously persisted revisions.
     - **Duplicate Content Rejection:** If multiple revisions within the batch or existing dataset share the same `knowledge_time_utc` and have *identical* canonical content (same fingerprint), they are rejected as duplicate revision content (`ERROR / INVALID`).
  3. **Later Arriving Revisions & Historical Backfills:**
     - If a new revision arrives in a later batch (whether with older, same, or newer `knowledge_time_utc`), existing persisted revisions are **never renumbered**.
     - The newly accepted revision simply receives the next available sequence number (`seq = max(existing_seq) + 1`), regardless of whether its content fingerprint is lower or higher than previously persisted records.
  4. **P-I-T Query Ordering Standard:** `knowledge_time_utc` is the **PRIMARY** temporal ordering field (`ORDER BY knowledge_time_utc DESC, revision_seq DESC`); `revision_seq` acts strictly as the stable deterministic tie-breaker for equal knowledge times.

#### Global Revision Identity Uniqueness:
- An exact `Revision Identity` must be globally unique across the canonical dataset. If an incoming record matches a `Revision Identity` already present in the incoming batch or existing canonical Parquet parts, it is rejected as a **fatal deterministic ingestion error (`ERROR / INVALID`)**.
- **Zero Premature Source Merging:** Multiple data sources observing the same symbol and timestamp remain distinct independent observations. Phase 2 PIT queries return source-specific authoritative records and do NOT merge, rank, or reconcile sources. (Source selection and reconciliation is a separate future research layer).

### 4.3 Source-Aware Point-in-Time (P-I-T) Query Standard:
DuckDB queries partition by `Event Observation Key` to select the authoritative revision as of $T_{\text{as\_of}}$ across all immutable parts:

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

## 5. Logical Provenance Hashing & Determinism

Provenance is tracked at the batch and source level without circular row-level self-referencing:
1. **Raw Source Hash (`raw_source_sha256`):**
   - SHA-256 computed over the exact raw input payload bytes prior to parsing.
2. **Canonical Batch Hash (`canonical_batch_sha256`):**
   - SHA-256 computed over the **deterministic logical representation** of the normalized batch columns, **NOT raw Parquet file bytes**:
     `[source_id, symbol, timeframe, event_start_utc, event_end_utc, knowledge_time_utc, revision_seq, open, high, low, close, volume, quote_volume, trade_count]`
   - **Deterministic Logical Normalization:**
     1. Exclude all digest and file metadata fields.
     2. Encode numeric decimals and UTC timestamps in canonical fixed-width binary representations.
     3. Sort rows strictly by `Revision Identity` (`source_id, symbol, timeframe, event_start_utc, knowledge_time_utc, revision_seq`).
   - **File-Layout Invariance:** The logical hash is completely invariant to Parquet compression codecs, row-group boundaries, file metadata, or physical storage chunking.
   - **Content Verification:** Modified canonical data content is detected by recomputing the logical canonical representation and comparing its `canonical_batch_sha256`. (It does not claim to detect raw metadata/file-level edits that leave logical canonical data unchanged).
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
   - Event End Inconsistency Across Revisions         - Statistically unusual observations
   - Distinct Event Monotonicity Violations            
   - Duplicate Event-Scoped revision_seq               
   - Duplicate Global Revision Identities              
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
  "batch_id": "batch_20260827_001_a1b2c3d4",
  "source_id": "binance_public",
  "source_uri_or_path": "data/raw/btc_usdt_1m.csv",
  "part_file_path": "data/parquet/BTC-USDT/M1/year=2026/part-000001-a1b2c3d4.parquet",
  "ingest_time_utc": "2026-08-27T21:30:00.000000Z",
  "raw_source_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "canonical_batch_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
  "schema_version": "1.12.0",
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
> **Audit Log Security Boundaries:** The JSONL provenance ledger is an append-only application audit log, not a cryptographically tamper-evident or chained ledger. The embedded SHA-256 hashes verify logical canonical data content. Cryptographic hash chaining or WORM storage may be evaluated in future enterprise security phases.
