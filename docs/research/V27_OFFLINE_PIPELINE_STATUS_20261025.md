# V27 Offline Research Pipeline — Status, Reuse Inventory, Owner Decision Packet

Boundaries unchanged: `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`,
`LANE_A = UNISSUED`, `LANE_B = UNISSUED`, `D5_REAL_DATA_NOT_ADMITTED`,
`V2_FORMAL_RATIFICATION = PENDING`, `D5_ADMISSION_TRUST_ANCHORS = EMPTY`.
No provider request, credential, subscription, or licensed dataset was used.

## 1. Delivered (offline, synthetic)

| Workstream | Artifact | Evidence |
|---|---|---|
| A. Harness | `src/acash/data/qualification/d5_offline_harness.py` | `tests/unit/data/test_d5_offline_harness.py` |
| A. Host preflight | `src/acash/data/qualification/host_preflight.py` | `tests/unit/data/test_host_preflight.py` |
| B. Fees 2024-05..2025-12 | `src/acash/execution/regulatory_fees.py` (canonical, extended) | `tests/unit/execution/test_regulatory_fees_2025_extension.py` |
| C. D6 accounting | `src/acash/research/d6/accounting.py` | `tests/unit/research/test_d6_golden_accounting.py` |
| C. D6 amendment | `docs/research/D6_AMENDMENT_A1_DESCRIPTIVE_COMPARISON_UNRATIFIED_20261025.md` | unratified |
| D. Source ledger | `src/acash/data/contracts/corporate_action_ledger.py` | `tests/unit/data/test_corporate_action_ledger.py` |
| F. Research artifact | `docs/research/V26_EXTERNAL_RESEARCH_RESULTS_20261025.md` | operator-reported |

Harness chain: frozen scope (`TEST_FIXTURE` authority, explicit `asof`, `limit=1000`,
adjustments `raw`+`split`) → budget planning floor before any artifact → `httpx.MockTransport`
only → strict identity-encoded capped read → pagination with cycle detection → reservation
journal → receipts → manifest → synthetic D5 candidate (`real_data_admitted: false`) → replay.

Budget integration: `simulate_bars_budget` is a pre-dispatch planning floor
(`PLANNING_FLOOR`, 1 byte/bar). Runtime enforcement is `CanaryBudget` on measured bytes.
Estimated bytes are not measured bytes.

Host preflight limits: process-crash durability is "create-once + fsync attempted, not
tested under kill"; OS crash and power loss `UNPROVEN`; clock not a trusted timestamp;
`ready_for_real_acquisition = false` always.

## 2. Corporate-action coverage matrix (2016–2025)

| Ticker | 2016–2024 | 2025 | Ledger status |
|---|---|---|---|
| VOO | UNKNOWN | NOT_PROVEN_COMPLETE (4 issuer examples) | `SOURCE_IDENTIFIED_NOT_EXTRACTED` |
| BND | UNKNOWN | NOT_PROVEN_COMPLETE (3 issuer examples) | `SOURCE_IDENTIFIED_NOT_EXTRACTED` |
| BIL | UNKNOWN | UNKNOWN | `SOURCE_IDENTIFIED_NOT_EXTRACTED` (State Street XLSX) |
| GLD | policy | policy | `NO_CASH_DISTRIBUTION_ENTITLEMENT` (no dated split census) |

Missing-source report: VOO, BND, BIL full issuer exports for every year 2016–2025; GLD
split/trust-record census by year. `require_complete_coverage` fails closed on this grid.

## 3. Reuse inventory

| Path | Status | Used by V27 | Missing integration |
|---|---|---|---|
| `src/acash/execution/regulatory_fees.py` | canonical, extended to 2025-12-31 | D6 sell fees | broker pass-through unverified |
| `src/acash/research/hyp_009/accounting.py` (`adverse_fill`, `DividendEvent`) | frozen HYP_009 | D6 fills, distribution input | — |
| `src/acash/data/contracts/etf_fx_benchmark.py` (`EtfDistributionRecord`) | tested | source ledger records | — |
| `src/acash/data/contracts/etf_fx_benchmark.py` (`HoldingsBasedBenchmark`) | tested, unused in `src` | not reused | weights must sum to 1 (no cash comparator), close fills, whole-share-only friction, no regulatory fees; D6 needs all four — overlap disclosed, see F02 |
| `src/acash/research/hyp_011/accounting.py` | frozen ACWI/AGG engine | not reused | asset-specific |
| `src/acash/data/qualification/d3_budget_simulation.py` | tested | harness planning floor | — |
| `src/acash/data/qualification/lane_a_*`, `lane_b_d5_rehearsal.py` | tested | harness primitives, D5 evaluation | real authority/anchors absent |
| `src/acash/validation/deflated_sharpe.py`, `overfitting.py`, `cpcv.py`, `multiple_testing.py` | tested | not wired to D6 | D6 contract forbids DSR/PBO over four baselines as a strategy search; wire only for sealed variant sets |

D7 (science): no new code. Existing validators stay the single authorities; D6 reports
descriptive metrics plus deterministic block bootstrap per contract section 6, after an
admitted dataset exists. No empirical run; HYP_003 stays falsified.

## 4. Findings

- **V27-F01 — TAF 2025 discrepancy.** `src/acash/research/step_r4_hyp_007.py` (HYP_007 M2)
  applies TAF $0.000195 / max $9.79 to 2025. Research R3 and FINRA Schedule A support
  $0.000166 / $8.30 through 2025-12-31; the canonical engine now uses the latter. The
  higher value may belong to a later effective date — needs primary-source reconciliation.
  HYP_007 is a frozen record and was not modified.
- **V27-F02 — Dual fee/accounting authorities.** HYP_007 M2 keeps its own fee schedule
  separate from `regulatory_fees.py`, and D6 adds a holdings engine beside
  `HoldingsBasedBenchmark`. Both overlaps are disclosed and need an owner decision on
  consolidation; no silent refactor was performed.

## 5. Owner Decision Packet (minimum)

1. Ratify or reject D6 Amendment A1 (descriptive comparison, no numeric threshold).
2. Answer the single Alpaca rights question in the research artifact (R1) for the account.
3. Authorize lawful issuer-source extraction for VOO/BND/BIL distributions 2016–2025.
4. Decide V27-F01/F02: reconcile the HYP_007 TAF row and whether to consolidate engines.

Next scientific milestone: an admitted, rights-verified 2016–2025 price and distribution
dataset, after which the D6 descriptive comparison can run under the ratified contract.
