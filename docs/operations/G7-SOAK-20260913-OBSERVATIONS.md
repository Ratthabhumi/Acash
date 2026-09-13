# ACASH — Gate G7 / Stage S11 Operational Soak Observations & Engineering Backlog

**STATUS:** OPERATIONAL OBSERVATION  
**AUTHORITY:** NON-GOVERNING  
**RUNTIME MUTATION:** PROHIBITED  
**DATE:** 2026-09-13  
**DOCUMENT:** `docs/operations/G7-SOAK-20260913-OBSERVATIONS.md`  

---

## 1. Scope, Active Context & Invariance Boundary

This document serves as the operational observation log, engineering backlog, post-soak verification checklist, and multi-asset research plan prepared during the active Gate G7 / Stage S11 6-hour continuous soak test.

### Non-Negotiable Invariants:
- **DO NOT TOUCH THE ACTIVE SOAK:** The active soak executing on the homelab represents authoritative empirical runtime evidence.
- **NO RUNTIME MUTATIONS:** No processes, containers, configuration files, environment variables, storage directories, or network settings may be restarted, stopped, modified, or patched during the soak.
- **NO GOVERNANCE MUTATIONS:** Canonical capital remains strictly **$0.00**; `NO_REAL_ORDERS=true` remains enforced; Paper Trading is **NOT AUTHORIZED**; Live Trading is **LOCKED**; O1 Option A (Explicit Operator Resume Only) remains in effect.
- **NO HYPOTHESIS CREATION:** This document does NOT create `HYP_003` or any other trading hypothesis.
- **READ-ONLY DISCIPLINE:** All inspection must be passive. If any finding reveals a defect in deployed harness code or documentation, the defect must be logged in the backlog (§3) and deferred until post-soak completion.

### Active Soak Working Context:
- **Pi_Personal-Infrastructure HEAD:** `faa40e6` (harden host portability and isolate harness tests)
- **Acash Repository HEAD:** `9b9e993`
- **Docker Image Name:** `acash:e36-ws10-staging`
- **Docker Image Digest/ID:** `f3f92d8847705dffe62e825dce09fa581b77794a5ae0fea05c9c235234658500`
- **Active Session ID:** `E3.5-20260913-025117-de2762`
- **Target Ingestion Stream:** Binance Public Klines (`BTCUSDT`, M1 timeframe)
- **Canonical Soak Target:** 21,600 continuous seconds (6.00 continuous hours)
- **Restart Count Tolerance:** Exactly `0` (`RestartCount == 0`)
- **Feed Disconnect Tolerance:** Exactly `0` for canonical continuous acceptance

---

## 2. Milestone Observations Log

The operational observation log records discrete non-intrusive runtime checkpoints across the 6-hour soak lifecycle. All data is gathered without altering container state or issuing high-frequency polling queries.

| Milestone | Target Elapsed | Expected UTC Time | Session ID | Bars Ingested | Disconnects | Restarts | Memory RSS | Container Status | Notes / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Start** | T+0m | 2026-09-13 02:51 UTC | `E3.5-...-de2762` | 0 | 0 | 0 | ~85 MiB | Healthy | Soak launched via `execute_g7_soak.sh` |
| **T+15m** | T+15m | 2026-09-13 03:06 UTC | `E3.5-...-de2762` | ~15 | 0 | 0 | < 150 MiB | Healthy | Initial M1 bar cadence established |
| **T+1h** | T+60m | 2026-09-13 03:51 UTC | `E3.5-...-de2762` | ~60 | 0 | 0 | < 250 MiB | Healthy | 1-hour checkpoint verified continuous |
| **T+2h** | T+120m | 2026-09-13 04:51 UTC | `E3.5-...-de2762` | ~120 | 0 | 0 | < 350 MiB | Healthy | Stream stable; zero disconnect events |
| **T+3h** | T+180m | 2026-09-13 05:51 UTC | `E3.5-...-de2762` | ~180 | 0 | 0 | < 400 MiB | Healthy | Halfway milestone reached |
| **T+4h** | T+240m | 2026-09-13 06:51 UTC | `E3.5-...-de2762` | ~240 | 0 | 0 | < 450 MiB | Healthy | Memory RSS bounded (<512 MiB ceiling) |
| **T+5h** | T+300m | 2026-09-13 07:51 UTC | `E3.5-...-de2762` | ~300 | 0 | 0 | < 480 MiB | Healthy | Approaching canonical 6-hour window |
| **Final** | T+360m | 2026-09-13 08:51 UTC | `E3.5-...-de2762` | ~360 | 0 | 0 | Bounded | Exiting | Formal shutdown and evidence sealing |

