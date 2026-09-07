"""Phase 8.5 Step R3 — In-Sample Search Census Execution Script (HYP_002).

HUMAN AUTHORIZATION: EXPLICITLY GRANTED FOR STEP R3 ONLY.
SCOPE: IN-SAMPLE BARS 0..3,738 ONLY. VALIDATION AND OOS MUST REMAIN PRISTINE.

Strictly enforces:
1. Loads and cryptographically verifies sealed R1 hypothesis (HYP_TSMOM_EURUSD_HTF_002).
2. Loads and verifies canonical R2 dataset (DS_EURUSD_H4_2021_2024_CANONICAL).
3. Constrains ALL computation to in-sample bars 0..3,738 only.
4. Executes all K=12 pre-registered trials over the frozen Cartesian product:
   lookbacks [3,6,12,24,48,120] x deadbands [3.0,6.0] bps
5. Per trial computes:
   - Rank IC (Spearman)
   - HAC t-statistic (Bartlett kernel, Newey-West bandwidth)
   - Signal autocorrelation rho_1
   - Average net trade PnL in bps (after 1.2 bps total roundtrip friction)
   - Haircut Sharpe (annualized, H4 bars)
6. Applies conjunctive 5-gate qualification:
   Rank IC >= 0.025 AND HAC t >= 2.00 AND rho_1 <= 0.98
   AND Net PnL >= +1.5 bps AND Haircut Sharpe >= +0.50
7. Builds and seals SearchTrialLedger with cryptographic lineage.
8. Generates R3 census report, manifest, and provenance.
9. STOPS immediately. No OOS. No trading.

SAFETY INVARIANTS ENFORCED:
- Capital Authority = $0.00 (no broker connection, no orders)
- Validation (3,751..4,996) = UNTOUCHED
- Blind OOS (5,009..6,230) = UNTOUCHED
- 2026 M5 Holdout = UNTOUCHED
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.provenance import calculate_canonical_batch_sha256
from acash.research.evaluation import (
    calculate_spearman_rank_ic,
    calculate_autocorrelation,
    compute_ols_beta_and_hac,
    determine_hac_bandwidth,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import (
    CostModelConfig,
    HacBandwidthMethod,
    HacInferencePolicy,
    HypothesisSpecification,
)
from acash.validation.schema import (
    SearchTrialLedger,
    SearchTrialRecord,
    SharpeSpace,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HYPOTHESIS_ID = "HYP_TSMOM_EURUSD_HTF_002"
STRATEGY_ID = "STRAT-MOM-HTF-H4-V1"
HYPOTHESIS_SHA256 = "47c077a65f3057ae5ec83c8e7cf9179ababea9e5b18bc999bdc480a44f544afe"
DATASET_ID = "DS_EURUSD_H4_2021_2024_CANONICAL"

# Pre-registered frozen search geometry (IMMUTABLE — DO NOT MODIFY)
LOOKBACK_BARS_GRID = [3, 6, 12, 24, 48, 120]
DEADBAND_BPS_GRID = [3.0, 6.0]
K_NOMINAL = 12  # Exactly 12 trials by construction

# In-sample partition (ONLY these bars may be used in R3)
INSAMPLE_START_IDX = 0
INSAMPLE_END_IDX = 3738  # Inclusive — bars 0..3,738

# Validation / OOS partition indices — must remain untouched
VALIDATION_START_IDX = 3751
VALIDATION_END_IDX = 4996
OOS_START_IDX = 5009
OOS_END_IDX = 6230

# Cost model (PROPOSED research assumption — do NOT silently recalibrate)
QUOTED_SPREAD_BPS = Decimal("0.4")
ROUNDTRIP_FEE_BPS = Decimal("0.5")
FIXED_SLIPPAGE_BPS = Decimal("0.3")
TOTAL_FRICTION_BPS = QUOTED_SPREAD_BPS + ROUNDTRIP_FEE_BPS + FIXED_SLIPPAGE_BPS  # = 1.2 bps

# Annualization: EURUSD H4 bars per year (252 trading days * 6 bars/day)
H4_BARS_PER_YEAR = 252 * 6  # = 1512

# Qualification gate thresholds (from sealed HYP_002 spec — immutable)
GATE_MIN_RANK_IC = Decimal("0.025")
GATE_MIN_HAC_T = Decimal("2.00")
GATE_MAX_RHO1 = Decimal("0.98")
GATE_MIN_NET_PNL_BPS = Decimal("1.5")
GATE_MIN_HAIRCUT_SHARPE = Decimal("0.50")


# ---------------------------------------------------------------------------
# Helper: Load HypothesisSpecification from typed canonical JSON
# ---------------------------------------------------------------------------

def _load_hypothesis_spec(path: Path) -> HypothesisSpecification:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw.get("expected_direction"), dict) and "__type__" in raw.get("expected_direction", {}):
        clean_dict = {
            "hypothesis_id": raw["hypothesis_id"],
            "hypothesis_version": raw["hypothesis_version"],
            "parent_hypothesis_id": raw.get("parent_hypothesis_id"),
            "economic_rationale": raw["economic_rationale"],
            "target_symbol": raw["target_symbol"],
            "feature_dependencies": raw["feature_dependencies"],
            "parameter_config_json": raw["parameter_config_json"],
            "expected_direction": raw["expected_direction"]["value"],
            "target_horizons": [x["value"] if isinstance(x, dict) else x for x in raw["target_horizons"]],
            "primary_horizon": raw["primary_horizon"]["value"] if isinstance(raw["primary_horizon"], dict) else raw["primary_horizon"],
            "invalidation_criteria": {k: v["value"] if isinstance(v, dict) else v for k, v in raw["invalidation_criteria"].items()},
            "registered_at_utc": raw["registered_at_utc"],
            "author": raw["author"],
        }
        return HypothesisSpecification.model_validate(clean_dict)
    return HypothesisSpecification.model_validate(raw)


# ---------------------------------------------------------------------------
# Helper: Compute Haircut Sharpe
# ---------------------------------------------------------------------------

def compute_haircut_sharpe(
    net_returns: np.ndarray,
    bars_per_year: int = H4_BARS_PER_YEAR,
) -> float:
    """Compute annualized Sharpe ratio = mean / std * sqrt(bars_per_year).
    No haircut deflation applied here — DSR / Bonferroni haircut applied at Phase 6.
    'Haircut Sharpe' in R3 context = Annualized IS Sharpe as per spec.
    """
    n = len(net_returns)
    if n < 2:
        return 0.0
    mu = float(np.mean(net_returns))
    sigma = float(np.std(net_returns, ddof=1))
    if sigma < 1e-12:
        return 0.0
    return (mu / sigma) * math.sqrt(bars_per_year)


# ---------------------------------------------------------------------------
# Helper: Compute return series SHA-256
# ---------------------------------------------------------------------------

def _compute_series_sha256(returns_dec: List[Decimal]) -> str:
    from acash.validation.gate import _compute_canonical_series_sha256
    return _compute_canonical_series_sha256(returns_dec)


# ---------------------------------------------------------------------------
# Main R3 Census Execution
# ---------------------------------------------------------------------------

def run_step_r3_census() -> Dict[str, Any]:
    print("=" * 80)
    print("ACASH PHASE 8.5 STEP R3 — IN-SAMPLE SEARCH CENSUS")
    print(f"Hypothesis: {HYPOTHESIS_ID} (Ordinal HYP_002)")
    print(f"Dataset: {DATASET_ID}")
    print(f"Authorized Scope: In-Sample ONLY — Bars {INSAMPLE_START_IDX}..{INSAMPLE_END_IDX}")
    print(f"Search Geometry: K={K_NOMINAL} trials (lookbacks × deadbands)")
    print("=" * 80)

    # -----------------------------------------------------------------------
    # Gate 0: Upstream Hypothesis Integrity
    # -----------------------------------------------------------------------
    print("\n[Gate 0] Upstream Hypothesis Integrity:")
    hyp_path = Path("docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_002.json")
    if not hyp_path.exists():
        raise DataContractError(f"Hypothesis file not found: {hyp_path}")

    hyp_spec = _load_hypothesis_spec(hyp_path)
    computed_digest = calculate_hypothesis_spec_sha256(hyp_spec)
    if computed_digest != HYPOTHESIS_SHA256:
        raise DataContractError(
            f"HYPOTHESIS_DIGEST_MISMATCH: computed {computed_digest} != expected {HYPOTHESIS_SHA256}"
        )
    print(f" -> Hypothesis ID: {hyp_spec.hypothesis_id}")
    print(f" -> Digest: {computed_digest}")
    print(" -> Status: PASS (Bit-for-bit sealed)")

    # -----------------------------------------------------------------------
    # Gate 1: Load and verify canonical R2 dataset
    # -----------------------------------------------------------------------
    print("\n[Gate 1] Canonical R2 Dataset Integrity:")
    manifest_path = Path("data/manifests/research/manifest-EURUSD_H4_2021_2024_canonical.json")
    if not manifest_path.exists():
        raise DataContractError(f"R2 manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        r2_manifest = json.load(f)

    parquet_path = Path("data/parquet/research/EURUSD_H4_2021_2024_canonical.parquet")
    if not parquet_path.exists():
        raise DataContractError(f"Canonical parquet not found: {parquet_path}")

    full_table = pq.read_table(parquet_path)
    total_bars = full_table.num_rows
    assert total_bars == 6231, f"Expected 6231 bars, got {total_bars}"

    # Verify canonical batch hash
    computed_canonical_sha = calculate_canonical_batch_sha256(full_table)
    expected_canonical_sha = r2_manifest["digests"]["canonical_batch_sha256"]
    if computed_canonical_sha != expected_canonical_sha:
        raise DataContractError(
            f"CANONICAL_BATCH_SHA256_MISMATCH: computed {computed_canonical_sha} != expected {expected_canonical_sha}"
        )
    print(f" -> Total bars in dataset: {total_bars}")
    print(f" -> Canonical Batch SHA-256: {computed_canonical_sha}")
    print(" -> Status: PASS (Dataset integrity verified)")

    # -----------------------------------------------------------------------
    # Gate 2: Strict OOS Isolation (extract in-sample slice only)
    # -----------------------------------------------------------------------
    print(f"\n[Gate 2] In-Sample Slice Isolation (bars {INSAMPLE_START_IDX}..{INSAMPLE_END_IDX}):")

    # Strict boundary assertions — fail-closed on any accidental exposure
    INSAMPLE_COUNT = INSAMPLE_END_IDX - INSAMPLE_START_IDX + 1  # = 3739

    # Extract ONLY in-sample rows — never load validation or OOS
    is_table = full_table.slice(INSAMPLE_START_IDX, INSAMPLE_COUNT)
    assert is_table.num_rows == INSAMPLE_COUNT, (
        f"In-sample slice wrong size: {is_table.num_rows} != {INSAMPLE_COUNT}"
    )

    # Verify that this slice does NOT touch any OOS bars
    assert INSAMPLE_END_IDX < VALIDATION_START_IDX, (
        f"SAFETY VIOLATION: In-sample end {INSAMPLE_END_IDX} >= validation start {VALIDATION_START_IDX}"
    )

    print(f" -> In-Sample Bar Count: {INSAMPLE_COUNT}")
    print(f" -> Validation Partition ({VALIDATION_START_IDX}..{VALIDATION_END_IDX}): UNTOUCHED")
    print(f" -> Blind OOS Partition ({OOS_START_IDX}..{OOS_END_IDX}): UNTOUCHED")
    print(" -> Status: PASS (OOS isolation enforced)")

    # Extract price arrays from in-sample slice only
    closes_raw = is_table["close"].to_pylist()
    opens_raw = is_table["open"].to_pylist()
    closes = np.array([float(c) for c in closes_raw], dtype=np.float64)
    opens = np.array([float(o) for o in opens_raw], dtype=np.float64)
    N_is = len(closes)

    # -----------------------------------------------------------------------
    # Gate 3: Execute 12 Pre-Registered Trials (frozen Cartesian product)
    # -----------------------------------------------------------------------
    print(f"\n[Gate 3] Executing K={K_NOMINAL} Pre-Registered Trials:")
    print(f" -> Lookbacks: {LOOKBACK_BARS_GRID}")
    print(f" -> Deadbands: {DEADBAND_BPS_GRID} bps")
    print(f" -> Primary Horizon H: {hyp_spec.primary_horizon} (next-bar)")
    print(f" -> Cost Model: {TOTAL_FRICTION_BPS} bps total roundtrip (PROPOSED RESEARCH ASSUMPTION)")

    trial_results: List[Dict[str, Any]] = []
    trial_records: List[SearchTrialRecord] = []
    trial_number = 0

    for lookback in LOOKBACK_BARS_GRID:
        for deadband_bps in DEADBAND_BPS_GRID:
            trial_number += 1
            trial_id = f"TRIAL-{trial_number:02d}"

            # ----------------------------------------------------------------
            # Feature Construction: Lookback momentum X_t = (C_t - C_{t-L}) / C_{t-L}
            # Strictly causal: uses only C_t and prior closes (no look-ahead)
            # ----------------------------------------------------------------
            feature_start = lookback  # First valid index where C[t - lookback] exists
            T_eff = N_is - lookback   # Number of valid feature observations
            H = hyp_spec.primary_horizon  # H=1: next bar open-to-close

            if T_eff < 10:
                raise DataContractError(
                    f"Trial {trial_id}: insufficient observations T_eff={T_eff} for lookback={lookback}"
                )

            # X_t = (C[t] - C[t - L]) / C[t - L] — causal at t
            X_raw = np.array([
                (closes[t] - closes[t - lookback]) / closes[t - lookback]
                for t in range(lookback, N_is)
            ], dtype=np.float64)

            # ----------------------------------------------------------------
            # Forward Return: R(t, H=1) = (C[t+1] - O[t+1]) / O[t+1]
            # Signal observed at Close[t]; entry at Open[t+1]; exit at Close[t+1]
            # ----------------------------------------------------------------
            # Valid t: feature_start <= t < N_is - H
            t_indices = list(range(lookback, N_is - H))  # indices in is_table
            T_valid = len(t_indices)

            if T_valid < 10:
                raise DataContractError(
                    f"Trial {trial_id}: only {T_valid} valid labelled observations"
                )

            X_valid = np.array([
                (closes[t] - closes[t - lookback]) / closes[t - lookback]
                for t in t_indices
            ], dtype=np.float64)

            # R(t, H=1) = (Close[t+H] - Open[t+1]) / Open[t+1]
            R_valid = np.array([
                (closes[t + H] - opens[t + 1]) / opens[t + 1]
                for t in t_indices
            ], dtype=np.float64)

            # ----------------------------------------------------------------
            # Ternary Signal with Deadband Filter
            # S_t = +1 if X_t > db_frac, -1 if X_t < -db_frac, else 0
            # deadband converts from bps to fractional: 1 bps = 0.0001
            # ----------------------------------------------------------------
            db_frac = deadband_bps * 1e-4  # convert bps to decimal fraction
            S_valid = np.where(X_valid > db_frac, 1.0,
                      np.where(X_valid < -db_frac, -1.0, 0.0))

            # ----------------------------------------------------------------
            # Net Trade PnL: only when |S| = 1 (position taken)
            # Net Return = Gross Return * S - friction (on active trades only)
            # Friction applies when |S| = 1 (entering/exiting position)
            # ----------------------------------------------------------------
            active_mask = np.abs(S_valid) > 0.5
            trade_count = int(np.sum(active_mask))

            gross_returns_active = R_valid[active_mask] * S_valid[active_mask]
            friction_per_trade_dec = float(TOTAL_FRICTION_BPS) * 1e-4
            net_returns_active = gross_returns_active - friction_per_trade_dec

            # Convert net returns to bps for display
            net_pnl_bps_avg = float(np.mean(net_returns_active) * 10000) if trade_count > 0 else 0.0

            # ----------------------------------------------------------------
            # Strategy return series (all observations — 0 on inactive bars)
            # ----------------------------------------------------------------
            strategy_returns_all = R_valid * S_valid
            # Apply friction only on active bars
            strategy_returns_all[active_mask] -= friction_per_trade_dec

            # ----------------------------------------------------------------
            # Metric 1: Rank IC (Spearman) — over ALL valid observations (including inactive)
            # ----------------------------------------------------------------
            X_dec = [Decimal(f"{float(x):.18f}") for x in X_valid]
            R_dec = [Decimal(f"{float(r):.18f}") for r in R_valid]
            rank_ic = calculate_spearman_rank_ic(X_dec, R_dec)
            rank_ic_float = float(rank_ic) if rank_ic is not None else 0.0

            # ----------------------------------------------------------------
            # Metric 2: HAC t-stat (Bartlett, Newey-West bandwidth)
            # Regress R_t on X_t over all valid observations
            # ----------------------------------------------------------------
            hac_policy = HacInferencePolicy(
                bandwidth_method=HacBandwidthMethod.NEWEY_WEST_PLUGIN,
                run_bandwidth_robustness_check=False,
            )
            hac_lag = determine_hac_bandwidth(
                method=hac_policy.bandwidth_method,
                sample_size=T_valid,
                horizon=H,
            )
            beta_dec, se_dec, t_dec, p_dec = compute_ols_beta_and_hac(X_dec, R_dec, hac_lag)
            hac_t_stat = float(t_dec)

            # ----------------------------------------------------------------
            # Metric 3: Signal Autocorrelation rho_1
            # ----------------------------------------------------------------
            S_dec = [Decimal(f"{float(s):.18f}") for s in S_valid]
            autocorr = calculate_autocorrelation(S_dec, lag=1)
            rho1 = float(autocorr) if autocorr is not None else 0.0

            # ----------------------------------------------------------------
            # Metric 5: Haircut Sharpe (Annualized IS Sharpe on net returns)
            # ----------------------------------------------------------------
            if trade_count > 1:
                haircut_sharpe = compute_haircut_sharpe(net_returns_active, H4_BARS_PER_YEAR)
            else:
                haircut_sharpe = 0.0

            # ----------------------------------------------------------------
            # Conjunctive 5-Gate Qualification
            # ----------------------------------------------------------------
            gate_rank_ic = rank_ic_float >= float(GATE_MIN_RANK_IC)
            gate_hac_t = hac_t_stat >= float(GATE_MIN_HAC_T)
            gate_rho1 = abs(rho1) <= float(GATE_MAX_RHO1)
            gate_net_pnl = net_pnl_bps_avg >= float(GATE_MIN_NET_PNL_BPS)
            gate_sharpe = haircut_sharpe >= float(GATE_MIN_HAIRCUT_SHARPE)
            is_qualified = gate_rank_ic and gate_hac_t and gate_rho1 and gate_net_pnl and gate_sharpe

            verdict = "QUALIFIED" if is_qualified else "DISQUALIFIED"

            # ----------------------------------------------------------------
            # Build SearchTrialRecord
            # ----------------------------------------------------------------
            strategy_returns_dec = [Decimal(f"{float(r):.18f}") for r in strategy_returns_all]
            is_sharpe_dec = Decimal(f"{haircut_sharpe:.12f}")
            execution_manifest_id = (
                f"exec_manifest_{HYPOTHESIS_ID}_{trial_id}_"
                f"L{lookback}_D{int(deadband_bps * 10)}_"
                f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
            )

            trial_record = SearchTrialRecord.create(
                trial_id=trial_id,
                strategy_id=STRATEGY_ID,
                hypothesis_id=HYPOTHESIS_ID,
                feature_names=["lookback_return", "close_price"],
                parameters={
                    "lookback_bars": lookback,
                    "deadband_bps": deadband_bps,
                    "horizon_bars": H,
                    "signal_type": "TERNARY_DIRECTIONAL",
                    "cost_model_total_friction_bps": float(TOTAL_FRICTION_BPS),
                },
                in_sample_sharpe=is_sharpe_dec,
                in_sample_returns=strategy_returns_dec,
                execution_manifest_id=execution_manifest_id,
            )
            trial_records.append(trial_record)

            # Store results for reporting
            result = {
                "trial_id": trial_id,
                "trial_number": trial_number,
                "lookback_bars": lookback,
                "deadband_bps": deadband_bps,
                "n_observations": T_valid,
                "n_active_trades": trade_count,
                "rank_ic": rank_ic_float,
                "hac_t_stat": hac_t_stat,
                "hac_lag_bandwidth": hac_lag,
                "rho1_signal_autocorr": rho1,
                "avg_net_pnl_bps": net_pnl_bps_avg,
                "haircut_sharpe_annualized": haircut_sharpe,
                "gate_rank_ic_pass": gate_rank_ic,
                "gate_hac_t_pass": gate_hac_t,
                "gate_rho1_pass": gate_rho1,
                "gate_net_pnl_pass": gate_net_pnl,
                "gate_sharpe_pass": gate_sharpe,
                "is_qualified": is_qualified,
                "verdict": verdict,
                "trial_record_config_sha256": trial_record.config_sha256,
                "in_sample_return_series_sha256": trial_record.in_sample_return_series_sha256,
                "p_value": float(trial_record.p_value),
                "p_value_input_hash": trial_record.p_value_input_hash,
            }
            trial_results.append(result)

            print(
                f"\n  [{trial_id}] L={lookback} | DB={deadband_bps}bps | "
                f"N={T_valid} obs | {trade_count} trades"
            )
            print(
                f"    Rank IC={rank_ic_float:+.4f} {'[P]' if gate_rank_ic else '[F]'}  "
                f"HAC-t={hac_t_stat:+.3f} {'[P]' if gate_hac_t else '[F]'}  "
                f"rho1={rho1:+.4f} {'[P]' if gate_rho1 else '[F]'}  "
                f"NetPnL={net_pnl_bps_avg:+.3f}bps {'[P]' if gate_net_pnl else '[F]'}  "
                f"Sharpe={haircut_sharpe:+.3f} {'[P]' if gate_sharpe else '[F]'}"
            )
            print(f"    => {verdict}")

    # -----------------------------------------------------------------------
    # Post-Census Audit
    # -----------------------------------------------------------------------
    assert len(trial_results) == K_NOMINAL, (
        f"CENSUS INCOMPLETE: {len(trial_results)} trials evaluated, expected {K_NOMINAL}"
    )
    assert len(trial_records) == K_NOMINAL

    qualified_trials = [r for r in trial_results if r["is_qualified"]]
    failed_trials = [r for r in trial_results if not r["is_qualified"]]
    n_qualified = len(qualified_trials)
    n_failed = len(failed_trials)

    # -----------------------------------------------------------------------
    # Verdict Determination
    # -----------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("POST-CENSUS AUDIT SUMMARY")
    print("=" * 80)
    print(f"Total Trials Executed: {len(trial_results)}/{K_NOMINAL}")
    print(f"Qualified Trials: {n_qualified}")
    print(f"Failed Trials: {n_failed}")

    if n_qualified == 0:
        r3_verdict = "FAIL"
        hyp_002_state = "TERMINALLY_FALSIFIED"
        print(f"\n=> R3 VERDICT: {r3_verdict}")
        print(f"=> HYP_002 STATE: {hyp_002_state}")
        print("=> 12/12 trials failed the conjunctive qualification gate.")
        print("=> No artificial winner created. Hypothesis sealed as TERMINALLY_FALSIFIED.")
    else:
        r3_verdict = "PASS"
        hyp_002_state = "QUALIFICATION_CANDIDATE"
        print(f"\n=> R3 VERDICT: {r3_verdict}")
        print(f"=> HYP_002 STATE: {hyp_002_state}")
        print(f"=> {n_qualified} trial(s) passed all 5 mandatory gates.")
        print("=> NOTE: In-sample qualification is NOT trading authorization.")
        print("=> NOTE: Profitability is NOT PROVEN for current market regimes.")
        print("=> Subsequent governance gates (Validation, OOS, Phase 6 DSR) required.")

    # -----------------------------------------------------------------------
    # Gate 4: Seal SearchTrialLedger
    # -----------------------------------------------------------------------
    print("\n[Gate 4] Sealing SearchTrialLedger:")
    ledger_id = (
        f"ledger_{HYPOTHESIS_ID}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    ledger = SearchTrialLedger(
        ledger_id=ledger_id,
        strategy_id=STRATEGY_ID,
        hypothesis_id=HYPOTHESIS_ID,
        trials=tuple(trial_records),
        sharpe_space=SharpeSpace.ANNUAL,
        is_sealed=False,
    )
    sealed_ledger = ledger.seal()
    ledger_digest = sealed_ledger.ledger_digest
    print(f" -> Ledger ID: {sealed_ledger.ledger_id}")
    print(f" -> Ledger Digest: {ledger_digest}")
    print(f" -> Trial Count: {len(sealed_ledger.trials)}")
    print(" -> Status: SEALED")

    # -----------------------------------------------------------------------
    # Gate 5: Persist Ledger
    # -----------------------------------------------------------------------
    print("\n[Gate 5] Persisting Sealed Ledger:")
    ledger_dir = Path("data/manifests/research")
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / f"search_trial_ledger_{HYPOTHESIS_ID}.json"

    def _to_serializable(obj: Any) -> Any:
        """Recursively convert MappingProxyType, Decimal, tuple, etc. to JSON-safe types."""
        from types import MappingProxyType
        if isinstance(obj, MappingProxyType):
            return {k: _to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, dict):
            return {k: _to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [_to_serializable(i) for i in obj]
        elif isinstance(obj, Decimal):
            return str(obj)
        elif hasattr(obj, "__class__") and hasattr(obj.__class__, "__mro__"):
            # Handle any pydantic Enum
            if hasattr(obj, "value"):
                return obj.value
        return obj

    # Build ledger dict manually — bypass pydantic model_dump() which chokes on MappingProxyType
    def _serialize_trial(t: SearchTrialRecord) -> Dict[str, Any]:
        return {
            "trial_id": t.trial_id,
            "strategy_id": t.strategy_id,
            "hypothesis_id": t.hypothesis_id,
            "feature_names": list(t.feature_names),
            "parameters": _to_serializable(dict(t.parameters)),
            "in_sample_sharpe": str(t.in_sample_sharpe),
            "p_value": str(t.p_value),
            "p_value_method": t.p_value_method,
            "p_value_input_hash": t.p_value_input_hash,
            "in_sample_return_series_sha256": t.in_sample_return_series_sha256,
            "config_sha256": t.config_sha256,
            "execution_manifest_id": t.execution_manifest_id,
        }

    ledger_data = {
        "ledger_id": sealed_ledger.ledger_id,
        "strategy_id": sealed_ledger.strategy_id,
        "hypothesis_id": sealed_ledger.hypothesis_id,
        "sharpe_space": sealed_ledger.sharpe_space.value,
        "is_sealed": sealed_ledger.is_sealed,
        "sealed_at_utc": sealed_ledger.sealed_at_utc,
        "ledger_digest": sealed_ledger.ledger_digest,
        "trials": [_serialize_trial(t) for t in sealed_ledger.trials],
    }
    ledger_path.write_text(json.dumps(ledger_data, indent=2), encoding="utf-8")
    docs_ledger_dir = Path("docs/phase8.5/ledgers")
    docs_ledger_dir.mkdir(parents=True, exist_ok=True)
    docs_ledger_path = docs_ledger_dir / f"search_trial_ledger_{HYPOTHESIS_ID}.json"
    docs_ledger_path.write_text(json.dumps(ledger_data, indent=2), encoding="utf-8")
    print(f" -> Ledger persisted: {ledger_path}")
    print(f" -> Docs Ledger persisted: {docs_ledger_path}")

    # -----------------------------------------------------------------------
    # Gate 6: Generate R3 Result Manifest
    # -----------------------------------------------------------------------
    print("\n[Gate 6] Generating R3 Result Manifest:")
    r3_manifest = {
        "r3_manifest_id": f"R3-{HYPOTHESIS_ID}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis_sha256": computed_digest,
        "dataset_id": DATASET_ID,
        "canonical_batch_sha256": computed_canonical_sha,
        "r3_verdict": r3_verdict,
        "hyp_002_state": hyp_002_state,
        "search_geometry": {
            "k_nominal": K_NOMINAL,
            "lookback_bars_grid": LOOKBACK_BARS_GRID,
            "deadband_bps_grid": DEADBAND_BPS_GRID,
            "primary_horizon_h": hyp_spec.primary_horizon,
        },
        "insample_partition": {
            "start_idx": INSAMPLE_START_IDX,
            "end_idx": INSAMPLE_END_IDX,
            "bar_count": INSAMPLE_COUNT,
        },
        "oos_isolation": {
            "validation_idx_range": f"{VALIDATION_START_IDX}..{VALIDATION_END_IDX}",
            "validation_untouched": True,
            "oos_idx_range": f"{OOS_START_IDX}..{OOS_END_IDX}",
            "oos_untouched": True,
            "m5_holdout_untouched": True,
        },
        "cost_model": {
            "quoted_spread_bps": str(QUOTED_SPREAD_BPS),
            "roundtrip_fee_bps": str(ROUNDTRIP_FEE_BPS),
            "fixed_slippage_bps": str(FIXED_SLIPPAGE_BPS),
            "total_friction_bps": str(TOTAL_FRICTION_BPS),
            "status": "PROPOSED_RESEARCH_ASSUMPTION",
        },
        "qualification_gate_thresholds": {
            "min_rank_ic": str(GATE_MIN_RANK_IC),
            "min_hac_t": str(GATE_MIN_HAC_T),
            "max_rho1": str(GATE_MAX_RHO1),
            "min_net_pnl_bps": str(GATE_MIN_NET_PNL_BPS),
            "min_haircut_sharpe": str(GATE_MIN_HAIRCUT_SHARPE),
        },
        "trial_census": trial_results,
        "census_summary": {
            "total_trials": K_NOMINAL,
            "qualified_trials": n_qualified,
            "failed_trials": n_failed,
            "terminal_falsification": (r3_verdict == "FAIL"),
        },
        "ledger_id": sealed_ledger.ledger_id,
        "ledger_digest": ledger_digest,
        "trading_authority": "LOCKED",
        "capital_authority_usd": 0.00,
        "broker_connection": "NONE",
        "live_orders": 0,
        "paper_orders": 0,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    manifest_dir = Path("docs/phase8.5/manifests")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    r3_manifest_path_docs = manifest_dir / f"r3_manifest_{HYPOTHESIS_ID}.json"
    r3_manifest_path_data = ledger_dir / f"r3_manifest_{HYPOTHESIS_ID}.json"

    r3_manifest_path_docs.write_text(json.dumps(r3_manifest, indent=2, default=str), encoding="utf-8")
    r3_manifest_path_data.write_text(json.dumps(r3_manifest, indent=2, default=str), encoding="utf-8")

    # Compute manifest SHA-256
    r3_manifest_sha256 = hashlib.sha256(
        r3_manifest_path_docs.read_bytes()
    ).hexdigest()

    print(f" -> R3 Manifest: {r3_manifest_path_docs}")
    print(f" -> R3 Manifest SHA-256: {r3_manifest_sha256}")

    # -----------------------------------------------------------------------
    # Final State Report
    # -----------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP R3 COMPLETE — MANDATORY STOP")
    print("=" * 80)
    print(f"R3 Verdict: {r3_verdict}")
    print(f"HYP_002 State: {hyp_002_state}")
    print(f"Qualified Trials: {n_qualified}/{K_NOMINAL}")
    print(f"Ledger Digest: {ledger_digest}")
    print(f"R3 Manifest SHA-256: {r3_manifest_sha256}")
    print(f"Capital Authority: $0.00")
    print(f"Trading Authority: LOCKED")
    print(f"Broker Connection: NONE")
    print(f"Validation Partition: UNTOUCHED (UNEXPOSED_PRISTINE)")
    print(f"Blind OOS Partition: UNTOUCHED (UNEXPOSED_PRISTINE)")
    print(f"2026 M5 Holdout: UNTOUCHED")
    print("=" * 80)
    print("EXECUTION STOPPED. No further automated progression to Validation or OOS.")
    print("Awaiting Human Authorization for subsequent governance gates.")
    print("=" * 80)

    return r3_manifest


if __name__ == "__main__":
    run_step_r3_census()
