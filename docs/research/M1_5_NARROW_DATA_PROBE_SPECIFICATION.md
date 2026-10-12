# ACASH — Bounded Data Qualification Probe Specification (Milestone M1.5)

**Document ID:** `DOC-ACASH-DATA-PROBE-SPEC-20261012`  
**Classification:** Research Data Acquisition Gate & Bounded Probe Protocol  
**Status:** `AWAITING_OPERATOR_AUTHORIZATION` (Design Only — Zero External HTTP Dispatched)  
**Governing Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Single Canonical Authority)  
**Effective Date:** 2026-10-12  
**Network Execution Boundary:** `NO_PROVIDER_MARKET_DATA_HTTP = true`; Zero external network requests permitted until explicitly ratified by human operator.

---

## 1. Objective & Rationale

Prior research proposals often assumed massive historical data acquisition (e.g., full 2010–2026 daily history for hundreds of symbols). Such broad queries waste API quotas, risk terms-of-service violations, and mask fundamental data quality flaws until late in the pipeline.

To preserve strict empirical discipline, Milestone M1.5 specifies the **smallest possible external data qualification probe** to verify:
1. Whether candidate providers deliver genuine unadjusted raw prices vs. pre-adjusted snapshots.
2. Whether split records and dividend distributions match official issuer prospectus filings.
3. Whether observation timestamps provide true point-in-time (PIT) certainty without revision lookahead.
4. Exact licensing, rate limits, and failure boundaries.

---

## 2. Bounded Probe Parameters

```yaml
data_qualification_probe:
  probe_id: "PROBE-ETF-M1-5-20261012"
  status: "PENDING_OPERATOR_RATIFICATION"
  execution_mode: "DRY_RUN_SPEC_ONLY"
  
  target_candidate_universe:
    - symbol: "VOO"
      name: "Vanguard S&P 500 ETF"
      isin: "US9229083632"
    - symbol: "BND"
      name: "Vanguard Total Bond Market ETF"
      isin: "US9219378356"
    - symbol: "GLD"
      name: "SPDR Gold Trust"
      isin: "US78463V1070"
    - symbol: "BIL"
      name: "SPDR Bloomberg 1-3 Month T-Bill ETF"
      isin: "US8464976023"
      
  candidate_sources:
    - provider_id: "ALPACAV2_MARKET_DATA"
      endpoints:
        - "GET /v2/stocks/bars?timeframe=1Day&adjustment=raw"
        - "GET /v2/stocks/bars?timeframe=1Day&adjustment=all"
        - "GET /v1/corporate-actions"
      purpose: "Compare raw unadjusted closes against retroactive all-adjusted series to verify adjustment mechanics."
    - provider_id: "FRED_STLOUIS_FED"
      endpoints:
        - "GET /fred/series/observations?series_id=DTB3"
      purpose: "Inspect quoted 3-month Treasury discount rates, holiday handling, and ACT/360 day-count conventions."
    - provider_id: "BANK_OF_THAILAND_API"
      endpoints:
        - "GET /Stat-ReferenceRate/daily_weighted_average_thb_usd"
      purpose: "Inspect official fixing rate format and calendar alignment with US market holidays."

  probe_window:
    # 5 consecutive trading days across a known monthly transition (e.g., 2026-09-28 to 2026-10-02)
    start_date: "2026-09-28"
    end_date: "2026-10-02"
    session_count: 5

  resource_budget:
    max_http_requests: 12
    max_payload_bytes: 524288  # 512 KB
    timeout_seconds_per_request: 5.0
    evidence_storage_path: "artifacts/evidence/data_probes/probe_m1_5/"

  cryptographic_sealing:
    save_raw_responses: true
    compute_sha256: true
    hash_manifest_filename: "probe_m1_5_manifest.json"
```

---

## 3. Strict Verification & Failure Classifications

Every probe response must be parsed and classified against fail-closed validation rules:

| Verification Check | Expected Canonical Invariant | Failure Classification | Consequence |
| :--- | :--- | :--- | :--- |
| **Price Basis Transparency** | Response includes explicit indicator of whether prices are raw, split-adjusted, or dividend-adjusted | `PROBE_ERR_UNVERIFIED_PRICE_BASIS` | Provider rejected for backtest ingestion. |
| **Split Ratio Representation** | Split records explicitly denote pre/post ratio with ex-date | `PROBE_ERR_INVALID_SPLIT_FORMAT` | Splits require manual regulatory filing reconciliation. |
| **Dividend Cash Net vs. Gross** | Cash distributions indicate gross amount; foreign withholding tax rate can be deterministically calculated | `PROBE_ERR_AMBIGUOUS_DIVIDEND_TAX` | Assume gross and apply standard 15% DTA withholding explicitly. |
| **Timestamp Alignment** | Bar close timestamp matches NYSE/Nasdaq official closing auction ($16:00:00 EST) | `PROBE_ERR_MISALIGNED_SESSION_CLOSE` | Data cannot be matched against official closing prices. |
| **Holiday / Zero-Volume Handling** | Missing weekend/holiday records are omissions, not zero-filled price bars ($0.00) | `PROBE_ERR_ZERO_PRICE_POLLUTION` | Immediate fail-closed abort. |

---

## 4. Automatic Stop Conditions

The probe runner MUST terminate immediately and fail closed upon any of the following triggers:
1. **HTTP 401 / 403**: Authentication or entitlement failure.
2. **HTTP 429**: Rate limit breach (do NOT retry aggressively).
3. **Payload Mismatch**: Response schema deviates from documented contract.
4. **Budget Exceeded**: Total requests exceed 12 or total payload exceeds 512 KB.
5. **Absence of Operator Token**: Attempted execution without explicit operator command flag `--ratified-probe-authorization-token`.

---

## 5. Required Operator Action

To authorize execution of this bounded probe, the operator must provide explicit authorization. Until then:
```text
PROBE_AUTHORIZATION_STATE: BLOCKED_PENDING_HUMAN_APPROVAL
REAL_CAPITAL_AUTHORITY: $0.00
NO_REAL_ORDERS: true
NO_PROVIDER_MARKET_DATA_HTTP: true
```
