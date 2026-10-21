"""Unit and adversarial tests for Lane B Candidate Evaluator.

Verifies strict compliance with:
- docs/research/LANE_B_SPEC_OFFLINE_QUALIFICATION.md
- AGENTS.md Section 1 (Strict Fail-Closed Contract, Literature & Unit Discipline)
"""

from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from typing import Optional
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_b_candidate_evaluator import (
    LaneBCandidateEvaluator,
    LaneBCandidateEvent,
    LaneBCandidateEvaluationResult,
)


def _sample_valid_event(
    symbol: str = "VOO",
    amount: str = "1.822600",
    ex_date: date = date(2026, 9, 28),
    record_date: Optional[date] = None,
    payable_date: Optional[date] = None,
    authority_class: str = "ISSUER_OFFICIAL_TABLE",
) -> LaneBCandidateEvent:
    rec_d = record_date if record_date is not None else ex_date
    pay_d = payable_date if payable_date is not None else rec_d
    return LaneBCandidateEvent(
        symbol=symbol,
        fund_legal_identity="Vanguard Index Funds",
        event_type="INCOME_DISTRIBUTION",
        amount=Decimal(amount),
        currency="USD",
        ex_date=ex_date,
        record_date=rec_d,
        payable_date=pay_d,
        source_url="https://www.vanguardoffshore.com/en/product/etf/equity/0968/vanguard-sp-500-etf",
        source_document="Vanguard Official S&P 500 ETF Distributions",
        retrieval_status="UNVERIFIED_CAPTURE_TIME",
        authority_class=authority_class,
    )


def test_happy_path_candidate_panel_json_evaluates() -> None:
    """Verify that the committed 2025-2026 JSON candidate panel parses and verifies cleanly."""
    json_path = Path(__file__).resolve().parents[3] / "docs" / "research" / "lane_b_candidate_events_2025_2026.json"
    assert json_path.exists(), f"Candidate JSON file not found at {json_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    events = [LaneBCandidateEvent.from_dict(ev) for ev in data["cash_distribution_events"]]
    assert len(events) >= 20

    evaluator = LaneBCandidateEvaluator()
    result = evaluator.evaluate_panel(events)

    assert result.status == "CANDIDATE_PANEL_VERIFIED"
    assert result.total_events == len(events)
    assert set(result.symbols_evaluated) == {"VOO", "BND", "BIL"}
    assert len(result.composite_digest) == 64  # Valid SHA-256 hex string


def test_gld_cash_dividend_strictly_rejected() -> None:
    """GLD is a physical grantor trust; cash dividend events must be rejected fail-closed."""
    evaluator = LaneBCandidateEvaluator()
    gld_event = _sample_valid_event(symbol="GLD", amount="0.00")

    with pytest.raises(DataContractError, match="NO_CASH_DISTRIBUTION_ENTITLEMENT"):
        evaluator.evaluate_panel([gld_event])


def test_unknown_basis_authority_rejected() -> None:
    """Records without authorized issuer authority must be rejected fail-closed."""
    evaluator = LaneBCandidateEvaluator()
    event = _sample_valid_event(authority_class="UNKNOWN_BASIS")

    with pytest.raises(DataContractError, match="invalid authority class 'UNKNOWN_BASIS'"):
        evaluator.evaluate_panel([event])


def test_negative_or_zero_amount_rejected() -> None:
    """Zero or negative dividend amounts are invalid for declared distribution events."""
    evaluator = LaneBCandidateEvaluator()
    
    with pytest.raises(DataContractError, match="must be positive"):
        event_neg = _sample_valid_event(amount="-1.50")
        evaluator.evaluate_panel([event_neg])

    with pytest.raises(DataContractError, match="must be positive"):
        event_zero = _sample_valid_event(amount="0.00")
        evaluator.evaluate_panel([event_zero])


def test_non_usd_currency_rejected() -> None:
    """Only USD distributions are supported in Lane A/B universe."""
    evaluator = LaneBCandidateEvaluator()
    event_eur = LaneBCandidateEvent(
        symbol="VOO",
        fund_legal_identity="Vanguard Index Funds",
        event_type="INCOME_DISTRIBUTION",
        amount=Decimal("1.80"),
        currency="EUR",
        ex_date=date(2026, 9, 28),
        record_date=date(2026, 9, 28),
        payable_date=date(2026, 9, 30),
        source_url="https://vanguard.com",
        source_document="Vanguard Distributions",
        retrieval_status="UNVERIFIED_CAPTURE_TIME",
    )
    with pytest.raises(DataContractError, match="Unsupported distribution currency 'EUR'"):
        evaluator.evaluate_panel([event_eur])


def test_date_inversion_rejected() -> None:
    """Date ordering invariant ex_date <= record_date <= payable_date must hold."""
    evaluator = LaneBCandidateEvaluator()

    # Record date before ex date
    event_rec_before_ex = _sample_valid_event(
        ex_date=date(2026, 9, 28),
        record_date=date(2026, 9, 27),
        payable_date=date(2026, 9, 30),
    )
    with pytest.raises(DataContractError, match="record_date 2026-09-27 precedes ex_date"):
        evaluator.evaluate_panel([event_rec_before_ex])

    # Payable date before record date
    event_pay_before_rec = _sample_valid_event(
        ex_date=date(2026, 9, 28),
        record_date=date(2026, 9, 28),
        payable_date=date(2026, 9, 25),
    )
    with pytest.raises(DataContractError, match="payable_date 2026-09-25 precedes record_date"):
        evaluator.evaluate_panel([event_pay_before_rec])


def test_contradictory_duplicate_rejected() -> None:
    """Duplicate ex_dates with conflicting dollar amounts must be quarantined and rejected."""
    evaluator = LaneBCandidateEvaluator()
    ev1 = _sample_valid_event(amount="1.822600")
    ev2 = _sample_valid_event(amount="1.950000")  # Same symbol & ex_date, different amount

    with pytest.raises(DataContractError, match="Contradictory duplicate event"):
        evaluator.evaluate_panel([ev1, ev2])


def test_deterministic_digest_permutation_invariance() -> None:
    """Panel ordering must not alter the resulting framed composite digest."""
    evaluator = LaneBCandidateEvaluator()
    ev1 = _sample_valid_event(symbol="VOO", ex_date=date(2026, 9, 28))
    ev2 = _sample_valid_event(symbol="BND", ex_date=date(2026, 9, 1), payable_date=date(2026, 9, 3))

    res_1 = evaluator.evaluate_panel([ev1, ev2])
    res_2 = evaluator.evaluate_panel([ev2, ev1])

    assert res_1.composite_digest == res_2.composite_digest


def test_empty_panel_raises() -> None:
    """Empty candidate panel is rejected fail-closed."""
    evaluator = LaneBCandidateEvaluator()
    with pytest.raises(DataContractError, match="must not be empty"):
        evaluator.evaluate_panel([])
