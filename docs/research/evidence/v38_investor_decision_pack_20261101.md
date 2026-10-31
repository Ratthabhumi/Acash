# ACASH Investor Decision Pack (illustrative, not advice)

- As of 2026-11-01; fee snapshot 2026-11-01b `b837ea49d9075b5e9c5ca3a58d49636627d8e728014e5bddeedb4e6dad5c0baa`; pack `31d381a296303aaf49e1d373f160d48654b14ed35a7308235024ce794d38d46b`
- Governance: NO_REAL_ORDERS=true; REAL_CAPITAL_AUTHORITY=USD 0.00; evidence grants no execution authority.

## 1. Savings
THB 3000 per month; batches of 1 and 3 months; VOO 60% / BND 40% is an illustrative allocation, not a recommendation. CASH / NO TRADE is the zero-friction, zero-exposure baseline.

## 2. USD that might be obtained (one month)
Hypothetical reference 33.86 THB/USD; FX spread UNKNOWN, so USD is an upper bound.

### `manual_1m`

| Route | USD investable (upper bound if FX unknown) | Cost evidence | Eligibility | Decision | Unknown |
| :--- | ---: | :---: | :---: | :---: | :--- |
| IBKR Pro via K PLUS SWIFT SHAR | 80.41 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | COST_EVIDENCE_INCOMPLETE | IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| IBKR Pro via K PLUS SWIFT DEBT | 59.94 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | COST_EVIDENCE_INCOMPLETE | IBKR_DEBT_FX_SPREAD, IBKR_DEBT_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| IBKR Pro via K PLUS SWIFT CRED | 75.84 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | COST_EVIDENCE_INCOMPLETE | IBKR_CRED_FX_SPREAD, IBKR_CRED_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 88.54 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | COST_EVIDENCE_INCOMPLETE | DIME_FX_SPREAD |
| Webull Thailand (Manual) | 88.50 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | COST_EVIDENCE_INCOMPLETE | WEBULL_MANUAL_FX_SPREAD |
| Webull Thailand (DCA - currently advertised 0%) | - | NOT_EVALUATED | ORDER_TYPE_INCOMPATIBLE | NOT_ELIGIBLE | - |
| Webull Thailand (DCA - 0.10% conflict sensitivity) | - | NOT_EVALUATED | ORDER_TYPE_INCOMPATIBLE | NOT_ELIGIBLE | - |
| CASH / NO TRADE | 0 | NOT_APPLICABLE | DOCUMENTED | CASH_NO_TRADE | - |

### `dca_1m`

| Route | USD investable (upper bound if FX unknown) | Cost evidence | Eligibility | Decision | Unknown |
| :--- | ---: | :---: | :---: | :---: | :--- |
| IBKR Pro via K PLUS SWIFT SHAR | 80.41 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | COST_EVIDENCE_INCOMPLETE | IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| IBKR Pro via K PLUS SWIFT DEBT | 59.94 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | COST_EVIDENCE_INCOMPLETE | IBKR_DEBT_FX_SPREAD, IBKR_DEBT_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| IBKR Pro via K PLUS SWIFT CRED | 75.84 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | COST_EVIDENCE_INCOMPLETE | IBKR_CRED_FX_SPREAD, IBKR_CRED_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 88.54 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | COST_EVIDENCE_INCOMPLETE | DIME_FX_SPREAD |
| Webull Thailand (Manual) | - | NOT_EVALUATED | ORDER_TYPE_INCOMPATIBLE | NOT_ELIGIBLE | - |
| Webull Thailand (DCA - currently advertised 0%) | 88.60 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | TERMS_CONFLICTING | WEBULL_DCA_ZERO_FX_SPREAD |
| Webull Thailand (DCA - 0.10% conflict sensitivity) | 88.50 | LOWER_BOUND_ONLY | ACCOUNT_SPECIFIC_UNVERIFIED | TERMS_CONFLICTING | WEBULL_DCA_STANDARD_FX_SPREAD |
| CASH / NO TRADE | 0 | NOT_APPLICABLE | DOCUMENTED | CASH_NO_TRADE | - |

