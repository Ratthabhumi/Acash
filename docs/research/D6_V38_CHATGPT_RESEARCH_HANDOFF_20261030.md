# ACASH V38 — ChatGPT External Research Handoff

**Date**: 2026-10-30  
**Status**: V38 FINAL ENGINEERING CLOSURE COMPLETE
**Current Fee Snapshot**: version 2026-11-01b, SHA-256 `b837ea49d9075b5e9c5ca3a58d49636627d8e728014e5bddeedb4e6dad5c0baa` (original 2026-10-30 handoff hash `3121459a…` is historical; see snapshot lineage)

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

## 5. Evidence Integration Addendum (2026-11-01; snapshot 2026-11-01, SHA-256 `89d223fac999065082af4964b5208d2bc6c4cac75550badef698f6570dd1eb6a`)

Integrity fixes (engine): synthetic or indicative quotes can no longer yield `QUOTE_OBSERVED`; THB route fees apply before
conversion and USD deducted/intermediary/receiving fees after it; order minimums are checked on the post-fee notional
(`FEES_DEDUCTED_FROM_ALLOCATION`, superseded in section 6 by `FEES_SOLVED_ON_FINAL_NOTIONAL`); `ALL_IN_DOCUMENTED` requires route terms with `OFFICIAL_PROVIDER_TARIFF` evidence.

Integrated research (dated inputs, not re-verified by the engineering agent): Dime! chronological free trade, 0.15% at
>= USD 6.67 or USD 0.01/share below, VAT, CAT 0.000046, supplemental freebie `SOURCE_VERSION_CONFLICT` (not applied);
Webull manual 0.10% + VAT, DCA 0% vs 0.10% `TERMS_CONFLICTING`, CAT 0.000024, sell-side SEC (min USD 0.01) and TAF
(min 0.01, max 9.79) recorded only (no sell engine), USD 1 candidate order minimum (THB 40 not certified); IBKR Tiered
0.0035/share min 0.35 with the fractional footnote max(1%, USD 0.01) kept as an unverified lower bound; KBank 2026
promotion window recorded as `PROMOTIONAL_CLAIM` with post-promotion fee UNKNOWN. ETF eligibility matrix
[`v38_etf_eligibility_matrix_20261101.csv`](evidence/v38_etf_eligibility_matrix_20261101.csv) is entirely
`ACCOUNT_SPECIFIC_UNVERIFIED`.

### Candidate register (recorded only; no calculator, no ranking)

| Candidate | Reported terms | Status |
| :--- | :--- | :--- |
| Pi Securities | 0.20%, no minimum, + VAT | UNVERIFIED_CANDIDATE |
| InnovestX | USD 0.08/share, minimum USD 4.99, + VAT, 1-share minimum | UNVERIFIED_CANDIDATE |
| TrueMoney / Webull distribution route | 0.15%, minimum USD 0.01 | UNVERIFIED_CANDIDATE |
| SP50001 DR | Alternative instrument (Thai depositary receipt) | NOT_COMPARABLE_INSTRUMENT |

### Open research questions for ChatGPT

| # | Required value | Source needed | Why it matters | Blocking | Owner-app evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Dime! and Webull THB->USD FX spread vs a contemporaneous mid | Official FX page or in-app quote with notional | Largest unknown cost for local brokers | Yes (cost) | Yes: current quote with amount + timestamp |
| 2 | Does the IBKR fractional footnote max(1%, USD 0.01) apply to IBKR Pro Tiered US ETF fractional orders? | IBKR commissions page footnote text | Decides IBKR commission for small orders | Yes (IBKR) | No |
| 3 | KBank SWIFT outward fee source URL, post-2026 fee, charge bearer (OUR/SHA/BEN), USD intermediary and receiving fees | KBank tariff page; IBKR receiving-bank terms | IBKR funding cost and 2027 viability | Yes (IBKR) | Possibly: bank fee preview |
| 4 | Webull DCA commission: 0% promotion vs 0.10% guide; effective dates | Webull TH official pages with dates | Resolves `TERMS_CONFLICTING` | Yes (DCA) | Optional: DCA order preview |
| 5 | Dime! supplemental freebie authoritative end date (2026-08-31 vs 2026-12-31) | Dated official page/archive | Only affects supplemental accounts | No | No |
| 6 | VOO/BND/GLD/BIL searchable, fractional, manual and DCA eligibility per platform | Official symbol lists | Fills the eligibility matrix | Yes (eligibility) | Yes: in-app search/order screen |
| 7 | Whether Dime! charges CAT on buys in the order preview | Dime! fee page | Owner preview (USD 100 = 99.84 + 0.15 + 0.01 VAT) showed no CAT line | No | Yes: preview with ticker |
| 8 | Webull order minimum in THB vs USD 1 | Webull fractional trading terms | Small-contribution eligibility | No | Optional |

## 6. Source Verification Addendum (2026-11-01; snapshot 2026-11-01b)

Closed by ChatGPT Research Lead sources (integrated, not re-fetched): question 2 (IBKR Footnote 11 applies to pure
fractional trades; mixed whole/fractional split still UNKNOWN), question 3 in part (K PLUS SWIFT SHAR THB 250 / DEBT THB 950 /
CRED USD 12 for 2026; K BIZ kept separate; post-promotion fee, intermediary and receiving charges still UNKNOWN), question 4
in part (0% currently advertised and seen in the owner app; 0.10% sensitivity kept), question 5 (current article states
2026-12-31; older 2026-08-31 version kept in lineage), question 7 (CAT rule kept; absence of a CAT line is attributed to
display rounding, not zero).

Engine correction: each allocation now splits exactly into final notional plus commission, VAT and per-share fees charged
on that final notional (FEES_SOLVED_ON_FINAL_NOTIONAL). This removes the earlier systematic overstatement and is
consistent with the owner Dime! preview (USD 100.00 -> 99.84 + 0.15 + 0.01 VAT).
