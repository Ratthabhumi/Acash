# ACASH V5 — BTC Historical Acquisition Decision Pack

**Document ID:** `docs/phase14/btc_historical_acquisition_decision_pack.md`
**STATUS: NON-GOVERNING**
**AUTHORITY: NONE**
**DATA ACQUISITION AUTHORIZATION: NONE**
**EMPIRICAL AUTHORIZATION: NONE**
**BACKTEST AUTHORIZATION: NONE**
**PAPER AUTHORIZATION: NONE**
**LIVE AUTHORIZATION: NONE**
**Canonical Architectural Context:** `AGENTS.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/phase14/historical_data_qualification_spec.md`, `docs/phase14/free_data_source_registry.md`, `docs/phase14/free_data_research_registry.md`

---

> [!CAUTION]
> ### STRICT RESEARCH-DATA BOUNDARIES & GOVERNANCE INVARIANTS
> - **PLANNING & EVIDENCE DOSSIER ONLY:** This document authorizes zero dataset downloads, zero network fetches, zero scraping scripts, and zero automated data ingestion.
> - **NO HYPOTHESIS CREATION:** `HYP_003` remains **ABSENT**. No trading hypothesis or alpha model is formulated or registered.
> - **ZERO CAPITAL & LOCKED EXECUTION:** Canonical trading capital remains **$0.00**; `NO_REAL_ORDERS=true`. Paper and live execution remain strictly locked.
> - **NON-GOVERNING DECISION SURFACES:** Recommendations in this document do not resolve canonical decisions (`DATA-DEC-001`, `DATA-DEC-002`, `DATA-DEC-003`). All final provider and storage selections require explicit Human Governance ratification.
> - **SEPARATION FROM ACTIVE G7 SOAK:** Active Gate 7 (`G7`) operational runtime evidence is decoupled from historical research datasets. This pack does not interact with, benchmark against, or mutate the active homelab runtime.

---

## 1. Executive Summary & Objective

The objective of this decision pack is to evaluate candidate providers, licensing boundaries, cross-verification protocols, coverage spans, and storage architectures for the future acquisition of Bitcoin (`BTC`) historical market data for ACASH quantitative research.

This pack addresses three open decision surfaces defined in Phase 14 planning:
1. **`DATA-DEC-001` — BTC Historical Provider Selection:** Primary archive candidate vs. secondary independent validation candidate.
2. **`DATA-DEC-002` — Target Historical Coverage Span:** 1-year, 2-year, 4-year, and maximum available coverage horizons evaluated across regime coverage, storage footprint, and download complexity.
3. **`DATA-DEC-003` — Partition & Compression Implementation Choice:** Standardized Parquet schema, zstd compression level, and DuckDB analytical query integration.

Every factual provider claim in this document is bound to verifiable primary sources (official exchange documentation, public terms of use, API documentation, or public archive endpoints).

---

## 2. Provider Evaluation Matrix

We evaluate three candidate exchange sources and one independent secondary reference:
- **Candidate 1:** Binance Official Public Data Archives (`data.binance.vision`)
- **Candidate 2:** Kraken Official Historical Data Archives & Public REST API
- **Candidate 3:** Coinbase Exchange Public REST Market Data API
- **Candidate 4:** Independent Aggregator / Vendor Benchmarks (Tardis.dev / CryptoDataDownload)

### 2.1 Detailed Provider Evidence Profiles

