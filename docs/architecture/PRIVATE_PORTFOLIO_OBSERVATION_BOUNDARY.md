# Unified Portfolio Intelligence V1 — Private Observation Boundary

Status: **V1.1 IMPLEMENTED (synthetic fixtures verified). Owner-private runtime GATED by `docs/governance/ODR_UPI_PRIVATE_OBSERVATION_001.json` (PROPOSED_NOT_RATIFIED).**

## 1. Purpose

Give the owner a read-only, offline book of record for personal holdings across
brokers and banks (NAV, allocation, concentration, capacity, decision status)
without creating a second ledger, without broker access and without any
trading, transfer or capital authority.

## 2. Component reuse (no second ledger)

| Component | Status | Role in UPI V1 |
|---|---|---|
| `src/acash/ppds/ledger.py` / `lots.py` | UNCHANGED | Historical acquisition lots; snapshots no longer build lots (V1.1), so no cost or acquisition date is invented |
| `src/acash/ppds/exposure.py` `evaluate_portfolio_base_currency` | EXTENDED (signature only) | Accepts the `ValuationSource` protocol; the ledger and the snapshot `SnapshotValuationView` both satisfy it |
| `src/acash/ppds/registry.py` `AccountRegistry`, `consolidate_portfolio_valuations` | REUSED | Multi-account consolidation per report currency |
| `src/acash/ppds/private_observation.py` | NEW (PPDS extension) | Snapshot schema, trust boundary, sub-portfolio/classification/concentration/stress analytics |
| `src/acash/invest/capacity_plan.py` | NEW | Liquidity adequacy, contribution scenarios, quant-budget isolation, contribution-first allocation |
| `src/acash/invest/wealth_pack.py` | NEW | Sections A–E pack (JSON + Markdown), CLI |
| `src/acash/research/d6/investor_decision.py`, `decision_pack.py` | REUSED, UNCHANGED | V38 route costs for 5,000 / 7,500 / 10,000 THB; V38 pack referenced by hash |
| `src/acash/research/d6/contributions.py` `twr_index`, `xirr` | UNCHANGED | Reserved for flow-aware performance once transaction history exists |
| `src/acash/ppds/reconcile.py`, `provenance.py`, `statement_ingest.py` | UNCHANGED | Synthetic statement path stays synthetic-only |
| `src/acash/invest/v0_report.py` | UNCHANGED | Synthetic demonstration report |

Sub-portfolio views are computed from snapshot lines through the same FX path
and checked against the PPDS NAV (conservation residual ≤ 1e-12, a 28-digit
Decimal context bound).

## 3. Trust boundary

| Rule | Enforcement |
|---|---|
| Every snapshot declares `data_class` = `SYNTHETIC_PUBLIC_FIXTURE` or `OWNER_PRIVATE_OBSERVATION` | `parse_snapshot` / `parse_capacity` |
| Owner-private inputs and outputs live outside the repo or under `data/private/` | `assert_private_location` in `load_snapshot`, `load_capacity`, `write_pack` |
| `data/private/` is git-ignored independently of `/data/` | `.gitignore` + test |
| Account and broker refs are opaque (`^[A-Z][A-Z0-9_]{1,31}$`, no 6+ digit runs) | `_ref` |
| Amounts are decimal strings; floats/JSON numbers rejected | `_dec`, `_money` |
| Error messages carry refs and codes, never amounts | code review + tests |
| Private observations are never D5 data and carry no authority | `GOVERNANCE_FLAGS` in every output |
| Snapshot and capacity must share a data class | `build_wealth_pack` |

Regex checks are secondary. The primary control is location: private files are
created only in ignored paths, so they never reach `git add`.

## 4. Data contract (V1)

Schema `ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1_1` (see
`docs/research/evidence/upi_v1_synthetic_snapshot.json`): tz-aware `observed_at`,
an explicit `valuation_date` (the market session all prices and FX are pinned to;
may precede the local observation date, never follow it), explicit FX rates (no
inversion), dated prices with optional tz-aware `published_at` (must not follow
`observed_at`), evidence-backed classifications, accounts with role, cash lines
(`SETTLED` in NAV, `ACCRUED_INTEREST` reported but excluded), positions with
quantity, optional cost basis + currency (missing: `COST_BASIS_UNKNOWN`, NAV-only)
and optional observed market value + currency (reconciled at displayed precision).
No market-session calendar authority exists in the repo, so session validity is
`NOT_PERFORMED`; asynchronous price dates are not supported.

Support state is always `SNAPSHOT_ONLY` in V1; performance is
`PERFORMANCE_NOT_ESTABLISHED`. TWR/XIRR, realized P&L, dividends, fees, taxes,
FX/security P&L split, splits and transfers need transaction history (V2).

Classification needs methodology `OWNER_DECLARED_WITH_EVIDENCE` and an evidence
reference; otherwise `UNKNOWN`. Sub-portfolio names never imply a class.
Look-through is `OVERLAP_NOT_ESTABLISHED` until dated constituent weights exist
(`etf_overlap_exposure` can consume them later).

## 5. Owner local usage (only after the owner ratifies the ODR; not run by AI on real data)

```text
mkdir data/private
# copy docs/research/evidence/upi_v1_synthetic_snapshot.json -> data/private/snapshot.json
# copy docs/research/evidence/upi_v1_synthetic_capacity.json -> data/private/capacity.json
# edit: data_class = OWNER_PRIVATE_OBSERVATION; fill your own figures and opaque refs
uv run python -m acash.invest.wealth_pack --snapshot data/private/snapshot.json \
    --capacity data/private/capacity.json --output data/private/out --report-date 2026-11-01
```

## 6. Governance conflict and proposed amendment

Conflict: `docs/audit/PPDS_READONLY_RUNTIME_SKELETON_PACK.md` states
"real-statement runtime 0% until separately authorized".

Proposed amendment (PROPOSAL, not ratified): permit owner-run, offline,
read-only processing of `OWNER_PRIVATE_OBSERVATION` snapshots for personal
decision support only, under the boundary in §3. It does not admit data to D5,
does not change `NO_REAL_ORDERS`, `REAL_CAPITAL_AUTHORITY = USD 0.00`, Lane A/B,
HYP_003, broker connectivity, credentials or the synthetic-only status of the
PPDS statement-import path. The decision record is `docs/governance/ODR_UPI_PRIVATE_OBSERVATION_001.md`.
Until it is ratified, the runtime gate refuses `OWNER_PRIVATE_OBSERVATION` data.
