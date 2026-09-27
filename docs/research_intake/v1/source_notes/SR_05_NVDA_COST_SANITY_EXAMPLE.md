# SR-05 — NVDA Cost Sanity Example

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Quantitative backtest demonstration / satirical educational case study.
- **Demonstration Setup**:
  - Single-stock strategy trading NVIDIA (NVDA) based on daily price change signals.
  - Strategy maintains long and short exposure with ~10% capital exposure per trade.
- **Initial "Fictional Zero-Cost" Headline Claims**:
  - Initial Capital: $100k
  - Claimed Terminal Wealth: >$28m
  - Annualized Return: 75% annualized (~75% annualized)
  - Volatility: 3.53% volatility (~3.53% volatility)
  - Maximum Drawdown: Minimal (max around 4)
  - Claimed Sharpe Ratio: Sharpe >16
  - Assumed Execution Cost: Exactly 0.0%.
- **The Realistic-World Collapse**:
  - When the creator enables realistic execution friction, commissions, bid/ask spread, and short borrow costs:
  - Annualized Return collapses to 7% (~7%).
  - Sharpe Ratio collapses to Sharpe 0.16 (~0.16).
  - Execution costs consume execution >6% (>6% annualized).

## 2. Human-Reviewed Scientific Critique
- **Educational Function**: This case serves as a perfect demonstration of the extreme sensitivity of high-turnover trading models to execution frictions.
- **Methodological Takeaway**: Any backtest that ignores bid/ask spread crossing, commissions, borrow fees, and slippage produces complete mathematical fiction. Gross Sharpe >16 is an immediate indicator of missing friction accounting, collapsing to Sharpe 0.16 with execution >6%.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - Directly maps to [METHODOLOGY_CONTROLS.md](file:///docs/research_intake/v1/METHODOLOGY_CONTROLS.md) (Complete Cost Accounting standard).
- **Trial Status**: Preserved as a methodology sanity benchmark.
