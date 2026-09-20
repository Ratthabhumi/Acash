# Phase 14 Step R1 Semantic Conformance Record: HYP_005

```text
[HUMAN-RATIFIED CLARIFICATION & SCHEMA ADAPTER RECORD]
[NON-DESTRUCTIVE]
[HYP_005 HASH PRESERVED]
[R1 LINEAGE PRESERVED]
[NO DATA AUTHORITY]
[STEP R2 STILL LOCKED]
[M2 STRESS & M3 PROSPECTIVE STRICTLY SEALED]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/phase14_r1_semantic_conformance_record_HYP_005.md`
- **Subject:** Governance clarification and schema adapter binding for sealed hypothesis `HYP_005` (SPY Noise-Area Intraday Momentum Net-Profitability Replication).
- **Governance Basis:** Human-Ratified Preregistration (`docs/research/MEC-0015-HYP-005-strategy-preregistration.md`, SHA-256: `5036c765cea2f36b95352f5bc0311580c375e8552ec1590c228690b2543cff9e`), Canonical Commit `4ec8e0fcaee73ea8cfbaf71f5d338ef813e1e33d`.
- **Human Authorization:** `AUTHORIZE_HYP_005_INCEPTION_AND_R1_REGISTRATION`.
- **Canonical Git-Tracked Sealed Hypothesis Mirrors:** `docs/phase8.5/hypotheses/HYP_005.json` and `docs/phase14/hypotheses/HYP_005.json`.
- **Canonical Git-Tracked R1 Manifest:** `docs/phase14/manifests/manifest_r1_HYP_005.json`.
- **Authority:** Strict Fail-Closed (`AGENTS.md`). Zero empirical claims, zero market data loaded, zero backtests executed, zero P&L computed.

---

## 1. Context & Purpose

On 2026-09-21, Step R1 successfully registered and sealed `HYP_005` through `ResearchReInceptionGate` under mechanism `MEC-0015`.

`HYP_005` is the first strategy-native executable economic hypothesis in ACASH. Its primary research objective is **net economic performance after realistic transaction friction** (commissions, slippage, SEC Section 31 fees, FINRA TAF, and borrow costs), rather than continuous-factor statistical correlation (such as Rank-IC or OLS t-statistics).

Because the repository's legacy `HypothesisSpecification` model and `ResearchReInceptionGate` validation checks were originally engineered around cross-sectional factor alphas (mandating `target_horizons`, `SplitPolicy`, `invalidation_criteria` with positive Rank-IC, and execution cost models), certain fields were populated using minimal deterministic schema compatibility values to satisfy Pydantic and gate invariants.

To ensure unambiguous interpretation and eliminate semantic debt, this record explicitly establishes the **binding authority precedence** and distinguishes binding scientific specifications from legacy schema compatibility stubs.

---

## 2. Authority Precedence Order

In any situation where an outer model field or generic evaluator encounters an apparent conflict, interpretation **MUST** strictly follow this immutable hierarchy:

1. **Human-Ratified MEC-0015 Strategy Preregistration:**
   `docs/research/MEC-0015-HYP-005-strategy-preregistration.md` (SHA-256: `5036c765cea2f36b95352f5bc0311580c375e8552ec1590c228690b2543cff9e`)
2. **Upstream MEC-0015 Authority Contracts & Manifests:**
   - Intake: `docs/research/MEC-0015-profitability-first-intraday-momentum-intake.md`
   - Strategy Contract Audit: `docs/research/MEC-0015-strategy-contract-audit.md`
   - Friction Contract: `docs/research/MEC-0015-friction-contract.md`
   - Partition Contract: `docs/research/MEC-0015-partition-and-acceptance-contract.md`
   - Provider manifests (`bar`, `dividend`, `quote`) & fee schedules (`sec31`, `finra-taf`)
3. **This HYP_005 R1 Semantic Conformance Record:**
   `docs/phase14/phase14_r1_semantic_conformance_record_HYP_005.md`
4. **Embedded Parameter Configuration JSON:**
   `parameter_config_json` inside the sealed `HypothesisSpecification` artifact
5. **Legacy Schema Compatibility Outer Fields:**
   Top-level Pydantic fields of `HypothesisSpecification` and `ResearchInceptionProposal`

---

## 3. Classification of Fields: Binding Authority vs. Non-Binding Schema Stubs

### 3.1 Binding Research Specifications

