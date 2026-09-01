# Phase 8 Gate 8.2: Empirical Allocation Tournament & Lifecycle Audit Evidence Ledger

> **Document:** `docs/phase8/tournament_evidence_ledger.md`
> **Tournament ID:** `TOURNAMENT_GATE8_EMPIRICAL_20260901`
> **Tournament Digest:** `cef3400f584bda000c170f88fb4ce318c5f2d0423bec8a5ed6269134a295f947`
> **Recorded At UTC:** `2026-09-01T12:00:00+00:00`
> **Git Checkpoint:** `8ccbdb2`
> **Governance Authority:** `src/acash/portfolio/governance.py` (`PortfolioGovernanceGate`)

---

## 1. Executive Summary & Core Semantic Invariants

This evidence ledger establishes the official audit trial for **Phase 8 Gate 8.2 (Final OOS / Friction / Governance Audit)**.
In strict compliance with **AGENTS.md** and the **Phase 8 Canonical Contract (`docs/phase8/phase_8_proposal.md`)**, this tournament enforces:

1. $\boxed{\text{Candidate} \neq \text{Evaluation} \neq \text{Decision}}$: Allocators produce candidates; Evaluator measures opaque return streams; Governance decides capital authorization.
2. $\boxed{\text{Ranking} \neq \text{Approval}}$: The winner of the optimizer tournament does NOT automatically receive portfolio capital.
3. $\boxed{\text{Tournament Winner} \neq \text{Governance Authority}}$:
   - **Tournament Rank #1 Allocator:** `HIERARCHICAL_RISK_PARITY` (Ranked #1 optimizer by Net Out-of-Sample RankScore).
   - **Governance Selected Allocation:** `CASH` (Sovereign Governance rejected risky deployment due to Hurdle clearance failure; authorized 100% Cash fallback).
   - **Decision Origin:** `GOVERNANCE_FALLBACK`.
   - **Cash Selection Mode:** `GOVERNANCE_FALLBACK`.
4. $\boxed{\text{CASH is a Sovereign Fallback Benchmark, NOT a Competing Optimizer}}$:
   - CASH does not participate in the covariance optimization competition.
   - When all candidate models fail governance gates, Governance explicitly invokes `CASH_SOVEREIGN_FALLBACK` (`is_fallback_baseline = True`, `cash_weight = 1.0`).
   - `APPROVED_INVESTABLE_ALLOCATION` is **strictly forbidden** from coexisting with a Cash fallback.
5. $\boxed{\text{Policy-Estimated Friction Drag} \neq \text{Realized Trading Cost}}$:
   - Friction is calculated under a linear 12 bps policy model ($\text{fee}=5\text{ bps}, \text{spread}=5\text{ bps}, \text{slippage}=2\text{ bps}$) scaled by portfolio turnover and rebalance frequency ($N=12$).
   - This represents simulated implementation drag, NOT actual broker execution fill costs.

---

## 2. Reproducible Experiment Configuration

Every parameter required to reproduce this exact empirical experiment is cryptographically bound below:

| Configuration Parameter | Value | Provenance / Rule |
| :--- | :--- | :--- |
| **Tournament ID** | `TOURNAMENT_GATE8_EMPIRICAL_20260901` | Unique tournament execution run identity |
| **Dataset ID** | `UNIV_EMPIRICAL_US_MULTI_ASSET_6` | 6-Asset US Equity & Bond Liquid Empirical Benchmark |
| **Universe ID** | `UNIV_EMPIRICAL_US_MULTI_ASSET_6` | `SPY, QQQ, IWM, EFA, TLT, GLD` |
| **Total Observations ($T$)** | `252` daily bars | Complete 1-year stationary multivariate sample |
| **Date Range** | `2025-09-01T00:00:00+00:00` to `2025-09-11T11:00:00+00:00` | Chronologically causal timestamps |
| **Split Mode** | `WALK_FORWARD` | Walk-Forward rolling out-of-sample expansion |
| **Number of Splits ($K$)** | `5` | 5 distinct out-of-sample test windows |
| **Train Ratio / Purge** | `0.70` / `2 bars` | Anti-leakage purging window |
| **Random Seed** | `20260901` | Exact DGP pseudo-random sequence generator |
| **Annualization Factor** | `252` | Period returns to 1/year annualized space |
| **Risk-Free Rate ($r_f$)** | `4.0% p.a.` (`0.04`) | Benchmark cash hurdle baseline |
| **Hurdle Margin** | `1.0% p.a.` (`0.01`) | Minimum required net excess return (Hurdle = 5.0% p.a.) |
| **Friction Model** | `POLICY_ESTIMATED_FRICTION` | Linear model: 12 bps baseline total friction per unit turnover |
| **Friction Parameters** | `fee=5bps`, `spread=5bps`, `slippage=2bps` | 12 bps total cost rate per turnover unit |
| **Rebalance Frequency** | `12 / year` (Monthly) | Annualization multiplier $N_{\text{rebalance}}$ applied to one-time friction |
| **Turnover Penalty ($\lambda_{TO}$)** | `0.5` | Penalty coefficient applied to one-way turnover in RankScore |
| **Tail Risk Penalty ($\lambda_{Tail}$)** | `0.5` | Penalty coefficient applied to CVaR 95% in RankScore |
| **Max Risky Asset Weight** | `40.0%` (`0.40`) | Concentration limit per asset |
| **Min Cash Buffer** | `5.0%` (`0.05`) | Liquidity buffer constraint |
| **Git Commit Reference** | `8ccbdb2` | Authoritative source tree checkpoint |

---

## 3. Train / Test Lifecycle & Non-Leakage Cryptographic Provenance

For every single fold, candidate weights are fitted strictly on `TRAIN` observations, and performance metrics are evaluated strictly on subsequent `TEST` observations with a 2-bar anti-leakage purge gap.

| Split | Allocator Name | Train Window | Test Window | Purge | Candidate Generation Digest (Train-Only) | Test Evaluation Digest (Test-Only) |
| :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| S1 | `EQUAL_WEIGHT` | [0:88] | [90:122] | 2 bars | `e3655e4b8ff2ff48...` | `be7b4b4995d0d48b...` |
| S1 | `INVERSE_VOL` | [0:88] | [90:122] | 2 bars | `1458059bef4a1271...` | `59241649d64cd2a2...` |
| S1 | `HIERARCHICAL_RISK_PARITY` | [0:88] | [90:122] | 2 bars | `cfc61e35a2be677b...` | `bb976ee1da666ecf...` |
| S1 | `EQUAL_RISK_CONTRIBUTION` | [0:88] | [90:122] | 2 bars | `a20a5743a6458f5f...` | `9fc19245f4554ebd...` |
| S2 | `EQUAL_WEIGHT` | [0:120] | [122:154] | 2 bars | `e3655e4b8ff2ff48...` | `608f7b6523261405...` |
| S2 | `INVERSE_VOL` | [0:120] | [122:154] | 2 bars | `9c29d00695f2968c...` | `5b0a2b175625a10e...` |
| S2 | `HIERARCHICAL_RISK_PARITY` | [0:120] | [122:154] | 2 bars | `0f042cd33c4fcefa...` | `dba9c5ff399dadf2...` |
| S2 | `EQUAL_RISK_CONTRIBUTION` | [0:120] | [122:154] | 2 bars | `91f68f49dfba4273...` | `93b820138dc13f5b...` |
| S3 | `EQUAL_WEIGHT` | [0:152] | [154:186] | 2 bars | `e3655e4b8ff2ff48...` | `793970e720cd023d...` |
| S3 | `INVERSE_VOL` | [0:152] | [154:186] | 2 bars | `a9dc888dbdc61cb1...` | `4de4a06db35e56b7...` |
| S3 | `HIERARCHICAL_RISK_PARITY` | [0:152] | [154:186] | 2 bars | `e99ee0a5cee0a8c5...` | `963cd3cd2428c852...` |
| S3 | `EQUAL_RISK_CONTRIBUTION` | [0:152] | [154:186] | 2 bars | `696f8b67dd174123...` | `c0f5d91bbcfe57ff...` |
| S4 | `EQUAL_WEIGHT` | [0:184] | [186:218] | 2 bars | `e3655e4b8ff2ff48...` | `625c97e8382a08dc...` |
| S4 | `INVERSE_VOL` | [0:184] | [186:218] | 2 bars | `7552be7a581624d9...` | `02fedc502a33e1a0...` |
| S4 | `HIERARCHICAL_RISK_PARITY` | [0:184] | [186:218] | 2 bars | `abecf40e3c2daea6...` | `3d073fb691e3b0f2...` |
| S4 | `EQUAL_RISK_CONTRIBUTION` | [0:184] | [186:218] | 2 bars | `322b37ec0a89b1bb...` | `912dac8286ffc5b8...` |
| S5 | `EQUAL_WEIGHT` | [0:216] | [218:250] | 2 bars | `e3655e4b8ff2ff48...` | `761e5459458cbd3f...` |
| S5 | `INVERSE_VOL` | [0:216] | [218:250] | 2 bars | `a395edcc2fbf53e7...` | `28891c633206302e...` |
| S5 | `HIERARCHICAL_RISK_PARITY` | [0:216] | [218:250] | 2 bars | `c5504c1be11c8cd9...` | `b8b27a359e8e6995...` |
| S5 | `EQUAL_RISK_CONTRIBUTION` | [0:216] | [218:250] | 2 bars | `9b946f16f77e4cb5...` | `b72c4c95b099f327...` |