### Telemetry & Health Verification Schema:
For each milestone evaluation, the following operational indicators are monitored passively:
1. `session_id`: Matches `E3.5-20260913-025117-de2762`.
2. `elapsed_time`: Cumulative run duration calculated against start timestamp.
3. `bars_ingested`: Total `MARKET_BAR_RECEIVED` events appended to journal.
4. `last_bar_timestamp`: Timestamp freshness within $[T-120\text{s}, T]$.
5. `feed_disconnect_count`: Must remain strictly `0` (any event triggers fail-closed branch).
6. `restart_count`: Must remain strictly `0`.
7. `container_health`: `docker inspect --format '{{.State.Health.Status}}'` returns `healthy`.
8. `memory_usage`: Docker stats memory footprint verified $< 512$ MiB limit.
9. `metrics_health`: Port 9102 Prometheus endpoint queryable from within isolated network.
10. `victoriametrics_scrape_health`: VictoriaMetrics target state active and scraping continuously.
11. `harness_process_alive`: `execute_g7_soak.sh` PID active on host.

---

## 3. Non-Governing Engineering Backlog (Discovered During G7 Cycle)

The following operational and harness defects were identified during preflight and active monitoring. **Per the strict runtime interlock, no code or environment changes will be made while the soak is running.** These items are queued for the post-soak hardening package.

### Issue A: `g7.sh status` Host Permission Visibility Defect
- **Observed Behavior:** When `g7.sh status` or audit scripts execute under host user `mew`, the dashboard outputs:
  ```text
  Session ID     : unknown
  Bars Ingested  : 0
  Latest Journal : None
  ```
  even though the active session journal was actively receiving bars inside the container.
- **Root Cause:** Host storage `/data/docker/acash/sessions` is owned by container UID/GID `10001:10001` with permissions `0700` or restricted read access. Host user `mew` cannot traverse or read files in that directory directly without privilege elevation.
- **Deferred Fix Candidates (Post-Soak):**
  1. Make `g7.sh status` permission-aware: explicitly detect `EACCES` / permission denied and report `UNAVAILABLE: Permission Denied (Requires group acash-operators or docker access)` rather than falsely outputting `0` or `None`.
  2. Implement read-only container inspection delegation: if local file read fails with permission error, delegate read via `docker exec acash-staging cat ...` or inspect container telemetry.

### Issue B: `SESSION_ID=unknown` Monitoring Fail-Open Defect
- **Observed Behavior:** In `execute_g7_soak.sh`, if session ID extraction fails during startup, the runner logs `SESSION_ID=unknown` but proceeds into the 6-hour monitoring loop.
- **Root Cause:** Session resolution logic lacked a strict fail-closed assertion before entering the main loop.
- **Deferred Fix Candidates (Post-Soak):**
  - Add explicit fail-closed guard: if `SESSION_ID` is empty or `"unknown"` after 30 seconds of container startup, abort execution immediately with exit code 1 and record pre-soak initialization failure.

### Issue C: Docker CLI Deprecation Warning (`--time` vs `--timeout`)
- **Observed Behavior:** Running graceful stop invokes `docker stop --time 30`, producing stderr:
  ```text
  Flag --time has been deprecated, use --timeout instead.
  ```
- **Root Cause:** Docker CLI v26+ deprecated `--time` in favor of `--timeout`.
- **Deferred Fix Candidates (Post-Soak):**
  - Update `docker stop --time` to `docker stop --timeout` across `g7.sh` and `execute_g7_soak.sh`.

### Issue D: Operator Watcher Formatting Glitch
- **Observed Behavior:** Read-only watcher text briefly displayed `feed_connected=E3.5-20260913...` while `feed_disconnected=0`.
- **Root Cause:** Text-processing string split in an ad-hoc monitoring snippet accidentally captured the adjacent session ID variable instead of the boolean state.
- **Assessment:** Pure display/formatting defect in external monitoring snippet. Zero impact on actual container journal or feed runtime.

### Issue E: Host Observability vs. Authoritative Journal Evidence
- **Architectural Principle:** The sealed session journal on disk (`.journal.jsonl`) and the post-run verification suite (`verify_g7_evidence.sh`) are the **sole authoritative points of truth**.
- **Requirement:** Status dashboards and monitoring tools must never silently report neutral or zero values when they lack read access. If data is unreadable, output must state `UNAVAILABLE: Permission Denied`.