| Parameter | Binding Value | Rationale / Authority |
| :--- | :--- | :--- |
| **Research Identity** | Strategy-native intraday momentum net profitability | Replicates Zarattini, Aziz, Barbon (2024) Noise-Area mechanism |
| **Primary Research Objective** | `NET_ECONOMIC_PERFORMANCE_AFTER_REALISTIC_FRICTION` | Evaluates real wealth generation after all institutional transaction costs |
| **Target Instrument** | `SPY` | Consolidated SIP trades, quotes, bars & cash dividends |
| **Session Authority** | NYSE Regular Session (390 standard minutes) | `EARLY_CLOSE_POLICY = EXCLUDE_NON_STANDARD_REGULAR_SESSIONS` |
| **Noise Area Contract** | 14 prior completed sessions lookback | Full 14-session warmup; zero current-session leakage; multiplier = 1.0 |
| **Gap & Anchor Model** | $\text{prev\_close} - \text{cash\_dividend}$ | Upper/Lower anchors bounded by open and dividend-adjusted previous close |
| **VWAP Contract** | Typical Price $(H+L+C)/3$, Cumulative RTH | Daily reset at 09:30; provider `vw` field strictly rejected |
| **Decision Epochs** | 30-minute intervals (10:00 to 15:30 ET) | Alpaca left-edge mapping: epoch $HH:MM \implies$ completed bar $HH:(MM-1)$ |
| **Entry Rules** | Close > UpperBand & Close > VWAP (Long) / Close < LowerBand & Close < VWAP (Short) | `ENTRY_REQUIRES_VWAP_CONFIRMATION = true`; no buffer or optimization |
| **Execution Mechanics** | First valid SIP NBBO at or after boundary ($T$) | Long entry / Short cover fills at Ask; Short entry / Long exit fills at Bid |
| **Adverse Slippage** | $\$0.001 / \text{share}$ per executed side | Standalone adverse execution penalty; spread embedded in NBBO |
| **End-of-Day Policy** | Strictly zero overnight exposure | All open positions flat by 16:00 ET close; frozen EOD semantics |
| **Volatility Sizing** | 15 unadjusted daily close-to-close returns | `ddof=1`, shift 1 ($t-1$), target vol $2.0\%$, max leverage $4.0\times$ |
| **Regulatory Fees** | SEC Section 31 (20 segments, `ROUND_CEILING`) & FINRA TAF (7 tiers, statutory caps) | Exact effective-date schedules applied to sell executions |
| **2× Friction Stress** | $2\times$ commissions + $2\times$ fees + half-spread adverse + 50 bps short borrow stress | Evaluated without double-counting quoted NBBO spread |
| **Primary M1 Acceptance** | Logical AND of all 7 primary gates | Net Return > 0, Sharpe $\ge 1.00$, MDD $\le 30\%$, Trades $\ge 100$, 2× Stress Return > 0, 2× Stress Sharpe $\ge 0.75$ |

---

### 3.2 Non-Binding Schema Compatibility Metadata (Stubs)

The following fields exist exclusively to satisfy Pydantic validation and gate assertions. Downstream execution, evaluation, and reporting harnesses **MUST NOT** derive research semantics from these stubs:

| Field | Outer Schema Value | Classification | Binding Semantic / Invariant |
| :--- | :--- | :--- | :--- |
| `expected_direction` | `ExpectedDirection.LONG` | **NON-BINDING SCHEMA STUB** | HYP_005 executes both long and short intraday positions. This stub does not restrict strategy exposure to long-only. |
| `target_horizons` | `[1]` | **NON-BINDING SCHEMA STUB** | HYP_005 is not a fixed forward-horizon return predictor. Holding durations are dynamic (30 minutes up to session close). |
| `primary_horizon` | `1` | **NON-BINDING SCHEMA STUB** | Do NOT interpret as a 1-minute or 1-day bar forward horizon. |
| `min_in_sample_rank_ic` | `Decimal("0.000001")` | **NON-BINDING SCHEMA STUB** | Rank-IC is irrelevant for an executable trading strategy. Acceptance is governed by net P&L, Sharpe, drawdown, and friction stress. |
| `max_feature_autocorrelation` | `Decimal("0.999999")` | **NON-BINDING SCHEMA STUB** | Satisfies gate threshold; actual time-series dynamics are governed by 14-day noise area and 15-day volatility estimation. |
| `min_cost_adjusted_spread_ratio` | `Decimal("1.0")` | **NON-BINDING SCHEMA STUB** | Satisfies gate threshold; actual cost adjustment is executed via the full institutional friction engine. |
| `cost_model` | All zero (`0.0` bps) | **NON-BINDING SCHEMA STUB** | Legacy cost model is replaced by full `friction_model` specified in `parameter_config_json`. |
| `SplitPolicy` | `60% / 20% / 20%` | **TRANSIENT NON-BINDING STUB** | Governed by partition contract: M1 replication (2007–2024), M2 stress (2024 onward), M3 prospective holdout. |

---

## 4. Governance Invariants Maintained at Step R1

- **HYP_005 Status:** `CREATED_AND_SEALED_R1` (Canonical Ordinal 5).
- **Step R2 Status:** `LOCKED` pending separate explicit Human Authorization for dataset construction.
- **Capital Allocation:** `$0.00` strictly enforced by `InceptionAuthorizationToken`.
- **Trading Execution:** `NO_REAL_ORDERS = true`. Paper trading = `NOT AUTHORIZED`. Live trading = `LOCKED`.
- **Market Data Retrieval:** ZERO operations performed during Step R1.
- **Terminal Hypothesis Protection:** `HYP_003` and `HYP_004` remain permanently closed and enrolled in `TERMINAL_HYPOTHESIS_REGISTRY`.
