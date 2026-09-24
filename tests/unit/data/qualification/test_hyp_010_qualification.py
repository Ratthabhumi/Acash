"""Unit tests for HYP_010 qualification path (mocked/synthetic only, no network)."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.hyp_010_qual_client import (
    HYP010AlpacaClient,
    HYP010_EXPECTED_PROBE_SESSIONS,
    assert_probe_sessions,
)
from acash.data.qualification.hyp_010_sponsor_authority import (
    parse_sponsor_records,
    qualify_sponsor_authority,
)
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment


def _bar_row(session: str) -> Dict[str, Any]:
    return {"t": f"{session}T05:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0,
            "c": 100.5, "v": 1000}


def _client(handler: Callable[[httpx.Request], httpx.Response], calls: List[int]) -> HYP010AlpacaClient:
    def _wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return handler(request)

    from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider

    return HYP010AlpacaClient(
        transport=httpx.MockTransport(_wrapped),
        credential_provider=EnvAlpacaCredentialProvider(
            environ={"ACASH_ALPACA_API_KEY_ID": "T", "ACASH_ALPACA_API_SECRET": "T"}
        ),
        http_attempt_listener=lambda: calls.append(10),
    )


def _probe_kwargs() -> Dict[str, Any]:
    return {
        "start_utc": datetime(2017, 1, 3, tzinfo=timezone.utc),
        "end_utc": datetime(2017, 1, 6, tzinfo=timezone.utc),
        "feed": MarketDataFeed.SIP,
        "timeframe": "1Day",
    }


def test_symbol_allowlist_rejects_before_network() -> None:
    calls: List[int] = []
    client = _client(lambda r: httpx.Response(200, json={"bars": []}), calls)
    with pytest.raises(DataContractError):
        client.fetch_tiny_probe(symbol="QQQ", adjustment=PriceAdjustment.RAW, **_probe_kwargs())
    assert calls == []


def test_timeframe_feed_adjustment_locked() -> None:
    calls: List[int] = []
    client = _client(lambda r: httpx.Response(200, json={"bars": []}), calls)
    with pytest.raises(DataContractError):
        client.fetch_tiny_probe(symbol="SPY", adjustment=PriceAdjustment.RAW,
                                timeframe="1Min", **{k: v for k, v in _probe_kwargs().items() if k != "timeframe"})
    assert calls == []


def test_exact_probe_dates_only() -> None:
    calls: List[int] = []
    client = _client(lambda r: httpx.Response(200, json={"bars": []}), calls)
    with pytest.raises(DataContractError):
        client.fetch_tiny_probe(
            symbol="SPY", adjustment=PriceAdjustment.RAW,
            start_utc=datetime(2017, 1, 3, tzinfo=timezone.utc),
            end_utc=datetime(2017, 1, 10, tzinfo=timezone.utc),
            feed=MarketDataFeed.SIP, timeframe="1Day",
        )
    with pytest.raises(DataContractError):
        client.fetch_tiny_probe(
            symbol="SPY", adjustment=PriceAdjustment.RAW,
            start_utc=datetime(2021, 1, 4, tzinfo=timezone.utc),
            end_utc=datetime(2021, 1, 8, tzinfo=timezone.utc),
            feed=MarketDataFeed.SIP, timeframe="1Day",
        )
    assert calls == []


def test_expected_four_sessions_and_alignment() -> None:
    assert list(HYP010_EXPECTED_PROBE_SESSIONS) == [
        date(2017, 1, 3), date(2017, 1, 4), date(2017, 1, 5), date(2017, 1, 6)
    ]
    calls: List[int] = []
    rows = [_bar_row(d) for d in ("2017-01-03", "2017-01-04", "2017-01-05", "2017-01-06")]
    client = _client(lambda r: httpx.Response(200, json={"bars": rows}), calls)
    result = client.fetch_tiny_probe(symbol="VEU", adjustment=PriceAdjustment.SPLIT, **_probe_kwargs())
    assert assert_probe_sessions(result.bars, "VEU") == list(HYP010_EXPECTED_PROBE_SESSIONS)
    assert calls.count(10) == 1


def test_duplicate_spill_fail() -> None:
    from acash.data.qualification.daily_models import DailyBar

    def _mk(session: str) -> DailyBar:
        return DailyBar(
            timestamp_utc=datetime.fromisoformat(f"{session}T05:00:00+00:00"),
            open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
            close=Decimal("100.5"), volume=Decimal("1000"),
        )

    bars = [_mk(d) for d in ("2017-01-03", "2017-01-04", "2017-01-05", "2017-01-06")]
    assert assert_probe_sessions(bars, "SPY")
    with pytest.raises(DataContractError):
        assert_probe_sessions(bars[:3], "SPY")
    with pytest.raises(DataContractError):
        assert_probe_sessions(bars + [bars[0]], "SPY")


def test_sponsor_identity_mapping_and_unofficial_rejected() -> None:
    recs = [{
        "ex_date": "2020-03-20", "cash_distribution": "1.0",
        "payable_date": "2020-04-30",
    }]
    parsed = parse_sponsor_records("SPY", recs, "SSGA_OFFICIAL", "STATE_STREET_SPDR_OFFICIAL")
    assert len(parsed) == 1
    with pytest.raises(DataContractError):
        parse_sponsor_records("SPY", recs, "YAHOO_UNOFFICIAL", "STATE_STREET_SPDR_OFFICIAL")
    with pytest.raises(DataContractError):
        parse_sponsor_records("SPY", recs, "SSGA_OFFICIAL", "VANGUARD_OFFICIAL")


def test_missing_fields_fail() -> None:
    with pytest.raises(DataContractError):
        parse_sponsor_records("AGG", [{"cash_distribution": "1.0", "payable_date": "2020-01-31"}],
                              "ISHARES_OFFICIAL", "BLACKROCK_ISHARES_OFFICIAL")
    with pytest.raises(DataContractError):
        parse_sponsor_records("AGG", [{"ex_date": "2020-01-10", "payable_date": "2020-01-31"}],
                              "ISHARES_OFFICIAL", "BLACKROCK_ISHARES_OFFICIAL")
    with pytest.raises(DataContractError):
        parse_sponsor_records("AGG", [{"ex_date": "2020-01-10", "cash_distribution": "1.0"}],
                              "ISHARES_OFFICIAL", "BLACKROCK_ISHARES_OFFICIAL")


def test_contradictory_duplicates_fail() -> None:
    recs = [
        {"ex_date": "2020-03-20", "cash_distribution": "1.0", "payable_date": "2020-04-30"},
        {"ex_date": "2020-03-20", "cash_distribution": "1.5", "payable_date": "2020-04-30"},
    ]
    parsed = parse_sponsor_records("VEU", recs, "VANGUARD_OFFICIAL", "VANGUARD_OFFICIAL")
    qual = qualify_sponsor_authority("VEU", "VANGUARD_OFFICIAL", parsed)
    assert qual.classification == "BLOCKED_VEU_DIVIDEND_AUTHORITY_CONTRADICTORY_RECORDS"


def _quarterly_series(symbol: str, sponsor: str, start_year: int, end_year: int) -> List[Any]:
    recs = []
    for year in range(start_year, end_year + 1):
        for month in (3, 6, 9, 12):
            recs.append({
                "ex_date": f"{year}-{month:02d}-20",
                "cash_distribution": "1.0",
                "payable_date": f"{year}-{month:02d}-30",
            })
    return parse_sponsor_records(symbol, recs, f"{sponsor}_OFFICIAL", sponsor)


def test_veu_incomplete_2016_coverage_fails() -> None:
    recs = _quarterly_series("VEU", "VANGUARD_OFFICIAL", 2017, 2024)
    qual = qualify_sponsor_authority("VEU", "VANGUARD_OFFICIAL", recs)
    assert qual.classification == "BLOCKED_VEU_DIVIDEND_AUTHORITY_COVERAGE_GAP"
    assert "2016-Q1" in qual.coverage_gaps


def test_multi_artifact_same_sponsor_can_pass() -> None:
    early = _quarterly_series("VEU", "VANGUARD_OFFICIAL", 2016, 2019)
    late = _quarterly_series("VEU", "VANGUARD_OFFICIAL", 2020, 2024)
    qual = qualify_sponsor_authority("VEU", "VANGUARD_OFFICIAL", early + late,
                                     source_artifact_hashes=("aaa", "bbb"))
    assert qual.classification == "VEU_DIVIDEND_AUTHORITY_QUALIFIED"
    assert qual.coverage_complete is True


def test_agg_monthly_not_silently_collapsed() -> None:
    recs = []
    for year in (2016, 2017):
        for month in range(1, 13):
            recs.append({
                "ex_date": f"{year}-{month:02d}-10",
                "cash_distribution": "0.2",
                "payable_date": f"{year}-{month:02d}-28",
            })
    parsed = parse_sponsor_records("AGG", recs, "ISHARES_OFFICIAL", "BLACKROCK_ISHARES_OFFICIAL")
    qual = qualify_sponsor_authority("AGG", "BLACKROCK_ISHARES_OFFICIAL", parsed)
    # Synthetic series spans only 2016-2017 AND contains January ex-dates, which
    # contradict the documented Feb-Dec schedule -> fail-closed block either way.
    assert qual.classification in (
        "BLOCKED_AGG_DIVIDEND_AUTHORITY_COVERAGE_GAP",
        "BLOCKED_AGG_DIVIDEND_AUTHORITY_SCHEDULE_CONTRADICTION",
    )


def _feb_dec_series(symbol: str, sponsor: str, start_year: int, end_year: int) -> List[Any]:
    recs = []
    for year in range(start_year, end_year + 1):
        for month in range(2, 13):
            recs.append({
                "ex_date": f"{year}-{month:02d}-05",
                "cash_distribution": "0.3",
                "payable_date": f"{year}-{month:02d}-10",
            })
        recs.append({
            "ex_date": f"{year}-12-18",
            "cash_distribution": "0.35",
            "payable_date": f"{year}-12-23",
        })
    return parse_sponsor_records(symbol, recs, f"{sponsor}_OFFICIAL", sponsor)


def test_affirmed_zero_accepted_with_flag_negative_rejected() -> None:
    recs = parse_sponsor_records(
        "BIL",
        [{"ex_date": "2016-02-01", "cash_distribution": "0.000000", "payable_date": "2016-02-09"}],
        "SSGA_OFFICIAL",
        "STATE_STREET_SPDR_OFFICIAL",
    )
    assert len(recs) == 1
    assert recs[0].affirmed_zero is True
    assert recs[0].cash_amount == Decimal("0")
    with pytest.raises(DataContractError):
        parse_sponsor_records(
            "BIL",
            [{"ex_date": "2016-02-01", "cash_distribution": "-0.5", "payable_date": "2016-02-09"}],
            "SSGA_OFFICIAL",
            "STATE_STREET_SPDR_OFFICIAL",
        )


def test_spy_bil_independent_and_no_d0_inference() -> None:
    spy = _quarterly_series("SPY", "STATE_STREET_SPDR_OFFICIAL", 2016, 2024)
    bil = _feb_dec_series("BIL", "STATE_STREET_SPDR_OFFICIAL", 2016, 2024)
    q_spy = qualify_sponsor_authority("SPY", "STATE_STREET_SPDR_OFFICIAL", spy)
    q_bil = qualify_sponsor_authority("BIL", "STATE_STREET_SPDR_OFFICIAL", bil)
    assert q_spy.classification == "SPY_DIVIDEND_AUTHORITY_QUALIFIED"
    assert q_bil.classification == "BIL_DIVIDEND_AUTHORITY_QUALIFIED"
    assert q_bil.records_count == 9 * 12
    # Removing one BIL month fails BIL only; SPY unaffected.
    bil_short = [r for r in bil if not (r.ex_date.year == 2020 and r.ex_date.month == 6)]
    q_bil2 = qualify_sponsor_authority("BIL", "STATE_STREET_SPDR_OFFICIAL", bil_short)
    assert q_bil2.classification == "BLOCKED_BIL_DIVIDEND_AUTHORITY_COVERAGE_GAP"
    # A January ex-date anywhere contradicts the Feb-Dec schedule.
    bil_jan = bil + parse_sponsor_records(
        "BIL",
        [{"ex_date": "2010-01-04", "cash_distribution": "0.1", "payable_date": "2010-01-08"}],
        "STATE_STREET_SPDR_OFFICIAL",
        "STATE_STREET_SPDR_OFFICIAL",
    )
    q_bil3 = qualify_sponsor_authority("BIL", "STATE_STREET_SPDR_OFFICIAL", bil_jan)
    assert q_bil3.classification == "BLOCKED_BIL_DIVIDEND_AUTHORITY_SCHEDULE_CONTRADICTION"
