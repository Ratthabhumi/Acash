# ACASH Pre-Empirical Backtest & Out-Of-Sample (OOS) Validation Protocol

**Document ID:** `docs/phase14/backtest_oos_validation_protocol.md`
**Status:** NON-GOVERNING PRE-EMPIRICAL VALIDATION PROTOCOL
**Authority:** NONE
**Empirical Test Authorization:** NONE
**Backtest Authorization:** NONE
**Paper Authorization:** NONE
**Live Authorization:** NONE
**Canonical Statistical Authority:** PHASE 6 / STRATEGY ADMISSION STANDARD (`docs/architecture/strategy_admission_standard.md`)
**Canonical Architectural Context:** `AGENTS.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/architecture/research_architecture.md`, `docs/phase14/research_doctrine.md`, `docs/phase14/historical_data_qualification_spec.md`, `docs/phase14/research_candidate_backlog.md`

---

> [!CAUTION]
> ### PRE-EMPIRICAL GOVERNANCE & STATISTICAL INTEGRITY INVARIANTS
> - **PRE-DECLARATION REQUIREMENT:** This protocol defines the mathematical and methodological rules of evaluation **BEFORE** backtest simulations are executed or results are observed. Under no circumstances may evaluation rules, cost tiers, or partition boundaries be altered post-hoc to rescue strategy performance.
> - **CANONICAL MATHEMATICAL AUTHORITY PRESERVED:** Phase 6 canonical implementations (`SearchTrialLedger`, `DeflatedSharpe`, `PBO`, `MinTRL`, `FWER`, `FDR`, `HaircutSharpe`) remain the sole authoritative arbiters of statistical validity. This document creates **zero** alternate formulas or mathematical heuristics.
> - **NO EMPIRICAL RUNS AUTHORIZED:** This document confers **zero** authority to run backtests, optimize parameters, execute simulations, or query historical databases for alpha.
> - **NO HYPOTHESIS CREATED:** `HYP_003` remains strictly **ABSENT**.
> - **CORE PRINCIPLE EQUALITIES & BOUNDARIES:**
>   $$\text{Backtest Profitability} \neq \text{Validated Empirical Alpha}$$
>   $$\text{Statistical Significance} \neq \text{Strategy Admission}$$
>   $$\text{Strategy Admission} \neq \text{Paper Trading Authorization}$$
>   $$\text{Paper Trading Success} \neq \text{Live Capital Authorization}$$
> - **SOAK & RUNTIME ISOLATION:** The active G7 soak runtime, homelab containers, and monitoring loops are 100% untouched.
> - **CAPITAL LOCKED:** Canonical capital is **$0.00**; `NO_REAL_ORDERS=true`.

---

## 1. Validation Philosophy & Pre-Registration Doctrine

### 1.1 The Epistemic Hazard of Unconstrained Backtesting
A backtest is not proof of future profitability; it is a historical simulation vulnerable to severe optimization bias, selection bias, survivorship bias, and multiple-testing distortion. If a researcher is permitted to iterate freely on parameters, indicators, and filters until a historically profitable backtest curve emerges, the resulting strategy is almost certainly an overfitted artifact of noise (Harvey, Liu, & Zhu 2016; Bailey, Borwein, López de Prado, & Zhu 2014).

To preserve statistical validity, ACASH operates under a strict **Pre-Registration Doctrine**:
1. All parameter search spaces, partition dates, cost multipliers, and rejection criteria must be cryptographically sealed in a research manifest **before** running the empirical backtest.
2. The final Out-Of-Sample (OOS) dataset must remain untouched until in-sample parameter selection is concluded.
3. Every backtest run—profitable or unprofitable—must be recorded in the canonical `SearchTrialLedger` to penalize multiple testing via the Deflated Sharpe Ratio.

### 1.2 End-to-End Experiment Lifecycle

