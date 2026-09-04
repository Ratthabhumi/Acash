# ACASH Strategy Admission Standard v1.0
## Sovereign Governance, Empirical Verification & Multi-Gate Strategy Admission Specification

> **Document ID:** `ACASH-SPEC-STRAT-ADMISSION-v1.0`  
> **Status:** Approved Architecture & Governance Specification (Phase 17 Rev 4.1)  
> **Parent Governance:** ADR-022 (Market-Adaptive Trading Governance), ADR-023 (Strategy Admission & Bounded Allocation)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief)  
> **Date:** 2026-09-04  
> **Version:** 1.0.0  

---

> [!IMPORTANT]
> **STRICT GOVERNANCE BOUNDARY & CAPITAL RESTRICTIONS:**
> - **THIS SPECIFICATION DOES NOT GRANT LIVE TRADING AUTHORITY.**
> - **THIS SPECIFICATION DOES NOT ALLOCATE LIVE CAPITAL.**
> - **CAPITAL ALLOCATION AUTHORITY REMAINS HARD-LOCKED AT $0.00.**
> - **GATE A REMAINS NOT CERTIFIED (PENDING CONSOLIDATED GATE A AUDIT).**
> - **GATE B REMAINS STRICTLY LOCKED.**
> - **ZERO RUNTIME MUTATION TO `src/acash/execution/`.**

---

## 1. Executive Summary & Epistemic Foundations

This specification establishes the institutional-grade **Strategy Admission Standard** for ACASH. It functions as the non-negotiable sovereign governance gateway that every trading strategy candidate—whether internal quantitative model, external commercial EA, machine learning system, or discretionary rule set—must satisfy before being admitted to the Sovereign Strategy Catalog or evaluated for capital allocation.

### 1.1 The Core Epistemic Identity: Profit $\neq$ Skill $\neq$ Edge $\neq$ Luck-Free
A foundational quantitative tenet of ACASH is that observed profitability is **never** self-authenticating proof of edge:

$$\boxed{\text{Observed Profit} \neq \text{Proven Skill} \neq \text{Structural Edge} \neq \text{Luck-Free Performance}}$$

Observed trading P&L is conceptually decomposed into distinct structural and stochastic components:
$$\begin{aligned}
\text{Observed Performance} = &\quad \text{Potential Unexplained Excess Return} \\
&+ \text{Market / Factor Exposure (Beta, Momentum, Carry, Value)} \\
&+ \text{Regime Tailwind (Favorable Market Environment)} \\
&+ \text{Liquidity Economics (Spread Capture, Immediacy Provision)} \\
&+ \text{Risk Premia (Variance, Tail-Risk, Liquidity Risk)} \\
&+ \text{Leverage / Sizing Multipliers} \\
&+ \text{Execution Advantage (Latency, Infrastructure, Fill Quality)} \\
&+ \text{Structural / Information Advantage} \\
&+ \text{Realized Randomness / Luck} \\
&- \text{Transaction Costs, Slippage, Financing Drag, and Implementation Friction}
\end{aligned}$$

> [!NOTE]
> This decomposition represents an institutional governance framework, **not** an exact closed-form accounting identity unless empirical factor/cost models can be estimated with statistical validity. The framework strictly forbids treating unexplained residual return as proven alpha.

### 1.2 Five Categorical Sources of Observed Performance
Every candidate's historical returns are categorized across five non-mutually-exclusive sources:
1. **Genuine / Persistent Skill:** Edge that survives repeated independent validation, out-of-sample testing, and cannot be attributed to known factor/regime risks.
2. **Structural Edge:** Repeatable microstructure advantage (liquidity provision economics, latency/queue advantage, spread capture, order flow asymmetry, financing differential).
3. **Exposure-Driven Performance:** Returns explained by market beta, momentum, carry, value, volatility premia, or structural leverage.
4. **Regime Tailwind:** Performance generated primarily because the testing window coincided with an exceptionally favorable market environment.
5. **Luck / Sample Anomaly:** Random trade sequencing, clustered wins, multiple-testing selection bias, or small-sample outliers.

---

## 2. Strategy Admission Lifecycle