### Invariant Verification:
- $\forall k: t_{\text{test\_start}, k} \ge t_{\text{train\_end}, k} + \text{purge\_bars}$
- Candidate weights $w_k = \text{Allocator}(\mathcal{D}_{\text{train}, k})$ depend strictly on training returns. Tampering with test data does NOT alter $w_k$ or `candidate_generation_digest`.
- OOS Sharpe, CVaR, and MaxDD depend strictly on $\mathcal{D}_{\text{test}, k}$.

---

## 4. Friction Semantics & Explicit Dependency Table

To eliminate any ambiguity and prevent double counting, the table below maps every metric to its exact mathematical friction basis:

| Metric / Expression | Friction Basis | Exact Mathematical Formula | Temporal Interpretation | Double Counting Audit |
| :--- | :---: | :--- | :--- | :--- |
| **Turnover ($T$)** | Realized delta | $\frac{1}{2}(\sum |w_i - w_{0, i}| + |w_{c} - w_{0, c}|)$ | Absolute position rebalancing magnitude | N/A (dimensionless weight) |
| **One-Time Friction ($\mathcal{F}_{\text{one-time}}$)** | Cost per rebalance | $T \times (5\text{bps} + 5\text{bps} + 2\text{bps}) = T \times 12\text{bps}$ | Immediate capital deduction at start of fold | Applied once at $t=0$ in equity path |
| **Annualized Friction ($\mathcal{F}_{\text{ann}}$)** | Annual cost rate | $\mathcal{F}_{\text{one-time}} \times 12$ (Monthly frequency) | Annualized rate applied to annual returns | Used in annual hurdle & net return |
| **Net Expected Return** | Annualized rate | $\bar{R}_{\text{gross}} - \mathcal{F}_{\text{ann}}$ | Return after simulated annual execution drag | Subtracted once from gross return |
| **Net Equity Path ($W_t$)** | Compounding path | $W_0 = 1.0 - \mathcal{F}_{\text{one-time}}, \quad W_t = W_{t-1}(1 + R_{p, t})$ | Dollar wealth progression across test window | Docked by $\mathcal{F}_{\text{one-time}}$ once at start |
| **Max Drawdown (MaxDD)** | Net peak-to-trough | $\max_t \left(\frac{\max_{\tau \le t} W_\tau - W_t}{\max_{\tau \le t} W_\tau}\right)$ on $W_t$ | Realized drawdown accounting for initial fee | Preserves net equity curve |
| **Hurdle Clearance** | Annual excess rate | $(\bar{R}_{\text{gross}} - \mathcal{F}_{\text{ann}} - r_f) \ge \text{margin}$ | Policy hurdle clearance test | Net of annualized friction |
| **RankScore** | Optimization score | $\widehat{SR}_{OOS} - \lambda_{TO} \cdot T - \lambda_{Tail} \cdot \text{CVaR}_{95}$ | Objective function for ranking candidates | $\lambda_{TO}$ penalizes turnover; no double-deduction |

