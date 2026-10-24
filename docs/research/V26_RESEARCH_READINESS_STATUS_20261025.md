# V26 Research Readiness Status (2026-10-25)

Baseline: `main` at `726afa97da44dab672cce29d90c9c8c5e9b929e7` (PR #51). This document is the
current decision surface; historical packets (e.g.
[`OWNER_DECISION_PACKET_20261023.md`](../governance/OWNER_DECISION_PACKET_20261023.md), PR #48 era)
are preserved unchanged.

## 1. Status by evidence class

| Class | Status | Evidence |
|---|---|---|
| Code integrated | D5 admission bridge, anchored admission, evidence authenticity semantics | PR #50, #51, V26 PR A |
| Offline tested | D1-D3 components, D5, D3 budget simulation | `tests/unit/data/` |
| Issuer source verified | Not yet for 2016-2025 census (D4 30 events: original scope only) | Section 4, R2 |
| Rights verified | `UNKNOWN` (account entitlement, retention, derived use) | [`ALPACA_RIGHTS_MATRIX_20261023.md`](../governance/ALPACA_RIGHTS_MATRIX_20261023.md) |
| Admission independently ratified | No. `D5_ADMISSION_TRUST_ANCHORS` empty | `lane_b_d5_rehearsal.py` |
| Dataset admitted | No. `D5_REAL_DATA_NOT_ADMITTED` | - |
| Scientific study executed | No | - |
| Paper / capital authorized | No. `NO_REAL_ORDERS=true`, capital USD 0.00 | - |

## 2. Human decisions that remain open

1. Confirm Alpaca account entitlement and data rights (retention, derived use) via the correct agreement.
2. Ratify V2 (`V2_FORMAL_RATIFICATION=PENDING`).
3. Provision a production admission authority: an admitter key whose custody is independent of
   acquisition; public key added to `D5_ADMISSION_TRUST_ANCHORS` by reviewed change.
4. Authorize a bounded acquisition (scope, budget; see Section 3).
5. Register a numerical D6 risk policy prospectively, or accept the descriptive after-cost Pareto comparison.
6. Resolve `asof` for multi-year PIT symbol mapping (open in `lane_a_d1_safety.py`).

## 3. D3 budget simulation (offline, `src/acash/data/qualification/d3_budget_simulation.py`)

Scope: BIL, BND, GLD, VOO; 2016-01-01..2025-12-31; adjustments `raw`, `split`; D5 identity
freezes `limit=1000`. Sessions from the repository NYSE calendar: **2,514** (10,056 bars per adjustment).

| Scenario | Bytes/bar (assumed) | Requests | Observed bytes | Fits 32 / 8 MiB |
|---|---|---|---|---|
| Realistic | 130 | 22 | 2,615,968 | Yes |
| Adverse (+1 trailing token page per adjustment) | 200 | 24 | 4,028,544 | Yes |
| Byte break-even | 417 | 24 | 8,392,848 | No (bytes) |
| `limit=100` (unfrozen/smaller limit) | 200 | 204 | - | No (requests) |
| Third adjustment (`all`) | 200 | 36 | - | No (requests) |

Conclusion: the proposed ceiling is likely sufficient **only if** `limit=1000` stays frozen,
exactly two adjustments are fetched, and the real payload stays under about 416 bytes per bar.
Bytes per bar are assumptions; replace them with observed receipts. No acquisition authority is issued.

## 4. Research reuse audit

Depth: module presence and prior PR evidence; not a line-by-line integration audit.

| Work | Classification | Reusable now |
|---|---|---|
| HYP_009 historical retrieval | ORIGINAL_SCOPE_ONLY | Client pattern incl. explicit `asof` parameter |
| HYP_010 / HYP_011 qualification | ORIGINAL_SCOPE_ONLY | Methods only; no result or authority transfer |
| HYP_011 accounting (`research/hyp_011/accounting.py`) | IMPLEMENTED_NOT_INTEGRATED | Candidate for D6 golden tests |
| D1-D3 acquisition components | IMPLEMENTED_NOT_INTEGRATED | No end-to-end offline harness yet |
| D4 30 events | ORIGINAL_SCOPE_ONLY | Original window only |
| D5 admission | REUSED_AND_INTEGRATED (offline); real admission BLOCKED_BY_EVIDENCE | Anchored admission, authenticity classes |
| MEC-0015 fee engine (`execution/regulatory_fees.py`) | IMPLEMENTED_NOT_INTEGRATED; 2024-05-01..2025-12-31 BLOCKED_BY_EVIDENCE | Schedule ends 2024-04-30 |
| ETF/FX benchmark (`data/contracts/etf_fx_benchmark.py`) | IMPLEMENTED_NOT_INTEGRATED | - |
| Portfolio baselines (`portfolio/baselines.py`) | IMPLEMENTED_NOT_INTEGRATED | Comparators for D6 |
| Backtest accounting (`backtest/accounting.py`) | IMPLEMENTED_NOT_INTEGRATED | - |
| Validators (`validation/deflated_sharpe.py`, `overfitting.py`, `cpcv.py`, `multiple_testing.py`) | IMPLEMENTED_NOT_INTEGRATED | No qualified new-universe study |
| D6 preregistration | RESEARCH_ONLY | Risk threshold unspecified |
| Alpaca rights | BLOCKED_BY_RIGHTS | - |

## 5. External research brief (for ChatGPT Research; no requests made from this repository)

Return results as `docs/research/V26_EXTERNAL_RESEARCH_RESULTS_<date>.md` with a URL, retrieval
date and verbatim excerpt for every claim. Mark anything not proven as `UNKNOWN`.

**R2: Corporate-action census, 2016-01-01..2025-12-31, for VOO, BND, GLD, BIL.**
Sources: Vanguard VOO/BND distribution history (10-year export), State Street SPDR Historical
Distributions XLSX (state its actual coverage range), SPDR Gold Trust disclosures. One row per event:
fund, ex-date, record date, payable date, amount/share, type (income, short-term or long-term capital
gain, return of capital), split or reverse split, source URL, artifact name, retrieval date,
publication or revision date if shown, PIT vintage status (`UNKNOWN` unless dated vintages exist).
Add a coverage table by ETF and year. Do not fill gaps from payment frequency. GLD: confirm no cash
distributions; do not model expenses as dividends.

**R3: Regulatory fees for 2024-05-01..2025-12-31.**
SEC Section 31: every rate and effective date from 2024-05-01, including the rate in force
2024-05-01..2024-05-21 and confirmation of $27.80/M (2024-05-22..2025-05-13) and $0.00/M (from
2025-05-14), plus any change through 2025-12-31. FINRA TAF (covered sales): per-share rate, per-trade
cap, effective dates and rounding rules. State whether each fee is levied on broker/SRO or passed to
retail customers, and what Alpaca charges customers. Format rows to match
`docs/research/MEC-0015-sec31-fee-schedule.md` and `MEC-0015-finra-taf-fee-schedule.md`.

**R1: Alpaca public documentation.**
Historical coverage by plan, SIP/IEX restrictions, rate limits, `limit` semantics across symbols,
`next_page_token`, `asof` default, adjustment values, corporate-action endpoint limitations,
redistribution terms. Leave account entitlement, retention duration, derived-data rights and
contract version `UNKNOWN`.

## 6. Not done in V26 (remaining work)

- Offline end-to-end acquisition harness (Scope to D5 candidate) and its adversarial suite.
- Host preflight (permissions, durability classes, clock, secret isolation).
- D6 fee schedule extension (awaits R3), D6 golden accounting tests for the USD 1,000 comparators.
- D7 scientific integration for the D6 workflow.
