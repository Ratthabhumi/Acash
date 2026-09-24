"""Phase 14 Step R1 Registration & Sealing Script: HYP_011 (CORE-001 Global 80/20).

Submits the frozen HYP_011 proposal to ResearchReInceptionGate (real
invocation, K = 1), seals docs/phase14/hypotheses/HYP_011.json under gate
authority, and emits manifest_r1_HYP_011.json. Zero market-data I/O.
"""

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.reinception import (
    InceptionAuthorizationToken,
    InceptionDecision,
    ResearchInceptionProposal,
    ResearchReInceptionGate,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    InvalidationCriteria,
    SplitPolicy,
)

REGISTERED_AT_UTC = "2026-09-24T21:00:00Z"
HUMAN_AUTHORIZATION = "AUTHORIZE_CORE_001_PARK_HYP_010_AND_PREREGISTER_HYP_011_R1"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_canonical(obj: object) -> str:
    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(obj).encode("utf-8")
    ).hexdigest()


def build_strategy_contract() -> Dict[str, Any]:
    return {
        "core_id": "CORE-001",
        "hypothesis_id": "HYP_011",
        "working_title": "Global 80/20 Strategic Allocation Core",
        "strategy_family": "STATIC_GLOBAL_EQUITY_BOND_STRATEGIC_ASSET_ALLOCATION",
        "target_holdings": {"ACWI": 0.8, "AGG": 0.2},
        "signal_present": False,
        "lookback_present": False,
        "rebalance_frequency": "ANNUAL",
        "first_allocation_rule": "FIRST_ELIGIBLE_CANONICAL_US_EQUITY_SESSION_OPEN_ON_OR_AFTER_PARTITION_START",
        "scheduled_rebalance_rule": "FIRST_ELIGIBLE_CANONICAL_US_EQUITY_SESSION_OPEN_OF_EACH_NEW_CALENDAR_YEAR",
        "whole_share_solver": "SELLS_FIRST_THEN_BUYS_FLOOR_WITH_MIN_DEVIATION_DECREMENT_TIE_BREAK_AGG",
        "max_gross_leverage": 1.0,
        "volatility_targeting": False,
        "cash_return": 0.0,
        "candidate_ordinal_within_core": 3,
    }


def build_provider_contract() -> Dict[str, Any]:
    return {
        "bars_provider": "ALPACA_HISTORICAL_STOCK_BARS",
        "bars_endpoint": "/v2/stocks/{symbol}/bars",
        "symbols": ["ACWI", "AGG", "SPY"],
        "bars_timeframe": "1Day",
        "bars_feed": "sip",
        "signal_price_adjustment": "split",
        "execution_price_adjustment": "raw",
        "dividend_authorities": {
            "ACWI": "BLACKROCK_ISHARES_OFFICIAL",
            "AGG": "BLACKROCK_ISHARES_OFFICIAL",
            "SPY": "STATE_STREET_SPDR_OFFICIAL",
        },
        "vendor_adjusted_close_as_authority": False,
        "no_provider_substitution": True,
        "no_provider_splicing": True,
    }


def build_sample_partitions() -> Dict[str, Any]:
    return {
        "research_start": "2016-01-01",
        "historical_exposed_replication": {
            "start": "2016-01-01",
            "end": "2024-12-31",
            "classification": "HISTORICAL_EXPOSED_REPLICATION_NOT_RESEARCHER_BLIND",
        },
        "recent_stress": {
            "start": "2025-01-01",
            "end": "2026-08-14",
            "classification": "PUBLICLY_EXPOSED_RECENT_STRESS_NOT_PRISTINE_NON_DECISIVE",
        },
        "quarantine": {
            "start": "2026-08-15",
            "end": "PROSPECTIVE_START_EXCLUSIVE",
            "classification": "STRICT_ZERO_ACCESS_PRE_PROSPECTIVE_GAP",
        },
        "prospective": {
            "rule": "FIRST_ELIGIBLE_REGULAR_SESSION_OPEN_STRICTLY_AFTER_R1_COMMIT_TIMESTAMP",
            "state_at_r1": "LOCKED_ZERO_ACCESS",
            "minimum_eligible_sessions": 504,
            "minimum_annual_rebalances": 2,
        },
    }


def build_acceptance_gates() -> Dict[str, Any]:
    return {
        "logical_conjunction": "G1 AND G2 AND G3 AND G4 AND G5 AND G6",
        "G1_net_total_return": "> 0",
        "G2_net_annualized_sharpe": ">= 0.50",
        "sharpe_convention": {
            "periods_per_year": 252, "ddof": 1, "risk_free_rate": 0,
            "zero_variance": "FAIL_CLOSED",
        },
        "G3_max_drawdown": "<= 0.35",
        "G4_core_mdd_lt_benchmark_mdd": True,
        "G5_10bps_stress_net_total_return": "> 0",
        "G6_no_material_contract_failure": True,
        "net_of": "BASELINE_FRICTION",
        "no_discretionary_override": True,
    }


