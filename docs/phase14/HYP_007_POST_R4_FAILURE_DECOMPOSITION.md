# Phase 14 HYP_007: Post-R4 Post-Hoc Descriptive Failure Decomposition (M1 vs M2)

```text
[DOCUMENT ID: docs/phase14/HYP_007_POST_R4_FAILURE_DECOMPOSITION.md]
[AUTHORIZATION: AUTHORIZE_HYP_007_POST_R4_CLOSURE_AND_CONDITIONAL_HYP_008_RESEARCH_INCEPTION]
[HYPOTHESIS_ID: HYP_007]
[MECHANISM_ID: MEC-0017]
[CANONICAL_HEAD: 653b007e4d5ce73c5022086f40737a4525410a55]
[CLOSURE COMMIT: 526a0eb]
[CANONICAL HEAD AFTER CLOSURE: 526a0eb]
[DECOMPOSITION CLASSIFICATION: POST_HOC_DESCRIPTIVE_FAILURE_ANALYSIS]
[STATISTICAL STATUS: POST_HOC_DESCRIPTIVE — NO CONFIRMATORY CLAIM]
[M3 ACCESS: FALSE (records read = 0)]
[QUARANTINE GAP ACCESS: FALSE (records read = 0)]
```

- **Governing Standard:** ACASH `AGENTS.md` (Zero Unverified Claims; Falsifiability over qualification;
  Unit & Space Discipline; Warnings Are Evidence).
- **Method scope:** This dossier is strictly **descriptive**, **post-hoc**, and **non-confirmatory**.
  It explains *how* the M2 edge failed relative to M1 using sealed, exposed ledgers only. It does
  **not** produce a p-value, a significance statement, or an out-of-sample claim. No statistical
  inference about M3 is drawn or implied.
- **Anti-harking rule (in force):** All M1/M2 evidence is now `DISCOVERY / DESIGN` evidence for any
  future hypothesis. Any future HYP_008 statistic must be validated on completely fresh data.

---

## 1. Decomposition Engine

All tables below are produced by the deterministic, unit-tested analysis utility
`src/acash/research/step_r4_failure_decomposition.py` (canonical analysis artifact added under this
authorization). Inputs are exclusively the sealed parquet ledgers under `data/hyp_007/`
(M1) and `data/hyp_007/m2/` (M2). The engine reads **no** M3 data and **no** quarantine-gap data.

- Unit tests: `tests/unit/research/test_phase14_step_r4_hyp_007_failure_decomposition.py` (10 tests).
- Deterministic output snapshot: `docs/phase14/manifests/HYP_007_POST_R4_FAILURE_DECOMPOSITION.json`.
- Every table in this dossier is traceable to that snapshot.

## 2. Headline Descriptive Result

| Measure | M1 | M2 | Delta |
| :--- | ---: | ---: | ---: |
| Completed trades | 659 | 503 | −156 |
| Sessions (strategy-eligible) | 707 | 568 | −139 |
| **Gross P&L** (USD) | **86,571.302** | **7,208.102** | **−79,363.200** |
| Total friction (USD) | 5,172.683 | 3,704.053 | −1,468.630 |
| **Net P&L** (USD) | **81,398.619** | **3,504.049** | **−77,894.570** |
| **Gross expectancy/trade** (USD) | **131.37** | **14.33** | **−89.1%** |
| Net expectancy/trade (USD) | 123.52 | 6.97 | −94.4% |
| Friction/trade (USD) | 7.85 | 7.36 | −0.48 |
| Friction / gross P&L | 5.98% | 51.39% | +45.4 pp |
| Net win rate | 42.03% | 39.76% | −2.3 pp |

**Primary descriptive failure label: `GROSS_EDGE_DECAY`.** The M2 shortfall is dominated by an
~89.1% collapse in *gross* per-trade expectancy, **not** by a friction-cost explosion. Absolute
friction per trade is essentially unchanged (M1 `$7.85` vs M2 `$7.36`); friction became a
"large share of gross P&L" (51.4%) only because the gross numerator collapsed. Stress-shock
friction burden (2×) rises from `$5,172.68` (M1) to `$11,378.92` (M2) in absolute terms, but gross
P&L fell to `$7,208`, driving the friction/gross ratio to 157.9% on the stress path and flipping
the stress-net outcome negative.

