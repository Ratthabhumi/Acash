# SR-10 — USDJPY Morning Range Breakout

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Foreign exchange trading tutorial / retail breakout system.
- **Reported Performance Claims (USDJPY)**:
  - Win Rate: 43.6%
  - Profit Factor: PF 1.16
  - Maximum Drawdown: MDD 14.54%
- **Exact Strategy Recipe**:
  - Range Definition: Form a price range between 03:00–06:00 (03:00 to 06:00) broker time (GMT+2/GMT+3 in summer).
  - Order Placement: At 06:00 broker time, place:
    - Buy Stop order at range high.
    - Sell Stop order at range low.
    - Stop Loss for each order placed at opposite side of the range.
    - Take Profit: No fixed Take Profit (no TP).
  - Trade Management:
    - Maximum one trade per day.
    - When one stop order fills, cancel the opposing order (OCO).
    - At 18:00 broker time, close any open position and cancel all pending orders.
  - Risk: Fixed percentage risk per trade.

## 2. Human-Reviewed Scientific Critique
- **Lack of Centralized Open**: Unlike equity markets, spot FX trades 24 hours OTC without a centralized 09:30 open. Session definitions depend heavily on interbank liquidity shifts (Tokyo, London, NY).
- **Broker Time Dependency**: Defining ranges in GMT+2/GMT+3 broker time creates severe alignment issues across US and European DST transition weeks.
- **Spread & Slippage Vulnerability**: Breakout orders in FX frequently suffer execution slippage, particularly during low-liquidity Tokyo afternoon sessions.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-01`: Opening-State / Intraday Momentum (FX session context).
  - `RI-02`: Opening Range Breakout (ORB).
- **Trial Status**: Preserved as an OTC currency breakout recipe.
