# Phase 8.5 Step R1: Canonical Hypothesis Pre-Registration Record (HYP_002)

> **Document ID:** `RECORD-PHASE85-R1-REGISTRATION-HYP-TSMOM-EURUSD-HTF-001`  
> **Timestamp:** `2026-09-07T00:00:00+00:00`  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Canonical Authority, Strict Fail-Closed)  
> **Governing Gate:** `ResearchReInceptionGate` (Gate Decision: `INCEPTION_AUTHORIZED`)  
> **Inception Token ID:** `AUTH_INCEPTION_HYP_TSMOM_EURUSD_HTF_001_dc9eebd1502d7ed4`  
> **Proposal SHA-256:** `dc9eebd1502d7ed4701f9c2edc456d927c0bedc8601940ad26ac1bbed2b15714`  
> **Sealed Hypothesis SHA-256:** `9c8c5e19a87c3780c779c4f4364b80a5f6331c309b011d0318aa5f44cacb8ac9`  
> **R1 Manifest SHA-256:** `0a5159097cbec296b0d2f66cb735011f96a6ee931d0ef7b795eaa77fedcb2e91`  
> **Step R1 Verdict:** `PASS & SEALED`  
> **Next Step:** `STEP R2 (HISTORICAL DATA PREPARATION) — STRICTLY LOCKED`  

---

## 1. Executive Summary & Governance Authority

Following the formal terminal falsification of `HYP_TSMOM_EURUSD_001` on M5, the human governance authority approved the inception of a higher-timeframe time-series momentum hypothesis on EURUSD.

The candidate proposal was submitted to the machine-enforced `ResearchReInceptionGate`, which verified:
1. **New Immutable ID:** `HYP_TSMOM_EURUSD_HTF_001` does not collide with `TERMINAL_HYPOTHESIS_REGISTRY`.
2. **Anti-HARKing Cardinal Equality:** Declared planned trial count ($K=12$) strictly equals search grid cardinality ($6 \times 2 = 12$).
3. **Declarative Data Window:** Proposed calendar window (`2021-01-01` to `2024-12-31`) is completely disjoint from the quarantined 2026 M5 holdout. Zero market-data files were opened or accessed during gate evaluation.
4. **Pre-Registration Completeness:** Economic rationale, causal feature definition, label horizons, strict complement invalidation criteria, and proposed cost models are fully defined.
5. **Decoupled Readiness:** The emitted `InceptionAuthorizationToken` hard-locks capital authority at **`$0.00`** and trading flags at `False`.

The hypothesis specification was compiled, cryptographically hashed, and sealed to disk. **Step R1 is officially COMPLETE & SEALED.**

---

## 2. Canonical Hypothesis Specification DTO

```json
{
  "hypothesis_id": "HYP_TSMOM_EURUSD_HTF_001",
  "hypothesis_version": "v1.0",
  "parent_hypothesis_id": null,
  "economic_rationale": "Higher-timeframe time-series momentum in liquid G10 FX (EURUSD) driven by monetary policy divergence and delayed macroeconomic information diffusion across global institutional participants. Directional price trends over H4 sessions (12h to 20d) exhibit positive persistence where gross price displacements are large enough to comfortably surmount institutional transaction friction.",
  "target_symbol": "EURUSD",
  "feature_dependencies": [
    "lookback_return",
    "close_price"
  ],
  "parameter_config_json": "{\"bar_frequency\":\"H4\",\"cost_model_proposed\":{\"fixed_slippage_bps\":\"0.3\",\"quoted_spread_bps\":\"0.4\",\"roundtrip_broker_fee_bps\":\"0.5\",\"status\":\"PROPOSED_SUBJECT_TO_R2_VERIFICATION\",\"total_friction_bps\":\"1.2\"},\"data_contract_proposed\":{\"canonical_window_utc\":[\"2021-01-01T00:00:00Z\",\"2024-12-31T23:59:59Z\"],\"minimum_usable_h4_bars\":5000,\"split_policy\":{\"embargo_bars\":12,\"oos_pct\":\"0.20\",\"train_pct\":\"0.60\",\"val_pct\":\"0.20\"}},\"deadband_bps_grid\":[3.0,6.0],\"lookback_bars_grid\":[3,6,12,24,48,120],\"nominal_trials_k\":12,\"signal_type\":\"TERNARY_DIRECTIONAL\",\"strategy_id\":\"STRAT-MOM-HTF-H4-V1\"}",
  "expected_direction": "LONG",
  "target_horizons": [
    1,
    6
  ],
  "primary_horizon": 1,
  "invalidation_criteria": {
    "min_in_sample_rank_ic": "0.025",
    "min_hac_t_stat": "2.00",
    "max_feature_autocorrelation": "0.98",
    "min_cost_adjusted_spread_ratio": "1.50"
  },
  "registered_at_utc": "2026-09-07T00:00:00Z",
  "author": "human_governance_auditor"
}
```

