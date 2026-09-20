# MEC-0015: Partition Governance & Economic Acceptance Contract

```text
[GOVERNANCE ARTIFACT: PARTITION GOVERNANCE AND ECONOMIC ACCEPTANCE CONTRACT]
[GENERATED: 2026-09-20]
[UPDATED: 2026-09-21]
[CANONICAL STARTING HEAD: dd249d54e59c471bfdc98bc3c6d17781cbc2a08e]
[HYP_005: NOT CREATED]
[BACKTEST: NOT STARTED]
[ALL THRESHOLDS DECLARED PRIOR TO OBSERVING ANY STRATEGY RESULTS]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true]
```

> [!IMPORTANT]
> All acceptance thresholds in this document are declared **BEFORE** any strategy
> results are observed. Post-hoc threshold adjustment is strictly prohibited
> (ANTI-HARKING invariant).

---

## 1. Historical Sample Contamination Audit

The following historical periods are **not pristine** for MEC-0015:

| Period | Exposure Source | Contamination Type |
| :--- | :--- | :--- |
| 2007-05 through 2024-04 | Zarattini, Aziz, Barbon (SSRN 4824172, rev Sept 2025) | Primary paper reports performance |
| 2017-01 through 2022-12 | ACASH HYP_003 and HYP_004 | ACASH internal econometric evaluation |
| 2024-05 through 2026-03 (approx.) | Paz Sheimy, Delgado (SSRN 7323419) | Public post-publication replications |

**Conclusion: No historical period through approximately March 2026 can be claimed as a pristine external holdout.**

---

## 2. Canonical Partition Designations (RESOLVED)

### 2.1. M1 — Publication-Exposed Replication Window

```
REPLICATION_WINDOW_START = 2007-05-01
REPLICATION_WINDOW_END   = 2024-04-30
ROLE = PUBLICATION_EXPOSED_REPLICATION_SAMPLE
```

**Purpose:** Verify whether ACASH can reproduce the published mechanism under its qualified data
and friction contract. Not out-of-sample. Not blind.

> [!WARNING]
> Successfully replicating performance in this window does NOT constitute independent evidence
> of genuine alpha. The paper already reports these results. Replication validates data and
> implementation fidelity ONLY.

### 2.2. M2 — Publicly-Exposed Post-Publication Stress Window

```
STRESS_WINDOW_START = 2024-05-01
STRESS_WINDOW_END   = [LAST PUBLICLY EXPOSED REPLICATION DATE]
ROLE = PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE
```

**Purpose:** Characterize whether the edge survives post-publication. Not blind OOS.
Paz Sheimy and Delgado (2026) have already published performance over this window.

### 2.3. M3 — True Holdout (Prospective Only)

```
TRUE_EXTERNAL_HOLDOUT = PROSPECTIVE_ONLY
HOLDOUT_START = AFTER_HYP_005_PREREGISTRATION_DATE (future)
ROLE = GENUINE_BLIND_OOS
```

**Policy:** No historical period already discussed in any published literature, public replication,
or ACASH internal evaluation may be labeled "pristine". The true holdout can only begin
**prospectively** after `HYP_005` is formally pre-registered.

`PROSPECTIVE_HOLDOUT_AUTHORIZATION = SEPARATE_HUMAN_DECISION_REQUIRED`

---

## 3. HYP_005 Staged Research Design (Pre-Declared)

| Stage | Name | Description |
| :--- | :--- | :--- |
| **R1** | Registration & Strategy Freeze | Exact strategy specification sealed via HYP_005 preregistration |
| **R2** | Dataset Build & Lineage Seal | Alpaca SIP bars, quotes, dividends dataset built and lineage sealed |
| **R3** | Replication (M1 window) | Publication-exposed historical replication (2007-05 — 2024-04) |
| **R4** | Stress Evaluation (M2 window) | Post-publication stress evaluation (2024-05 onward, exposed dates only) |
| **R5** | Evidence Decision Gate | Human ratification: is evidence sufficient to authorize prospective Paper/shadow? |
| **R6** | Prospective Evaluation | Untouched forward evaluation (M3 window); separate authorization required |
| **Live** | Live Authorization | **Requires separate explicit human authorization. NOT authorized here.** |

---

## 4. Primary Historical Replication Gate (R3 — Pre-Declared)

Thresholds apply to the **net** (after all frictions) strategy performance over M1:

