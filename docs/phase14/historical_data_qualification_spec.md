# ACASH Historical Market-Data Foundation & Data Qualification Specification

**Document ID:** `docs/phase14/historical_data_qualification_spec.md`
**Status:** NON-GOVERNING RESEARCH-DATA SPECIFICATION
**Authority:** NONE
**Implementation Authorization:** NONE
**Data Acquisition Authorization:** NONE
**Empirical Test Authorization:** NONE
**Backtest Authorization:** NONE
**Paper Authorization:** NONE
**Live Authorization:** NONE
**Canonical Architectural Context:** `AGENTS.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/architecture/research_architecture.md`, `docs/architecture/asset_market_agnostic_research_direction.md`, `docs/architecture/strategy_admission_standard.md`, `docs/phase14/phase14_master_research_architecture_plan.md`, `docs/phase14/research_doctrine.md`

---

> [!CAUTION]
> ### STRICT RESEARCH-DATA BOUNDARIES & SAFETY INVARIANTS
> - **DOCUMENTATION & SPECIFICATION ONLY:** This document authorizes zero data downloads, zero network fetches, zero scraping, and zero automated vendor ingestion.
> - **NO HYPOTHESIS CREATION:** `HYP_003` remains **ABSENT**. No research hypothesis is registered or ratified.
> - **NO STRATEGY ADMISSION OR BACKTESTING:** Dataset qualification is an infrastructural precondition; a qualified dataset confers **zero** strategy admission, **zero** backtest execution authority, and **zero** statistical validity to any trading model.
> - **SEPARATION FROM G7 SOAK:** Gate 7 (`G7`) validates feed resilience, session journalling, and operational container health over short operational windows (e.g. 6-hour soak). **G7 does NOT provide research-grade historical market datasets.**
> - **CAPITAL & ORDERS LOCKED:** Canonical trading capital remains **$0.00**; `NO_REAL_ORDERS=true`.

---

## 1. Executive Summary & Objective

The objective of this specification is to define the architectural foundation, metadata schema, data lifecycle, quality verification tests, and version-freeze protocols required for historical market data in ACASH before empirical quantitative research commences.

Moving from operational infrastructure verification (such as G7) into empirical hypothesis testing requires clean, well-characterized, time-consistent, and auditable historical data (with stationarity or non-stationarity evaluated downstream per series, transformation, and hypothesis rather than as a qualification gate). Without an authoritative data qualification standard, quantitative research is vulnerable to:
1. Silent survivorship bias, look-ahead bias, and corporate action leakage.
2. Inconsistent timezone alignments and artificial weekend/holiday gap artifacts.
3. Unverified volume definitions (e.g., tick count masquerading as traded contract volume).
4. Silent interpolation or synthetic bar creation masquerading as empirical market activity.
5. Inability to reproduce backtest results due to floating or mutated vendor history.

This document establishes the fail-closed verification standard that all candidate historical datasets must satisfy prior to being bound into frozen empirical research trials.

---

## 2. Distinction Between Operational Soak and Historical Research Data

ACASH maintains a strict separation between operational runtime evidence and research data:

| Dimension | G7 Operational Harness / Soak | Historical Research Data Foundation |
| :--- | :--- | :--- |
| **Primary Objective** | Validate process resilience, socket stability, journal lineage, memory bounds, and operator-only recovery. | Provide deep, clean, multi-regime, multi-year, stationary inputs for empirical hypothesis evaluation. |
| **Observation Horizon** | Short operational window (e.g., 6 hours to 24 hours). | Multi-month to multi-year history across distinct macroeconomic regimes. |
| **Data Continuity** | Real-time live websocket / polling feed subject to network jitters and vendor throttles. | Frozen, reconciled, verified, and immutable historical archives. |
| **Research Authority** | Proves the engine can run without crashing or leaking state; **zero research validity**. | Authoritative input for backtests, out-of-sample (OOS) validation, and walk-forward testing. |
| **Execution Permission** | Synthetic paper session with zero capital ($0.00). | Completely decoupled from execution engines; offline analytical storage only. |

The data layer must remain strictly decoupled from strategy execution engines, order routing coordinators, paper trading runners, and live trading authority.

---

## 3. Proposed Research Data Domains

In accordance with [asset_market_agnostic_research_direction.md](../architecture/asset_market_agnostic_research_direction.md), ACASH research architectures are designed to be cross-asset and market-agnostic. The domains below represent prospective data domains for future research ingestion.

