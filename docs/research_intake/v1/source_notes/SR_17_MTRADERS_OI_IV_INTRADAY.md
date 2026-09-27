# SR-17 — MTraders OI / IV Intraday

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Proprietary day-trading stream / options-based market profiling method.
- **Reported Concepts & Price Zone Heuristics**:
  - Integrates option Open Interest (OI), Implied Volatility (IV), and market opening price action.
  - Constructs stylized price zones in S&P index points: e.g., 4325, 4350, 4375, 4400, 4450.
  - Asserts that market prices spend ~70% (70%) of time centered around median balance zones.
  - Uses a 1-standard-deviation (1 SD) "abnormal price" concept to identify overextended levels.
  - Trades below or above key zones are interpreted as mean-reversion setups or breakout continuations toward targets: 4325, 4300, 4250.
  - Thesis of natural price movement: price moves in discrete 25-point blocks (25-point block) between strikes.
  - IV Interpretation: Mentions annualized IV 24 (IV approximately 24), calculating daily movement as 1.51% (roughly ~1.51% daily movement via 24% / sqrt(252)).
  - Specific Probability Claims:
    - Claims market open retest/rebound probability is approximately 65% (65%).
    - Claims selling or fading at the 1 SD zone boundary offers a 65–75% (65-75%) edge.
  - Market Maker Narrative: Explains moves via dealer delta neutral (delta-neutral) hedging and options pricing dynamics.
  - scale/grid Entries: Advocates adding contracts ("repairing" trades via scale/grid) if price pushes beyond the initial zone.
  - Stop Placement: Recommends stop loss 5–10 points beyond the outer zone boundary.

## 2. Human-Reviewed Scientific Critique
- **OI != GEX Distinction**: Open Interest is a static count of open contracts; OI != GEX. Open interest does NOT equal Gamma Exposure (GEX) or directional intent. Every contract has a buyer and a seller.
- **official vs estimated OI**: Official CME/OCC open interest is published once daily after overnight clearing; real-time "intraday OI" is an unverified model estimate (official vs estimated OI distinction must be maintained).
- **dealer sign & 0DTE**: Public OI does not reveal dealer sign. With heavy 0DTE volume, intraday positioning shifts rapidly.
- **IV Mathematics vs. Reversal Probability**:
  - While IV 24 gives 24% / sqrt(252) ≈ 1.51% as a valid first-order daily volatility approximation, a 1 SD boundary does NOT imply a 65–75% reversal probability.
  - risk-neutral option-implied distributions do NOT equal real-world physical probability (risk-neutral vs physical probability).
- **Unverified Numbers**: Claims of 65% open retest, 65–75% boundary reversal, 70% zone centering, and 25-point block travel are purely `EXTERNAL_UNVERIFIED_CLAIM`.
- **Martingale / Grid Hazard**: "Repairing" trades via unbudgeted scale/grid averaging is an unhedged martingale technique strictly prohibited in ACASH. Any staged entry must be a predetermined staged entry with total fixed risk.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-05`: Dealer Gamma / GEX Regime (OI != GEX, official vs estimated OI, dealer sign, 0DTE).
  - `RI-06`: Option Open Interest Changes.
  - `RI-07`: Intraday Option Flow.
  - `RI-08`: IV / Expected-Move Regime (IV 24, 1.51%, risk-neutral, physical probability).
  - `RI-11`: Mean Reversion / Overreaction (scale/grid, predetermined staged entry).
- **Trial Status**: Preserved as catalogued retail options heuristics.