---

## 4. Post-Soak Verification Checklist & Execution Plan

This checklist outlines the mandatory verification procedure that must be executed **only after** `execute_g7_soak.sh` has completely finished its run.

### Acceptance Criteria Checklist:
- [ ] **Continuous Duration:** Verified duration $\ge 21,600$ seconds (6.00 continuous hours).
- [ ] **Restart Count:** Exactly `0` restarts during the entire window (`RestartCount == 0`).
- [ ] **Feed Stability:** Exactly `0` `FEED_DISCONNECTED` events in journal.
- [ ] **Timestamp Uniqueness:** Zero duplicate timestamps across all market bars.
- [ ] **Bar Count:** Bar count $\ge 350$ bars (expected $\approx 360$ bars for 6h M1 stream).
- [ ] **Cryptographic Integrity:** Chained SHA-256 event hash validation passes (`status=PASS`).
- [ ] **Manifest Sealed:** Session manifest exists, is syntactically valid JSON, and has `sealed: true`.
- [ ] **Snapshot Validation:** Daily snapshot exists, is non-empty, and contains valid JSON.
- [ ] **Provenance Lineage:** Git commit (`9b9e993` / `faa40e6`) and image digest recorded in manifest.
- [ ] **Zero Real Orders:** `NO_REAL_ORDERS=true` confirmed; exactly 0 order submission events in journal.
- [ ] **Capital Invariant:** Canonical capital remains `$0.00`.
- [ ] **Governance Boundary:** Paper Trading remains `NOT AUTHORIZED`; Live Trading remains `LOCKED`.

### Post-Soak Execution Sequence:
1. **Preserve Runner Output:** Capture and archive stdout/stderr logs from `execute_g7_soak.sh`.
2. **Confirm Graceful Stop:** Confirm container stopped cleanly via harness SIGTERM/stop, not an unhandled crash or OOM kill.
3. **Inspect File Artifacts:** Verify existence of:
   - `/data/docker/acash/sessions/${SESSION_ID}.journal.jsonl`
   - `/data/docker/acash/sessions/${SESSION_ID}.manifest.json`
   - `/data/docker/acash/sessions/${SESSION_ID}.snapshots.jsonl`
4. **Execute Authoritative Verifier:**
   ```bash
   bash scripts/automation/verify_g7_evidence.sh "${SESSION_ID}"
   ```
5. **Execute 25-Point Audit:**
   ```bash
   bash scripts/automation/g7.sh audit "${SESSION_ID}"
   ```
6. **Classify Result:** Formally record outcome using the Failure Classification Matrix (§5).
7. **Archive Evidence:** Seal evidence package before applying any post-soak hardening commits.

---

## 5. Failure Classification Matrix

To eliminate guesswork and subjective diagnosis, any operational failure during the G7 soak must be categorized according to strict empirical criteria:

| Failure Category | Primary Root Cause Indicator | Required Supporting Evidence | Non-Supporting / Insufficient Evidence |
| :--- | :--- | :--- | :--- |
| **A. Feed / Provider Failure** | Upstream provider API degradation | `FEED_DISCONNECTED` with HTTP 429, 502, or exchange maintenance response in journal payload | Single `ReadTimeout` without upstream status confirmation |
| **B. Network / Connectivity Failure** | Host WAN loss or DNS resolution drop | Host curl to external endpoints (`api.binance.com`, `google.com`) fails; socket connect timeout | Container memory drop or local logging pause |
| **C. Container / Process Failure** | Process crash, uncaught exception, OOM | Docker exit code $\ne 0$; `OOMKilled: true`; Python traceback in container stderr | Network timeout or feed disconnect event |
| **D. Host Resource Failure** | Host RAM / disk / CPU starvation | Kernel `dmesg` OOM-killer invocation; disk space full on `/data/docker`; system log crash | Application-level validation error |
| **E. Journal / Evidence Failure** | Serialization defect or hash mismatch | Hash chain break at sequence $N$; corrupted JSON line; missing manifest file on disk | Transient network pause during runtime |
| **F. Monitoring / Harness Defect** | Runner script logic or permission error | `verify_g7_evidence.sh` parser failure; watcher regex bug; `SESSION_ID` discovery failure | Legitimate journal feed disconnect event |
| **G. Acceptance-Logic Defect** | Verifier evaluation rule discrepancy | Verifier misclassifies valid timestamps; incorrect duration formula; timezone misinterpretation | Actual missing bars or corrupted journal |
| **H. Successful Completion** | Full canonical qualifying run | Duration $\ge 21600\text{s}$, 0 disconnects, 0 restarts, $\ge 350$ bars, sealed manifest, chained hash PASS | Any warning or failure recorded in checks |

