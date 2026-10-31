## Scenario `manual_1m`

# ACASH Investor Decision Report

- Scenario date: 2026-10-31
- Fee snapshot: version 2026-10-31b, SHA-256 `b2db8e05a098c1dedfef21cf0450262e3eb49a2b3d234bebef429f0df11a9b07`
- Input SHA-256: `64b1a29cc635d2bc84865e24bde9e27f7a96e8b729e1b9faa8e1f7eed7673886`
- Overall status: `COST_EVIDENCE_INCOMPLETE`
- Savings: THB 3,000.00 x 1 month(s); order type `MANUAL`; weights BND 0.4, VOO 0.6
- Hypothetical inputs: reference FX 35.00 THB/USD (HYPOTHETICAL_INPUT unless sourced); prices BND USD 72.00, VOO USD 500.00

| Platform | Funding THB | Commission+VAT THB | Regulatory THB | FX cost THB | Known friction THB | Share | Numerically complete | Cost evidence | Spread source | Eligibility | Decision | Unknown |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Interactive Brokers (IBKR Pro) | 250.00 | 24.50 | 0.00 | 0.00 | 274.55 | 9.15% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DEDUCTED_FEE_USD, IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 0.00 | 1.93 | 0.00 | 0.00 | 2.25 | 0.08% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DIME_FX_SPREAD |
| Webull Thailand (Manual) | 0.00 | 3.21 | 0.00 | 0.00 | 3.30 | 0.11% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | WEBULL_MANUAL_FX_SPREAD |
| Webull Thailand (DCA - Promo 0%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| Webull Thailand (DCA - Standard 0.10%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| CASH / NO TRADE | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | yes | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `DOCUMENTED` | `CASH_NO_TRADE` | - |

No ranking is produced: unknown or hypothetical components can reverse any ordering. CASH / NO TRADE has zero friction and zero market exposure.

Before any real decision: observe a current FX quote per platform with a comparable reference timestamp; confirm per-security and fractional eligibility in the account; resolve conflicting commission terms; confirm funding-route fees and eligibility. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.

## Scenario `manual_3m`

# ACASH Investor Decision Report

- Scenario date: 2026-10-31
- Fee snapshot: version 2026-10-31b, SHA-256 `b2db8e05a098c1dedfef21cf0450262e3eb49a2b3d234bebef429f0df11a9b07`
- Input SHA-256: `16b46130410d95eec03430e89832eccc1294264aa3ad090738d386057885ce5e`
- Overall status: `COST_EVIDENCE_INCOMPLETE`
- Savings: THB 3,000.00 x 3 month(s); order type `MANUAL`; weights BND 0.4, VOO 0.6
- Hypothetical inputs: reference FX 35.00 THB/USD (HYPOTHETICAL_INPUT unless sourced); prices BND USD 72.00, VOO USD 500.00

| Platform | Funding THB | Commission+VAT THB | Regulatory THB | FX cost THB | Known friction THB | Share | Numerically complete | Cost evidence | Spread source | Eligibility | Decision | Unknown |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Interactive Brokers (IBKR Pro) | 250.00 | 24.50 | 0.00 | 0.00 | 274.50 | 3.05% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DEDUCTED_FEE_USD, IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 0.00 | 5.78 | 0.00 | 0.00 | 6.05 | 0.07% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DIME_FX_SPREAD |
| Webull Thailand (Manual) | 0.00 | 9.63 | 0.00 | 0.00 | 9.90 | 0.11% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | WEBULL_MANUAL_FX_SPREAD |
| Webull Thailand (DCA - Promo 0%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| Webull Thailand (DCA - Standard 0.10%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| CASH / NO TRADE | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | yes | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `DOCUMENTED` | `CASH_NO_TRADE` | - |

No ranking is produced: unknown or hypothetical components can reverse any ordering. CASH / NO TRADE has zero friction and zero market exposure.

Before any real decision: observe a current FX quote per platform with a comparable reference timestamp; confirm per-security and fractional eligibility in the account; resolve conflicting commission terms; confirm funding-route fees and eligibility. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.

## Scenario `dca_1m`

# ACASH Investor Decision Report

- Scenario date: 2026-10-31
- Fee snapshot: version 2026-10-31b, SHA-256 `b2db8e05a098c1dedfef21cf0450262e3eb49a2b3d234bebef429f0df11a9b07`
- Input SHA-256: `196d6cbab0ed9206a3307496bc9b48b1c212a97931f7cf0d1163dcb34897a97f`
- Overall status: `COST_EVIDENCE_INCOMPLETE`
- Savings: THB 3,000.00 x 1 month(s); order type `DCA`; weights BND 0.4, VOO 0.6
- Hypothetical inputs: reference FX 35.00 THB/USD (HYPOTHETICAL_INPUT unless sourced); prices BND USD 72.00, VOO USD 500.00

| Platform | Funding THB | Commission+VAT THB | Regulatory THB | FX cost THB | Known friction THB | Share | Numerically complete | Cost evidence | Spread source | Eligibility | Decision | Unknown |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Interactive Brokers (IBKR Pro) | 250.00 | 24.50 | 0.00 | 0.00 | 274.55 | 9.15% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DEDUCTED_FEE_USD, IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 0.00 | 1.93 | 0.00 | 0.00 | 2.25 | 0.08% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DIME_FX_SPREAD |
| Webull Thailand (Manual) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| Webull Thailand (DCA - Promo 0%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.15 | 0.00% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `TERMS_CONFLICTING` | WEBULL_DCA_ZERO_FX_SPREAD |
| Webull Thailand (DCA - Standard 0.10%) | 0.00 | 3.21 | 0.00 | 0.00 | 3.30 | 0.11% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `TERMS_CONFLICTING` | WEBULL_DCA_STANDARD_FX_SPREAD |
| CASH / NO TRADE | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | yes | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `DOCUMENTED` | `CASH_NO_TRADE` | - |

No ranking is produced: unknown or hypothetical components can reverse any ordering. CASH / NO TRADE has zero friction and zero market exposure.

Before any real decision: observe a current FX quote per platform with a comparable reference timestamp; confirm per-security and fractional eligibility in the account; resolve conflicting commission terms; confirm funding-route fees and eligibility. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.

## Scenario `manual_1m_dime_quote`

# ACASH Investor Decision Report

- Scenario date: 2026-10-31
- Fee snapshot: version 2026-10-31b, SHA-256 `b2db8e05a098c1dedfef21cf0450262e3eb49a2b3d234bebef429f0df11a9b07`
- Input SHA-256: `281dc247896e9bd10f0b3e5ba0568b2c72c5950cefe892480d50c1564fd8db2b`
- Overall status: `COST_EVIDENCE_INCOMPLETE`
- Savings: THB 3,000.00 x 1 month(s); order type `MANUAL`; weights BND 0.4, VOO 0.6
- Hypothetical inputs: reference FX 35.00 THB/USD (HYPOTHETICAL_INPUT unless sourced); prices BND USD 72.00, VOO USD 500.00

| Platform | Funding THB | Commission+VAT THB | Regulatory THB | FX cost THB | Known friction THB | Share | Numerically complete | Cost evidence | Spread source | Eligibility | Decision | Unknown |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Interactive Brokers (IBKR Pro) | 250.00 | 24.50 | 0.00 | 0.00 | 274.55 | 9.15% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DEDUCTED_FEE_USD, IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 0.00 | 1.91 | 0.00 | 17.89 | 20.10 | 0.67% | yes | `QUOTE_OBSERVED` | `USER_QUOTE_CURRENT` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `SECURITY_ELIGIBILITY_UNKNOWN` | - |
| Webull Thailand (Manual) | 0.00 | 3.21 | 0.00 | 0.00 | 3.30 | 0.11% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | WEBULL_MANUAL_FX_SPREAD |
| Webull Thailand (DCA - Promo 0%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| Webull Thailand (DCA - Standard 0.10%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| CASH / NO TRADE | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | yes | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `DOCUMENTED` | `CASH_NO_TRADE` | - |

No ranking is produced: unknown or hypothetical components can reverse any ordering. CASH / NO TRADE has zero friction and zero market exposure.

Before any real decision: observe a current FX quote per platform with a comparable reference timestamp; confirm per-security and fractional eligibility in the account; resolve conflicting commission terms; confirm funding-route fees and eligibility. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.
