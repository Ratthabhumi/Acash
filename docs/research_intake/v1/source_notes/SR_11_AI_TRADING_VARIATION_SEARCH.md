# SR-11 — AI Trading / Variation Search

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Promotional video on AI-assisted algorithmic trading and strategy generation.
- **Reported Claims & Methodology**:
  - Claims AI dramatically accelerates strategy development, allowing retail traders to test thousands of variations.
  - Asserts that high win rate alone is insufficient for trading success.
  - Creator argues that older historical data is less useful or irrelevant due to continuous market regime changes.
  - Claims that deep programming knowledge is becoming obsolete; prompt engineering and LLM direction are allegedly more critical.
  - Singles out Profit Factor (PF) as the single most important metric for evaluating strategy quality.
  - Suggests improving PF by iteratively adding filters, indicators, entry/exit tweaks, and time-of-day constraints.
  - Recommends variation searching through hundreds or thousands of parameter configurations to find top performers.
  - Claims that generating more trades helps strategies reach their statistical win-rate expectation under the Law of Large Numbers.
  - Recommends specific AI models for automated code generation.

## 2. Human-Reviewed Scientific Critique
- **Profit Factor Fallacy: profit factor is not supreme**: Profit factor is a single ratio that ignores trade sequence, autocorrelation, and drawdown duration; it is NOT supreme.
- **Regime & Old Data Value**: Dismissing historical data discards out-of-sample stress regimes (e.g., 2008 GFC, 2020 crash), drastically amplifying overfitting risk.
- **Multiple-Testing Explosion**: Scanning hundreds or thousands of AI-generated variations expands the trial count K (multiple testing), causing nominal $p$-values to collapse under data-snooping bias.
- **Replication Fallacy**: Duplicating a signal across multiple funded prop firm accounts does NOT create independent observations.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - Directly maps to [METHODOLOGY_CONTROLS.md](file:///docs/research_intake/v1/METHODOLOGY_CONTROLS.md) (Multiple Testing, K Expansion, and Metric Evaluation standards: profit factor is not supreme).
- **Trial Status**: Preserved as a critique benchmark for automated strategy mining.