```text
1. RESEARCH QUESTION (Documented in Backlog, e.g. RQ-BACKLOG-001)
       ↓
2. FORMAL HYPOTHESIS RATIFICATION (Human Authorization → Formal HYP_###)
       ↓
3. DATASET FREEZE (Cryptographic Binding to Qualified Dataset Hash)
       ↓
4. PRE-REGISTRATION (Trial Plan, Search Space, Partitions, Costs Frozen)
       ↓
5. TRIAL CENSUS REGISTRATION (Trial ID sealed in SearchTrialLedger)
       ↓
6. DEVELOPMENT & TRAIN (In-Sample Parameter Estimation)
       ↓
7. VALIDATION STAGE (Model Family Selection, Complexity Penalization)
       ↓
8. UNTOUCHED OUT-OF-SAMPLE (OOS) EVALUATION (Single Final Evaluation)
       ↓
9. WALK-FORWARD & REGIME ROBUSTNESS BATTERY (Stability Checks)
       ↓
10. FRICTION STRESS (Base, Conservative, and Stress Cost Tiers)
       ↓
11. CANONICAL PHASE 6 GATE (DSR, PBO, MinTRL, Haircut Sharpe Verification)
       ↓
12. STRATEGY ADMISSION DECISION (Independent Human Governance Review)
       ↓
13. SEPARATE PAPER TRADING AUTHORIZATION (Phase 13 90-Day Forward Run)
```

---

## 2. Dataset Freeze & Pre-Trial Binding Requirements

Before any backtest trial can be registered, the researcher must bind the experiment to a qualified historical dataset freeze (`docs/phase14/historical_data_qualification_spec.md`).

### Mandatory Pre-Trial Binding Record
The experiment configuration must explicitly record:
- `dataset_id`: Authoritative dataset identifier (e.g., `DS-CRYPTO-BTC-M1-v1.0`).
- `dataset_sha256`: Cryptographic hash of the normalized data file.
- `qualification_report_sha256`: Hash of the automated data qualification report.
- `instrument_universe`: Explicit list of permissible symbols (no dynamic expansion).
- `bar_timeframe`: Base aggregation frequency (`M1`, `M5`, `H1`, `D1`).
- `temporal_boundary`: Exact `[start_timestamp_utc, end_timestamp_utc]`.
- `corporate_action_policy`: Verified handling of splits/dividends where applicable.
- `futures_roll_policy`: Authoritative roll schedule and adjustment method where applicable.

> [!CAUTION]
> **DATASET MUTATION INVALIDATION:** If the underlying dataset is updated, patched, or extended, the dataset hash changes. Any prior backtest runs bound to the old hash cannot be directly combined with new runs without recording a formal dataset version transition in the trial ledger.

---

## 3. Data Partitioning: Train, Validation, and Untouched OOS

Data partitioning must be designed deliberately to reflect the strategy's time horizon and market cycles.

```text
|==================== TOTAL FROZEN HISTORICAL DATASET ====================|
[------- TRAIN / DEVELOPMENT -------][--- VALIDATION ---][-- UNTOUCHED OOS --]
         (In-Sample Fitting)            (Model Selection)    (Final Blind Eval)
                                       [--- PURGE ---]      [--- PURGE ---]
```

### 3.1 Partition Roles & Rules of Engagement

1. **TRAIN / DEVELOPMENT (In-Sample):**
   - *Allowed Activities:* Feature exploration, signal design, hyperparameter optimization, initial diagnostic visualization.
   - *Governance:* Every parameter variation tested during this phase must be accounted for in the trial census ($K$ trials).
2. **VALIDATION (Model Selection):**
   - *Allowed Activities:* Comparing model families (e.g. SMA vs. EMA vs. Breakout), selecting regularization penalties, evaluating hyperparameter stability surfaces.
   - *Epistemic Decay:* Repeated evaluation on the validation partition causes information leakage. With each inspection, the validation set becomes progressively less independent.
3. **UNTOUCHED OUT-OF-SAMPLE (OOS):**
   - *Allowed Activities:* A single, final, unadulterated evaluation of the chosen model candidate.
   - *Strict Invariant:* **The OOS partition must never be used to tune parameters, select features, or rescue a failing strategy.**
   - *Consequence of Failure:* If a candidate fails on the untouched OOS partition, the strategy is declared **`FAILED_OOS`**. The researcher cannot tweak parameters and re-test on the same OOS partition; doing so turns the OOS data into an in-sample dataset. A new, subsequent forward period or distinct market must be acquired.

