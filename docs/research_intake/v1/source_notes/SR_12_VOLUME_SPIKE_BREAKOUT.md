# SR-12 — Volume Spike Breakout

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Proprietary breakout strategy guide / automated strategy report.
- **Exact Strategy Recipe (Volume spike)**:
  - Signal Condition: Traded volume reaches many times the average volume and bar closes beyond the recent high or low.
  - Specific Parameter Family:
    - Volume Multiplier: 2.5 (vol_mult = 2.5)
    - Volume Lookback: 50 (vol_n = 50)
    - Breakout Extremum Lookback: k=10 (k = 10)
  - Direction: Both long and short.
  - Order Entry: 50% retracement limit order placed after the breakout bar; cancel if not filled within 10 bars.
  - Stop Loss: 1 * ATR(14) (ATR14).
  - Profit Target: 1 * ATR(14) (ATR14).
  - Permitted Session Window: 12:00–16:00 ET (12:00–16:00, afternoon session).
  - Daily Exit: Flat by 15:59 ET (15:59).
  - Maximum Trades: 2 trades/day (2 trades per day).
  - Day-of-Week Filters: Skip Wednesday, skip Friday (Wednesday, Friday).
- **Reported Family Performance Claims**:
  - One version described as the highest-profit candidate despite a very low win rate of ~7–14%, relying on large payoff asymmetry.
  - Creator notes this low win rate makes it a poor fit for prop-firm consistency rules.
  - Another high-pass variant reportedly yielded only ~27 trades over 7 years.

## 2. Human-Reviewed Scientific Critique
- **Extreme Parameter Overfitting**: The recipe combines 11 distinct degrees of freedom (multiplier 2.5, lookback 50, k=10, 50% retracement limit, 10 bars cancel, ATR14, 12:00–16:00 window, 15:59 flat, 2 trades/day, skipping Wednesday and Friday). This is a textbook example of in-sample curve fitting.
- **Intrabar Ambiguity**: Symmetrical 1 ATR stop and 1 ATR target introduces severe same-bar outcome ambiguity if evaluated on coarse bars.
- **Data Semantic Pitfall**: CFD tick volume behaves completely differently from CME futures volume or consolidated equity volume.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-10`: Volume-Spike Breakout.
- **Trial Status**: Preserved as an overfitted external recipe. Zero parameters preregistered.
