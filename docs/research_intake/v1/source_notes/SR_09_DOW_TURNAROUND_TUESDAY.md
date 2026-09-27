# SR-09 — Dow Turnaround Tuesday

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Retail algorithmic trading course / anomaly presentation.
- **Reported Performance Claims (Turnaround Tuesday)**:
  - Win Rate: 57.5%
  - Profit Factor: PF 1.49
  - Maximum Drawdown: MDD 8.09%
- **Exact Strategy Recipe**:
  - Day / Time: Monday at 01:05 broker time.
  - Chart Inspection: Daily chart of Dow Jones Industrial Average (DJI / YM).
  - Filter: Check if price is below the 25-day Simple Moving Average (SMA25 / SMA 25).
  - Entry: If below 25-day SMA -> Buy long.
  - Holding Horizon: Hold position through Monday and Tuesday.
  - Exit: Close trade on Tuesday at 23:50 broker time.
  - Direction: Long only.
  - Stops / Targets: No Stop Loss (no SL), No Take Profit (no TP).
  - Narrative: Early-week weakness tends to reverse into institutional midweek recovery (Turnaround Tuesday).

## 2. Human-Reviewed Scientific Critique
- **External Unverified Claim**: Metrics (57.5%, PF 1.49, MDD 8.09%) are unverified retail backtest claims.
- **Arbitrary Heuristics**: The combination of Monday entry below SMA25 and Tuesday exit is a hyper-specific parameter combination exhibiting classic symptoms of historical snooping.
- **Decay of Calendar Anomalies**: While the weekend/turnaround effect has historical academic roots (French 1980), modern electronic trading has largely compressed and shifted weekday returns.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-12`: Calendar / Weekday Seasonality.
- **Trial Status**: Preserved as historical recipe. Prohibited from empirical adoption without multi-decade out-of-sample validation.
