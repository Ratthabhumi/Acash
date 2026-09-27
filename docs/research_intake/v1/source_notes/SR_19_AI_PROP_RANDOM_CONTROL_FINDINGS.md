# SR-19 — AI / Prop / Random Control Findings

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Algorithmic trading video report / prop firm strategy mining presentation.
- **Reported Claims & Mining Statistics**:
  - Asserts manual backtesting requires 10–20 hours per strategy.
  - Claims an automated AI system tested 10,000+ strategy variations (10,000+) representing 5.6 million trades (~5.6 million) overnight.
  - Creator claims personal five-figure prop payouts achieved through AI-assisted trading setups.
  - Highlights that tight stop-losses are systematically destroyed by commission drag.
  - Reports that NASDAQ CFD was the best performing asset in their automated search.
  - Reports that higher timeframes (30m / 60m) produced significantly more winning systems than lower timeframes (1m / 3m).
  - Identifies New York AM / opening hours as the top performing session window.
  - Claims fixed stop (fixed stops) outperformed structural stops in their empirical pool.
  - Claims time exit (time-based exits) outperformed indicator-based exits.
  - Reports that across 50 popular retail strategy families, all were net negative after commissions.
  - Out of 10,000 tested systems, only ~60 strategies (0.6%) achieved a >50% estimated probability of passing a prop evaluation.
  - Creator infers that 99.4% (99.4%) of automated retail systems fail.
  - Notes that top volume-spike candidates achieved large payoffs but had win rates of only 7–14%.
  - Reports that a pure random control strategy (random entries with fixed exit) beat ~99% of the tested strategy pool.
  - Concludes from this that algorithmic trading is flawed and human discretion (human discretion) intuition is superior.

## 2. Human-Reviewed Scientific Critique
- **External Unverified Claim**: All search statistics (10,000+ strategies, 5.6 million trades, 0.6% pass rate, 99.4% failure) are unverified vendor claims (`EXTERNAL_UNVERIFIED_CLAIM`).
- **Massive Multiple-Testing Fallacy**: Searching 10,000 strategies without False Discovery Rate adjustments guarantees that any "surviving" 60 strategies are primarily statistical flukes (multiple testing, K).
- **Misinterpretation of Random Control**: The fact that a random control beat 99% of strategies does NOT mean random trading has alpha; it demonstrates that naive retail strategies suffer catastrophic friction loss from overtrading and spread crossing.
- **Non Sequitur on Discretion**: Concluding that "automation fails, therefore human discretion has an edge" is a complete logical fallacy. human discretion requires prospective, controlled A/B evaluation.
- **Account Duplication vs. Sample Size**: Copying a signal to multiple prop accounts does NOT create independent observations.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - Directly maps to [METHODOLOGY_CONTROLS.md](file:///docs/research_intake/v1/METHODOLOGY_CONTROLS.md) (Random / Negative Controls standard, random control, human discretion, fixed stop, time exit).
  - `RI-01`: Opening-State / Intraday Momentum.
  - `RI-10`: Volume-Spike Breakout.
- **Trial Status**: Preserved as an empirical case study in multi-testing hazards.
