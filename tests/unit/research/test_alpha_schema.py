"""Unit & Adversarial Tests for Phase 8.5 Domain Contracts & State Machine (Slice 1).

Covers:
- AlphaLifecycleState enum completeness and discrete definitions.
- Deterministic forward lifecycle transitions and illegal transition rejection.
- Terminal-state finality and zero retrospective mutation.
- AlphaEconomicDecomposition arithmetic invariants and rebate isolation.
- AlphaFalsificationTrigger immutability and evaluation models.
- AlphaQualificationDossier cryptographic DAG, SHA-256 validation, and zero capital authority ($0.00).
- Strict separation: RESEARCH_QUALIFIED != Live execution authorization.
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from acash.core.domain.exceptions import DataContractError
from acash.research.alpha_schema import (
    ALLOWED_LIFECYCLE_TRANSITIONS,
    AlphaEconomicDecomposition,
    AlphaFalsificationTrigger,
    AlphaLifecycleState,
    AlphaQualificationDossier,
    FalsificationComparisonOperator,
    validate_lifecycle_transition,
)


# ---------------------------------------------------------------------------
# 1. Lifecycle State Machine Tests
# ---------------------------------------------------------------------------


def test_alpha_lifecycle_state_enum_completeness() -> None:
    """Verify all 11 core, rejection, and terminal states are uniquely defined."""
    expected_states = {
        "HYPOTHESIS",
        "RESEARCH_SEARCH",
        "CANDIDATE",
        "STATISTICAL_VALIDATED",
        "ECONOMIC_EDGE_QUALIFIED",
        "FORWARD_PAPER_MONITORED",
        "RESEARCH_QUALIFIED",
        "REJECTED_STATISTICAL_GATE",
        "REJECTED_HURDLE_COLLAPSE",
        "DEGRADED_FORWARD_TEST",
        "RETIRED_STRUCTURAL_BREAK",
    }
    actual_states = {s.value for s in AlphaLifecycleState}
    assert actual_states == expected_states
    assert len(AlphaLifecycleState) == 11


def test_valid_forward_lifecycle_transitions() -> None:
    """Verify standard happy-path progression through the research lifecycle."""
    progression = [
        AlphaLifecycleState.HYPOTHESIS,
        AlphaLifecycleState.RESEARCH_SEARCH,
        AlphaLifecycleState.CANDIDATE,
        AlphaLifecycleState.STATISTICAL_VALIDATED,
        AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED,
        AlphaLifecycleState.FORWARD_PAPER_MONITORED,
        AlphaLifecycleState.RESEARCH_QUALIFIED,
        AlphaLifecycleState.RETIRED_STRUCTURAL_BREAK,
    ]
    for i in range(len(progression) - 1):
        validate_lifecycle_transition(progression[i], progression[i + 1])

    # Self-transition (idempotent)
    for state in AlphaLifecycleState:
        validate_lifecycle_transition(state, state)


def test_valid_rejection_and_degradation_branches() -> None:
    """Verify deterministic transition to all failure/rejection states."""
    # CANDIDATE -> REJECTED_STATISTICAL_GATE
    validate_lifecycle_transition(
        AlphaLifecycleState.CANDIDATE,
        AlphaLifecycleState.REJECTED_STATISTICAL_GATE,
    )
    # STATISTICAL_VALIDATED -> REJECTED_HURDLE_COLLAPSE
    validate_lifecycle_transition(
        AlphaLifecycleState.STATISTICAL_VALIDATED,
        AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE,
    )
    # ECONOMIC_EDGE_QUALIFIED -> DEGRADED_FORWARD_TEST
    validate_lifecycle_transition(
        AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED,
        AlphaLifecycleState.DEGRADED_FORWARD_TEST,
    )
    # FORWARD_PAPER_MONITORED -> DEGRADED_FORWARD_TEST
    validate_lifecycle_transition(
        AlphaLifecycleState.FORWARD_PAPER_MONITORED,
        AlphaLifecycleState.DEGRADED_FORWARD_TEST,
    )


def test_invalid_lifecycle_skipping_transitions_raise() -> None:
    """Verify that jumping stages or skipping gates is strictly rejected (Fail-Closed)."""
    # Direct jump from HYPOTHESIS to RESEARCH_QUALIFIED
    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        validate_lifecycle_transition(
            AlphaLifecycleState.HYPOTHESIS,
            AlphaLifecycleState.RESEARCH_QUALIFIED,
        )

    # Jumping from RESEARCH_SEARCH directly to STATISTICAL_VALIDATED without sealed CANDIDATE
    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        validate_lifecycle_transition(
            AlphaLifecycleState.RESEARCH_SEARCH,
            AlphaLifecycleState.STATISTICAL_VALIDATED,
        )

    # Jumping from CANDIDATE to ECONOMIC_EDGE_QUALIFIED without STATISTICAL_VALIDATED
    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        validate_lifecycle_transition(
            AlphaLifecycleState.CANDIDATE,
            AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED,
        )


def test_retrospective_and_backwards_transitions_rejected() -> None:
    """Verify that no backward state transitions are permitted (No retrospective mutation)."""
    backwards_pairs = [
        (AlphaLifecycleState.RESEARCH_QUALIFIED, AlphaLifecycleState.HYPOTHESIS),
        (AlphaLifecycleState.FORWARD_PAPER_MONITORED, AlphaLifecycleState.STATISTICAL_VALIDATED),
        (AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED, AlphaLifecycleState.RESEARCH_SEARCH),
        (AlphaLifecycleState.STATISTICAL_VALIDATED, AlphaLifecycleState.CANDIDATE),
        (AlphaLifecycleState.CANDIDATE, AlphaLifecycleState.HYPOTHESIS),
    ]
    for from_state, to_state in backwards_pairs:
        with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
            validate_lifecycle_transition(from_state, to_state)


def test_terminal_and_rejection_states_have_zero_outbound_transitions() -> None:
    """Verify that once rejected, degraded, or retired, a candidate cannot be revived."""
    terminal_states = [
        AlphaLifecycleState.REJECTED_STATISTICAL_GATE,
        AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE,
        AlphaLifecycleState.DEGRADED_FORWARD_TEST,
        AlphaLifecycleState.RETIRED_STRUCTURAL_BREAK,
    ]
    for term_state in terminal_states:
        assert len(ALLOWED_LIFECYCLE_TRANSITIONS[term_state]) == 0
        for target_state in AlphaLifecycleState:
            if target_state != term_state:
                with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
                    validate_lifecycle_transition(term_state, target_state)


# ---------------------------------------------------------------------------
# 2. Economic Decomposition & Rebate Isolation Tests
# ---------------------------------------------------------------------------


def test_alpha_economic_decomposition_valid_arithmetic() -> None:
    """Verify exact economic decomposition arithmetic and properties."""
    decomp = AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal("15.0"),
        realized_spread_slippage_bps=Decimal("2.5"),
        broker_commissions_bps=Decimal("1.5"),
        net_trading_alpha_bps=Decimal("11.0"),  # 15.0 - (2.5 + 1.5) = 11.0
        broker_rebate_income_bps=Decimal("3.0"),
        total_realized_economic_bps=Decimal("14.0"),  # 11.0 + 3.0 = 14.0
    )
    assert decomp.gross_trading_pnl_bps == Decimal("15.0")
    assert decomp.net_trading_alpha_bps == Decimal("11.0")
    assert decomp.total_realized_economic_bps == Decimal("14.0")

    # Viability tested against hurdle (e.g. 5.0 bps)
    assert decomp.is_economically_viable(hurdle_rate_bps=Decimal("5.0")) is True
    assert decomp.is_economically_viable(hurdle_rate_bps=Decimal("12.0")) is False


def test_rebate_cannot_rescue_negative_alpha_strategy() -> None:
    """Critical Invariant: Positive rebates cannot make a negative-alpha strategy viable."""
    decomp = AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal("3.0"),
        realized_spread_slippage_bps=Decimal("4.0"),
        broker_commissions_bps=Decimal("1.0"),
        net_trading_alpha_bps=Decimal("-2.0"),  # 3.0 - 5.0 = -2.0 (Bleeding strategy)
        broker_rebate_income_bps=Decimal("10.0"),  # Huge broker rebate subsidy
        total_realized_economic_bps=Decimal("8.0"),  # -2.0 + 10.0 = +8.0 (Looks profitable!)
    )
    # Total economic return is positive (+8.0 bps)
    assert decomp.total_realized_economic_bps == Decimal("8.0")
    # But net trading alpha is negative (-2.0 bps)
    assert decomp.net_trading_alpha_bps == Decimal("-2.0")

    # Invariant: Must fail hurdle (even a 0.0 bps hurdle!)
    assert decomp.is_economically_viable(hurdle_rate_bps=Decimal("0.0")) is False
    assert decomp.is_economically_viable(hurdle_rate_bps=Decimal("1.0")) is False


def test_economic_decomposition_arithmetic_violations_raise() -> None:
    """Verify that inconsistent or fabricated net/total values raise DataContractError."""
    # Net alpha fabricated (15.0 - 4.0 != 12.0)
    with pytest.raises(DataContractError, match="Economic arithmetic violation: net_trading_alpha_bps"):
        AlphaEconomicDecomposition(
            gross_trading_pnl_bps=Decimal("15.0"),
            realized_spread_slippage_bps=Decimal("2.5"),
            broker_commissions_bps=Decimal("1.5"),
            net_trading_alpha_bps=Decimal("12.0"),  # False value!
            broker_rebate_income_bps=Decimal("3.0"),
            total_realized_economic_bps=Decimal("15.0"),
        )

    # Total economic result fabricated (11.0 + 3.0 != 20.0)
    with pytest.raises(DataContractError, match="Economic arithmetic violation: total_realized_economic_bps"):
        AlphaEconomicDecomposition(
            gross_trading_pnl_bps=Decimal("15.0"),
            realized_spread_slippage_bps=Decimal("2.5"),
            broker_commissions_bps=Decimal("1.5"),
            net_trading_alpha_bps=Decimal("11.0"),
            broker_rebate_income_bps=Decimal("3.0"),
            total_realized_economic_bps=Decimal("20.0"),  # False value!
        )


def test_economic_decomposition_negative_friction_rejected() -> None:
    """Verify negative spread, commissions, or rebates are rejected."""
    with pytest.raises((DataContractError, ValidationError)):
        AlphaEconomicDecomposition(
            gross_trading_pnl_bps=Decimal("10.0"),
            realized_spread_slippage_bps=Decimal("-1.0"),  # Negative spread illegal
            broker_commissions_bps=Decimal("0.0"),
            net_trading_alpha_bps=Decimal("11.0"),
            broker_rebate_income_bps=Decimal("0.0"),
            total_realized_economic_bps=Decimal("11.0"),
        )


# ---------------------------------------------------------------------------
# 3. Computable Falsification Trigger Tests
# ---------------------------------------------------------------------------


def test_alpha_falsification_trigger_immutability() -> None:
    """Verify AlphaFalsificationTrigger fields, immutability, and validation."""
    trigger = AlphaFalsificationTrigger(
        trigger_name="OOS_RANK_IC_DEGRADATION",
        metric_name="spearman_rank_ic",
        threshold_value=Decimal("0.02"),
        comparison_operator=FalsificationComparisonOperator.LESS_THAN,
        is_triggered=False,
        observed_value=Decimal("0.045"),
        trigger_reason=None,
    )
    assert trigger.trigger_name == "OOS_RANK_IC_DEGRADATION"
    assert trigger.is_triggered is False

    # Immutability check: modifying frozen instance raises ValidationError
    with pytest.raises(ValidationError, match="Instance is frozen"):
        trigger.is_triggered = True


# ---------------------------------------------------------------------------
# 4. Alpha Qualification Dossier & Lineage Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def canonical_dossier_fixture() -> AlphaQualificationDossier:
    """Generate a canonical valid AlphaQualificationDossier."""
    decomp = AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal("15.0"),
        realized_spread_slippage_bps=Decimal("2.5"),
        broker_commissions_bps=Decimal("1.5"),
        net_trading_alpha_bps=Decimal("11.0"),
        broker_rebate_income_bps=Decimal("0.0"),
        total_realized_economic_bps=Decimal("11.0"),
    )
    trigger = AlphaFalsificationTrigger(
        trigger_name="MAX_DRAWDOWN_LIMIT",
        metric_name="max_drawdown_pct",
        threshold_value=Decimal("10.0"),
        comparison_operator=FalsificationComparisonOperator.GREATER_THAN,
        is_triggered=False,
        observed_value=Decimal("4.2"),
    )
    dossier = AlphaQualificationDossier(
        alpha_id="ALPHA_MOM_VOL_FILTER_V1",
        strategy_id="STRAT_MOM_001",
        lifecycle_state=AlphaLifecycleState.RESEARCH_QUALIFIED,
        hypothesis_digest="a" * 64,
        trial_ledger_digest="b" * 64,
        validation_report_digest="c" * 64,
        governance_policy_digest="d" * 64,
        economic_decomposition=decomp,
        falsification_triggers=(trigger,),
        governance_policy_version="v1.0",
        created_timestamp_utc="2026-09-01T12:00:00Z",
        capital_authority_usd=Decimal("0.00"),
    )
    return dossier


def test_dossier_zero_capital_authority_invariant(canonical_dossier_fixture: AlphaQualificationDossier) -> None:
    """Critical Invariant: Dossier strictly enforces capital_authority_usd == Decimal('0.00')."""
    dossier = canonical_dossier_fixture
    assert dossier.capital_authority_usd == Decimal("0.00")
    assert dossier.is_research_qualified is True

    # Attempting to assign positive capital authority raises DataContractError
    with pytest.raises((DataContractError, ValidationError)):
        AlphaQualificationDossier(
            alpha_id="ALPHA_ILLEGAL_CAPITAL",
            strategy_id="STRAT_001",
            lifecycle_state=AlphaLifecycleState.RESEARCH_QUALIFIED,
            hypothesis_digest="a" * 64,
            trial_ledger_digest="b" * 64,
            validation_report_digest="c" * 64,
            governance_policy_digest="d" * 64,
            economic_decomposition=dossier.economic_decomposition,
            created_timestamp_utc="2026-09-01T12:00:00Z",
            capital_authority_usd=Decimal("100000.00"),  # Illegal capital grant!
        )


def test_dossier_lineage_digest_computation_determinism(canonical_dossier_fixture: AlphaQualificationDossier) -> None:
    """Verify deterministic SHA-256 dossier_digest generation."""
    dossier = canonical_dossier_fixture
    digest1 = dossier.compute_dossier_digest()
    digest2 = dossier.compute_dossier_digest()
    assert len(digest1) == 64
    assert digest1 == digest2


def test_dossier_lineage_digest_pattern_validation() -> None:
    """Verify malformed SHA-256 hashes (non-64 hex) are rejected."""
    decomp = AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal("10.0"),
        realized_spread_slippage_bps=Decimal("2.0"),
        broker_commissions_bps=Decimal("1.0"),
        net_trading_alpha_bps=Decimal("7.0"),
        broker_rebate_income_bps=Decimal("0.0"),
        total_realized_economic_bps=Decimal("7.0"),
    )
    # Short hash (not 64 characters)
    with pytest.raises(ValidationError):
        AlphaQualificationDossier(
            alpha_id="ALPHA_BAD_HASH",
            strategy_id="STRAT_001",
            lifecycle_state=AlphaLifecycleState.CANDIDATE,
            hypothesis_digest="short_hash",  # Invalid!
            trial_ledger_digest="b" * 64,
            validation_report_digest="c" * 64,
            governance_policy_digest="d" * 64,
            economic_decomposition=decomp,
            created_timestamp_utc="2026-09-01T12:00:00Z",
        )


def test_dossier_extra_forbid_and_immutability(canonical_dossier_fixture: AlphaQualificationDossier) -> None:
    """Verify extra='forbid' and frozen immutability across the dossier model."""
    dossier = canonical_dossier_fixture

    # Mutation attempt: modifying frozen instance raises ValidationError
    with pytest.raises(ValidationError, match="Instance is frozen"):
        dossier.lifecycle_state = AlphaLifecycleState.RETIRED_STRUCTURAL_BREAK

    # Extra field attempt
    decomp = dossier.economic_decomposition
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AlphaQualificationDossier(
            alpha_id="ALPHA_EXTRA",
            strategy_id="STRAT_001",
            lifecycle_state=AlphaLifecycleState.CANDIDATE,
            hypothesis_digest="a" * 64,
            trial_ledger_digest="b" * 64,
            validation_report_digest="c" * 64,
            governance_policy_digest="d" * 64,
            economic_decomposition=decomp,
            created_timestamp_utc="2026-09-01T12:00:00Z",
            unauthorized_field="malicious_payload",  # type: ignore[call-arg]
        )