### 3.2 Rejection of Arbitrary Universal Partition Ratios
ACASH strictly rejects dogmatic rules such as *"all datasets must use a 70/20/10 split"*. Partition boundaries must be established based on:
- **Regime Diversity:** Both Train and OOS partitions must span distinct volatility and macro environments (e.g. an OOS partition consisting entirely of a single one-directional bull market is statistically uninformative).
- **Effective Sample Size:** High-frequency strategies (M1/M5) require shorter calendar spans to accumulate sufficient trades; low-frequency macro strategies (D1) require multi-year partitions to capture adequate macro cycles.
- **Independence:** Partition dates must be explicitly declared and frozen in the pre-registration manifest.

---

## 4. Time-Series Leakage & Information Barrier Controls

Time-series backtesting is highly susceptible to subtle look-ahead bias. The following information barrier controls are strictly enforced:

### 4.1 Point-in-Time Feature Transformations
- **Rolling Estimators:** Rolling means, standard deviations, and ATR calculations must strictly use backward-looking windows ($t-W$ to $t$). Centered or forward-looking rolling windows are strictly forbidden.
- **Normalization & Scaling:** Z-score normalization or Min-Max scaling must use parameters ($\mu, \sigma$) estimated strictly from historical data up to time $t$. Using full-sample statistics to normalize past bars constitutes fatal look-ahead leakage.
- **Macro & Fundamental Data:** Economic data releases (e.g. CPI, Non-Farm Payrolls) must be timestamped to their **actual public release time**, not their statistical reference period. Point-in-time vintage data must be used to prevent revision leakage.

### 4.2 Purged & Embargoed Cross-Validation (CPCV)
When using cross-validation or evaluating strategies with multi-bar holding horizons:
- **Purging:** If a label or forward return spans from time $t$ to $t+h$, observations within $h$ bars before a partition boundary must be purged to prevent forward-return information from leaking into the adjacent fold (López de Prado 2018).
- **Embargoing:** Post-event serial correlation requires an embargo period following test folds to eliminate autoregressive memory leakage.
- *Canonical Integration:* Where Combinatorial Purged Cross-Validation (CPCV) is utilized for PBO calculation, the execution must strictly invoke the canonical Phase 6 implementation.

---

## 5. Walk-Forward Validation Protocol

Walk-forward analysis evaluates how dynamically re-estimated models perform across rolling or expanding historical segments:

```text
Expanding Window Walk-Forward:
Fold 1: [--- Train 1 ---][ Test 1 ]
Fold 2: [------ Train 2 ------][ Test 2 ]
Fold 3: [--------- Train 3 ---------][ Test 3 ]
Fold 4: [------------ Train 4 ------------][ Test 4 ]

Rolling Window Walk-Forward:
Fold 1: [--- Train 1 ---][ Test 1 ]
Fold 2:       [--- Train 2 ---][ Test 2 ]
Fold 3:             [--- Train 3 ---][ Test 3 ]
```

### 5.1 Protocol Invariants
1. **Mechanism Justification:** The choice between Expanding Window (accumulating all structural history) and Rolling Window (adapting to regime shifts by discarding stale history) must be justified economically by the strategy mechanism *prior* to testing.
2. **Anti-Cherry-Picking Invariant:** Walk-forward analysis is **not** an opportunity to adjust retraining frequencies or window lengths until every fold passes. The retrain interval and window parameters must be pre-declared.
3. **Consolidated Ledger Accounting:** All optimization iterations executed across all walk-forward folds must be aggregated into the canonical trial count ($K_{\text{total}} = \sum K_{\text{fold}}$).

---

## 6. Mandatory Benchmark Baselines (The Complexity Ladder)

A strategy cannot claim alpha in a vacuum. Every empirical backtest must be evaluated alongside mandatory benchmark baselines:

| Strategy Family | Required Benchmark Baselines | Hurdle Criteria |
| :--- | :--- | :--- |
| **Directional Crypto / Equity** | 1. Cash / Risk-Free ($0.00$ return).<br>2. Buy-and-Hold asset benchmark.<br>3. Simple Moving Average (SMA) baseline. | Must achieve higher Sharpe and lower MaxDD than Buy-and-Hold net of costs; must demonstrate statistically significant information gain over plain SMA. |
| **Regime-Conditioned Model** | 1. Unconditioned identical baseline model.<br>2. Passive cash benchmark. | Must prove that adding the regime filter significantly improves OOS Sharpe and MinTRL over the unconditioned baseline. |
| **Mean Reversion / Dislocation** | 1. Random-entry null model.<br>2. Unconditioned counter-trend baseline. | Must demonstrate that timing conditional on dislocation outperforms random-entry timing net of spread/friction. |
| **Cross-Sectional Momentum** | 1. Naive Equal-Weight universe portfolio.<br>2. Market-Cap Weighted universe benchmark. | Must outperform equal-weight allocation after accounting for turnover drag. |
| **Multi-Horizon Model** | 1. Standalone single-horizon baseline models. | Must demonstrate incremental information gain over the best individual horizon after parameter penalization. |

---

## 7. Friction, Cost Modeling, and Execution Realism

A profitable gross backtest that collapses under real-world transaction friction is completely worthless.

### 7.1 Separation of Gross and Net Performance
Every simulation run must independently report:
$$\text{Gross Return Series } \{R_{\text{gross}, t}\} \quad \text{and} \quad \text{Net Return Series } \{R_{\text{net}, t}\}$$
$$\Delta_{\text{friction}} = \text{Annualized Sharpe}_{\text{gross}} - \text{Annualized Sharpe}_{\text{net}}$$

### 7.2 Mandatory Three-Tier Cost Stress Battery
Every candidate strategy must be evaluated across three pre-declared friction tiers:

| Cost Tier | Exchange Fee Assumption | Spread Assumption | Slippage Assumption | Assessment Role |
| :--- | :--- | :--- | :--- | :--- |
| **Base Cost Tier** | Published VIP-0 / Retail taker fee (e.g. 5–10 bps). | Historical median bid-ask spread. | 1 tick adverse execution. | Realistic expected baseline friction. |
| **Conservative Tier** | Retail taker fee + 25% buffer. | 75th percentile historical spread. | 2 ticks adverse execution. | Buffer against deteriorating market liquidity. |
| **Stress Cost Tier** | 2.0x Base taker fee. | 95th percentile historical spread (high-volatility regime spread). | 3–5 ticks adverse slippage / queue penalty. | Evaluates strategy survival during flash crashes and liquidity vacuums. |

> [!CAUTION]
> **SURVIVAL HURDLE:** A candidate strategy that achieves positive net Sharpe under Base Cost but collapses to negative Sharpe or catastrophic drawdown under the Conservative Tier is classified as **`FAILED_UNDER_COSTS`** and blocked from qualification.

### 7.3 Execution Realism Models
- **Bar-Close vs. Next-Bar Execution:** Signals generated at the close of Bar $t$ must execute at the Open of Bar $t+1$ ($\text{price} = \text{open}_{t+1}$ plus spread/slippage). Zero-lag bar-close execution ($\text{price} = \text{close}_t$) is prohibited unless justified by high-frequency limit order simulation.
- **Resolution Limit:** Tick-level precision or intra-bar limit order fills cannot be claimed when testing against M1 or M5 OHLC bar data. If intra-bar execution is required, conservative assumptions must be applied (e.g. buying at bar High, selling at bar Low for adverse bounding).

---

## 8. Parameter Search Governance & Trial Accounting

Unbounded parameter searches destroy statistical degrees of freedom.

### 8.1 Pre-Declaration of Parameter Search Space
Before running optimization sweeps, the research manifest must record:
- Parameter names and economic interpretations.
- Explicit bounds and step sizes (e.g., `lookback_period` $\in [10, 100]$ step 10).
- Total discrete parameter permutations ($N_{\text{configs}}$).
- Optimization algorithm (Grid search, Random search, Bayesian optimization).
- Objective function (e.g. in-sample Sharpe ratio, Calmar ratio).

### 8.2 Canonical Alignment with SearchTrialLedger
- **Zero Discarded Trials:** Every evaluated parameter configuration constitutes a trial. A researcher must never discard losing trials from the ledger.
- **Trial Census:** The total trial count $K$ is authoritatively registered in `SearchTrialLedger`.
- **DSR Calculation:** Canonical Phase 6 `DeflatedSharpe` utilizes the total trial count $K$, sample variance of candidate trials $\mathbb{V}[\text{SR}_k]$, return skewness, and kurtosis to compute the multiple-testing adjusted $p$-value.

