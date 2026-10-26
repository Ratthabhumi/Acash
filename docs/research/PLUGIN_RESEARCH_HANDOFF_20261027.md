# ChatGPT Research handoff — 2026-10-27

Use this brief with the existing Research Sprint; reconcile its completed work
first and research only unresolved items. Do not create duplicate scheduled
tasks. Sprint scheduling itself was not verified by the Codex audit.
Baseline: main `228359c8d807a58bd44ca2ca90066e04747a7156`,
[V36 results](D6_V36_FUNDING_COST_AUDIT_RESULTS_20261026.md),
[capability audit](../audit/PLUGIN_CAPABILITY_AUDIT_20261027.md).

## Research tasks, in order

1. BND capital-gain history: cover the attachment's 2016–2018 questions and
   V36's unresolved 2020/2021/2022 issuer originals. Reconcile reporting period,
   share class, CUSIP, split basis, event aggregation and rounding. OCC corroboration
   is not Vanguard original evidence. Do not replace event-level amounts with
   rounded annual totals or silently treat administrative labels as new amounts.
2. Payable dates: validate the recorded backlog of 47 BND + 16 VOO events;
   preserve unknown dates rather than guess. Resolve BIL 2017 cash-in-lieu basis.
3. PIT/licensing/provider pilot: compare a small predeclared sample only after
   endpoint rights/cost review. Investigate inactive/delisted coverage, historical
   vintages, release/acceptance/capture timestamps, restatements, adjustment basis,
   pagination, quotas, retention and derived-output redistribution. Document shared
   upstream dependencies; vendor agreement is not independent empirical replication.
4. Funding friction: settle IBKR US Tiered cap/fractional-rule ambiguities and
   Thai-resident entity/security eligibility with primary documentation. Identify
   legally eligible remittance routes, sender/intermediary/receiver fees, FX spread,
   settlement and applicable effective dates. H.10 is a reference, not retail FX.
   No transfer, bank contact or paid service is authorized by this brief.
5. D7 readiness/literature: existing accounting/funding limitations first; no new
   strategy hypotheses, optimization or claims of expected profitability. Clarify
   which questions require evidence, code correctness or an owner decision.

## Required return package

Return one concise unresolved-item table plus a machine-readable evidence index:
`question_id, symbol_or_entity, event_date, source_title, source_url,
accession_or_document_id, page_or_table, reporting_period, share_class,
publication_or_acceptance_time, captured_at_utc, timezone, vintage_or_revision,
raw_or_adjusted_basis, claim, supporting_excerpt, contradictory_evidence,
rights_scope, rights_source_url, status, remaining_gap`.

Use VERIFIED / UNVERIFIED / UNAVAILABLE per claim. Preserve quotations within
applicable rights; unknowns remain explicit. Source bytes and hashes may be
retained only where licensed, outside public Git. Hashes establish identity, not
source authenticity or a trusted historical timestamp. Do not publish account
identifiers, balances, credentials, full paid responses or restricted documents.

Financial Datasets currently refused the audited filing request for exhausted
credits: do not retry or purchase access automatically. Massive catalog access
was verified, historical entitlement was not. Other listed providers are tool
surfaces, not verified subscriptions. Use the best primary source first; do not
call every plugin or repeat Codex's funding-engine work.

Do not change ACASH datasets, D5 admission, Lane A/B, trust anchors or capital.
Return research as EXPLORATORY evidence for separate reconciliation and review.
`NO_REAL_ORDERS=true`; no paper/live trading, deployment or automatic promotion.
