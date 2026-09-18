# Phase 14 Step R1: Canonical Hypothesis Pre-Registration Record (HYP_003)

```text
[STEP R1: PRE-REGISTRATION SEALED]
[RESEARCH RE-INCEPTION GATE: PASS & AUTHORIZED]
[TOKEN: AUTH_INCEPTION_HYP_003_845fda6b9ec7dc77]
[OOS 2023-2026: STRICTLY SEALED / UNREAD]
[STEP R2: DATA QUALIFICATION LOCKED]
[NO EMPIRICAL BACKTEST EXECUTED]
[PAPER/LIVE: STRICTLY LOCKED]
```

- **Document ID:** `docs/phase14/phase14_r1_hypothesis_registration_record_HYP_003.md`
- **Timestamp:** `2026-09-18T23:00:00+00:00`
- **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Canonical Authority, Strict Fail-Closed)
- **Canonical Hypothesis Ordinal:** `HYP_003` (Third Sequential Research Hypothesis)
- **Canonical Hypothesis ID:** `HYP_003`
- **Mechanism Lineage:** `MEC-0013` (Price-Only Opening Range Breakout on SPY)
- **Governing Gate:** `ResearchReInceptionGate` (Gate Decision: `INCEPTION_AUTHORIZED`)
- **Inception Token ID:** `AUTH_INCEPTION_HYP_003_845fda6b9ec7dc77`
- **Proposal SHA-256:** `845fda6b9ec7dc77520c690f7618e86e18484b787db6aa421340ce71e6e55d33`
- **Sealed Hypothesis SHA-256:** `f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0`
- **R1 Manifest SHA-256:** `27952f476cf96f75dc47ca0eb68a4b74d1f8dc6bf2f0848d1a877740cc32b372`
- **Preregistration Spec SHA-256:** `3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c`
- **Step R1 Verdict:** `PASS & SEALED`
- **Next Step:** `STEP R2 (HISTORICAL DATA QUALIFICATION) — STRICTLY LOCKED`

---

## 1. Executive Summary & Governance Authority

Following the formal terminal falsification of `HYP_001` and `HYP_002` under Phase 8.5, and the ratification of Decision `D-PREREG-1 (Option A)` and Decision `D-EMP-1 (Option A)` under Phase 14, the Human Operator explicitly authorized:
1. Formal submission of the frozen `MEC-0013` price-only ORB proposal to `ResearchReInceptionGate`.
2. Mechanical evaluation of all 6 institutional invariants.
3. Sealing of the canonical hypothesis specification `HYP_003` upon a gate `PASS`.

### Invariant Verification Results:
- **Invariant 1 (Identity & Immutability):** `HYP_003` matches pattern `^HYP_[A-Z0-9_]+$`. Not in `TERMINAL_HYPOTHESIS_REGISTRY`. No collision with existing sealed files. **VERIFIED PASS**.
- **Invariant 2 (Anti-HARKing Cardinal Equality):** `parameter_search_grid` contains 2 OR windows (5m, 15m) $\times$ 2 directions (LONG, SHORT) = 4 combinations. Declared `planned_trial_count = 4`. Equality strictly satisfied ($K = 4$). **VERIFIED PASS**.
- **Invariant 3 (Declarative Data Contract & Quarantine):** Instrument is `SPY` at `1m` timeframe. Proposed data window is `2017-01-01T00:00:00+00:00` to `2022-12-31T23:59:59+00:00` (In-Sample only). Does not overlap with EURUSD quarantined holdouts. Out-of-Sample window (`2023–2026`) is strictly sealed and unread. **VERIFIED PASS**.
- **Invariant 4 (Pre-Registration Completeness):** Structural economic rationale is 388 characters ($\ge 20$). Non-empty feature dependencies (`["opening_range_high", "opening_range_low", "bar_close"]`). Target horizons defined (`[1, 390]`, `primary_horizon = 390`). Invalidation criteria strictly positive (`min_in_sample_rank_ic = 0.010`, `min_hac_t_stat = 1.50`). Realistic cost model specified (1.6 bps roundtrip fee + 1.0 bps adverse slippage). **VERIFIED PASS**.
- **Invariant 5 (Decoupled Readiness):** Inception Authorization Token hard-locks `capital_authority_usd == $0.00`, `is_strategy_qualified == False`, `is_paper_authorized == False`, `is_live_authorized == False`. **VERIFIED PASS**.
- **Invariant 6 (Zero Data / Execution Access):** Evaluation performed zero market data reads, zero CSV/Parquet reads, zero network calls, and zero backtest execution. **VERIFIED PASS**.

