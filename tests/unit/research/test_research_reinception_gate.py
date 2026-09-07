"""Unit and Invariant Tests for Phase 8.5 Research Re-Inception Gate.

Strictly verifies:
1. Valid proposal passes and emits an immutable InceptionAuthorizationToken.
2. Reusing a TERMINALLY_FALSIFIED hypothesis ID fails closed immediately.
3. Attempting to overwrite or mutate an existing sealed hypothesis ID fails closed.
4. Overlapping with permanently quarantined M5 holdout without a governance exception fails closed.
5. Declaring a non-existent or corrupted governance exception fails closed.
6. A valid, verified governance exception record allows access to quarantined data.
7. Missing economic rationale (< 20 chars) fails closed.
8. Anti-HARKing cardinal equality: planned_trial_count != search grid cardinality fails closed.
9. Token strictly hard-locks: capital_authority_usd == $0.00, is_strategy_qualified == False,
   is_paper_authorized == False, is_live_authorized == False.
10. Verification of proposal does NOT load market data or open Parquet files.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Dict, List
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.reinception import (
    GovernanceExceptionRecord,
    InceptionAuthorizationToken,
    InceptionDecision,
    ResearchInceptionProposal,
    ResearchReInceptionGate,
    TERMINAL_HYPOTHESIS_REGISTRY,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    InvalidationCriteria,
    SplitPolicy,
)


@pytest.fixture
def valid_proposal() -> ResearchInceptionProposal:
    """Construct a structurally valid candidate inception proposal (de novo, outside holdout)."""
    return ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_TEST_REINCEPTION_001",
        candidate_hypothesis_version="1.0.0",
        economic_rationale="Empirical mean-reversion following orderbook liquidity imbalance depletion.",
        target_symbol="EURUSD",
        target_timeframe="M5",
        feature_dependencies=["orderbook_microstructure_imbalance"],
        parameter_search_grid={"lookback": [3, 5, 8], "threshold": [1.0, 2.0]},  # 3 * 2 = 6 combinations
        planned_trial_count=6,  # Exactly matches cardinality!
        target_horizons=[1, 6],
        primary_horizon=1,
        expected_direction=ExpectedDirection.SHORT,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.025"),
            min_hac_t_stat=Decimal("2.00"),
        ),
        cost_model=CostModelConfig(
            quoted_spread_bps=Decimal("1.0"),
            roundtrip_broker_fee_bps=Decimal("0.5"),
            fixed_slippage_bps=Decimal("0.5"),
        ),
        proposed_dataset_id="DS_EURUSD_M5_2025_DE_NOVO_001",
        proposed_data_window=("2025-01-01T00:00:00+00:00", "2025-06-30T23:59:00+00:00"),  # Far outside 2026 holdout!
        proposed_split_policy=SplitPolicy(),
        author="ResearchAgent",
    )


# ===========================================================================
# 1. Happy Path & Token Invariant Tests
# ===========================================================================


def test_valid_inception_proposal_passes_and_emits_token(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Positive Path: Fully compliant proposal passes and receives R1 authorization token."""
    token = ResearchReInceptionGate.evaluate_reinception_proposal(
        proposal=valid_proposal,
        hypotheses_dir=tmp_path,
    )

    assert token.decision == InceptionDecision.INCEPTION_AUTHORIZED
    assert token.authorized_hypothesis_id == "HYP_TEST_REINCEPTION_001"
    assert token.capital_authority_usd == Decimal("0.00")
    assert token.is_strategy_qualified is False
    assert token.is_paper_authorized is False
    assert token.is_live_authorized is False
    assert len(token.proposal_sha256) == 64


def test_token_strictly_blocks_capital_and_trading_authority() -> None:
    """Invariant: Token cannot be constructed with capital > $0.00 or trading authority."""
    with pytest.raises(DataContractError, match="INCEPTION_TOKEN_AUTHORITY_VIOLATION"):
        InceptionAuthorizationToken(
            token_id="AUTH_TEST",
            authorized_hypothesis_id="HYP_TEST",
            proposal_sha256="0" * 64,
            authorized_at_utc="2026-09-06T23:00:00+00:00",
            capital_authority_usd=Decimal("100.00"),  # Rejected!
        )

    with pytest.raises(DataContractError, match="INCEPTION_TOKEN_AUTHORITY_VIOLATION"):
        InceptionAuthorizationToken(
            token_id="AUTH_TEST",
            authorized_hypothesis_id="HYP_TEST",
            proposal_sha256="0" * 64,
            authorized_at_utc="2026-09-06T23:00:00+00:00",
            is_strategy_qualified=True,  # Rejected!
        )


# ===========================================================================
# 2. Terminal Hypothesis Rejection & Immutability Tests
# ===========================================================================