The strategy lifecycle enforces a formal state-space progression from initial concept to catalog retirement:

$$\begin{aligned}
\text{STRATEGY CANDIDATE} &\longrightarrow \text{GATE 0: DEFINITION \& OPERATIONAL SPECS} \\
&\longrightarrow \text{GATE 1: ECONOMIC / STATISTICAL HYPOTHESIS} \\
&\longrightarrow \text{GATE 2: HISTORICAL BACKTEST \& HAC INFERENCE} \\
&\longrightarrow \text{GATE 3: OUT-OF-SAMPLE \& WALK-FORWARD PERSISTENCE} \\
&\longrightarrow \text{GATE 4: CANONICAL STRESS TESTING MATRIX} \\
&\longrightarrow \text{GATE 5: MONTE CARLO PATH \& SEQUENCE RISK} \\
&\longrightarrow \text{GATE 6: PARAMETER ROBUSTNESS \& CLIFF ANALYSIS} \\
&\longrightarrow \text{GATE 7: EXECUTION REALITY ATTRIBUTION} \\
&\longrightarrow \text{GATE 8: FORWARD DEMO / PAPER EVIDENCE} \\
&\longrightarrow \text{GATE 9: EXPECTED VS ACTUAL MECHANISM DRIFT} \\
&\longrightarrow \text{GATE 10: SOVEREIGN ADMISSION DOSSIER (20 QUESTIONS)} \\
&\longrightarrow \text{SOVEREIGN CATALOG ACTIVE} \longrightarrow \text{RE-VALIDATION / SUSPENSION / RETIREMENT}
\end{aligned}$$

### Orthogonal State Plane Model
To avoid semantic collision with Phase 11 `ForwardHealthStateMachine`, ACASH decouples state into three independent orthogonal planes:
1. **Admission Status (`StrategyAdmissionStatus`):** Sovereign committee authority (`ADMITTED`, `CONDITIONALLY_ADMITTED`, `OBSERVE_ONLY`, `REJECTED`, `SUSPENDED`, `RETIRED`).
2. **Lifecycle State (`StrategyLifecycleState`):** Pipeline progress (`CANDIDATE`, `IN_EVALUATION`, `GOVERNANCE_REVIEW`, `CATALOG_ACTIVE`, `CATALOG_SUSPENDED`, `ARCHIVED`).
3. **Operational Health (`ForwardHealthState`):** Runtime monitoring plane (`INSUFFICIENT_EVIDENCE`, `HEALTHY`, `DEGRADED`, `STRUCTURAL_BREAK`, `MONITORING_BLOCKED`).

---

## 3. The 11 Strategy Admission Gates (Gate 0 through Gate 10)

### Gate 0 — Strategy Mechanism & Operational Definition
- **Objective:** Establish unambiguous machine-readable identity, operational mechanics, and structural constraints.
- **Mandatory Requirements:**
  - `strategy_id`, `strategy_name`, `strategy_version`
  - `StrategyMechanism`: `FORECASTING`, `LIQUIDITY_PROVISION`, `ARBITRAGE`, `CARRY`, `VOLATILITY`, `EXECUTION`, `OTHER_RESEARCH_DEFINED`
  - `StrategyStyle`: `MOMENTUM`, `MEAN_REVERSION`, `BREAKOUT`, `MARKET_NEUTRAL`, `TREND_FOLLOWING`, `GRID_PROGRESSION`, `OTHER`
  - Instrument universe, timeframe, entry/exit logic summaries, sizing method, `max_positions`, `max_gross_exposure_ratio`.
- **Failure Condition:** Ambiguous entry/exit logic, undeclared leverage, or unbounded position counts fail closed immediately.

### Gate 1 — Economic / Statistical Hypothesis & Falsification Criteria
- **Objective:** Answer *"Why should this strategy have an edge?"* before analyzing performance.
- **Mandatory Requirements:**
  - Mechanism statement (e.g. behavioral overreaction, liquidity premium, structural queue priority).
  - Explicit falsification criteria (e.g. "If net expectancy drops below 1.0 pip over 200 trades, hypothesis is falsified").
  - Declared known failure regimes.
