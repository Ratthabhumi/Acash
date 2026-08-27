# ACASH — Comprehensive Technology & Open-Source Evaluation (Phase 0 Final)

**Document:** `docs/TECHNOLOGY_EVALUATION.md`  
**Version:** 3.1.0 (Cleanup & Precision Applied)  
**Date:** 2026-08-27  
**Evaluation Standard:** Master Engineering Prompt & Phase 0 Final Review  

---

## 1. Evaluation Principles & Decision Classifications

ACASH evaluates external technologies based on actual technical fit, mathematical correctness, architectural independence, and operational safety:

- **ADOPT:** Integrate directly as a core component/dependency because it delivers proven correctness, maintenance quality, and superior value over building from scratch.
- **ADAPT:** Integrate behind ACASH abstract interfaces to keep sovereign domain models completely insulated from vendor lock-in.
- **REFERENCE:** Study architectural patterns, mathematical formulations, and edge-case handling without introducing runtime dependencies.
- **EXPERIMENT:** Sandbox in isolated research experiments (`experiments/`). Prohibit from core allocation or live execution paths until empirical evidence justifies adoption.
- **DEFER:** Do not install or implement in early phases; reconsider when specific operational, architectural, or transactional requirements emerge.
- **REJECT:** Explicitly do not use. Document technical rationale to prevent redundant future re-evaluation.

---

## 2. Complete Technology Decision Matrix

| # | Candidate / Technology | Domain / Layer | Primary ACASH Problem Solved | Maturity | License | Maintenance | Integration Cost | Lock-in Risk | Performance | ACASH Fit | Final Decision |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **ACASH Core** | Sovereign Architecture | Domain logic, Risk boundary, Decision ledger, State machine | Custom | Sovereign | High (Internal) | Low | None | High | Perfect | **ADOPT (Foundational)** |
| 2 | **skfolio** | Portfolio Optimization | Portfolio optimization & risk allocation (HRP, ERC, CVaR), Scikit-Learn API, CPCV | High | BSD-3-Clause | Active | Low | Very Low | High | High | **ADOPT** |
| 3 | **NautilusTrader** | Simulation & Execution | Tier-2 event-driven simulation & future execution candidate | High | LGPL-3.0 | Very Active | Medium | Low (via Adapter) | Ultra-High (Rust) | High | **ADAPT (Tier-2 Sim & Future Exec Candidate)** |
| 4 | **vectorbt (OSS)** | Research & Screening | Fast Numba-vectorized parameter sweeps & factor screening | High | Apache-2.0 | Active | Low | Low | Ultra-High | High | **ADAPT (Tier-1 Screening)** |
| 5 | **QuantConnect LEAN**| Trading Engine | Architectural benchmark for multi-asset slicing & fill models | Very High | Apache-2.0 | Active | High (.NET CLR) | High | High | Medium | **USE AS REFERENCE** |
| 6 | **Freqtrade** | Crypto Trading | Reference for CCXT rate limits, order reconciliation, dry-run | High | GPL-3.0 | Very Active | High | High | Moderate | Low | **USE AS REFERENCE** |
| 7 | **Hummingbot** | Market Making | Order book liquidity provision & Avellaneda-Stoikov quoting | High | Apache-2.0 | Active | High | High | High | Specialized | **SPECIALIZED FUTURE OPTION (DEFERRED)** |
| 8 | **Kronos** | AI Forecasting | Foundation model time-series forecasting experiments | Experimental | Research/Open | Low-Medium | Medium | Low | Low-Mod (GPU) | Research Only | **EXPERIMENT** |
| 9 | **Vibe-Trading** | AI Research | Automated hypothesis drafting & quant markdown reporting | Experimental | Open Source | Active | Medium | Low | N/A | Research Only | **USE AS REFERENCE / AI TOOL** |
| 10 | **Alpha-Lake** | Data Integrity | Bi-temporal point-in-time modeling & anti-leakage concepts | Emerging | Concepts/OSS | Active | Low | Low | High | High | **ADOPT PRINCIPLES (Custom)** |
| 11 | **Parquet + DuckDB**| Data Storage | Local columnar storage & efficient embedded analytical queries | Very High | MIT / Apache-2 | Very Active | Low | Very Low | High | Perfect | **ADOPT (Local Analytical Standard)** |
| 12 | **PostgreSQL** | Control Plane DB | Transactional persistence, concurrent writers, account state | Very High | PostgreSQL | Very Active | Medium | Low | High | Future Need | **DEFER (Reconsider if needed)** |
| 13 | **MetaTrader 5 (MT5)**| Broker Gateway | Retail FX / CFD / Futures execution interface on Windows | High (Prod) | Proprietary | Vendor (MQ) | Medium | Low (via Adapter) | High (IPC) | Adapter Only | **ADAPT (Initial Execution Adapter)** |
| 14 | **yfinance** | Market Data (Research)| Research data adapter without paid subscription requirement | High | Apache-2.0 | Active | Low | Very Low | Moderate | Research Only | **ADAPT (Research Data Adapter)** |
| 15 | **PyPortfolioOpt** | Portfolio Optimization | Classical Markowitz Mean-Variance, Black-Litterman, Basic HRP | High | MIT | Low-Medium | Low | Low | Moderate | Redundant to skfolio | **REJECT (Redundant)** |
| 16 | **Plotly** | Visualization | Interactive charting, equity curves, drawdown & tear sheets | High | MIT | Very Active | Low | Very Low | High | High | **ADOPT (Research Visualization)** |
| 17 | **C++ / Rust / Python**| Implementation Lang | Performance vs Development Velocity vs Correctness | N/A | Open | N/A | High (C++/Rust) | Medium | Ultra-High | Python-First | **PYTHON-FIRST + CONDITIONAL RUST** |

