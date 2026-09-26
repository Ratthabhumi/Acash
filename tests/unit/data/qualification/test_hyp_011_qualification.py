"""Unit tests for HYP_011 qualification path (mocked/synthetic only, no network)."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.hyp_011_qual_client import (
    HYP011AlpacaClient,
    HYP011_EXPECTED_PROBE_SESSIONS,
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


def _client(handler: Callable[[httpx.Request], httpx.Response], calls: List[int]) -> HYP011AlpacaClient:
    def _wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return handler(request)

    from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider

    return HYP011AlpacaClient(
        transport=httpx.MockTransport(_wrapped),
        credential_provider=EnvAlpacaCredentialProvider(
            environ={"ACASH_ALPACA_API_KEY_ID": "T", "ACASH_ALPACA_API_SECRET": "T"}
        ),
        http_attempt_listener=lambda: calls.append(10),
    )


def _probe_kwargs() -> Dict[str, Any]:
    return {
        "start_utc": datetime(2016, 1, 4, tzinfo=timezone.utc),
        "end_utc": datetime(2016, 1, 7, tzinfo=timezone.utc),
        "feed": MarketDataFeed.SIP,
        "timeframe": "1Day",
    }


def test_allowlist_acwi_agg_spy_only() -> None:
    calls: List[int] = []
    client = _client(lambda r: httpx.Response(200, json={"bars": []}), calls)
    for bad in ("VEU", "QQQ", "BIL", "IVV", ""):
        with pytest.raises(DataContractError):
            client.fetch_tiny_probe(symbol=bad, adjustment=PriceAdjustment.RAW, **_probe_kwargs())
    assert calls == []


def test_exact_window_and_contract_locked() -> None:
    calls: List[int] = []
    client = _client(lambda r: httpx.Response(200, json={"bars": []}), calls)
    with pytest.raises(DataContractError):
        client.fetch_tiny_probe(
            symbol="ACWI", adjustment=PriceAdjustment.RAW,
            start_utc=datetime(2016, 1, 4, tzinfo=timezone.utc),
            end_utc=datetime(2016, 1, 8, tzinfo=timezone.utc),
            feed=MarketDataFeed.SIP, timeframe="1Day",
        )
    with pytest.raises(DataContractError):
        client.fetch_tiny_probe(symbol="ACWI", adjustment=PriceAdjustment.RAW,
                                timeframe="1Min",
                                **{k: v for k, v in _probe_kwargs().items() if k != "timeframe"})
    with pytest.raises(DataContractError):
        client.fetch_tiny_probe(symbol="ACWI", adjustment=PriceAdjustment.RAW,
                                feed=MarketDataFeed.IEX,
                                **{k: v for k, v in _probe_kwargs().items() if k != "feed"})
    assert calls == []


def test_expected_sessions_and_pass_shape() -> None:
    assert list(HYP011_EXPECTED_PROBE_SESSIONS) == [
        date(2016, 1, 4), date(2016, 1, 5), date(2016, 1, 6), date(2016, 1, 7)
    ]
    calls: List[int] = []
    rows = [_bar_row(d) for d in ("2016-01-04", "2016-01-05", "2016-01-06", "2016-01-07")]
    client = _client(lambda r: httpx.Response(200, json={"bars": rows}), calls)
    result = client.fetch_tiny_probe(symbol="AGG", adjustment=PriceAdjustment.SPLIT, **_probe_kwargs())
    assert assert_probe_sessions(result.bars, "AGG") == list(HYP011_EXPECTED_PROBE_SESSIONS)
    assert calls.count(10) == 1


def test_missing_extra_duplicate_spill_fail() -> None:
    from acash.data.qualification.daily_models import DailyBar

    def _mk(session: str) -> DailyBar:
        return DailyBar(
            timestamp_utc=datetime.fromisoformat(f"{session}T05:00:00+00:00"),
            open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
            close=Decimal("100.5"), volume=Decimal("1000"),
        )

    full = [_mk(d) for d in ("2016-01-04", "2016-01-05", "2016-01-06", "2016-01-07")]
    assert assert_probe_sessions(full, "SPY")
    with pytest.raises(DataContractError):
        assert_probe_sessions(full[:3], "SPY")
    with pytest.raises(DataContractError):
        assert_probe_sessions(full + [full[0]], "SPY")


def _semiannual_series(sponsor: str, start_year: int, end_year: int) -> List[Any]:
    recs = []
    for year in range(start_year, end_year + 1):
        for month, day in ((6, 20), (12, 18)):
            recs.append({
                "ex_date": f"{year}-{month:02d}-{day:02d}",
                "cash_distribution": "0.5",
                "payable_date": f"{year}-{month:02d}-28",
            })
    return parse_sponsor_records("ACWI", recs, "ISHARES_OFFICIAL", sponsor)


def test_acwi_semiannual_coverage_and_missing_half_fails() -> None:
    full = _semiannual_series("BLACKROCK_ISHARES_OFFICIAL", 2016, 2024)
    qual = qualify_sponsor_authority("ACWI", "BLACKROCK_ISHARES_OFFICIAL", full)
    assert qual.classification == "ACWI_DIVIDEND_AUTHORITY_QUALIFIED"
    assert qual.records_count == 18
    short = [r for r in full if not (r.ex_date.year == 2020 and r.ex_date.month == 6)]
    qual2 = qualify_sponsor_authority("ACWI", "BLACKROCK_ISHARES_OFFICIAL", short)
    assert qual2.classification == "BLOCKED_ACWI_DIVIDEND_AUTHORITY_COVERAGE_GAP"
    assert "2020-H1" in qual2.coverage_gaps


def test_acwi_sponsor_mapping_and_special_extra_accepted() -> None:
    full = _semiannual_series("BLACKROCK_ISHARES_OFFICIAL", 2016, 2024)
    extra = parse_sponsor_records(
        "ACWI",
        [{"ex_date": "2020-12-28", "cash_distribution": "0.1", "payable_date": "2021-01-05"}],
        "ISHARES_OFFICIAL",
        "BLACKROCK_ISHARES_OFFICIAL",
    )
    qual = qualify_sponsor_authority("ACWI", "BLACKROCK_ISHARES_OFFICIAL", full + extra)
    assert qual.classification == "ACWI_DIVIDEND_AUTHORITY_QUALIFIED"
    with pytest.raises(DataContractError):
        parse_sponsor_records("ACWI", [{
            "ex_date": "2020-06-20", "cash_distribution": "0.5",
        }], "ISHARES_OFFICIAL", "BLACKROCK_ISHARES_OFFICIAL")


def test_agg_spy_reuse_paths_unchanged() -> None:
    # Sealed HYP_010 AGG manifest still qualifies under the shared module.
    import json
    from pathlib import Path

    agg = json.loads(Path(
        "docs/research/manifests/HYP_010_AGG_ISHARES_DIVIDEND_AUTHORITY.json"
    ).read_text(encoding="utf-8"))
    recs = parse_sponsor_records(
        "AGG",
        [{"ex_date": d["ex_date"], "cash_distribution": d["cash_distribution"],
          "payable_date": d["payable_date"]} for d in agg["distributions"]],
        "ISHARES_OFFICIAL_PAGE",
        "BLACKROCK_ISHARES_OFFICIAL",
    )
    qual = qualify_sponsor_authority("AGG", "BLACKROCK_ISHARES_OFFICIAL", recs)
    assert qual.classification == "AGG_DIVIDEND_AUTHORITY_QUALIFIED"