> [!IMPORTANT]
> **CLASSIFICATION:** Every asset below is classified strictly as a **PROPOSED RESEARCH DATA DOMAIN**, NOT an approved trading universe.

### 3.1 Crypto Assets
- **Candidate Scope:** `BTC` (Bitcoin), `ETH` (Ethereum).
- **Research Role:** Continuous 24/7 regime analysis, liquidity-expansion studies, cross-market risk sentiment.
- **Structural Nuance:** Spot vs. perpetual futures distinctions, funding rate series, exchange-specific fragmentation.

### 3.2 Foreign Exchange (FX)
- **Candidate Scope:** `EURUSD` initially; potentially major currency pairs (`USDJPY`, `GBPUSD`, `AUDUSD`) later.
- **Research Role:** Global macroeconomic momentum, interest rate differential responses, systematic macro state.
- **Structural Nuance:** Decentralized OTC quotes, absence of centralized volume, 5 PM New York rollover conventions, Sunday-Friday sessions.

### 3.3 Metals & Commodities
- **Candidate Scope:** `XAU` (Gold spot or continuous futures proxy).
- **Research Role:** Inflation hedge dynamics, geopolitical flight-to-safety, risk-off regime identification.
- **Structural Nuance:** London fix vs. COMEX futures pricing, rollover gaps, custody/storage pricing differentials.

### 3.4 Equity Index Futures
- **Candidate Scope:** `ES` (E-mini S&P 500); potentially `NQ` (E-mini Nasdaq 100) later.
- **Research Role:** Broad market equity beta, intraday session transitions, systematic market momentum.
- **Structural Nuance:** Quarterly contract rolls, back-adjustment methodologies (proportional vs. difference), cash market hours vs. Globex overnight sessions.

### 3.5 Equities / ETFs / Sectors
- **Candidate Scope:** Broad-market ETFs (`SPY`, `QQQ`, `IWM`), sector SPDRs, liquid large-cap US equities.
- **Research Role:** Cross-sectional relative strength, sector dispersion, multi-factor cross-sectional anomaly testing.
- **Structural Nuance:** Corporate actions (cash dividends, stock splits, spinoffs), delistings, point-in-time index constituent changes (survivorship bias).

### 3.6 Fixed Income & Rates
- **Candidate Scope:** Treasury yield curves (FRED/DGS series), Treasury futures proxies (`ZT`, `ZN`, `ZB`).
- **Research Role:** Discount factor regimes, yield curve slope/curvature conditioning, term premia analysis.
- **Structural Nuance:** Tenor rolls, yield-to-price non-linear inversion, coupon adjustments.

---

## 4. Non-Binding Bar Count Planning Heuristics

To evaluate storage footprint, ingestion pipeline throughput, and statistical sample dimensions, the following planning approximations are established for M1 (1-minute) bar frequencies:

| Duration | Approximate M1 Bar Count (Crypto 24/7) | Approximate M1 Bar Count (Futures ~23/5) | Approximate M1 Bar Count (US Equities ~6.5h/d) |
| :--- | :--- | :--- | :--- |
| **1 Day** | $\approx 1,440$ | $\approx 1,380$ | $\approx 390$ |
| **7 Days** | $\approx 10,080$ | $\approx 6,900$ | $\approx 1,950$ |
| **30 Days** | $\approx 43,200$ | $\approx 29,900$ | $\approx 8,190$ |
| **90 Days** | $\approx 129,600$ | $\approx 89,700$ | $\approx 24,570$ |
| **6 Months** | $\approx 262,800$ | $\approx 180,000$ | $\approx 49,500$ |
| **1 Year** | $\approx 525,600$ | $\approx 360,000$ | $\approx 99,000$ |
| **2 Years** | $\approx 1,051,200$ | $\approx 720,000$ | $\approx 198,000$ |
| **4 Years** | $\approx 2,102,400$ | $\approx 1,440,000$ | $\approx 396,000$ |

### Planning Interpretations
- **6 to 12 Months:** Useful for initial exploratory feature design, schema stress testing, and pipeline pipeline debugging.
- **2 to 4 Years:** Preferred baseline for empirical research to span diverse macro environments (e.g. bull, bear, sideways, high-volatility, low-volatility regimes).

