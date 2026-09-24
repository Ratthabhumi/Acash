# tests/unit/data/qualification/test_hyp_009_daily_alpaca_client.py
"""Expanded unit tests for the HYP_009 daily SIP qualification contract.

Frozen contract under test (CORE-001 / HYP_009 R1 + pre-R2 clarification):

- symbol = SPY, timeframe = 1Day, feed = SIP
- adjustments = SPLIT, RAW
- authorized window: 2016-01-01 <= start_date <= end_date <= 2020-12-31

All pre-network violations must raise BEFORE any HTTP execution (HTTP call
count == 0). No real network in tests: httpx.MockTransport only.
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.client import (
    AlpacaHistoricalSipClient,
    SipContractViolationError,
)
from acash.data.qualification.daily_models import DailyBar
from acash.data.qualification.hyp_009_daily_client import (
    HYP009AlpacaClient,
    Hyp009PreNetworkGuard,
    Hyp009RetrievalResult,
    assert_split_raw_alignment,
)
from acash.data.qualification.models import (
    HistoricalSipBar,
    MarketDataFeed,
    PriceAdjustment,
)
from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider


# =============================================================================
# Fixtures & helpers (mocked transport only - zero real network)
# =============================================================================


class MockCredentialProvider(EnvAlpacaCredentialProvider):
    def __init__(self, key_id: str = "FAKE_KEY_ID_123", secret: str = "FAKE_SECRET_XYZ") -> None:
        super().__init__(
            venue="ALPACA_PAPER",
            api_key_id=key_id,
            api_secret=secret,
        )


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _row(
    day: date,
    o: Any = "200.0",
    h: Any = "210.0",
    l: Any = "190.0",
    c: Any = "205.0",
    v: Any = "1000000",
) -> Dict[str, Any]:
    return {
        "t": f"{day.isoformat()}T00:00:00Z",
        "o": o,
        "h": h,
        "l": l,
        "c": c,
        "v": v,
    }


def _payload(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"bars": rows, "symbol": "SPY", "next_page_token": None}


def _make_client(rows: List[Dict[str, Any]], calls: List[httpx.Request]) -> HYP009AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=_payload(rows))

    transport = httpx.MockTransport(handler)
    return HYP009AlpacaClient(
        credential_provider=MockCredentialProvider(),
        transport=transport,
    )


NOV_2016_WINDOW = (_dt(2016, 11, 1), _dt(2016, 11, 4))
NOV_2016_ROWS = [
    _row(date(2016, 11, 1)),
    _row(date(2016, 11, 2)),
    _row(date(2016, 11, 3)),
    _row(date(2016, 11, 4)),
]


def _fetch(
    client: HYP009AlpacaClient,
    rows_window: Any = None,
    **kwargs: Any,
) -> Hyp009RetrievalResult:
    params: Dict[str, Any] = {
        "symbol": "SPY",
        "start_utc": _dt(2016, 11, 1),
        "end_utc": _dt(2016, 11, 4),
    }
    params.update(kwargs)
    return client.fetch_historical_bars(**params)


# =============================================================================
# 1-9. Symbol / timeframe / feed / adjustment contract
# =============================================================================


def test_01_spy_accepted() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    result = _fetch(client)
    assert isinstance(result, Hyp009RetrievalResult)
    assert len(result.bars) == 4
    assert all(isinstance(bar, DailyBar) for bar in result.bars)
    assert result.bars[0].open == Decimal("200.0")
    assert len(calls) == 1


def test_02_non_spy_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        _fetch(client, symbol="QQQ")
    assert calls == []


def test_03_1day_accepted() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    result = _fetch(client, timeframe="1Day")
    assert len(result.bars) == 4


def test_04_non_1day_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        _fetch(client, timeframe="1Min")
    assert calls == []


def test_05_sip_accepted() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    result = _fetch(client, feed=MarketDataFeed.SIP)
    assert len(result.bars) == 4


def test_06_non_sip_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        _fetch(client, feed=MarketDataFeed.IEX)
    assert calls == []


def test_07_split_accepted() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    result = _fetch(client, adjustment=PriceAdjustment.SPLIT)
    assert len(result.bars) == 4


def test_08_raw_accepted() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    result = _fetch(client, adjustment=PriceAdjustment.RAW)
    assert len(result.bars) == 4


def test_09_unsupported_adjustment_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        _fetch(client, adjustment=PriceAdjustment.DIVIDEND)
    assert calls == []


# =============================================================================
# 10-17. Authorized window boundaries
# =============================================================================


def test_10_lower_boundary_2016_01_01_accepted() -> None:
    # 2016-01-01 is itself a market holiday: the window must pass pre-network
    # validation while the provider legitimately returns no row for it.
    calls: List[httpx.Request] = []
    rows = [_row(date(2016, 1, 4))]
    client = _make_client(rows, calls)
    result = client.fetch_historical_bars(
        symbol="SPY",
        start_utc=_dt(2016, 1, 1),
        end_utc=_dt(2016, 1, 4),
    )
    assert len(result.bars) == 1
    assert result.bars[0].timestamp_utc.date() == date(2016, 1, 4)


def test_11_upper_boundary_2020_12_31_accepted() -> None:
    calls: List[httpx.Request] = []
    rows = [
        _row(date(2020, 12, 28)),
        _row(date(2020, 12, 29)),
        _row(date(2020, 12, 30)),
        _row(date(2020, 12, 31)),
    ]
    client = _make_client(rows, calls)
    result = client.fetch_historical_bars(
        symbol="SPY",
        start_utc=_dt(2020, 12, 28),
        end_utc=_dt(2020, 12, 31),
    )
    assert len(result.bars) == 4


def test_12_pre_2016_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=_dt(2015, 12, 31),
            end_utc=_dt(2016, 1, 4),
        )
    assert calls == []


def test_13_2021_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=_dt(2020, 12, 31),
            end_utc=_dt(2021, 1, 1),
        )
    assert calls == []


def test_14_2024_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=_dt(2024, 1, 2),
            end_utc=_dt(2024, 1, 3),
        )
    assert calls == []


def test_15_2025_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=_dt(2025, 6, 2),
            end_utc=_dt(2025, 6, 3),
        )
    assert calls == []


def test_16_2026_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=_dt(2026, 8, 14),
            end_utc=_dt(2026, 8, 15),
        )
    assert calls == []


def test_17_start_after_end_rejected_pre_network() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=_dt(2016, 11, 4),
            end_utc=_dt(2016, 11, 1),
        )
    assert calls == []


def test_naive_datetimes_rejected_fail_closed() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    naive_start = datetime(2016, 11, 1)
    naive_end = datetime(2016, 11, 4)
    assert naive_start.tzinfo is None
    with pytest.raises(DataContractError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=naive_start,
            end_utc=naive_end,
        )
    assert calls == []


# =============================================================================
# 18. Forbidden request performs zero HTTP calls
# =============================================================================


def test_18_forbidden_request_zero_http_calls() -> None:
    calls: List[httpx.Request] = []
    client = _make_client(NOV_2016_ROWS, calls)
    with pytest.raises(SipContractViolationError):
        client.fetch_historical_bars(
            symbol="QQQ",
            start_utc=_dt(2016, 11, 1),
            end_utc=_dt(2016, 11, 4),
            feed=MarketDataFeed.SIP,
            adjustment=PriceAdjustment.SPLIT,
            timeframe="1Day",
        )
    assert calls == []


# =============================================================================
# 19-29. Response validation (spill, duplicates, OHLCV, calendar)
# =============================================================================


def test_19_spill_before_start_rejected() -> None:
    calls: List[httpx.Request] = []
    rows = [_row(date(2016, 10, 31))] + NOV_2016_ROWS
    client = _make_client(rows, calls)
    with pytest.raises(SipContractViolationError, match="precedes"):
        _fetch(client)


def test_20_spill_after_end_rejected() -> None:
    calls: List[httpx.Request] = []
    rows = NOV_2016_ROWS + [_row(date(2016, 11, 7))]
    client = _make_client(rows, calls)
    with pytest.raises(SipContractViolationError, match="exceeds"):
        _fetch(client)


def test_21_duplicate_session_rejected() -> None:
    calls: List[httpx.Request] = []
    rows = NOV_2016_ROWS + [_row(date(2016, 11, 2))]
    client = _make_client(rows, calls)
    with pytest.raises(SipContractViolationError, match="duplicate"):
        _fetch(client)


def test_22_zero_price_rejected() -> None:
    calls: List[httpx.Request] = []
    client = _make_client([_row(date(2016, 11, 1), o="0")], calls)
    with pytest.raises(SipContractViolationError):
        _fetch(client)


def test_23_negative_price_rejected() -> None:
    calls: List[httpx.Request] = []
    client = _make_client([_row(date(2016, 11, 1), c="-5")], calls)
    with pytest.raises(SipContractViolationError):
        _fetch(client)


def test_24_invalid_ohlc_geometry_rejected() -> None:
    calls: List[httpx.Request] = []
    # high (205) < max(open, close) = max(200, 210) = 210.
    client = _make_client(
        [_row(date(2016, 11, 1), o="200.0", h="205.0", l="190.0", c="210.0")],
        calls,
    )
    with pytest.raises(SipContractViolationError):
        _fetch(client)


def test_25_negative_volume_rejected() -> None:
    calls: List[httpx.Request] = []
    client = _make_client([_row(date(2016, 11, 1), v="-10")], calls)
    with pytest.raises(SipContractViolationError):
        _fetch(client)


def test_26_null_and_malformed_rows_rejected() -> None:
    calls: List[httpx.Request] = []
    missing_close = dict(_row(date(2016, 11, 1)))
    del missing_close["c"]
    client = _make_client([missing_close], calls)
    with pytest.raises(SipContractViolationError, match="null/missing"):
        _fetch(client)

    null_timestamp = _row(date(2016, 11, 1))
    null_timestamp["t"] = None
    client = _make_client([null_timestamp], calls)
    with pytest.raises(SipContractViolationError, match="null/missing"):
        _fetch(client)

    bad_timestamp = _row(date(2016, 11, 1))
    bad_timestamp["t"] = "not-a-timestamp"
    client = _make_client([bad_timestamp], calls)
    with pytest.raises(SipContractViolationError, match="malformed timestamp"):
        _fetch(client)

    non_finite = _row(date(2016, 11, 1), o="nan")
    client = _make_client([non_finite], calls)
    with pytest.raises(SipContractViolationError):
        _fetch(client)


def test_27_weekend_row_rejected() -> None:
    # Saturday 2016-11-05 is inside the requested window but is not a session.
    calls: List[httpx.Request] = []
    rows = NOV_2016_ROWS + [_row(date(2016, 11, 5)), _row(date(2016, 11, 7))]
    client = _make_client(rows, calls)
    with pytest.raises(SipContractViolationError, match="weekend"):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=_dt(2016, 11, 1),
            end_utc=_dt(2016, 11, 7),
        )


def test_28_full_holiday_row_rejected() -> None:
    # Thanksgiving 2016-11-24 is a CA-1 full holiday inside the window.
    calendar = NyseCa1Calendar()
    assert calendar.is_holiday(date(2016, 11, 24)) is True
    calls: List[httpx.Request] = []
    rows = [
        _row(date(2016, 11, 21)),
        _row(date(2016, 11, 22)),
        _row(date(2016, 11, 23)),
        _row(date(2016, 11, 24)),
    ]
    client = _make_client(rows, calls)
    with pytest.raises(SipContractViolationError, match="holiday"):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=_dt(2016, 11, 21),
            end_utc=_dt(2016, 11, 25),
        )


def test_29_legitimate_early_close_session_accepted() -> None:
    # 2016-11-25 is a REAL CA-1 pinned 13:00 ET early close (day after
    # Thanksgiving) - accepted as a valid session, not invented.
    calendar = NyseCa1Calendar()
    assert calendar.is_trading_session(date(2016, 11, 25)) is True
    assert calendar.is_early_close(date(2016, 11, 25)) is True
    calls: List[httpx.Request] = []
    client = _make_client([_row(date(2016, 11, 25))], calls)
    result = client.fetch_historical_bars(
        symbol="SPY",
        start_utc=_dt(2016, 11, 25),
        end_utc=_dt(2016, 11, 25),
    )
    assert len(result.bars) == 1
    assert result.bars[0].timestamp_utc.date() == date(2016, 11, 25)


# =============================================================================
# 30-31. Split/raw date-set alignment
# =============================================================================


def _daily_bar(day: date) -> DailyBar:
    return DailyBar(
        timestamp_utc=_dt(day.year, day.month, day.day),
        open=Decimal("200.0"),
        high=Decimal("210.0"),
        low=Decimal("190.0"),
        close=Decimal("205.0"),
        volume=Decimal("1000000"),
    )


def test_30_split_raw_date_mismatch_rejected() -> None:
    split_bars = [_daily_bar(date(2016, 11, 1)), _daily_bar(date(2016, 11, 2))]
    raw_bars = [_daily_bar(date(2016, 11, 1)), _daily_bar(date(2016, 11, 3))]
    with pytest.raises(SipContractViolationError):
        assert_split_raw_alignment(split_bars, raw_bars)


def test_31_aligned_split_raw_result_accepted() -> None:
    split_bars = [_daily_bar(date(2016, 11, 1)), _daily_bar(date(2016, 11, 2))]
    raw_bars = [_daily_bar(date(2016, 11, 2)), _daily_bar(date(2016, 11, 1))]
    aligned = assert_split_raw_alignment(split_bars, raw_bars)
    assert aligned == [date(2016, 11, 1), date(2016, 11, 2)]


# =============================================================================
# 32. Legacy intraday client untouched (1Min/RAW retained)
# =============================================================================


def test_32_legacy_client_retains_1min_raw_behavior() -> None:
    calls: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "bars": [
                    {
                        "t": "2024-01-02T14:30:00Z",
                        "o": 470.0,
                        "h": 470.5,
                        "l": 469.8,
                        "c": 470.3,
                        "v": 1000,
                    }
                ],
                "symbol": "SPY",
                "next_page_token": None,
            },
        )

    transport = httpx.MockTransport(handler)
    client = AlpacaHistoricalSipClient(
        credential_provider=MockCredentialProvider(),
        transport=transport,
    )
    result = client.fetch_historical_bars(
        symbol="SPY",
        start_utc=datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc),
        end_utc=datetime(2024, 1, 2, 14, 31, tzinfo=timezone.utc),
        feed=MarketDataFeed.SIP,
        adjustment=PriceAdjustment.RAW,
        timeframe="1Min",
    )
    assert len(result.bars) == 1
    assert isinstance(result.bars[0], HistoricalSipBar)
    assert len(calls) == 1

    # RAW-only contract preserved: SPLIT still rejected.
    with pytest.raises(SipContractViolationError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc),
            end_utc=datetime(2024, 1, 2, 14, 31, tzinfo=timezone.utc),
            feed=MarketDataFeed.SIP,
            adjustment=PriceAdjustment.SPLIT,
            timeframe="1Min",
        )


# =============================================================================
# Guard unit + runner dry-run safety
# =============================================================================


def test_guard_window_boundaries() -> None:
    guard = Hyp009PreNetworkGuard()
    start, end = guard.validate_window(_dt(2016, 1, 1), _dt(2020, 12, 31))
    assert (start, end) == (date(2016, 1, 1), date(2020, 12, 31))
    with pytest.raises(SipContractViolationError):
        guard.validate_window(_dt(2015, 12, 31), _dt(2016, 1, 4))


def test_runner_defaults_to_no_network(monkeypatch: Any) -> None:
    # The qualification runner must default to zero network calls; hermetic:
    # strip any ambient credentials so the dry-run path is deterministic.
    monkeypatch.delenv("ACASH_ALPACA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ACASH_ALPACA_API_SECRET", raising=False)
    repo_root = Path(__file__).resolve().parents[4]
    spec = importlib.util.spec_from_file_location(
        "execute_hyp_009_r2_provider_qualification",
        repo_root / "scripts" / "execute_hyp_009_r2_provider_qualification.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.parse_args([]).execute_network is False
    assert module.main([]) == module.EXIT_BLOCKED
