"""Unit tests for the offline F10 corporate-action determination intake.

Proves the operator-prepared pipeline (shadow_ca_intake) enforces the frozen
sponsor mapping, exact-amount discipline, scope-evidence-backed no-events, and
runner-path round-trip acceptance — without any network or sponsor scraping.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow_ca import CADetermination, SPONSOR_BY_SYMBOL
from acash.research.hyp_011.shadow_ca_intake import (
    ScopeEvidence,
    build_event_determination,
    build_no_event_determination,
)

PROC = datetime(2026, 10, 2, 0, 0, 0, tzinfo=timezone.utc)
RETRIEVED = "2026-10-01T12:00:00+00:00"
EVIDENCE = b"official-sponsor-schedule-bytes-fixture"
EVIDENCE_REF = "evidence/ishares-2026-distribution-schedule.pdf"
FAKE_SHA = "ab" * 32


def _scope() -> ScopeEvidence:
    return ScopeEvidence(
        schedule_id="ISHARES_2026_2028_MONTHLY_DISTRIBUTION_SCHEDULE",
        schedule_sha256=FAKE_SHA,
        scope_note="Monthly-distribution group coverage incl. 2026-10-01 session.",
        retrieved_at_utc=RETRIEVED,
    )


def test_sponsor_mapping_frozen() -> None:
    assert SPONSOR_BY_SYMBOL == {
        "ACWI": "BLACKROCK_ISHARES_OFFICIAL",
        "AGG": "BLACKROCK_ISHARES_OFFICIAL",
        "SPY": "STATE_STREET_SPDR_OFFICIAL",
    }


def test_event_determination_accepted_with_exact_amount() -> None:
    doc = build_event_determination(
        symbol="AGG",
        session=date(2026, 10, 1),
        ex_date=date(2026, 10, 1),
        amount_per_share="0.123456",
        payable_date=date(2026, 10, 6),
        authority_source="BLACKROCK_ISHARES_OFFICIAL",
        retrieved_at_utc=RETRIEVED,
        evidence_bytes=EVIDENCE,
        evidence_ref=EVIDENCE_REF,
        processing_utc=PROC,
        record_date=date(2026, 10, 1),
    )
    assert doc["has_event"] is True
    assert doc["amount_per_share"] == "0.123456"
    assert doc["payable_date"] == "2026-10-06"
    # Runner-path proof is intrinsic (build round-trips from_dict).
    parsed = CADetermination.from_dict(doc, "AGG", date(2026, 10, 1), PROC)
    assert parsed.amount_per_share == Decimal("0.123456")


def test_event_without_amount_refused_agg_obs2_blocked() -> None:
    """AGG 2026-10-01 cannot be completed without the exact official amount."""
    with pytest.raises(DataContractError, match="CA_EVENT_AMOUNT_REQUIRED"):
        build_event_determination(
            symbol="AGG",
            session=date(2026, 10, 1),
            ex_date=date(2026, 10, 1),
            amount_per_share=None,
            payable_date=date(2026, 10, 6),
            authority_source="BLACKROCK_ISHARES_OFFICIAL",
            retrieved_at_utc=RETRIEVED,
            evidence_bytes=EVIDENCE,
            evidence_ref=EVIDENCE_REF,
            processing_utc=PROC,
        )


def test_event_amount_must_be_exact_decimal() -> None:
    bad_amounts: Any = [0.123, True, "0", "-1", "nan", "Infinity", "abc", "", "  "]
    for bad in bad_amounts:
        with pytest.raises(DataContractError):
            build_event_determination(
                symbol="AGG",
                session=date(2026, 10, 1),
                ex_date=date(2026, 10, 1),
                amount_per_share=bad,
                payable_date=date(2026, 10, 6),
                authority_source="BLACKROCK_ISHARES_OFFICIAL",
                retrieved_at_utc=RETRIEVED,
                evidence_bytes=EVIDENCE,
                evidence_ref=EVIDENCE_REF,
                processing_utc=PROC,
            )


def test_no_event_with_scope_evidence_accepted() -> None:
    for symbol, sponsor in (
        ("ACWI", "BLACKROCK_ISHARES_OFFICIAL"),
        ("SPY", "STATE_STREET_SPDR_OFFICIAL"),
    ):
        doc = build_no_event_determination(
            symbol=symbol,
            session=date(2026, 10, 1),
            authority_source=sponsor,
            retrieved_at_utc=RETRIEVED,
            scope=_scope(),
            evidence_bytes=EVIDENCE,
            evidence_ref=EVIDENCE_REF,
            processing_utc=PROC,
        )
        assert doc["has_event"] is False
        assert doc["scope_evidence"]["schedule_sha256"] == FAKE_SHA
        parsed = CADetermination.from_dict(doc, symbol, date(2026, 10, 1), PROC)
        assert parsed.has_event is False


def test_no_event_bare_absence_rejected() -> None:
    """Absence of a parsed row alone is never sufficient (scope required)."""
    bad_scopes = [
        ScopeEvidence(schedule_id="", schedule_sha256=FAKE_SHA,
                      scope_note="x", retrieved_at_utc=RETRIEVED),
        ScopeEvidence(schedule_id="S", schedule_sha256="not-a-sha",
                      scope_note="x", retrieved_at_utc=RETRIEVED),
        ScopeEvidence(schedule_id="S", schedule_sha256=FAKE_SHA,
                      scope_note="", retrieved_at_utc=RETRIEVED),
        ScopeEvidence(schedule_id="S", schedule_sha256=FAKE_SHA,
                      scope_note="x", retrieved_at_utc="2026-10-05T00:00:00+00:00"),
    ]
    for bad_scope in bad_scopes:
        with pytest.raises(DataContractError):
            build_no_event_determination(
                symbol="ACWI",
                session=date(2026, 10, 1),
                authority_source="BLACKROCK_ISHARES_OFFICIAL",
                retrieved_at_utc=RETRIEVED,
                scope=bad_scope,
                evidence_bytes=EVIDENCE,
                evidence_ref=EVIDENCE_REF,
                processing_utc=PROC,
            )


def test_wrong_sponsor_rejected() -> None:
    with pytest.raises(DataContractError, match="CA_SPONSOR_MISMATCH"):
        build_event_determination(
            symbol="SPY",
            session=date(2026, 10, 1),
            ex_date=date(2026, 10, 1),
            amount_per_share="1.00",
            payable_date=date(2026, 10, 6),
            authority_source="BLACKROCK_ISHARES_OFFICIAL",
            retrieved_at_utc=RETRIEVED,
            evidence_bytes=EVIDENCE,
            evidence_ref=EVIDENCE_REF,
            processing_utc=PROC,
        )


def test_future_retrieval_rejected() -> None:
    with pytest.raises(DataContractError, match="CA_FUTURE_RETRIEVAL"):
        build_no_event_determination(
            symbol="ACWI",
            session=date(2026, 10, 1),
            authority_source="BLACKROCK_ISHARES_OFFICIAL",
            retrieved_at_utc="2026-10-03T00:00:00+00:00",
            scope=_scope(),
            evidence_bytes=EVIDENCE,
            evidence_ref=EVIDENCE_REF,
            processing_utc=PROC,
        )


def test_empty_evidence_rejected() -> None:
    with pytest.raises(DataContractError, match="CA_EVIDENCE_BYTES_EMPTY"):
        build_event_determination(
            symbol="AGG",
            session=date(2026, 10, 1),
            ex_date=date(2026, 10, 1),
            amount_per_share="0.5",
            payable_date=date(2026, 10, 6),
            authority_source="BLACKROCK_ISHARES_OFFICIAL",
            retrieved_at_utc=RETRIEVED,
            evidence_bytes=b"",
            evidence_ref=EVIDENCE_REF,
            processing_utc=PROC,
        )


def test_non_session_ex_date_rejected() -> None:
    cal = NyseCa1Calendar()
    assert cal.is_trading_session(date(2016, 11, 24)) is False
    # Saturday ex-date cannot carry a dividend.
    with pytest.raises(DataContractError, match="CA_EX_DATE_NON_SESSION"):
        build_event_determination(
            symbol="AGG",
            session=date(2016, 11, 7),
            ex_date=date(2016, 11, 5),
            amount_per_share="0.5",
            payable_date=date(2016, 11, 9),
            authority_source="BLACKROCK_ISHARES_OFFICIAL",
            retrieved_at_utc="2016-11-07T12:00:00+00:00",
            evidence_bytes=EVIDENCE,
            evidence_ref=EVIDENCE_REF,
            processing_utc=datetime(2016, 11, 8, tzinfo=timezone.utc),
        )


def test_payable_before_ex_rejected() -> None:
    with pytest.raises(DataContractError, match="CA_PAYABLE_BEFORE_EX"):
        build_event_determination(
            symbol="AGG",
            session=date(2026, 10, 1),
            ex_date=date(2026, 10, 1),
            amount_per_share="0.5",
            payable_date=date(2026, 9, 30),
            authority_source="BLACKROCK_ISHARES_OFFICIAL",
            retrieved_at_utc=RETRIEVED,
            evidence_bytes=EVIDENCE,
            evidence_ref=EVIDENCE_REF,
            processing_utc=PROC,
        )


def test_from_dict_rejects_nonfinite_amount() -> None:
    doc: Dict[str, Any] = {
        "symbol": "AGG",
        "session": "2026-10-01",
        "has_event": True,
        "ex_date": "2026-10-01",
        "amount_per_share": "Infinity",
        "payable_date": "2026-10-06",
        "authority_source": "BLACKROCK_ISHARES_OFFICIAL",
        "retrieved_at_utc": RETRIEVED,
        "source_sha256": FAKE_SHA,
    }
    with pytest.raises(DataContractError, match="CA_EVENT_AMOUNT_NONFINITE"):
        CADetermination.from_dict(doc, "AGG", date(2026, 10, 1), PROC)
