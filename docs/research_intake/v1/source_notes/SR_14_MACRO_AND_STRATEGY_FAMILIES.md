# SR-14 — Macro and Strategy Families

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Quantitative finance overview / macro strategy taxonomy lecture.
- **Preserved Macro / Regime Variables (Macro list)**:
  - Cboe Volatility Index (VIX)
  - Crude Oil Benchmarks (WTI, Brent)
  - Manufacturing / Services Purchasing Managers' Index (PMI)
  - High Yield Credit Spreads (HY spreads)
  - Equity Benchmarks (S&P 500, NASDAQ)
  - Consumer Price Index (CPI)
  - US 10-Year Treasury Yield (10Y Treasury)
  - US Dollar Index (DXY)
  - Baltic Dry Index (BDI)
- **Preserved Quantitative Strategy Families**:
  - Seasonality & Calendar-based trading
  - Mean reversion & statistical arbitrage
  - Trend following & momentum breakout
  - Relative value & spread trading

## 2. Human-Reviewed Scientific Critique
- **Context vs. Signals**: Macroeconomic indicators (VIX, WTI, Brent, PMI, HY spreads, S&P 500, NASDAQ, CPI, 10Y Treasury, DXY, BDI) represent state/regime variables, NOT direct trade execution signals.
- **Family Validity != Alpha**: Categorizing a strategy into a legitimate quantitative family (e.g., trend following or stat-arb) provides conceptual grounding, but does not guarantee tradeable profitability after costs.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-09`: Time-Series Momentum / Trend.
  - `RI-11`: Mean Reversion / Overreaction.
  - `RI-12`: Calendar / Weekday Seasonality.
  - `RI-13`: Relative-Value / Pairs Stat-Arb.
- **Trial Status**: Preserved as a structural taxonomy of quantitative regimes.
