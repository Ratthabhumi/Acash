# ETF Data Admission — Research Handoff (2026-10-14)

Source-linked handoff for the first bounded ETF data canary and subsequent
historical qualification. Labels: FACT / EVIDENCE / INFERENCE / PROPOSAL /
AUTHORIZATION. Nothing below is DATA_QUALIFIED evidence.

## FACT — Alpaca historical bars contract

- EVIDENCE: `start`/`end` are inclusive; multi-symbol pagination must be
  exhausted via `next_page_token`; `limit` counts total observations per
  page, not per symbol; explicit `feed` and `adjustment` parameters are
  required. Source: https://docs.alpaca.markets/us/reference/stockbars
  (verified 2026-10-14).
- EVIDENCE: Basic (USD 0) and Algo Trader Plus (USD 99/month) plan tables
  both list historical US equities coverage since 2016. A Plus subscription
  is NOT justified merely to obtain pre-2016 coverage. Basic limits only
  the most recent 15 minutes. Source:
  https://docs.alpaca.markets/us/docs/about-market-data-api
  (verified 2026-10-14).

## FACT — IBKR published fee assumptions

- EVIDENCE: US Stocks/ETFs published pricing includes Pro Tiered minimum
  USD 0.35/order and Pro Fixed minimum USD 1.00/order. Source:
  https://www.interactivebrokers.com/en/pricing/commissions-stocks.php
  (verified 2026-10-14). These are tariff assumptions, NOT account-verified
  charges. Actual economics also require spread, funding, FX, taxes, and
  pass-through fees.

## INFERENCE — IEX versus SIP

- IEX and SIP feeds are not assumed comparable: a run must bind exactly
  one operator-authorized feed, with no fallback. Comparability, if ever
  claimed, needs same-window dual-feed evidence — none exists here.

## INFERENCE — coverage and vintage limits

- Pre-2016 history is out of scope for the Alpaca path under current
  documentation; do not promise 2010–2015 coverage without a separate
  licensed source and its own qualification.
- Raw versus adjusted series, dataset vintage, and point-in-time
  correctness are unresolved for any future historical study; ticker
  mapping or adjusted snapshots alone do not establish PIT correctness.
- Corporate actions (dividends/splits) require issuer/sponsor evidence
  (Lane B); provider adjustment flags alone do not qualify them.

## PROPOSAL — first five-session canary (retrieval feasibility only)

- Scope: VOO, BND, GLD, BIL; 1Day; 2026-09-28 through 2026-10-02;
  adjustments raw and all; one authorized feed; max 12 operations;
  max 524288 observed response bytes; USD 0 paid; no retries; no fallback.
- A successful canary establishes retrieval/evidence feasibility ONLY —
  not historical profitability, not strategy selection.

## PROPOSAL — conditions for historical portfolio evaluation

- Qualified multi-year prices, qualified distributions/splits, explicit
  return basis, inception boundaries, consistent currency, modeled-vs-actual
  cost reconciliation, PIT-safe macro inputs, and preregistered baselines
  (cash/no-trade, equity buy-and-hold, equity/bond mix, low-turnover mix
  on hypothetical USD 1,000).

## AUTHORIZATION — explicitly absent

- Lane A packet: UNISSUED. No provider HTTP, no credentials, no paid
  subscription, no broker authentication, no paper/live orders, no capital.
  Real capital authority remains USD 0.00 with `NO_REAL_ORDERS=true`.
