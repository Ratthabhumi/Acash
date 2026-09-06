"""Unit and Invariant Tests for ACASH Governance Hardening & Readiness Separation.

Strictly verifies:
1. Cross-hypothesis data quarantine: a new hypothesis cannot inherit prior datasets without explicit authorization.
2. M5 Validation/OOS holdouts from HYP_TSMOM_EURUSD_001 are permanently quarantined.
3. UNKNOWN or REVOKED dataset authorization states fail closed immediately.
4. Positive path: a valid hypothesis with explicit dataset binding passes authorization.
5. Terminally falsified hypotheses have 0 outbound transitions and cannot be reopened.
6. Mutation of sealed hypothesis parameters under the same ID is strictly forbidden.
7. Four readiness planes are decoupled: Infrastructure != Research != Alpha != Trading.
8. No single master boolean switch exists in readiness plane representation (Amendment 3).
9. Phase 13 Step 9 cannot start automatically without Phase 13 Step 8 Human GO and qualified strategy.
10. Capital authority remains strictly $0.00 during standing-by state.
11. Existing HYP_TSMOM_EURUSD_001 sealed lineage remains immutable and readable.
"""

from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Dict
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.readiness_planes import (
    HumanGOCheckpointState,
    InfrastructureReadinessState,
    ReadinessPlaneEvaluator,
    ResearchEngineReadinessState,
    StrategyAlphaReadinessState,
    SystemReadinessPlanes,
    TradingCapitalAuthorityState,
)
from acash.research.alpha_schema import (
    AlphaLifecycleState,
    validate_hypothesis_immutability,
    validate_lifecycle_transition,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.quarantine import (
    DatasetAvailabilityPlane,
    DatasetExposureState,
    DatasetQuarantineValidator,
)
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
)


@pytest.fixture
def sealed_hyp_spec() -> HypothesisSpecification:
    """Load canonical sealed HYP_TSMOM_EURUSD_001 specification."""
    hyp_path = Path("docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_001.json")
    assert hyp_path.exists(), f"Sealed hypothesis not found at {hyp_path}"
    with open(hyp_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return HypothesisSpecification.model_validate(data)


@pytest.fixture
def canonical_m5_manifest() -> Dict[str, Any]:
    """Load canonical EURUSD M5 dataset manifest."""
    manifest_path = Path("docs/phase8.5/manifests/manifest-EURUSD_M5_canonical.json")
    assert manifest_path.exists(), f"Dataset manifest not found at {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data: Dict[str, Any] = json.load(f)
        return manifest_data


# ===========================================================================
# 1. Cross-Hypothesis Data Quarantine Tests
# ===========================================================================


def test_new_hypothesis_cannot_implicitly_inherit_prior_dataset(
    sealed_hyp_spec: HypothesisSpecification,
    canonical_m5_manifest: Dict[str, Any],
) -> None:
    """Invariant: A new hypothesis ID cannot execute against a dataset bound to another hypothesis."""
    # Create candidate new hypothesis
    new_spec = HypothesisSpecification(
        hypothesis_id="HYP_TSMOM_EURUSD_002",
        hypothesis_version="1.0.0",
        economic_rationale="Candidate test hypothesis",
        target_symbol="EURUSD",
        feature_dependencies=["feature_momentum_lookback"],
        parameter_config_json='{"lookback": 10}',
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1, 6],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-09-06T23:00:00+00:00",
        author="ResearchAgent",
    )

    # Attempting to bind new_spec to the M5 dataset bound to HYP_TSMOM_EURUSD_001 must fail closed
    with pytest.raises(DataContractError, match="CROSS_HYPOTHESIS_CONTAMINATION_ERROR"):
        DatasetQuarantineValidator.validate_dataset_binding_for_execution(
            spec=new_spec,
            dataset_manifest=canonical_m5_manifest,
            requested_partition="train",
        )