| Gate Criterion | Threshold | Rationale |
| :--- | :--- | :--- |
| `NET_TOTAL_RETURN > 0` | Strictly positive | Strategy must generate positive net wealth |
| `NET_SHARPE >= 1.00` | Annualized | Paper reports ≈1.33; threshold demands usable economic performance |
| `MAX_DRAWDOWN <= 30%` | Peak-to-trough | Paper reports ≈25%; threshold provides margin above reported value |
| `MINIMUM_COMPLETED_TRADES >= 100` | Exact floor | `HUMAN_RATIFIED_SAMPLE_ADEQUACY_FLOOR` (non-result-dependent floor) |
| `NO_MATERIAL_CONTRACT_FAILURE` | Zero | Zero silent imputation or contract breach in dataset |
| `2X_FRICTION_STRESS_NET_RETURN > 0` | Strictly positive | Strategy survives doubled friction stack |
| `2X_FRICTION_STRESS_NET_SHARPE >= 0.75` | Annualized | Viability under adverse transaction cost stress |

**`PRIMARY_HISTORICAL_REPLICATION_GATE = [NET_SHARPE >= 1.00, MDD <= 30%, TRADES >= 100, 2X_STRESS > 0]`**

If R3 gate fails: `HYP_005_REPLICATION_FAILED` → no further authorization.

---

## 5. Recent Stress Gate (R4 — Pre-Declared)

Thresholds apply to the **net** strategy performance over M2 (publicly exposed post-publication window):

| Gate Criterion | Threshold | Rationale |
| :--- | :--- | :--- |
| `NET_TOTAL_RETURN > 0` | Strictly positive | Edge must survive recent period |
| `NET_SHARPE >= 0.50` | Annualized | Below R3 threshold; acknowledges public evidence of degradation |
| `MAX_DRAWDOWN <= 35%` | Peak-to-trough | Captures regime deterioration |
| `NO_CATASTROPHIC_RISK_FAILURE` | Zero | No extreme leverage or blow-up events |
| `2X_FRICTION_STRESS_TOTAL_RETURN >= 0` | Non-negative | Cost-stress survivability |

> [!WARNING]
> The M2 stress window is **publicly exposed** and cannot independently qualify the strategy.
> Passing R4 is necessary but not sufficient for Paper authorization.
> If R4 fails: `HYP_005_CURRENT_EDGE_NOT_SUPPORTED` → Paper authorization is NOT granted.
> **Do NOT tune parameters or alter strategy design in response to R4 results.**

**`RECENT_STRESS_GATE = [NET_SHARPE >= 0.50, NET_RETURN > 0, MDD <= 35%]`**

---

## 6. Benchmark Contract (RESOLVED)

| Benchmark | Definition | Purpose |
| :--- | :--- | :--- |
| **Primary** | SPY buy-and-hold total return (dividend-inclusive) | Opportunity cost benchmark |
| **Supplementary** | Excess CAGR over SPY | Absolute alpha measure |
| **Supplementary** | Excess total return | Wealth comparison |
| **Supplementary** | Information ratio | Risk-adjusted active return |
| **Supplementary** | Exposure-matched SPY | Volatility-matched comparison |

**`PRIMARY_BENCHMARK = SPY_BUY_AND_HOLD_TOTAL_RETURN`**

---

## 7. Anti-Harking Invariants

All thresholds above are declared before observing any ACASH strategy results:

| Invariant | Enforcement |
| :--- | :--- |
| No post-hoc threshold adjustment | Thresholds sealed in this document at commit SHA |
| No parameter tuning after observing R3 results | Anti-HARKING prohibition |
| No parameter tuning after observing R4 results | Anti-HARKING prohibition |
| Partitions are fixed before implementation | M1, M2, M3 designations locked |

---

## 8. Summary of Partition & Acceptance Decisions

| Item | Status | Governing Specification |
| :--- | :--- | :--- |
| Replication window (M1) definition | `RESOLVED` | 2007-05-01 through 2024-04-30 |
| Stress window (M2) definition | `RESOLVED` | 2024-05-01 through last exposed date |
| True holdout policy (M3) | `RESOLVED` | `PROSPECTIVE_ONLY` |
| HYP_005 staged research design (R1–R6) | `RESOLVED` | Staged research plan locked |
| Primary historical replication gate (R3) | `RESOLVED` | Net Sharpe $\ge 1.00$, MDD $\le 30\%$, Trades $\ge 100$, 2× stress |
| Recent stress gate (R4) | `RESOLVED` | Net Sharpe $\ge 0.50$, MDD $\le 35\%$, Return $> 0$ |
| Benchmark contract | `RESOLVED` | Primary: SPY buy-and-hold total return |
| Minimum trade count floor | `RESOLVED` | `MINIMUM_COMPLETED_TRADES = 100` (`HUMAN_RATIFIED_SAMPLE_ADEQUACY_FLOOR`) |

**TOTAL REMAINING OPEN PARTITION/GATE BLOCKERS: 0**