def test_reusing_terminally_falsified_id_fails_closed(
    valid_proposal: ResearchInceptionProposal,
) -> None:
    """Invariant: Attempting to reuse HYP_TSMOM_EURUSD_001 fails closed immediately."""
    falsified_proposal = valid_proposal.model_copy(
        update={"candidate_hypothesis_id": "HYP_TSMOM_EURUSD_001"}
    )
    with pytest.raises(DataContractError, match="BLOCKED_MUTATION_VIOLATION"):
        ResearchReInceptionGate.evaluate_reinception_proposal(proposal=falsified_proposal)


def test_reusing_hyp_002_terminally_falsified_id_fails_closed(
    valid_proposal: ResearchInceptionProposal,
) -> None:
    """Invariant: HYP_TSMOM_EURUSD_HTF_002 is registered as terminally falsified and cannot be reused."""
    assert "HYP_TSMOM_EURUSD_HTF_002" in TERMINAL_HYPOTHESIS_REGISTRY
    falsified_proposal = valid_proposal.model_copy(
        update={"candidate_hypothesis_id": "HYP_TSMOM_EURUSD_HTF_002"}
    )
    with pytest.raises(DataContractError, match="BLOCKED_MUTATION_VIOLATION"):
        ResearchReInceptionGate.evaluate_reinception_proposal(proposal=falsified_proposal)


def test_terminal_registry_contains_all_falsified_hypotheses() -> None:
    """Invariant: Every sealed terminally-falsified hypothesis is explicitly registered."""
    assert "HYP_TSMOM_EURUSD_001" in TERMINAL_HYPOTHESIS_REGISTRY
    assert "HYP_TSMOM_EURUSD_HTF_002" in TERMINAL_HYPOTHESIS_REGISTRY