---

## 9. Sample Size, Independence, and Degrees of Freedom

ACASH maintains a strict distinction between raw bar count and independent statistical observations:

$$\text{Raw Bar Count } (T) \neq \text{Independent Effective Observations } (T_{\text{eff}}) \neq \text{Trade Count } (N_{\text{trades}})$$

### 9.1 Serial Dependence & Autocorrelation
- High-frequency bars (M1/M5) exhibit severe autocorrelation and volatility clustering. Treating $1,000,000$ M1 bars as $1,000,000$ independent IID samples is mathematically fraudulent.
- Effective sample size must be adjusted for serial correlation using canonical Newey-West long-run variance and effective degrees of freedom formulations.

### 9.2 Non-Binding Trade Count Planning Heuristics
While canonical acceptance is governed strictly by Minimum Track Record Length ($\text{MinTRL}$) and statistical significance, the following non-binding sample heuristics guide pre-empirical feasibility:

| Total Completed Trades | Statistical Evidence Level | Feasibility Assessment |
| :--- | :--- | :--- |
| **$< 100$ Trades** | Statistically Underpowered | Extremely vulnerable to small-sample noise; insufficient for distributional confidence. |
| **$100 - 300$ Trades** | Exploratory Feasibility | Minimum threshold for preliminary feature exploration; high error bounds on Sharpe. |
| **$500 - 1,000$ Trades** | Robust Research Evidence | Sufficient sample density to evaluate parameter stability and regime splits. |
| **$> 1,000$ Trades** | Strong Empirical Evidence | High statistical power, provided trades span multiple independent macro regimes. |

> [!WARNING]
> **GOVERNANCE STATUS: NON-BINDING PLANNING HEURISTIC ONLY.**
> A high trade count alone does not guarantee validity if trades are concentrated in a single regime or exhibit strong serial dependence. Canonical MinTRL formulas in Phase 6 override intuition.

---

## 10. Robustness Battery & Parameter Stability Analysis

A genuine market edge exhibits stability across neighboring parameter choices. Overfitted strategies display sharp, isolated "needles" of profitability surrounded by catastrophic losses.

```text
Robust Surface (Desirable):        Overfitted Spike (Disqualified):
   Sharpe                              Sharpe
     ^   _---_                           ^       |
     |  /     \                          |       |
     | /       \                         | _____/ \_____
     +------------> Parameter          +------------> Parameter
```

### 10.1 Parameter Stability Verification
- **Surface Smoothness:** Evaluate strategy performance across a $\pm 20\%$ perturbation grid around chosen parameters.
- **Cliff-Edge Detection:** If a $10\%$ shift in lookback period or threshold causes Sharpe to collapse by $> 50\%$ or swing from positive to negative, the strategy is flagged as **`FAILED_PARAMETER_STABILITY`**.
- **Sign Stability:** Returns must remain positive across the majority of neighboring parameter sets.

### 10.2 Component Ablation Testing
For multi-factor, multi-timeframe, or regime-conditioned strategies:
- Systematically remove each individual component or filter.
- Re-evaluate performance of the ablated sub-model.
- **Hurdle:** Each component must demonstrate statistically significant incremental contribution to the strategy's risk-adjusted returns. If removing a complex filter produces no material change in OOS performance, the filter must be pruned.

### 10.3 Cross-Regime Stress Battery
Strategies must be evaluated independently across partitioned macroeconomic environments:
1. **Bull Regime:** Sustained upward market trend.
2. **Bear Regime:** Sustained downward market trend.
3. **Sideways / Range-Bound:** High mean reversion, low directional drift.
4. **High-Volatility Regime:** Top 20th percentile volatility environment.
5. **Low-Volatility Regime:** Bottom 20th percentile volatility environment.
6. **Liquidity Stress Events:** Historical market flash crashes and crisis days.

---

## 11. Pre-Empirical Failure Taxonomy & Stopping Rules

ACASH treats empirical research failure as valuable scientific knowledge. Experiments that fail must be cataloged according to the authoritative failure taxonomy:

### 11.1 Authoritative Failure Codes
1. **`FAILED_IN_SAMPLE`:** Strategy cannot achieve statistical significance or required baseline outperformance in-sample.
2. **`FAILED_VALIDATION`:** Model family selection collapses during validation fold analysis.
3. **`FAILED_OOS`:** Strategy fails to maintain positive risk-adjusted returns on the untouched out-of-sample partition.
4. **`FAILED_WALK_FORWARD`:** Performance degrades substantially across rolling walk-forward test segments.
5. **`FAILED_UNDER_COSTS`:** Net returns turn negative or fall below hurdle rates under Conservative or Stress cost tiers.
6. **`FAILED_PARAMETER_STABILITY`:** Strategy exhibits cliff-edge sensitivity to minor parameter adjustments.
7. **`FAILED_REGIME_ROBUSTNESS`:** Edge is entirely confined to a single historical market regime and collapses in others.
8. **`FAILED_MULTIPLE_TESTING`:** Deflated Sharpe Ratio ($p > 0.05$) or Haircut Sharpe fails canonical Phase 6 significance tests.
9. **`FAILED_MIN_TRL`:** Historical track record length is shorter than the statistically required Minimum Track Record Length.
10. **`FAILED_DATA_QUALITY`:** Post-hoc discovery of data corruption, unadjusted corporate actions, or timestamp anomalies.
11. **`FAILED_REPRODUCIBILITY`:** Independent execution fails to replicate identical metrics from the simulation manifest.
12. **`FAILED_MECHANISM_REVIEW`:** Empirical behavior directly contradicts the hypothesized economic mechanism.

### 11.2 Early Stopping Rules (Anti-Data Mining Limits)
To prevent infinite iterative strategy rescue:
- **Maximum Search Budget:** Each formal hypothesis must declare a strict maximum parameter evaluation budget (e.g. $K_{\max} = 100$ trials). Once exhausted, research on that hypothesis terminates.
- **Zero OOS Rescues:** If a strategy fails OOS, modifying rules and re-testing on the same OOS partition is strictly blocked.

---

## 12. Reproducibility Contract & Simulation Manifest

Every completed backtest run must generate an immutable, cryptographically verifiable **Simulation Manifest** (`manifest.json`):

```json
{
  "simulation_id": "SIM-20260913-BTC-TREND-001",
  "trial_id": "TRIAL-0042",
  "hypothesis_id": "HYP_PROPOSAL_ONLY_NOT_RATIFIED",
  "dataset_freeze": {
    "dataset_id": "DS-CRYPTO-BTC-M1-v1.0",
    "dataset_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
    "qualification_report_id": "QR-20260913-BTC-M1-001"
  },
  "code_lineage": {
    "git_commit_sha": "c17c336b527de2762a1234567890abcdef123456",
    "clean_working_tree": true
  },
  "experiment_config_sha256": "a8f5f167f44f4964e6c998dee827110c...",
  "random_seed": 42,
  "partitions": {
    "train_utc": ["2022-01-01T00:00:00Z", "2023-12-31T23:59:00Z"],
    "validation_utc": ["2024-01-01T00:00:00Z", "2024-06-30T23:59:00Z"],
    "untouched_oos_utc": ["2024-07-01T00:00:00Z", "2025-12-31T23:59:00Z"]
  },
  "cost_model": {
    "tier": "CONSERVATIVE",
    "fee_bps": 7.5,
    "spread_model": "HISTORICAL_75TH_PERCENTILE",
    "slippage_ticks": 2
  },
  "metrics_summary": {
    "gross_sharpe_annualized": 1.85,
    "net_sharpe_annualized": 1.22,
    "max_drawdown_pct": 14.5,
    "total_trades": 642,
    "win_rate_pct": 52.4,
    "profit_factor": 1.38
  },
  "phase6_validation_bridge": {
    "trial_count_k": 42,
    "canonical_dsr_p_value": 0.021,
    "canonical_pbo": 0.12,
    "min_trl_years": 1.8,
    "haircut_sharpe": 1.05
  },
  "verdict": "FAILED_PARAMETER_STABILITY",
  "failure_rationale": "Strategy Sharpe drops from 1.22 to 0.15 when lookback period is adjusted from 20 to 22."
}
```

---

## 13. Definition of "Paper-Ready Candidate"

Passing this validation protocol does **not** grant execution authority. A candidate that successfully navigates all in-sample, out-of-sample, walk-forward, friction-stress, and Phase 6 statistical hurdles is classified strictly as a:

$$\text{\textbf{PAPER-READY RESEARCH CANDIDATE}}$$

### Explicit Invariants
1. **Zero Execution Authorization:** "Paper-Ready" status does **not** mean paper trading is authorized, running, or permitted.
2. **Separation of Governance:** Promotion to actual forward paper trading requires an independent human governance ratification.
3. **Preservation of Phase 13 Requirements:** If authorized by a human, forward testing must complete the mandatory **Phase 13 Step 9 (90-day continuous paper forward run)** with zero real capital before live trading can ever be contemplated.
4. **Anti-Schedule Discipline:** Project management deadlines (e.g. "must deploy strategy by end of month") are strictly prohibited. Research terminates or pauses if hypotheses fail validation.

---

## 14. Pre-Registration Pre-Flight Checklist

Before any empirical backtest code is executed, the researcher must verify and sign off on each item in this checklist:

```markdown
- [ ] 1. Research Question is documented in the Research Backlog without parameter tuning.
- [ ] 2. Economic / Behavioral / Structural mechanism is documented and peer-reviewed.
- [ ] 3. Formal Hypothesis (HYP_###) has been explicitly authorized by human governance.
- [ ] 4. Historical dataset version, checksum, and qualification report are frozen.
- [ ] 5. Instrument universe, timeframe, and calendar normalization are frozen.
- [ ] 6. Train, Validation, and Untouched OOS partition dates are sealed.
- [ ] 7. Information barrier and purging/embargo rules are configured for time-series isolation.
- [ ] 8. Mandatory benchmark baselines (Cash, Buy-and-Hold, Simple Trend) are defined.
- [ ] 9. Base, Conservative, and Stress cost tiers are explicitly configured.
- [ ] 10. Parameter search space bounds, step sizes, and search budget ($K_{\max}$) are frozen.
- [ ] 11. Canonical Phase 6 multiple-testing integration (SearchTrialLedger) is acknowledged.
- [ ] 12. Component ablation testing plan is documented.
- [ ] 13. Pre-empirical falsification and stopping criteria are sealed.
- [ ] 14. OOS failure policy is acknowledged (zero post-hoc tuning on failed OOS data).
- [ ] 15. Clean Git commit hash and execution environment manifest are recorded.
```

---

## 15. Open Human Decisions Register (Validation Protocol)

| Decision ID | Decision Subject | Context | Candidate Alternatives | Status | Human Ratification Required? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VAL-DEC-001** | Canonical OOS Partition Length for Crypto Research | Define standardized duration for the untouched OOS partition in crypto assets. | 6 Months vs. 12 Months vs. 18 Months. | **UNRESOLVED** | **YES** |
| **VAL-DEC-002** | Default Maximum Parameter Search Budget ($K_{\max}$) | Set default upper bound on discrete parameter combinations per formal hypothesis. | $K_{\max} = 50$ vs. $K_{\max} = 100$ vs. $K_{\max} = 250$. | **UNRESOLVED** | **YES** |
| **VAL-DEC-003** | Standardized Walk-Forward Fold Horizon | Ratify default walk-forward retraining frequency for intraday vs. daily strategies. | Quarterly retraining vs. Semi-annual retraining vs. Expanding window. | **UNRESOLVED** | **YES** |
| **VAL-DEC-004** | Execution Latency Standard for M1/M5 Backtests | Define standard simulated latency delay between bar completion and order entry. | Next-bar Open (0 latency) vs. Next-bar Open + 200ms queue penalty. | **UNRESOLVED** | **YES** |

---

## 16. Governance Verification Ledger

- **Implementation Status:** DOCUMENTATION & VALIDATION PROTOCOL DESIGN ONLY (NO CODE MUTATIONS).
- **Hypothesis Creation:** `HYP_003` IS ABSENT / NOT CREATED.
- **Canonical Phase 6 Authority:** FULLY PRESERVED (ZERO MATHEMATICAL MUTATIONS).
- **Backtest / Empirical Execution:** STRICTLY PROHIBITED / NONE EXECUTED.
- **Active G7 Soak Interaction:** ZERO TOUCH / 100% UNTOUCHED.
- **Canonical Capital:** $0.00 (`NO_REAL_ORDERS=true`).