> [!WARNING]
> **GOVERNANCE STATUS: NON-BINDING PLANNING HEURISTIC ONLY.**
> These bar counts are strictly planning guides. They do **NOT** constitute statistical acceptance gates. Under no circumstances shall an arbitrary bar count (e.g. "500,000 bars reached") be interpreted as strategy qualification or sample sufficiency. Canonical statistical significance is governed by effective degrees of freedom ($T_{\text{eff}}$), Minimum Track Record Length ($\text{MinTRL}$), and canonical Phase 6 mathematical standards.

---

## 5. Data Acquisition Metadata Contract

Every historical market data file or stream ingested into the ACASH research boundary must be accompanied by an immutable, cryptographically sealed metadata manifest. No bare data files without complete provenance manifests are permitted.

### 5.1 Mandatory Metadata Fields

```json
{
  "provider": "STRING (e.g., 'Binance_Public_Archive', 'Interactive_Brokers', 'DoltHub', 'FirstRateData')",
  "source_dataset_id": "STRING (Vendor-assigned dataset or batch identifier)",
  "instrument": "STRING (Canonical ACASH asset identifier, e.g., 'BTC', 'ES', 'EURUSD')",
  "venue": "STRING (Primary trading venue or composite feed, e.g., 'BINANCE', 'CME', 'EBS')",
  "asset_class": "STRING ('CRYPTO', 'FX', 'COMMODITY', 'EQUITY', 'FUTURE', 'RATE')",
  "symbol_vendor": "STRING (Exact symbol text as reported by vendor, e.g., 'BTCUSDT', 'ESH26')",
  "symbol_canonical": "STRING (ACASH canonical standardized symbol)",
  "timeframe": "STRING (Bar aggregation interval, e.g., 'M1', 'M5', 'H1', 'D1')",
  "coverage_start_utc": "ISO8601_TIMESTAMP (e.g., '2022-01-01T00:00:00Z')",
  "coverage_end_utc": "ISO8601_TIMESTAMP (e.g., '2025-12-31T23:59:00Z')",
  "retrieval_timestamp_utc": "ISO8601_TIMESTAMP (Timestamp when data was acquired)",
  "retrieval_method": "STRING ('REST_API', 'S3_BUCKET', 'DIRECT_CSV_DOWNLOAD', 'DB_EXPORT')",
  "endpoint_or_uri": "STRING (Target endpoint, archive URL, or bucket ARN)",
  "authentication_requirement": "STRING ('PUBLIC_ANONYMOUS', 'API_KEY', 'AUTHENTICATED_SUBSCRIPTION')",
  "license_and_terms": "STRING (License type, e.g., 'OPEN_RESEARCH', 'COMMERCIAL_REDISTRIBUTION_PROHIBITED')",
  "redistribution_restrictions": "STRING ('RESTRICTED_INTERNAL_ONLY', 'PUBLIC_DERIVATIVE_ALLOWED')",
  "timezone_semantics": "STRING ('UTC_EXPLICIT', 'US_EASTERN_PRE_NORMALIZED', 'EXCHANGE_LOCAL')",
  "session_calendar_semantics": "STRING ('CRYPTO_24_7', 'CME_GLOBEX', 'NYSE_REGULAR_TRADING_HOURS')",
  "price_adjustment_policy": "STRING ('RAW_UNADJUSTED', 'SPLIT_ONLY', 'SPLIT_AND_DIVIDEND', 'BACK_ADJUSTED_PANAMA')",
  "volume_semantics": "STRING ('ACTUAL_CONTRACTS', 'BASE_ASSET_UNITS', 'QUOTE_ASSET_VOLUME', 'TICK_VOLUME', 'UNAVAILABLE')",
  "corporate_action_policy": "STRING ('NONE', 'POINT_IN_TIME_PERSISTED', 'VENDOR_ADJUSTED_UNVERIFIED')",
  "contract_roll_policy": "STRING ('NOT_APPLICABLE', 'VOLUME_CROSSOVER', 'OPEN_INTEREST_CROSSOVER', 'FIXED_DAYS_PRIOR_EXPIRY')",
  "raw_file_sha256": "STRING (64-character SHA-256 hex digest of raw download artifact)",
  "transformation_version": "STRING (Semantic version of transformation code, e.g., 'transform_v1.0.0')",
  "normalization_version": "STRING (Semantic version of schema normalizer, e.g., 'norm_v1.0.0')"
}
```

