"""Phase 8.5 Step R1 Registration Script: HYP_TSMOM_EURUSD_HTF_001.

Strictly enforces:
1. Submits candidate proposal to ResearchReInceptionGate.
2. Validates all 6 governance invariants (New Immutable ID, Anti-HARKing Cardinality,
   Declarative Data Contract, Quarantine Boundary, Completeness, Readiness Separation).
3. If gate authorizes, seals HypothesisSpecification to canonical JSON.
4. Computes canonical SHA-256 digest.
5. Emits R1 Manifest and Registration Record.
6. Zero market data access, zero empirical research, zero capital authority ($0.00).
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.reinception import (
    InceptionAuthorizationToken,
    InceptionDecision,
    ResearchInceptionProposal,
    ResearchReInceptionGate,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
    SplitPolicy,
)


def register_step_r1() -> None:
    print("================================================================================")
    print("ACASH PHASE 8.5 STEP R1: HYPOTHESIS PRE-REGISTRATION")
    print("Target: HYP_TSMOM_EURUSD_HTF_001 (Higher-Timeframe Time-Series Momentum)")
    print("================================================================================")

    # 1. Construct Proposal
    registered_at_utc = "2026-09-07T00:00:00Z"
    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_TSMOM_EURUSD_HTF_001",
        candidate_hypothesis_version="v1.0",
        economic_rationale=(
            "Higher-timeframe time-series momentum in liquid G10 FX (EURUSD) driven by monetary "
            "policy divergence and delayed macroeconomic information diffusion across global "
            "institutional participants. Directional price trends over H4 sessions (12h to 20d) "
            "exhibit positive persistence where gross price displacements are large enough to "
            "comfortably surmount institutional transaction friction."
        ),
        target_symbol="EURUSD",
        target_timeframe="H4",
        feature_dependencies=["lookback_return", "close_price"],
        parameter_search_grid={
            "lookback_bars": [3, 6, 12, 24, 48, 120],
            "deadband_bps": [3.0, 6.0],
        },
        planned_trial_count=12,  # Exactly 6 * 2 = 12
        target_horizons=[1, 6],
        primary_horizon=1,
        expected_direction=ExpectedDirection.LONG,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.025"),
            min_hac_t_stat=Decimal("2.00"),
            max_feature_autocorrelation=Decimal("0.98"),
            min_cost_adjusted_spread_ratio=Decimal("1.50"),
        ),
        cost_model=CostModelConfig(
            quoted_spread_bps=Decimal("0.4"),
            roundtrip_broker_fee_bps=Decimal("0.5"),
            fixed_slippage_bps=Decimal("0.3"),
        ),
        proposed_dataset_id="DS_EURUSD_H4_2021_2024_CANONICAL",
        proposed_data_window=("2021-01-01T00:00:00+00:00", "2024-12-31T23:59:59+00:00"),
        proposed_split_policy=SplitPolicy(
            train_pct=Decimal("0.60"),
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=12,
        ),
        author="human_governance_auditor",
        proposed_at_utc=registered_at_utc,
    )

    print("\n[Step 1] Submitting candidate proposal to ResearchReInceptionGate...")
    token = ResearchReInceptionGate.evaluate_reinception_proposal(proposal=proposal)
    print(f" -> Gate Decision: {token.decision.value}")
    print(f" -> Token ID: {token.token_id}")
    print(f" -> Authorized Hypothesis ID: {token.authorized_hypothesis_id}")
    print(f" -> Proposal SHA-256: {token.proposal_sha256}")
    print(f" -> Capital Authority: ${token.capital_authority_usd}")
    print(f" -> Strategy Qualified: {token.is_strategy_qualified}")
    print(f" -> Trading Authorized: {token.is_paper_authorized or token.is_live_authorized}")

    if token.decision != InceptionDecision.INCEPTION_AUTHORIZED:
        raise DataContractError(f"Re-Inception Gate rejected proposal: {token.decision}")

    # 2. Build HypothesisSpecification
    parameter_config = {
        "bar_frequency": "H4",
        "deadband_bps_grid": [3.0, 6.0],
        "lookback_bars_grid": [3, 6, 12, 24, 48, 120],
        "nominal_trials_k": 12,
        "signal_type": "TERNARY_DIRECTIONAL",
        "strategy_id": "STRAT-MOM-HTF-H4-V1",
        "cost_model_proposed": {
            "quoted_spread_bps": "0.4",
            "roundtrip_broker_fee_bps": "0.5",
            "fixed_slippage_bps": "0.3",
            "total_friction_bps": "1.2",
            "status": "PROPOSED_SUBJECT_TO_R2_VERIFICATION",
        },
        "data_contract_proposed": {
            "canonical_window_utc": ["2021-01-01T00:00:00Z", "2024-12-31T23:59:59Z"],
            "minimum_usable_h4_bars": 5000,
            "split_policy": {
                "train_pct": "0.60",
                "val_pct": "0.20",
                "oos_pct": "0.20",
                "embargo_bars": 12,
            },
        },
    }
    parameter_config_json = CanonicalConfigSerializer.to_canonical_json(parameter_config)

    hyp_spec = HypothesisSpecification(
        hypothesis_id=proposal.candidate_hypothesis_id,
        hypothesis_version=proposal.candidate_hypothesis_version,
        parent_hypothesis_id=None,
        economic_rationale=proposal.economic_rationale,
        target_symbol=proposal.target_symbol,
        feature_dependencies=proposal.feature_dependencies,
        parameter_config_json=parameter_config_json,
        expected_direction=proposal.expected_direction,
        target_horizons=proposal.target_horizons,
        primary_horizon=proposal.primary_horizon,
        invalidation_criteria=proposal.invalidation_criteria,
        registered_at_utc=registered_at_utc,
        author=proposal.author,
    )

    # Compute Canonical SHA-256
    hyp_sha256 = calculate_hypothesis_spec_sha256(hyp_spec)
    print(f"\n[Step 2] Computed Canonical Hypothesis SHA-256: {hyp_sha256}")

    # 3. Persist Sealed JSON
    hyp_dest_dir = Path("docs/phase8.5/hypotheses")
    hyp_dest_dir.mkdir(parents=True, exist_ok=True)
    hyp_file = hyp_dest_dir / f"{hyp_spec.hypothesis_id}.json"

    raw_json = hyp_spec.to_canonical_json()
    # Format nicely with indentation for readability while preserving deterministic contents
    pretty_dict = json.loads(raw_json)
    hyp_file.write_text(json.dumps(pretty_dict, indent=2), encoding="utf-8")
    print(f" -> Persisted Sealed Hypothesis to: {hyp_file}")

    # Mirror in data/manifests/research/hypotheses/ if directory exists
    data_hyp_dir = Path("data/manifests/research/hypotheses")
    data_hyp_dir.mkdir(parents=True, exist_ok=True)
    (data_hyp_dir / f"{hyp_spec.hypothesis_id}.json").write_text(
        json.dumps(pretty_dict, indent=2), encoding="utf-8"
    )

    # 4. Persist R1 Registration Manifest
    manifest_payload = {
        "manifest_type": "HYPOTHESIS_REGISTRATION_MANIFEST",
        "hypothesis_id": hyp_spec.hypothesis_id,
        "hypothesis_version": hyp_spec.hypothesis_version,
        "hypothesis_sha256": hyp_sha256,
        "registered_at_utc": registered_at_utc,
        "author": hyp_spec.author,
        "target_symbol": hyp_spec.target_symbol,
        "primary_timeframe": "H4",
        "search_trial_count_k": 12,
        "inception_token_id": token.token_id,
        "proposal_sha256": token.proposal_sha256,
        "status": "SEALED_STEP_R1_PASS",
        "capital_authority_usd": "0.00",
        "next_required_step": "STEP_R2_HISTORICAL_DATA_PREPARATION_LOCKED",
    }
    manifest_json = CanonicalConfigSerializer.to_canonical_json(manifest_payload)
    manifest_digest = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    manifest_payload["manifest_sha256"] = manifest_digest

    manifest_dest = Path("docs/phase8.5/manifests") / f"manifest_r1_{hyp_spec.hypothesis_id}.json"
    manifest_dest.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    print(f" -> Persisted R1 Manifest to: {manifest_dest}")
    print(f" -> Manifest SHA-256: {manifest_digest}")

    data_man_dir = Path("data/manifests/research")
    data_man_dir.mkdir(parents=True, exist_ok=True)
    (data_man_dir / f"manifest_r1_{hyp_spec.hypothesis_id}.json").write_text(
        json.dumps(manifest_payload, indent=2), encoding="utf-8"
    )

    print("\n================================================================================")
    print("STEP R1 PRE-REGISTRATION SUCCESSFULLY SEALED!")
    print(f"Hypothesis ID: {hyp_spec.hypothesis_id}")
    print(f"Hypothesis SHA-256: {hyp_sha256}")
    print("Status: R1 PASS / SEALED (R2 LOCKED / CAPITAL $0.00)")
    print("================================================================================")


if __name__ == "__main__":
    register_step_r1()
