# ACASH — Risk Register & Mitigation Strategy (Phase 0)

**Document:** `docs/RISKS.md`  
**Version:** 3.0.0 (Final Review Corrections Applied)  
**Date:** 2026-08-27  

---

## 1. Risk Matrix Overview

| Risk ID | Category | Description | Severity | Probability | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-01** | Quantitative | Overfitting / Data Snooping from multiple parameter trials | High | High | Combinatorial Purged CV, Deflated Sharpe Ratio (DSR), mandatory held-out OOS split. |
| **RSK-02** | Data | Look-ahead bias / Temporal leakage in features | Critical | Medium | Bi-temporal indexing ($t_{\text{knowledge}} \le T_{\text{decision}}$), automated timestamp leakage unit tests. |
| **RSK-03** | Financial | Optimizer estimation error / Error maximization in skfolio | High | Medium | **Evaluate skfolio against transparent baselines (1/N, Inv Vol, Cash); allow baseline selection if optimizer fails OOS.** |
| **RSK-04** | Data Source | `yfinance` throttling, missing adjustments, or API endpoint changes | Medium | Medium | Strict isolation behind `IMarketDataProvider`; use for research only; automated sanity checks on ingested bars. |
| **RSK-05** | Execution | NautilusTrader integration complexity or PoC failure | Medium | Medium | Maintain sovereign ACASH interfaces (`IBacktestEngine`, `IExecutionEngine`); replace adapter if PoC criteria fail. |
| **RSK-06** | Operational | Broker API disconnection / Unacknowledged orders in MT5 | High | Medium | Heartbeat monitors, background order reconciliation loop, deadman timeout fail-safes. |
| **RSK-07** | Systemic | Uncontrolled order loop / Duplicate execution bug | Critical | Low | Idempotency keys on all orders, orders-per-minute rate limiter, global kill switch. |
| **RSK-08** | Technical | Transactional concurrency bottlenecks in local Parquet/DuckDB | Low-Med | Low (V1) | Defer PostgreSQL until concurrent multi-process writer or durable control-plane requirements emerge. |
| **RSK-09** | Governance | Premature live trading without rigorous validation | Critical | Low | Mandatory Human Approval Gate (Section 37); live mode physically disabled in codebase by default. |

---

## 2. In-Depth Mitigation Protocols

### 2.1 Baseline Allocation Safety Valve
To mitigate the risk of sophisticated portfolio optimization error maximization:
- The system evaluates $\Delta \text{Sharpe}_{\text{OOS}} = \text{Sharpe}(\mathbf{w}_{\text{skfolio}}) - \max(\text{Sharpe}(\mathbf{w}_{\text{EW}}), \text{Sharpe}(\mathbf{w}_{\text{InvVol}}))$.
- If $\Delta \text{Sharpe}_{\text{OOS}} \le 0$ or uncertainty is high, the system automatically allocates to the simpler baseline or Cash.

### 2.2 yfinance Research Adapter Containment
- `yfinance` is barred from live execution.
- All bars downloaded via `yfinance` undergo geometric validation ($\text{High} \ge \max(\text{Open}, \text{Close})$, $\text{Low} \le \min(\text{Open}, \text{Close})$, $\text{Volume} \ge 0$) and duplicate timestamp checks before storage in Parquet format.

### 2.3 Decoupled Execution Adapter Safety
- `MT5Adapter` and `NautilusTraderAdapter` implement `IExecutionEngine`.
- If an adapter fails to reconcile positions or experiences API timeouts $> 60\text{s}$, the sovereign Risk Engine trips the **Kill Switch**, freezing active order dispatching.