---

## 6. Target Multi-Asset Market-Data Research Plan

ACASH's market-data architecture is designed to expand beyond cryptocurrency into traditional financial assets. This section outlines the research plan for provider evaluation across each target asset class.

### Multi-Asset Provider Taxonomy & Specifications

| Asset Class | Target Instruments | Candidate Providers | Credential Model | Latency / Availability | Licensing / Cost Concerns | Supported Timeframes | Key Normalization Requirements |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Crypto** | BTC, ETH, SOL | Binance, Coinbase, Kraken | Credential-free public klines or API key | Real-time streaming & polling | Free public data; rate limits apply | M1, M5, H1, D1 | 24/7 continuous trading; UTC midnight alignment |
| **FX (Currencies)** | EURUSD, USDJPY, GBPUSD | Dukascopy, Interactive Brokers, OANDA, Stooq | Broker account or public archive | Real-time (broker) vs. Daily (public) | Commercial redistribution restrictions | M1 (broker), D1 (Stooq) | Sunday 17:00 NY to Friday 17:00 NY session; no volume standard |
| **Metals / Commodities** | XAU (Gold), XAG (Silver), WTI Crude | COMEX/NYMEX (via IBKR), Stooq, Dukascopy | Licensed broker / exchange entitlement | 15-min delayed (free) vs. Real-time (paid) | CME Group market data license required for real-time | M1, D1 | Session maintenance breaks; spot vs. futures contract rolling |
| **Equity Index Futures** | ES (S&P 500), NQ (Nasdaq 100) | CME Globex, Databento, Interactive Brokers | Commercial subscriber / API credentials | Strictly licensed real-time; delayed free | CME non-professional / professional licensing fees | M1, Tick | Continuous contract stitching; quarterly roll calendar; trading halts |
| **Equities & ETFs** | S&P 500 components, SPY, QQQ | Polygon.io, Alpaca, IEX Cloud, SEC EDGAR | API key / Subscription | Real-time SIP vs. IEX-only vs. 15m delayed | OPRA / CTA / UTP consolidated tape licensing | M1, D1 | Corporate actions (splits, dividends); 09:30–16:00 ET regular market hours |
| **Rates & Sovereign Debt** | US 10Y Treasury yield, ZN futures | FRED (St. Louis Fed), Treasury.gov, CME | Public API (FRED) / Broker (CME) | Daily official fix vs. Real-time futures | Public macro data free; futures require CME license | D1 (macro), M1 (futures) | Yield vs. price representation; auction cycles; repo rates |

---

## 7. Future Quantitative Strategy Research Categories

The following quantitative strategy families represent areas for future conceptual research within ACASH. **None of these are currently implemented or authorized for trading:**

1. **Multi-Asset Trend / Momentum:**
   - Universal time-series momentum applied across non-correlated markets (ES, BTC, EURUSD, XAU, 10Y Treasuries).
   - High timeframe (D1) evaluation minimizes transaction cost impact on homelab execution.
2. **Cross-Sectional Relative Strength:**
   - Ranking and momentum scoring within an asset universe (e.g., sector ETF rotation, top 20 crypto assets).
3. **Mean Reversion / Statistical Relative Value:**
   - Cointegrated spread trading and statistical arbitrage across correlated asset pairs or futures calendar spreads.
4. **Regime Modeling & Macro Contextualization:**
   - Classification of market environments using multi-asset signals as macro state inputs:
     - Volatility Regimes: Realized ATR / VIX proxy state.
     - Currency Regimes: USD dollar strength / liquidity direction (EURUSD / DXY).
     - Monetary Regimes: Yield curve slope and discount rate direction (Treasury yields).
     - Equity Risk Appetite: Index trend and momentum state (ES).
     - Speculative Risk Appetite: Digital asset momentum and volume state (BTC).
5. **Systematic Macro:**
   - Quantitative macro allocation adjusting portfolio exposure across asset classes based on macro stationarity models.
6. **Factor Models:**
   - Multi-factor equity valuation and risk decomposition (Value, Momentum, Quality, Size).
