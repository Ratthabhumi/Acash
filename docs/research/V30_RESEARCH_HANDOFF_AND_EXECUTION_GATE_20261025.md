# ACASH V30 — Research Handoff and Minimal Execution Gate (2026-10-25)

Status: **RESEARCH HANDOFF / NO NEW AUTHORITY**. Baseline: `main` `0f7d50b7b5c4e2ebbb99e494503316dc89286a80`, merged PR #58, main CI run `40169052956` success. This document does **not** ratify research contracts or authorize external acquisitions.

## 1. What is already implemented (do not rebuild)

- V25–V26: independent D5 admission record; V26 independent acquisition-envelope signature verification. Production anchors remain **EMPTY**.
- V27: mock-only D1–D5 offline harness, fee schedules through 2025-12-31, five USD 1,000 D6 comparators, event-source ledger.
- V28: fee-defect correction artifact for frozen HYP_007, multiple same-ex-date events, structural cash/split census, prior-close/next-open sizing, synthetic FX reporting.
- V29: negative-cash/uneconomic-order guards, ledger cash reconciliation, `SOURCE_BYTES_RECONCILED` trust ceiling for caller-provided corporate-action evidence.
- D6 A1 (descriptive comparison) and A2 (causal execution timing) are both **PROPOSED_UNRATIFIED**. No real-data D6 run.
- `REAL_CAPITAL_AUTHORITY=USD 0.00`, `NO_REAL_ORDERS=true`, `LANE_A/B=UNISSUED`, `D5_REAL_DATA_NOT_ADMITTED`, `V2_FORMAL_RATIFICATION=PENDING`. HYP_003 remains terminally falsified.

## 2. Short research brief for ChatGPT Research (research ONLY; no bulk downloads)

### R30-A — Issuer exports and rights (highest priority)

For **VOO/BND** locate the official Vanguard distribution export, ascertain **actual earliest and latest ex-date available**, whether 2016-01-01..2016-12-31 is complete, whether income and capital-gain events are separately present, and identify official archives filling a 2016 gap. The public page says **up to ten years**: this is NOT proof that January 2016 is covered in October 2026.

For **BIL** identify the actual issuer SPDR Historical Distributions XLSX document URL, version, date range, fund identifier, split/other-action references and issuer rights; link discovery is NOT extraction or coverage.

For **GLD** check issuer/SEC (SPDR Gold Trust SEC CIK **1222333**) for a complete 2016–2025 split/reverse-split history and the distinction between *no dividends* and *no share splits*. Secondary services report no splits but do NOT prove a full official negative-event census. The issuer GLD page has a separate **Historical Archive (XLSX)**; research what its content actually is before claiming it contains corporate actions. Do not treat ordinary gold redemptions as shareholder cash dividends.

For each source: identify official document/terms URL; publication/version date; coverage; rights for one-person internal noncommercial research, normalization, raw private retention, automated access and derived results; whether written permission is required. Never equate public accessibility with redistribution permission. **Do not download protected bulk archives or request access through authentication** under this handoff.

Official candidate sources:
- https://advisors.vanguard.com/investments/products/voo/vanguard-sp-500-etf
- https://advisors.vanguard.com/investments/products/bnd/vanguard-total-bond-market-etf
- https://investor.vanguard.com/terms-conditions
- https://www.ssga.com/us/en/institutional/resources/documents/etf-dividend-distributions
- https://www.ssga.com/us/en/footer/terms-and-conditions
- https://www.spdrgoldshares.com/usa/gld/
- https://www.spdrgoldshares.com/terms-and-conditions/
- https://www.sec.gov/edgar/browse/?CIK=1222333

### R30-B — Account rights, not API capabilities

Check controlling Alpaca agreement or obtain provider confirmation for **account-specific** historical SIP/IEX access, verbatim JSON retention, private derived research, retention period, after-termination usage, and governing agreement version. Public documentation alone cannot establish these rights. Confirm daily bars `end` exclusivity, pinned `asof`, feeds and adjustments for the proposed scope, using documentation only; no authenticated API calls.