---

## 2. Canonical Hypothesis Specification DTO

```json
{
  "hypothesis_id": "HYP_003",
  "hypothesis_version": "v1.0",
  "parent_hypothesis_id": null,
  "economic_rationale": "Opening Range Breakout (ORB) in US benchmark equity ETF (SPY) under MEC-0013 price-only mechanics. Early regular-session price discovery establishes an initial range reflecting overnight order assimilation and opening auction balance; completed 1-minute close-through breakouts beyond this range capture directional momentum driven by institutional order flow imbalance through the remainder of the regular trading session.",
  "target_symbol": "SPY",
  "feature_dependencies": [
    "opening_range_high",
    "opening_range_low",
    "bar_close"
  ],
  "parameter_config_json": "{\"all_14_frozen_parameters\":{\"10_closing_auction_handling\":\"EXCLUDE_1600_BAR_EXIT_1559_CLOSE\",\"11_is_oos_partition\":{\"in_sample_dates\":[\"2017-01-01\",\"2022-12-31\"],\"oos_state\":\"SEALED_UNREAD\",\"out_of_sample_dates\":[\"2023-01-01\",\"2026-12-31\"]},\"12_embargo_purge_days\":0,\"13_data_quality_threshold\":\"100% COMPLETE CA-1 390-MINUTE GRID\",\"14_session_exclusion_policy\":\"REGULAR 390-MIN SESSIONS ONLY\",\"1_breakout_confirmation\":\"CLOSE-THROUGH\",\"2_entry_timing\":\"NEXT-BAR OPEN\",\"3_directional_lane\":\"SYMMETRIC LONG + SHORT\",\"4_stop_loss_rule\":\"OPPOSITE OPENING-RANGE BOUNDARY\",\"5_exit_holding_horizon\":\"END-OF-DAY FLATTEN\",\"6_transaction_cost_bps\":\"1.6 bps ROUND-TRIP (0.8 entry + 0.8 exit)\",\"7_slippage_bps\":\"0.5 bps ADVERSE PER SIDE (1.0 roundtrip)\",\"8_execution_price_convention\":\"CONSERVATIVE_EXECUTABLE\",\"9_opening_auction_handling\":\"INCLUDE_0930_BAR\"},\"bar_frequency\":\"1m\",\"calendar_authority\":{\"authority_code\":\"CA-1\",\"calendar_name\":\"NyseCa1Calendar\",\"regular_session_bars\":390,\"timezone\":\"America/New_York\"},\"data_contract\":{\"adjustment\":\"raw\",\"d13_status\":\"PARTIALLY RESOLVED (AVAILABILITY/DEPTH: RETIRED; PIT/VINTAGE: OPEN)\",\"d14_status\":\"BLOCKED (AUTHORITY-CONDITIONAL / DECOUPLED FROM PRICE-ONLY LANE)\",\"feed\":\"sip\",\"symbol\":\"SPY\",\"timeframe\":\"1Min\"},\"governance_lineage\":{\"freeze_ratification\":\"D-PREREG-1 (Option A, 2026-09-18)\",\"hypothesis_ordinal\":3,\"hypothesis_ordinal_alias\":\"HYP_003\",\"inception_token_id\":\"AUTH_INCEPTION_HYP_003_845fda6b9ec7dc77\",\"preregistration_doc\":\"docs/phase14/mec_0013_price_only_preregistration.md\",\"preregistration_sha256\":\"3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c\",\"proposal_sha256\":\"845fda6b9ec7dc77520c690f7618e86e18484b787db6aa421340ce71e6e55d33\",\"source_git_sha\":\"5ec7d8b52333c71ab89b32426e4f80bd1aea2784\",\"validation_auth\":\"D-EMP-1 (Option A, 2026-09-18)\"},\"mechanism_id\":\"MEC-0013\",\"nominal_trials_k\":4,\"primary_cells\":[{\"cell_id\":\"ORB_5M_LONG\",\"direction\":\"LONG\",\"opening_range_minutes\":5},{\"cell_id\":\"ORB_5M_SHORT\",\"direction\":\"SHORT\",\"opening_range_minutes\":5},{\"cell_id\":\"ORB_15M_LONG\",\"direction\":\"LONG\",\"opening_range_minutes\":15},{\"cell_id\":\"ORB_15M_SHORT\",\"direction\":\"SHORT\",\"opening_range_minutes\":15}],\"signal_type\":\"PRICE_ONLY_OPENING_RANGE_BREAKOUT\",\"strategy_id\":\"STRAT-ORB-SPY-PRICE-ONLY-V1\"}",
  "expected_direction": "LONG",
  "target_horizons": [
    1,
    390
  ],
  "primary_horizon": 390,
  "invalidation_criteria": {
    "min_in_sample_rank_ic": "0.01",
    "min_hac_t_stat": "1.5",
    "max_feature_autocorrelation": "0.98",
    "min_cost_adjusted_spread_ratio": "1.50"
  },
  "registered_at_utc": "2026-09-18T23:00:00Z",
  "author": "human_operator_ratified"
}
```

