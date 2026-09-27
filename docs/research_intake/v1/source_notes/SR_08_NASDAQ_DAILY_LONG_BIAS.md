# SR-08 — Nasdaq Daily Long Bias

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Algorithmic retail trading presentation.
- **Reported Performance Claims (NASDAQ daily long)**:
  - Win Rate: 57.7%
  - Profit Factor: PF 1.24
  - Maximum Drawdown: MDD 6.19%
- **Exact Strategy Rules**:
  - Action: Buy every trading day at 01:05 broker time (01:05).
  - Exit: Close position at 23:50 broker time (23:50).
  - Stops / Targets: Zero Stop Loss (no SL), Zero Take Profit (no TP).
  - Filters: Completely unfiltered daily buy.
  - Creator Narrative: Intended to avoid most overnight financing/swap fees while capturing the equity index upward drift.

## 2. Human-Reviewed Scientific Critique
- **Beta Confusion**: This is an unconditional long market exposure that captures equity risk premium (market beta), NOT timing alpha.
- **Ambiguous Broker Time**: 01:05 and 23:50 broker time are non-canonical, vendor-specific timestamps that fail to account for exchange session boundaries or DST shifts.
- **Instrument Ambiguity**: Unspecified whether tested on cash index, CFD, futures (NQ/MNQ), or ETF (QQQ).
- **Tail Risk Hazard**: Trading long with zero stop loss exposes capital to catastrophic gap risk and intraday market crashes.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-09`: Time-Series Momentum / Trend (as a BASELINE_CONTROL).
  - Maps to [METHODOLOGY_CONTROLS.md](file:///docs/research_intake/v1/METHODOLOGY_CONTROLS.md) (Beta / Baseline Drift standard).
- **Trial Status**: Preserved strictly as an equity drift baseline comparator.
