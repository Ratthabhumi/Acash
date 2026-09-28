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
  - US dividends paid to a Thai resident with a valid W-8BEN are subject to a maximum US withholding tax of **15.0%** at source.
  - Taxes legitimately paid to the US Internal Revenue Service (IRS) may generally be claimed as a Foreign Tax Credit (FTC) against Thai personal income tax on the same income, up to the amount of Thai tax attributable to that foreign income.

### 2.4 Broker-Neutral Tax Truth
- Broker choice (e.g. Dime! vs. Webull vs. Interactive Brokers) does **not** alter Thai statutory tax liability.
- Thai tax liability is determined by residency, income realization, and remittance into Thailand, not by the broker's marketing label. Claims that any specific broker "avoids tax" are legally spurious.

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

    # Currency & BOT Exchange Rate Lineage
    bot_reference_fx_rate: Decimal     # Bank of Thailand official daily counter rate
    gross_amount_thb: Decimal          # gross_amount_usd * bot_reference_fx_rate

    # Realized Capital Gains (SELL events)
    cost_basis_method: str             # FIFO / AVERAGE_COST
    cost_basis_usd: Decimal
    realized_gain_loss_usd: Decimal
    realized_gain_loss_thb: Decimal

    # Dividend & Withholding Taxes
    foreign_withholding_tax_usd: Decimal
    foreign_withholding_tax_thb: Decimal
    jurisdiction_withholding: str      # e.g. "US" (W-8BEN 15%)

    # Statutory Document Provenance
    source_document_name: str          # e.g. "Dime_Statement_202609.pdf"
    source_document_sha256: str        # Immutable SHA-256 of official statement
```

---

## 4. Remittance Tracking & Matching Engine

The critical accounting challenge under Thai tax law is tracing whether remitted funds constitute:
1. **Original Principal (Capital):** Repatriation of after-tax savings previously remitted abroad (non-taxable return of capital).
2. **Realized Capital Gains / Offshore Profits:** Assessable income subject to Thai PIT.

The ACASH Tax Engine maintains an unbroken cash ledger separating **Deposited Principal** from **Realized Profit**:
- When funds are remitted to Thailand, the engine supports both **Specific Identification** and **Pro-Rata Gain/Capital Matching**, allowing the operator and accountant to review the exact tax lot breakdown.

---

## 5. Verification Ledger

- Requirements Scope: COMPLETE (2026 Thai RD Guidelines Ingested)
- Legal Boundaries: NON-ADVISORY / EVIDENCE LEDGER ONLY
- Statutory Basis: Section 41, Paw 161/2566, Paw 162/2566, US-Thai DTA
- Status: `TAX_INTERPRETATION_REQUIRES_HUMAN/PROFESSIONAL_REVIEW = true`
