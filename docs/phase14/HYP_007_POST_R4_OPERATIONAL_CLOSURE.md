# Phase 14 HYP_007: Post-R4 Operational Closure Dossier

```text
[OPERATIONAL STATE: CLOSED]
[AUTHORIZATION: AUTHORIZE_HYP_007_POST_R4_CLOSURE_AND_CONDITIONAL_HYP_008_RESEARCH_INCEPTION]
[HYPOTHESIS_ID: HYP_007]
[MECHANISM_ID: MEC-0017]
[CANONICAL_HEAD: 653b007e4d5ce73c5022086f40737a4525410a55]
[M1_HISTORICAL_REPLICATION: SUPPORTED (ACCEPTED_SUPPORTED_ON_REGISTERED_M1)]
[M2_CURRENT_EDGE: NOT_SUPPORTED (FAIL_CURRENT_EDGE_NOT_SUPPORTED)]
[COMBINED INTERPRETATION: HISTORICAL_REPLICATION_SUPPORTED_BUT_CURRENT_EDGE_NOT_SUPPORTED]
[R4 RESULT PACKAGE SHA256: 9fbf1413e8ad517d6ee5b7c1a77d0c7324a359396c9e0591beaba0344d3c52b0]
[M2 DATASET CONTENT SHA256: 4b2e997ed825359cb6830b03759fdeebe9ba666426e434ddbb91c771e1ba1284]
[PAPER: NOT_AUTHORIZED]
[LIVE: LOCKED]
[REAL_CAPITAL: 0.00]
[NO_REAL_ORDERS: true]
[M3: PRESERVED_UNTOUCHED (PROSPECTIVE_ONLY / LOCKED_ZERO_ACCESS)]
[OPERATIONAL PROGRESSION: CLOSED]
```

- **Document ID:** `docs/phase14/HYP_007_POST_R4_OPERATIONAL_CLOSURE.md`
- **Governing Standard:** ACASH `AGENTS.md` (Zero Unverified Claims; Strict Fail-Closed; Do Not Optimize for Green CI; Never Broaden Scope).

> **Scientific interpretation scope (mandatory).** This document closes HYP_007 **operationally**
> after the frozen R4 M2 current-edge evaluation. It does **NOT** declare HYP_007 "universally
> disproven." The correct interpretation, per authorization §2/§3, is:
>
> *"The frozen HYP_007 implementation is historically supported on M1 but lacks sufficient
> recent post-publication economic robustness under the registered friction contract."*
>
> HYP_007 is **not** parameter-tunable, re-specifiable, or rescuable by any downstream variant.

---

## 1. Research Identity

Phase 14 (`HYP_007` / `MEC-0017`) evaluated the SPY Noise-Area intraday momentum strategy:
a direct-SIP replication of a VWAP/HLC3 anchor-band mechanism with 12 decision epochs
(10:00–15:30 ET), a 2% annualized volatility target (`L_t = min(4.0, 0.02 / σ_d,t)`), `$100,000`
simulated AUM, and EOD flatten at 15:59:00 ET, under a registered friction contract
(commission `max($0.35, 0.0035·sh)`, SEC 31 sell-side, FINRA TAF sell-side, `$0.001/share`
adverse slippage, NBBO quote crossing; 2× stress adds one half-spread per side + 50 bps annual
short borrow prorated to holding minutes).

## 2. Registered Evidence States (Sealed, Immutable)

| Register | State | Evidence |
| :--- | :--- | :--- |
| M1 (2021-07-01..2024-04-30) | `ACCEPTED_SUPPORTED_ON_REGISTERED_M1` | M1 parquet + sealed M1 manifests |
| M2 (2024-05-01..2026-08-14) | `FAIL_CURRENT_EDGE_NOT_SUPPORTED` | R4 decision/result manifests, `9fbf1413…` |
| Combined | `HISTORICAL_REPLICATION_SUPPORTED_BUT_CURRENT_EDGE_NOT_SUPPORTED` | `HYP_007_R4_M2_RESULT_MANIFEST.json` |
| M3 (prospective, `>= 2026-09-23`) | `PROSPECTIVE_ONLY` / `LOCKED_ZERO_ACCESS` | Guard: M3 records read = 0 |
| Quarantine gap `[2026-08-15, 2026-09-23)` | `STRICTLY_ZERO_ACCESSED` | Guard: quarantine records read = 0 |

## 3. Frozen R4 Result (Recap, Immutable)

- Baseline: initial AUM `$100,000.00` → final `$103,504.05`; net total return `+3.504%`;
  annualized Sharpe `0.1762`; max drawdown `21.70%`; completed baseline trades `503`.
- 2× friction stress: final AUM `$96,042.29`; net total return `-3.958%`;
  annualized Sharpe `-0.0506`; max drawdown `24.16%`.
- Gate ledger: **G1(+3.50% > 0) PASS · G2(0.176 ≥ 0.50) FAIL · G3(21.70% ≤ 35%) PASS ·
  G4(-3.96% ≥ 0) FAIL** → conjunction FAIL → `FAIL_CURRENT_EDGE_NOT_SUPPORTED`.
- Deterministic reproducibility rerun: **identical** (`deterministic_rerun_identical: true`).

## 4. Absolute Closure Covenant

Under `AUTHORIZE_HYP_007_POST_R4_CLOSURE_AND_CONDITIONAL_HYP_008_RESEARCH_INCEPTION`, the
following are **prohibited** in any future work and recorded here as a hard covenant:

- changing Noise-Area lookback; changing decision epochs; changing volatility target;
  changing leverage cap; changing VWAP; changing friction; changing quote policy; changing AUM;
- excluding losing dates; adding regime filters to HYP_007; lowering R4 gates;
  rerunning M2 with alternative specifications; using M3 to attempt rescue of HYP_007.

The HYP_007 scientific result is **immutable** and remains exactly as sealed at `653b007`.

## 5. Preserved State Assertions

| Assertion | Value |
| :--- | :--- |
| `PAPER = NOT_AUTHORIZED` | false paper authority |
| `LIVE = LOCKED` | locked |
| `REAL_CAPITAL = 0.00` | `$0.00` |
| `NO_REAL_ORDERS = true` | true |
| `M3` | `PRESERVED_UNTOUCHED` |

## 6. Effective Authority After Closure

- This dossier (additive) + sealed HYP_007 artifacts (immutable).
- Next scientific action: descriptive failure decomposition and **conditional** HYP_008 research
  inception per the authorization workflow (see `HYP_007_POST_R4_FAILURE_DECOMPOSITION.md`
  and `HYP_008_RESEARCH_INCEPTION_REVIEW.md`).