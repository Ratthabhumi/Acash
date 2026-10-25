# V26 External Research Results (condensed, labelled)

- Classification: `EXTERNAL_RESEARCH_ARTIFACT` — operator-supplied research handoff
  (`OPERATOR_REPORTED`), condensed by the engineering agent on 2026-10-25.
- Not governance authority, not rights evidence, not dataset admission.
- No authenticated provider call, credential, or licensed raw dataset was used or is
  stored here. Issuer rows below are a short human-curated excerpt, not persisted source
  artifacts.

## R1 — Alpaca public documentation (`PUBLIC_DOCUMENTATION_ONLY`)

| Topic | Public finding |
|---|---|
| Basic plan | Free; historical data since 2016; 200 historical calls/minute documented |
| Bars endpoint | `GET /v2/stocks/bars`; symbol-first then timestamp ordering; `1Day` available |
| `limit` | Default 1000, range 1–10000; counts across **all** symbols; short pages may occur before the end; always follow `next_page_token` |
| `adjustment` | `raw`, `split`, `dividend`, `spin-off`, `all`; `all` is not an archived PIT event ledger |
| `asof` | Defaults to current day and changes symbol mapping; must be frozen and justified |
| `feed` | `sip` and `iex` are distinct; documented availability is not account entitlement |
| Corporate actions | `GET /v1/corporate-actions`, ≤1000 records/page, by process date; no PIT revision proof |
| Redistribution | Public FAQ: API data cannot be redistributed |

`UNKNOWN` until checked against the account's controlling agreement: entitlement, feed,
historical SIP access, archival retention, caching duration, derived internal research,
sharing, continued use after access ends. Single operator question: may a single-user
internal research project obtain 2016–2025 daily IEX/SIP ETF bars, retain verbatim JSON
pages with checksums locally, for how long, and use derived backtests internally without
redistribution — and which agreement/version controls?

## R2 — Corporate actions (partial; no census)

Example issuer rows (Vanguard, `PARTIAL_EVENT_EVIDENCE`, retrieved 2026-10-25,
`published_on=UNKNOWN`, `pit_vintage=UNKNOWN`):

| Ticker | Ex-date | Payable | USD/share |
|---|---|---|---|
| VOO | 2025-03-27 | 2025-03-31 | 1.812100 |
| VOO | 2025-06-30 | 2025-07-02 | 1.744700 |
| VOO | 2025-09-29 | 2025-10-01 | 1.740000 |
| VOO | 2025-12-22 | 2025-12-24 | 1.771000 |
| BND | 2025-11-03 | 2025-11-05 | 0.243631 |
| BND | 2025-12-01 | 2025-12-03 | 0.238572 |
| BND | 2025-12-18 | 2025-12-22 | 0.246638 |

- BIL: State Street "SPDR Historical Distributions XLSX" identified but not opened →
  `SOURCE_IDENTIFIED_NOT_EXTRACTED`.
- GLD: trust holds bullion and sells gold to pay expenses → `NO_CASH_DISTRIBUTION_ENTITLEMENT`
  (policy, not a dated negative-event census). Do not fabricate $0.00 events; do not
  deduct the expense ratio again from observed prices.
- Every year 2016–2025 stays not complete unless issuer rows plus a completeness proof exist.

## R3 — SEC Section 31 / FINRA TAF (`PRIMARY_SOURCE_VERIFIED` per handoff)

| Fee | Effective window | Rate |
|---|---|---|
| SEC §31 | 2023-02-27 .. 2024-05-21 | $8.00 per $1M sale principal |
| SEC §31 | 2024-05-22 .. 2025-05-13 | $27.80 per $1M (Fee Rate Advisory FY2024, Rel. 2024-47) |
| SEC §31 | 2025-05-14 .. 2025-12-31 | $0.00 per $1M (Rel. 34-104909; next change 2026-04-04) |
| FINRA TAF | 2024-01-01 .. 2025-12-31 | $0.000166/share sold, max $8.30/trade (Schedule A) |

Caveat: statutory/SRO rates, not proof of how a particular broker passes them through.
Integrated into the canonical `src/acash/execution/regulatory_fees.py` in V27.
