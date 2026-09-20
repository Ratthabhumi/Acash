# MEC-0015: Evidence Matrix & Lineage Ledger

This document tracks all external literature claims, author reference implementations, independent replication findings, and ACASH-internal verification states for the **MEC-0015** profitability-first research candidate.

## Evidence Status Legend
- `LITERATURE_CLAIM`: Reported by the primary authors in published or working papers.
- `AUTHOR_REFERENCE_IMPLEMENTATION`: Verified in author-published Concretum MATLAB/Python reference code.
- `INDEPENDENT_REPLICATION_CLAIM`: Reported by third-party external replications (Delgado 2026, Paz Sheimy 2024–2026).
- `ACASH_RESOLVED`: Formally audited, contractually frozen, and verified within ACASH research documentation.
- `ACASH_OPEN`: A critical technical, data, or mathematical dependency that remains open and blocks hypothesis registration.

---

## Evidence Matrix

| Claim / Requirement ID | Description | Source / Authority | Source Type | Evidence Status | Literature / Code Explicit? | Independent Replication? | ACASH Verified? | Required Before HYP_005? | Notes |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **CLM-001** | Trailing 14-day same-time-of-day move magnitude quantifies intraday Noise Area on SPY | Zarattini, Aziz, Barbon (2024, rev 2025) | Academic Paper (SSRN 4824172) | `ACASH_RESOLVED` | Yes | Yes (Sheimy, Delgado) | Yes | Yes | Frozen: 14 prior completed sessions (`shift(1)`). |
| **CLM-002** | Adjusting boundaries using overnight gap ($\max/\min$ of open and prior close) anchors bands | Zarattini, Aziz, Barbon (2024) / Concretum | Paper & Author Code | `ACASH_RESOLVED` | Yes | Yes | Yes | Yes | Gap anchor adjusted for cash dividend (`prev_close - div`). |
| **CLM-003** | Semi-hourly trading decisions (10:00 to 15:30 ET) evaluate entries and exits | Zarattini, Aziz, Barbon (2024) / Concretum | Paper & Author Code | `ACASH_RESOLVED` | Yes | Yes | Yes | Yes | Enforces 30-min discrete epoch (`min_from_open % 30 == 0`). |
| **CLM-004** | Entry requires joint confirmation of Noise Band breach AND session VWAP | Concretum Reference Code / Delgado (2026) | Author Code & Replication | `ACASH_RESOLVED` | Yes (Code) | Yes (Delgado 2026) | Yes | Yes | Long: Close > Band & Close > VWAP. Corrects intake. |
| **CLM-005** | Session VWAP uses Typical Price $(H+L+C)/3$, cumulative regular session (09:30–16:00 ET) | Concretum Reference Implementation | Author Code | `ACASH_RESOLVED` | Yes (Code) | Yes (Delgado 2026) | Yes | Yes | Rejects close-only and tick SIP VWAP for baseline. |
| **CLM-006** | Signal exposure is lagged by 1 minute; P&L accrues starting minute $t+1$ | Concretum Reference Implementation | Author Code | `ACASH_RESOLVED` | Yes (Code) | Yes | Yes | Yes | `position = signal.shift(1)`. Not same-bar close execution. |
| **CLM-007** | Forced flat exit at 16:00 ET eliminates overnight inventory | Zarattini, Aziz, Barbon (2024) / Concretum | Paper & Author Code | `ACASH_RESOLVED` | Yes | Yes | Yes | Yes | Zero overnight holding constraint. |
| **CLM-008** | Dynamic sizing targeting 2% daily vol with 4× leverage cap, integer share rounding | Concretum Reference Implementation | Author Code | `ACASH_RESOLVED` | Yes (Code) | Yes | Yes | Yes | Sizing price = Session Open; AUM = prior day ending. |
| **CLM-009** | Literature commission is $\max(\$0.35, \$0.0035 \times \text{shares})$ per order side | Concretum Reference Implementation | Author Code | `ACASH_RESOLVED` | Yes (Code) | Yes | Yes | Yes | Author reference model includes minimum ticket charge. |
| **CLM-010** | Standalone $\$0.001$/share slippage is paper-reported approximation, not in author code | Zarattini et al. (Paper text vs Code) | Audit Comparison | `ACASH_RESOLVED` | Text only | Variable | Yes | Yes | Decoupled: `PAPER_REPORTED` vs `AUTHOR_CODE_APPLIED`. |
| **CLM-011** | Out-of-sample performance decayed in May 2024–March 2026 (pooled Sharpe $\approx 0.39$) | Paz Sheimy (2024–2026) | Public GitHub Replication | `INDEPENDENT_REPLICATION_CLAIM` | N/A | Yes | No | Yes (Risk) | Evidence of recent post-publication degradation. |
| **CLM-012** | Delgado (2026) shows strong OOS through Aug 2025, degradation thereafter (regime dynamics) | Delgado (2026, SSRN 7323419) | Academic Replication | `INDEPENDENT_REPLICATION_CLAIM` | N/A | Yes | No | Yes (Risk) | Material: regime deterioration vs immediate collapse. |
| **REQ-001** | ACASH real execution fill price model (Next Open vs prevailing NBBO quote) | ACASH Architecture Team | Execution Contract | `ACASH_OPEN` | Ambiguous | Variable | No | Yes | Decoupled from literature 1-min exposure lag. |
| **REQ-002** | Exact daily volatility window cardinality (14 vs 15 days) and `ddof` normalization | ACASH Research Team | Econometric Contract | `ACASH_OPEN` | Ambiguous | Variable | No | Yes | Precision blocker: code/prose discrepancy audit. |
| **REQ-003** | ACASH realistic friction model (NBBO spread + time-varying SEC/TAF + broker rates) | ACASH Governance | Risk Contract | `ACASH_OPEN` | Exceeds Paper | Exceeds Paper | No | Yes | Full spread $0.01 / half-spread $0.005. Rule 612 delayed. |
| **REQ-004** | Short-selling borrow availability, locate confirmation, and intraday fees for SPY | ACASH Execution Engine | Broker Contract | `ACASH_OPEN` | No | Variable | No | Yes | Assumes frictionless shorting; real borrow required. |
| **REQ-005** | Early-close session policy (exclusion vs truncated 13:00 schedule) | ACASH Data Governance | Calendar Policy | `ACASH_OPEN` | Silent | Variable | No | Yes | Thanksgiving / Christmas Eve protocol. |
| **REQ-006** | Historical sample partitioning policy accounting for 2017–2026 publication exposure | ACASH Governance | Data Authority | `ACASH_OPEN` | N/A | N/A | No | Yes | 2023–2026 cannot be labeled pristine holdout. |
| **REQ-007** | Economic qualification hurdles (Net Sharpe, Net Return, Max DD, Cost-Stress Ratio) | ACASH Research Council | Strategy Gate | `ACASH_OPEN` | N/A | N/A | No | Yes | Strategy-native economic acceptance gates. |
| **REQ-008** | Alpaca SIP 1-minute bar feed qualification (RTH filtering, volume completeness) | ACASH Infrastructure Team | Data Qualification | `ACASH_OPEN` | N/A | N/A | No | Yes | Zero market data access until formally qualified. |