- **Failure Condition:** A profitable backtest without a plausible economic/statistical mechanism is strictly rejected.

### Gate 2 — Historical Backtest & HAC-Adjusted Inference
- **Objective:** Quantify historical return distribution net of realistic market frictions.
- **Mandatory Requirements:**
  - Gross vs Net P/L (net of historical spreads, commissions, swaps, and conservative slippage).
  - Sharpe Ratio Estimate + HAC (Heteroskedasticity and Autocorrelation Consistent) standard errors / confidence intervals.
  - Sortino, Calmar, Profit Factor, Expectancy, Maximum Closed Drawdown, Maximum Floating Drawdown.
  - Tail risk: Expected Shortfall (CVaR at 95% and 99%).
  - Factor decomposition using applicable `FactorModelType` (`NONE`, `MARKET_SPECIFIC`, `RESEARCH_DEFINED`, `VALIDATED`).
- **Failure Condition:** Net profit factor $\le 1.0$, negative net expectancy, or undefined drawdown boundaries.

### Gate 3 — Out-of-Sample & Walk-Forward Persistence
- **Objective:** Test persistence outside development data to guard against data mining and overfitting.
- **Mandatory Requirements:**
  - Strict temporal separation: In-Sample (IS), Out-of-Sample (OOS), and untouched Holdout.
  - Multi-window Walk-Forward Analysis (WFA) with Walk-Forward Efficiency (WFE) ratio $\ge 0.50$.
  - Combinatorial Purged Cross-Validation (CPCV) to test path-independent stability.
- **Failure Condition:** Severe OOS performance collapse (>50% degradation vs IS) or negative OOS return.

### Gate 4 — Canonical Stress Testing Matrix
- **Objective:** Verify survival under acute liquidity, volatility, and structural shocks.
- **Authoritative Stress Testing Scenarios:**

| Scenario ID | Scenario Class | Perturbation Applied | Parameter Provenance | Calibration Methodology | Required Observations | Pass/Fail Semantics | Applicability Basis | Status |
|---|---|---|---|---|---|---|---|---|
| `SCN-VOL-01` | Volatility Spike | Instantaneous 3x ATR expansion over 5 bars | `RESEARCH_DERIVED` | Historical 99th percentile ATR jump in G10 FX | Floating DD, margin consumption, liquidation distance | Ruin prob = 0; Free margin > 30% | All strategies | **MANDATORY** |
| `SCN-VOL-02` | Volatility Compression | ATR drops to < 10th percentile for 30 days | `RESEARCH_DERIVED` | Historical multi-week summer holiday range compression | Opportunity cost, stale carrying costs | No runaway grid expansion; zero invalid exits | Breakout / Trend | **MANDATORY** |
| `SCN-SPR-01` | Spread Widening | 5x normal spread expansion at entry/exit | `BROKER_OBSERVED` | MetaQuotes MT5 roll-over hour (21:00–22:00 UTC) spread logs | Realized net P/L, slippage drag | Expectancy remains $\ge 0$ under 2x spread | All strategies | **MANDATORY** |
| `SCN-GAP-01` | Weekend / Session Gap | 200 bps price gap through Stop Loss | `HISTORICAL_EMPIRICAL` | Historical weekend election/geopolitical gap distributions | Gap slippage loss, negative balance risk | Max loss strictly $\le$ Risk Budget ceiling | All strategies | **MANDATORY** |
| `SCN-LIQ-01` | Liquidity Vacuum | Order book depth drops 80%; partial fills | `BROKER_OBSERVED` | Thin session execution observations & holiday book depth | Unfilled leg risk, basket desynchronization | No orphan legs; execution fails closed | Multi-leg / Grid / Arbitrage | **MANDATORY** |
| `SCN-LAT-01` | Execution Delay Spike | 500 ms roundtrip broker latency injected | `BROKER_OBSERVED` | Cross-region VPS-to-broker network congestion tail | Adverse fill slippage, stale signal execution | Fails closed on quote expiration | Scalping / Microstructure | **MANDATORY** |
| `SCN-TRN-01` | Persistent Adverse Trend | 5-sigma monotonic trend without pullbacks | `RESEARCH_DERIVED` | Historical SNB 2015 / Brexit multi-standard-deviation extensions | Max basket exposure, margin exhaustion level | Basket resolves within max exposure or halts | Grid / Martingale / Mean-Rev | **MANDATORY** |
| `SCN-COR-01` | Correlation Breakdown | Pair/basket correlation flips from +0.8 to -0.8 | `HISTORICAL_EMPIRICAL` | Regime-switch correlation breakdown during liquidity crisis | Net portfolio directional exposure | Max portfolio gross exposure strictly bounded | Multi-asset / Pair Arbitrage | **MANDATORY** |
| `SCN-EVT-01` | High-Impact News Shock | 100 bps dislocation in < 1 second (e.g. NFP/CPI) | `HISTORICAL_EMPIRICAL` | High-impact economic release tick feed recordings | Slippage, stop execution price, spread spike | Adheres to Event Policy (Hold, Halt, or Flatten)| All strategies | **MANDATORY** |
| `SCN-BRK-01` | Structural Regime Break | Mean return shifts negative; volatility doubles | `RESEARCH_DERIVED` | Out-of-sample monetary policy regime shifts | Expected-vs-actual drift, downgrade trigger | Strategy trips Gate 9 drift within $N$ bars | All strategies | **MANDATORY** |
| `SCN-SWP-01` | Financing Drag (Swap) | Triple swap / high-interest rate differential | `GOVERNANCE_DEFINED` | Conservative financing rate stress model | Long-term holding cost erosion | Net expectancy positive after 60-day holding | Swing / Long-duration | RESEARCH_ONLY |
| `SCN-REC-01` | Recovery Trap Excursion | Sustained underwater float near liquidation | `RESEARCH_DERIVED` | Historical near-death recovery trajectories | Drawdown duration, near-death exposure | No unhedged infinite recovery assumption | Grid / Averaging | **MANDATORY** |