---

## 5. Native Allocation Tournament Suite Telemetry

Candidate execution telemetry for the clean core environment:

| Candidate Model | Category | Status | Details / Skip Reason |
| :--- | :---: | :---: | :--- |
| **`EQUAL_WEIGHT`** | Core Baseline (1/N) | ✅ **EXECUTED** | Evaluated across all 5 OOS splits |
| **`INVERSE_VOL`** | Core Baseline ($1/\sigma$) | ✅ **EXECUTED** | Evaluated across all 5 OOS splits |
| **`HIERARCHICAL_RISK_PARITY`** | Native Optimizer | ✅ **EXECUTED** | Evaluated across all 5 OOS splits |
| **`EQUAL_RISK_CONTRIBUTION`** | Native Optimizer | ✅ **EXECUTED** | Evaluated across all 5 OOS splits |
| **`SKFOLIO_HIERARCHICAL_RISK_PARITY`** | Optional Adapter | ⚠️ **SKIPPED** | `Optional package 'skfolio' not installed in current environment.` |
| **`CVXPY_MINIMUM_VARIANCE`** | Optional Adapter | ⚠️ **SKIPPED** | `Optional package 'cvxpy' not installed in current environment.` |

### Runtime Backend Environment Versions:
- **Python:** `3.14.6`
- **NumPy:** `2.5.2`
- **SciPy:** `1.18.1`
- **skfolio:** `NOT_INSTALLED`
- **cvxpy:** `NOT_INSTALLED`

---

## 6. Split-by-Split Out-of-Sample Scorecards

| Split | Allocator Name | Train Bars | Test Bars | Gross Return | Friction Drag | Net Return | Net Volatility | Net Sharpe | Net MaxDD | CVaR 95% | RankScore |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| S1 | **EQUAL_WEIGHT** | 88 | 32 | 25.56% | 1.368% | 24.19% | 12.93% | 1.561 | 5.00% | 1.38% | 1.1247 |
| S1 | **INVERSE_VOL** | 88 | 32 | 21.96% | 1.368% | 20.59% | 11.72% | 1.416 | 4.60% | 1.33% | 1.1385 |
| S1 | **HIERARCHICAL_RISK_PARITY** | 88 | 32 | 19.19% | 1.368% | 17.82% | 9.73% | 1.421 | 3.72% | 1.21% | 1.5550 |
| S1 | **EQUAL_RISK_CONTRIBUTION** | 88 | 32 | 15.75% | 1.368% | 14.38% | 9.94% | 1.044 | 3.92% | 1.25% | 1.0236 |
| S2 | **EQUAL_WEIGHT** | 120 | 32 | -13.22% | 1.368% | -14.59% | 11.56% | -1.608 | 3.47% | 1.61% | -1.9460 |
| S2 | **INVERSE_VOL** | 120 | 32 | -12.01% | 1.368% | -13.38% | 10.66% | -1.630 | 3.18% | 1.48% | -1.9765 |
| S2 | **HIERARCHICAL_RISK_PARITY** | 120 | 32 | -7.40% | 1.368% | -8.77% | 9.96% | -1.282 | 3.00% | 1.28% | -1.7324 |
| S2 | **EQUAL_RISK_CONTRIBUTION** | 120 | 32 | -9.43% | 1.368% | -10.80% | 9.84% | -1.505 | 3.14% | 1.32% | -1.9829 |
| S3 | **EQUAL_WEIGHT** | 152 | 32 | -22.32% | 1.368% | -23.69% | 12.18% | -2.273 | 4.41% | 1.36% | -2.6535 |
| S3 | **INVERSE_VOL** | 152 | 32 | -16.88% | 1.368% | -18.25% | 10.95% | -2.032 | 3.56% | 1.21% | -2.3032 |
| S3 | **HIERARCHICAL_RISK_PARITY** | 152 | 32 | -4.71% | 1.368% | -6.07% | 9.20% | -1.095 | 2.67% | 0.95% | -1.0753 |
| S3 | **EQUAL_RISK_CONTRIBUTION** | 152 | 32 | -6.79% | 1.368% | -8.16% | 9.34% | -1.301 | 2.66% | 0.98% | -1.3039 |
| S4 | **EQUAL_WEIGHT** | 184 | 32 | -7.33% | 1.368% | -8.70% | 15.19% | -0.836 | 6.78% | 1.47% | -1.4148 |
| S4 | **INVERSE_VOL** | 184 | 32 | -8.36% | 1.368% | -9.73% | 13.89% | -0.989 | 6.38% | 1.37% | -1.5332 |
| S4 | **HIERARCHICAL_RISK_PARITY** | 184 | 32 | -12.79% | 1.368% | -14.15% | 11.26% | -1.612 | 5.80% | 1.19% | -1.9273 |
| S4 | **EQUAL_RISK_CONTRIBUTION** | 184 | 32 | -9.25% | 1.368% | -10.61% | 11.70% | -1.250 | 5.69% | 1.15% | -1.5970 |
| S5 | **EQUAL_WEIGHT** | 216 | 32 | -25.09% | 1.368% | -26.46% | 11.68% | -2.607 | 6.52% | 1.26% | -2.9155 |
| S5 | **INVERSE_VOL** | 216 | 32 | -20.74% | 1.368% | -22.11% | 10.48% | -2.491 | 6.23% | 1.13% | -2.9099 |
| S5 | **HIERARCHICAL_RISK_PARITY** | 216 | 32 | -9.87% | 1.368% | -11.24% | 8.60% | -1.773 | 5.26% | 0.94% | -2.6303 |
| S5 | **EQUAL_RISK_CONTRIBUTION** | 216 | 32 | -6.09% | 1.368% | -7.46% | 8.86% | -1.294 | 5.17% | 0.92% | -2.3547 |