---

## 3. Deep-Dive Evaluations & Corrected Findings

### 3.1 skfolio & Transparent Baseline Mandate
- **Role:** Portfolio optimization and risk-allocation methods including HRP, ERC, and CVaR-based approaches, Scikit-Learn pipeline integration, and combinatorial cross-validation.
- **Evaluation Principle:** **skfolio must be evaluated for statistically significant incremental value versus transparent baselines out-of-sample.**
- **Required Baselines:**
  - Equal Weight ($1/N$)
  - Inverse Volatility ($1/\sigma$)
  - Cash / No-trade ($w_{\text{cash}} = 1.0$) where applicable
- **Sovereign Rule:** The system does **NOT** force skfolio to win. If a simple baseline is more robust out-of-sample, ACASH selects the baseline. The optimizer is never optimized merely to beat the benchmark.
- **Final Decision:** **ADOPT (behind `IPortfolioOptimizer` interface, gated against baselines)**.

### 3.2 yfinance (Research Data Adapter)
- **Role & Definition:** **Research-oriented market and fundamental data adapter with no paid subscription requirement for the intended research use case, subject to source availability, API limitations, and applicable terms.**
- **Boundaries:** Kept strictly isolated behind `IMarketDataProvider`. Prohibited from use as the production execution or institutional real-time data backbone.
- **Final Decision:** **ADAPT (Research Data Adapter Only)**.

### 3.3 NautilusTrader (Tier-2 Event Simulation & Future Execution Candidate)
- **Role & Definition:** **ADAPT — Tier-2 event-driven simulation and future execution candidate.**
- **PoC Requirement:** NautilusTrader must pass a dedicated Phase 5 Proof of Concept (PoC) before ACASH commits to it as a production live execution substrate.
- **Decoupled Architecture:**
  $$\text{ACASH Interfaces} \to \text{Nautilus Adapter} \to \text{NautilusTrader}$$
  If the PoC fails required acceptance criteria, ACASH retains full sovereign autonomy to replace the adapter without changing sovereign domain models.
- **Final Decision:** **ADAPT (Tier-2 Sim & Future Exec Candidate via PoC Gate)**.

### 3.4 Storage: Parquet + DuckDB (Analytical) vs SQLite (V1 Transactional) vs PostgreSQL (Deferred)
- **Analytical Layer (Adopted):** Local partitioned Parquet files queried via embedded **DuckDB**. DuckDB provides an efficient embedded analytical query engine for ACASH's local research workload.
- **Operational Layer (Adopted for V1):** Local **SQLite** for transactional operational state, order state machines, and execution ledger persistence.
- **Enterprise Control Plane (Deferred):** **PostgreSQL is DEFERRED** (not permanently rejected). It will be reconsidered later if ACASH develops explicit requirements for transactional workloads, concurrent writers, durable operational control-plane state, or multi-process execution persistence.
- **Final Decision:** **ADOPT Parquet + DuckDB for analytical research, ADOPT SQLite for V1 transactional state; DEFER PostgreSQL**.

### 3.5 Language & Performance: Python-First + Conditional Native Layer
- **Architecture:** Python owns 100% of the sovereign domain logic, research workflows, portfolio orchestration, and risk control. Vectorized operations leverage NumPy/Polars/Numba. High-throughput event simulation leverages NautilusTrader's pre-compiled Rust core where applicable. Custom C++ or standalone Rust will only be introduced if measured profiling identifies a genuine, verified bottleneck.
- **Final Decision:** **PYTHON-FIRST CORE; CONDITIONAL RUST VIA NAUTILUS ADAPTER; REJECT CUSTOM C++ FOR V1**.