### Gate 5 — Monte Carlo Sequence & Path Risk (Dependency-Aware)
- **Objective:** Evaluate distribution of drawdowns and ruin under randomized trade order.
- **Mandatory Requirements:**
  - Declaration of dependency assumptions: Plain IID trade shuffling is strictly prohibited if trade returns exhibit serial correlation, volatility clustering, or regime dependence.
  - Implementation of Block Bootstrap or Markov Resampling for dependent series.
  - Distributional outputs: 95th and 99th percentile maximum drawdown, longest loss streak, probability of ruin (must be mathematically 0.00% under allocation bounds).
- **Failure Condition:** Probability of ruin $> 0.00\%$ or 99th percentile drawdown exceeding portfolio survival tolerance.

### Gate 6 — Parameter Robustness & Cliff Analysis
- **Objective:** Test sensitivity to parameter neighborhood perturbations.
- **Mandatory Requirements:**
  - Multi-dimensional parameter neighborhood sweep ($\pm 10\%, \pm 20\%$).
  - Detection of "parameter cliffs" (isolated spiky peaks where small parameter changes destroy profitability).
  - Cost decay sensitivity (at what multiple of spread does the edge vanish?).
- **Failure Condition:** Strategy collapses under $\pm 10\%$ parameter shift or vanishing edge under $+50\%$ spread.

### Gate 7 — Execution Reality Attribution
- **Objective:** Bridge research assumptions to executable reality.
- **Mandatory Requirements:**
  - Reality Gap Attribution: Decomposing execution drag into spread delta, slippage delta, and latency drag.
  - Minimum lot size, lot step quantization, and margin requirement constraints verified against live broker specs (`BrokerSymbolSpec`).
- **Failure Condition:** Edge reliant on unrealistic zero-spread, instantaneous fills, or sub-micro-lot execution.

### Gate 8 — Forward Demo / Paper Evidence (Effective Sample > Calendar Days)
- **Objective:** Validate operational execution under live market data feeds.
- **Strict Anti-Calendar Rule:**
  $$\boxed{\text{Calendar Days (e.g. 90 days)} \neq \text{Sufficient Forward Evidence}}$$
  - 90 calendar days with 5 trades in a single quiet summer regime provides **zero** statistical certification.
  - 30 calendar days with 400 independent execution observations across trending, mean-reverting, and news-event regimes provides substantive operational evidence.