---

## 3. Bound Primary Hypothesis Census ($K = 4$)

The primary research grid is bounded strictly to 4 cells:

| Cell ID | Opening Range Window | Direction | Local Time Window (ET) | Bar Count in OR | Primary Evaluation Horizon |
|---|---|---|---|---|---|
| `ORB_5M_LONG` | 5 minutes | LONG | `09:30:00` to `09:35:00` | 5 bars (`09:30`–`09:34`) | EOD Flatten (15:59 ET) |
| `ORB_5M_SHORT` | 5 minutes | SHORT | `09:30:00` to `09:35:00` | 5 bars (`09:30`–`09:34`) | EOD Flatten (15:59 ET) |
| `ORB_15M_LONG` | 15 minutes | LONG | `09:30:00` to `09:45:00` | 15 bars (`09:30`–`09:44`) | EOD Flatten (15:59 ET) |
| `ORB_15M_SHORT` | 15 minutes | SHORT | `09:30:00` to `09:45:00` | 15 bars (`09:30`–`09:44`) | EOD Flatten (15:59 ET) |

*Anti-HARKing Rule:* No candidate cell may be added, deleted, or selectively pruned following empirical observation.

---

## 4. Preservation of All 14 Frozen Parameters

| # | Parameter | Frozen Value Bound in HYP_003 | Lineage / Authority |
|---|---|---|---|
| 1 | Breakout Confirmation | `CLOSE-THROUGH` | `Close_t > OR_high` (Long), `Close_t < OR_low` (Short). No intrabar wicks. |
| 2 | Entry Timing | `NEXT-BAR OPEN` | Execution simulated at `Open(t+1)`. No same-bar fills. |
| 3 | Directional Lane | `SYMMETRIC LONG + SHORT` | Both directions primary and reported independently. |
| 4 | Stop-Loss Rule | `OPPOSITE OPENING-RANGE BOUNDARY` | Long Stop: `OR_low`; Short Stop: `OR_high`. Fixed throughout trade. |
| 5 | Exit / Holding Horizon | `END-OF-DAY FLATTEN` | Exit on final eligible regular-session minute (`15:59 ET`). |
| 6 | Transaction Cost Model | `1.6 bps ROUND-TRIP` | Deterministic research friction: 0.8 bps entry + 0.8 bps exit. |
| 7 | Slippage Model | `0.5 bps ADVERSE PER SIDE` | 0.5 bps adverse per entry/exit (1.0 bps roundtrip). |
| 8 | Execution Price Convention | `CONSERVATIVE_EXECUTABLE` | Entry `Open(t+1)`; Stop worse of stop vs observable; EOD `Close(15:59 ET)`. |
| 9 | Opening Auction Handling | `INCLUDE 09:30 ET BAR` | Commences official CA-1 trading grid. |
| 10 | Closing Auction Handling | `EXCLUDE 16:00 ET+ BARS` | EOD flatten uses `15:59 ET` close; `16:00 ET` cross excluded. |
| 11 | IS / OOS Partitions | `2017–2022 IS / 2023–2026 OOS` | IS active; OOS strictly sealed and unread. |
| 12 | Embargo / Purge Rules | `0 TRADING DAYS` | Intraday only; zero multi-day overnight inventory. |
| 13 | Data Quality Threshold | `100% COMPLETE CA-1 GRID` | Exactly 390 bars per regular session. |
| 14 | Session Exclusion Policy | `REGULAR 390-MIN SESSIONS ONLY` | Excludes 13:00 ET early closes, holidays, and incomplete sessions. |

