# ACASH V38 — ChatGPT External Research Handoff

**Date**: 2026-10-30  
**Status**: V38 FINAL ENGINEERING CLOSURE COMPLETE
**Fee Snapshot Hash (SHA-256)**: `3121459a2fcbf10cf9c840b7caa61d4bb2e4fd428262bea134d07de6b1ffd8b5`

---

## 1. Division of Responsibility
- **Codex (Engineering)**:
  - Architecture, pure Decimal fail-closed calculation core.
  - P0.1 FX double-counting elimination & cash conservation.
  - P0.2 Comprehensive canonical input hashing.
  - P0.3 Webull DCA dual-scenario modeling (`TERMS_CONFLICTING`).
  - P0.4 IBKR account-specific fail-closed boundaries.
  - P0.5 Missing reference price fail-closed handling (`PRICES_ILLUSTRATIVE`).
  - P1 Chronological sequence free trade allocation for Dime! Thailand.
  - Automated tests & GitHub CI verification. *(Complete)*
- **ChatGPT (Research)**:
  - External fee discovery, retail FX quotes, broker promotional terms, and ETF eligibility. *(Handed off below)*

---

## 2. Priority Research Questions for ChatGPT

To convert the `LOWER_BOUND_ONLY` cost assessments into `ALL_IN_DOCUMENTED` numbers, the following specific primary-source data points are needed:

| ID | Platform | Research Topic | Current Status in Engine | Specific Evidence Needed |
| :---: | :--- | :--- | :--- | :--- |
| **RQ-01** | **Dime! Thailand** | Effective THB/USD Conversion Spread | Recorded as `UNKNOWN` (`DIME_FX_SPREAD`) | User-observable in-app exchange quote sample (THB/USD rate, timestamp, and BOT mid-rate at that moment) to benchmark effective markup in bps. |
| **RQ-02** | **Webull Thailand** | Effective THB/USD Conversion Spread | Recorded as `UNKNOWN` (`WEBULL_FX_SPREAD`) | User-observable in-app currency exchange quote sample (Funding -> Currency Exchange) to benchmark effective markup in bps. |
| **RQ-03** | **Webull Thailand** | DCA Commission Conflict Resolution | Modeled as dual scenarios (`WEBULL_DCA_ZERO` vs `WEBULL_DCA_STANDARD`) | Clarification from official support/announcements on whether 0% DCA is permanent, promotional, or subject to trade-value caps. |
| **RQ-04** | **Dime! & Webull** | Specific ETF Fractional Availability | Modeled as `CONDITIONALLY_ELIGIBLE` | Verify if `VOO`, `BND`, `GLD`, and `BIL` are individually enabled for fractional trading in standard retail cash accounts. |
| **RQ-05** | **IBKR** | Outbound Funding Route Verification | Modeled as `ACCOUNT_SPECIFIC_UNVERIFIED` | Verify user's actual deposit instructions (receiving bank location, SWIFT BIC, whether intermediary deductions occur on USD deposits from Thai banks). |

---

## 3. Integrated Regulatory Fees Status
- **Dime! CAT Fee**: Integrated at USD 0.000046 per share (effective June 1, 2025) on BUY executions.
- **Dime! / Webull SEC & TAF Fees**: Confirmed applicable to SELL executions only (zero on BUY accumulations).
- **Thai VAT (7%)**: Correctly applied to paid commissions for Dime! and Webull Thailand; zero on IBKR US commissions.

---

## 4. Acceptance Closure Addendum (2026-10-31; supersedes the header hash above)

- Fee snapshot version `2026-10-31b`, SHA-256 `b2db8e05a098c1dedfef21cf0450262e3eb49a2b3d234bebef429f0df11a9b07`.
  Lineage: `ccb899ca…` (2026-10-30, unsupported `generated_at`) and `1ddbcf98…` (2026-10-31). Capture time stays
  `CAPTURE_TIME_UNKNOWN`; no capture log exists.
- Dime! supplemental Monthly Freebie: `SOURCE_VERSION_CONFLICT` (observed end dates 2026-08-31 and 2026-12-31);
  not applied by the engine and never applied to standard accounts.
- Webull DCA: both scenarios kept; status `TERMS_CONFLICTING`.
- Engine changes: an observed quote no longer hides unknown fees; hypothetical spreads and historical or
  timing-mismatched quotes are `SCENARIO_ONLY`; missing prices make CAT fees and IBKR share counts `UNKNOWN`;
  IBKR pass-through fees are `UNKNOWN`; per-security and fractional eligibility default to
  `ACCOUNT_SPECIFIC_UNVERIFIED`; USD charges are applied after conversion; the input hash covers every input field.
- Reproducible demo: `uv run python -m acash.research.d6.investor_decision --acceptance-demo --output docs/research/evidence/v38_acceptance_demo_20261031`
  (synthetic inputs only; no `ALL_IN_DOCUMENTED` result).

Open items for the owner or ChatGPT: RQ-01 to RQ-05 above, plus the authoritative Dime! campaign version,
Webull SEC/TAF minimum and cap values (sell side is not modeled), and IBKR fractional-trade pricing footnotes.
