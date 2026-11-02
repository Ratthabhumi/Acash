# UPI V1 — Research Handoff (for external research; not performed by the coding agent)

Each item is a question the code cannot answer without external sources. Return
answers with source URL, publication/effective date and quoted text.

Facts marked "owner-supplied" were returned by external research (ChatGPT) on
2026-11-01 and are recorded as received. The coding agent did not verify them and
no code depends on them.

## 1. Webull Thailand OpenAPI (interface documentation only)

Source: https://developer.webull.co.th/apis/docs/

Owner-supplied: read-only account/data APIs exist; the historical-orders endpoint
covers 7 days; market data requires a separate subscription; data API rate limit
300 requests / 60 s.

Still open:
- Exact read-only endpoint list (path, method, auth scheme) and whether a read-only scope exists without trading permission.
- Transaction history beyond 7 days (dividends, withholding, FX, fees): available through any endpoint or export?
- Market-data subscription cost and terms.

Constraint: documentation only. No credentials, no calls, no paper/live activation.
Engineering status: BLOCKED_BY_AUTHORIZATION (broker connectivity is not authorized).

## 2. Transaction exports (needed for V2 replay of real data)

Owner-supplied: Dime! and Webull export formats are unverified.

Owner-supplied (2026-11-02): Webull Thailand documents trade confirmations and monthly
statements downloadable as PDF or CSV
(https://www.webull.co.th/help/faq/494-Can-I-export-my-trading-transactions-to-Excel-or-CSV-format).
Dime! documents requesting FCD statements
(https://dime.co.th/th/articles/how-to-request-dime-fcd-statement). Neither establishes a
column schema, and an FCD statement is not assumed to contain stock trades. Status:
BROKER_NATIVE_IMPORT_NOT_ESTABLISHED until a redacted sample exists.

- Dime!: can the app export transaction history (buys, sells, dividends, withholding tax, FX conversions, fees) as CSV/PDF? Column list, date/time zone, decimal format?
- Webull Thailand: same question.
- Bank FCD statement: does it show interest accrual vs paid?

V2 accepts only `ACASH_CANONICAL_TRANSACTIONS_V1` JSON. A broker mapping contract
can be written only after a real redacted sample format is supplied.

## 3. Look-through data

Owner-supplied candidate sources: Vanguard issuer holdings files, SEC N-PORT
filings, TickerInside (licence check required).

Still open: licence terms permitting local storage, update frequency and as-of date
semantics for VOO, VT, VXUS, BND, BIL; N-PORT reporting lag.

## 4. Research utilization matrix

| Reference | Feature mirrored | Status |
|---|---|---|
| IBKR PortfolioAnalyst | Consolidated NAV across accounts (snapshot) | IMPLEMENTED_AND_TESTED |
| Portfolio Performance / Sharesight | Transaction ledger, FIFO lots, TWR/XIRR from flows | IMPLEMENTED_AND_TESTED (synthetic only, V2) |
| Wealthfront | Reserve planning, contribution-first allocation (cent-exact) | IMPLEMENTED_AND_TESTED |
| Morningstar X-Ray | Allocation, concentration | PARTIALLY_IMPLEMENTED (direct holdings only; look-through WAITING_FOR_EVIDENCE) |
| Bloomberg PORT / Aladdin | Scenario stress | PARTIALLY_IMPLEMENTED (illustrative parametric shocks only) |
| Benchmark-relative performance | Benchmark comparison | WAITING_FOR_EVIDENCE (no admitted benchmark series) |
| FX attribution | Currency vs local return split | DOCUMENTED_ONLY (FX_ATTRIBUTION_NOT_ESTABLISHED) |
| Webull read-only API | Automated position import | WAITING_FOR_EVIDENCE + authorization |
| Dime! FCD statement / Webull monthly CSV | Native import mapping | WAITING_FOR_EVIDENCE (channel documented, schema not) |
| Broker-displayed totals (V1_2) | Account/sub-portfolio total reconciliation, unclassified residual | IMPLEMENTED_AND_TESTED (synthetic) |
| Security identifiers (ISIN/FIGI/MIC) | Non-merging of unverified tickers | IMPLEMENTED_AND_TESTED (format checks only; no security master) |
| NYSE hours/calendar | Market-session validation | DOCUMENTED_ONLY (MARKET_SESSION_NOT_VERIFIED). Source confirmed (nyse.com hours-calendars, 2026–2028). An offline fixture still needs the exact holiday and early-close date list, quoted from that page, to avoid typing dates from memory |
| Broker fees / FX route costs | V38 route cost engine | PARTIALLY_IMPLEMENTED (owner quote evidence still open) |
| ETF holdings (Vanguard, QQQM, SEC N-PORT) | Look-through | WAITING_FOR_EVIDENCE |
| Alpaca / IBKR / Settrade | Broker capability registry | DOCUMENTED_ONLY (not built; no adapters) |
| Thai/US tax | After-tax return | DOCUMENTED_ONLY |
| QuantConnect LEAN | Backtest engine | NOT_RELEVANT_CURRENT_SCOPE |

## 5. Tax treatment (owner decision support)

Owner-supplied: US dividend withholding 30% unless a treaty rate applies via
W-8BEN; Thai foreign-sourced income rules changed from 2024 and need
product-specific interpretation.

Still open: the Thailand–US treaty dividend rate as applied by Dime!/Webull custody
chains; whether remittance timing of FCD balances triggers Thai assessable income;
effective dates. V2 records DIVIDEND_WITHHOLDING as observed amounts only and makes
no tax computation.