## 3-5. Documented, observed and unknown costs

Published terms per platform:

- **DIME**: Thai licensed broker: 1 free trade/month for first chronological qualifying trade; subsequent 0.15% + 7% VAT; CAT fee $0.000046/sh.
  - FX: DIME_FX_PREVIEW_20261101: 88.57 USD for 2999.87 THB at 33.87 (indicative; spread UNKNOWN)
  - Funding: LOCAL_THB_QR_ATS; unknowns: DIME_FX_SPREAD
- **WEBULL**: Thai licensed broker: 0.10% commission + 7% VAT; CAT fee $0.000024/sh; no commission minimum; local THB deposit via QR/ATS. / CURRENTLY_ADVERTISED_0_PERCENT: official DCA page advertises zero commission for eligible US stocks/ETFs (min USD 1); owner app showed the same claim on 2026-11-01. Conflict with the 2026-06-15 guide (0.10%) is unresolved; duration not established; zero commission is not zero regulatory, FX or other cost. / 0.10_PERCENT_CONFLICT_SENSITIVITY: 0.10% rate described by the Webull guide published 2026-06-15, kept until the conflict is resolved.
  - FX: WEBULL_FX_PREVIEW_20261031: 88.60 USD for 3000.00 THB at 33.858804 (indicative; spread UNKNOWN)
  - Funding: LOCAL_THB_QR_ATS; unknowns: WEBULL_DCA_STANDARD_FX_SPREAD, WEBULL_DCA_ZERO_FX_SPREAD, WEBULL_MANUAL_FX_SPREAD
- **IBKR**: IBKR Pro Tiered base USD 0.0035/sh, min USD 0.35; exchange, clearing and regulatory pass-through UNKNOWN; pure fractional trades use Footnote 11 max(1% of value, USD 0.01); mixed whole/fractional split UNKNOWN; minimum order not modeled; third-party deposits prohibited.
  - FX: NO_OBSERVATION; spread UNKNOWN
  - Funding: KBANK_KPLUS_SWIFT_CRED, KBANK_KPLUS_SWIFT_DEBT, KBANK_KPLUS_SWIFT_SHAR; unknowns: IBKR_BND_MIXED_ORDER_COMMISSION, IBKR_CRED_BND_MIXED_ORDER_COMMISSION, IBKR_CRED_FX_SPREAD, IBKR_CRED_PASS_THROUGH_FEES, IBKR_DEBT_BND_MIXED_ORDER_COMMISSION, IBKR_DEBT_FX_SPREAD, IBKR_DEBT_PASS_THROUGH_FEES, IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD

Observed previews (FX comparability: `NON_SIMULTANEOUS_NO_RANKING`):