### 5.2 Handling of Unknowns and Missing Fields
- **Fail-Closed Principle:** Under no circumstances shall an ingest script fabricate or default an unknown metadata value.
- Missing or ambiguous fields must explicitly receive an authoritative sentinel:
  - `"UNKNOWN"`: Information could not be determined from vendor documentation.
  - `"UNRESOLVED"`: Ambiguity exists requiring human research decision.
  - `"NOT_APPLICABLE"`: Field does not apply to asset class (e.g., `contract_roll_policy` for Spot Crypto).
- Datasets containing `"UNKNOWN"` or `"UNRESOLVED"` in critical governance fields (such as `timezone_semantics`, `price_adjustment_policy`, or `license_and_terms`) are strictly **blocked** from advancing to `QUALIFIED` status.

---

## 6. Dataset Lifecycle: Raw to Versioned Research Dataset

All historical data must flow through a deterministic, one-way state machine:

```text
RAW (Immutable Source Artifact)
  ↓
INGESTED (Staged in Isolation, Unaltered)
  ↓
NORMALIZED (Canonical ACASH Schema, Strict UTC Timestamps)
  ↓
QUALIFICATION CHECKS (Automated Anomaly & Structural Verification Battery)
  ↓
[DECISION GATE]
  ├── FAIL ──────────→ REJECTED / QUARANTINED (Isolated with Failure Manifest)
  └── PASS ──────────→ QUALIFIED / QUALIFIED_WITH_LIMITATIONS
                         ↓
                       VERSIONED RESEARCH DATASET (Frozen, Cryptographically Bound)
```

### Core Lifecycle Principles
1. **Raw Immutability:** Raw downloaded archives (CSVs, JSONs, vendor dumps) are stored in read-only cold storage and never modified in place.
2. **Deterministic Normalization:** Normalization code must be pure and reproducible. Given the same raw artifact and code version, the normalized output must produce an identical byte stream and SHA-256 hash.
3. **Persisted Audit Logs:** Every qualification run writes a persistent, machine-readable qualification report detailing every checked bar, flag, and metric.
4. **No Silent Discarding:** Rejected or anomalous rows are recorded in a quarantine log with exact line numbers, timestamps, and error codes. They must never be silently dropped without audit traces.
5. **Version Locking:** Once qualified, a research dataset is tagged with a permanent dataset ID and hash. Empirical trials must bind directly to this hash.

---

## 7. Proposed Research Normalized Bar Contract (Non-Canonical)

All normalized historical bar series evaluated under this non-governing specification are expected to conform to the following proposed research schema:

| Field Name | Type | Constraints / Invariants | Required? |
| :--- | :--- | :--- | :--- |
| `timestamp_utc` | `INT64` or `TIMESTAMP[ns/us]` | Nanoseconds or microseconds since Unix epoch; strictly monotonically increasing; UTC normalized. | **YES** |
| `symbol` | `STRING` | Standardized canonical ACASH symbol string (e.g. `BTC-USDT`, `ES_CONT`). | **YES** |
| `timeframe` | `STRING` | Canonical timeframe identifier (`M1`, `M5`, `H1`, `D1`). | **YES** |
| `open` | `FLOAT64` | Finite, non-negative, $> 0.0$ for economic assets. | **YES** |
| `high` | `FLOAT64` | Finite, $\ge \max(\text{open}, \text{close})$, $\ge \text{low}$. | **YES** |
| `low` | `FLOAT64` | Finite, $\le \min(\text{open}, \text{close})$, $> 0.0$. | **YES** |
| `close` | `FLOAT64` | Finite, non-negative, $\in [\text{low}, \text{high}]$. | **YES** |
| `volume` | `FLOAT64` or `NULL` | Optional finite value $\ge 0.0$. If the vendor feed does not supply volume, it must remain `NULL` (unavailable) matching `FeedBar` doctrine. It must **never** be fabricated as `0.0`. True zero volume must be strictly distinguished from unavailable volume. | **CONDITIONAL** |
| `source_id` | `STRING` | Identifier of the vendor/origin data feed. | **YES** |
| `flags` | `UINT32` | Bitmask capturing qualification anomalies, auction bars, or vendor warning flags. | **YES** |

> [!CAUTION]
> **VOLUME DISCIPLINE & UNAVAILABLE SEMANTICS:** In alignment with canonical `FeedBar` invariants (`src/acash/paper/feed.py`), fields not supplied by a data provider are recorded as unavailable (`None`/`NULL`) and must never be fabricated. In markets lacking centralized exchange volume (such as Spot FX), tick volume must **never** be silently cast or relabeled as true contract volume. If tick volume is used, `volume_semantics` must explicitly be tagged `"TICK_VOLUME"`.

