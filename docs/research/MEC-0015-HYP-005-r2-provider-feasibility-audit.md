# MEC-0015 / HYP_005: Post-R1 Provider Coverage Feasibility Audit

```text
[GOVERNANCE AUDIT ARTIFACT: PROVIDER COVERAGE FEASIBILITY AUDIT]
[GENERATED: 2026-09-21]
[CANONICAL STARTING HEAD: 333af02424349bfb43ec05c7afc96ca960f6d5d7]
[HYP_005_STATUS: CREATED_AND_SEALED_R1]
[R2_DATASET_BUILD: LOCKED / BLOCKED]
[R3_REPLICATION: LOCKED]
[M1_WINDOW: 2007-05-01 THROUGH 2024-04-30 (FROZEN)]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
[PAPER: NOT_AUTHORIZED | LIVE: LOCKED]
[STRATEGY_BACKTEST: NOT_STARTED | STRATEGY_PNL: NOT_COMPUTED]
```

- **Document ID:** `docs/research/MEC-0015-HYP-005-r2-provider-feasibility-audit.md`
- **Subject:** Pre-R2 audit of historical data provider coverage for `HYP_005` across the full preregistered M1 replication sample (`2007-05-01` through `2024-04-30`).
- **Governing Standard:** ACASH `AGENTS.md` (Zero Unverified Claims, Single Canonical Authority, Strict Fail-Closed).
- **Audit Mandate:** Provider feasibility research only. Zero strategy data downloaded, zero backtest executed, zero strategy P&L computed, zero mutation to original sealed R1 artifacts.

---

## 1. Executive Summary & Coverage Conflict Declaration

### 1.1 The Coverage Conflict
`HYP_005` formally sealed its replication window as:
```text
M1_START = 2007-05-01
M1_END   = 2024-04-30
M1_ROLE  = PUBLICATION_EXPOSED_REPLICATION_SAMPLE
```
The original pre-inception contracts named **Alpaca Historical SIP** as the primary market data provider.

However, authoritative Alpaca provider documentation confirms:
> **Alpaca Historical US Equities data begins on 2016-01-01.**
> Requests for bars, quotes, or trades prior to 2016 return empty datasets (`alpaca.markets/support/alpaca-data-timeline`).

Therefore:
- **Coverage Deficit:** Alpaca lacks coverage for the first **8 years and 8 months** (2007-05-01 through 2015-12-31) of the 17-year M1 replication sample.
- **Feasibility Classification:**
  ```text
  ALPACA_FULL_M1_COVERAGE = NOT_AVAILABLE
  R2_PROVIDER_FEASIBILITY = BLOCKED
  ```

### 1.2 Non-Negotiable Governance Invariants
1. **Zero Sample Truncation:** We do **NOT** shorten M1 to begin in 2016. That would constitute post-hoc hypothesis surgery and an unprincipled alteration of the replication sample.
2. **Zero Piecemeal Download:** We do **NOT** download 2016–2024 data to "peek" at recent results before solving provider lineage for the full period.
3. **Immutability of Sealed R1:** Sealed R1 artifacts (`docs/phase14/hypotheses/HYP_005.json`, `docs/phase14/manifests/manifest_r1_HYP_005.json`, `docs/research/MEC-0015-HYP-005-strategy-preregistration.md`) remain untouched. Any remediation must be recorded via an additive amendment record (`HYP_005_R1_PROVIDER_AMENDMENT_001`).

---

## 2. Required Data Types for Full HYP_005 M1 Execution

To execute the preregistered `HYP_005` strategy without compromising scientific fidelity, a provider solution must supply three distinct data streams for SPY across `2007-05-01` through `2024-04-30`:

### A. 1-Minute SPY OHLCV Bars
- **Window:** `2007-05-01` through `2024-04-30`.
- **Required Fields:** `Open`, `High`, `Low`, `Close`, `Volume`.
- **Timestamp Semantics:** Unambiguous left-edge or right-edge labeling that maps deterministically to regular trading sessions (`09:30:00` to `16:00:00` America/New_York; 390 standard bars/day).
- **VWAP Derivation:** Must support independent Typical Price $(H+L+C)/3$ volume-weighted accumulation.