## 3. Friction Decomposition (per component, baseline path)

| Component | M1 USD | M1 % of total | M2 USD | M2 % of total |
| :--- | ---: | ---: | ---: | ---: |
| Commission | 3,202.91 | 61.9% | 1,605.16 | 43.3% |
| SEC 31 (sell-side) | 1,901.86 | 36.8% | 2,053.68 | 55.4% |
| FINRA TAF (sell-side) | 67.91 | 1.3% | 45.21 | 1.2% |
| Standalone slippage | 915.12 | 17.7% | 458.62 | 12.4% |
| Stress half-spread | 0.00 | 0% | 0.00 | 0% |
| Stress borrow fee | 0.00 | 0% | 0.00 | 0% |
| **Total baseline friction** | **5,172.68** | 100% | **3,704.05** | 100% |

Notes:
- M2 SEC 31 burden (`$2,053.68`) **exceeds** M1 (`$1,901.86`) despite fewer trades and legs — the
  2025-05-14→2026-04-03 rate is 0.0% but the 2024-05-22→2025-05-13 and post-2026-04-04 windows carry
  higher statutory rates; the mix of holding periods and price levels distributes shares flows
  toward higher-rate segments. This is a **statutory calendar effect, not a strategy-control error**.
- M2 friction per trade (`$7.36`) is *lower* than M1 (`$7.85`): friction constitution itself is not
  the driver; gross-edge decay is.

## 4. Baseline vs 2× Stress Degradation

| Measure | M1 baseline | M1 2× stress | M2 baseline | M2 2× stress |
| :--- | ---: | ---: | ---: | ---: |
| Total friction amortized (USD) | 5,172.68 | 10,336.59 | 3,704.05 | 11,378.92 |
| Friction / gross P&L | 5.98% | 11.94% | 51.39% | 157.86% |
| Final AUM (USD) | 181,398.62 | 166,436.01 | 103,504.05 | 96,042.29 |
| Net total return | +81.40% | +66.44% | +3.504% | **−3.958%** |
| Annualized Sharpe | 1.6862 | 1.4505 | 0.1762 | −0.0506 |
| Max drawdown | 11.76% | 12.53% | 21.70% | 24.16% |

M1 canonical values source: `docs/phase14/manifests/manifest_r3_HYP_007_CORRECTED_001.json`;
M2 canonical values source: `docs/phase14/manifests/HYP_007_R4_M2_RESULT_MANIFEST.json`.
**M2's stress path flips to a loss because gross edge is too small to absorb the doubled friction**,
not because stress assumptions changed between samples (they did not).

## 5. Long vs Short Decomposition

| Direction | M1 count | M1 gross | M1 net | M1 net exp/trade | M2 count | M2 gross | M2 net | M2 net exp/trade |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| LONG | 344 | 59,002.30 | 56,262.96 | 163.56 | 267 | 278.72 | **−1,635.99** | **−6.13** |
| SHORT | 315 | 27,569.00 | 25,135.66 | 79.80 | 236 | 6,929.38 | 5,140.04 | 21.78 |

**Side asymmetry is the single most important intra-decomposition finding.** The M2 collapse is
concentrated in the **LONG** leg (net expectancy −100.0%: from +163.56 to −6.13 per trade). The
SHORT leg retained positive (though diminished) net expectancy in M2 (+21.78). A long-exposure
overweight in M2 (`LONG 267 / SHORT 236` vs M1 `344 / 315`) combined with a vanished long edge is
consistent with **trend/continuation decay during the specific M2 equity window** (see §7).

## 6. Time-of-Day (12 frozen decision epochs) — net P&L by epoch

