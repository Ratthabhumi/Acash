# MEC-0015: Evidence Matrix & Lineage Ledger

This document tracks all external literature claims, independent replication findings, and ACASH-internal verification states for the **MEC-0015** profitability-first research candidate.

## Evidence Status Legend
- `LITERATURE_CLAIM`: Reported by the primary authors in published or working papers. Not independently audited by ACASH.
- `INDEPENDENT_REPLICATION_CLAIM`: Reported by third-party external replications. Not independently audited by ACASH.
- `ACASH_OPEN`: A critical technical, data, or mathematical dependency that must be resolved prior to empirical execution.
- `ACASH_RESOLVED`: Formally audited, implemented, and verified within the ACASH codebase.

---

## Evidence Matrix

| Claim ID | Claim Description | Source | Source Type | Evidence Status | Literature Explicit? | Independent Replication? | ACASH Verified? | Required Before HYP_005? | Notes |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **CLM-001** | Trailing 14-day same-time-of-day move magnitude quantifies intraday Noise Area on SPY | Zarattini, Aziz, Barbon (2024) | Academic Paper (SSRN 4824172) | `LITERATURE_CLAIM` | Yes | Yes (Sheimy 2024) | No | Yes | Defines baseline volatility envelope. |
| **CLM-002** | Adjusting boundaries using overnight gap ($\max/\min$ of open and prior close) improves band fit | Zarattini, Aziz, Barbon (2024) | Academic Paper (SSRN 4824172) | `LITERATURE_CLAIM` | Yes | Yes | No | Yes | Anchors noise bands to gap direction. |
| **CLM-003** | Semi-hourly trading decisions (10:00 to 15:30) prevent over-trading in 1-min noise | Zarattini, Aziz, Barbon (2024) | Academic Paper (SSRN 4824172) | `LITERATURE_CLAIM` | Yes | Yes | No | Yes | Enforces 30-minute discrete epoch constraint. |
| **CLM-004** | Combining Noise Area boundary with session VWAP forms effective trailing stop | Zarattini, Aziz, Barbon (2024) | Academic Paper (SSRN 4824172) | `LITERATURE_CLAIM` | Yes | Yes | No | Yes | Core risk control and exit trigger. |
| **CLM-005** | Forced flat exit at 16:00 eliminates overnight gap exposure | Zarattini, Aziz, Barbon (2024) | Academic Paper (SSRN 4824172) | `LITERATURE_CLAIM` | Yes | Yes | No | Yes | Pure intraday holding period constraint. |
| **CLM-006** | 2% daily volatility targeting with 4× leverage cap achieves 19.6% CAGR, 1.33 Sharpe (2007–2024) | Zarattini, Aziz, Barbon (2024) | Academic Paper (SSRN 4824172) | `LITERATURE_CLAIM` | Yes | Yes | No | No (Eval only) | Claimed historical performance under reported friction. |
| **CLM-007** | Historical in-sample performance is independently replicable (Sharpe ≈ 1.34) | Paz Sheimy (2024–2026) | Public GitHub Replication | `INDEPENDENT_REPLICATION_CLAIM` | N/A | Yes | No | No (Context) | Corroborates code/logic validity of original paper. |
| **CLM-008** | Out-of-sample performance decayed significantly in May 2024–March 2026 (Sharpe ≈ 0.39) | Paz Sheimy (2024–2026) | Public GitHub Replication | `INDEPENDENT_REPLICATION_CLAIM` | N/A | Yes | No | Yes (Risk) | Core motivation for strict OOS failure criteria. |
| **CLM-009** | Edge compression observed on both SPY ETF and ES futures around 2025–2026 | Independent Replication B (2026) | External Audit | `INDEPENDENT_REPLICATION_CLAIM` | N/A | Yes | No | Yes (Risk) | Indicates systematic degradation across index wrappers. |
| **CLM-010** | Post-publication parameter optimization (e.g. Maróy 2025) fails to generalize OOS | Replication B / Maróy Review (2025) | Literature Analysis | `INDEPENDENT_REPLICATION_CLAIM` | No | Yes | No | Yes (Rule) | Mandates baseline $K=1$ ex-ante parameter freeze. |
| **REQ-001** | Exact execution price semantics for 30-min decision epoch (Close vs Next Open vs Quote) | ACASH Architecture Team | Data Contract | `ACASH_OPEN` | Ambiguous | Variable | No | Yes | Must be mathematically and operationally frozen. |
| **REQ-002** | Exact session VWAP numerator convention (Close vs Typical $(H+L+C)/3$ vs Tick) | ACASH Architecture Team | Data Contract | `ACASH_OPEN` | Ambiguous | Variable | No | Yes | Provider differences cause significant divergence. |
| **REQ-003** | ACASH conservative friction model (commissions + bid-ask spread + SEC/TAF + slippage) | ACASH Governance | Risk Contract | `ACASH_OPEN` | Exceeds Paper | Exceeds Paper | No | Yes | Literature model ($0.0035 + $0.001) is insufficient. |
| **REQ-004** | Short-selling borrow availability, locate fees, and margin constraints for SPY | ACASH Execution Engine | Broker Contract | `ACASH_OPEN` | No | Variable | No | Yes | Assumes frictionless shorting; real borrow required. |
| **REQ-005** | Early-close session policy (exclusion vs. truncated 13:00 timeline) | ACASH Data Governance | Calendar Policy | `ACASH_OPEN` | Silent | Variable | No | Yes | Explicit rule needed for Thanksgiving/Christmas Eves. |
| **REQ-006** | Historical sample partitioning policy accounting for 2017–2026 publication exposure | ACASH Governance | Data Authority | `ACASH_OPEN` | N/A | N/A | No | Yes | Pristine holdout design is structurally complicated. |
| **REQ-007** | Economic qualification hurdles (Net Sharpe, Net Return, Max DD, Cost-Stress Ratio) | ACASH Research Council | Strategy Gate | `ACASH_OPEN` | N/A | N/A | No | Yes | Must replace simple statistical $p$-value tests. |
