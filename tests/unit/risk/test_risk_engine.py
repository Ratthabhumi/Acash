"""Unit and adversarial tests for Deterministic Risk Engine & Derisking (Slice 2).

Tests:
- Already-safe allocations emit APPROVED.
- Gross leverage, concentration, and cash buffer gating.
- EXACT_SCALE_DOWN mathematical proofs:
  - Monotonicity (w_i' <= w_i)
  - No short creation (w_i' >= 0)
  - Leverage ceiling bound (sum(w_i') <= max_gross_leverage)
  - Asset concentration bound (w_i' <= max_asset_concentration)
  - Cash buffer preservation (w_cash' >= min_cash_buffer)
  - Idempotency (scaling already-scaled weights leaves them unchanged)
- BINARY_REJECT policy (unsafe => REJECTED, 0 risky weights, 100% Cash).
- Peak-to-trough drawdown and daily loss gates.
- Margin buffer headroom check with AccountState.
- Telemetry anomaly checks (stale data, clock skew, broker disconnect).
- IRiskEngine interface compliance and float-Decimal compatibility.
- Separation of concerns (Phase 9 has zero broker transmission authority).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import pytest

from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.signal import RiskAssessment, TargetAllocation
from acash.core.interfaces.risk import IRiskEngine
from acash.risk.risk_engine import (
    DeriskEngine,
    DeterministicRiskEngine,
    calculate_exact_scale_down_factor,
)
from acash.risk.risk_schema import (
    CandidateRiskAllocation,
    DeriskPolicy,
    RiskPolicyConfig,
    RiskVerdict,
)


@pytest.fixture
def valid_sha256() -> str:
    return hashlib.sha256(b"canonical_risk_engine_fixture").hexdigest()


@pytest.fixture
def sample_portfolio_state() -> PortfolioState:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    pos_aapl = Position(
        symbol="AAPL",
        quantity=Decimal("10"),
        entry_price=Decimal("150.00"),
        current_price=Decimal("150.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=now,
    )
    # cash = 8500, positions mv = 1500, total_equity = 10000, gross_exposure = 1500, net = 1500
    return PortfolioState(
        timestamp_utc=now,
        positions={"AAPL": pos_aapl},
        cash_balance=Decimal("8500.00"),
        total_equity=Decimal("10000.00"),
        margin_used=Decimal("1500.00"),
        gross_exposure=Decimal("1500.00"),
        net_exposure=Decimal("1500.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )


@pytest.fixture
def sample_account_state() -> AccountState:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    return AccountState(
        account_id="ACC_PAPER_001",
        currency="USD",
        balance=Decimal("10000.00"),
        equity=Decimal("10000.00"),
        free_margin=Decimal("8500.00"),
        margin_level_pct=666.67,
        leverage=1.0,
        is_live=False,
        timestamp_utc=now,
    )


@pytest.fixture
def sample_candidate_allocation() -> CandidateRiskAllocation:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    digest = hashlib.sha256(b"source_decision").hexdigest()
    return CandidateRiskAllocation(
        candidate_id="CAND_001",
        strategy_id="MOM_01",
        weights={"AAPL": Decimal("0.20"), "MSFT": Decimal("0.20")},
        cash_weight=Decimal("0.60"),
        source_decision_digest=digest,
        as_of_utc=now,
    )


# ============================================================================
# 1. EXACT_SCALE_DOWN MATHEMATICAL FACTOR TESTS
# ============================================================================


def test_scale_down_factor_already_safe() -> None:
    weights = {"AAPL": Decimal("0.20"), "MSFT": Decimal("0.20")}
    alpha = calculate_exact_scale_down_factor(
        weights=weights,
        max_gross_leverage=Decimal("1.00"),
        max_asset_concentration=Decimal("0.25"),
        min_cash_buffer=Decimal("0.05"),
    )
    assert alpha == Decimal("1.0")


def test_scale_down_factor_leverage_breach() -> None:
    # Sum of weights = 1.50 > max_gross_leverage (1.00)
    weights = {"AAPL": Decimal("0.75"), "MSFT": Decimal("0.75")}
    alpha = calculate_exact_scale_down_factor(
        weights=weights,
        max_gross_leverage=Decimal("1.00"),
        max_asset_concentration=Decimal("1.00"),  # allow high conc to isolate leverage
        min_cash_buffer=Decimal("0.05"),
    )
    # alpha_lev = 1.00 / 1.50 = 2/3
    # alpha_cash = (1.0 - 0.05) / 1.50 = 0.95 / 1.50 = 19/30 (approx 0.6333)
    # min is alpha_cash = 0.6333333333333333333333333333
    expected_alpha = Decimal("0.95") / Decimal("1.50")
    assert alpha == expected_alpha
    # Proof: sum of scaled weights <= 0.95 => cash >= 0.05
    scaled_sum = sum((alpha * w for w in weights.values()), Decimal("0.0"))
    assert scaled_sum <= Decimal("0.95")


def test_scale_down_factor_concentration_breach() -> None:
    # AAPL = 0.50 > max_asset_concentration (0.25)
    weights = {"AAPL": Decimal("0.50"), "MSFT": Decimal("0.10")}
    alpha = calculate_exact_scale_down_factor(
        weights=weights,
        max_gross_leverage=Decimal("1.00"),
        max_asset_concentration=Decimal("0.25"),
        min_cash_buffer=Decimal("0.05"),
    )
    # alpha_conc = 0.25 / 0.50 = 0.50
    assert alpha == Decimal("0.50")
    # Proof: AAPL' = 0.50 * 0.50 = 0.25 <= 0.25
    assert (alpha * weights["AAPL"]) <= Decimal("0.25")


def test_scale_down_factor_zero_weights() -> None:
    weights: dict[str, Decimal] = {}
    alpha = calculate_exact_scale_down_factor(
        weights=weights,
        max_gross_leverage=Decimal("1.00"),
        max_asset_concentration=Decimal("0.25"),
        min_cash_buffer=Decimal("0.05"),
    )
    assert alpha == Decimal("1.0")


# ============================================================================
# 2. DERISK ENGINE TESTS (PROOFS & INVARIANTS)
# ============================================================================


def test_derisk_engine_exact_scale_down_properties() -> None:
    policy = RiskPolicyConfig(
        derisk_policy=DeriskPolicy.EXACT_SCALE_DOWN,
        max_gross_leverage=Decimal("0.80"),
        max_asset_concentration=Decimal("0.30"),
        min_cash_buffer=Decimal("0.20"),
    )
    # Candidate weights: AAPL=0.50, MSFT=0.50 (sum=1.00 > 0.80, conc=0.50 > 0.30)
    raw_weights = {"AAPL": Decimal("0.50"), "MSFT": Decimal("0.50")}

    adj_weights, cash_w, verdict, reason = DeriskEngine.evaluate_and_derisk(
        weights=raw_weights,
        policy=policy,
    )

    assert verdict == RiskVerdict.REDUCED
    assert reason is None

    # 1. Monotonicity: w_i' <= w_i
    for sym, raw_w in raw_weights.items():
        assert adj_weights[sym] <= raw_w

    # 2. No short creation: w_i' >= 0
    for sym, adj_w in adj_weights.items():
        assert adj_w >= Decimal("0.0")

    # 3. Leverage bounded: sum(w_i') <= max_gross_leverage (0.80)
    assert sum(adj_weights.values()) <= policy.max_gross_leverage

    # 4. Concentration bounded: w_i' <= max_asset_concentration (0.30)
    for sym, adj_w in adj_weights.items():
        assert adj_w <= policy.max_asset_concentration

    # 5. Cash buffer preserved: cash_w >= min_cash_buffer (0.20)
    assert cash_w >= policy.min_cash_buffer
    assert sum(adj_weights.values()) + cash_w == Decimal("1.00")

    # 6. Idempotency: Re-derisking the scaled weights must NOT change them
    adj_weights2, cash_w2, verdict2, reason2 = DeriskEngine.evaluate_and_derisk(
        weights=adj_weights,
        policy=policy,
    )
    assert verdict2 == RiskVerdict.APPROVED  # Already safe!
    assert adj_weights2 == adj_weights
    assert cash_w2 == cash_w


def test_derisk_engine_binary_reject() -> None:
    policy = RiskPolicyConfig(
        derisk_policy=DeriskPolicy.BINARY_REJECT,
        max_gross_leverage=Decimal("0.80"),
        max_asset_concentration=Decimal("0.25"),
        min_cash_buffer=Decimal("0.20"),
    )
    raw_weights = {"AAPL": Decimal("0.50"), "MSFT": Decimal("0.50")}

    adj_weights, cash_w, verdict, reason = DeriskEngine.evaluate_and_derisk(
        weights=raw_weights,
        policy=policy,
    )

    # Invariant: BINARY_REJECT produces 0 risky weights and 100% Cash
    assert verdict == RiskVerdict.REJECTED
    assert len(adj_weights) == 0
    assert cash_w == Decimal("1.0")
    assert reason is not None
    assert "BINARY_REJECT" in reason


# ============================================================================
# 3. DETERMINISTIC RISK ENGINE EVALUATION TESTS
# ============================================================================


def test_risk_engine_approved_flow(
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_candidate_allocation: CandidateRiskAllocation,
) -> None:
    engine = DeterministicRiskEngine()
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=sample_candidate_allocation,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
    )

    assert report.verdict == RiskVerdict.APPROVED
    assert report.adjusted_weights["AAPL"] == Decimal("0.20")
    assert report.adjusted_weights["MSFT"] == Decimal("0.20")
    assert report.cash_weight == Decimal("0.60")
    assert report.rejection_reason is None
    assert len(report.report_digest) == 64


def test_risk_engine_reduced_flow(
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    valid_sha256: str,
) -> None:
    engine = DeterministicRiskEngine()
    # Breaches concentration limit (AAPL=0.40 > 0.25)
    cand = CandidateRiskAllocation(
        candidate_id="CAND_OVER",
        strategy_id="MOM",
        weights={"AAPL": Decimal("0.40"), "MSFT": Decimal("0.20")},
        cash_weight=Decimal("0.40"),
        source_decision_digest=valid_sha256,
        as_of_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=cand,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
    )

    assert report.verdict == RiskVerdict.REDUCED
    assert report.adjusted_weights["AAPL"] <= Decimal("0.25")
    assert report.cash_weight >= Decimal("0.05")


def test_risk_engine_drawdown_limit_breach(
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_candidate_allocation: CandidateRiskAllocation,
) -> None:
    policy = RiskPolicyConfig(max_drawdown_limit_pct=Decimal("10.00"))
    engine = DeterministicRiskEngine(policy_config=policy)

    # Current equity = 10,000, Peak = 12,000 => Drawdown = (12000-10000)/12000 = 16.67% >= 10%
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=sample_candidate_allocation,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        peak_equity=Decimal("12000.00"),
    )

    assert report.verdict == RiskVerdict.KILL_SWITCH_BLOCKED
    assert len(report.adjusted_weights) == 0
    assert report.cash_weight == Decimal("1.0")
    assert "MAX_DRAWDOWN_BREACHED" in (report.rejection_reason or "")


def test_risk_engine_daily_loss_breach(
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_candidate_allocation: CandidateRiskAllocation,
) -> None:
    policy = RiskPolicyConfig(max_daily_loss_usd=Decimal("500.00"))
    engine = DeterministicRiskEngine(policy_config=policy)

    # Realized loss today = -$600 < -$500
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=sample_candidate_allocation,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        realized_pnl_today=Decimal("-600.00"),
    )

    assert report.verdict == RiskVerdict.KILL_SWITCH_BLOCKED
    assert "MAX_DAILY_LOSS_BREACHED" in (report.rejection_reason or "")


def test_risk_engine_stale_market_data(
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_candidate_allocation: CandidateRiskAllocation,
) -> None:
    engine = DeterministicRiskEngine()
    # Data age = 2000ms > max 1500ms
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=sample_candidate_allocation,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        data_age_ms=2000,
    )

    assert report.verdict == RiskVerdict.KILL_SWITCH_BLOCKED
    assert "STALE_MARKET_DATA" in (report.rejection_reason or "")


def test_risk_engine_broker_disconnect(
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_candidate_allocation: CandidateRiskAllocation,
) -> None:
    engine = DeterministicRiskEngine()
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=sample_candidate_allocation,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        is_broker_connected=False,
    )

    assert report.verdict == RiskVerdict.KILL_SWITCH_BLOCKED
    assert "BROKER_DISCONNECTED" in (report.rejection_reason or "")


def test_risk_engine_margin_buffer_breach(
    sample_portfolio_state: PortfolioState,
    sample_candidate_allocation: CandidateRiskAllocation,
) -> None:
    policy = RiskPolicyConfig(min_margin_buffer_usd=Decimal("5000.00"))
    engine = DeterministicRiskEngine(policy_config=policy)

    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    low_margin_acc = AccountState(
        account_id="ACC_001",
        currency="USD",
        balance=Decimal("10000.00"),
        equity=Decimal("10000.00"),
        free_margin=Decimal("1000.00"),  # < 5000 min margin buffer
        leverage=1.0,
        is_live=False,
        timestamp_utc=now,
    )

    report = engine.evaluate_candidate_allocation(
        candidate_allocation=sample_candidate_allocation,
        portfolio_state=sample_portfolio_state,
        account_state=low_margin_acc,
    )

    assert report.verdict == RiskVerdict.REJECTED
    assert "MARGIN_BUFFER_BREACHED" in (report.rejection_reason or "")


# ============================================================================
# 4. IRISKENGIINE INTERFACE CONTRACT COMPLIANCE TESTS
# ============================================================================


def test_risk_engine_implements_iriskengine_interface(
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
) -> None:
    engine = DeterministicRiskEngine()
    assert isinstance(engine, IRiskEngine)

    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    target = TargetAllocation(
        weights={"AAPL": 0.20, "MSFT": 0.20},
        cash_weight=0.60,
        rationale="Test target allocation",
        timestamp_utc=now,
    )

    assessment = engine.evaluate_allocation(
        target_allocation=target,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        timestamp_utc=now,
    )

    assert isinstance(assessment, RiskAssessment)
    assert assessment.approved is True
    assert assessment.adjusted_weights["AAPL"] == 0.20
    assert assessment.adjusted_weights["MSFT"] == 0.20
    assert assessment.rejection_reason is None


# ============================================================================
# 5. ADVERSARIAL & PATHOLOGICAL EDGE CASES
# ============================================================================


def test_risk_engine_clock_drift_breach(
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_candidate_allocation: CandidateRiskAllocation,
) -> None:
    engine = DeterministicRiskEngine()
    # Clock drift = 800ms > max 500ms
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=sample_candidate_allocation,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        clock_drift_ms=800,
    )

    assert report.verdict == RiskVerdict.KILL_SWITCH_BLOCKED
    assert "CLOCK_SKEW_DETECTED" in (report.rejection_reason or "")


def test_risk_engine_pathological_constraints() -> None:
    # Pathological: 100% Cash buffer required => zero risky budget
    policy = RiskPolicyConfig(
        derisk_policy=DeriskPolicy.EXACT_SCALE_DOWN,
        min_cash_buffer=Decimal("1.00"),
    )
    raw_weights = {"AAPL": Decimal("0.50")}
    adj_w, cash_w, verdict, reason = DeriskEngine.evaluate_and_derisk(
        weights=raw_weights,
        policy=policy,
    )
    # alpha = 0.0 => fail closed to REJECTED with 100% Cash
    assert verdict == RiskVerdict.REJECTED
    assert len(adj_w) == 0
    assert cash_w == Decimal("1.00")
    assert reason is not None


def test_risk_engine_zero_broker_execution_authority() -> None:
    """Architectural Invariant: Phase 9 has NO direct broker execution authority."""
    engine = DeterministicRiskEngine()

    # Engine must not expose direct execution or wire transmission methods
    forbidden_methods = [
        "submit_order",
        "execute_order",
        "place_order",
        "cancel_order",
        "transmit_order",
        "send_order",
        "get_broker_client",
    ]
    for method in forbidden_methods:
        assert not hasattr(engine, method), f"DeterministicRiskEngine must not have '{method}' authority."