---

## 8. Generic Data Qualification Specification

Before a normalized dataset can be admitted for research, it must execute and pass the following automated test families:

### 8.1 Identity & Mapping Verification
- Verify instrument identity against repository master symbol table.
- Verify asset class, currency denomination, and exchange/venue mapping.
- Confirm consistency of contract code, multiplier, and minimum tick size where applicable.

### 8.2 Temporal Integrity Verification
- **Parseability:** 100% of timestamps must parse cleanly into UTC without parsing errors.
- **Strict Monotonicity:** $\text{timestamp}_{i} > \text{timestamp}_{i-1}$. Zero backward time steps allowed.
- **Interval Consistency:** Check that $\Delta t = \text{timestamp}_{i} - \text{timestamp}_{i-1}$ matches the declared `timeframe`.
- **Session-Aware Gap Detection:** Gaps must be classified as:
  - *Expected Calendar Closure* (weekend, holiday, overnight exchange halt).
  - *Unexpected Missing Data* (feed drop, vendor gap, missing file).
- **Daylight Saving Time (DST) Invariance:** UTC timestamps must not jump by $\pm 1$ hour during spring/autumn clock shifts.

### 8.3 OHLC Structural Sanity Checks
- Structural bounding invariants must hold for every individual bar:
  $$\text{high} \ge \max(\text{open}, \text{close})$$
  $$\text{low} \le \min(\text{open}, \text{close})$$
  $$\text{high} \ge \text{low}$$
- Numerical validity: All price fields must be strictly finite (no `NaN`, `+Inf`, `-Inf`).
- Economic validity: Prices must be strictly positive ($P > 0.0$) for all conventional asset classes. (Negative commodity price exceptions, such as WTI April 2020, require explicit human parameterization).

### 8.4 Volume Semantics & Boundary Checks
- Non-negativity: $\text{volume} \ge 0.0$.
- Finitude: No `NaN` or infinite volume values.
- Zero-volume behavior: Check frequency of zero-volume bars. Distinguish illiquid market conditions from data drops.

### 8.5 Duplicate & Replay Detection
- Identify duplicate timestamps ($\text{timestamp}_{i} == \text{timestamp}_{i-1}$).
- Categorize duplicates into:
  1. *Exact Duplicates:* Identical OHLCV and metadata (duplicate row error).
  2. *Conflicting Duplicates:* Identical timestamp with differing OHLCV values (critical data corruption error).
- Any presence of conflicting duplicates triggers immediate fail-closed quarantine.

### 8.6 Missing Data & Gap Analysis
- Output complete statistical summary:
  - Total expected intervals given the market calendar.
  - Total observed bars.
  - Total missing intervals.
  - Distribution of gap lengths (longest single gap, gap clusters).
- **Zero Silent Imputation:** The qualification engine must **NEVER** silently interpolate or forward-fill missing bars. Forward-filling or synthetic bar generation changes empirical distributions and creates false trading opportunities. Any imputation requires explicit pre-empirical research authorization.

### 8.7 Price Discontinuities & Outlier Auditing
- Flag, but do not automatically delete, extreme price jumps:
  $$|r_t| = \left|\ln\left(\frac{\text{close}_t}{\text{close}_{t-1}}\right)\right| > \kappa_{\text{outlier}}$$
- Identify stale repeated bars (e.g. flatlined price across 50 consecutive M1 bars during active trading hours).
- Identify abnormal bar ranges ($\text{high}_t - \text{low}_t > 10 \times \text{ATR}$).
- *Principle:* Genuine market dislocations (flash crashes, macro shocks) must not be silently scrubbed as errors. Outlier flags are recorded in the manifest for researcher inspection.

### 8.8 Provenance Traceability
- Every qualified dataset row must be deterministically traceable back to its raw source archive chunk via line index and source file SHA-256.

---

## 9. Market-Specific Qualification Requirements

Different asset classes possess unique microstructure characteristics that require dedicated qualification checks:

### 9.1 Crypto Assets
- **Continuous Calendar:** Ingestion must verify 24/7/365 coverage without weekend gaps.
- **Maintenance Windows:** Account for recorded exchange downtime/scheduled maintenance (e.g. historical exchange upgrade freezes).
- **Funding & Basis Data:** If perpetual swap data is ingested, funding rate series and open interest must be qualified as separate synchronous or timestamped channels.
- **Fragmented Liquidity:** Multi-venue crypto requires documenting whether pricing is venue-specific (e.g., Binance spot) or a composite index (e.g., CME CF Benchmark).