def test_quarantined_m5_holdout_inaccessible_to_any_new_research(
    sealed_hyp_spec: HypothesisSpecification,
    canonical_m5_manifest: Dict[str, Any],
) -> None:
    """Invariant: M5 validation and OOS holdouts from HYP_TSMOM_EURUSD_001 are permanently quarantined."""
    new_spec = HypothesisSpecification(
        hypothesis_id="HYP_MR_EURUSD_001",
        hypothesis_version="1.0.0",
        economic_rationale="Candidate mean reversion",
        target_symbol="EURUSD",
        feature_dependencies=["feature_reversal"],
        parameter_config_json='{"lookback": 5}',
        expected_direction=ExpectedDirection.SHORT,
        target_horizons=[1],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-09-06T23:00:00+00:00",
        author="ResearchAgent",
    )

    # Even if allowed_hypothesis_ids included the new hypothesis, holdout partition is quarantined
    modified_manifest = dict(canonical_m5_manifest)
    modified_manifest["allowed_hypothesis_ids"] = ["HYP_MR_EURUSD_001"]

    with pytest.raises(DataContractError, match="DATASET_QUARANTINED_ERROR"):
        DatasetQuarantineValidator.validate_dataset_binding_for_execution(
            spec=new_spec,
            dataset_manifest=modified_manifest,
            requested_partition="validation",
        )

    with pytest.raises(DataContractError, match="DATASET_QUARANTINED_ERROR"):
        DatasetQuarantineValidator.validate_dataset_binding_for_execution(
            spec=new_spec,
            dataset_manifest=modified_manifest,
            requested_partition="oos",
        )


def test_unknown_dataset_exposure_state_fails_closed(
    sealed_hyp_spec: HypothesisSpecification,
    canonical_m5_manifest: Dict[str, Any],
) -> None:
    """Invariant: Dataset with UNKNOWN exposure state fails closed immediately."""
    corrupted_manifest = dict(canonical_m5_manifest)
    corrupted_manifest["exposure_state"] = "UNKNOWN"

    with pytest.raises(DataContractError, match="DATASET_AUTHORIZATION_UNKNOWN"):
        DatasetQuarantineValidator.validate_dataset_binding_for_execution(
            spec=sealed_hyp_spec,
            dataset_manifest=corrupted_manifest,
            requested_partition="train",
        )


def test_revoked_dataset_exposure_state_fails_closed(
    sealed_hyp_spec: HypothesisSpecification,
    canonical_m5_manifest: Dict[str, Any],
) -> None:
    """Invariant: Dataset with REVOKED exposure state fails closed immediately."""
    corrupted_manifest = dict(canonical_m5_manifest)
    corrupted_manifest["exposure_state"] = "REVOKED"

    with pytest.raises(DataContractError, match="DATASET_AUTHORIZATION_REVOKED"):
        DatasetQuarantineValidator.validate_dataset_binding_for_execution(
            spec=sealed_hyp_spec,
            dataset_manifest=corrupted_manifest,
            requested_partition="train",
        )


def test_positive_path_authorized_hypothesis_dataset_passes(
    sealed_hyp_spec: HypothesisSpecification,
    canonical_m5_manifest: Dict[str, Any],
) -> None:
    """Positive Path: Properly bound and authorized hypothesis passes dataset validation for training."""
    # HYP_TSMOM_EURUSD_001 is the authorized hypothesis for the M5 train partition
    DatasetQuarantineValidator.validate_dataset_binding_for_execution(
        spec=sealed_hyp_spec,
        dataset_manifest=canonical_m5_manifest,
        requested_partition="train",
    )


# ===========================================================================
# 2. Hypothesis Immutability & Lifecycle Safety Tests
# ===========================================================================