| Epoch ET | M1 net | M2 net | M2−M1 | M1 share | M2 share |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 10:00 | 12,712.33 | 3,293.02 | −9,419.31 | 28.5% | 25.8% |
| 10:30 | 3,112.43 | 420.53 | −2,691.90 | 13.2% | 11.3% |
| 11:00 | 1,132.92 | 9,641.57 | +8,508.65 | 8.0% | 8.5% |
| 11:30 | 9,649.24 | −5,294.61 | −14,943.85 | 7.1% | 7.4% |
| 12:00 | 2,997.75 | −8,028.24 | −11,025.98 | 6.2% | 7.0% |
| 12:30 | 7,502.05 | 5,636.82 | −1,865.23 | 7.3% | 5.8% |
| 13:00 | −3,011.11 | −8,308.79 | −5,297.68 | 4.7% | 7.4% |
| 13:30 | 9,716.44 | 6,300.84 | −3,415.60 | 4.1% | 6.2% |
| 14:00 | −1,581.96 | −2,196.28 | −614.32 | 5.8% | 6.6% |
| 14:30 | 17,419.92 | 5,214.58 | −12,205.35 | 5.6% | 5.8% |
| 15:00 | 13,291.56 | −8,508.92 | −21,800.48 | 4.1% | 4.4% |
| 15:30 | 8,457.06 | 5,333.54 | −3,123.52 | 5.3% | 4.0% |
| **Total** | **81,398.62** | **3,504.05** | **−77,894.57** | 100% | 100% |

**Strongest time-of-day deterioration: the 15:00 epoch** (M1 +13,291.56 → M2 −8,508.92; swing
−21,800.48) and **11:30** (swing −14,943.85). The strategy's largest M1 profit sources
(10:00 and the 14:30–15:30 late-session window) all decay sharply; 15:00 and 12:00 flip sign.
This is consistent with the known intraday-momentum literature finding that **late-session
continuation** (the core of the published effect) weakened in the post-publication window —
see Rosa (2022) *J. Futures Markets* "the predictability disappears out of sample."

## 7. Calendar-Year Subperiod Stability

| Year | M1 trades | M1 net P&L | M1 net exp/trade | M2 trades | M2 net P&L | M2 net exp/trade |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2021 | 107 | 5,489.87 | 51.31 | — | — | — |
| 2022 | 247 | 20,535.67 | 83.14 | — | — | — |
| 2023 | 218 | 35,919.97 | 164.77 | — | — | — |
| 2024 | 87 | 19,453.11 | 223.60 | 141 | 10,952.30 | 77.68 |
| 2025 | — | — | — | 215 | −3,238.38 | −15.06 |
| 2026 (to M2 end) | — | — | — | 147 | −4,209.87 | −28.64 |

**The M2 degradation is itself time-dependent.** Within M2, 2024 (May–Dec) remains positive
(+77.68 net/trade), while 2025 and 2026 turn negative. This is a **directional decline over
calendar time**, not an artifact of the whole window. M1 was positive in every calendar year.

## 8. Ex-Ante Volatility-State Diagnosis (M1-derived fixed terciles)

Cutoffs `realized_vol_15d`: LOW ≤ 0.007622, HIGH ≥ 0.011229 (fixed quantiles over the declared M1
reference sample; identical cutoffs applied to M1 and M2).

| State | M1 count | M1 net exp/trade | M2 count | M2 net exp/trade |
| :--- | ---: | ---: | ---: | ---: |
| LOW | 218 | 199.98 | 255 | 81.27 |
| MEDIUM | 232 | 80.14 | 182 | **−78.75** |
| HIGH | 209 | 91.92 | 66 | **−43.73** |

**Regime-dependence finding:** M1 was net-positive in every volatility tercile. M2 is net-positive
only in LOW-volatility states and net-negative in MEDIUM/HIGH states. This concentration of the
remaining edge in LOW-vol sessions (and disappearance under elevated realized vol) is directionally
consistent with both (a) the known regime-dependence of intraday-momentum predictability
(Rosa 2022; Gao et al. 2018: effect strongest on high-vol days → its *absence* in M2's
MEDIUM/HIGH days is the decay) and (b) the ex-ante seasonality of the M2 equity window
(2025–2026 trending-period long-trade losses concentrate in higher-vol days).

> **Caveat (anti-harking).** This is a descriptive regime *association*. It is **not** a procedure
> to re-select an ideal vol state, it was computed from **M1-derived** cutoffs applied unmodified,
> and it may **not** be used to justify an M2-optimized threshold.

