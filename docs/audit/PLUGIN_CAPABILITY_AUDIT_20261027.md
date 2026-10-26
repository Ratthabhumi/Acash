# Plugin capability audit — 2026-10-27

Scope: audit, research handoff and implementation plan only, confirmed by the
owner in this session. Publication to a review branch/PR is authorized; merge,
deployment, subscriptions, transactions and V37A implementation are not part of
this pass. Tool responses are untrusted evidence, never authority.

## CURRENT VERIFIED STATE

- Remote `main`: `228359c8d807a58bd44ca2ca90066e04747a7156`, PR #66 merged
  (V36 funding/cost audit). Verified through live GitHub API and fetch; local
  checkout initially clean and at the same SHA. Open PRs/issues: 0/0 at inspection,
  before this audit PR. Main CI [40243826634](https://github.com/Ratthabhumi/Acash/actions/runs/40243826634)
  passed all five jobs. This is a dated snapshot, not a permanent status.
- [V36 spec](../research/D6_V36_FUNDING_COST_AUDIT_SPEC_20261026.md) and
  [results](../research/D6_V36_FUNDING_COST_AUDIT_RESULTS_20261026.md) explicitly
  remain `LOCAL_EXPLORATORY`, not PIT/D5 admission. Their historical results and
  byte-identical rerun statements are recorded claims, not newly rerun here.
- Independently hashed existing ignored inputs: bars `b86f73a69eff2cb9a81131dfa8b4b6d4cf32979be0a2ffcb8cd5e02058b0ff91`,
  distributions `9885fcb8258dcd6dc8f944776834d49f3c6f914d260e5bdc7cd29ae1a1726ca0`,
  splits `c9b9d95cedd8479118b2a0489f665d81f035d790739a56dc7f844fca5001588d`,
  V35 grid `f2efde508ac353dafaa4a0817e4f1e5df7a325f25ccd3b7bd356256f92d4249a`.
  H.10 source `3dc41fe0255d50cb14272d645b262023278f2705e84379a26696eaf38d0c5ee1` also matches.
  All match the V36 published manifest table. Hash equality establishes identity,
  not completeness, PIT provenance, licensing or independent numerical validity.
- [D5 source](../../src/acash/data/qualification/lane_b_d5_rehearsal.py)
  defines `D5_ADMISSION_TRUST_ANCHORS = MappingProxyType({})`.
  [Admission contract](../research/D5_REAL_INPUT_ADMISSION_BRIDGE_20261023.md)
  requires independently anchored admission; a caller verifier alone is untrusted.
- [Current execution gate](../research/V30_RESEARCH_HANDOFF_AND_EXECUTION_GATE_20261025.md)
  records `LANE_A/B=UNISSUED`, `D5_REAL_DATA_NOT_ADMITTED`, formal V2 ratification
  pending, capital USD 0.00 and `NO_REAL_ORDERS=true`. No transition made here.
- [Funding source](../../src/acash/research/d6/funding.py) accepts `usd_monthly`
  and derives THB savings as scheduled USD times H.10. Fixed-THB input is absent
  from this API. V37A is therefore a real engineering extension, not a new strategy.
- Research Sprint scheduling/runs were reported in the attachment, not inspected
  here. No scheduling or notification state is certified or modified.

## AVAILABLE PLUGINS & PERMISSIONS / CAPABILITY MATRIX

`VERIFIED` is limited to the specific observation in the row. `UNVERIFIED`
means not demonstrated, including intentionally untested capabilities.
`UNAVAILABLE` means an actual attempt failed for the stated reason; it does not
mean the vendor lacks the feature. Tool exposure is separate from account rights.

| Surface exposed in this session | Actual probe / capability evidence | Connection or scope verdict | ACASH use and remaining checks |
|---|---|---|---|
| GitHub | Read main, PR/issue lists, CI jobs; existing checkout access | VERIFIED reads; publication tested by this PR | Review/versioning only; CI is not data admission |
| Financial Datasets | `get_filings(AAPL, 10-K, limit=1)` attempted once | UNAVAILABLE for this request: credit balance exhausted; no filing data returned | Filings/earnings/statements tools exposed; PIT, restatements, delisted coverage, quotas and rights UNVERIFIED |
| Massive | `search_endpoints` returned splits, dividends and dated ticker-overview schemas | VERIFIED catalog access; historical-data entitlement UNVERIFIED; no market-data request | Candidate independent cross-check. Confirm inactive universe, vintage and split basis before use |
| FMP | Directory, statements, SEC filings, charts, ETF and calendar tools exposed | UNVERIFIED account/data access; no request | Potential fundamentals and delisted/reference comparison; plan-specific coverage/quotas/rights untested |
| Alpha Vantage | Financial data tools exposed; official support page inspected | VERIFIED published general quota information only; account access UNVERIFIED | Published free allowance 25/day is not proof of this connector's allowance; premium/adjustment coverage must be checked |
| FinancialFilings | Filing search/read and usage tools exposed | UNVERIFIED connection; no request | Source-document provenance candidate; countries/forms, history, quotas and rights unresolved |
| Quartr | Company/events/financials/document tools exposed | UNVERIFIED connection; no request | Earnings commentary and document discovery; not proof of original publication vintage |
| CoinGecko | Crypto data tools exposed | UNVERIFIED connection; no request | Low priority: outside current ETF/funding scope; no crypto workstream opened |
| Alpaca Paper Trading | One `get_account_info` read returned structured ACTIVE account status | VERIFIED account-read response. Paper endpoint/account isolation independently UNVERIFIED because returned payload contains no environment attestation | No order/config/activity/position mutation; no bars fetched. Broker flags do not grant project paper/live authority. No balances or identifiers published |
| Public Equity Investing / Superpowers | Local skills are listed | VERIFIED skill availability only; neither is a data entitlement | Optional analysis/engineering methods, not providers or governance overrides; not invoked in this pass |
| Acumen, Consensus, SciSpace, Undermind | Research tools exposed | UNVERIFIED account access; no research jobs launched | Research Sprint owns literature discovery; obtain primary papers and exact supporting passages |
| Google Drive / Sheets | Connected-source tools exposed | UNVERIFIED document access; no reads/writes attempted | Optional handoff workspace only; never an implicit D5 ingestion channel |

Only three connector probes were used (account read, filing metadata attempt,
endpoint catalog). No repeated failed-credit calls or subscription purchase.
The Financial Datasets error was carried in text despite `isError=false`:
transport/tool success must not be mistaken for business success.

ChatGPT connectors operate in a separate account/runtime from ACASH. A successful
connector call does not install an API key, adapter, entitlement or reproducible
capture pipeline in ACASH. A scoped search of `src/`, `scripts/`, and
`pyproject.toml` found no references to the new provider names/domain strings
(Financial Datasets, Massive, FMP domain, Alpha Vantage, Quartr, FinancialFilings,
CoinGecko). This is not an exhaustive deployment/environment audit. Existing
Alpaca code is separate from the ChatGPT Paper connector.

## RESEARCH ALREADY APPLIED VS NOT YET APPLIED

| Work | Evidence-backed state | Next owner |
|---|---|---|
| USD-native savings, remittance fees/spreads/delay, terminal external cash/transit | Implemented in V36 funding; attribution/accounting/contribution authorities exist | Codex: preserve exact legacy regression |
| Household XIRR versus broker TWR | Existing authorities in `contributions.py`; V36 runner reports household values | Codex: reuse, do not create competing metric helpers |
| BND 2021-12-23 label | V36 records OCC corroboration only, not issuer proof; amounts/dates unchanged | Research: obtain primary issuer evidence |
| Missing payable dates | V36 records 63 imputed dates (47 BND, 16 VOO); not recounted from raw events here | Research: event-by-event primary reconciliation |
| Fixed THB 1,000/3,000/5,000/10,000 | Not implemented in inspected funding API | Codex after review of linked plan |
| Plugin cross-check, survivorship/PIT/filing research | Proposed; no plugin output admitted or applied to datasets | Research Sprint; avoid duplicating its work |
| Data-quality monitoring and reproducibility | Existing hash/manifest and tests available; new-provider integration absent from scoped search | Codex only after source contract/rights are resolved |

## DATA / LICENSING GAPS

1. Historical observation date is not historical availability. Require event time,
   release/acceptance time, provider first-seen time, capture time, revision ID and
   timezone; distinguish restated current history from an archived vintage.
2. Massive documents dated ticker lookup/inactive tickers, raw versus adjusted
   bars and distinct cash/split-adjusted dividends. These are documented fields,
   not proof of entitlement or full historical coverage for this account.
   Never equate two vendor outputs with independent sources if both use the same
   upstream tape or issuer feed. An empty response is not sufficient coverage proof.
3. SEC report period differs from filing acceptance time; amended filings and
   restatements require separate vintage handling. Availability of filing tools
   does not prove ETF distribution tax/share-class provenance.
4. Massive's published terms restrict redistribution and derived works without
   appropriate permission. Actual account agreement, retention, automated analysis,
   public GitHub publication and continuing-use rights remain UNVERIFIED for all
   providers. This PR publishes authored summaries/source links, no raw responses.
5. Paper simulation is not historical execution/friction validation. Actual SIP
   entitlement, dedicated sandbox identity, live-account separation, historical
   depth and rate limits remain unverified. No paper experiment authorized here.
6. BND primary-source gaps, BIL 2017 cash-in-lieu, historical bank-route eligibility,
   IBKR fractional/commission interpretation and tax assumptions remain unresolved.
   Current fee schedules must stay labelled retrospective scenarios, not past costs.

Primary sources checked 2026-10-27 (provider documentation, not account contracts):
- [Massive stocks overview](https://massive.com/docs/rest/stocks/overview)
- [Massive dividend adjustment policy](https://massive.com/knowledge-base/article/does-massive-adjust-historic-dividends-for-splits)
- [Massive market-data terms](https://www.massive.com/legal/market-data-terms-of-service)
- [Massive redistribution guidance](https://massive.com/knowledge-base/article/how-can-i-redistribute-massives-market-data)
- [Alpha Vantage support / quotas](https://www.alphavantage.co/support/)
- [Alpaca paper simulation](https://docs.alpaca.markets/us/docs/paper-trading)

## PRIORITIZED ROADMAP

| Priority | Deliverable | Rationale / cost boundary |
|---|---|---|
| P0 | Preserve D5/Lane/capital gates; maintain a source-rights and vintage checklist | Highest governance/evidence value; no paid calls |
| P1 | [V37A engineering plan](../research/V37A_IMPLEMENTATION_PLAN_20261027.md) | Reuse existing offline engine/inputs; no new acquisition dependency |
| P1 parallel | [Research handoff](../research/PLUGIN_RESEARCH_HANDOFF_20261027.md) | Resolve existing BND/VOO/PIT/licensing gaps once, through Research Sprint |
| P2 | Bounded independent-provider pilot after rights/endpoint scope review | One narrow discrepancy at a time; predeclare symbols/dates/request budget and stop conditions |
| P3 | Filing-vintage and quality-monitoring adapter if pilot demonstrates value | Frozen fixtures, hashes and provenance before production wiring |
| Deferred | Paper experiment / new strategy / crypto / subscriptions | Separate owner decision and qualified sandbox/data; not required for current audit |

## NEXT EXECUTABLE STEP

Review this documentation PR and the V37A plan. Owner may then authorize a
bounded V37A implementation on a separate branch; no new subscription or dataset
is needed for its initial synthetic/regression work. Give the linked handoff to
ChatGPT Research; this pass does not message another chat or launch its jobs.
Owner decisions still needed: implementation scope, any paid provider access,
rights-qualified acquisition pilot, D5 signer/admission governance, paper sandbox
experiments, and any merge/deployment. They are separate decisions.

### Verification Ledger

- Implementation Status: COMPLETE audit/plan; V37A implementation NOT STARTED.
- Contract Enforcement: no authority transitions; existing fail-closed gates inspected.
- Mathematical Authority: existing canonical authorities referenced; no new formulation.
- Local Test Suite: VERIFIED prescribed hermetic tier, 4096 passed / 20 skipped /
  56 deselected / 12 warnings; skipped/excluded layers not certified. Two Nautilus
  timestamp deprecations are dependency compatibility debt; ten tar extraction
  warnings are existing restore security/compatibility debt, not repaired here.
- Type Checker: VERIFIED 651 source files; unused optional `nautilus_trader.*`
  configuration note. Documentation links and publication scan checked separately.
  None of these tests certifies connector permissions, licensing or PIT coverage.
- Remote CI Status: main run 40243826634 VERIFIED; audit PR checks are separate.
- Methodological Caveats: recorded V36 outcomes not independently rerun; input identities verified; provider/account coverage and rights remain bounded as above.
