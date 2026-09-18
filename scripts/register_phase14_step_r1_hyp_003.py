"""Phase 14 Step R1 Registration & Sealing Script: HYP_003 (Price-Only ORB).

Strictly enforces:
1. Submits frozen MEC-0013 price-only ORB proposal to ResearchReInceptionGate.
2. Formally evaluates all 6 institutional invariants.
3. Generates InceptionAuthorizationToken bound to HYP_003.
4. Seals canonical HypothesisSpecification to disk with deterministic SHA-256 digest.
5. Emits canonical R1 Registration Manifest for HYP_003.
6. Strictly maintains fail-closed boundaries: zero market data loading, $0.00 capital, backtest locked.
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


def register_step_r1_hyp_003() -> InceptionAuthorizationToken:
    print("================================================================================")
    print("ACASH PHASE 14 STEP R1: HYPOTHESIS REGISTRATION & SEALING (HYP_003)")
    print("Mechanism Lineage: MEC-0013 Price-Only Opening Range Breakout (ORB)")
    print("Target Instrument: SPY (1-minute Consolidated SIP Aggregates)")
    print("Session Authority: Accepted NyseCa1Calendar (CA-1)")
    print("================================================================================")

    registered_at_utc = "2026-09-18T23:00:00Z"
    prereg_doc_path = Path("docs/phase14/mec_0013_price_only_preregistration.md")
    if not prereg_doc_path.exists():
        raise DataContractError(f"CRITICAL: Frozen pre-registration document not found at '{prereg_doc_path}'.")

    prereg_sha256 = hashlib.sha256(prereg_doc_path.read_bytes()).hexdigest()
    print(f"[Pre-Flight] Frozen Pre-Registration SHA-256: {prereg_sha256}")

    # 1. Construct Proposal for HYP_003
    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_003",
        candidate_hypothesis_version="v1.0",
        economic_rationale=(
            "Opening Range Breakout (ORB) in US benchmark equity ETF (SPY) under MEC-0013 price-only "
            "mechanics. Early regular-session price discovery establishes an initial range reflecting "
            "overnight order assimilation and opening auction balance; completed 1-minute close-through "
            "breakouts beyond this range capture directional momentum driven by institutional order "
            "flow imbalance through the remainder of the regular trading session."
        ),
        target_symbol="SPY",
        target_timeframe="1m",
        feature_dependencies=["opening_range_high", "opening_range_low", "bar_close"],
        parameter_search_grid={
            "opening_range_minutes": [5, 15],
            "breakout_direction": ["LONG", "SHORT"],
        },
        planned_trial_count=4,  # Exactly 2 * 2 = 4 (K=4 primary cells)
        target_horizons=[1, 390],
        primary_horizon=390,
        expected_direction=ExpectedDirection.LONG,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.010"),
            min_hac_t_stat=Decimal("1.50"),
            max_feature_autocorrelation=Decimal("0.98"),
            min_cost_adjusted_spread_ratio=Decimal("1.50"),
        ),
        cost_model=CostModelConfig(
            quoted_spread_bps=Decimal("0.0"),
            roundtrip_broker_fee_bps=Decimal("1.6"),  # 0.8 bps entry + 0.8 bps exit
            fixed_slippage_bps=Decimal("1.0"),        # 0.5 bps adverse per side
        ),
        proposed_dataset_id="DS_SPY_1MIN_SIP_HISTORICAL",
        proposed_data_window=("2017-01-01T00:00:00+00:00", "2022-12-31T23:59:59+00:00"),
        proposed_split_policy=SplitPolicy(
            train_pct=Decimal("0.60"),
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=0,
        ),
        author="human_operator_ratified",
        proposed_at_utc=registered_at_utc,
    )

    print("\n[Step 1] Submitting candidate proposal HYP_003 to ResearchReInceptionGate...")
    token = ResearchReInceptionGate.evaluate_reinception_proposal(proposal=proposal)
    print(f" -> Gate Decision: {token.decision.value}")
    print(f" -> Token ID: {token.token_id}")
    print(f" -> Authorized Hypothesis ID: {token.authorized_hypothesis_id}")
    print(f" -> Proposal SHA-256: {token.proposal_sha256}")
    print(f" -> Capital Authority: ${token.capital_authority_usd}")
    print(f" -> Strategy Qualified: {token.is_strategy_qualified}")
    print(f" -> Paper Authorized: {token.is_paper_authorized}")
    print(f" -> Live Authorized: {token.is_live_authorized}")

    if token.decision != InceptionDecision.INCEPTION_AUTHORIZED:
        raise DataContractError(f"Re-Inception Gate rejected proposal: {token.decision}")

    # 2. Build Canonical HypothesisSpecification parameter config
    parameter_config = {
        "bar_frequency": "1m",
        "nominal_trials_k": 4,
        "signal_type": "PRICE_ONLY_OPENING_RANGE_BREAKOUT",
        "strategy_id": "STRAT-ORB-SPY-PRICE-ONLY-V1",
        "mechanism_id": "MEC-0013",
        "primary_cells": [
            {"cell_id": "ORB_5M_LONG", "opening_range_minutes": 5, "direction": "LONG"},
            {"cell_id": "ORB_5M_SHORT", "opening_range_minutes": 5, "direction": "SHORT"},
            {"cell_id": "ORB_15M_LONG", "opening_range_minutes": 15, "direction": "LONG"},
            {"cell_id": "ORB_15M_SHORT", "opening_range_minutes": 15, "direction": "SHORT"},
        ],
        "all_14_frozen_parameters": {
            "1_breakout_confirmation": "CLOSE-THROUGH",
            "2_entry_timing": "NEXT-BAR OPEN",
            "3_directional_lane": "SYMMETRIC LONG + SHORT",
            "4_stop_loss_rule": "OPPOSITE OPENING-RANGE BOUNDARY",
            "5_exit_holding_horizon": "END-OF-DAY FLATTEN",
            "6_transaction_cost_bps": "1.6 bps ROUND-TRIP (0.8 entry + 0.8 exit)",
            "7_slippage_bps": "0.5 bps ADVERSE PER SIDE (1.0 roundtrip)",
            "8_execution_price_convention": "CONSERVATIVE_EXECUTABLE",
            "9_opening_auction_handling": "INCLUDE_0930_BAR",
            "10_closing_auction_handling": "EXCLUDE_1600_BAR_EXIT_1559_CLOSE",
            "11_is_oos_partition": {
                "in_sample_dates": ["2017-01-01", "2022-12-31"],
                "out_of_sample_dates": ["2023-01-01", "2026-12-31"],
                "oos_state": "SEALED_UNREAD",
            },
            "12_embargo_purge_days": 0,
            "13_data_quality_threshold": "100% COMPLETE CA-1 390-MINUTE GRID",
            "14_session_exclusion_policy": "REGULAR 390-MIN SESSIONS ONLY",
        },
        "governance_lineage": {
            "hypothesis_ordinal": 3,
            "hypothesis_ordinal_alias": "HYP_003",
            "preregistration_doc": "docs/phase14/mec_0013_price_only_preregistration.md",
            "preregistration_sha256": prereg_sha256,
            "freeze_ratification": "D-PREREG-1 (Option A, 2026-09-18)",
            "validation_auth": "D-EMP-1 (Option A, 2026-09-18)",
            "inception_token_id": token.token_id,
            "proposal_sha256": token.proposal_sha256,
            "source_git_sha": "5ec7d8b52333c71ab89b32426e4f80bd1aea2784",
        },
        "calendar_authority": {
            "calendar_name": "NyseCa1Calendar",
            "code": "CA-1",
            "timezone": "America/New_York",
            "regular_session_bars": 390,
        },
        "data_contract": {
            "symbol": "SPY",
            "feed": "sip",
            "adjustment": "raw",
            "timeframe": "1Min",
            "d13_status": "PARTIALLY RESOLVED (AVAILABILITY/DEPTH: RETIRED; PIT/VINTAGE: OPEN)",
            "d14_status": "BLOCKED (AUTHORITY-CONDITIONAL / DECOUPLED FROM PRICE-ONLY LANE)",
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

    # 3. Compute Canonical SHA-256
    hyp_sha256 = calculate_hypothesis_spec_sha256(hyp_spec)
    print(f"\n[Step 2] Computed Canonical Hypothesis SHA-256: {hyp_sha256}")

    # 4. Persist Sealed JSON in Canonical Locations
    # Phase 8.5 hypotheses directory (checked by ReInceptionGate for collision)
    p85_hyp_dir = Path("docs/phase8.5/hypotheses")
    p85_hyp_dir.mkdir(parents=True, exist_ok=True)
    p85_hyp_file = p85_hyp_dir / f"{hyp_spec.hypothesis_id}.json"

    # Phase 14 hypotheses directory
    p14_hyp_dir = Path("docs/phase14/hypotheses")
    p14_hyp_dir.mkdir(parents=True, exist_ok=True)
    p14_hyp_file = p14_hyp_dir / f"{hyp_spec.hypothesis_id}.json"

    # Data manifests hypotheses directory
    data_hyp_dir = Path("data/manifests/research/hypotheses")
    data_hyp_dir.mkdir(parents=True, exist_ok=True)
    data_hyp_file = data_hyp_dir / f"{hyp_spec.hypothesis_id}.json"

    # Serialize canonical JSON using model_dump(mode="json")
    spec_json_dict = hyp_spec.model_dump(mode="json")
    formatted_spec_json = json.dumps(spec_json_dict, indent=2)

    p85_hyp_file.write_text(formatted_spec_json, encoding="utf-8")
    p14_hyp_file.write_text(formatted_spec_json, encoding="utf-8")
    data_hyp_file.write_text(formatted_spec_json, encoding="utf-8")
    print(f" -> Persisted Sealed Hypothesis to: {p85_hyp_file}")
    print(f" -> Persisted Sealed Hypothesis to: {p14_hyp_file}")
    print(f" -> Persisted Sealed Hypothesis to: {data_hyp_file}")

    # 5. Persist R1 Registration Manifest
    manifest_payload = {
        "manifest_type": "HYPOTHESIS_REGISTRATION_MANIFEST",
        "hypothesis_id": hyp_spec.hypothesis_id,
        "hypothesis_ordinal": 3,
        "hypothesis_ordinal_alias": "HYP_003",
        "mechanism_id": "MEC-0013",
        "hypothesis_version": hyp_spec.hypothesis_version,
        "hypothesis_sha256": hyp_sha256,
        "registered_at_utc": registered_at_utc,
        "author": hyp_spec.author,
        "target_symbol": hyp_spec.target_symbol,
        "primary_timeframe": "1m",
        "search_trial_count_k": 4,
        "inception_token_id": token.token_id,
        "proposal_sha256": token.proposal_sha256,
        "preregistration_sha256": prereg_sha256,
        "status": "SEALED_STEP_R1_PASS",
        "capital_authority_usd": "0.00",
        "next_required_step": "STEP_R2_HISTORICAL_DATA_QUALIFICATION_LOCKED",
    }
    manifest_json = CanonicalConfigSerializer.to_canonical_json(manifest_payload)
    manifest_digest = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    manifest_payload["manifest_sha256"] = manifest_digest
    formatted_manifest = json.dumps(manifest_payload, indent=2)

    p14_man_dir = Path("docs/phase14/manifests")
    p14_man_dir.mkdir(parents=True, exist_ok=True)
    p14_man_file = p14_man_dir / f"manifest_r1_{hyp_spec.hypothesis_id}.json"
    p14_man_file.write_text(formatted_manifest, encoding="utf-8")

    data_man_dir = Path("data/manifests/research")
    data_man_dir.mkdir(parents=True, exist_ok=True)
    data_man_file = data_man_dir / f"manifest_r1_{hyp_spec.hypothesis_id}.json"
    data_man_file.write_text(formatted_manifest, encoding="utf-8")

    print(f" -> Persisted R1 Manifest to: {p14_man_file}")
    print(f" -> Persisted R1 Manifest to: {data_man_file}")
    print(f" -> Manifest SHA-256: {manifest_digest}")

    print("\n================================================================================")
    print("HYP_003 CANONICAL PRE-REGISTRATION COMPLETED & SEALED!")
    print(f"Canonical Hypothesis ID: {hyp_spec.hypothesis_id}")
    print(f"Canonical Hypothesis SHA-256: {hyp_sha256}")
    print(f"Canonical Manifest SHA-256: {manifest_digest}")
    print("Status: R1 PASS / SEALED (R2 LOCKED / CAPITAL $0.00 / OOS SEALED)")
    print("================================================================================")

    return token


if __name__ == "__main__":
    register_step_r1_hyp_003()