### B. Consolidated Top-of-Book Quotes (NBBO)
- **Window:** `2007-05-01` through `2024-04-30`.
- **Role:** Required to execute the preregistered fill rule:
  $$\text{FIRST\_VALID\_SIP\_NBBO\_AT\_OR\_AFTER\_EXECUTION\_BOUNDARY}$$
- **Required Fields:** `bid`, `ask`, `timestamp` (sub-second / nanosecond precision), `bid_size`, `ask_size`.
- **Market Coverage:** Consolidated US equity tape (CTA/UTP SIP top-of-book).

### C. Cash Dividends
- **Window:** Comprehensive historical coverage identifying every cash-dividend ex-date affecting `2007-05-01` through `2024-04-30`.
- **Role:** Required for cash-dividend gap adjustment:
  $$\text{prev\_close\_adjusted} = \text{previous\_regular\_close} - \text{current\_day\_cash\_dividend}$$
- **Required Fields:** `symbol`, `ex_date`, `cash_amount`, `record_date`, `pay_date`.

---

## 3. Candidate Provider Feasibility Analysis

### 3.1 Provider A: Alpaca (Historical SIP)
- **1-Minute OHLCV:** Available from `2016-01-01` to present. Pre-2016 returns empty.
- **NBBO Quotes:** Available from `2016-01-01` to present.
- **Dividends:** Available via corporate actions snapshot, but coverage prior to 2016 is unverified and point-in-time vintage is not guaranteed.
- **Delivery:** REST API.
- **Cost / Subscription:** Existing ACASH integration.
- **Classification:** `ALPACA_ROLE = PARTIAL_M1_ONLY` (Covers 2016–2024; fails 2007–2015).
- **Assessment:** Cannot alone satisfy full M1. Remains valuable for cross-provider validation during the 2016–2024 overlap window.

### 3.2 Provider B: DTN IQFeed
- **1-Minute OHLCV:** 1-minute historical bars for US equities date back to May 2007 (covers approximately 17 years).
- **Tick / NBBO Quotes:** Standard service provides only **180 calendar days** of historical tick/quote data. Historical tick archives prior to 180 days are not accessible via standard subscription.
- **Dividends:** Limited reference data capabilities; not a canonical corporate actions provider.
- **Delivery:** Local client daemon / TCP socket protocol.
- **Cost / Subscription:** Base feed ~$175+/month + exchange fees.
- **Classification:** `IQFEED_FULL_M1_NBBO = NOT_AVAILABLE_STANDARD_SERVICE`.
- **Assessment:** While IQFeed can supply 1-minute bars back to 2007, its lack of historical NBBO quotes violates the `HYP_005` execution-fill contract. Infeasible as a primary provider.

### 3.3 Provider C: Polygon.io (Massive)
- **1-Minute OHLCV:** US Stocks SIP minute aggregates flat files date back to **September 10, 2003** (covers full M1 window 2007–2024).
- **NBBO Quotes:** US Stocks SIP top-of-book quote flat files (`us_stocks_sip/quotes_v1`) date back to **September 10, 2003**, with complete daily files available throughout 2007–2024. Contains nanosecond-timestamped bid/ask quotes from the consolidated SIP.
- **Dividends:** REST API Reference endpoint `/v3/reference/dividends` covers US equity distributions. However, public user reports note occasional gaps in historical dividend coverage. Polygon's dividend coverage for SPY 2007–2024 requires formal pre-qualification against official SPDR/SSGA records.
- **Delivery:** Bulk flat files via S3-compatible endpoints / web browser, plus REST API.
- **Cost / Subscription:**
  - Stocks Developer: ~$79/month (10 years history; insufficient for 2007).
  - Stocks Advanced: ~$199/month (20+ years history, flat files, tick/quote access).
- **Classification:** `POLYGON_FULL_M1_CANDIDATE = UNDER_AUDIT / STRONG_SINGLE_PROVIDER_CANDIDATE`.
- **Assessment:** Polygon is the only audited provider capable of delivering both 1-minute SIP bars and nanosecond NBBO quotes for the complete 2007–2024 horizon.

