## Scenario `manual_1m`

# ACASH Investor Decision Report

- Scenario date: 2026-10-31
- Fee snapshot: version 2026-11-01, SHA-256 `89d223fac999065082af4964b5208d2bc6c4cac75550badef698f6570dd1eb6a`
- Input SHA-256: `19ef5bc57dc569c6ea7e30472588d61b4aafe529bf39d5749a0f97fe762ac158`
- Overall status: `COST_EVIDENCE_INCOMPLETE`
- Savings: THB 3,000.00 x 1 month(s); order type `MANUAL`; weights BND 0.4, VOO 0.6
- Hypothetical inputs: reference FX 35.00 THB/USD (HYPOTHETICAL_INPUT unless sourced); prices BND USD 72.00, VOO USD 500.00

| Platform | Funding THB | Commission+VAT THB | Regulatory THB | FX cost THB | Known friction THB | Share | Numerically complete | Cost evidence | Spread source | Eligibility | Decision | Unknown |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Interactive Brokers (IBKR Pro) | 250.00 | 23.25 | 0.00 | 0.00 | 273.50 | 9.12% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DEDUCTED_FEE_USD, IBKR_BND_FRACTIONAL_COMMISSION_APPLICABILITY, IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, IBKR_VOO_FRACTIONAL_COMMISSION_APPLICABILITY, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 0.00 | 1.93 | 0.00 | 0.00 | 2.25 | 0.08% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DIME_FX_SPREAD |
| Webull Thailand (Manual) | 0.00 | 3.21 | 0.00 | 0.00 | 3.30 | 0.11% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | WEBULL_MANUAL_FX_SPREAD |
| Webull Thailand (DCA - Promo 0%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| Webull Thailand (DCA - Standard 0.10%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| CASH / NO TRADE | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | yes | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `DOCUMENTED` | `CASH_NO_TRADE` | - |

No ranking is produced: unknown or hypothetical components can reverse any ordering. CASH / NO TRADE has zero friction and zero market exposure.

Sizing policy `FEES_DEDUCTED_FROM_ALLOCATION`: commission, VAT and per-share regulatory fees are bounded on each allocation and deducted from it; minimum-order and fractional checks use the post-fee notional. THB funding fees apply before conversion; USD deducted, intermediary and receiving fees apply after it.

## Disclosures (informational, not advice)

- Reference FX provenance: the reference rate is a scenario input. A daily central-bank reference rate is a `DAILY_REFERENCE_PROXY`, not a contemporaneous mid-rate; implied spreads against it include intraday movement.
- Cadence: batching months lowers fixed per-transfer and per-order charges but keeps savings in cash longer. No expected return is assumed, so the opportunity cost of waiting is disclosed, not computed.
- Portfolio risks: equity drawdown; bond duration/interest-rate risk; gold price risk; USD/THB currency risk on every USD asset; concentration in US-listed funds; inflation erodes THB cash; holding cash carries opportunity cost; historical drawdowns can be exceeded.
- Tax and jurisdiction (verify with a qualified adviser; no tax is calculated): US dividend withholding is 30% by default and may be 15% under the US-Thailand treaty with a valid W-8BEN; Thai rules on foreign income remitted from 2024 onward may apply; US estate tax may apply to US-situs assets above USD 60,000 for non-resident aliens (Form 706-NA); custody and broker-insolvency protection differ by platform and jurisdiction.

Before any real decision: observe a current FX quote per platform with a comparable reference timestamp; confirm per-security and fractional eligibility in the account; resolve conflicting commission terms; confirm funding-route fees and eligibility. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.

## Scenario `manual_3m`

# ACASH Investor Decision Report

- Scenario date: 2026-10-31
- Fee snapshot: version 2026-11-01, SHA-256 `89d223fac999065082af4964b5208d2bc6c4cac75550badef698f6570dd1eb6a`
- Input SHA-256: `9e620d96717a9fb45d378544a4512d8dfb0e8813045bc4fa8482833dd6876d35`
- Overall status: `COST_EVIDENCE_INCOMPLETE`
- Savings: THB 3,000.00 x 3 month(s); order type `MANUAL`; weights BND 0.4, VOO 0.6
- Hypothetical inputs: reference FX 35.00 THB/USD (HYPOTHETICAL_INPUT unless sourced); prices BND USD 72.00, VOO USD 500.00

| Platform | Funding THB | Commission+VAT THB | Regulatory THB | FX cost THB | Known friction THB | Share | Numerically complete | Cost evidence | Spread source | Eligibility | Decision | Unknown |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Interactive Brokers (IBKR Pro) | 250.00 | 24.50 | 0.00 | 0.00 | 274.50 | 3.05% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DEDUCTED_FEE_USD, IBKR_BND_FRACTIONAL_COMMISSION_APPLICABILITY, IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, IBKR_VOO_FRACTIONAL_COMMISSION_APPLICABILITY, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 0.00 | 5.78 | 0.00 | 0.00 | 6.05 | 0.07% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DIME_FX_SPREAD |
| Webull Thailand (Manual) | 0.00 | 9.63 | 0.00 | 0.00 | 9.90 | 0.11% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | WEBULL_MANUAL_FX_SPREAD |
| Webull Thailand (DCA - Promo 0%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| Webull Thailand (DCA - Standard 0.10%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| CASH / NO TRADE | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | yes | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `DOCUMENTED` | `CASH_NO_TRADE` | - |

No ranking is produced: unknown or hypothetical components can reverse any ordering. CASH / NO TRADE has zero friction and zero market exposure.

Sizing policy `FEES_DEDUCTED_FROM_ALLOCATION`: commission, VAT and per-share regulatory fees are bounded on each allocation and deducted from it; minimum-order and fractional checks use the post-fee notional. THB funding fees apply before conversion; USD deducted, intermediary and receiving fees apply after it.

## Disclosures (informational, not advice)

- Reference FX provenance: the reference rate is a scenario input. A daily central-bank reference rate is a `DAILY_REFERENCE_PROXY`, not a contemporaneous mid-rate; implied spreads against it include intraday movement.
- Cadence: batching months lowers fixed per-transfer and per-order charges but keeps savings in cash longer. No expected return is assumed, so the opportunity cost of waiting is disclosed, not computed.
- Portfolio risks: equity drawdown; bond duration/interest-rate risk; gold price risk; USD/THB currency risk on every USD asset; concentration in US-listed funds; inflation erodes THB cash; holding cash carries opportunity cost; historical drawdowns can be exceeded.
- Tax and jurisdiction (verify with a qualified adviser; no tax is calculated): US dividend withholding is 30% by default and may be 15% under the US-Thailand treaty with a valid W-8BEN; Thai rules on foreign income remitted from 2024 onward may apply; US estate tax may apply to US-situs assets above USD 60,000 for non-resident aliens (Form 706-NA); custody and broker-insolvency protection differ by platform and jurisdiction.

Before any real decision: observe a current FX quote per platform with a comparable reference timestamp; confirm per-security and fractional eligibility in the account; resolve conflicting commission terms; confirm funding-route fees and eligibility. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.

## Scenario `dca_1m`

# ACASH Investor Decision Report

- Scenario date: 2026-10-31
- Fee snapshot: version 2026-11-01, SHA-256 `89d223fac999065082af4964b5208d2bc6c4cac75550badef698f6570dd1eb6a`
- Input SHA-256: `1a05263e4fb24f22080a16cb7c1ee9caa3817fdb96cdade782ad4b8ec1885786`
- Overall status: `COST_EVIDENCE_INCOMPLETE`
- Savings: THB 3,000.00 x 1 month(s); order type `DCA`; weights BND 0.4, VOO 0.6
- Hypothetical inputs: reference FX 35.00 THB/USD (HYPOTHETICAL_INPUT unless sourced); prices BND USD 72.00, VOO USD 500.00

| Platform | Funding THB | Commission+VAT THB | Regulatory THB | FX cost THB | Known friction THB | Share | Numerically complete | Cost evidence | Spread source | Eligibility | Decision | Unknown |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Interactive Brokers (IBKR Pro) | 250.00 | 23.25 | 0.00 | 0.00 | 273.50 | 9.12% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DEDUCTED_FEE_USD, IBKR_BND_FRACTIONAL_COMMISSION_APPLICABILITY, IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, IBKR_VOO_FRACTIONAL_COMMISSION_APPLICABILITY, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 0.00 | 1.93 | 0.00 | 0.00 | 2.25 | 0.08% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DIME_FX_SPREAD |
| Webull Thailand (Manual) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| Webull Thailand (DCA - Promo 0%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.15 | 0.00% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `TERMS_CONFLICTING` | WEBULL_DCA_ZERO_FX_SPREAD |
| Webull Thailand (DCA - Standard 0.10%) | 0.00 | 3.21 | 0.00 | 0.00 | 3.30 | 0.11% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `TERMS_CONFLICTING` | WEBULL_DCA_STANDARD_FX_SPREAD |
| CASH / NO TRADE | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | yes | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `DOCUMENTED` | `CASH_NO_TRADE` | - |

No ranking is produced: unknown or hypothetical components can reverse any ordering. CASH / NO TRADE has zero friction and zero market exposure.

Sizing policy `FEES_DEDUCTED_FROM_ALLOCATION`: commission, VAT and per-share regulatory fees are bounded on each allocation and deducted from it; minimum-order and fractional checks use the post-fee notional. THB funding fees apply before conversion; USD deducted, intermediary and receiving fees apply after it.

## Disclosures (informational, not advice)

- Reference FX provenance: the reference rate is a scenario input. A daily central-bank reference rate is a `DAILY_REFERENCE_PROXY`, not a contemporaneous mid-rate; implied spreads against it include intraday movement.
- Cadence: batching months lowers fixed per-transfer and per-order charges but keeps savings in cash longer. No expected return is assumed, so the opportunity cost of waiting is disclosed, not computed.
- Portfolio risks: equity drawdown; bond duration/interest-rate risk; gold price risk; USD/THB currency risk on every USD asset; concentration in US-listed funds; inflation erodes THB cash; holding cash carries opportunity cost; historical drawdowns can be exceeded.
- Tax and jurisdiction (verify with a qualified adviser; no tax is calculated): US dividend withholding is 30% by default and may be 15% under the US-Thailand treaty with a valid W-8BEN; Thai rules on foreign income remitted from 2024 onward may apply; US estate tax may apply to US-situs assets above USD 60,000 for non-resident aliens (Form 706-NA); custody and broker-insolvency protection differ by platform and jurisdiction.

Before any real decision: observe a current FX quote per platform with a comparable reference timestamp; confirm per-security and fractional eligibility in the account; resolve conflicting commission terms; confirm funding-route fees and eligibility. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.

## Scenario `manual_1m_dime_quote`

# ACASH Investor Decision Report

- Scenario date: 2026-10-31
- Fee snapshot: version 2026-11-01, SHA-256 `89d223fac999065082af4964b5208d2bc6c4cac75550badef698f6570dd1eb6a`
- Input SHA-256: `8a42aa425349eff1a4002371bf562798cfed3452662f721318553377e668fa56`
- Overall status: `COST_EVIDENCE_INCOMPLETE`
- Savings: THB 3,000.00 x 1 month(s); order type `MANUAL`; weights BND 0.4, VOO 0.6
- Hypothetical inputs: reference FX 35.00 THB/USD (HYPOTHETICAL_INPUT unless sourced); prices BND USD 72.00, VOO USD 500.00

| Platform | Funding THB | Commission+VAT THB | Regulatory THB | FX cost THB | Known friction THB | Share | Numerically complete | Cost evidence | Spread source | Eligibility | Decision | Unknown |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Interactive Brokers (IBKR Pro) | 250.00 | 23.25 | 0.00 | 0.00 | 273.50 | 9.12% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | DEDUCTED_FEE_USD, IBKR_BND_FRACTIONAL_COMMISSION_APPLICABILITY, IBKR_FX_SPREAD, IBKR_PASS_THROUGH_FEES, IBKR_VOO_FRACTIONAL_COMMISSION_APPLICABILITY, INTERMEDIARY_FEE_USD, RECEIVING_FEE_USD |
| Dime! Thailand (KKP) | 0.00 | 1.91 | 0.00 | 17.89 | 20.10 | 0.67% | yes | `SCENARIO_ONLY` | `SYNTHETIC_QUOTE` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `SECURITY_ELIGIBILITY_UNKNOWN` | - |
| Webull Thailand (Manual) | 0.00 | 3.21 | 0.00 | 0.00 | 3.30 | 0.11% | no | `LOWER_BOUND_ONLY` | `UNKNOWN` | `ACCOUNT_SPECIFIC_UNVERIFIED` | `COST_EVIDENCE_INCOMPLETE` | WEBULL_MANUAL_FX_SPREAD |
| Webull Thailand (DCA - Promo 0%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| Webull Thailand (DCA - Standard 0.10%) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | no | `NOT_EVALUATED` | `NOT_APPLICABLE` | `ORDER_TYPE_INCOMPATIBLE` | `NOT_ELIGIBLE` | - |
| CASH / NO TRADE | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | yes | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `DOCUMENTED` | `CASH_NO_TRADE` | - |

No ranking is produced: unknown or hypothetical components can reverse any ordering. CASH / NO TRADE has zero friction and zero market exposure.

Sizing policy `FEES_DEDUCTED_FROM_ALLOCATION`: commission, VAT and per-share regulatory fees are bounded on each allocation and deducted from it; minimum-order and fractional checks use the post-fee notional. THB funding fees apply before conversion; USD deducted, intermediary and receiving fees apply after it.

## Disclosures (informational, not advice)

- Reference FX provenance: the reference rate is a scenario input. A daily central-bank reference rate is a `DAILY_REFERENCE_PROXY`, not a contemporaneous mid-rate; implied spreads against it include intraday movement.
- Cadence: batching months lowers fixed per-transfer and per-order charges but keeps savings in cash longer. No expected return is assumed, so the opportunity cost of waiting is disclosed, not computed.
- Portfolio risks: equity drawdown; bond duration/interest-rate risk; gold price risk; USD/THB currency risk on every USD asset; concentration in US-listed funds; inflation erodes THB cash; holding cash carries opportunity cost; historical drawdowns can be exceeded.
- Tax and jurisdiction (verify with a qualified adviser; no tax is calculated): US dividend withholding is 30% by default and may be 15% under the US-Thailand treaty with a valid W-8BEN; Thai rules on foreign income remitted from 2024 onward may apply; US estate tax may apply to US-situs assets above USD 60,000 for non-resident aliens (Form 706-NA); custody and broker-insolvency protection differ by platform and jurisdiction.

Before any real decision: observe a current FX quote per platform with a comparable reference timestamp; confirm per-security and fractional eligibility in the account; resolve conflicting commission terms; confirm funding-route fees and eligibility. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.
