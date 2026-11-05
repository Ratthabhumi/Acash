# Research Utilization Ledger (V107, 2026-11-05)

What ACASH has built, what is actually usable for a decision, and what is still missing. Statuses are
deliberately narrow: `INTEGRATED` means the output is computed from qualified inputs and shown in the
dashboard, not that it is profitable or admissible.

| Area | Status | Evidence / limitation |
| --- | --- | --- |
| Massive EOD + Parquet warehouse | **INTEGRATED** | 26 partitions, SHA-256 verified, `storage_rights: PERMITTED` under ODR-004 amendment 004 |
| Massive Grouped Daily (1 request/session) | **INTEGRATED** | production collector, 1 request for 2026-11-04, `failed=0` |
| Point-in-time security identity | **PARTIALLY_INTEGRATED** | registry + quarantine gate live; SPCX identity is unresolved (ticker reuse) |
| OpenFIGI identity mapping | **INTEGRATED** | owner confirmation recorded; venue status still per-instrument |
| Economic classification | **INTEGRATED** | 28/28 holdings classified |
| NYSE session calendar | **INTEGRATED** | XNYS fixture only; other venues not covered |
| BOT USD/THB reference FX | **INTEGRATED** | 142 reference points; reference rate, never executable |
| THB return decomposition | **RESEARCH_ONLY** | hypothetical fixed-weight basket, `PRICE_RETURN_ONLY`, not realized performance |
| Research cohorts (established / recent inception) | **RESEARCH_ONLY** | NASA included only in the exploratory cohort; SPCX now excluded |
| Portfolio valuation (PPDS/UPI) | **INTEGRATED** | 28 position rows; cash and broker residual excluded from holdings |
| FIFO / TWR / XIRR engines | **ENGINE_IMPLEMENTED_DATA_PENDING** | no complete life-of-account transaction journal |
| Dime! tax evidence | **PARTIALLY_INTEGRATED** | annual aggregate staged; dividends/withholding not itemised; liability NOT_ESTABLISHED |
| V38 fee / route cost research | **ENGINE_IMPLEMENTED_DATA_PENDING** | no broker fee schedule or FX spread evidence |
| ETF look-through / overlap | **BLOCKED** | no dated, rights-qualified holdings file → `OVERLAP_NOT_ESTABLISHED` |
| Windows warehouse sync | **INTEGRATED** | delta transfer, hash-verified cutover, 0 provider calls |
| Windows scheduled sync | **PARTIALLY_INTEGRATED** | Task Scheduler script prepared; not yet registered on the workstation |
| Off-device backup | **DEFERRED** | no independent destination (`/data/backups` is same-HDD) |
| Homelab daily collector | **INTEGRATED** | timer active, service success, next run 2026-11-06 13:00 ICT |
| Execution / orders | **BLOCKED (by contract)** | `NO_REAL_ORDERS=true`, authority USD 0.00 |

## SPCX identity decision (P0)

The stored SPCX series (455 sessions, 2024-11-04 → 2026-11-04) contains two securities: the SPAC and New
Issue ETF (last bar 2026-04-06, ~$22) and Space Exploration Technologies common stock (first bar
2026-06-12, ~$161). A return across 2026-06-12 would be a fabricated +600%.

- the bytes stay in the warehouse, hash-verifiable;
- `docs/research/evidence/security_identity_registry.json` records both identities and the rename gap;
- `security_identity.research_eligibility` marks the series `MULTI_IDENTITY` → excluded from every
  return calculation, with `assert_single_identity` available as a hard gate;
- the cohorts are rebuilt offline: ESTABLISHED 24 instruments / 404 sessions, RECENT 25 / 152, both
  excluding SPCX and reporting the reason;
- the readiness contract reports `decision_readiness: BLOCKED` while the identity is unresolved.

No price was fabricated and no history was bridged.

## What would move each blocked item forward

1. SPCX: confirm the FIGI/CUSIP and listing interval of the new listing, then add a verified registry
   entry and re-admit only the post-listing sessions.
2. Realized performance: export the complete trade and cash-flow history (Dime!), then use the existing
   accounting engine — no new engine.
3. ETF look-through: a dated, rights-qualified holdings file per fund; otherwise stay
   `OVERLAP_NOT_ESTABLISHED`.
4. Off-device backup: an independent destination and a restore drill.

## PR chain

`main` is still at `a6eae54`; PRs #71–#80 are stacked and unmerged. Integration into main needs a
dependency review, not a blind merge of #80. This ledger records repository state only.