def test_terminally_falsified_hypothesis_cannot_be_reopened() -> None:
    """Invariant: TERMINALLY_FALSIFIED has strictly 0 allowed outbound transitions."""
    # Legal transitions to TERMINALLY_FALSIFIED
    validate_lifecycle_transition(
        current_state=AlphaLifecycleState.RESEARCH_SEARCH,
        target_state=AlphaLifecycleState.TERMINALLY_FALSIFIED,
    )
    validate_lifecycle_transition(
        current_state=AlphaLifecycleState.CANDIDATE,
        target_state=AlphaLifecycleState.TERMINALLY_FALSIFIED,
    )

    # Illegal transition: attempting to reopen or transition out of TERMINALLY_FALSIFIED fails closed
    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        validate_lifecycle_transition(
            current_state=AlphaLifecycleState.TERMINALLY_FALSIFIED,
            target_state=AlphaLifecycleState.RESEARCH_SEARCH,
        )

    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        validate_lifecycle_transition(
            current_state=AlphaLifecycleState.TERMINALLY_FALSIFIED,
            target_state=AlphaLifecycleState.HYPOTHESIS,
        )


def test_sealed_hypothesis_parameter_mutation_fails_closed(
    sealed_hyp_spec: HypothesisSpecification,
) -> None:
    """Invariant: Re-registering an existing hypothesis ID with modified parameters is strictly blocked."""
    # Attempt to modify lookbacks under the same hypothesis ID
    mutated_spec = HypothesisSpecification(
        hypothesis_id=sealed_hyp_spec.hypothesis_id,
        hypothesis_version=sealed_hyp_spec.hypothesis_version,
        economic_rationale=sealed_hyp_spec.economic_rationale,
        target_symbol=sealed_hyp_spec.target_symbol,
        feature_dependencies=sealed_hyp_spec.feature_dependencies,
        parameter_config_json='{"lookback_grid": [10, 20, 30]}',  # Mutated parameters!
        expected_direction=sealed_hyp_spec.expected_direction,
        target_horizons=sealed_hyp_spec.target_horizons,
        primary_horizon=sealed_hyp_spec.primary_horizon,
        invalidation_criteria=sealed_hyp_spec.invalidation_criteria,
        registered_at_utc=sealed_hyp_spec.registered_at_utc,
        author=sealed_hyp_spec.author,
    )

    with pytest.raises(DataContractError, match="HYPOTHESIS_MUTATION_FORBIDDEN"):
        validate_hypothesis_immutability(existing_spec=sealed_hyp_spec, candidate_spec=mutated_spec)


def test_current_hyp_tsmom_eurusd_001_lineage_remains_immutable_and_readable(
    sealed_hyp_spec: HypothesisSpecification,
) -> None:
    """Invariant: Upstream sealed hypothesis SHA-256 digest remains verifiable and exact."""
    expected_digest = "5afb92d7175721872d51ab82b2ebaaaa353c2d21bcbbd596e8bf1a3c52de0ef4"
    digest = calculate_hypothesis_spec_sha256(sealed_hyp_spec)
    assert digest == expected_digest, f"Digest mismatch: {digest} != {expected_digest}"


# ===========================================================================
# 3. Four Readiness Planes Decoupling Tests
# ===========================================================================


def test_no_single_master_switch_in_readiness_planes() -> None:
    """Invariant (Amendment 3): SystemReadinessPlanes has no single master boolean switch."""
    planes = SystemReadinessPlanes(
        infrastructure=InfrastructureReadinessState.SOAK_VERIFIED_PASS,
        research_engine=ResearchEngineReadinessState.ENGINE_VERIFIED_PASS,
        strategy_alpha=StrategyAlphaReadinessState.UNPROVEN_ZERO_QUALIFIED,
        trading_authority=TradingCapitalAuthorityState.HARD_LOCKED_ZERO_CAPITAL,
        human_go=HumanGOCheckpointState.LOCKED_PENDING_PREREQUISITES,
        capital_authority_usd=Decimal("0.00"),
    )

    # Assert no 'system_ready' or 'is_ready' attributes exist
    assert not hasattr(planes, "system_ready"), "Single master switch 'system_ready' must not exist!"
    assert not hasattr(planes, "is_ready"), "Single master switch 'is_ready' must not exist!"


