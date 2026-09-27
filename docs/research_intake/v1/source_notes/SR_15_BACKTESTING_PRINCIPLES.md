# SR-15 — Backtesting Principles

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Quantitative trading tutorial / backtesting methodology guide.
- **Preserved Creator Principles**:
  - Cost Accounting: Must include spread, commission, slippage, and swap (overnight swap).
  - Overfitting Safeguards:
    - Every parameter tweak and re-run matters.
    - Deleted, discarded, or unpublished strategy versions still count toward overfitting.
    - Always maintain a strictly untouched hard OOS holdout data set.
    - Test parameter perturbation around optimal values (approximately $\pm 20\%$).
  - Sample Size Rules of Thumb:
    - Fewer than 100 trades is merely an unverified hypothesis.
    - 100+ trades per year is recommended to establish statistical confidence.
    - Backtests must be split across individual years and span multiple market regimes.
  - Data Granularity:
    - OHLC bars do not reveal the intrabar price path.
    - Tick-level or finer data is necessary to model fill realism.
    - Same-bar stop-loss and take-profit ambiguity (bar-path ambiguity) is dangerous.

## 2. Human-Reviewed Scientific Critique
- **Comprehensive Cost Additions**: In addition to spread, commission, slippage, and swap, complete friction accounting requires: market impact, short borrow fees (borrow), exchange clearing fees, SEC/FINRA regulatory fees, financing costs, and futures contract roll drag.
- **The 100 Trades Fallacy: 100 trades is not proof**: The claim that "100 trades proves a strategy" is `INCORRECT_AS_STATED`. 100 trades is not proof; 100 trades is an arbitrary milestone. Statistical validity depends on variance, skewness, kurtosis, autocorrelation, regime diversity, and total trials K (multiple testing).
- **Perturbation Limits**: $\pm 20\%$ parameter stability is a useful diagnostic check, but does NOT mathematically prove the absence of data snooping.
- **Bar-Path Fail-Closed Contract**: Intrabar bar-path ambiguity must be resolved with strict fail-closed assumptions (worst-case fill path) if high-resolution tick data is unavailable.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - Directly maps to [METHODOLOGY_CONTROLS.md](file:///docs/research_intake/v1/METHODOLOGY_CONTROLS.md) (spread, commission, slippage, swap, market impact, multiple testing, K, hard OOS, prospective, bar-path ambiguity, negative control, 100 trades is not proof, profit factor is not supreme).
- **Trial Status**: Preserved as a foundational methodology reference.