### 9.2 Foreign Exchange (FX)
- **OTC Nature:** Explicitly record provider identity; no single global order book exists.
- **Weekend Roll Boundaries:** Verify Friday 5:00 PM EST market close to Sunday 5:00 PM EST open. Do not flag weekend closure as a missing data defect.
- **Bid/Ask vs. Midpoint:** The dataset must state whether bars represent Midpoint, Bid, or Ask prices. If only Midpoint is provided, spread costs cannot be directly observed from OHLC.
- **Tick Volume Semantics:** Document that FX volume almost universally represents provider quote update counts rather than transacted money.

### 9.3 Equities / ETFs
- **Calendar & Trading Hours:** Verify regular trading hours (09:30 - 16:00 US Eastern) vs. extended-hours trading.
- **Corporate Action Adjustments:**
  - Verify whether historical series are raw unadjusted or adjusted for splits/dividends.
  - Require explicit point-in-time adjustment factors.
  - Adjusted series alter historical prices; raw prices are required to compute true transaction frictions and execution realism.
- **Survivorship Bias Audit:** Cross-sectional universes must document the historical point-in-time constituent list. Using current S&P 500 constituents historically is strictly prohibited.

### 9.4 Equity Index & Commodity Futures
- **Contract Identification:** Individual contract data must record contract code, delivery month, and expiration date.
- **Continuous Contract Methodology:**
  - If a continuous series is provided, the exact roll rule must be mathematically defined:
    - Fixed-day roll (e.g. $N$ days prior to expiration).
    - Liquidity/Volume roll (date when forward contract volume exceeds active contract).
    - Open Interest roll.
  - Back-adjustment methodology must be declared:
    - *Panama Canal (Difference adjustment)* — shifts price level; can cause negative historical prices.
    - *Ratio / Proportional adjustment* — preserves percentage returns; alters historical nominal tick sizes.
    - *Unadjusted stitched* — preserves absolute prices; introduces artificial price jumps at roll boundaries.
- **Multiplier & Tick Semantics:** Futures data must document point value multiplier (e.g., \$50 per index point for ES) and minimum price increment (\$0.25).

### 9.5 Fixed Income & Rates
- **Instrument Semantics:** Explicitly record whether data is a Treasury constant-maturity yield (e.g. FRED DGS10 in percent per annum), a Treasury bond ETF (`TLT`, `IEF`), or a Treasury futures contract (`ZN`, `ZB`).
- **Yield-Price Inversion:** Fixed income yields move inversely to bond prices. Research signals based on yield data must account for bond duration and convexity.

---

## 10. Conceptual Data Qualification Report Schema

Every qualification run generates a persistent JSON report structured as follows:

```json
{
  "qualification_report_id": "QR-20260913-BTC-M1-001",
  "dataset_id": "DS-CRYPTO-BINANCE-BTCUSDT-M1-RAW",
  "dataset_version": "v1.0.0",
  "source_provider": "Binance_Public_Archive",
  "instrument": "BTC",
  "symbol_canonical": "BTC-USDT",
  "timeframe": "M1",
  "coverage_start_utc": "2022-01-01T00:00:00Z",
  "coverage_end_utc": "2025-12-31T23:59:00Z",
  "raw_file_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "normalized_file_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
  "qualification_timestamp_utc": "2026-09-13T06:00:00Z",
  "qualification_engine_version": "qual_engine_v1.0.0",
  "metrics": {
    "total_bars_evaluated": 2102400,
    "valid_bars": 2102380,
    "exact_duplicates": 0,
    "conflicting_duplicates": 0,
    "structural_ohlc_errors": 0,
    "timestamp_monotonicity_errors": 0,
    "unexpected_missing_intervals": 20,
    "expected_calendar_closures": 0,
    "longest_gap_minutes": 12,
    "zero_volume_bar_count": 45,
    "outlier_return_flag_count": 8,
    "stale_price_bar_count": 14
  },
  "market_specific_checks": {
    "continuous_trading_compliance": "PASS",
    "timezone_normalization": "PASS",
    "corporate_action_audit": "NOT_APPLICABLE",
    "roll_continuity_audit": "NOT_APPLICABLE"
  },
  "provenance_traceability": "VERIFIED_100_PERCENT",
  "qualification_verdict": "QUALIFIED_WITH_LIMITATIONS",
  "rejection_reasons": [],
  "known_limitations": [
    "20 missing M1 intervals detected across 2 exchange maintenance events on 2023-03-24 and 2024-08-11.",
    "Zero-fill or interpolation NOT applied; raw gaps preserved in dataset."
  ]
}
```