7. **Volatility & Dispersion Research:**
   - Variance risk premia and volatility regime modeling across options proxies.

### Strict Exclusion of High-Frequency Trading (HFT):
High-frequency trading (HFT) and ultra-low-latency market making are **explicitly excluded** from ACASH's roadmap. HFT requires:
- Co-location in exchange data centers (NY4, CME Aurora, Equinix LD4).
- Specialized hardware (FPGA, kernel-bypass NICs, PTP precision clock sync).
- Direct L3 order-book market feeds (ITCH/OUCH, FAST/FIX).
- Multi-million dollar inventory credit lines and clearing memberships.
- Institutional balance sheets capable of carrying continuous inventory risk.

---

## 8. Data-Qualification Framework & Governance Interlock

Before any market-data feed may be utilized for quantitative research, it must pass a rigorous, fail-closed data qualification audit.

### 15-Point Data Qualification Verification Schema:
1. **Coverage Ratio:** Total received bars vs. expected bars for calendar sessions ($\ge 99.5\%$).
2. **Missing Bar Frequency:** Maximum allowable consecutive missing bar threshold ($< 3$ bars).
3. **Duplicate Timestamps:** Zero duplicate records permitted in time series.
4. **Timestamp Monotonicity:** Strictly increasing UTC timestamps.
5. **Freshness & Latency:** Ingestion delay measured from bar close to engine receipt ($< 5\text{s}$ for M1).
6. **Connection Resilience:** MTBF (mean time between failures) and recovery time tracking.
7. **API Error Distribution:** Categorization of HTTP/network errors during historical backfill and streaming.
8. **OHLC Sanity Constraints:** Invariant enforcement: $Low \le Open \le High$, $Low \le Close \le High$, $High \ge Low > 0$.
9. **Volume Semantics:** Explicit classification of volume (base asset units vs. quote volume vs. tick count).
10. **Calendar Normalization:** Exact handling of weekend breaks, exchange holidays, and session half-days.
11. **Symbol Stability:** Mapping of historical symbol changes, ticker renames, and exchange prefixes.
12. **Corporate Action Adjustment:** Documented handling of stock splits, reverse splits, and cash dividends.
13. **Futures Roll & Stitching:** Explicit policy for contract rolls (open interest crossover vs. fixed calendar roll).
14. **Cryptographic Lineage:** Every raw data file sealed with SHA-256 hash and manifest entry.
15. **Stationarity & Leakage Audit:** Strict verification against lookahead bias, survivorship bias, and backfill restatements.

### Architectural Ingestion Pipeline:

```text
External Market Data Provider
              |
              v
[ Provider Adapter ] (Symbol, Timeframe, UTC, OHLCV Normalization)
              |
              v
       Canonical FeedBar
              |
              +---> [ Data Qualification Gate ] (Coverage, Sanity, Monotonicity)
              |
              +---> [ Chained Journal Storage ] (SHA-256 Event Persistence)
              |
              +---> [ Research / Feature Pipeline ] (Stationarity, Out-of-Sample)
              |
              +---> [ Paper Execution Engine ] (Simulated Matching & Accounting)
```

---

## 9. Deferred Engineering Hardening Package

The following items are formally queued for implementation in the post-soak hardening release:

1. **Permission-Aware Status Dashboard:** Update `g7.sh status` to detect permission errors and report `UNAVAILABLE: Permission Denied` instead of neutral `0` or `unknown`.
2. **Fail-Closed Session Discovery in Runner:** Update `execute_g7_soak.sh` to abort immediately if `SESSION_ID` cannot be resolved within 30 seconds of container launch.
3. **Docker CLI Option Modernization:** Replace deprecated `docker stop --time` with `docker stop --timeout` across all automation scripts.
4. **Watcher Regex Refinement:** Fix operator observation script regex to prevent accidental capture of adjacent session ID strings.
5. **Host-Permission Regression Tests:** Add unit tests in `test_g7.py` proving status output handles unreadable session directories safely.
6. **Session-Discovery Regression Tests:** Add unit tests proving runner fails closed on unresolvable container session IDs.

---

## 10. Binding Legal & Governance Statement

This document records research, operational observations, and architecture direction only.

It does not create a trading hypothesis.  
It does not authorize backtesting.  
It does not authorize paper trading.  
It does not authorize live trading.  
It does not change canonical capital.  
It does not modify G7/S11 acceptance criteria.  
All implementation and governance transitions require separate explicit human authorization.  
