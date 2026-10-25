# HYP_007 M2 TAF Rate Correction 001 (historical defect record)

- Status: `CONFIRMED_HISTORICAL_RATE_DEFECT` (calendar 2025). Additive record; the frozen
  R4 report, manifests, checksums and verdict are **not modified**.
- Primary source: SEC Release No. 34-101696 (FINRA, 2024-11-21), PDF p. 18, TAF
  implementation table: 2024 and 2025 equity TAF $0.000166/share, max $8.30/trade;
  2026 proposed $0.000195 / $9.79 (later amended; not used as a 2026 authority here).
  Verification class: `PRIMARY_SOURCE_VERIFIED` (operator-inspected, V28 handoff).

## 1. Defect

`src/acash/research/step_r4_hyp_007.py`, `M2_FINRA_TAF_SCHEDULE[1]`: effective
2025-01-01..2026-12-31 at $0.000195 / $9.79, citing "Schedule A ... Effective Jan 1, 2025".
For 2025 the correct rate is $0.000166 / $8.30, as in the canonical
`src/acash/execution/regulatory_fees.py`. The M2 SEC §31 rows for 2024-05-22..2025-12-31
match the canonical engine; 2026 rows (both fees) are outside canonical coverage and
remain `UNVERIFIED`.

Evaluation window: M2 2024-05-01..2026-08-14
(`src/acash/research/step_r4_hyp_007_governance.py`), USD 100,000 simulated AUM,
503 baseline completed trades. Affected: every sell leg dated 2025-01-01..2025-12-31.

## 2. Corrected-fee impact (bounded, analytical)

Trade-level M2 inputs (quarantined market data and per-trade ledgers) are not in the
repository, so a full rerun is `NOT_REPRODUCIBLE_WITH_AVAILABLE_INPUTS`.

Per sell leg, the M2 overcharge is
`ceil_cent(min(0.000195·q, 9.79)) − ceil_cent(min(0.000166·q, 8.30)) ∈ [0, 1.50]`, verified
over a share grid in `tests/unit/research/test_hyp_007_taf_correction_001.py`. Each
completed trade has one sell leg (long exit or short entry), and the 2x stress scenario
applies TAF once. Worst case, all 503 trades in 2025 at the cap:

- Overcharge ≤ 503 × $1.50 = **$754.50 ≤ 0.76% of initial AUM** (≈0.80% allowing for
  AUM growth up to the observed path), in both baseline and 2x stress.

## 3. Gate impact

| Gate | Frozen value | Hurdle | Corrected bound | Verdict change |
|---|---|---|---|---|
| R4-G1 net total return | 3.50% | > 0 | ≤ 4.30% | none (PASS) |
| R4-G2 net annualized Sharpe | 0.1762 | ≥ 0.50 | see below | none (FAIL) |
| R4-G3 max drawdown | 21.70% | ≤ 35% | not increased | none (PASS) |
| R4-G4 2x stress total return | −3.96% | ≥ 0 | ≤ −3.16% | none (FAIL) |

G2 (heuristic bound): the cost reduction raises annualized mean return by at most about
0.80% / (574/252) ≈ 0.35%/yr. Lifting Sharpe by the required 0.324 would need annualized
volatility ≤ 0.35/0.324 ≈ 1.1%, which cannot coexist with the observed 21.70% maximum
drawdown. The conjunction rule therefore still fails on G2 and G4.

**Conclusion:** `R4_VERDICT: FAIL_CURRENT_EDGE_NOT_SUPPORTED` is unchanged under the
corrected 2025 TAF. No upgrade to scientific PASS. HYP_003 remains terminally falsified.