| Field | Binance Public Data Archives | Kraken Public Historical Dumps / API | Coinbase Exchange Public API | Tardis.dev (Sample / Paid) |
| :--- | :--- | :--- | :--- | :--- |
| **Provider** | Binance | Kraken (Payward, Inc.) | Coinbase Inc. | Tardis.dev (Commercial Vendor) |
| **Source Type** | Public S3 Archive / HTTP Gateway | Public Web Download / REST API | REST Public API (`candles`) | Cloud Archive / Replay API |
| **Official / Third-Party** | Official Exchange Archive | Official Exchange Archive & API | Official Exchange API | Commercial Third-Party Vendor |
| **Market** | Spot & USDⓈ-M Futures (Separated) | Spot & Futures (Separated) | Spot | Spot & Derivatives (Multi-exchange) |
| **Instrument** | `BTCUSDT` (also `BTCUSDC`, `BTCFDUSD`) | `XXBTZUSD`, `XBTUSDT` | `BTC-USD`, `BTC-USDT` | Normalized multi-exchange symbols |
| **Available Timeframes** | 1s, 1m (M1), 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d | Raw trade prints (aggregate to M1) / API OHLC (last 720 bars) | 1m (M1), 5m, 15m, 1h, 6h, 1d | Tick-level trades, book snapshots, M1 |
| **M1 Availability** | Direct M1 kline archives (`monthly` / `daily`) | Derived from tick trade history CSVs | Paginated REST (max 300 bars/call) | Generated from raw tick stream |
| **Earliest M1 Date** | 2017-08-17 (`BTCUSDT` Spot launch) | ~2013-10-06 (XBT/USD trade history) | ~2015-01-26 (Coinbase BTC-USD) | Multi-year (~2018+ for Binance/Kraken) |
| **Latest Coverage** | Rolling daily updates (T-1 day lag) | Rolling periodic CSV dumps / Live REST | Live rolling real-time | Rolling daily updates |
| **Archive Organization** | Hierarchical: `data/spot/monthly/klines/{SYMBOL}/1m/` | Flat ZIP/CSV files by symbol/quarter | No bulk zip archive; REST query only | AWS S3 / HTTP REST streaming |
| **Archive Mutability** | Externally revisable by provider; frozen locally upon acquisition | Quarterly historical CSV dumps | Real-time endpoint queryable | Daily tick archives |
| **Revision Policy** | Provider may update/replace archives with revised checksums; ACASH binds local bytes | Periodic additions of completed quarters | Real-time bar updates | Versioned parser schema |
| **Timestamp Semantics** | Unix Epoch Milliseconds (`open_time`, `close_time`) | Unix Epoch Seconds / Nanoseconds | Unix Epoch Seconds (ISO-8601 available) | Unix Epoch Microseconds / Nanoseconds |
| **OHLC Semantics** | Standard Open, High, Low, Close per window | Aggregated from discrete trade ticks | Standard Open, High, Low, Close | Derived from order book / trades |
| **Volume Semantics** | Base asset volume & Quote asset volume | Base volume (BTC quantity traded) | Base volume (BTC quantity) | Base & Quote traded volume |
| **Trade Count Availability** | Available (`number_of_trades` field in CSV) | Available (discrete trade records) | Not reported in standard candles | Available |
| **Bid/Ask Availability** | Absent in klines; separate order book archive | Absent in trade CSVs; separate L2 book | Absent in candles; separate L2 REST/WS | Top-of-book and L2 depth available |
| **Funding Availability** | USDⓈ-M funding archives published separately | Kraken Futures funding published separately | Not applicable (Spot only) | Funding series archived |
| **Authentication** | None required ($0, public access) | None required for public dumps / API | None required for public candles | API key required (Free sample / Paid) |
| **Rate Limits** | AWS S3 standard limits; HTTP 429 backoff | 1–2 req/s REST; bulk CSV via browser/CDN | 10 req/s REST public endpoint | API key rate limits |
| **Download Mechanism** | Direct HTTP / AWS S3 CLI / Public curl | Web browser direct download / curl | Paginated REST crawler script | Python/Node client library / S3 |
| **Checksum Support** | Provided (`.CHECKSUM` SHA-256 for each zip) | Provided for historical bulk zips | None (REST JSON payload) | MD5 / SHA-256 in manifest |
| **Licensing / Terms** | Binance Public Data Terms of Use | Kraken Website Terms of Use | Coinbase Developer Platform Terms | Tardis Commercial Subscription License |
| **Redistribution** | Personal / internal research; no resale | Personal / non-commercial research | Personal / internal developer use | Commercial restricted; no resale |
| **Commercial Restrictions** | Commercial redistribution prohibited | Commercial redistribution restricted | Commercial redistribution restricted | Tiered commercial pricing |
| **Cost** | $0.00 | $0.00 | $0.00 | $0 (Sample 1st of month) / Paid full |
| **PIT Characteristics** | High (exact historical execution timestamps) | High (exact historical trade timestamps) | High (historical execution timestamps) | Exact nanosecond exchange timestamps |
| **Known Gaps / Outages** | Documented maintenance windows (2018, 2019) | Documented system maintenance events | Documented degraded engine periods | Tracks underlying exchange outages |
| **Known Symbol Changes** | None for `BTCUSDT` (stable since 2017) | `XXBTZUSD` vs `XBTUSDT` symbology | `BTC-USD` vs `BTC-USDT` | Handled via unified mapping |
| **Known Data Corrections** | Provider file replacements documented (e.g. issue #475); exact checksum & retrieval UTC binding required | None reported for completed quarters | None reported | Monitored |
| **Reproducibility** | High once frozen locally (vendor zips + dual SHA-256) | High (static CSV archives + hashes) | Low (floating window pagination) | High (deterministic raw data replay) |
| **Primary Risks** | External provider mutability; single-exchange concentration | Aggregation complexity from trade ticks | Crawler rate-limit throttling; incomplete bars | Paid license cost boundary |
| **Evidence Status** | **VERIFIED** | **VERIFIED** | **PARTIALLY VERIFIED** | **NOT SUITABLE AT $0** |

---

## 3. Candidate Categorization & Recommendations

Based on the empirical evidence gathered above:

### 3.1 Primary Candidate Recommendation: Binance Public Data Archives
- **Status:** **`PRIMARY CANDIDATE (RECOMMENDED)`**
- **Rationale:**
  1. Direct, pre-aggregated M1 kline archives organized by month and day at `$0.00`.
  2. Cryptographic checksum files (`.CHECKSUM` SHA-256) are published alongside every raw artifact.
  3. Includes critical microstructural fields: base volume, quote volume, trade count, taker buy base volume, taker buy quote volume.
  4. Deepest continuous M1 liquidity history for `BTCUSDT` (from August 2017 to present, > 4.7 million bars).
  5. Completely public S3 / HTTP bucket (`data.binance.vision`) requiring zero API keys, tokens, or credential storage.

### 3.2 Secondary Validation Candidate Recommendation: Kraken Public Historical Dumps
- **Status:** **`SECONDARY / VALIDATION CANDIDATE (RECOMMENDED)`**
- **Rationale:**
  1. Fully independent matching engine, order book, and regulatory jurisdiction (US / EU fiat banking rails vs. offshore stablecoin).
  2. Publicly downloadable historical trade data CSVs covering Bitcoin from late 2013 to present.
  3. Serves as the independent cross-exchange validation reference to confirm macro trend direction, extreme event timing, and trading halts without assuming Binance data is flawless.
  4. Requires offline trade-to-bar aggregation to synthesize M1 OHLCV.

### 3.3 Deferred Candidate: Coinbase Public REST API
- **Status:** **`DEFERRED`**
- **Rationale:** Coinbase does not offer a free, official multi-year bulk archive of historical M1 bars. Historical acquisition requires crawling the paginated `candles` endpoint at 300 bars per call (requiring ~16,000 HTTP calls per year of M1 data), exposing the process to network drops, rate-limit throttling, and pagination gaps. Deferred unless official bulk archives become available.

### 3.4 Rejected Candidates: Unverified Aggregators
- **Status:** **`REJECTED`**
- **Rationale:** Aggregator websites (e.g. CryptoDataDownload, free Kaggle uploads) lack cryptographic provenance, clear licensing contracts, documented revision histories, and volume field definitions. Using unverified third-party aggregators violates the strict fail-closed contract of ACASH.

---

## 4. Cross-Verification & Reconciliation Protocol

To ensure ACASH does not assume primary vendor data is immaculate, the acquisition pipeline must support dual-source cross-verification:

```
+-----------------------------+         +-----------------------------+
|    Primary Data Source      |         |   Secondary Validation      |
|  (Binance Public Archives)  |         |   (Kraken Historical Dumps) |
+--------------+--------------+         +--------------+--------------+
               |                                       |
               v                                       v
      [ Raw Binance M1 ]                     [ Raw Kraken Trades ]
               |                                       |
               |                                       v
               |                            [ Synthesized Kraken M1 ]
               |                                       |
               +-------------------+-------------------+
                                   |
                                   v
                   +-------------------------------+
                   | Cross-Verification Engine     |
                   | - Daily OHLC Alignment        |
                   | - Outlier Print Identification|
                   | - Extreme Event Synchronization|
                   | - Trading Halt Verification   |
                   +---------------+---------------+
                                   |
                                   v
                   +-------------------------------+
                   | Reconciliation Report & Ledger|
                   +-------------------------------+
```

### 4.1 Verification Principles
1. **Exchange Price Differences are Legitimate:** Prices between Binance (`BTCUSDT`) and Kraken (`BTCUSD` / `BTCUSDT`) naturally diverge due to differing liquidity, counterparty credit, and fiat vs. stablecoin pegs. **Exact price equality must never be asserted.**
2. **Structural Sanity Invariants:**
   - **Timestamp Monotonicity:** Both series must strictly advance forward in time without backwards jumps.
   - **Extreme Event Coincidence:** Major historical market movements (e.g. 2020-03-12 50% crash, 2021-05-19 liquidation cascade, 2022-11-08 FTX collapse) should show contemporaneous peak volatility within an illustrative candidate window (e.g. $\pm 2$ to $\pm 5$ minutes, `ILLUSTRATIVE / NOT FROZEN`).
   - **Directional Parity:** Daily return correlation ($r$) between Binance BTCUSDT and Kraken XBTUSD can serve as a sanity benchmark (e.g. candidate threshold $r > 0.95$, `ILLUSTRATIVE / NOT FROZEN`, across continuous operational months).
   - **Bar Cadence:** Any gap in Binance M1 bars exceeding 15 consecutive minutes must be checked against Kraken to classify whether the event was an exchange-specific downtime or a market-wide phenomenon.

---

## 5. Target Historical Coverage Span Evaluation (`DATA-DEC-002`)

The table below evaluates four candidate historical coverage spans.

> [!NOTE]
> All bar counts, download durations, CSV sizes, and Parquet sizes are **ILLUSTRATIVE CAPACITY ESTIMATES** (no machine- or network-specific download time promise). Coverage selection does not constitute a statistical sufficiency claim or an admission gate, and remains subject to `DATA-DEC-002` human ratification.

| Horizon | Approximate M1 Bars (Illustrative) | Regime Coverage Span | Uncompressed CSV Footprint (Estimate) | Compressed Parquet (zstd) (Estimate) | Ingestion & Verification Complexity | Research Utility & Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 Year** (e.g. 2023 Sample) | ~525,600 | Single macro regime (post-FTX recovery, low-to-medium volatility, ETF speculation). | ~45 MB | ~8 MB | Low complexity (illustrative quick download). | **Insufficient Regime Diversity:** Fails to cover deep bear markets, high-inflation tightening shocks, or extreme liquidation spirals. |
| **2 Years** (e.g. 2022–2023 Sample) | ~1,051,200 | Severe bear market (Luna/FTX collapse, aggressive Fed hikes) + early recovery regime. | ~90 MB | ~16 MB | Moderate complexity. | **Moderate Diversity:** Captures structural distress and grinding recovery; lacks multi-year halving cycle dynamics. |
| **Candidate Rolling 4-Year Window** (e.g. 2020–2023 Historical Example or Latest Window through 2024–2026) | ~2,102,400 | Full liquidity cycle: COVID crash, monetary expansion, bull market, 2022 unwind, 2023–2024 consolidation/ETF era. | ~180 MB | ~32 MB | Moderate complexity (multi-regime qualification). | **Candidate Baseline:** Provides multi-regime out-of-sample splits across distinct monetary environments. Exact boundary dates subject to `DATA-DEC-002` human decision. |
| **Maximum Available** (2017–Present) | ~4,750,000+ | Complete Binance exchange history: 2017 retail mania, 2018–2019 crypto winter, 2020–2021 bull market, 2022 bear, 2023–2026 ETF era. | ~420 MB | ~75 MB | Moderate-High (requires handling early 2017 exchange-growth anomalies and maintenance outages). | **Comprehensive Longitudinal Scope:** Maximum statistical power, but early periods (2017–2018) exhibit non-stationary microstructure and fragmented liquidity. |

---

## 6. Partition & Storage Implementation (`DATA-DEC-003`)

### 6.1 Storage Hierarchy
ACASH evaluates a candidate storage implementation using local Parquet files queried via DuckDB (`CANDIDATE IMPLEMENTATION — subject to DATA-DEC-003 human ratification`):

```text
/data/research/market_data/
└── crypto/
    └── binance/
        └── spot/
            └── btcusdt/
                ├── raw_archives/                          <-- Provider archives (frozen locally upon acquisition + verified with vendor & ACASH checksums)
                │   ├── BTCUSDT-1m-2022-01.zip
                │   ├── BTCUSDT-1m-2022-01.zip.CHECKSUM
                │   └── ...
                ├── manifests/
                │   └── acquisition_manifest_20260913.json <-- Cryptographic acquisition record
                └── normalized/                            <-- Hive-partitioned Parquet files
                    ├── year=2022/
                    │   ├── month=01/
                    │   │   └── data.parquet
                    │   └── ...
                    └── year=2023/
                        └── ...
```

### 6.2 Parquet Column Specification & DuckDB Types
Normalized files must conform strictly to the schema defined in [historical_data_qualification_spec.md](./historical_data_qualification_spec.md):

| Column Name | Arrow / Parquet Type | DuckDB SQL Type | Nullable | Description |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp_utc` | `TIMESTAMP(US, "UTC")` | `TIMESTAMPTZ` | **No** | Bar open timestamp in UTC. |
| `symbol` | `STRING` | `VARCHAR` | **No** | Normalized symbol identifier (`BTCUSDT`). |
| `open` | `DECIMAL(18, 8)` | `DECIMAL(18, 8)` | **No** | Opening price during bar window. |
| `high` | `DECIMAL(18, 8)` | `DECIMAL(18, 8)` | **No** | Maximum price during bar window. |
| `low` | `DECIMAL(18, 8)` | `DECIMAL(18, 8)` | **No** | Minimum price during bar window. |
| `close` | `DECIMAL(18, 8)` | `DECIMAL(18, 8)` | **No** | Closing price during bar window. |
| `volume` | `DECIMAL(28, 8)` | `DECIMAL(28, 8)` | **No** | Total base asset units traded. |
| `quote_volume` | `DECIMAL(28, 8)` | `DECIMAL(28, 8)` | **No** | Total quote asset volume traded. |
| `trade_count` | `INT64` | `BIGINT` | **No** | Total discrete trades executed. |
| `taker_buy_base_volume`| `DECIMAL(28, 8)` | `DECIMAL(28, 8)` | **No** | Taker aggressive buy base units. |
| `taker_buy_quote_volume`| `DECIMAL(28, 8)` | `DECIMAL(28, 8)` | **No** | Taker aggressive buy quote volume. |

### 6.3 Compression & Chunking Configuration
- **Compression Codec:** `zstd` (level 7 for research archives; optimal balance of compression ratio and decompression speed).
- **Row Group Size:** 100,000 rows (~70 calendar days of M1 bars per row group).
- **Partitioning Strategy:** Hive-style directory partitioning by `year=YYYY/month=MM/`.
- **Query Engine:** DuckDB queries Parquet files directly via glob patterns (`read_parquet('/data/research/.../year=*/month=*/*.parquet')`) with zero database server overhead.

---

## 7. Acquisition Lifecycle & Fail-Closed Failure Playbook

When human authorization is granted to acquire historical data, the execution pipeline must follow this 10-stage fail-closed lifecycle:

```
  [ 1. Select Provider & Review Terms ]
                   │
                   ▼
  [ 2. Record Terms & License in Dossier ]
                   │
                   ▼
  [ 3. Download Raw Archives + Checksums ]
                   │
                   ▼
  [ 4. Verify Vendor SHA-256 Checksums ]
                   │
                   ▼
  [ 5. Preserve Original Raw Bytes (Read-Only) ]
                   │
                   ▼
  [ 6. Generate Acquisition Manifest & Root Hash ]
                   │
                   ▼
  [ 7. Validate Archive Completeness & File Count ]
                   │
                   ▼
  [ 8. Normalize to Arrow / Parquet Standard ]
                   │
                   ▼
  [ 9. Run Data Qualification Verification Suite ]
                   │
                   ▼
  [ 10. Freeze Dataset Version & Seal Lineage ]
```

### 7.1 Fail-Closed Failure Handling

| Failure Scenario | Immediate System Action | Diagnostic Protocol | Remediation Protocol |
| :--- | :--- | :--- | :--- |
| **Download Interruption / HTTP Error** | Abort batch immediately; delete partial file. | Log HTTP status code, URL, bytes transferred. | Retry with exponential backoff; if persistent, fail closed. |
| **Vendor SHA-256 Mismatch** | Quarantine file immediately; raise `DataContractError`. | Compute local hash vs. vendor `.CHECKSUM` content. | Re-download once; if mismatch persists, flag vendor corrupt archive. |
| **Missing Monthly / Daily Archive** | Halt acquisition; mark universe incomplete. | Inspect vendor listing for date gap. | Check exchange maintenance announcements; record documented gap. |
| **Vendor Revision / Hash Change** | Quarantine new file; do not overwrite existing. | Compare old vs. new byte content and diff. | Escalate to human governance; determine if restatement is valid. |
| **Duplicate Timestamp within File** | Reject file; fail qualification. | Identify offending bar timestamps. | Do not average or drop silently; investigate raw trades. |
| **Negative or Zero Price / Volume** | Reject file immediately; fail closed. | Locate record row index and raw line. | Escalate; zero price indicates bad print or data corruption. |
| **Schema Field Count Mismatch** | Abort parsing; raise `DataContractError`. | Compare header/column count against parser spec. | Update parser version; require human review before proceeding. |

---

## 8. Open Decisions for Human Governance

Before any historical acquisition script is executed, human governance must ratify:

1. **`DATA-DEC-001` Ratification:** Approve Binance Public Data Archives as primary acquisition source and Kraken as secondary validation reference.
2. **`DATA-DEC-002` Ratification:** Authorize specific historical target horizon (e.g., candidate rolling 4-year window through 2024–2026 vs. maximum available 2017–present).
3. **`DATA-DEC-003` Ratification:** Authorize candidate Parquet/DuckDB storage implementation and physical local storage allocation (illustrative capacity estimate < 100 MB).

---

## 9. External Evidence & Citations

1. **Binance Public Data Vision Portal:**
   - URL: `https://data.binance.vision/`
   - Access Date: 2026-09-13 UTC
   - Supported Claims: Public availability of monthly/daily M1 klines, aggTrades, and trade archives for `BTCUSDT`; S3 public bucket `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision`.
2. **Binance Public Data Terms of Use:**
   - URL: `https://data.binance.vision/terms-of-use.html`
   - Access Date: 2026-09-13 UTC
   - Supported Claims: Public access terms; personal and research use; redistribution constraints.
3. **Binance Public Data GitHub Documentation & Mutability Notices:**
   - URL: `https://github.com/binance/binance-public-data/`
   - Access Date: 2026-09-13 UTC
   - Supported Claims: Archive directory structure, file naming conventions, `.CHECKSUM` hash support, and automated download scripts. Note: binance-public-data issue #475 documents discrepancies between monthly archives and daily archives/API, and repository documentation confirms archived files may be updated or replaced when issues are found, publishing replacement checksums. External provider archives are therefore treated as externally mutable until frozen locally by ACASH acquisition manifests.
4. **Kraken Historical Market Data Archives:**
   - URL: `https://support.kraken.com/hc/en-us/articles/360047124832-Downloadable-historical-market-data`
   - Access Date: 2026-09-13 UTC
   - Supported Claims: Downloadable historical trade CSV files for `XBTUSD` and `XBTUSDT` since exchange inception; public availability for research.
5. **Coinbase Exchange API Reference:**
   - URL: `https://docs.cdp.coinbase.com/exchange/reference/getproductcandles`
   - Access Date: 2026-09-13 UTC
   - Supported Claims: REST candles endpoint returns max 300 candles per call; public rate limits apply; absence of official multi-year bulk ZIP archives.

---

### Verification Ledger
- Implementation Status: COMPLETE (Documentation & decision pack specification)
- Contract Enforcement: STRICT FAIL-CLOSED (Zero download, zero backtest authority, zero hypothesis creation)
- Mathematical Authority: PLANNING / NON-GOVERNING SPEC (Aligned with `historical_data_qualification_spec.md`)
- Local Test Suite: NOT RUN (Documentation-only deliverable)
- Type Checker (MyPy): NOT RUN (Documentation-only deliverable)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: Planning bar counts and storage sizes are non-binding illustrative capacity estimates. Dual-source cross-verification does not assume price identity between distinct venues. All external archives are treated as externally mutable until locally verified and frozen.