---

## 4. Single-Provider vs. Hybrid-Provider Architecture

### 4.1 Single-Provider Preference
The ACASH engineering standard strictly prefers a **single unified provider** supplying all required data streams for the entire M1 period.

**Rationale:**
1. Preserves consistent bar construction and trade inclusion rules.
2. Eliminates artificial regime breaks at data splicing boundaries.
3. Unifies timestamp resolution and tick aggregation semantics.

### 4.2 Hybrid-Provider Risks (Material)
If a hybrid architecture (e.g. Polygon for 2007–2015 + Alpaca for 2016–2024) were adopted, it introduces material econometric and operational risks:
- **Bar Construction Divergence:** Differences in exchange inclusion, volume weighting, and odd-lot filtering.
- **Timestamp Offsets:** Discrepancies between Alpaca left-edge 1m aggregation and Polygon interval definitions.
- **Quote Consolidation Disparities:** Microsecond vs. nanosecond timestamp alignment at decision boundaries.
- **Splicing Regime Break:** Risk of generating an artificial jump in strategy volatility or P&L around the 2016-01-01 splice point.

**Classification:**
```text
HYBRID_PROVIDER_REGIME_BREAK_RISK = MATERIAL
```
*Rule:* A hybrid solution may only be entertained if single-provider qualification fails. Any hybrid solution requires mandatory overlap reconciliation (2016–2024) prior to R2 admission.

---

## 5. Exact Provider Requirement Feasibility Matrix

| Candidate Provider | 2007–2024 1m OHLCV | 2007–2024 NBBO Quotes | 2007–2024 Cash Dividends | Single-Provider Feasible? | Qualification Needed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Alpaca (Historical SIP)** | `PARTIAL` (2016–2024 only) | `PARTIAL` (2016–2024 only) | `PARTIAL` (Vintage unverified) | `NOT AVAILABLE` | Overlap partner only |
| **DTN IQFeed** | `VERIFIED` (Back to May 2007) | `NOT AVAILABLE` (180 days only) | `NOT AVAILABLE` | `NOT AVAILABLE` | Infeasible for NBBO |
| **Polygon.io (Massive)** | `VERIFIED` (Back to Sep 2003) | `VERIFIED` (Back to Sep 2003) | `OPEN` (Requires SPY dividend audit) | `VERIFIED` (Pending dividend audit) | Full qualification probe |

---

## 6. R1 Contract Impact & Governance Classification

Based on this audit, **STATE A** applies:

```text
STATE A CLASSIFICATION:
R1_PROVIDER_AMENDMENT_REQUIRED = YES
SCIENTIFIC_HYPOTHESIS_CHANGE   = NO
R2_DATASET_BUILD               = BLOCKED_PENDING_AMENDMENT
```

### Justification:
1. **Scientific Integrity Preserved:** The hypothesis statement, SPY instrument, 2007–2024 M1 replication window, 14-session noise area, cumulative VWAP, 30-minute decision epochs, NBBO execution rules, friction stack, and 7 primary acceptance gates remain **100% identical**.
2. **Provider Lineage Amendment:** The data-provider contract must be amended from Alpaca-only to Polygon (or Polygon primary + Alpaca overlap) to supply the full 2007–2024 M1 historical depth.
3. **No Retrospective Tampering:** Original R1 artifacts remain frozen. An additive `HYP_005_R1_PROVIDER_AMENDMENT_001` record will formally bind the amended provider lineage.

---

## 7. Recommended Next Actions

1. **Human Decision:** Review and ratify this feasibility audit.
2. **Action Token:**
   ```text
   AUTHORIZE_ADDITIVE_HYP_005_R1_PROVIDER_AMENDMENT
   ```
3. **Next Technical Step:** Prepare additive provider qualification and amendment specification (`HYP_005_R1_PROVIDER_AMENDMENT_001`) targeting Polygon (Massive) for full M1 coverage.
4. **Execution Boundaries Remain Active:**
   - Capital: `$0.00`
   - `NO_REAL_ORDERS = true`
   - Zero M1 strategy data downloaded.
   - Zero backtests run.
   - Zero strategy P&L computed.