### Qualification Verdict Classes
1. **`QUALIFIED`:** 100% of identity, temporal, structural, and provenance checks pass. Zero missing intervals outside documented exchange closures.
2. **`QUALIFIED_WITH_LIMITATIONS`:** Data passes all structural and integrity checks; minor documented limitations exist (e.g. isolated maintenance gaps) that do not compromise research validity.
3. **`QUARANTINED`:** Data contains unresolved anomalies, conflicting duplicates, or unexplained gaps. Isolated from research use until resolved.
4. **`REJECTED`:** Critical contract failures (e.g. inverted OHLC, unparseable timestamps, unknown timezone, corporate action leakage). Permanently disqualified.

> [!NOTE]
> `QUALIFIED` or `QUALIFIED_WITH_LIMITATIONS` status certifies data integrity **only**. It does **not** authorize trading, paper execution, or hypothesis validation.

---

## 11. Dataset Versioning & Freeze Contract

To prevent data snooping, post-hoc cherry-picking, and irreproducible backtests, empirical quantitative research must bind to an immutable **Dataset Freeze**:

```text
EMPIRICAL RESEARCH RUN
  └── BOUND TO:
        ├── Dataset UUID
        ├── Dataset Version (e.g., 'DS-BTC-M1-v1.0')
        ├── Normalized Data SHA-256 Digest
        ├── Raw Source Artifact SHA-256 Digest
        ├── Normalizer Git Commit Hash
        ├── Qualification Report Hash
        └── Temporal Boundary Bounds [Start_UTC, End_UTC]
```

### Invariants for Research Freezes
1. **Hash Immutability:** If a dataset file is regenerated, corrected, or updated, it receives a **new** Dataset ID and version. The original dataset version and hash must never be modified or overwritten in place.
2. **No Silent Re-pulls:** Code must not query dynamic vendor endpoints during backtesting. All backtest inputs must read exclusively from a frozen, local, hashed research archive.
3. **Point-in-Time OOS Isolation:** The dataset freeze protocol enables splitting data into Train, Validation, and Out-of-Sample (OOS) partitions prior to parameter exploration. Once the freeze is executed, the OOS partition must remain sealed until final evaluation.

---

## 12. Storage & Hardware Architecture Planning (Homelab Context)

The ACASH homelab operates in a resource-constrained environment. Loading multi-year M1 bar data across multiple assets simultaneously into memory should be avoided in favor of streaming, chunked, or partitioned access.

### 12.1 Format Evaluation: Parquet vs. DuckDB (Proposal)

| Evaluation Dimension | Apache Parquet (Storage) | DuckDB (Analytical Engine) |
| :--- | :--- | :--- |
| **Storage Paradigm** | Columnar binary format with snappy/zstd compression. | In-process vectorized analytical SQL / OLAP database. |
| **Compression Ratio** | High (illustrative: substantial storage footprint reduction vs. raw CSV). | High; supports direct zero-copy querying of Parquet files. |
| **Memory Footprint** | Low when scanned in row-groups or partitions. | Low RAM overhead; operates out-of-core with spill-to-disk. |
| **Predicate Pushdown** | Supported natively (filters on timestamp/symbol read only required pages). | Executes vectorized SQL queries directly over partitioned Parquet files. |
| **Operational Overhead** | Zero daemon processes; pure static filesystem files. | Embedded engine (library import); zero background services. |
| **Recommendation** | **CANDIDATE STORAGE FORMAT (NON-CANONICAL PROPOSAL)** | **CANDIDATE QUERY ENGINE (NON-CANONICAL PROPOSAL)** |

### 12.2 Partitioning & Storage Strategy (Proposal)
- **Directory Structure:**
  ```text
  /data/research/historical/
    ├── raw/
    │   └── crypto/binance/BTCUSDT/
    │       └── 2024-01-01_BTCUSDT_M1.csv.gz (Read-only source archive + SHA256)
    └── normalized/
        └── parquet/
            └── asset_class=crypto/
                └── symbol=BTC-USDT/
                    └── timeframe=M1/
                        ├── year=2022/part-0.parquet
                        ├── year=2023/part-0.parquet
                        ├── year=2024/part-0.parquet
                        └── year=2025/part-0.parquet
  ```
