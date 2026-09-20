"""Unit tests for MEC-0015 Alpaca Corporate Actions (Cash Dividend) Qualification."""

from decimal import Decimal
import json
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0015_dividend_contract import (
    MEC_0015_DIVIDEND_START_DATE,
    MEC_0015_DIVIDEND_MAX_ALLOWED_DATE,
    MEC_0015_DIVIDEND_FORBIDDEN_OOS_DATE,
    DIVIDEND_PROVIDER_MAPPING_QUALIFIED,
    DIVIDEND_POINT_IN_TIME_VINTAGE_NOT_GUARANTEED,
    Mec0015CashDividendRecord,
    validate_and_parse_dividend_records,
)


def _build_valid_payload() -> bytes:
    data = {
        "corporate_actions": {
            "cash_dividends": [
                {
                    "symbol": "SPY",
                    "ex_date": "2016-06-17",
                    "rate": 1.078442,
                    "process_date": "2016-06-17",
                    "id": "c3b774ec-c4d6-4ef7-b262-c1ed32867b37",
                    "special": False,
                },
                {
                    "symbol": "SPY",
                    "ex_date": "2024-03-15",
                    "rate": 1.595,
                    "process_date": "2024-03-15",
                    "id": "e8d69f0c-1122-3344-5566-778899aabbcc",
                    "special": False,
                },
            ]
        },
        "next_page_token": None,
    }
    return json.dumps(data).encode("utf-8")


def test_valid_dividend_payload_parsing() -> None:
    payload = _build_valid_payload()
    report = validate_and_parse_dividend_records(payload)

    assert report.is_qualified is True
    assert report.record_count == 2
    assert report.provider_mapping_status == DIVIDEND_PROVIDER_MAPPING_QUALIFIED
    assert report.pit_vintage_status == DIVIDEND_POINT_IN_TIME_VINTAGE_NOT_GUARANTEED
    assert report.max_accessed_date == "2024-03-15"
    assert report.records[0].rate == Decimal("1.078442")
    assert report.records[1].rate == Decimal("1.595")


def test_fail_closed_on_forbidden_oos_ex_date() -> None:
    """Any ex_date >= 2024-05-01 must immediately raise DataContractError."""
    data = {
        "corporate_actions": {
            "cash_dividends": [
                {
                    "symbol": "SPY",
                    "ex_date": "2024-05-01",
                    "rate": 1.50,
                    "process_date": "2024-05-01",
                    "id": "bad-id",
                    "special": False,
                }
            ]
        },
        "next_page_token": None,
    }
    with pytest.raises(DataContractError, match="FORBIDDEN_OOS_EX_DATE"):
        validate_and_parse_dividend_records(json.dumps(data).encode("utf-8"))


def test_fail_closed_on_ex_date_before_start() -> None:
    """Any ex_date < 2007-01-01 must raise DataContractError."""
    data = {
        "corporate_actions": {
            "cash_dividends": [
                {
                    "symbol": "SPY",
                    "ex_date": "2006-12-15",
                    "rate": 0.50,
                    "id": "too-early",
                }
            ]
        },
        "next_page_token": None,
    }
    with pytest.raises(DataContractError, match="EX_DATE_BEFORE_START"):
        validate_and_parse_dividend_records(json.dumps(data).encode("utf-8"))


def test_fail_closed_on_incomplete_pagination() -> None:
    """Presence of next_page_token indicates partial fetch, must raise DataContractError."""
    data = {
        "corporate_actions": {"cash_dividends": []},
        "next_page_token": "token-12345",
    }
    with pytest.raises(DataContractError, match="PAGINATION_INCOMPLETE"):
        validate_and_parse_dividend_records(json.dumps(data).encode("utf-8"))


def test_fail_closed_on_nonpositive_rate() -> None:
    """Dividend rate must be positive."""
    data = {
        "corporate_actions": {
            "cash_dividends": [
                {
                    "symbol": "SPY",
                    "ex_date": "2020-03-20",
                    "rate": 0.0,
                    "id": "zero-rate",
                }
            ]
        },
        "next_page_token": None,
    }
    with pytest.raises(DataContractError, match="NON_POSITIVE_RATE"):
        validate_and_parse_dividend_records(json.dumps(data).encode("utf-8"))