Official documentation:
- https://docs.alpaca.markets/us/docs/about-market-data-api
- https://docs.alpaca.markets/us/docs/market-data-faq
- https://docs.alpaca.markets/us/reference/stockbars

### Required ChatGPT research output

Return one compact Markdown report: `V30_EXTERNAL_RESEARCH_RESULTS_20261025.md`. Each claim needs primary-source URL and checked date. Table columns:
`question | finding | evidence URL | effective/publication date | evidence class | unresolved dependency | engineering consequence`.
Use `PRIMARY_SOURCE_VERIFIED`, `SECONDARY_INDICATION_ONLY`, `SOURCE_IDENTIFIED_NOT_EXTRACTED`, `RIGHTS_UNKNOWN`, or `UNKNOWN`. Do not fabricate coverage. Propose targeted questions to licensors; do not contact anyone automatically.

## 3. Minimal continuation order for Codex

1. First inspect actual `main`, PR #58, current CI and `docs/research/V29_EVIDENCE_CLOSURE_DECISION_PACKET_20261025.md`.
2. **Do not run broad engineering phases again.** With no independently verified regression or new licensed source, there is no justified repeat of F01–F06 or D1–D6.
3. Once R30-A/B results arrive, reconcile evidence into the corporate-action source ledger **without elevating claims**. Rights and issuer authentication remain separate from bytes/row reconciliation.
4. If a real, authorized issuer artifact is provided, implement only its missing parser/adapter and its tests; preserve source bytes privately only if licensed. No real D5 admission without a genuine independent anchored admitter.
5. Prepare a dated, hash-bound owner ratification for A1/A2 **only after explicit owner approval naming both amendments**. Do not infer ratification from this directive.
6. Provider acquisition requires a separately ratified V2, account-specific data rights, strictly bounded authority and independent admitter review. Proposed budget `32 requests / 8,388,608 observed bytes` is a *simulation*, not granted authority; `limit=1000`, `raw+split`, explicit `feed` and `asof`, zero retry.
7. Open a coherent PR for **genuinely new** evidence integration or verified defect only; check exact-head CI, review and merge under branch protection, then verify post-merge CI. Avoid documentation churn and arbitrary extra PRs.

## 4. Human gates and current limit

- Owner decision: A1 + A2 ratification (both unratified).
- Issuer-specific permission for private extraction, normalization and retention (unverified).
- Alpaca controlling agreement and actual account rights (unknown).
- Actual ten-year cash-distribution/split coverage (currently **0/40** full symbol-year cells qualified).
- Separate custody and independently reviewed production admitter/trust anchor (absent).
- Separate acquisition authority for a bounded pilot (UNISSUED).

**Next milestone:** lawful, rights-scoped primary-source pilot with original-byte receipts and partial-coverage labels. No full-period D6 inference, no paper/live orders.

## 5. Research notes verified in this ChatGPT handoff

- Vanguard terms grant limited personal informational noncommercial viewing/downloading, but explicitly restrict derivative uses absent further authorization: https://investor.vanguard.com/terms-conditions
- Vanguard VOO product page advertises an export of *up to ten years*, with no proof here of exact 2016 completeness: https://advisors.vanguard.com/investments/products/voo/vanguard-sp-500-etf
- Official GLD sponsor page identifies GLD CUSIP `78463V107` and offers a `Historical Archive (XLSX)`; **contents/date coverage not inspected here**: https://www.spdrgoldshares.com/usa/gld/
- SEC-hosted GLD material discusses 2016 and subsequent price history, but does **not establish a complete no-split census**: https://www.sec.gov/Archives/edgar/data/1222333/000119312516688586/d157574dfwp.htm

Research notes are discovery/provisional evidence, **not** rights certification, PIT vintages, or dataset admission.