- **Mandatory Requirements:**
  - `EffectiveEvidenceSample` evaluating $N_{\text{eff}}$ after adjusting for autocorrelation, overlapping positions, and signal clustering.
  - Minimum regime diversity: Strategy must have been observed across at least two distinct classified market states.
  - Realized execution observations (actual broker spreads, actual slippage, fill latency).
- **Failure Condition:** Insufficient effective observations ($N_{\text{eff}} < \text{threshold}$) or zero regime coverage, regardless of elapsed calendar time.

### Gate 9 — Expected vs Actual Mechanism Drift
- **Objective:** Continuous monitoring to detect when realized forward mechanics diverge from research expectations.
- **Mandatory Requirements:**
  - Tracking error against expected return distribution.
  - Dynamic monitoring of win rate, average payout ratio, and holding duration.
  - Integration with Phase 11 `ForwardTelemetryIngestor` emitting `ForwardHealthState`.
- **Failure Condition:** Divergence exceeding statistical control bands triggers `ForwardHealthState.DEGRADED`.

### Gate 10 — Sovereign Admission Dossier & The 20 Mandatory Questions
- **Objective:** Comprehensive sovereign review and formal admission decision.
- **Mandatory Requirements:**
  - Review of the **Alternative Explanation Register**.
  - Written forensic answers to all **20 Mandatory Admission Questions**.
  - Sovereign Committee Verdict: `ADMITTED`, `CONDITIONALLY_ADMITTED`, `OBSERVE_ONLY`, `REJECTED`, `SUSPENDED`, `RETIRED`.

---

## 4. The Alternative Explanation Register (Gate 10)

Every strategy candidate must maintain an explicit counter-hypothesis register:

| Explanation ID | Counter-Hypothesis | Evaluation Scope | Mandatory Status Values |
|---|---|---|---|
| `ALT-01` | **Market Beta Drift** | Returns explained by broad market drift rather than strategy logic | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-02` | **Short Volatility Premia** | Returns are compensation for unhedged tail-risk exposure (picking up pennies) | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-03` | **Regime Tailwind** | Performance was generated by an abnormal, non-repeating favorable market state | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-04` | **Selection / Data Mining Bias** | Strategy was selected as the lucky winner among hundreds of tested variations | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-05` | **Execution Fantasy** | Profitability depends on zero slippage or unrealistic order-fill queue priority | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-06` | **Asymmetric Recovery / Averaging** | Strategy hides risk via unclosed floating drawdown or martingale progression | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |

> [!CAUTION]
> If any critical alternative explanation remains `PLAUSIBLE` or `SUPPORTED` without satisfactory risk bounds, unconditional admission is **strictly prohibited**.

---

## 5. The 20 Mandatory Admission Questions

The final Gate 10 dossier must explicitly record written answers to:
1. What is the economic, statistical, or microstructure mechanism generating the return?
2. Under which specific market states and regimes is the strategy expected to generate positive excess return?
3. Under which specific market states and regimes is the strategy expected to suffer losses or decay?
4. What systematic market, factor, or alternative risk premia exposures does the strategy carry?
5. Does the strategy demonstrate positive net expectancy after accounting for realistic spreads, commissions, slippage, and swap costs?
6. Does the empirical edge persist in out-of-sample testing outside the discovery dataset?
7. Does the edge persist across multiple walk-forward or temporal validation windows?
8. Does historical profitability depend predominantly on a single regime or isolated historical episode?
9. Could the observed performance plausibly be explained by randomness, trade sequencing, or luck?
10. What is the effective sample size ($N_{\text{eff}}$) after accounting for autocorrelation and position clustering?
11. How many strategy variants, indicators, and parameter permutations were evaluated before discovering this candidate?
12. Is the candidate vulnerable to multiple testing bias, selection bias, or data snooping?
13. How much of the net performance is attributable to execution quality, speed, or broker microstructure?
14. What are the quantified risk consequences under the 12 canonical stress testing scenarios?
15. What is the maximum drawdown and ruin probability under adverse trade sequencing via Monte Carlo simulation?
16. What plausible alternative explanations in the Alternative Explanation Register remain unresolved?
17. What observable empirical evidence would conclusively falsify the strategy's core hypothesis?
18. What observable monitoring conditions would trigger immediate strategy suspension or de-allocation?
19. What critical data, regime observations, or execution telemetry are currently missing or unverified?
20. **[MANDATORY GOVERNANCE QUESTION] Why should this strategy NOT receive additional capital or operational risk at this time?**

---

## 6. Multi-Dimensional Evidence Vector (No Single Skill Score)

ACASH strictly rejects scalar composite numbers such as `skill_score = 87/100`. Skill is evaluated via the multi-dimensional **`SkillEvidence`** vector DTO using `EvidenceSupportLevel` (`SUPPORTED`, `WEAK`, `INCONCLUSIVE`, `NOT_TESTED`, `FAILED`, `NOT_APPLICABLE`):

```python
class SkillEvidence(BaseModel):
    out_of_sample_support: EvidenceSupportLevel
    walk_forward_support: EvidenceSupportLevel
    regime_coverage_support: EvidenceSupportLevel
    execution_realism_support: EvidenceSupportLevel
    robustness_support: EvidenceSupportLevel
    attribution_support: EvidenceSupportLevel
    persistence_support: EvidenceSupportLevel
    sample_quality_support: EvidenceSupportLevel
    unresolved_alternatives_count: int
    statistical_confidence: Decimal