---

## 3. Cryptographic Lineage & Sealing Hashes

| Artifact Description | Canonical File Path | Authoritative SHA-256 Digest |
| :--- | :--- | :--- |
| **Inception Proposal Digest** | *In-Memory DTO submitted to Gate* | `dc9eebd1502d7ed4701f9c2edc456d927c0bedc8601940ad26ac1bbed2b15714` |
| **Inception Auth Token** | *Emitted by ResearchReInceptionGate* | `AUTH_INCEPTION_HYP_TSMOM_EURUSD_HTF_001_dc9eebd1502d7ed4` |
| **Sealed Hypothesis Spec** | `./docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_001.json` | `9c8c5e19a87c3780c779c4f4364b80a5f6331c309b011d0318aa5f44cacb8ac9` |
| **R1 Registration Manifest** | `./docs/phase8.5/manifests/manifest_r1_HYP_TSMOM_EURUSD_HTF_001.json` | `0a5159097cbec296b0d2f66cb735011f96a6ee931d0ef7b795eaa77fedcb2e91` |

---

## 4. Anti-HARKing Search Space Geometry ($K=12$)

Under the pre-registered search grid, exactly 12 candidate trials are frozen. All 12 trials must be executed in Step R3:

| Trial ID | Timeframe | Lookback $L$ (Bars) | Lookback (Real Time) | Deadband $\theta$ (bps) | Target Horizon $H$ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `TRIAL-01` | H4 | 3 | $12\text{ hours}$ | $3.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-02` | H4 | 3 | $12\text{ hours}$ | $6.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-03` | H4 | 6 | $24\text{ hours}$ (1 day) | $3.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-04` | H4 | 6 | $24\text{ hours}$ (1 day) | $6.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-05` | H4 | 12 | $48\text{ hours}$ (2 days) | $3.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-06` | H4 | 12 | $48\text{ hours}$ (2 days) | $6.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-07` | H4 | 24 | $96\text{ hours}$ (4 days) | $3.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-08` | H4 | 24 | $96\text{ hours}$ (4 days) | $6.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-09` | H4 | 48 | $192\text{ hours}$ (8 days) | $3.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-10` | H4 | 48 | $192\text{ hours}$ (8 days) | $6.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-11` | H4 | 120 | $480\text{ hours}$ (20 days) | $3.0\text{ bps}$ | 1 bar ($4\text{h}$) |
| `TRIAL-12` | H4 | 120 | $480\text{ hours}$ (20 days) | $6.0\text{ bps}$ | 1 bar ($4\text{h}$) |

---

## 5. Pre-Registered Invalidation Criteria & Boolean Gate

