# SR-18 — Derivatives Pricing / Calibration

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Quant finance practitioner interview / podcast discussion.
- **Preserved Themes**:
  - Discusses quantitative algorithmic trading development using Python.
  - Examines exotic derivatives pricing, risk-neutral valuation (risk-neutral), and numerical PDE solvers.
  - Reflects on the challenges of quantitative research, noting that practitioner understanding of model calibration was historically incomplete.
  - Discusses volatility-surface calibration, local volatility models, and volatility surface extrapolation beyond observed strikes.

## 2. Human-Reviewed Scientific Critique
- **Pricing vs. Forecasting Distinction**: Risk-neutral derivatives pricing and volatility surface calibration are mathematically rigorous tools for pricing contingent claims and hedging inventory; they do NOT automatically produce directional alpha in underlying assets.
- **Current ACASH Relevance**: Exotic derivatives pricing is completely outside CORE-001 scope. Relevant strictly as background context for potential future options and GEX regime research.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-05`: Dealer Gamma / GEX Regime.
  - `RI-08`: IV / Expected-Move Regime.
- **Trial Status**: Preserved as practitioner background context.