```

### Luck Sensitivity & Uncertainty
Rather than asking the unanswerable metaphysical question of whether luck is "present or absent", ACASH measures:
- **`LuckSensitivity` (`LOW`, `MODERATE`, `HIGH`, `UNKNOWN`):** Quantifies how sensitive the observed return is to random trade reshuffling and bootstrap perturbations.
- **`ObservedOutcomeUncertainty` (`LOW`, `MODERATE`, `HIGH`, `UNKNOWN`):** Quantifies the dispersion band around observed outcome metrics.

---

## 7. Mandatory Scientific Language Rules

All documentation, logs, and generated research dossiers must adhere to institutional epistemic language:

| Prohibited Unverified Claims | Mandatory Epistemic Formulations |
|---|---|
| ❌ *"Strategy proved skill"* | ✅ *"Evidence is supportive of persistent excess return"* |
| ❌ *"Strategy proved alpha"* | ✅ *"Observed performance is consistent with the stated mechanism"* |
| ❌ *"Luck was completely eliminated"* | ✅ *"Performance remains statistically distinguishable from null under tested sequencing"* |
| ❌ *"Regime X caused the returns"* | ✅ *"Conditional performance is significantly stronger under Regime X"* |
| ❌ *"Backtest guarantees execution"* | ✅ *"Research performance under tested cost assumptions"* |
| ❌ *"Strategy is certified safe"* | ✅ *"Strategy satisfied Gate 0–10 evidence criteria under tested boundaries"* |

---

## 8. Authoritative Academic & Empirical Grounding

1. **Barber, Lee, Liu, & Odean (2014):** *The Cross-Section of Speculator Skill: Evidence from Day Trading.* Proves that while the vast majority of day traders lose net of costs, a small persistent upper tail exists; crucially, luck explains a substantial fraction of top performers' short-term returns.
2. **Berk & van Binsbergen (2015):** *Measuring Skill in the Mutual Fund Industry.* Proves managerial skill exists when measured as gross value extraction, but investor net returns depend entirely on cost and fee drag.
3. **Choi & Zhao (2020):** Demonstrates that historical performance persistence is not stationary; out-of-sample persistence decays significantly across eras, mandating continuous forward monitoring.
4. **Market Microstructure Literature (Glosten-Milgrom 1985, Kyle 1985, Amihud 2002):** Establishes that liquidity-providing and market-making strategies derive edge from spread capture and adverse-selection management—fundamentally distinct from directional forecasting.
5. **MetaTrader 5 MqlRates Technical Architecture:** Proves that MetaQuotes explicitly decouples `tick_volume` (quote ticks) from `real_volume` (exchange traded lots) and instantaneous `spread`, validating ACASH's strict volume provenance contracts.
