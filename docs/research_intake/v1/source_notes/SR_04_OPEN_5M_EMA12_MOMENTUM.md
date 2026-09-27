# SR-04 — Open 5m EMA12 Momentum

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Algorithmic trading video / strategy backtest showcase.
- **Reported Strategy Rules**:
  - Evaluate the first 5-minute candle at the New York open (09:30–09:35 America/New_York).
  - If the candle closes above the 12-period Exponential Moving Average (EMA 12) -> Enter Long.
  - If the candle closes below the 12-period EMA (EMA 12) -> Enter Short.
  - Stop loss is placed immediately after entry at candle extreme.
  - Trailing stop is applied to let trends run.
- **Claimed Backtest Metrics (NASDAQ 2019–2026)**:
  - Total Trades: 1,448 trades
  - Claimed Return: 982%
  - Claimed Win Rate: 57%
  - Claimed Profit Factor (PF): PF 1.29
  - Claimed Max Drawdown (MDD): <20%

## 2. Human-Reviewed Scientific Critique
- **External Unverified Claim**: All performance metrics (982% return, 1,448 trades, 57% win rate, PF 1.29, MDD <20%) are `EXTERNAL_UNVERIFIED_CLAIM`.
- **Severe Unreported Methodological Gaps**:
  - Exact underlying instrument is unspecified (CFD, cash index, NQ futures, or QQQ ETF).
  - Leverage, position sizing, and margin interest are undocumented.
  - Execution costs, bid/ask spread crossing, and commissions are omitted or unrealistically low.
  - Same-bar fill ambiguity on stop-loss and trailing-stop exits is unresolved.
  - Number of historical lookback variations tested prior to reporting EMA 12 is undisclosed (data-snooping bias).

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-01`: Opening-State / Intraday Momentum.
  - `RI-09`: Time-Series Momentum / Trend (Baseline Control).
  - `RI-15`: EMA / Chart / Candlestick Features.
- **Trial Status**: Catalogued external claim. Frozen out of all ACASH empirical execution.