---

## 5. Explicit Quarantine & Sealing Verification
- **In-Sample Period:** `2017-01-01` through `2022-12-31` (Authorized for Step R2 data qualification).
- **Out-of-Sample Period:** `2023-01-01` through `2026-12-31` (100% Sealed / Unread).
- **Zero Market Data Touch:** During Step R1 registration, zero market data was queried, downloaded, or loaded into memory.
- **Zero Backtests Executed:** Step R1 constitutes hypothesis pre-registration and sealing only.

---

## 6. Preserved Governance State

| Boundary Dimension | State Post-R1 Sealing | Authority / Source |
|---|---|---|
| **D-EMP-1 Status** | `RATIFIED — OPTION A` | Human Decision `D-EMP-1` |
| **Research Re-Inception Gate** | `PASS & AUTHORIZED` | Token `AUTH_INCEPTION_HYP_003_845fda6b9ec7dc77` |
| **Step R1 Status** | `COMPLETE & SEALED` | Specification `HYP_003.json` |
| **Step R2 (Data Prep)** | `STRICTLY LOCKED` | Requires explicit acquisition step |
| **Empirical Backtesting** | `NOT EXECUTED / LOCKED` | No empirical code run |
| **OOS Partition (`2023–2026`)** | `STRICTLY SEALED` | Immutable holdout discipline |
| **MEC-0013 Status** | `ARCHIVED` / `NOT PROMOTED` | Decisions `MEC-0013-D01`, `MEC-0013-D02` |
| **Paper Trading** | `NOT AUTHORIZED` | Gate 4 clearance required |
| **Live Trading** | `STRICTLY LOCKED` | `capital = $0.00`, `NO_REAL_ORDERS = true` |

---

### Verification Ledger
- Implementation Status: COMPLETE (HYP_003 Evaluated, Authorized, Registered, and Sealed)
- Contract Enforcement: STRICT FAIL-CLOSED (All 6 Re-Inception Invariants passed; zero market data loaded)
- Mathematical Authority: RESEARCH RE-INCEPTION GATE (Inception Token emitted)
- Local Test Suite: VERIFIED (15/15 Re-Inception Gate unit tests passed)
- Type Checker (MyPy): VERIFIED
- Remote CI Status: NOT APPLICABLE (Local governance sealing)
- Methodological Caveats: Step R1 pre-registration complete; empirical data acquisition (Step R2) and backtesting remain strictly locked.