def test_infrastructure_ready_cannot_authorize_trading() -> None:
    """Invariant: Infrastructure SOAK_VERIFIED_PASS alone cannot authorize trading or capital."""
    planes = SystemReadinessPlanes(
        infrastructure=InfrastructureReadinessState.SOAK_VERIFIED_PASS,
        research_engine=ResearchEngineReadinessState.ENGINE_VERIFIED_PASS,
        strategy_alpha=StrategyAlphaReadinessState.TERMINALLY_FALSIFIED,
        trading_authority=TradingCapitalAuthorityState.HARD_LOCKED_ZERO_CAPITAL,
        human_go=HumanGOCheckpointState.LOCKED_PENDING_PREREQUISITES,
        capital_authority_usd=Decimal("0.00"),
    )

    # Cannot transition to Phase 13 Step 9
    with pytest.raises(DataContractError, match="STEP9_PRECONDITION_FAILED"):
        ReadinessPlaneEvaluator.validate_step9_continuous_paper_transition(planes)

    # Cannot allocate capital > $0.00
    with pytest.raises(DataContractError, match="CAPITAL_ALLOCATION_REJECTED"):
        ReadinessPlaneEvaluator.validate_capital_authority_boundary(planes, requested_capital_usd=Decimal("100.00"))


def test_alpha_qualification_cannot_authorize_capital_without_human_go() -> None:
    """Invariant: Strategy RESEARCH_QUALIFIED cannot allocate capital without Phase 13 Step 8 Human GO."""
    planes = SystemReadinessPlanes(
        infrastructure=InfrastructureReadinessState.SOAK_VERIFIED_PASS,
        research_engine=ResearchEngineReadinessState.ENGINE_VERIFIED_PASS,
        strategy_alpha=StrategyAlphaReadinessState.RESEARCH_QUALIFIED,
        trading_authority=TradingCapitalAuthorityState.PAPER_AUTHORIZED_PENDING_GATE_B,
        human_go=HumanGOCheckpointState.LOCKED_PENDING_PREREQUISITES,  # Human GO locked!
        capital_authority_usd=Decimal("0.00"),
    )

    # Attempting to allocate positive capital fails closed
    with pytest.raises(DataContractError, match="CAPITAL_ALLOCATION_REJECTED"):
        ReadinessPlaneEvaluator.validate_capital_authority_boundary(planes, requested_capital_usd=Decimal("500.00"))

    # Attempting to start Step 9 fails closed
    with pytest.raises(DataContractError, match="STEP9_PRECONDITION_FAILED"):
        ReadinessPlaneEvaluator.validate_step9_continuous_paper_transition(planes)


def test_standing_by_state_enforces_zero_capital_authority() -> None:
    """Invariant: Standing by state strictly enforces capital_authority_usd == Decimal('0.00')."""
    standing_by_planes = SystemReadinessPlanes(
        infrastructure=InfrastructureReadinessState.SOAK_VERIFIED_PASS,
        research_engine=ResearchEngineReadinessState.ENGINE_VERIFIED_PASS,
        strategy_alpha=StrategyAlphaReadinessState.TERMINALLY_FALSIFIED,
        trading_authority=TradingCapitalAuthorityState.HARD_LOCKED_ZERO_CAPITAL,
        human_go=HumanGOCheckpointState.LOCKED_PENDING_PREREQUISITES,
        capital_authority_usd=Decimal("0.00"),
    )

    # Zero capital is valid and accepted
    ReadinessPlaneEvaluator.validate_capital_authority_boundary(
        standing_by_planes,
        requested_capital_usd=Decimal("0.00"),
    )
    assert standing_by_planes.capital_authority_usd == Decimal("0.00")