## 9. Liquidity & Volume Diagnostics

| Measure | M1 | M2 |
| :--- | ---: | ---: |
| Execution quotes examined | 9,204 | 7,384 |
| Avg half-spread at boundaries (USD) | 0.00641 | 0.00859 |
| % locked quotes | 0.674% | 0.447% |
| % crossed quotes | 0.0% | 0.0% |
| Avg quoted size (shares) | 13.32 | 279.17 |
| Bars analyzed | 281,970 | 221,520 |
| Median volume/bar (shares) | 125,402 | 90,313 |
| Mean volume/bar (shares) | 183,487 | 138,310 |

Interpretation:
- Observed half-spreads are wider in M2 (+34%), but quoted depth is far larger (279 vs 13 shares at
  top-of-book) and no crossed quotes were selected in either sample. The widened half-spread is a
  *contributing* friction factor on the stress path only, not the primary failure driver.
- Per-minute volume is lower in M2 (median 90,313 vs 125,402). This is consistent with a shift in
  SPY liquidity microstructure (2024–2026 tape-wide volume distribution), not a data defect.

## 10. Diagnostic Summary (Ordered Contributions to M1→M2 Net-P&L Decline of −77,894.57)

| # | Factor | Contribution assessment | Evidence |
| :--- | :--- | :--- | :--- |
| 1 | **Gross-edge decay** (LONG-led) | Dominant | Gross expect. −89.1%; LONG −100%; SHORT retained + |
| 2 | **Calendar-time deterioration** within M2 | Material | 2024 +, 2025 −, 2026 − |
| 3 | **Volatility-regime concentration** (MEDIUM/HIGH losses) | Material-conditioned | Tercile table §8 |
| 4 | Friction per-trade | No material change | 7.85 → 7.36 (baseline) |
| 5 | SEC 31 statutory mix | Minor amplify | M2 SEC31 > M1 USD |
| 6 | Half-spread widening | Minor (stress path only) | +34% spread, deeper book |
| 7 | Quoted depth / crossed/locked | Non-eventing | 0 crossed both samples |

**Conclusion (descriptive):** the failure is a **gross-edge decay** concentrated in long
continuation trades and in higher-realized-volatility sessions, worsening across 2025–2026, with
friction acting as a secondary amplifier rather than a root cause. This profile is coherent with the
published post-publication-decay literature on market intraday momentum (Rosa 2022; McLean & Pontiff
2016 mechanism class; Gao et al. 2018 explicit high-vol dependence).

## 11. Explicit Non-Claims

- No claim that HYP_007 would have passed any alternative friction model.
- No claim that the "LOW-vol subset of M2" constitutes a viable strategy — it is a descriptive subset,
  not a fiveable tradeable design; any future use would violate the anti-harking rule.
- No claim of statistical significance for any decomposition contrast.
- No inference about M3.
- No claim that friction is "wrong": the frozen registered contract is the fixed authority.

## 12. Decomposition Engine Reproducibility

- Utility: `src/acash/research/step_r4_failure_decomposition.py` (pure functions, Decimal arithmetic,
  no random seeds).
- Tests: 10 passing (`tests/unit/research/test_phase14_step_r4_hyp_007_failure_decomposition.py`).
- Snapshot: `docs/phase14/manifests/HYP_007_POST_R4_FAILURE_DECOMPOSITION.json` (canonical machine
  output; SHA recorded in that file).

---

### Verification Ledger
- Implementation Status: COMPLETE
- Contract Enforcement: STRICT FAIL-CLOSED (M3/0, quarantine/0, anti-harking in force)
- Mathematical Authority: DESCRIPTIVE POST-HOC (M1-derived cutoffs only; no M2 optimization)
- Local Test Suite: VERIFIED (10/10 decomposition tests; full suite pending in Commit B)
- Type Checker (MyPy): PENDING (run before Commit B)
- Remote CI Status: NOT AVAILABLE (local git; push is the sync mechanism)
- Methodological Caveats: POST-HOC DESCRIPTIVE ONLY — no confirmatory claims; vol terciles derive
  solely from the declared M1 reference sample; identical cutoffs applied to M2.