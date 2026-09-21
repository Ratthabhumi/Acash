# Phase 14 HYP_005 Step R1 Provider Amendment 001

```text
[GOVERNANCE ARTIFACT: ADDITIVE R1 PROVIDER AMENDMENT]
[AMENDMENT_ID: HYP_005_R1_PROVIDER_AMENDMENT_001]
[CANONICAL STARTING HEAD: 886db67bf88241929a2a32557e3c0ef9bffcc693]
[FEASIBILITY_AUDIT_COMMIT: 886db67bf88241929a2a32557e3c0ef9bffcc693]
[ORIGINAL_R1_COMMIT: 333af02424349bfb43ec05c7afc96ca960f6d5d7]
[SCIENTIFIC_HYPOTHESIS_CHANGED: NO]
[M1_SAMPLE_WINDOW_CHANGED: NO]
[STRATEGY_PARAMETERS_CHANGED: NO]
[FRICTION_STACK_CHANGED: NO]
[ACCEPTANCE_GATES_CHANGED: NO]
[AMENDMENT_STATUS: AMENDMENT_SEALED_LINEAGE_ONLY_PROVIDER_QUALIFICATION_PENDING]
[MASSIVE_MARKET_DATA_PROVIDER_QUALIFICATION: NOT_EXECUTED_ENTITLEMENT_MISSING]
[R2_READINESS: BLOCKED_PENDING_MASSIVE_ENTITLEMENT_AND_LIVE_QUALIFICATION]
[R2_DATASET_BUILD: NOT_STARTED]
[NEXT_ACTION: CONFIGURE_MASSIVE_ENTITLEMENT_THEN_AUTHORIZE_NARROW_PROVIDER_QUALIFICATION]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/HYP_005_R1_PROVIDER_AMENDMENT_001.md`
- **Subject:** Formal additive amendment to the data-provider lineage for sealed hypothesis `HYP_005` (MEC-0015: SPY Noise-Area Intraday Momentum Net-Profitability Replication).
- **Governing Standard:** ACASH `AGENTS.md` (Zero Unverified Claims, Single Canonical Authority, Strict Fail-Closed).
- **Original R1 Inception Token:** `AUTH_INCEPTION_HYP_005_8b61aa2dcf7cc4f0`

---

## 1. Upstream R1 Lineage & Immutability Ledger

This amendment is **strictly additive**. Original R1 artifacts remain byte-for-byte unmodified:

| Original R1 Artifact | Tracked Path | Immutable Canonical SHA-256 Digest |
| :--- | :--- | :--- |
| **Original Sealed Spec (Phase 8.5)** | `docs/phase8.5/hypotheses/HYP_005.json` | `ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f` |
| **Original Sealed Spec (Phase 14)** | `docs/phase14/hypotheses/HYP_005.json` | `ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f` |
| **Original Preregistration Spec** | `docs/research/MEC-0015-HYP-005-strategy-preregistration.md` | `5036c765cea2f36b95352f5bc0311580c375e8552ec1590c228690b2543cff9e` |
| **Original R1 Manifest** | `docs/phase14/manifests/manifest_r1_HYP_005.json` | `f0322a049b6990ed2131f28cb33f0f2fd768a982be2e75815d9f999091422e61` |

- **Original R1 Registration Commit:** `333af02424349bfb43ec05c7afc96ca960f6d5d7`
- **Feasibility Audit Commit:** `886db67bf88241929a2a32557e3c0ef9bffcc693`

---

## 2. Rationale for Amendment

The sealed `HYP_005` preregistration requires:
```text
M1_START = 2007-05-01
M1_END   = 2024-04-30
M1_ROLE  = PUBLICATION_EXPOSED_REPLICATION_SAMPLE
```
The original pre-inception contracts designated Alpaca Historical SIP as the primary market data provider. However, authoritative provider documentation confirms Alpaca US equities data begins on **2016-01-01**, lacking the first 8 years and 8 months of the M1 sample.

To avoid altering the scientific replication sample (shortening to 2016 is strictly prohibited) and to eliminate dangerous market-data splicing, this amendment ratifies a robust dual-authority architecture:
1. **Primary Market-Data Provider (Bars & Quotes):** Massive / Polygon US Stocks SIP (history back to September 10, 2003).
2. **Primary Dividend Authority:** State Street Global Advisors (SSGA) Official Historical Distributions.

---

## 3. Amended Provider Lineage Specifications

### 3.1 Primary Market-Data Provider: Massive / Polygon US Stocks SIP
- **Minute Aggregates (`us_stocks_sip/minute_aggs_v1`):**
  - Complete historical depth back to **September 10, 2003** (covers full 2007–2024 M1 sample).
  - Schema: `ticker`, `volume`, `open`, `close`, `high`, `low`, `window_start` (nanosecond epoch integer), `transactions`.