| Observation | Status | Checks | Missing |
| :--- | :--- | :--- | :--- |
| DIME_FX_PREVIEW_20261101 | INDICATIVE_PREVIEW_ARITHMETIC_CHECKED | PAYABLE_THB_VS_TARGET_X_RATE CONSISTENT_WITHIN_DISPLAY_ROUNDING (residual 0.004100); UNSPENT_INPUT_THB NOT_MODELED | INDEPENDENT_CONTEMPORANEOUS_MID, FX_SPREAD, AUTHENTICATED_QUOTE_EXPIRY, EXECUTION_FILL |
| DIME_ORDER_PREVIEW_USD100 | FEE_PREVIEW_RECONCILED | SECURITY_VALUE_USD CONSISTENT_WITHIN_DISPLAY_ROUNDING (residual 0.000243); COMMISSION_USD CONSISTENT_WITHIN_DISPLAY_ROUNDING (residual 0.000240); VAT_USD CONSISTENT_WITHIN_DISPLAY_ROUNDING (residual -0.000483); REGULATORY_USD NOT_DISPLAYED | CAT_FEE (documented rule; share count not displayed), EXECUTION_FILL |
| WEBULL_AAPL_USD1_FRACTIONAL_PREVIEW | FEE_PREVIEW_RECONCILED | SECURITY_VALUE_USD NOT_DISPLAYED; COMMISSION_USD NOT_DISPLAYED; VAT_USD NOT_DISPLAYED; REGULATORY_USD NOT_DISPLAYED; DISPLAYED_TOTAL_FEE_USD ROUNDED_ZERO_NOT_PROOF_OF_ZERO (residual -0.001069) | EXECUTION_FILL |
| WEBULL_AAPL_WHOLE_SHARE_PREVIEW | INSUFFICIENT_DATA | - | ORDER_VALUE, EXECUTION_FILL |
| WEBULL_EWZ_WHOLE_SHARE_PREVIEW | INSUFFICIENT_DATA | - | ORDER_VALUE, EXECUTION_FILL |
| WEBULL_FX_PREVIEW_20261031 | INDICATIVE_PREVIEW_ARITHMETIC_CHECKED | TARGET_USD_VS_SOURCE_DIV_RATE CONSISTENT_WITHIN_DISPLAY_ROUNDING (residual -0.003248) | INDEPENDENT_CONTEMPORANEOUS_MID, FX_SPREAD, AUTHENTICATED_QUOTE_EXPIRY, EXECUTION_FILL |
| WEBULL_VOO_DCA_SETUP_UI | UI_CAPABILITY_OBSERVED_NOT_EXECUTION_ELIGIBILITY | - | EXECUTION_FILL |
| WEBULL_VOO_USD1_FRACTIONAL_PREVIEW | FEE_PREVIEW_RECONCILED | SECURITY_VALUE_USD NOT_DISPLAYED; COMMISSION_USD NOT_DISPLAYED; VAT_USD NOT_DISPLAYED; REGULATORY_USD NOT_DISPLAYED; DISPLAYED_TOTAL_FEE_USD ROUNDED_ZERO_NOT_PROOF_OF_ZERO (residual -0.001069) | EXECUTION_FILL |

A rounding residual is not a broker fee; a rounded zero is not proof of zero; a preview is not an execution.

## 6. Route status (no route is confirmed without account-level evidence)

| Route | dca_1m | dca_3m | manual_1m | manual_3m |
| :--- | :---: | :---: | :---: | :---: |
| IBKR Pro via K PLUS SWIFT SHAR | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE |
| IBKR Pro via K PLUS SWIFT DEBT | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE |
| IBKR Pro via K PLUS SWIFT CRED | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE |
| Dime! Thailand (KKP) | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE |
| Webull Thailand (Manual) | NOT_ELIGIBLE | NOT_ELIGIBLE | COST_EVIDENCE_INCOMPLETE | COST_EVIDENCE_INCOMPLETE |
| Webull Thailand (DCA - currently advertised 0%) | TERMS_CONFLICTING | TERMS_CONFLICTING | NOT_ELIGIBLE | NOT_ELIGIBLE |
| Webull Thailand (DCA - 0.10% conflict sensitivity) | TERMS_CONFLICTING | TERMS_CONFLICTING | NOT_ELIGIBLE | NOT_ELIGIBLE |
| CASH / NO TRADE | CASH_NO_TRADE | CASH_NO_TRADE | CASH_NO_TRADE | CASH_NO_TRADE |

| Platform | Symbol | Searchable | Fractional | Manual | DCA | Account permission | Evidence | UI observed |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| DIME | BIL | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| DIME | BND | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| DIME | GLD | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| DIME | VOO | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| WEBULL | BIL | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| WEBULL | BND | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| WEBULL | GLD | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| WEBULL | VOO | YES | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | OWNER_UI_OBSERVATION | DCA_SETUP_UI_USD_1, FRACTIONAL_USD_ORDER_ENTRY_UI |
| IBKR | BIL | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| IBKR | BND | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| IBKR | GLD | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |
| IBKR | VOO | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNVERIFIED | ACCOUNT_SPECIFIC_UNVERIFIED | - |

## 7. Monthly versus batched explicit friction