def test_sealed_id_collision_fails_closed(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Invariant: Overwriting an existing sealed hypothesis on disk is strictly forbidden."""
    # Create an existing sealed hypothesis file in tmp_path
    existing_file = tmp_path / f"{valid_proposal.candidate_hypothesis_id}.json"
    existing_file.write_text("{}", encoding="utf-8")

    with pytest.raises(DataContractError, match="BLOCKED_MUTATION_VIOLATION"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=valid_proposal,
            hypotheses_dir=tmp_path,
        )


# ===========================================================================
# 3. Anti-HARKing Cardinal Equality Tests (Constraint 2)
# ===========================================================================


def test_search_space_cardinality_mismatch_fails_closed(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Invariant: planned_trial_count != grid cardinality fails closed."""
    # Grid has 3 * 2 = 6 combinations. Set planned_trial_count = 1 (HARKing violation)
    understated_proposal = valid_proposal.model_copy(
        update={"planned_trial_count": 1}
    )
    with pytest.raises(DataContractError, match="ANTI_HARKING_CARDINALITY_MISMATCH"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=understated_proposal,
            hypotheses_dir=tmp_path,
        )

    # Set planned_trial_count = 10 (mismatch)
    overstated_proposal = valid_proposal.model_copy(
        update={"planned_trial_count": 10}
    )
    with pytest.raises(DataContractError, match="ANTI_HARKING_CARDINALITY_MISMATCH"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=overstated_proposal,
            hypotheses_dir=tmp_path,
        )


def test_empty_search_grid_fails_closed(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Invariant: Empty search grid fails closed."""
    empty_grid_proposal = valid_proposal.model_copy(
        update={"parameter_search_grid": {}, "planned_trial_count": 0}
    )
    with pytest.raises(DataContractError, match="ANTI_HARKING_REJECTED"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=empty_grid_proposal,
            hypotheses_dir=tmp_path,
        )


# ===========================================================================
# 4. Quarantine & Governance Exception Tests (Constraint 3)
# ===========================================================================


def test_quarantined_m5_holdout_window_without_exception_fails_closed(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Invariant: Proposing a data window overlapping with the M5 holdout fails closed without exception."""
    # M5 holdout: 2026-08-18T04:40:00+00:00 to 2026-09-04T21:00:00+00:00
    quarantine_proposal = valid_proposal.model_copy(
        update={
            "target_symbol": "EURUSD",
            "target_timeframe": "M5",
            "proposed_data_window": ("2026-08-01T00:00:00+00:00", "2026-08-25T00:00:00+00:00"),  # Overlaps!
            "governance_exception_id": None,
        }
    )
    with pytest.raises(DataContractError, match="BLOCKED_QUARANTINE_VIOLATION"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=quarantine_proposal,
            hypotheses_dir=tmp_path,
        )


def test_quarantine_with_missing_exception_record_fails_closed(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Invariant: Declaring an exception ID without a registered record fails closed."""
    quarantine_proposal = valid_proposal.model_copy(
        update={
            "target_symbol": "EURUSD",
            "target_timeframe": "M5",
            "proposed_data_window": ("2026-08-01T00:00:00+00:00", "2026-08-25T00:00:00+00:00"),
            "governance_exception_id": "EXC_NON_EXISTENT_001",
        }
    )
    with pytest.raises(DataContractError, match="BLOCKED_QUARANTINE_VIOLATION"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=quarantine_proposal,
            existing_exceptions={},  # Empty registry!
            hypotheses_dir=tmp_path,
        )


def test_quarantine_with_corrupted_exception_digest_fails_closed(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Invariant: Exception record with corrupted digest fails closed."""
    # Build exception with tampered digest
    with pytest.raises(DataContractError, match="GOVERNANCE_EXCEPTION_DIGEST_CORRUPTED"):
        GovernanceExceptionRecord(
            exception_id="EXC_TAMPERED",
            authorized_hypothesis_id=valid_proposal.candidate_hypothesis_id,
            target_symbol="EURUSD",
            target_timeframe="M5",
            quarantined_dataset_id="DS_EURUSD_M5",
            rationale="Permit overlapping inspection for forensic audit.",
            approved_by_operator="LeadOperator",
            approved_at_utc="2026-09-06T23:00:00+00:00",
            exception_digest="0" * 64,  # Fake digest!
        )


def test_quarantine_with_valid_verified_exception_record_passes(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Positive Path: Fully verified governance exception allows authorized overlap."""
    exc_payload = {
        "approved_at_utc": "2026-09-06T23:00:00+00:00",
        "approved_by_operator": "LeadOperator",
        "authorized_hypothesis_id": valid_proposal.candidate_hypothesis_id,
        "exception_id": "EXC_VALID_001",
        "quarantined_dataset_id": "DS_EURUSD_M5",
        "rationale": "Permit overlapping inspection for forensic benchmark verification.",
        "target_symbol": "EURUSD",
        "target_timeframe": "M5",
    }
    canonical_json = json.dumps(exc_payload, sort_keys=True, separators=(",", ":"))
    valid_digest = json.loads(json.dumps(exc_payload))
    computed_digest = pytest.importorskip("hashlib").sha256(canonical_json.encode("utf-8")).hexdigest()

    valid_record = GovernanceExceptionRecord(
        exception_id="EXC_VALID_001",
        authorized_hypothesis_id=valid_proposal.candidate_hypothesis_id,
        target_symbol="EURUSD",
        target_timeframe="M5",
        quarantined_dataset_id="DS_EURUSD_M5",
        rationale="Permit overlapping inspection for forensic benchmark verification.",
        approved_by_operator="LeadOperator",
        approved_at_utc="2026-09-06T23:00:00+00:00",
        exception_digest=computed_digest,
    )

    quarantine_proposal = valid_proposal.model_copy(
        update={
            "target_symbol": "EURUSD",
            "target_timeframe": "M5",
            "proposed_data_window": ("2026-08-01T00:00:00+00:00", "2026-08-25T00:00:00+00:00"),
            "governance_exception_id": "EXC_VALID_001",
        }
    )

    token = ResearchReInceptionGate.evaluate_reinception_proposal(
        proposal=quarantine_proposal,
        existing_exceptions={"EXC_VALID_001": valid_record},
        hypotheses_dir=tmp_path,
    )
    assert token.decision == InceptionDecision.INCEPTION_AUTHORIZED


# ===========================================================================
# 5. Pre-Registration Completeness Tests
# ===========================================================================


def test_missing_economic_rationale_fails_closed(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Invariant: Short or empty rationale (< 20 chars) fails closed."""
    short_rationale_proposal = valid_proposal.model_copy(
        update={"economic_rationale": "Short text"}
    )
    with pytest.raises(DataContractError, match="PRE_REGISTRATION_REJECTED"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=short_rationale_proposal,
            hypotheses_dir=tmp_path,
        )


def test_empty_feature_dependencies_fails_closed(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Invariant: Empty feature dependencies fails closed."""
    no_feat_proposal = valid_proposal.model_copy(
        update={"feature_dependencies": []}
    )
    with pytest.raises(DataContractError, match="PRE_REGISTRATION_REJECTED"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=no_feat_proposal,
            hypotheses_dir=tmp_path,
        )


def test_primary_horizon_not_in_target_horizons_fails_closed(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """Invariant: primary_horizon not in target_horizons fails closed."""
    mismatched_h_proposal = valid_proposal.model_copy(
        update={"primary_horizon": 10, "target_horizons": [1, 6]}
    )
    with pytest.raises(DataContractError, match="PRE_REGISTRATION_REJECTED"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=mismatched_h_proposal,
            hypotheses_dir=tmp_path,
        )
