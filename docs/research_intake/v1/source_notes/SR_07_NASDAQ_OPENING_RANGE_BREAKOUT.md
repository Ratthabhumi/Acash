# SR-07 — Nasdaq Opening Range Breakout

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Quantitative trading blog / retail strategy report.
- **Reported Performance Claims (NASDAQ ORB)**:
  - Win Rate: 49.0%
  - Profit Factor (PF): PF 1.10
  - Maximum Drawdown (MDD): MDD 24.61%
- **Exact Strategy Recipe**:
  - Time Window: 09:30–09:45 New York opening range (first 15 minutes of regular trading hours).
  - Trading Window: 09:45–15:00 America/New_York.
  - Entry Trigger:
    - 5-minute bar close above 09:30–09:45 high -> Buy.
    - 5-minute bar close below 09:30–09:45 low -> Sell.
  - Trade Frequency: Strictly one trade per day.
  - Stop Loss: Placed on opposite side of opening range + 0.25 ATR (0.25 * ATR(14)).
  - Profit Target: Placed at 2x range height from the breakout point.
  - Risk Budget: 1% account risk per trade.
  - Session Close: Flat by 15:55 New York time (15:55 flat, no overnight exposure).

## 2. Human-Reviewed Scientific Critique
- **External Unverified Claim**: All performance metrics (49.0%, PF 1.10, MDD 24.61%) are unverified retail vendor claims.
- **Target vs. Realized R:R**: A theoretical 2x range target does NOT guarantee a realized 2:1 profit factor. Slippage on stop entries and wide opening spreads degrade performance.
- **Degree of Overfitting**: Testing specific combinations of 09:30–09:45 range, 0.25 ATR buffer, and 15:55 exit represents severe data mining without multi-testing corrections.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-01`: Opening-State / Intraday Momentum.
  - `RI-02`: Opening Range Breakout (ORB).
- **Trial Status**: Preserved as external recipe. Required negative control: matched-volatility midday breakout.