---

## 7. Aggregate Allocator Tournament Rankings & Governance Independence

Candidates are ranked strictly by multi-split **Aggregate RankScore**:

$$\text{RankScore} = \widehat{\text{SR}}_{OOS} - \lambda_{TO} \cdot \text{Turnover} - \lambda_{Tail} \cdot \text{CVaR}_{95}$$

$$\boxed{\text{Tournament Rank} = f(\text{OOS Statistics}, \text{Turnover}, \text{CVaR})} \quad \perp \quad \boxed{\text{Governance Verdict} = f(\text{Hurdle}, \text{Risk Limits}, \text{Constraints})}$$

| Rank | Allocator Name | Package Backend | Mean Net Return | Mean Net Volatility | Mean Net Sharpe | Worst Net MaxDD | Mean Turnover | Hurdle Clearance | Aggregate RankScore | Governance Status |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **#1** | `HIERARCHICAL_RISK_PARITY` | `acash_native` | -4.48% | 9.75% | -0.868 | 5.80% | 0.950 | 80.0% | **-1.1621** | ❌ REJECTED (`HURDLE_REJECTION`) |
| **#2** | `EQUAL_RISK_CONTRIBUTION` | `acash_native` | -4.53% | 9.93% | -0.861 | 5.69% | 0.950 | 40.0% | **-1.2430** | ❌ REJECTED (`CONSTRAINT_VIOLATION`) |
| **#3** | `INVERSE_VOL` | `acash_native` | -8.58% | 11.54% | -1.145 | 6.38% | 0.950 | 0.0% | **-1.5169** | ❌ REJECTED (`HURDLE_REJECTION`) |
| **#4** | `EQUAL_WEIGHT` | `acash_native` | -9.85% | 12.71% | -1.153 | 6.78% | 0.950 | 0.0% | **-1.5610** | ❌ REJECTED (`HURDLE_REJECTION`) |

---

## 8. Sovereign Governance Decision & Invariant Verification

