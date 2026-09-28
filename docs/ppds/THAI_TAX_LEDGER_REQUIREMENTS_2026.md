# ACASH Thai Tax Evidence Ledger Requirements (2026 Guidelines)

**Document:** `docs/ppds/THAI_TAX_LEDGER_REQUIREMENTS_2026.md`
**System Module:** Tax Evidence Ledger & Regulatory Accounting
**Jurisdiction:** Kingdom of Thailand (Revenue Department — กรมสรรพากร)
**Stage:** R0 Accounting Requirements & Data Architecture
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 1, 3, 4

---

## 1. Executive Summary & Legal Disclaimer

ACASH is explicitly **NOT an autonomous legal or tax adviser**. The system does not provide automated tax counsel or make binding tax liability determinations.

The purpose of the **ACASH Tax Evidence Ledger** is to maintain an immutable, double-entry audit trail of offshore capital gains, cash distributions, withholding taxes, broker fees, currency exchanges, and repatriation remittances. This ledger exports structured, cryptographic evidence for:
1. Operator personal inspection and records.
2. Independent review by certified public accountants or tax attorneys.
3. Accurate documentation supporting annual Personal Income Tax (PIT) filings (Form P.N.D. 90/91) to the Thai Revenue Department.

> **MANDATORY GOVERNANCE NOTICE:**
> `TAX_INTERPRETATION_REQUIRES_HUMAN/PROFESSIONAL_REVIEW = true`
> All tax classifications are documented as timestamped evidentiary schemas, not self-executing legal judgments.

---

## 2. Thai Statutory Tax Context (2026 Regulatory Landscape)

Based on primary guidance from the Thai Revenue Department (including Departmental Instruction No. Paw 161/2566, Paw 162/2566, and the official 2026 Guide on Taxation of Foreign-Source Income):

### 2.1 The 180-Day Tax Residency Rule (Section 41 Paragraph 3)
- An individual who resides in Thailand for an aggregate period of **180 days or more** in any calendar tax year (1 January to 31 December) is deemed a **Tax Resident of Thailand** for that tax year.
- Non-residents are not subject to Thai personal income tax on foreign-source income that is not derived from sources in Thailand.

### 2.2 Foreign-Source Income & Remittance Rule
- Assessable income derived from offshore sources (foreign employment, foreign business, or foreign capital gains and dividends from foreign securities):
  - If a Thai tax resident brings (remits) that foreign-source assessable income into Thailand, it must be included in the individual's annual personal income tax computation.
  - Under the current Revenue Department interpretation (effective 1 January 2024 onwards), foreign assessable income remitted into Thailand is taxable **regardless of the calendar year in which the income was originally earned**, subject to transitional provisions.

### 2.3 Double Taxation Agreements (DTA) & Foreign Tax Credits (FTC)
- Under the **US–Thailand Double Taxation Agreement (DTA)**:
  - Form W-8BEN is statutory documentation executed by a foreign individual to establish non-US status and, where eligible, claim applicable bilateral treaty benefits. Form W-8BEN is not itself a tax levy.
  - Under Article 10 (Dividends) of the US–Thailand DTA, the tax imposed by the US on gross dividends paid to an eligible Thai resident beneficial owner is capped at:
    - **10%** in the qualifying corporate-control case specified by the treaty.
    - **15%** of gross dividends in all other ordinary beneficial-owner cases.
    - Per Article 10 Paragraph 3, dividends paid by a US Regulated Investment Company (RIC / ETF) are governed by the 15% rule rather than the corporate-control rule.
    - Therefore, for an ordinary Thai individual beneficial owner of US equities and ETFs, 15% represents the statutory treaty withholding ceiling, subject to treaty eligibility, beneficial-owner verification, proper documentation, and applicable exceptions.
  - Taxes legitimately paid to the US Internal Revenue Service (IRS) may generally be claimed as a Foreign Tax Credit (FTC) against Thai personal income tax on the same income, up to the amount of Thai tax attributable to that foreign income.
  - All classifications remain subject to mandatory professional review (`TAX_INTERPRETATION_REQUIRES_HUMAN/PROFESSIONAL_REVIEW = true`).

### 2.5 Foreign Exchange Valuation Rule (Section 9 Revenue Code)
- Under Section 9 of the Thai Revenue Code and the Ministry of Finance / Revenue Department Notification on Exchange Rates:
  - Conversion of foreign currency into Thai Baht for assessable income computation may utilize, subject to the applicable statutory context:
    1. The daily exchange rate announced by a commercial bank established under Thai banking law; OR
    2. The daily reference exchange rate announced by the Bank of Thailand (BOT).
  - Under the statutory announcement, once a taxpayer selects an authorized exchange rate computation method, consistency must be maintained across tax years unless formal approval for method change is obtained.
  - Hardcoding BOT reference rates as the sole canonical tax truth is legally ungrounded. The ledger must preserve the chosen method, exchange rate provider, rate type (e.g. buying telegraphic transfer vs reference rate), and effective date:
    ```text
    TAX_FX_METHOD = HUMAN_PROFESSIONAL_POLICY_REQUIRED
    ```

---

## 3. Required Data Schema for the Tax Evidence Ledger

To support verifiable tax accounting, the ledger records discrete events across the investment and trading lifecycle:

```python
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum, auto

class TaxEventType(Enum):
    SECURITY_BUY = auto()
    SECURITY_SELL = auto()
    DIVIDEND_PAYMENT = auto()
    FOREIGN_WITHHOLDING_TAX = auto()
    BROKER_FEE = auto()
    FX_CONVERSION = auto()
    REMITTANCE_INTO_THAILAND = auto()
    CAPITAL_REPATRIATION = auto()

@dataclass(frozen=True)
class TaxEvidenceRecord:
    event_id: str                      # Unique cryptographic hash of transaction
    event_type: TaxEventType
    timestamp_utc: datetime
    timestamp_ict: datetime            # UTC+7 local tax timestamp
    tax_year: int                      # Calendar tax year (e.g. 2026)
    broker_code: str                   # DIME, WEBULL_TH, IBKR
    account_number_masked: str         # Masked account identifier (e.g. ***1234)
    symbol: str                        # US Ticker (e.g. VOO, QQQM)
    asset_class: str                   # US_EQUITY, US_ETF, CME_FUTURE
    quantity: Decimal
    executed_price_usd: Decimal
    gross_amount_usd: Decimal

    # Currency & Tax FX Lineage (Section 9 Revenue Code)
    # TAX_FX_METHOD = HUMAN_PROFESSIONAL_POLICY_REQUIRED
    tax_fx_method: str                 # BOT_REFERENCE or COMMERCIAL_BANK_DAILY
    tax_fx_source: str                 # e.g. "BOT", "SCB", "KBANK", "BBL"
    tax_fx_rate: Decimal               # Converted rate
    tax_fx_rate_type: str              # REFERENCE, BUYING_TT, MID_RATE
    tax_fx_effective_date: date
    tax_fx_source_reference: str       # Link or publication identifier
    gross_amount_thb: Decimal          # gross_amount_usd * tax_fx_rate

    # Realized Capital Gains (SELL events)
    # TAX_COST_BASIS_METHOD = HUMAN_PROFESSIONAL_DETERMINATION_REQUIRED
    # All underlying lot lineage preserved; method is an external accounting parameter
    cost_basis_method: str             # e.g. "FIFO", "SPECIFIC_LOT", "AVERAGE"
    cost_basis_usd: Decimal
    realized_gain_loss_usd: Decimal
    realized_gain_loss_thb: Decimal

    # Dividend & Withholding Taxes
    foreign_withholding_tax_usd: Decimal
    foreign_withholding_tax_thb: Decimal
    jurisdiction_withholding: str      # e.g. "US" (US-Thailand DTA Art. 10 15% via Form W-8BEN)

    # Statutory Document Provenance
    source_document_name: str          # e.g. "Dime_Statement_202609.pdf"
    source_document_sha256: str        # Immutable SHA-256 of official statement
```

---

## 4. Remittance Evidence & Tracing Architecture

The statutory challenge under Thai tax guidelines is distinguishing between:
1. **Original Principal (Capital):** Repatriation of after-tax personal savings previously remitted abroad (non-taxable return of capital).
2. **Realized Foreign Income:** Offshore gains, dividends, or interest remitted to Thailand by a tax resident.

### Legal Boundary Notice:
The Thai Revenue Department has not published a binding, universal statutory formula mandating either "FIFO lot-matching" or "pro-rata gain-capital apportionment" for individual offshore equities. Encoding either method as legal ground truth violates ACASH research standards:
```text
TAX_COST_BASIS_METHOD            = HUMAN_PROFESSIONAL_DETERMINATION_REQUIRED
TAX_REMITTANCE_CHARACTERIZATION  = HUMAN_PROFESSIONAL_REVIEW_REQUIRED
```

### `RemittanceEvidenceLink` Data Contract:
Instead of making unilateral legal determinations, PPDS records an unbroken evidentiary link preserving:
- Source brokerage and bank accounts.
- Source cash deposit history (inbound principal).
- Realized gains, losses, and cash dividend receipts.
- Inter-broker and multi-currency transfers.
- Actual quoted conversion rates and bank FX counter slips.
- Repatriation timestamp, remittance destination, and receiving Thai bank statement hashes.

This structured evidence enables certified public accountants and tax counsel to compute and justify alternative allocation views (e.g. principal-first, pro-rata, or specific identification) during tax filing preparation without destroying underlying lot lineage.

---

## 5. Verification Ledger

- Requirements Scope: COMPLETE (Thai Revenue Code § 9 & § 41, Paw 161/2566, Paw 162/2566)
- Legal Boundaries: NON-ADVISORY / EVIDENCE LEDGER ONLY
- Foreign Exchange Valuation: `TAX_FX_METHOD = HUMAN_PROFESSIONAL_POLICY_REQUIRED` (Commercial Bank vs BOT)
- Cost Basis Status: `TAX_COST_BASIS_METHOD = HUMAN_PROFESSIONAL_DETERMINATION_REQUIRED` (Lot lineage preserved)
- Remittance Tracing: `TAX_REMITTANCE_CHARACTERIZATION = HUMAN_PROFESSIONAL_REVIEW_REQUIRED`
- Statutory Lineage: Section 41, Section 9, US-Thai DTA Article 10
- Execution Status: STRICTLY $0.00 / NO REAL ORDERS
