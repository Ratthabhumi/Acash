"""Tests for HYP_011 prospective shadow activation machinery (no price access).

Covers: corrected-authority gating, scientific boundary, missed-session
derivation + zero counting, activation from real commit timestamps, guards
(duplicate/out-of-order/early/future/recent-stress/quarantine), fresh 100k,
80/20 strategy constants, 504+2 minimums, and locks. Calendar only.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011 import shadow as SH


def test_corrected_authority_required() -> None:
    with pytest.raises(DataContractError):
        SH.shadow_readiness("SOMETHING_ELSE", True)
    with pytest.raises(DataContractError):
        SH.shadow_readiness(
            "HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW", False
        )
    ready = SH.shadow_readiness(
        "HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW", True
    )
    assert ready["state"] == "PROSPECTIVE_SHADOW_ARMED_WAITING_FOR_FIRST_COMPLETED_SESSION"
    assert ready["starting_aum"] == "100000.00"


def test_scientific_boundary_and_missed_sessions_calendar_derived() -> None:
    cal = NyseCa1Calendar()
    assert SH.SCIENTIFIC_PROSPECTIVE_BOUNDARY == date(2026, 9, 25)
    assert cal.is_trading_session(date(2026, 9, 25)) is True
    # Activation-exclusive upper of 2026-09-28 (Monday): Fri 25th missed.
    missed = SH.missed_unobserved_sessions(cal, date(2026, 9, 28))
    assert missed == [date(2026, 9, 25)]
    # Missed sessions never count toward evaluation.
    state = SH.ShadowState(activation_session=date(2026, 9, 28))
    assert state.observed_count == 0
    assert state.minimums_satisfied() is False


def test_activation_uses_real_commit_timestamp() -> None:
    cal = NyseCa1Calendar()
    # R1 commit Friday 2026-09-24T22:34:44Z (after close) -> next open Friday... verified:
    session = SH.derive_activation_session(
        cal, datetime(2026, 9, 24, 22, 34, 44, tzinfo=timezone.utc)
    )
    assert session == date(2026, 9, 25)
    assert session > date(2026, 9, 24)
    # Naive timestamp rejected.
    with pytest.raises(DataContractError):
        SH.derive_activation_session(cal, datetime(2026, 9, 24, 22, 34, 44))


def test_activation_same_day_edge_cases() -> None:
    cal = NyseCa1Calendar()
    # Commit BEFORE today's eligible open -> today qualifies.
    assert SH.derive_activation_session(
        cal, datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    ) == date(2026, 9, 25)
    # Commit EXACTLY at open -> strictly-after rule moves to next session.
    assert SH.derive_activation_session(
        cal, datetime(2026, 9, 25, 13, 30, 0, tzinfo=timezone.utc)
    ) == date(2026, 9, 28)
    # Commit after open -> next session.
    assert SH.derive_activation_session(
        cal, datetime(2026, 9, 25, 15, 0, 0, tzinfo=timezone.utc)
    ) == date(2026, 9, 28)
    # Weekend commit -> next session.
    assert SH.derive_activation_session(
        cal, datetime(2026, 9, 26, 17, 39, 1, tzinfo=timezone.utc)
    ) == date(2026, 9, 28)


def test_fresh_start_no_carryover_and_strategy_constants() -> None:
    assert SH.SHADOW_STARTING_AUM == Decimal("100000.00")
    assert SH.PROSPECTIVE_MIN_SESSIONS == 504
    assert SH.PROSPECTIVE_MIN_REBALANCES == 2


def _after_close(session: date) -> datetime:
    cal = NyseCa1Calendar()
    close_utc = cal.get_session(session).close_utc
    assert close_utc is not None
    return close_utc + timedelta(seconds=1)


def test_completion_guard_uses_close_utc() -> None:
    cal = NyseCa1Calendar()
    close_utc = cal.get_session(date(2026, 9, 25)).close_utc
    assert close_utc == datetime(2026, 9, 25, 20, 0, 0, tzinfo=timezone.utc)
    state = SH.ShadowState(activation_session=date(2026, 9, 25))
    # One second before close -> incomplete.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 25), cal, close_utc - timedelta(seconds=2))
    # One second after close -> processable.
    state.record_session(date(2026, 9, 25), cal, _after_close(date(2026, 9, 25)))
    assert state.observed_count == 1
    # Naive now rejected.
    with pytest.raises(DataContractError):
        state.record_session(
            date(2026, 9, 28), cal, datetime(2026, 9, 29, 0, 0, 0)
        )


def test_session_guards() -> None:
    cal = NyseCa1Calendar()
    # Use the scientific boundary itself as a synthetic activation so all
    # guard paths execute against completed sessions (guard mechanics only;
    # production activation never backfills missed sessions).
    state = SH.ShadowState(activation_session=date(2026, 9, 25))
    after = _after_close(date(2026, 9, 25))
    # Earlier-than-activation rejected.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 24), cal, after)
    # Recent-stress rejected.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 8, 14), cal, after)
    # Quarantine rejected.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 8, 15), cal, after)
    # Future/incomplete rejected.
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 28), cal, after)
    # Valid append + duplicate + out-of-order.
    state.record_session(date(2026, 9, 25), cal, after)
    assert state.observed_count == 1
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 25), cal, after)
    with pytest.raises(DataContractError):
        state.record_session(date(2026, 9, 24), cal, after)


def test_early_close_uses_actual_close_utc() -> None:
    cal = NyseCa1Calendar()
    # 2024-11-29: official early close (18:00Z, not 20:00Z).
    close_utc = cal.get_session(date(2024, 11, 29)).close_utc
    assert close_utc == datetime(2024, 11, 29, 18, 0, 0, tzinfo=timezone.utc)
    state = SH.ShadowState(activation_session=date(2024, 11, 29))
    with pytest.raises(DataContractError):
        state.record_session(
            date(2024, 11, 29), cal, close_utc - timedelta(seconds=1)
        )
    state.record_session(
        date(2024, 11, 29), cal, close_utc + timedelta(seconds=1)
    )
    assert state.observed_count == 1


def test_minimums_conjunctive() -> None:
    state = SH.ShadowState(activation_session=date(2026, 9, 28))
    state.observed_sessions = [f"2027-01-{i:02d}" for i in range(1, 505)]
    state.completed_annual_rebalances = 1
    assert state.minimums_satisfied() is False
    state.completed_annual_rebalances = 2
    assert state.minimums_satisfied() is True