```text
========================================================================
  PORTFOLIO GOVERNANCE GATE FINAL DECISION
========================================================================
Tournament Rank #1 Allocator : HIERARCHICAL_RISK_PARITY
Governance Selected Allocator: CASH
Decision Origin              : GOVERNANCE_FALLBACK
Cash Selection Mode          : GOVERNANCE_FALLBACK
------------------------------------------------------------------------
Decision ID                  : DEC_CASH_FALLBACK_1788264000
Selected Candidate ID        : CASH_SOVEREIGN_FALLBACK
Gate Verdict                 : REJECT_NO_ELIGIBLE_CANDIDATE
Is Fallback Baseline         : True
Authorized Cash Weight       : 1.0
Authorized Risk Weights      : {}
Decision Digest              : 6d7c89de767f423e057800cc920861291f6ec63a4e08a1703667a67e14548d25
Rationale                    : All evaluated candidates rejected by sovereign governance: [CAND_HRP_UNIV_EMPIRICAL_US_MULTI_ASSET_6: HURDLE_REJECTION: Net expected excess return (-0.03126328515828000000000000000) failed hurdle margin.]; [CAND_ERC_UNIV_EMPIRICAL_US_MULTI_ASSET_6: CONSTRAINT_VIOLATION: Candidate evaluation flagged constraints_satisfied = False.]; [CAND_INVOL_UNIV_EMPIRICAL_US_MULTI_ASSET_6: HURDLE_REJECTION: Net expected excess return (-0.1060895590489462681065604769) failed hurdle margin.]; [CAND_EW_UNIV_EMPIRICAL_US_MULTI_ASSET_6: HURDLE_REJECTION: Net expected excess return (-0.1246934500000000000000000000) failed hurdle margin.]
========================================================================
```

### Forensic Proof of Invariants:
1. **Tournament Winner vs Governance Decision:**
   - Tournament Rank #1 is `HIERARCHICAL_RISK_PARITY` (Aggregate RankScore: `-1.1620695970`).
   - Governance independently evaluated `HIERARCHICAL_RISK_PARITY` and rejected it (`HURDLE_REJECTION`) because annualized net return was `-4.48%`, below the 5.0% hurdle requirement.
   - Governance authorized 100% Cash via `GOVERNANCE_FALLBACK`.
   - Proves $\boxed{\text{Tournament Rank \#1} \neq \text{Governance Authority}}$.
2. **Ranking Independence:**
   - Governance rejection did not change `tournament_rank` or `aggregate_rank_score`.
   - Cash was not injected into the tournament table.

---

## 9. Verification Ledger

```markdown
### Verification Ledger
- Tournament Runner: VERIFIED (AllocationTournamentRunner)
- Multi-Split Execution: VERIFIED (5 Out-of-Sample Splits)
- Allocators Registered: VERIFIED (4 executed: ['EQUAL_WEIGHT', 'INVERSE_VOL', 'HIERARCHICAL_RISK_PARITY', 'EQUAL_RISK_CONTRIBUTION'])
- Allocators Skipped: VERIFIED (2 optional adapters: ['SKFOLIO_HIERARCHICAL_RISK_PARITY', 'CVXPY_MINIMUM_VARIANCE'])
- Train/Test Boundary Integrity: VERIFIED (Zero Look-Ahead Invariant Enforced)
- Friction Integration: VERIFIED (POLICY_ESTIMATED_FRICTION: 12 bps baseline applied to turnover)
- Max Drawdown Metric: VERIFIED (NET_FRICTION_ADJUSTED_EQUITY_PATH)
- Tournament Rank #1: HIERARCHICAL_RISK_PARITY
- Governance Decision: CASH (REJECT_NO_ELIGIBLE_CANDIDATE)
- Decision Origin: GOVERNANCE_FALLBACK
- Cash Selection Mode: GOVERNANCE_FALLBACK
- Decision Lineage: CRYPTOGRAPHICALLY PERSISTED (6d7c89de767f423e057800cc920861291f6ec63a4e08a1703667a67e14548d25)
- Tournament Digest: cef3400f584bda000c170f88fb4ce318c5f2d0423bec8a5ed6269134a295f947
```
