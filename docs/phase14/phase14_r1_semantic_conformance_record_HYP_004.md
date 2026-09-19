# Phase 14 Step R1 Semantic Conformance Record: HYP_004

```text
[HUMAN-RATIFIED CLARIFICATION & SCHEMA ADAPTER RECORD]
[NON-DESTRUCTIVE]
[HYP_004 HASH PRESERVED]
[R1 LINEAGE PRESERVED]
[NO DATA AUTHORITY]
[STEP R2 STILL LOCKED]
[OOS 2023-2026 STRICTLY SEALED]
```

- **Document ID:** `docs/phase14/phase14_r1_semantic_conformance_record_HYP_004.md`
- **Subject:** Governance clarification and schema adapter binding for sealed hypothesis `HYP_004` (Market Intraday Momentum: Gao Baseline Predictive-Relation Econometric Replication on `SPY`).
- **Governance Basis:** Human-Ratified Preregistration (`docs/research/MEC-0014A-statistical-preregistration-draft.md`, SHA-256: `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce`), Canonical Commit `ccd42a50be935cacb22b7681d5b806c449495057`.
- **Canonical Git-Tracked Sealed Hypothesis Mirrors:** `docs/phase8.5/hypotheses/HYP_004.json` and `docs/phase14/hypotheses/HYP_004.json`.
- **Local Runtime / Gitignored Hypothesis Mirror:** `data/manifests/research/hypotheses/HYP_004.json` (reproducible from registration script; excluded by `.gitignore`).
- **Canonical Git-Tracked R1 Manifest:** `docs/phase14/manifests/manifest_r1_HYP_004.json`.
- **Local Runtime / Gitignored Manifest Mirror:** `data/manifests/research/manifest_r1_HYP_004.json` (reproducible from registration script; excluded by `.gitignore`).
- **Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`).
- **Authority:** Strict Fail-Closed (`AGENTS.md`). Zero empirical claims, zero market data loaded, zero backtests executed, OOS strictly sealed.

---

## 1. Context & Purpose

On 2026-09-19, Step R1 successfully registered and sealed `HYP_004` through `ResearchReInceptionGate` under the human-ratified statistical specification for `MEC-0014A`.

Because the repository's legacy `HypothesisSpecification` model and `ResearchReInceptionGate` validation checks were originally engineered around continuous-factor predictive rankings and algorithmic trading execution (e.g. mandatory `target_horizons`, `SplitPolicy`, `invalidation_criteria` with positive Rank-IC, and execution cost models), certain fields were populated using minimal deterministic schema compatibility values to satisfy Pydantic and gate invariants.

To prevent any future semantic debt, ambiguity, or downstream misinterpretation, this record explicitly establishes the **binding authority precedence** and classifies all fields at inception.

---

## 2. Authority Precedence Order

In any situation where an outer model field or generic evaluator encounters an apparent conflict, interpretation **MUST** strictly follow this immutable hierarchy:

1. **Human-Ratified MEC-0014A Statistical Preregistration:**
   `docs/research/MEC-0014A-statistical-preregistration-draft.md` (SHA-256: `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce`)
2. **This HYP_004 R1 Semantic Conformance Record:**
   `docs/phase14/phase14_r1_semantic_conformance_record_HYP_004.md`
3. **Embedded Parameter Configuration JSON:**
   `parameter_config_json` inside the sealed `HypothesisSpecification` artifact
4. **Legacy Schema Compatibility Outer Fields:**
   Top-level Pydantic fields of `HypothesisSpecification` and `ResearchInceptionProposal`

---

## 3. Classification of Fields: Binding Authority vs. Non-Binding Schema Stubs

### 3.1 Binding Research Specifications

| Parameter | Binding Value | Rationale / Authority |
| :--- | :--- | :--- |
| **Research Identity** | Gao Baseline Predictive-Relation Econometric Replication | Econometric test of $r_{13,t} = \alpha + \beta r_{1,t} + \varepsilon_t$ |
| **Expected Direction (`expected_direction`)** | `ExpectedDirection.LONG` $\equiv \beta_{r_1} > 0$ | Represents positive regression slope; grants **ZERO** trading/long position authority |
| **Predictor Variable ($r_{1,t}$)** | Simple return: $p_{1,t} / p_{0,t} - 1$ | From previous regular-session close ($p_{0,t}$) through 10:00 ET ($p_{1,t}$); includes overnight |
| **Target Variable ($r_{13,t}$)** | Simple return: $p_{13,t} / p_{12,t} - 1$ | From 15:30 ET ($p_{12,t}$) through 16:00 ET closing auction ($p_{13,t}$) |
| **Primary Acceptance Criterion** | $\hat{\beta}_{r_1} > 0 \text{ AND } \text{two-sided NW-HAC } p < 0.05$ | Immutably locked prior to observing returns; no alternative significance threshold permitted |
| **Newey-West HAC Lag Rule** | $L = \lfloor 4 \cdot (T / 100)^{2/9} \rfloor$ | Deterministic non-parametric bandwidth rule frozen pre-execution |
| **Daily Trade-Count Filter** | $\ge 500$ raw regular-session SIP trades | $09:30:00 \le \text{timestamp} \le 16:00:00 \text{ ET}$ (`ACASH_PROVIDER_OPERATIONALIZATION_CHOICE`) |
| **Intraday Endpoint Rule** | `QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY` | Distinct-price fail-closed rule; no trade ID tie-breaking |
| **Closing Auction Authority** | Unique NYSE Arca $x=P, c=6$ print | $1498/1498$ complete normal path verified |
| **Replication Sample Partition** | `2017-01-01` through `2022-12-31` | `MEC_0014A_MECHANISM_SPECIFIC_REPLICATION_SAMPLE` |
| **External Holdout** | `2023-01-01` through `2026-12-31` | `SEALED_UNREAD` (Technical infrastructure probes disclosed; zero strategy exposure) |

---

### 3.2 Non-Binding Schema Compatibility Metadata (Stubs)

The following fields exist exclusively to satisfy Pydantic validation and gate assertions. Downstream execution, evaluation, and reporting harnesses **MUST NOT** derive research semantics from these stubs:

| Field | Outer Schema Value | Classification | Binding Semantic / Invariant |
| :--- | :--- | :--- | :--- |
| `target_horizons` | `[1]` | **NON-BINDING SCHEMA STUB** | MEC-0014A is not a fixed-horizon forward-return model. Binding target is $r_{13,t}$ (15:30–16:00 ET). |
| `primary_horizon` | `1` | **NON-BINDING SCHEMA STUB** | Do NOT interpret as 1-minute or 1-day bar forward horizon. |
| `min_in_sample_rank_ic` | `Decimal("0.000001")` | **NON-BINDING SCHEMA STUB** | Rank-IC is not a metric of interest for MEC-0014A. Primary acceptance evaluates OLS $\hat{\beta}_{r_1}$ and HAC $p$-value. |
| `max_feature_autocorrelation`| `Decimal("0.999999")` | **NON-BINDING SCHEMA STUB** | Satisfies gate threshold; actual time-series correlation is handled via Newey-West HAC covariance. |
| `min_cost_adjusted_spread_ratio` | `Decimal("1.0")` | **NON-BINDING SCHEMA STUB** | Economic cost qualification is out of scope for MEC-0014A; belongs to MEC-0014B. |
| `cost_model` | All zero (`0.0` bps) | **NON-BINDING SCHEMA STUB** | Statistical replication only; zero trading fees/slippage assumed because no trades are executed. |
| `SplitPolicy` | `60% / 20% / 20%` | **TRANSIENT NON-BINDING STUB** | Does not govern MEC-0014A. Primary test is evaluated on full 2017–2022 in-sample replication sample; secondary OOS uses 2017–2019 init / 2020–2022 eval. The 20% schema OOS is NOT canonical holdout. |

---

## 4. Governance Invariants Maintained at Step R1

- **HYP_004 Status:** `CREATED & SEALED` (Canonical Ordinal 4).
- **Step R2 Status:** `LOCKED` pending separate explicit Human Authorization for dataset construction.
- **Capital Allocation:** `$0.00` strictly enforced by `InceptionAuthorizationToken`.
- **Trading Execution:** `NO_REAL_ORDERS = true`. Paper trading = `NOT AUTHORIZED`. Live trading = `LOCKED`.
- **Market Data Retrieval:** ZERO operations performed during Step R1.
- **Out-of-Sample Window ($\ge 2023-01-01$):** Strictly sealed and untouched.
- **Terminal Hypothesis Protection:** `HYP_003` permanently registered in `TERMINAL_HYPOTHESIS_REGISTRY`.
