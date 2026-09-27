# Source-to-Mechanism Traceability Matrix

## 1. Overview & Lineage Mapping

This document provides the authoritative many-to-many traceability mapping connecting external, unverified source notes (`SR-01` through `SR-19`) to human-reviewed research mechanisms (`RI-01` through `RI-15`) and overarching methodology controls.

### Structural Mapping Table

| Source Note (`SR-xx`) | Source Document Title | Mapped Mechanisms (`RI-xx`) | Core Methodology Mapping |
| :--- | :--- | :--- | :--- |
| **SR-01** | 9:30 Breakout and FVG | `RI-01`, `RI-02`, `RI-14` | Bar-path ambiguity, fixed RR overclaim |
| **SR-02** | Whale Pivot / Footprint | `RI-03`, `RI-04` | Normalization, heuristic threshold (>400) |
| **SR-03** | Tradefather Discretionary Toolkit | `RI-01`, `RI-09`, `RI-15` | Discretionary bias, subjective definitions |
| **SR-04** | Open 5m EMA12 Momentum | `RI-01`, `RI-09`, `RI-15` | External claim unverified, lookback snooping |
| **SR-05** | NVDA Cost Sanity Example | *Methodology Control Only* | Execution friction impact, gross vs. net |
| **SR-06** | Ninja GEX A+ Checklist | `RI-05`, `RI-10`, `RI-15` | GEX estimation, subjective patterns, volume |
| **SR-07** | Nasdaq Opening Range Breakout | `RI-01`, `RI-02` | Unverified social recipe, matched controls |
| **SR-08** | Nasdaq Daily Long Bias | `RI-09` (Baseline Control) | Equity drift vs. alpha, timezone mapping |
| **SR-09** | Dow Turnaround Tuesday | `RI-12` | Calendar anomaly, sample stability |
| **SR-10** | USDJPY Morning Range Breakout | `RI-01`, `RI-02` (FX Context) | OTC FX session mapping, spread friction |
| **SR-11** | AI Trading / Variation Search | *Methodology Control Only* | Multiple testing ($K$), trial ledger, snooping |
| **SR-12** | Volume Spike Breakout | `RI-10` | Degree-of-freedom penalty, volume semantics |
| **SR-13** | 121 New York Window Sweep | `RI-01` (Incomplete Specification) | Incomplete source preservation, regime shift |
| **SR-14** | Macro & Strategy Families | `RI-09`, `RI-11`, `RI-12`, `RI-13` | Regime variables vs. direct trade rules |
| **SR-15** | Backtesting Principles | *Methodology Control Only* | 100 trades fallacy, bar path, cost list |
| **SR-16** | Probability / LLN / Casino | *Methodology Control Only* | Weak vs. Strong Law, casino vs. market math |
| **SR-17** | MTraders OI / IV Intraday | `RI-05`, `RI-06`, `RI-07`, `RI-08`, `RI-11` | OI vs. GEX, risk-neutral vs. physical prob |
| **SR-18** | Derivatives Pricing / Calibration | `RI-05`, `RI-08` | Risk-neutral models vs. directional alpha |
| **SR-19** | AI / Prop / Random Control Findings | `RI-01`, `RI-10`, *Methodology Controls* | Random control utility, multiple testing |

---

## 2. Epistemological Rationale: Many-to-Many Mapping

In quantitative finance, external source materials rarely isolate single theoretical mechanisms:
1. **Multiple Source Ideas Inform One Mechanism**: For example, `RI-01` (Opening-State Momentum) receives motivation from `SR-01` (9:30 open rules), `SR-03` (session open focus), `SR-04` (first 5m candle), `SR-07` (Nasdaq ORB), and `SR-19` (NY AM open performance). Each source provides a distinct anecdotal observation of the same underlying market-microstructure opening phenomenon.
2. **Single Sources Combine Multiple Mechanisms**: Conversely, `SR-06` combines dealer gamma (`RI-05`), volume acceleration (`RI-10`), and candlestick pattern confirmation (`RI-15`) into a single discretionary checklist.

### Important Trial Ledger Note
This mapping documents conceptual motivation only. Mapping a source note to a mechanism does **NOT** increment the empirical trial count $K$ at R0, because **zero empirical backtests or parameter sweeps are authorized**.
