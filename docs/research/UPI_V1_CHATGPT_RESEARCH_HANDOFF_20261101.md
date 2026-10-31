# UPI V1 — Research Handoff (for external research; not performed by the coding agent)

Each item is a question the code cannot answer without external sources. Return
answers with source URL, publication/effective date and quoted text.

## 1. Webull Thailand OpenAPI (interface documentation only)

Source: https://developer.webull.co.th/apis/docs/

- Which endpoints are read-only (account balances, positions, order history, market data)? List path, method, auth scheme.
- Is market data separately entitled or billed? Any subscription cost?
- Does a read-only scope exist without trading permission?
- Rate limits and data retention for transaction history.

Constraint: documentation only. No credentials, no calls, no paper/live activation.

## 2. Transaction exports (needed for V2 performance)

- Dime!: can the app export transaction history (buys, sells, dividends, withholding tax, FX conversions, fees) as CSV/PDF? Column list?
- Webull Thailand: same question.
- Bank FCD statement format: does it show interest accrual vs paid?

## 3. Look-through data

- Free, dated constituent weights for VOO, VT, VXUS, BND, BIL (issuer holdings files): URL, update frequency, licence terms.

## 4. Research utilization matrix inputs

For each, confirm the specific feature ACASH should mirror and whether the description below is accurate:

| Reference | Feature mirrored in UPI V1 | Status |
|---|---|---|
| Morningstar X-Ray | Allocation by bucket, concentration, overlap | Direct-holdings only; overlap NOT_ESTABLISHED |
| Portfolio Performance / Sharesight | Multi-account book, TWR/XIRR from transactions | Book done; performance needs V2 transactions |
| IBKR PortfolioAnalyst | Consolidated NAV across accounts | Done (snapshot) |
| Bloomberg PORT / Aladdin | Illustrative scenario stress | Simple parametric shocks only |
| Wealthfront | Cash-flow/reserve planning, contribution-first rebalancing | Done (no forecasts) |
| QuantConnect LEAN | Backtest benchmarks | Not used; existing ACASH engine retained |

## 5. Thai tax treatment (owner decision support)

- Withholding tax on US ETF dividends for Thai residents via Dime!/Webull; treatment of foreign-sourced income remitted to Thailand (2024+ rules). Effective dates.