| Order type | Route | THB/month (1m) | THB/month (3m batch) | Lower bound |
| :--- | :--- | ---: | ---: | :---: |
| MANUAL | IBKR | 277.32 | 104.63 | yes |
| MANUAL | IBKR_DEBT | 970.43 | 336.57 | yes |
| MANUAL | IBKR_CRED | 432.06 | 156.44 | yes |
| MANUAL | DIME | 2.04 | 2.04 | yes |
| MANUAL | WEBULL_MANUAL | 3.39 | 3.28 | yes |
| DCA | IBKR | 277.32 | 104.63 | yes |
| DCA | IBKR_DEBT | 970.43 | 336.57 | yes |
| DCA | IBKR_CRED | 432.06 | 156.44 | yes |
| DCA | DIME | 2.04 | 2.04 | yes |
| DCA | WEBULL_DCA_ZERO | 0.00 | 0.00 | yes |
| DCA | WEBULL_DCA_STANDARD | 3.39 | 3.28 | yes |

## 8. Hypothetical assumptions

- monthly_savings_thb: 3000
- reference_thb_per_usd: 33.86
- reference_kind: HYPOTHETICAL_INPUT (illustrative; not a market mid)
- prices_usd: {'BND': '72.00', 'VOO': '500.00'}
- weights: {'BND': '0.4', 'VOO': '0.6'}
- fx_spread: UNKNOWN (not assumed)

## 9. Risks and disclosures

- Reference FX provenance: the reference rate is a scenario input. A daily central-bank reference rate is a `DAILY_REFERENCE_PROXY`, not a contemporaneous mid-rate; implied spreads against it include intraday movement.
- Cadence: batching months lowers fixed per-transfer and per-order charges but keeps savings in cash longer. No expected return is assumed, so the opportunity cost of waiting is disclosed, not computed.
- Portfolio risks: equity drawdown; bond duration/interest-rate risk; gold price risk; USD/THB currency risk on every USD asset; concentration in US-listed funds; inflation erodes THB cash; holding cash carries opportunity cost; historical drawdowns can be exceeded.
- Tax and jurisdiction (verify with a qualified adviser; no tax is calculated): US dividend withholding is 30% by default and may be 15% under the US-Thailand treaty with a valid W-8BEN; Thai rules on foreign income remitted from 2024 onward may apply; US estate tax may apply to US-situs assets above USD 60,000 for non-resident aliens (Form 706-NA); custody and broker-insolvency protection differ by platform and jurisdiction.

## 10. Evidence needed next

- OWNER: in-app FX quote with amount and timestamp, captured with an independent mid at the same minute.
- OWNER or RESEARCH: bank/IBKR statement or receiving-bank terms showing intermediary and receiving deductions.
- RESEARCH: IBKR exchange, clearing and regulatory pass-through charges for small US ETF buys.
- RESEARCH: IBKR pricing of mixed whole/fractional executions.
- OWNER: in-app per-symbol eligibility (searchable, fractional, manual/DCA) for VOO and BND on each platform considered.
- RESEARCH: Webull DCA contractual commission and effective dates (0% advertised vs 0.10% guide).
- OWNER: investment horizon, emergency liquidity and risk tolerance; ACASH does not infer a risk profile.

## Reproducibility

- fee_snapshot_sha256: `b837ea49d9075b5e9c5ca3a58d49636627d8e728014e5bddeedb4e6dad5c0baa`
- owner_evidence_digest: `c8942de4e4f2255105ea9b51233a28498bb7b408969f8eca136c30945f9f138b`
- eligibility_matrix_digest: `8a445d02f09e89d0fa257dee7efb22ac03d598d25f31017c0312c403e83ecfed`
- scenario `dca_1m`: `f6c9369d5b12a1aac9940d79a5bb9b6ae7de3673617db7b08cbe563e1be53214`
- scenario `dca_3m`: `77660aa842e297f8a379c86082165165fba8f1f7f679839c814475c0c187bf85`
- scenario `manual_1m`: `485c2b38f98771778764267ebfff90d3a372bc2df495933d2a58b5b1031fb9b7`
- scenario `manual_3m`: `ebf885513347c507a77c1cda89126c5ef648d44a09c61630943861ea9895c0fb`