A candidate trial is **QUALIFIED** if and only if **ALL** mandatory criteria pass simultaneously:
$$\mathbf{Qualified \iff (\text{Rank IC} \ge 0.025) \land (t_{\text{HAC}} \ge 2.00) \land (\rho_1 \le 0.98) \land (\overline{\text{Net PnL}} \ge +1.5\text{ bps}) \land (\text{Haircut } SR \ge +0.50)}$$

- **Strict Complement Semantics:**
  - $\text{Rank IC} < 0.025 \implies \text{FAIL}$
  - $t_{\text{HAC}} < 2.00 \implies \text{FAIL}$
  - $\rho_1(s_t) > 0.98 \implies \text{FAIL}$
  - $\overline{\text{Net PnL}} < +1.5\text{ bps} \implies \text{FAIL}$
  - $\text{Haircut } SR < +0.50 \implies \text{FAIL}$
- **Disqualification Rule:** Failure of ANY single mandatory criterion disqualifies the trial.
- **Terminal Falsification Rule:** If $12 / 12$ trials fail to clear this conjunctive gate in Step R3, the hypothesis will be declared **`TERMINALLY_FALSIFIED`** with zero outbound transitions.

---

## 6. Pre-Registered Data Contract (For Future Step R2)

- **Canonical Calendar Research Window:**
  $$\mathbf{2021\text{-}01\text{-}01T00:00:00+00:00 \quad \text{through} \quad 2024\text{-}12\text{-}31T23:59:59+00:00}$$
- **Minimum Usable Observed H4 Bars:**
  $$\mathbf{N_{\text{usable}} \ge 5,000\ H4\ bars}$$
- **Quarantine Boundary:** Completely disjoint from `EURUSD_M5_HOLDOUT` (`2026-08-18` to `2026-09-04`).
- **Partition Ratios:** $60\%$ Train / Census (bars $0$ to $0.60 \times N - 1$), $20\%$ Validation, $20\%$ Blind OOS (with 12-bar embargo).

---

## 7. Evidence Classification Table

| Proposition / Claim | Evidence Classification | Ground Truth Reference |
| :--- | :--- | :--- |
| **Step R1 Registration & Sealing** | **VERIFIED** | Enforced by `ResearchReInceptionGate`; files written on disk |
| **Search Space Cardinal Equality ($K=12$)** | **VERIFIED** | $6 \times 2 = 12$ trials exactly declared and sealed |
| **Quarantine Boundary Isolation** | **VERIFIED** | Window 2021–2024 completely disjoint from 2026 M5 holdout |
| **Zero Market Data Accessed** | **VERIFIED** | Zero Parquet/CSV reads executed |
| **Capital Authority Hard-Lock ($0.00)** | **VERIFIED** | Enforced in `InceptionAuthorizationToken` |
| **Phase 13 Step 8/9 Lock Preservation** | **VERIFIED** | Token grants zero trading authority |
| **Higher-Timeframe Trend Profitability** | **NOT PROVEN** | Unproven until historical dataset is acquired in R2 and evaluated in R3 |

---

## 8. Mandatory Non-Execution Affirmations

- **Zero market data was accessed, read, evaluated, or resampled.**
- **Zero empirical research, backtests, or parameter fits were executed.**
- **The quarantined M5 holdout (bars 6,060..9,999) remains 100% unexposed and pristine.**
- **No broker connections were initialized; zero orders were submitted.**
- **Capital authority remains strictly `$0.00`.**
- **Phase 13 Step 8 and Step 9 remain strictly locked.**
- **Step R2 (Historical Data Preparation) is NOT authorized and remains strictly LOCKED.**

---

## 9. Final Step R1 Verdict

$$\boxed{\mathbf{STEP\ R1\ VERDICT:\ PASS\ \&\ SEALED}}$$

**Hypothesis Registration Certified:**  
`HYP_TSMOM_EURUSD_HTF_001` is officially registered and sealed into the ACASH research ledger.  
**Execution is now immediately STOPPED.** No further actions will be taken until explicit human authorization is granted for Step R2.