- **Chunking & Row-Group Sizing:** Partition by `year` or `year-month` to ensure individual Parquet files remain manageably sized (e.g. illustrative planning target of ~20–100MB partitions), facilitating scans on resource-constrained hardware.

---

## 13. Fail-Closed Error Boundaries

The historical data pipeline enforces the project-wide **Fail-Closed Contract** (`AGENTS.md`):

1. **Unknown Timezone Semantics:** If a vendor dataset does not explicitly certify UTC or exchange local timezone rules, the normalizer must raise `DataContractError`. It must **never** assume UTC.
2. **Ambiguous Adjustment State:** If equity/ETF prices cannot be proven to be pure unadjusted or explicitly adjusted via known factors, raise `DataContractError`. Never assume prices are raw.
3. **Unspecified Roll Construction:** If a futures series lacks an authoritative roll schedule or back-adjustment manifest, it is blocked from canonical research use.
4. **Missing Checksums:** If a raw artifact lacks a verifiable SHA-256 digest matching its acquisition manifest, ingestion terminates immediately.

---

## 14. Open Decisions Register (Data Foundation)

The following decisions represent unresolved open surfaces requiring human research prioritization or ratification prior to empirical ingestion. All listed candidate options are **illustrative and non-exhaustive**:

| Decision ID | Decision Description | Rationale | Candidate Options (Illustrative, Non-Exhaustive) | Status | Human Ratification Required? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DATA-DEC-001** | Initial BTC Historical Market Data Provider | Select authoritative primary source for historical BTC M1 research data. | Binance Public Archives, DoltHub, Kraken Public API, Commercial Vendor. | **UNRESOLVED** | **YES** |
| **DATA-DEC-002** | Target Historical Coverage Span for Crypto | Define planning research span for initial exploratory studies. | 1 Year vs. 2 Years vs. 4 Years. | **UNRESOLVED** | **YES** |
| **DATA-DEC-003** | Parquet Partitioning & Compression Standard | Evaluate compression algorithm and directory partitioning schema. | Snappy vs. ZSTD; Year vs. Year-Month partitions. | **UNRESOLVED** | **YES** |
| **DATA-DEC-004** | Historical Data Retention & Storage Policy | Define retention tiers across hot, warm, and cold storage on homelab. | Keep all raw archives on homelab vs. external NAS / object storage. | **UNRESOLVED** | **YES** |
| **DATA-DEC-005** | FX Reference Data Provider Authority | Select reference data source for EURUSD tick/M1 data. | TrueFX, Dukascopy, Interactive Brokers, HistData. | **UNRESOLVED** | **YES** |
| **DATA-DEC-006** | Equity Index Futures (`ES`) Data Authority | Determine commercial licensing vs. proxy data source for continuous ES. | Licensed CME data, Interactive Brokers historical API, ETF proxy (`SPY`). | **UNRESOLVED** | **YES** |
| **DATA-DEC-007** | Gold (`XAU`) Pricing Representation | Identify research proxy for gold. | Spot XAUUSD (OTC), COMEX Gold Futures (`GC`), ETF proxy (`GLD`). | **UNRESOLVED** | **YES** |
| **DATA-DEC-008** | Continuous Futures Roll & Adjustment Policy | Define roll and adjustment policy per instrument and provider rather than as a single universal default, reflecting contract differences. | Volume rollover with Panama difference adjustment, Open interest rollover, Ratio adjustment, Unadjusted stitched. | **UNRESOLVED** | **YES** |

---

## 15. Governance Verification Ledger

- **Implementation Status:** DOCUMENTATION & RESEARCH-DATA DESIGN ONLY (NO CODE MUTATIONS).
- **Data Acquisition Status:** ZERO DATA DOWNLOADED.
- **Contract Enforcement:** STRICT FAIL-CLOSED SPECIFIED.
- **HYP_003 Creation:** ABSENT / NOT CREATED.
- **Backtest / Empirical Execution:** STRICTLY PROHIBITED / NONE EXECUTED.
- **Active G7 Soak Interaction:** ZERO TOUCH / 100% UNTOUCHED.
- **Canonical Capital:** $0.00 (`NO_REAL_ORDERS=true`).
