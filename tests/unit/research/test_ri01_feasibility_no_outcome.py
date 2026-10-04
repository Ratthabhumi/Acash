"""RI-01 zero-outcome feasibility tests (synthetic fixtures ONLY).

Covers calendar/session mapping, timestamp parsing, opening-bar semantics,
missing-session handling, provider-response schema, symbol identity, and
deterministic evidence hashing. Computes NOTHING predictive: no returns, no
PnL, no Sharpe, no hit-rate, no thresholds. Zero network.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.ri01.feasibility import (
    canonical_evidence_digest,
    evidence_digest,
    opening_bar_index,
    parse_utc_timestamp,
    require_complete_rth_grid,
    require_tz_aware,
    session_utc_bounds,
    validate_provider_bar,
    validate_symbol_identity,
)


def _bar(ts: str, volume: str = "1000") -> Dict[str, Any]:
    return {
        "timestamp": ts,
        "open": "100",
        "high": "101",
        "low": "99",
        "close": "100.5",
        "volume": volume,
    }


def test_parse_utc_timestamp_normalizes_offsets() -> None:
    assert parse_utc_timestamp(
        "2026-10-05T09:30:00-04:00", "ctx"
    ) == datetime(2026, 10, 5, 13, 30, tzinfo=timezone.utc)


def test_parse_rejects_naive_and_malformed() -> None:
    with pytest.raises(DataContractError):
        parse_utc_timestamp("2026-10-05T09:30:00", "ctx")
    with pytest.raises(DataContractError):
        parse_utc_timestamp("not-a-timestamp", "ctx")
    with pytest.raises(DataContractError):
        require_tz_aware(datetime(2026, 10, 5, 9, 30), "ctx")


def test_validate_provider_bar_accepts_synthetic() -> None:
    normalized = validate_provider_bar(_bar("2026-10-05T13:30:00+00:00"), "ctx")
    assert normalized["timestamp"] == "2026-10-05T13:30:00+00:00"
    assert normalized["volume"] == "1000"


def test_zero_volume_preserved_not_coerced() -> None:
    normalized = validate_provider_bar(
        _bar("2026-10-05T13:30:00+00:00", volume="0"), "ctx"
    )
    assert normalized["volume"] == "0"


@pytest.mark.parametrize(
    "mutation",
    [
        {"timestamp": "2026-10-05T09:30:00"},  # naive
        {"open": "0"},  # non-positive
        {"open": "-1"},
        {"high": "50"},  # high < max(open, close)
        {"low": "500"},  # low > min(open, close)
        {"volume": "-3"},  # negative
        {"close": "NaN"},  # non-finite
    ],
)
def test_validate_provider_bar_rejects_malformed(mutation: Dict[str, Any]) -> None:
    bar = _bar("2026-10-05T13:30:00+00:00")
    bar.update(mutation)
    with pytest.raises(DataContractError):
        validate_provider_bar(bar, "ctx")


def test_validate_provider_bar_rejects_missing_field() -> None:
    bar = _bar("2026-10-05T13:30:00+00:00")
    del bar["volume"]
    with pytest.raises(DataContractError):
        validate_provider_bar(bar, "ctx")


def test_symbol_identity_accepts_complete_record() -> None:
    identity = validate_symbol_identity(
        {
            "ticker": "SPY",
            "product_id": "284681",
            "cusip": "78462F103",
            "sponsor": "STATE_STREET_SPDR_OFFICIAL",
        },
        "ctx",
    )
    assert identity["ticker"] == "SPY"


@pytest.mark.parametrize(
    "mutation",
    [
        {"ticker": "  "},
        {"cusip": ""},
        {"delisted": True},
    ],
)
def test_symbol_identity_rejects_lifecycle_gaps(mutation: Dict[str, Any]) -> None:
    record = {
        "ticker": "SPY",
        "product_id": "284681",
        "cusip": "78462F103",
        "sponsor": "STATE_STREET_SPDR_OFFICIAL",
    }
    record.update(mutation)
    with pytest.raises(DataContractError):
        validate_symbol_identity(record, "ctx")


def test_opening_bar_found_at_exact_open() -> None:
    bars: List[Dict[str, Any]] = [
        _bar("2026-10-05T13:30:00+00:00"),
        _bar("2026-10-05T13:31:00+00:00"),
    ]
    assert (
        opening_bar_index(
            bars, datetime(2026, 10, 5, 13, 30, tzinfo=timezone.utc)
        )
        == 0
    )


def test_missing_opening_bar_is_unavailable_not_imputed() -> None:
    bars: List[Dict[str, Any]] = [_bar("2026-10-05T13:31:00+00:00")]
    with pytest.raises(DataContractError):
        opening_bar_index(
            bars, datetime(2026, 10, 5, 13, 30, tzinfo=timezone.utc)
        )
    with pytest.raises(DataContractError):
        opening_bar_index([], datetime(2026, 10, 5, 13, 30, tzinfo=timezone.utc))


def _true_rth_grid(session: date, calendar: NyseCa1Calendar) -> List[Dict[str, Any]]:
    """Build the exact canonical minute grid for a session (test oracle)."""
    bounds = session_utc_bounds(session, calendar)
    open_utc = datetime.fromisoformat(bounds["open_utc"])
    close_utc = datetime.fromisoformat(bounds["close_utc"])
    count = int((close_utc - open_utc).total_seconds() // 60)
    return [
        _bar((open_utc + timedelta(minutes=k)).isoformat()) for k in range(count)
    ]


def test_require_complete_rth_grid_regular_session() -> None:
    calendar = NyseCa1Calendar()
    bars = _true_rth_grid(date(2026, 10, 5), calendar)
    assert len(bars) == 390
    require_complete_rth_grid(bars, date(2026, 10, 5), calendar, "ctx")


def test_require_complete_rth_grid_half_day() -> None:
    calendar = NyseCa1Calendar()
    session = date(2026, 11, 27)
    bars = _true_rth_grid(session, calendar)
    # Late November is EST: 14:30 UTC open, 18:00 UTC early close = 210 minutes.
    assert len(bars) == 210
    require_complete_rth_grid(bars, session, calendar, "ctx")


def test_grid_rejects_shortfall() -> None:
    calendar = NyseCa1Calendar()
    bars = _true_rth_grid(date(2026, 10, 5), calendar)
    with pytest.raises(DataContractError):
        require_complete_rth_grid(bars[:389], date(2026, 10, 5), calendar, "ctx")


def test_grid_rejects_missing_middle_masked_by_duplicate() -> None:
    calendar = NyseCa1Calendar()
    bars = _true_rth_grid(date(2026, 10, 5), calendar)
    tampered = bars[:100] + [bars[99]] + bars[101:]
    assert len(tampered) == 390  # same count: count-only checks would pass
    with pytest.raises(DataContractError):
        require_complete_rth_grid(tampered, date(2026, 10, 5), calendar, "ctx")


def test_grid_rejects_duplicate_minute() -> None:
    calendar = NyseCa1Calendar()
    bars = _true_rth_grid(date(2026, 10, 5), calendar)
    tampered = bars[:200] + [bars[50]] + bars[200:-1]
    assert len(tampered) == 390
    with pytest.raises(DataContractError):
        require_complete_rth_grid(tampered, date(2026, 10, 5), calendar, "ctx")


def test_grid_rejects_out_of_order_bar() -> None:
    calendar = NyseCa1Calendar()
    bars = _true_rth_grid(date(2026, 10, 5), calendar)
    tampered = list(bars)
    tampered[10], tampered[11] = tampered[11], tampered[10]
    with pytest.raises(DataContractError):
        require_complete_rth_grid(tampered, date(2026, 10, 5), calendar, "ctx")


def test_grid_rejects_second_spacing_masquerade() -> None:
    calendar = NyseCa1Calendar()
    session = date(2026, 10, 5)
    bounds = session_utc_bounds(session, calendar)
    open_utc = datetime.fromisoformat(bounds["open_utc"])
    # 390 records at 1-SECOND spacing cover ~6.5 minutes, not a session.
    bars = [
        _bar((open_utc + timedelta(seconds=k)).isoformat()) for k in range(390)
    ]
    with pytest.raises(DataContractError):
        require_complete_rth_grid(bars, session, calendar, "ctx")


def test_grid_rejects_wrong_opening_timestamp() -> None:
    calendar = NyseCa1Calendar()
    bars = _true_rth_grid(date(2026, 10, 5), calendar)
    shifted = [_bar("2026-10-05T13:31:00+00:00")] + bars[1:]
    with pytest.raises(DataContractError):
        require_complete_rth_grid(shifted, date(2026, 10, 5), calendar, "ctx")


def test_grid_rejects_post_close_contamination() -> None:
    calendar = NyseCa1Calendar()
    bars = _true_rth_grid(date(2026, 10, 5), calendar)
    # Final left-edge (19:59) replaced by a post-close 20:00 record.
    tampered = bars[:-1] + [_bar("2026-10-05T20:00:00+00:00")]
    with pytest.raises(DataContractError):
        require_complete_rth_grid(tampered, date(2026, 10, 5), calendar, "ctx")


def test_grid_rejects_non_session() -> None:
    calendar = NyseCa1Calendar()
    with pytest.raises(DataContractError):
        require_complete_rth_grid([], date(2026, 7, 4), calendar, "ctx")


def test_session_bounds_summer_vs_winter_dst() -> None:
    calendar = NyseCa1Calendar()
    summer = session_utc_bounds(date(2026, 10, 5), calendar)
    assert summer["open_utc"] == "2026-10-05T13:30:00+00:00"
    assert summer["close_utc"] == "2026-10-05T20:00:00+00:00"
    winter = session_utc_bounds(date(2026, 1, 5), calendar)
    assert winter["open_utc"] == "2026-01-05T14:30:00+00:00"
    assert winter["close_utc"] == "2026-01-05T21:00:00+00:00"


def test_session_bounds_early_close_and_holiday() -> None:
    calendar = NyseCa1Calendar()
    early = session_utc_bounds(date(2026, 11, 27), calendar)
    assert early["close_utc"] == "2026-11-27T18:00:00+00:00"
    with pytest.raises(DataContractError):
        session_utc_bounds(date(2026, 7, 4), calendar)


def test_evidence_digest_deterministic_and_tamper_sensitive() -> None:
    raw = b'{"session":"2026-10-05","bars":390}'
    first = evidence_digest(raw)
    assert len(first) == 64
    assert evidence_digest(raw) == first
    assert evidence_digest(b'{"session":"2026-10-05","bars":389}') != first
    with pytest.raises(DataContractError):
        evidence_digest(b"")


def test_canonical_digest_ignores_key_order() -> None:
    assert canonical_evidence_digest({"b": 1, "a": 2}) == canonical_evidence_digest(
        {"a": 2, "b": 1}
    )