def register_step_r1_hyp_011() -> InceptionAuthorizationToken:
    print("================================================================================")
    print("ACASH PHASE 14 STEP R1: REGISTRATION & SEALING (HYP_011 / CORE-001)")
    print("Global 80/20 Strategic Allocation Core | K = 1 | No backtest")
    print("================================================================================")

    prereg_path = Path("docs/research/CORE-001-HYP-011-strategy-preregistration.md")
    if not prereg_path.exists():
        raise DataContractError(f"CRITICAL: preregistration not found at '{prereg_path}'.")
    prereg_bytes = prereg_path.read_bytes()
    prereg_sha256 = hashlib.sha256(prereg_bytes).hexdigest()
    prereg_text = prereg_bytes.decode("utf-8")
    for marker in (
        "PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_R1_SEAL",
        "OPEN_BEFORE_R1_UNRESOLVED_COUNT = 0",
        "HYP_011 = PROPOSED_NOT_PREREGISTERED",
        "EMPIRICAL_EXECUTION = NOT_AUTHORIZED",
    ):
        if marker not in prereg_text:
            raise DataContractError(f"CRITICAL: prereg missing marker '{marker}'.")
    print(f"[Pre-Flight] Pre-Registration SHA-256: {prereg_sha256}")

    hyp_path = Path("docs/phase14/hypotheses/HYP_011.json")
    hyp_pre = json.loads(hyp_path.read_text(encoding="utf-8"))
    if hyp_pre["state"] != "PROPOSED_NOT_PREREGISTERED":
        raise DataContractError(f"CRITICAL: HYP_011 state must be PROPOSED, got {hyp_pre['state']}.")
    if hyp_pre.get("mechanism_id") is not None:
        raise DataContractError("CRITICAL: HYP_011 mechanism_id must be null.")
    hyp_pre_sha256 = _sha256_file(hyp_path)

    upstream_authority_hashes = {
        "inception_doc_sha256": _sha256_file(
            Path("docs/phase14/CORE_001_HYP_011_RESEARCH_INCEPTION.md")
        ),
        "inception_manifest_sha256": _sha256_file(
            Path("docs/phase14/manifests/CORE_001_HYP_011_RESEARCH_INCEPTION.json")
        ),
        "semantic_conformance_record_sha256": _sha256_file(
            Path("docs/phase14/phase14_pre_r1_semantic_conformance_record_HYP_011.md")
        ),
        "semantic_conformance_manifest_sha256": _sha256_file(
            Path("docs/phase14/manifests/HYP_011_PRE_R1_SEMANTIC_CONFORMANCE.json")
        ),
        "hyp_011_pre_r1_proposal_record_sha256": hyp_pre_sha256,
        "hyp_010_park_manifest_sha256": _sha256_file(
            Path("docs/phase14/manifests/HYP_010_PARKED_NON_FALSIFIED_BLOCKER.json")
        ),
    }

    proposal = ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_011",
        candidate_hypothesis_version="v1.0",
        economic_rationale=str(hyp_pre["economic_rationale"]),
        target_symbol="ACWI",
        target_timeframe="1Day",
        feature_dependencies=list(hyp_pre["feature_dependencies"]),
        parameter_search_grid={
            "core_specification": ["CORE_001_GLOBAL_80_20_STATIC_ALLOCATION_V1"],
        },
        planned_trial_count=1,
        target_horizons=[21],  # Non-binding schema compatibility stub
        primary_horizon=21,  # Non-binding schema compatibility stub
        expected_direction=ExpectedDirection.LONG,  # Non-binding schema stub
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.000001"),
            min_hac_t_stat=Decimal("1.96"),
            max_feature_autocorrelation=Decimal("0.999999"),
            min_cost_adjusted_spread_ratio=Decimal("1.0"),
        ),
        cost_model=CostModelConfig(
            quoted_spread_bps=Decimal("0.0"),
            roundtrip_broker_fee_bps=Decimal("0.0"),
            fixed_slippage_bps=Decimal("0.0"),
        ),
        proposed_dataset_id="DS_CORE001_HYP011_ACWI_AGG_SPY_ALPACA_1DAY_SIP_2016_2024",
        proposed_data_window=("2016-01-01T00:00:00+00:00", "2024-12-31T23:59:59+00:00"),
        proposed_split_policy=SplitPolicy(
            train_pct=Decimal("0.60"),
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=0,
        ),
        author="external_research_authority_specification__implementation_only_encoding",
        proposed_at_utc=REGISTERED_AT_UTC,
    )

    print("\n[Step 1] Submitting HYP_011 to ResearchReInceptionGate...")
    token = ResearchReInceptionGate.evaluate_reinception_proposal(proposal=proposal)
    print(f" -> Gate Decision: {token.decision.value}")
    print(f" -> Token ID: {token.token_id}")
    print(f" -> Proposal SHA-256: {token.proposal_sha256}")
    if token.decision != InceptionDecision.INCEPTION_AUTHORIZED:
        raise DataContractError(f"Gate rejected proposal: {token.decision}")
    if token.authorized_hypothesis_id != "HYP_011":
        raise DataContractError("Token hypothesis mismatch.")
    if token.capital_authority_usd != Decimal("0.00"):
        raise DataContractError("Token capital must be $0.00.")
    if token.is_strategy_qualified or token.is_paper_authorized or token.is_live_authorized:
        raise DataContractError("Token must carry zero qualification/trading authority.")

    strategy_contract = build_strategy_contract()
    provider_contract = build_provider_contract()
    sample_partitions = build_sample_partitions()
    acceptance_gates = build_acceptance_gates()
    contract_hashes = {
        "strategy_specification_hash": _sha256_canonical(strategy_contract),
        "provider_contract_hash": _sha256_canonical(provider_contract),
        "sample_partition_hash": _sha256_canonical(sample_partitions),
        "gate_contract_hash": _sha256_canonical(acceptance_gates),
    }
    for key, digest in contract_hashes.items():
        print(f" -> {key}: {digest}")
    if contract_hashes["gate_contract_hash"] != (
        "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b"
    ):
        raise DataContractError(
            "Gate-contract hash differs from the frozen CORE-001 gate hash; "
            "inspect why BEFORE sealing R1 (do not force)."
        )

    hyp_sealed = dict(hyp_pre)
    hyp_sealed["state"] = "R1_PREREGISTERED_SEALED"
    hyp_sealed["registered_at_utc"] = REGISTERED_AT_UTC
    hyp_sealed["inception_token_id"] = token.token_id
    hyp_sealed["proposal_sha256"] = token.proposal_sha256
    hyp_sealed["preregistration_sha256"] = prereg_sha256
    hyp_sealed["r1_manifest"] = "docs/phase14/manifests/manifest_r1_HYP_011.json"
    hyp_path.write_text(json.dumps(hyp_sealed, indent=2), encoding="utf-8")
    hyp_sha256 = _sha256_file(hyp_path)
    print(f"\n[Step 2] HYP_011 sealed (R1_PREREGISTERED_SEALED) SHA-256: {hyp_sha256}")

    manifest_payload: Dict[str, object] = {
        "manifest_type": "HYPOTHESIS_REGISTRATION_MANIFEST",
        "hypothesis_id": "HYP_011",
        "hypothesis_ordinal": 11,
        "hypothesis_ordinal_alias": "HYP_011",
        "core_id": "CORE-001",
        "mechanism_id": None,
        "candidate_ordinal_within_core": 3,
        "canonical_title": "HYP_011 — Global 80/20 Strategic Allocation Core",
        "hypothesis_version": "v1.0",
        "hypothesis_sha256": hyp_sha256,
        "registered_at_utc": REGISTERED_AT_UTC,
        "author": "external_research_authority_specification__implementation_only_encoding",
        "target_symbol": "ACWI",
        "target_holdings": {"ACWI": 0.8, "AGG": 0.2},
        "benchmark_primary": "SPY_BUY_AND_HOLD",
        "primary_timeframe": "1Day",
        "search_trial_count_k": 1,
        "human_authorization": HUMAN_AUTHORIZATION,
        "inception_token_id": token.token_id,
        "proposal_sha256": token.proposal_sha256,
        "preregistration_sha256": prereg_sha256,
        "upstream_authority_hashes": upstream_authority_hashes,
        "contract_hashes": contract_hashes,
        "strategy_contract": strategy_contract,
        "provider_contract": provider_contract,
        "sample_partitions": sample_partitions,
        "acceptance_gates": acceptance_gates,
        "legacy_schema_semantics": "NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY",
        "predecessors": {
            "HYP_009": "TERMINAL_NOT_SUPPORTED_CANDIDATE_NOT_PARENT",
            "HYP_010": "BLOCKED_NON_FALSIFIED_CANDIDATE_NOT_PARENT",
        },
        "status": "SEALED_STEP_R1_PASS",
        "capital_authority_usd": "0.00",
        "no_real_orders": True,
        "market_data_access": "ZERO",
        "historical_data_access": "ZERO",
        "recent_stress_access": "ZERO",
        "quarantine_access": "ZERO",
        "prospective_access": "ZERO",
        "is_paper_authorized": False,
        "is_live_authorized": False,
        "next_required_step": "REVIEW_CORE_001_HYP_011_R1_AND_AUTHORIZE_PROVIDER_AND_SPONSOR_QUALIFICATION",
    }
    manifest_json = CanonicalConfigSerializer.to_canonical_json(manifest_payload)
    manifest_digest = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    manifest_payload["manifest_sha256"] = manifest_digest
    man_path = Path("docs/phase14/manifests/manifest_r1_HYP_011.json")
    man_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    print(f"[Step 3] R1 Manifest: {manifest_digest}")
    print("HYP_011 CANONICAL R1 REGISTRATION COMPLETED & SEALED!")
    return token


if __name__ == "__main__":
    register_step_r1_hyp_011()
