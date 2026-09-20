"""Unit tests for MEC-0015 historical SIP quotes execution contract."""

from datetime import date, time
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0015_quote_contract import (
    MEC_0015_AUTHORIZED_QUOTE_PROBE_DATES,
    MEC_0015_PROBE_DECISION_TIMES_ET,
    PRIMARY_EXECUTION_MODEL_NAME,
    SPREAD_MODEL_NAME,
    parse_sip_quote,
    evaluate_boundary_quotes,
)


def test_quote_authorized_dates_only() -> None:
    """Verify strictly 3 authorized dates (2019-06-03, 2022-06-01, 2024-03-01) and fail-closed on others."""
    assert len(MEC_0015_AUTHORIZED_QUOTE_PROBE_DATES) == 3
    assert MEC_0015_AUTHORIZED_QUOTE_PROBE_DATES == (
        date(2019, 6, 3),
        date(2022, 6, 1),
        date(2024, 3, 1),
    )

    unauthorized_date = date(2020, 6, 1)
    with pytest.raises(DataContractError, match="UNAUTHORIZED_QUOTE_DATE"):
        evaluate_boundary_quotes(
            unauthorized_date,
            time(10, 0, 0),
            raw_quotes_before=[],
            raw_quotes_after=[],
        )


def test_quote_bid_ask_invariants() -> None:
    """Bid and ask prices must be positive; parse fails closed on nonpositive or missing."""
    valid_raw = {
        "t": "2024-03-01T15:00:00.005Z",
        "bp": 508.95,
        "ap": 508.96,
        "bs": 5,
        "as": 10,
        "bx": "P",
        "ax": "Z",
        "c": ["R"],
        "z": "B",
    }
    q = parse_sip_quote(valid_raw)
    assert q.bid_price == Decimal("508.95")
    assert q.ask_price == Decimal("508.96")
    assert q.spread == Decimal("0.01")
    assert q.is_locked is False
    assert q.is_crossed is False

    # Nonpositive bid
    bad_bid = dict(valid_raw, bp=0.0)
    with pytest.raises(DataContractError, match="NONPOSITIVE_NBBO_QUOTE"):
        parse_sip_quote(bad_bid)

    # Missing field
    missing_ask = dict(valid_raw)
    del missing_ask["ap"]
    with pytest.raises(DataContractError, match="MALFORMED_QUOTE_STRUCTURE"):
        parse_sip_quote(missing_ask)


def test_first_valid_quote_at_or_after_boundary() -> None:
    """PRIMARY_EXECUTION_MODEL selects first valid quote >= T, BUY fills at ask, SELL fills at bid."""
    d = date(2024, 3, 1)
    t = time(10, 0, 0)  # 15:00:00 UTC

    quotes_before = [
        {
            "t": "2024-03-01T14:59:59.950Z",
            "bp": 508.90,
            "ap": 508.92,
            "bs": 2,
            "as": 2,
            "bx": "P",
            "ax": "Z",
        }
    ]
    quotes_after = [
        {
            "t": "2024-03-01T15:00:00.005Z",
            "bp": 508.91,
            "ap": 508.93,
            "bs": 4,
            "as": 6,
            "bx": "P",
            "ax": "Z",
        },
        {
            "t": "2024-03-01T15:00:00.010Z",
            "bp": 508.92,
            "ap": 508.94,
            "bs": 1,
            "as": 1,
            "bx": "P",
            "ax": "Z",
        },
    ]

    pair = evaluate_boundary_quotes(d, t, quotes_before, quotes_after)
    assert pair.is_valid is True
    assert pair.quote_delay_ms == 5.0
    assert pair.simulated_buy_fill == Decimal("508.93")  # Ask
    assert pair.simulated_sell_fill == Decimal("508.91")  # Bid
    assert pair.latest_quote_before is not None
    assert pair.latest_quote_before.bid_price == Decimal("508.90")


def test_spread_model_embedded_in_nbbo_and_no_double_deduction() -> None:
    """Under NBBO fill, spread is embedded: BUY at ask, SELL at bid.

    Zero additional half-spread deduction is permitted.
    """
    assert SPREAD_MODEL_NAME == "EMBEDDED_IN_NBBO_FILL"
    assert PRIMARY_EXECUTION_MODEL_NAME == "FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY"


def test_fail_closed_on_crossed_quote() -> None:
    """If the first quote >= T is crossed (ask < bid), evaluation raises DataContractError."""
    d = date(2024, 3, 1)
    t = time(10, 0, 0)
    crossed_quotes_after = [
        {
            "t": "2024-03-01T15:00:00.002Z",
            "bp": 509.00,
            "ap": 508.95,  # ask < bid
            "bs": 1,
            "as": 1,
        }
    ]
    with pytest.raises(DataContractError, match="CROSSED_NBBO_AT_BOUNDARY"):
        evaluate_boundary_quotes(d, t, [], crossed_quotes_after)