- **Top-of-Book Quotes (`us_stocks_sip/quotes_v1`):**
  - Complete historical depth back to **September 10, 2003** (covers full 2007–2024 M1 sample).
  - Schema: `ticker`, `bid_price`, `ask_price`, `bid_size`, `ask_size`, `bid_exchange`, `ask_exchange`, `sip_timestamp`, `participant_timestamp`, `trf_timestamp`, `conditions`.
  - Nanosecond timestamp precision supports exact execution fill modeling:
    $$\text{FIRST\_VALID\_SIP\_NBBO\_AT\_OR\_AFTER\_EXECUTION\_BOUNDARY}$$
- **Required Commercial Subscription:** Stocks Advanced (~$199/month, full 20+ years history + flat files).

### 3.2 Primary Dividend Authority: State Street / SSGA Official Distributions
- **Sovereign Authority:** State Street Global Advisors (SSGA), fund sponsor and trustee of `SPY`.
- **Coverage:** Full M1 window (`2007-05-01` through `2024-04-30`) contains **exactly 68 quarterly cash distributions**.
- **Audit Finding:** All 35 pre-2016 distributions absent from Alpaca are fully supplied by SSGA. Across the 33 post-2016 distributions, 31 Alpaca-present events match SSGA rates exactly (`ALPACA_PRESENT_RATE_RECONCILIATION = 31/31 PASS`), while 2 post-2016 distributions (`2016-03-18` and `2018-06-15`) are classified as `ALPACA_CROSS_CHECK_ABSENT_OR_UNVERIFIED` (total 37 unverified across M1; 36 distributions prior to the first verified Alpaca distribution on `2016-06-17`).
- **Authority vs. Overlap Distinction:** `FULL_POST_2016_ALPACA_COVERAGE = NOT_ESTABLISHED`, while `SSGA_FULL_M1_DIVIDEND_AUTHORITY = ESTABLISHED`.
- **Manifest Reference:** `docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json` (File SHA-256: `0f99ab26884e8767d2bade35039770a342e66c0628dbd2b8ff1e03075cc871bc`).

### 3.3 Reclassification of Alpaca
- **Amended Role:** `ALPACA_ROLE = CROSS_PROVIDER_VALIDATION_ONLY`.
- **Overlap Window:** `2016-01-01` through `2024-04-30`.
- **Restriction:** Alpaca data MUST NOT be spliced into the primary M1 dataset. Primary M1 price and quote lineage is single-provider Massive/Polygon.

---

## 4. Operational & Timestamp Semantics

### 4.1 Author Decision-Time to Massive Bar Timestamp Mapping
- Author conceptual decision epochs: `10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30 ET`.
- Under Massive flat-file schema, `window_start` represents the start of the 1-minute interval (left-edge):
  - Author 10:00 decision reads completed bar covering `[09:59:00, 10:00:00)`.
  - In Massive flat files, this bar is labeled by `window_start` matching `09:59:00 ET` (converted to nanosecond epoch timestamp).
  - Mapping is mathematically and operationally identical to Alpaca left-edge mapping.
  - Scientific decision epoch remains strictly unchanged.

### 4.2 Quote Validity & Condition Filtering
To implement `FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY` using Massive quotes:
- `sip_timestamp >= decision_boundary_nanoseconds`
- `bid_price > 0` and `ask_price > 0`
- `ask_price >= bid_price` (crossed/locked markets excluded)
- Non-NBBO or invalid quote condition flags excluded per official SIP specifications.

---

## 5. Scope & Invariant Declarations

- **Scientific Hypothesis Changed:** `NO` (Hypothesis statement, instrument, formulas, signals, and gates are 100% unchanged).
- **M1 Window Changed:** `NO` (`2007-05-01` through `2024-04-30` preserved).
- **Strategy Parameters Changed:** `NO` ($K = 1$, vol window = 15, noise lookback = 14).
- **Friction Model Changed:** `NO` (Commissions, slippage, SEC Section 31, FINRA TAF, 2× stress unchanged).
- **Acceptance Gates Changed:** `NO` (7 primary gates unchanged).
- **Strategy P&L Computed:** `NO` (`STRATEGY_PNL = NOT_COMPUTED`).
- **M2 Access:** `ZERO` (`M2_ACCESS = LOCKED`).
- **Capital:** `$0.00` (`NO_REAL_ORDERS = true`).
- **Paper / Live Trading:** `LOCKED`.

---

## 6. Amendment State & R2 Readiness

- **Amendment Status:** `AMENDMENT_SEALED_LINEAGE_ONLY_PROVIDER_QUALIFICATION_PENDING`
- **Massive Market-Data Provider Qualification:** `NOT_EXECUTED_ENTITLEMENT_MISSING`
  - Live qualification on authorized probe dates (`2019-06-03`, `2022-06-01`, `2024-03-01`) has not been executed because Massive API credentials are not configured in local environment.
- **R2 Readiness Classification:** `BLOCKED_PENDING_MASSIVE_ENTITLEMENT_AND_LIVE_QUALIFICATION`
- **R2 Dataset Build:** `NOT_STARTED`
- **Next Action:** `CONFIGURE_MASSIVE_ENTITLEMENT_THEN_AUTHORIZE_NARROW_PROVIDER_QUALIFICATION`
  - Zero strategy data downloaded during this audit.
  - No backtest, signals, trades, or P&L computed.
