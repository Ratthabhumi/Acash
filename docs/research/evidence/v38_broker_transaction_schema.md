# ACASH V38 Normalized Broker Transaction Schema (Read-Only Offline Specification)

## 1. Purpose & Scope
This specification defines the normalized, read-only transaction data contract for future user-initiated imports across Interactive Brokers (IBKR), Dime! Thailand, and Webull Securities (Thailand).

**Strict Governance Boundaries:**
- **Zero Automated Connections**: No trading APIs, scrapers, or private banking/brokerage credential access.
- **User-Initiated Offline Files Only**: Historical transaction data must be exported manually by the user (e.g. IBKR Flex Query CSV/XML) and parsed locally.
- **No Fabricated Records**: Formats for Dime! and Webull Thailand exports remain unverified; broker-specific parsers are deferred until real sample files (with personal data redacted) are available.

---

## 2. Normalized Transaction Fields

| Field Name | Type | Description | Required | Example |
| :--- | :--- | :--- | :---: | :--- |
| `broker` | String | Identifier of the brokerage platform (`IBKR`, `DIME`, `WEBULL_TH`) | YES | `"IBKR"` |
| `transaction_id` | String | Unique transaction / execution ID provided by broker | YES | `"TRX-20261030-001"` |
| `transaction_datetime` | ISO-8601 UTC | Timestamp of order execution | YES | `"2026-10-30T14:30:00Z"` |
| `settlement_date` | Date | Settlement date (T+1 / T+2) | NO | `"2026-10-31"` |
| `symbol` | String | Ticker symbol in canonical format | YES | `"VOO"` |
| `action` | String | `BUY`, `SELL`, `DIVIDEND_CASH`, `INTEREST`, `FEE` | YES | `"BUY"` |
| `quantity` | Decimal | Executed quantity (supports fractional shares) | YES | `"0.5421"` |
| `price` | Decimal | Unit execution price in trade currency | YES | `"500.25"` |
| `trade_currency` | String | Currency of execution (`USD`) | YES | `"USD"` |
| `gross_amount` | Decimal | Gross amount before fees (`quantity * price`) | YES | `"271.19"` |
| `commission` | Decimal | Broker execution commission | YES | `"0.35"` |
| `other_fees` | Decimal | Regulatory/exchange fees (SEC, FINRA, etc.) | NO | `"0.02"` |
| `vat_amount` | Decimal | Applicable local VAT (e.g. 7% on Thai commissions) | NO | `"0.00"` |
| `fx_rate` | Decimal | Executed or settled THB/USD conversion rate, if converted by broker | NO | `"35.12"` |
| `net_amount_thb` | Decimal | Total THB deducted from user cash account | NO | `"9550.00"` |
| `source_file_sha256` | String | Cryptographic hash of the source export file | YES | `"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"` |

---

## 3. Platform Export Sources & Readiness Status

1. **Interactive Brokers (IBKR)**:
   - **Source**: Client Portal -> Reports -> Flex Queries (Custom Trade & Activity Reports).
   - **Format**: CSV or XML.
   - **Status**: `CAPABLE_USER_EXPORT_AVAILABLE` (Parser deferred until offline schema integration).
2. **Dime! Thailand (KKP Securities)**:
   - **Source**: In-app transaction statement export.
   - **Format**: UNVERIFIED (Typically PDF/CSV monthly statement).
   - **Status**: `UNVERIFIED_FORMAT` (Requires user-provided redacted sample).
3. **Webull Securities (Thailand)**:
   - **Source**: Webull App / Web Client transaction history.
   - **Format**: UNVERIFIED.
   - **Status**: `UNVERIFIED_FORMAT` (Requires user-provided redacted sample).
