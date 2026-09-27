"""Tests for prospective CA adapters (mock fixtures only, zero network)."""

from datetime import date, datetime, timezone

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.hyp_011.shadow_ca import (
    MockSponsorAuthorityAdapter,
    SPONSOR_BY_SYMBOL,
)


def _now() -> datetime:
    return datetime(2026, 9, 29, 0, 0, 0, tzinfo=timezone.utc)


def _adapter() -> MockSponsorAuthorityAdapter:
    return MockSponsorAuthorityAdapter(
        sponsor_identity="BLACKROCK_ISHARES_OFFICIAL",
        domain_fragment="ishares.com",
        events={
            "2026-09-29": {
                "ex_date": "2026-09-29",
                "amount": "0.25",
                "payable_date": "2026-10-05",
                "record_date": "2026-09-30",
                "source_sha256": "abc",
            }
        },
        no_event_sessions=["2026-09-28"],
        ambiguous_sessions=["2026-09-30"],
    )


def test_official_sponsor_mapping() -> None:
    assert SPONSOR_BY_SYMBOL == {
        "ACWI": "BLACKROCK_ISHARES_OFFICIAL",
        "AGG": "BLACKROCK_ISHARES_OFFICIAL",
        "SPY": "STATE_STREET_SPDR_OFFICIAL",
    }


def test_event_determination() -> None:
    det = _adapter().query("ACWI", date(2026, 9, 29), _now())
    assert det.has_event is True
    assert det.ex_date == date(2026, 9, 29)
    assert det.payable_date == date(2026, 10, 5)
    assert det.authority_source == "BLACKROCK_ISHARES_OFFICIAL"


def test_explicit_no_event_determination() -> None:
    det = _adapter().query("ACWI", date(2026, 9, 28), _now())
    assert det.has_event is False
    assert det.authority_source == "BLACKROCK_ISHARES_OFFICIAL"


def test_ambiguous_blocks_and_unknown_blocks() -> None:
    adapter = _adapter()
    with pytest.raises(DataContractError):
        adapter.query("ACWI", date(2026, 9, 30), _now())
    with pytest.raises(DataContractError):
        adapter.query("ACWI", date(2026, 10, 1), _now())


def test_wrong_sponsor_and_unofficial_rejected() -> None:
    adapter = _adapter()
    with pytest.raises(DataContractError):
        adapter.query("SPY", date(2026, 9, 29), _now())
    with pytest.raises(DataContractError):
        adapter.query("QQQ", date(2026, 9, 29), _now())
    with pytest.raises(DataContractError):
        adapter.query("ACWI", date(2026, 9, 29), datetime(2026, 9, 29, 0, 0, 0))
