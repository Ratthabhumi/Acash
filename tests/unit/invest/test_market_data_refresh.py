"""Market data refresh: provider adapters, endpoint allowlist, ODR-004 gate, refresh service, routes.

Synthetic data and in-memory transports only; no test opens a socket or marks a real provider live.
"""

from __future__ import annotations

import json
import socket
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.dashboard_api import market_service as ms
from acash.dashboard_api import private_input as pi
from acash.dashboard_api import private_view_server as srv
from acash.invest import market_authority as ma
from acash.invest import market_refresh as mr
from acash.market_data import providers as mp
from acash.invest.capacity_plan import CAPACITY_SCHEMA
from acash.invest.market_valuation import partial_snapshot
from acash.ppds import private_observation as po

SNAPSHOT = Path("docs/research/evidence/upi_v1_2_synthetic_snapshot.json")
CAPACITY = Path("docs/research/evidence/upi_v1_synthetic_capacity.json")
NOW = datetime(2026, 11, 3, 21, 30, tzinfo=timezone.utc)
CRED = ("SYNKEYID", "SYNSECRETVALUE123")
PORT, TOKEN, ORIGIN = 8765, "t" * 43, "http://127.0.0.1:3002"


class Store:
    def __init__(self, creds: Optional[Dict[str, Tuple[str, str]]] = None) -> None:
        self.creds = creds if creds is not None else {p: CRED for p in ma.ADAPTED_PROVIDERS}

    def lookup(self, provider_id: str) -> Optional[Tuple[str, str]]:
        return self.creds.get(provider_id)


class FakeTransport:
    def __init__(self, routes: Optional[Dict[str, Tuple[int, Any]]] = None, fail: Optional[str] = None) -> None:
        self.routes, self.fail = routes or {}, fail
        self.calls: List[mp.HttpRequest] = []

    def __call__(self, request: mp.HttpRequest) -> Tuple[int, bytes]:
        mp.assert_allowed(request)
        self.calls.append(request)
        if self.fail:
            raise DataContractError(f"{self.fail}: {request.provider_id}.")
        for fragment, (status, body) in self.routes.items():
            if fragment in request.url:
                return status, body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        return 404, b""


def _alpaca(prices: Dict[str, str], stamp: str = "2026-11-03T20:59:58.123456789Z") -> Dict[str, Any]:
    return {"trades": {s: {"t": stamp, "x": "V", "p": float(p) if "." in p else int(p), "s": 100, "c": ["@"], "i": 1, "z": "B"}
                       for s, p in prices.items()}}


PREV_SESSION_MS = int(datetime(2026, 11, 2, tzinfo=mr.NEW_YORK).timestamp() * 1000)


def _massive(symbol: str, close: Any, ms_stamp: int = PREV_SESSION_MS, adjusted: bool = False) -> Dict[str, Any]:
    return {"ticker": symbol, "adjusted": adjusted, "status": "OK", "resultsCount": 1,
            "results": [{"T": symbol, "c": close, "o": close, "h": close, "l": close, "v": 1, "t": ms_stamp}]}


BOT_UNIT = "(Unit: Baht / 1 Unit of Foreign Currency)"


def _bot(rows: List[Tuple[str, str]], currency: str = "USD",
         unit: str = BOT_UNIT) -> Dict[str, Any]:
    return {"result": {"api": "Daily Weighted-average Interbank Exchange Rate - THB / USD",
                       "data": {"data_header": {"report_uoq_name_eng": unit},
                                "data_detail": [{"period": d, "currency_id": currency, "mid_rate": r}
                                                for d, r in rows]}}}


def _clock() -> datetime:
    return NOW


def _allow() -> bool:
    return True


# ---- endpoint allowlist and egress ----------------------------------------------------------

@pytest.mark.parametrize("pid, url", [
    ("ALPACA_BASIC", "https://api.alpaca.markets/v2/orders?symbols=SYNA"),
    ("ALPACA_BASIC", "https://paper-api.alpaca.markets/v2/stocks/trades/latest?symbols=SYNA"),
    ("ALPACA_BASIC", "https://data.alpaca.markets/v2/account"),
    ("ALPACA_BASIC", "http://data.alpaca.markets/v2/stocks/trades/latest?symbols=SYNA"),
    ("ALPACA_BASIC", "https://data.alpaca.markets@evil.example/v2/stocks/trades/latest?symbols=SYNA"),
    ("ALPACA_BASIC", "https://data.alpaca.markets:8443/v2/stocks/trades/latest?symbols=SYNA"),
    ("ALPACA_BASIC", "https://data.alpaca.markets.evil.example/v2/stocks/trades/latest?symbols=SYNA"),
    ("ALPACA_BASIC", "https://data.alpaca.markets/v2/stocks/trades/latest?symbols=SYNA&qty=10"),
    ("ALPACA_BASIC", "https://data.alpaca.markets/v2/stocks/trades/latest?symbols=SYNA&symbols=SYNV"),
    ("ALPACA_BASIC", "https://data.alpaca.markets/v2/stocks/trades/latest?symbols=SYNA%20100%20shares"),
    ("MASSIVE_BASIC", "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?adjusted=false"),
    ("MASSIVE_BASIC", "https://api.massive.com/v2/aggs/ticker/../../x/prev?adjusted=false"),
    ("BOT_REFERENCE_FX", "https://169.254.169.254/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/"),
    ("BOT_REFERENCE_FX", "https://gateway.api.bot.or.th/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE"),
    ("BOT_REFERENCE_FX", "https://gateway.api.bot.or.th/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/get"),
    ("BOT_REFERENCE_FX", "https://gateway.api.bot.or.th/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/?year=2026"),
    ("BOT_HOLIDAYS", "https://gateway.api.bot.or.th/financial-institutions-holidays/get?year=2026"),
    ("BOT_HOLIDAYS", "https://gateway.api.bot.or.th/Stat-ExchangeRate/?year=2026"),
    ("WEBULL_TH_OPENAPI", "https://example.invalid/"),
])
def test_allowlist_refuses_trading_ssrf_and_private_egress(pid: str, url: str) -> None:
    with pytest.raises(DataContractError, match="ENDPOINT_|EGRESS_"):
        mp.assert_allowed(mp.HttpRequest(pid, url, {}))


def test_allowlist_refuses_unlisted_headers_and_transport_rechecks() -> None:
    url = mp.build_url("ALPACA_BASIC", "/v2/stocks/trades/latest", {"symbols": "SYNA,SYNV", "feed": "iex"})
    with pytest.raises(DataContractError, match="ENDPOINT_HEADER_NOT_ALLOWED"):
        mp.assert_allowed(mp.HttpRequest("ALPACA_BASIC", url, {"Cookie": "x"}))
    with pytest.raises(DataContractError, match="ENDPOINT_NOT_ALLOWED"):
        mp.urllib_transport(mp.HttpRequest("ALPACA_BASIC", "https://api.alpaca.markets/v2/orders", {}))


def test_adapters_send_only_symbols_and_keep_secrets_out_of_urls() -> None:
    t = FakeTransport({"trades/latest": (200, _alpaca({"SYNA": "10.5"})), "/prev": (200, _massive("SYNA", 10)),
                       "DAILY_AVG_EXG_RATE": (200, _bot([("2026-11-03", "33.10")]))})
    mp.AlpacaIEXMarketDataProvider(CRED, t, _allow, _clock).latest_prices(["SYNA", "not a symbol"], date(2026, 11, 3))
    mp.MassiveEODMarketDataProvider(CRED, t, _allow, _clock).latest_prices(["SYNA"], date(2026, 11, 3))
    mp.BOTReferenceFXProvider(CRED, t, _allow, _clock).reference_rates(date(2026, 11, 3))
    assert [c.provider_id for c in t.calls] == ["ALPACA_BASIC", "MASSIVE_BASIC", "BOT_REFERENCE_FX"]
    assert t.calls[0].url == "https://data.alpaca.markets/v2/stocks/trades/latest?symbols=SYNA&feed=iex"
    assert all(CRED[1] not in c.url and CRED[0] not in c.url for c in t.calls)
    assert t.calls[1].headers == {"Authorization": f"Bearer {CRED[1]}"}


# ---- Alpaca -----------------------------------------------------------------------------------

def test_alpaca_parses_iex_last_trade_with_new_york_session_date() -> None:
    t = FakeTransport({"trades/latest": (200, _alpaca({"SYNA": "187.25", "SYNT": "91"}))})
    obs = mp.AlpacaIEXMarketDataProvider(CRED, t, _allow, _clock).latest_prices(["SYNA", "SYNT", "SYNV"], date(2026, 11, 3))
    by = {o.security_id: o for o in obs}
    assert set(by) == {"SYNA", "SYNT"}
    assert by["SYNA"].price == Decimal("187.25") and by["SYNA"].price_type == "LAST_TRADE"
    assert by["SYNA"].coverage == "IEX_ONLY" and by["SYNA"].currency == "USD"
    assert by["SYNA"].market_timestamp == datetime(2026, 11, 3, 20, 59, 58, 123456, tzinfo=timezone.utc)
    assert by["SYNA"].market_date == date(2026, 11, 3)
    late = FakeTransport({"trades/latest": (200, _alpaca({"SYNA": "1"}, "2026-11-04T02:00:00Z"))})
    assert mp.AlpacaIEXMarketDataProvider(CRED, late, _allow, _clock).latest_prices(["SYNA"], date(2026, 11, 3))[0].market_date == date(2026, 11, 3)


@pytest.mark.parametrize("status, body, code", [
    (401, b"", "PROVIDER_ACCESS_DENIED"), (403, b"", "PROVIDER_ACCESS_DENIED"),
    (429, b"", "PROVIDER_RATE_LIMITED"), (503, b"", "PROVIDER_UNAVAILABLE"),
    (200, b"{not json", "PROVIDER_RESPONSE_INVALID"), (200, {"trades": []}, "PROVIDER_RESPONSE_INVALID"),
    (200, _alpaca({"SYNA": "0"}), "PROVIDER_RESPONSE_INVALID"), (200, _alpaca({"SYNA": "-1"}), "PROVIDER_RESPONSE_INVALID"),
    (200, _alpaca({"SYNA": "1"}, "2026-11-03 20:59:58"), "PROVIDER_RESPONSE_INVALID"),
    (200, {"trades": {"SYNA": {"t": "2026-11-03T20:59:58Z", "p": "NaN", "x": "V"}}}, "PROVIDER_RESPONSE_INVALID"),
    (200, {"trades": {"SYNA": {"t": "2026-11-03T20:59:58Z", "p": 1}}}, "PROVIDER_RESPONSE_INVALID"),
])
def test_alpaca_fails_closed(status: int, body: Any, code: str) -> None:
    t = FakeTransport({"trades/latest": (status, body)})
    with pytest.raises(DataContractError, match=code):
        mp.AlpacaIEXMarketDataProvider(CRED, t, _allow, _clock).latest_prices(["SYNA"], date(2026, 11, 3))


def test_transport_failure_and_rate_limit_make_no_request() -> None:
    with pytest.raises(DataContractError, match="PROVIDER_UNREACHABLE"):
        mp.AlpacaIEXMarketDataProvider(CRED, FakeTransport(fail="PROVIDER_UNREACHABLE"), _allow, _clock).latest_prices(["SYNA"], date(2026, 11, 3))
    t = FakeTransport()
    with pytest.raises(DataContractError, match="PROVIDER_RATE_LIMITED"):
        mp.AlpacaIEXMarketDataProvider(CRED, t, lambda: False, _clock).latest_prices(["SYNA"], date(2026, 11, 3))
    assert t.calls == []


# ---- Massive ----------------------------------------------------------------------------------

def test_massive_previous_close_budget_and_cache() -> None:
    t = FakeTransport({f"/ticker/{s}/prev": (200, _massive(s, 20 + i)) for i, s in enumerate("ABCDEFG")})
    budget = iter([True] * 5 + [False] * 10)
    provider = mp.MassiveEODMarketDataProvider(CRED, t, lambda: next(budget), _clock)
    obs = provider.latest_prices(list("ABCDEFG"), date(2026, 11, 3))
    assert len(obs) == 5 and provider.skipped == ["F", "G"] and len(t.calls) == 5
    assert obs[0].price_type == "EOD_CLOSE" and obs[0].adjustment_policy == "UNADJUSTED"
    assert obs[0].market_date == date(2026, 11, 2) and obs[0].market_timestamp is None
    again = provider.latest_prices(["A", "B"], date(2026, 11, 3))
    assert [o.price for o in again] == [Decimal(20), Decimal(21)] and len(t.calls) == 5


@pytest.mark.parametrize("body", [
    _massive("SYNA", 10, adjusted=True), _massive("SYNM", 10), _massive("SYNA", 0),
    _massive("SYNA", 10, ms_stamp=0), {"ticker": "SYNA", "adjusted": False, "results": [{}, {}]},
])
def test_massive_rejects_adjusted_misattributed_or_malformed(body: Any) -> None:
    t = FakeTransport({"/prev": (200, body)})
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        mp.MassiveEODMarketDataProvider(CRED, t, _allow, _clock).latest_prices(["SYNA"], date(2026, 11, 3))


# ---- BOT --------------------------------------------------------------------------------------

def test_bot_reference_rate_both_directions_and_holiday_gap() -> None:
    t = FakeTransport({"DAILY_AVG_EXG_RATE": (200, _bot([("2026-10-30", "33.2000"), ("2026-11-02", ""), ("2026-11-03", "33.1000")]))})
    obs = mp.BOTReferenceFXProvider(CRED, t, _allow, _clock).reference_rates(date(2026, 11, 3))
    assert [(o.from_currency, o.to_currency, o.market_date.isoformat()) for o in obs][:2] == [
        ("USD", "THB", "2026-10-30"), ("THB", "USD", "2026-10-30")]
    assert len(obs) == 4 and all(o.kind == "REFERENCE_FX" for o in obs)
    assert obs[2].rate == Decimal("33.1000") and abs(obs[3].rate * obs[2].rate - 1) < Decimal("1e-9")


@pytest.mark.parametrize("body", [{"result": {}}, _bot([("2026-11-03", "abc")]), _bot([("2026-11-09", "33")]),
                                  _bot([("2026-11-03", "33"), ("2026-11-03", "33")]), _bot([("03/11/2026", "33")])])
def test_bot_rejects_malformed_or_out_of_range(body: Any) -> None:
    t = FakeTransport({"DAILY_AVG_EXG_RATE": (200, body)})
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        mp.BOTReferenceFXProvider(CRED, t, _allow, _clock).reference_rates(date(2026, 11, 3))


def test_bot_ignores_other_currencies_and_requires_usd_rows() -> None:
    mixed = {"result": {"data": {"data_header": {"report_uoq_name_eng": BOT_UNIT}, "data_detail": [
        {"period": "2026-11-03", "currency_id": "EUR", "mid_rate": "39.5"},
        {"period": "2026-11-03", "currency_id": "USD", "mid_rate": "33.10"}]}}}
    obs = mp.BOTReferenceFXProvider(CRED, FakeTransport({"DAILY_AVG_EXG_RATE": (200, mixed)}),
                                    _allow, _clock).reference_rates(date(2026, 11, 3))
    assert len(obs) == 2 and obs[0].rate == Decimal("33.10")
    only_eur = {"result": {"data": {"data_header": {"report_uoq_name_eng": BOT_UNIT}, "data_detail": [
        {"period": "2026-11-03", "currency_id": "EUR", "mid_rate": "39.5"}]}}}
    with pytest.raises(DataContractError, match="no USD rows"):
        mp.BOTReferenceFXProvider(CRED, FakeTransport({"DAILY_AVG_EXG_RATE": (200, only_eur)}),
                                  _allow, _clock).reference_rates(date(2026, 11, 3))


def test_bot_refuses_an_unexpected_rate_direction() -> None:
    body = _bot([("2026-11-03", "33.10")], unit="(Unit: USD / 1 Unit of Baht)")
    with pytest.raises(DataContractError, match="rate direction"):
        mp.BOTReferenceFXProvider(CRED, FakeTransport({"DAILY_AVG_EXG_RATE": (200, body)}),
                                  _allow, _clock).reference_rates(date(2026, 11, 3))


def test_bot_rate_limit_refuses_before_the_request() -> None:
    t = FakeTransport({"DAILY_AVG_EXG_RATE": (200, _bot([("2026-11-03", "33.10")]))})
    with pytest.raises(DataContractError, match="PROVIDER_RATE_LIMITED"):
        mp.BOTReferenceFXProvider(CRED, t, lambda: False, _clock).reference_rates(date(2026, 11, 3))
    assert t.calls == []


def _holidays(rows: List[Tuple[str, str]]) -> Dict[str, Any]:
    return {"result": {"api": "API_V2.FIHolidays", "data": [
        {"Date": d, "HolidayDescription": name, "HolidayWeekDay": "Thursday"} for d, name in rows]}}


def test_bot_holidays_are_sorted_deduplicated_and_year_checked() -> None:
    t = FakeTransport({"financial-institutions-holidays": (200, _holidays([
        ("2026-05-04", "Coronation Day"), ("2026-01-01", "New Year's Day"),
        ("2026-01-01", "New Year's Day")]))})
    out = mp.BOTFinancialHolidaysProvider(CRED, t, _allow, _clock).holidays(2026)
    assert [h.date.isoformat() for h in out] == ["2026-01-01", "2026-05-04"]
    assert out[0].name == "New Year's Day" and out[0].provider_id == "BOT_HOLIDAYS"


@pytest.mark.parametrize("body", [
    {"result": {"data": []}},
    _holidays([("2027-01-01", "Wrong year")]),
    _holidays([("01/01/2026", "Bad date")]),
    {"result": {"data": [{"Date": "2026-01-01"}]}},
])
def test_bot_holidays_reject_malformed_payloads(body: Any) -> None:
    t = FakeTransport({"financial-institutions-holidays": (200, body)})
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        mp.BOTFinancialHolidaysProvider(CRED, t, _allow, _clock).holidays(2026)


# ---- Alpaca Historical SIP ------------------------------------------------------------------

def _sip_bar(symbol: str, opened: str, o: float = 100.0, h: float = 101.0,
             l: float = 99.0, c: float = 100.5) -> Dict[str, Any]:
    return {"t": opened, "o": o, "h": h, "l": l, "c": c, "v": 10000, "n": 50, "vw": c}


def _sip_resp(symbol: str, bars: List[Any], next_token: Optional[str] = None) -> Dict[str, Any]:
    return {"bars": {symbol: bars}, "next_page_token": next_token}


# NOW = datetime(2026, 11, 3, 21, 30, utc) → limit = NOW - 15min - 2min = 21:13 utc
_SIP_LIMIT = datetime(2026, 11, 3, 21, 13, tzinfo=timezone.utc)
# A 1-min bar opened at 21:10 UTC → closed 21:11 UTC < 21:13 → eligible
_VALID_1MIN_OPEN = "2026-11-03T21:10:00Z"
# A daily bar: opened 2026-11-03 NY (11:00 UTC); closes at 16:00 NY = 21:00 UTC < 21:13 → eligible
_VALID_DAY_OPEN = "2026-11-03T11:00:00-05:00"


def test_alpaca_historical_intraday_bar_selected_first() -> None:
    bar = _sip_bar("SYNA", _VALID_1MIN_OPEN)
    t = FakeTransport({"stocks/bars": (200, _sip_resp("SYNA", [bar]))})
    provider = mp.AlpacaHistoricalSIPProvider(CRED, t, _allow, _clock)
    obs = provider.latest_prices(["SYNA"], date(2026, 11, 3))
    assert len(obs) == 1
    assert obs[0].price_type == "INTRADAY_BAR_CLOSE"
    assert obs[0].security_id == "SYNA"
    assert obs[0].price == Decimal("100.5")
    assert obs[0].coverage == "CONSOLIDATED"


def test_alpaca_historical_falls_back_to_daily_when_no_intraday() -> None:
    # 1Min returns empty; 1Day returns a bar
    day_bar = _sip_bar("SYNA", _VALID_DAY_OPEN)
    t = FakeTransport({"stocks/bars": (200, {"bars": {"SYNA": []}, "next_page_token": None})})
    # Second call (1Day) returns valid
    call_count = [0]
    def transport(req: mp.HttpRequest) -> Tuple[int, bytes]:
        mp.assert_allowed(req)
        call_count[0] += 1
        if "1Min" in req.url:
            return 200, json.dumps({"bars": {"SYNA": []}, "next_page_token": None}).encode()
        return 200, json.dumps({"bars": {"SYNA": [day_bar]}, "next_page_token": None}).encode()
    provider = mp.AlpacaHistoricalSIPProvider(CRED, transport, _allow, _clock)
    obs = provider.latest_prices(["SYNA"], date(2026, 11, 3))
    assert len(obs) == 1
    assert obs[0].price_type == "EOD_CLOSE"


def test_alpaca_historical_rejects_future_bar() -> None:
    # Bar opened after limit: 21:20 UTC > 21:13 limit
    future_bar = _sip_bar("SYNA", "2026-11-03T21:20:00Z")
    t = FakeTransport({"stocks/bars": (200, _sip_resp("SYNA", [future_bar]))})
    provider = mp.AlpacaHistoricalSIPProvider(CRED, t, _allow, _clock)
    with pytest.raises(DataContractError, match="bar timestamp"):
        provider.latest_prices(["SYNA"], date(2026, 11, 3))


def test_alpaca_historical_rejects_bad_bar_range() -> None:
    # high < low is impossible
    bad_bar = _sip_bar("SYNA", _VALID_1MIN_OPEN, o=100.0, h=98.0, l=99.0, c=100.0)
    t = FakeTransport({"stocks/bars": (200, _sip_resp("SYNA", [bad_bar]))})
    provider = mp.AlpacaHistoricalSIPProvider(CRED, t, _allow, _clock)
    with pytest.raises(DataContractError, match="bar range"):
        provider.latest_prices(["SYNA"], date(2026, 11, 3))


def test_alpaca_historical_rejects_duplicate_bar_timestamp() -> None:
    bar = _sip_bar("SYNA", _VALID_1MIN_OPEN)
    t = FakeTransport({"stocks/bars": (200, _sip_resp("SYNA", [bar, bar]))})
    provider = mp.AlpacaHistoricalSIPProvider(CRED, t, _allow, _clock)
    with pytest.raises(DataContractError, match="bar timestamp"):
        provider.latest_prices(["SYNA"], date(2026, 11, 3))


def test_alpaca_historical_rejects_unrequested_symbol() -> None:
    t = FakeTransport({"stocks/bars": (200, {"bars": {"EVIL": [_sip_bar("EVIL", _VALID_1MIN_OPEN)]},
                                            "next_page_token": None})})
    provider = mp.AlpacaHistoricalSIPProvider(CRED, t, _allow, _clock)
    with pytest.raises(DataContractError, match="unrequested symbol"):
        provider.latest_prices(["SYNA"], date(2026, 11, 3))


def test_alpaca_historical_rate_limited_stops_immediately() -> None:
    t = FakeTransport({"stocks/bars": (429, b"")})
    provider = mp.AlpacaHistoricalSIPProvider(CRED, t, _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_RATE_LIMITED"):
        provider.latest_prices(["SYNA"], date(2026, 11, 3))


def test_alpaca_historical_credential_not_in_url() -> None:
    bar = _sip_bar("SYNA", _VALID_1MIN_OPEN)
    t = FakeTransport({"stocks/bars": (200, _sip_resp("SYNA", [bar]))})
    provider = mp.AlpacaHistoricalSIPProvider(CRED, t, _allow, _clock)
    provider.latest_prices(["SYNA"], date(2026, 11, 3))
    assert all(CRED[0] not in c.url and CRED[1] not in c.url for c in t.calls)


# ---- MarketDataApp Free (documented contract: s / symbol[] / last[] / updated[]) -------------

_MARKETDATA_OK = {"s": "ok", "symbol": ["SYNA", "SYNB"], "last": ["100.25", "50.10"],
                  "updated": [1769210435, 1769210436]}
_MARKETDATA_NO_DATA = {"s": "no_data", "symbol": [], "last": [], "updated": []}
_MARKETDATA_ERROR = {"s": "error", "message": "invalid symbols"}


def _marketdata_body(doc: Dict[str, Any]) -> bytes:
    return json.dumps(doc).encode("utf-8")


def test_marketdata_app_raises_contract_unverified() -> None:
    """Adapter must refuse live requests until MARKETDATA_CONTRACT_VERIFIED is set True."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", False)
    try:
        t = FakeTransport()
        provider = mp.MarketDataAppFreeProvider(CRED, t, _allow, _clock)
        with pytest.raises(DataContractError, match="PROVIDER_CONTRACT_UNVERIFIED"):
            provider.latest_prices(["SYNA"], date(2026, 11, 3))
        assert len(t.calls) == 0  # no request sent
    finally:
        monkeypatch.undo()


def test_marketdata_app_endpoint_allowlist_rejects_wrong_host() -> None:
    """MARKETDATA_APP_FREE endpoint must only allow api.marketdata.app."""
    with pytest.raises(DataContractError, match="ENDPOINT_NOT_ALLOWED"):
        mp.assert_allowed(mp.HttpRequest("MARKETDATA_APP_FREE",
                                         "https://evil.example/v1/stocks/quotes/?symbols=SYNA", {}))


def test_marketdata_app_parses_index_aligned_arrays(monkeypatch: pytest.MonkeyPatch) -> None:
    """Index-aligned symbol/last/updated arrays; updated is Unix seconds -> New York session date."""
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", True)
    t = FakeTransport({"quotes": (200, _MARKETDATA_OK)})
    provider = mp.MarketDataAppFreeProvider(CRED, t, _allow, _clock)
    obs = provider.latest_prices(["SYNA", "SYNB"], date(2026, 11, 3))
    assert len(obs) == 2
    assert {o.security_id: o.price for o in obs} == {"SYNA": Decimal("100.25"), "SYNB": Decimal("50.10")}
    assert all(o.price_type == "HISTORICAL_DELAYED_LAST" for o in obs)
    first = next(o for o in obs if o.security_id == "SYNA")
    assert first.market_timestamp is not None


def test_marketdata_app_bearer_token_never_in_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Token travels only in Authorization: Bearer; never as a URL query parameter."""
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", True)
    t = FakeTransport({"quotes": (200, _MARKETDATA_OK)})
    provider = mp.MarketDataAppFreeProvider(CRED, t, _allow, _clock)
    provider.latest_prices(["SYNA", "SYNB"], date(2026, 11, 3))
    assert len(t.calls) == 1
    assert "token" not in t.calls[0].url
    # The token lives in the credential's secret half (SETUP-MARKET-DATA writes it there).
    assert t.calls[0].headers.get("Authorization") == f"Bearer {CRED[1]}"


def test_marketdata_app_bearer_uses_whichever_credential_half_carries_the_token(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", True)
    for credential, expected in ((("SYNKEYID", "SYNTOKEN"), "SYNTOKEN"), (("SYNTOKEN", ""), "SYNTOKEN")):
        t = FakeTransport({"quotes": (200, _MARKETDATA_OK)})
        mp.MarketDataAppFreeProvider(credential, t, _allow, _clock).latest_prices(["SYNA", "SYNB"],
                                                                                 date(2026, 11, 3))
        assert t.calls[0].headers.get("Authorization") == f"Bearer {expected}"


def test_marketdata_app_handles_no_data_and_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """no_data is an empty result; error status is a contract failure, never a price."""
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", True)
    provider = mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, _MARKETDATA_NO_DATA)}),
                                            _allow, _clock)
    assert provider.latest_prices(["SYNA"], date(2026, 11, 3)) == []
    bad = mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, _MARKETDATA_ERROR)}),
                                       _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        bad.latest_prices(["SYNA"], date(2026, 11, 3))


def test_marketdata_app_rejects_bad_shapes_and_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mismatched arrays, unknown symbols, duplicates, nonpositive/future prices are rejected."""
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", True)
    base = dict(_MARKETDATA_OK)

    mismatched = dict(base, symbol=["SYNA", "SYNB"], last=["100.25"])
    provider = mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, mismatched)}),
                                            _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        provider.latest_prices(["SYNA", "SYNB"], date(2026, 11, 3))

    unknown = dict(base, symbol=["SYNA", "ZZZ"], last=["100.25", "50.10"],
                   updated=[1769210435, 1769210436])
    provider = mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, unknown)}),
                                            _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        provider.latest_prices(["SYNA"], date(2026, 11, 3))

    dup = dict(base, symbol=["SYNA", "SYNA"], last=["100.25", "100.25"],
               updated=[1769210435, 1769210436])
    provider = mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, dup)}),
                                            _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        provider.latest_prices(["SYNA"], date(2026, 11, 3))

    nonpositive = dict(base, last=["0", "50.10"])
    provider = mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, nonpositive)}),
                                            _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        provider.latest_prices(["SYNA", "SYNB"], date(2026, 11, 3))


def test_marketdata_app_accepts_200_and_203(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 200 and 203 are both successful provider responses."""
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", True)
    for status in (200, 203):
        t = FakeTransport({"quotes": (status, _MARKETDATA_OK)})
        provider = mp.MarketDataAppFreeProvider(CRED, t, _allow, _clock)
        assert len(provider.latest_prices(["SYNA", "SYNB"], date(2026, 11, 3))) == 2


def test_marketdata_app_credit_window_is_new_york_0930() -> None:
    """Credit window opens at 09:30 America/New_York and follows EST/EDT via the zoneinfo clock."""
    before = datetime(2026, 6, 1, 13, 29, tzinfo=timezone.utc)  # 09:29 EDT
    after = datetime(2026, 6, 1, 13, 30, tzinfo=timezone.utc)   # 09:30 EDT
    assert mp.MarketDataAppFreeProvider.credit_window(before) == date(2026, 5, 31)
    assert mp.MarketDataAppFreeProvider.credit_window(after) == date(2026, 6, 1)
    winter = datetime(2026, 12, 1, 14, 29, tzinfo=timezone.utc)  # 09:29 EST
    assert mp.MarketDataAppFreeProvider.credit_window(winter) == date(2026, 11, 30)


def test_marketdata_app_credit_persists_across_restart(tmp_path: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    """Consumed credits survive a simulated restart through an atomic ledger file."""
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", True)
    ledger = tmp_path / "credits.json"
    provider = mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, _MARKETDATA_OK)}),
                                            _allow, _clock, ledger_path=ledger)
    provider.latest_prices(["SYNA", "SYNB"], date(2026, 11, 3))
    assert provider.credits_used() == 2
    # Simulated restart: new provider instance reads the same ledger.
    provider2 = mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, _MARKETDATA_OK)}),
                                             _allow, _clock, ledger_path=ledger)
    assert provider2.credits_used() == 2


def test_marketdata_app_concurrent_refreshes_do_not_overspend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two concurrent refreshes against a near-empty budget cannot both succeed."""
    import threading
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", True)
    provider = mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, _MARKETDATA_OK)}),
                                            _allow, _clock)
    provider._reserve(98)
    results: List[BaseException | None] = [None, None]

    def hit(slot: int) -> None:
        try:
            provider._reserve(2)
        except BaseException as exc:
            results[slot] = exc

    threads = [threading.Thread(target=hit, args=(i,)) for i in (0, 1)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    failures = [r for r in results if isinstance(r, DataContractError)]
    assert len(failures) == 1  # exactly one of the two loses the race


# ---- Frankfurter ECB FX (documented V2 contract: date / base / quote / rate) ---------------

def _frankfurter_v2(rate: str = "34.12", date_str: str = "2026-11-03") -> Dict[str, Any]:
    return {"date": date_str, "base": "USD", "quote": "THB", "rate": rate}


def test_frankfurter_raises_contract_unverified() -> None:
    """Adapter must refuse live requests until FRANKFURTER_CONTRACT_VERIFIED is set True."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(mp, "FRANKFURTER_CONTRACT_VERIFIED", False)
    try:
        t = FakeTransport()
        provider = mp.FrankfurterECBFxProvider(t, _allow, _clock)
        with pytest.raises(DataContractError, match="PROVIDER_CONTRACT_UNVERIFIED"):
            provider.reference_rate()
        assert len(t.calls) == 0
    finally:
        monkeypatch.undo()


def test_frankfurter_endpoint_allowlist_correct_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mp, "FRANKFURTER_CONTRACT_VERIFIED", True)
    url = mp.build_url("FRANKFURTER_ECB_FX", "/v2/rate/USD/THB", {"providers": "ECB"})
    assert "api.frankfurter.dev" in url
    mp.assert_allowed(mp.HttpRequest("FRANKFURTER_ECB_FX", url, {}))


def test_frankfurter_parses_v2_scalar_rate_both_directions(monkeypatch: pytest.MonkeyPatch) -> None:
    """V2 scalar {date, base, quote, rate}; reciprocal consistent; source ECB preserved."""
    monkeypatch.setattr(mp, "FRANKFURTER_CONTRACT_VERIFIED", True)
    t = FakeTransport({"rate/USD/THB": (200, _frankfurter_v2("34.12"))})
    provider = mp.FrankfurterECBFxProvider(t, _allow, _clock)
    obs = provider.reference_rate("USD", "THB")
    assert len(obs) == 2
    fwd = next(o for o in obs if o.from_currency == "USD")
    back = next(o for o in obs if o.from_currency == "THB")
    assert fwd.rate == Decimal("34.12")
    assert fwd.kind == "REFERENCE_FX"
    assert abs(back.rate * fwd.rate - 1) < Decimal("1e-9")
    assert fwd.market_date.isoformat() == "2026-11-03"


def test_frankfurter_rejects_wrong_pair_and_future_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mp, "FRANKFURTER_CONTRACT_VERIFIED", True)
    wrong = mp.FrankfurterECBFxProvider(FakeTransport({"rate/USD/THB": (200, _frankfurter_v2("34.12", "2026-11-05"))}),
                                        _allow, _clock)
    with pytest.raises(DataContractError, match="future date"):
        wrong.reference_rate("USD", "THB")
    mismatch = mp.FrankfurterECBFxProvider(FakeTransport({"rate/USD/THB": (200, {"date": "2026-11-03",
                                                                           "base": "EUR", "quote": "USD",
                                                                           "rate": "1.1"})}),
                                           _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        mismatch.reference_rate("USD", "THB")


def test_frankfurter_requests_historical_date_and_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """reference_rates(end) asks for ``end`` and keeps only rates within [end-lookback, end]."""
    monkeypatch.setattr(mp, "FRANKFURTER_CONTRACT_VERIFIED", True)
    captured: List[str] = []

    def transport(request: mp.HttpRequest) -> Tuple[int, bytes]:
        captured.append(request.url)
        return 200, _marketdata_body(_frankfurter_v2("34.12", "2026-11-03"))

    provider = mp.FrankfurterECBFxProvider(transport, _allow, _clock)
    obs = provider.reference_rates(date(2026, 11, 3), lookback_days=7)
    assert any("date=2026-11-03" in u for u in captured)
    assert len(obs) == 2 and obs[0].market_date == date(2026, 11, 3)


def test_frankfurter_rejects_unknown_rates_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    """The old nested ``rates.ECB`` envelope is not accepted by V2."""
    monkeypatch.setattr(mp, "FRANKFURTER_CONTRACT_VERIFIED", True)
    bad = {"date": "2026-11-03", "base": "USD", "quote": "THB", "rates": {"ECB": 34.12}}
    provider = mp.FrankfurterECBFxProvider(FakeTransport({"rate/USD/THB": (200, bad)}), _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        provider.reference_rate()


def test_frankfurter_no_credential_in_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Frankfurter is keyless; no secret must appear in any outbound URL."""
    monkeypatch.setattr(mp, "FRANKFURTER_CONTRACT_VERIFIED", True)
    t = FakeTransport({"rate/USD/THB": (200, _frankfurter_v2())})
    provider = mp.FrankfurterECBFxProvider(t, _allow, _clock)
    provider.reference_rate()
    assert len(t.calls) == 1
    assert "token" not in t.calls[0].url.lower()
    assert t.calls[0].headers == {}


def test_frankfurter_is_keyless_and_can_be_ready_without_credential(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(ma.REGISTRY["FRANKFURTER_ECB_FX"], "contract_verified", True)
    _odr4(root, scope=[_entry("FRANKFURTER_ECB_FX")])
    status = {p["provider_id"]: p for p in ma.provider_statuses(Store({}))[1]}["FRANKFURTER_ECB_FX"]
    assert status["status"] == "READY"
    assert status["capabilities"]["credentials_configured"] == "ESTABLISHED"


def test_provider_factory_builds_new_adapted_providers() -> None:
    service = ms.MarketService(Store(), FakeTransport())
    ready = [{"provider_id": pid, "cache_permitted": False} for pid in
             ("ALPACA_BASIC", "ALPACA_HISTORICAL", "MARKETDATA_APP_FREE", "FRANKFURTER_ECB_FX")]
    built = ms._providers(service, ready)
    assert type(built["ALPACA_HISTORICAL"]).__name__ == "AlpacaHistoricalSIPProvider"
    assert type(built["MARKETDATA_APP_FREE"]).__name__ == "MarketDataAppFreeProvider"
    assert type(built["FRANKFURTER_ECB_FX"]).__name__ == "FrankfurterECBFxProvider"


# ---- ODR-004 authority ------------------------------------------------------------------------


def _odr1(root: Path, status: str = "RATIFIED") -> None:
    record = root / po.AUTHORIZATION_RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"capability": po.AUTHORIZED_CAPABILITY, "status": status, "ratified_by": "OWNER",
                                  "ratified_on": "2026-11-02", "scope_schemas": [po.SCHEMA_V1_2, CAPACITY_SCHEMA]}),
                      encoding="utf-8")


def _entry(pid: str, **changes: Any) -> Dict[str, Any]:
    return {"provider_id": pid, "entitlement_verified": True, "display_permitted": True, "calculation_permitted": True,
            "derived_value_permitted": True, "cache_permitted": False, "evidence": "synthetic test", **changes}


def _odr4(root: Path, status: str = "RATIFIED", scope: Optional[List[Any]] = None, **changes: Any) -> None:
    doc = {"decision_id": ma.DECISION_ID, "capability": ma.CAPABILITY, "status": status, "ratified_by": "OWNER",
           "ratified_on": "2026-11-03", "requires": list(ma.REQUIRES),
           "scope_providers": [] if scope is None else scope, **changes}
    record = root / ma.RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(ma, "_repo_root", lambda: tmp_path)
    monkeypatch.setitem(ma.REGISTRY["BOT_REFERENCE_FX"], "contract_verified", True)
    _odr1(tmp_path)
    return tmp_path


def _status(store: Optional[Store] = None) -> Dict[str, str]:
    return {p["provider_id"]: p["status"] for p in ma.provider_statuses(store or Store())[1]}


@pytest.mark.parametrize("status, changes, state", [
    ("PROPOSED_NOT_RATIFIED", {}, "PROPOSED_NOT_RATIFIED"), ("REVOKED", {}, "REVOKED"),
    ("RATIFIED", {"decision_id": "ODR_OTHER"}, "RECORD_INVALID"),
    ("RATIFIED", {"capability": "OWNER_PRIVATE_OBSERVATION_AUTHORIZED"}, "RECORD_CAPABILITY_MISMATCH"),
    ("RATIFIED", {"ratified_on": "soon"}, "RECORD_INVALID"), ("RATIFIED", {"ratified_by": "AGENT"}, "RECORD_INVALID"),
    ("RATIFIED", {"requires": []}, "DEPENDENCY_NOT_RATIFIED"),
    ("RATIFIED", {"scope_providers": "ALPACA_BASIC"}, "RECORD_INVALID"),
])
def test_odr4_states_close_every_provider(root: Path, status: str, changes: Dict[str, Any], state: str) -> None:
    _odr4(root, status, [_entry("ALPACA_BASIC")], **changes)
    assert ma.record_state()[0] == state
    assert set(_status().values()) == {"GOVERNANCE_REQUIRED", "NOT_CONFIGURED"}


def test_odr4_dependency_and_scope_gates(root: Path) -> None:
    _odr4(root, scope=[_entry("ALPACA_BASIC")])
    _odr1(root, "REVOKED")
    assert ma.record_state()[0] == "DEPENDENCY_NOT_RATIFIED"
    _odr1(root)
    _odr4(root)
    assert _status() == {"ALPACA_BASIC": "GOVERNANCE_REQUIRED", "MASSIVE_BASIC": "GOVERNANCE_REQUIRED",
                         "BOT_REFERENCE_FX": "GOVERNANCE_REQUIRED", "BOT_HOLIDAYS": "GOVERNANCE_REQUIRED",
                         "ALPACA_HISTORICAL": "GOVERNANCE_REQUIRED",
                         "MARKETDATA_APP_FREE": "GOVERNANCE_REQUIRED",
                         "FRANKFURTER_ECB_FX": "GOVERNANCE_REQUIRED",
                         "WEBULL_TH_OPENAPI": "NOT_CONFIGURED"}
    _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("MASSIVE_BASIC", entitlement_verified=None),
                       _entry("BOT_REFERENCE_FX", display_permitted=False), _entry("WEBULL_TH_OPENAPI")])
    assert _status() == {"ALPACA_BASIC": "READY", "MASSIVE_BASIC": "ENTITLEMENT_REQUIRED",
                         "BOT_REFERENCE_FX": "DISPLAY_RIGHTS_UNVERIFIED",
                         "BOT_HOLIDAYS": "GOVERNANCE_REQUIRED",
                         "ALPACA_HISTORICAL": "GOVERNANCE_REQUIRED",
                         "MARKETDATA_APP_FREE": "GOVERNANCE_REQUIRED",
                         "FRANKFURTER_ECB_FX": "GOVERNANCE_REQUIRED",
                         "WEBULL_TH_OPENAPI": "NOT_CONFIGURED"}
    assert _status(Store({}))["ALPACA_BASIC"] == "CREDENTIALS_REQUIRED"
    _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("ALPACA_BASIC")])
    assert _status()["ALPACA_BASIC"] == "GOVERNANCE_REQUIRED"


@pytest.mark.parametrize("changes", [{"calculation_permitted": None}, {"derived_value_permitted": False},
                                     {"derived_value_permitted": "yes"}])
def test_calculation_and_derived_value_rights_are_required(root: Path, changes: Dict[str, Any]) -> None:
    _odr4(root, scope=[_entry("MASSIVE_BASIC", **changes)])
    assert _status()["MASSIVE_BASIC"] == "DERIVED_USE_UNVERIFIED"


def test_unverified_bot_contract_is_never_ready(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(ma.REGISTRY["BOT_REFERENCE_FX"], "contract_verified", False)
    _odr4(root, scope=[_entry("BOT_REFERENCE_FX")])
    status = {p["provider_id"]: p for p in ma.provider_statuses(Store())[1]}["BOT_REFERENCE_FX"]
    assert status["status"] == "CONTRACT_UNVERIFIED"
    assert status["capabilities"]["real_response_verified"] == "NOT_OBSERVED"
    assert ma.REGISTRY["MASSIVE_BASIC"]["known_restriction"] == "TERMS_MAY_RESTRICT_DERIVED_WORKS_INCLUDING_NAV"
    # The wire contract is verified from a live payload; the ODR scope entry still keeps the feed
    # ungoverned, so contract verification alone never makes it READY.
    assert mp.BOT_SPEC_VERIFIED is True and mp.BOT_LIVE_RESPONSE_VERIFIED is True


def test_capabilities_default_to_unknown_and_never_claim_live_verification(root: Path) -> None:
    _odr4(root, scope=[{"provider_id": "ALPACA_BASIC"}])
    status = {p["provider_id"]: p for p in ma.provider_statuses(Store())[1]}["ALPACA_BASIC"]
    assert status["status"] == "ENTITLEMENT_REQUIRED" and status["cache_permitted"] is False
    assert {status["capabilities"][k] for k in ma.ATTESTATIONS} == {"UNKNOWN"}
    _odr4(root, scope=[_entry("ALPACA_BASIC")])
    ready = {p["provider_id"]: p for p in ma.provider_statuses(Store())[1]}["ALPACA_BASIC"]
    assert ready["status"] == "READY" and ready["detail"] == "ATTESTED_NOT_LIVE_VERIFIED"
    assert ready["capabilities"]["cache_permitted"] == ("ATTESTED" if ready["cache_permitted"] else "DENIED")
    assert ready["capabilities"]["authentication_verified"] == ready["capabilities"]["real_response_verified"] == "NOT_OBSERVED"


def test_repository_odr4_scope_attests_only_documented_rights() -> None:
    """The attested set is explicit: Alpaca keeps cache/retention denied; nothing is inferred."""
    doc = json.loads((Path(".") / ma.RECORD).read_text(encoding="utf-8"))
    assert doc["decision_id"] == ma.DECISION_ID
    entries = {e["provider_id"]: e for e in doc["scope_providers"]}
    assert set(entries) == {"ALPACA_BASIC", "ALPACA_HISTORICAL", "MARKETDATA_APP_FREE",
                            "FRANKFURTER_ECB_FX", "MASSIVE_BASIC", "BOT_REFERENCE_FX"}
    for provider_id in ("ALPACA_BASIC", "ALPACA_HISTORICAL"):
        assert entries[provider_id]["entitlement_verified"] is True
        assert entries[provider_id]["cache_permitted"] is None
        assert entries[provider_id]["cache_rights"]["persistent_historical_price"] == "PENDING_RIGHTS_VERIFICATION"
        assert entries[provider_id]["retention_policy_verified"] is None
    for provider_id in ("MARKETDATA_APP_FREE", "FRANKFURTER_ECB_FX"):
        assert entries[provider_id]["cache_permitted"] is True
    assert entries["FRANKFURTER_ECB_FX"]["retention_policy_verified"] is True
    assert doc["attestation_record"]["attested_on"] == "2026-11-03"
    assert {"TRADING_AUTHORIZED", "BROKER_ACCOUNT_CONNECTIVITY", "MARKET_DATA_SUBSCRIPTION"} <= set(doc["independent_of"])
    statuses = {p["provider_id"]: p["status"] for p in ma.provider_statuses(Store({}))[1]}
    assert statuses["MASSIVE_BASIC"] in ("CREDENTIALS_REQUIRED", "CONTRACT_UNVERIFIED")
    # The wire contract is verified (live 2026-11-04), so the credential gate now comes first; with no
    # stored credential the feed still cannot be used for a portfolio value.
    assert statuses["BOT_REFERENCE_FX"] == "CREDENTIALS_REQUIRED"
    # Amendment history is append-only: 003 recorded the scope, 004 the private-storage right.
    assert "ODR_UPI_MARKET_DATA_004_AMENDMENT_003_MASSIVE_BOT" in doc["amendments"]
    assert doc["amendments"][-1] == "ODR_UPI_MARKET_DATA_004_AMENDMENT_004_PRIVATE_STORAGE"
    massive = entries["MASSIVE_BASIC"]
    assert massive["cache_permitted"] is True and massive["retention_policy_verified"] is True
    assert massive["retention_policy"]["max_retention_after_terms_termination_days"] == 30
    assert massive["cache_rights"]["redistribution"] == "DENIED"
    assert massive["retention_terms"]["terms_revision_dated"] == "2026-11-03"
    # A retention decision for one provider never widens another provider's rights.
    assert entries["ALPACA_BASIC"]["cache_permitted"] is None


# ---- partial valuation ------------------------------------------------------------------------

def _owner_doc() -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    return doc


def _install(root: Path) -> Dict[str, bytes]:
    private = root / "data" / "private"
    private.mkdir(parents=True, exist_ok=True)
    capacity = json.loads(CAPACITY.read_text(encoding="utf-8"))
    capacity["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    files = {"snapshot.json": json.dumps(_owner_doc()).encode("utf-8"), "capacity.json": json.dumps(capacity).encode("utf-8")}
    for name, data in files.items():
        (private / name).write_bytes(data)
    return files


def test_partial_valuation_counts_but_never_values_missing_components(root: Path) -> None:
    obs = mp.AlpacaIEXMarketDataProvider(CRED, FakeTransport({"trades/latest": (200, _alpaca({"SYNIDX": "50.25"}))}),
                                         _allow, _clock).latest_prices(["SYNIDX"], date(2026, 11, 3))
    fx = mp.BOTReferenceFXProvider(CRED, FakeTransport({"DAILY_AVG_EXG_RATE": (200, _bot([("2026-11-03", "33.10")]))}),
                                   _allow, _clock).reference_rates(date(2026, 11, 3))
    doc = _owner_doc()
    before = json.dumps(doc, sort_keys=True)
    derived, meta = partial_snapshot(doc, {o.security_id: o for o in obs}, fx, "MKT_TEST")
    assert json.dumps(doc, sort_keys=True) == before
    assert meta["valuation_status"] == "PARTIAL_INDICATIVE_VALUATION"
    assert meta["coverage"] == {"held_with_quantity": 2, "priced": 1, "misaligned_date": 0, "unpriced": 1,
                                "value_only": 1, "total_only_accounts": 1}
    assert "REFERENCE_FX_NOT_EXECUTABLE" in meta["flags"] and "IEX_ONLY_NOT_CONSOLIDATED" in meta["flags"]
    assert derived is not None
    original = {(a["account_ref"], p["security_id"]): p.get("quantity") for a in doc["accounts"] for p in a.get("positions") or []}
    for account in derived["accounts"]:
        for p in account["positions"]:
            assert p["quantity"] == original[(account["account_ref"], p["security_id"])]
            assert "observed_market_value" not in p
        assert "reported_total" not in account
    book = po.build_book(po.parse_snapshot(derived))
    assert set(book.consolidated) == {"THB", "USD"}
    none, unavailable = partial_snapshot(doc, {}, fx, "MKT_TEST")
    assert none is None and unavailable["valuation_status"] == "UNAVAILABLE"


# ---- refresh service and routes ---------------------------------------------------------------

def _service(transport: FakeTransport, store: Optional[Store] = None) -> ms.MarketService:
    return ms.MarketService(store or Store(), transport, _clock)


def _call(service: ms.MarketService, method: str, name: str, body: Any = None,
          headers: Optional[Dict[str, str]] = None) -> Tuple[int, Any]:
    data = b"" if body is None else json.dumps(body).encode("utf-8")
    hdrs = headers or {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN,
                       "Content-Type": "application/json"}
    status, out_headers, out = srv.respond(method, ms.PREFIX + name, hdrs, TOKEN, Path("unused.json"), PORT, data,
                                           pi.InputService(), False, None, service)
    assert out_headers["Cache-Control"] == "no-store"
    return status, json.loads(out) if out else None


ROUTES = {"trades/latest": (200, _alpaca({"SYNIDX": "50.25"})), "/ticker/SYNBOND/prev": (200, _massive("SYNBOND", 98.5)),
          "DAILY_AVG_EXG_RATE": (200, _bot([("2026-11-03", "33.10")]))}


@pytest.mark.parametrize("status, scope, http, code", [
    ("PROPOSED_NOT_RATIFIED", [_entry("ALPACA_BASIC")], 403, "MARKET_DATA_AUTHORIZATION_REQUIRED"),
    ("REVOKED", [_entry("ALPACA_BASIC")], 403, "MARKET_DATA_AUTHORIZATION_REQUIRED"),
    ("RATIFIED", [], 409, "NO_READY_PRICE_PROVIDER"),
    ("RATIFIED", [_entry("ALPACA_BASIC", display_permitted=None)], 409, "NO_READY_PRICE_PROVIDER"),
])
def test_refresh_without_authority_makes_no_request(root: Path, status: str, scope: List[Any], http: int, code: str) -> None:
    _install(root)
    _odr4(root, status, scope)
    transport = FakeTransport(ROUTES)
    assert _call(_service(transport), "POST", "refresh", {})[1]["status"] == code
    assert transport.calls == []


def test_refresh_values_through_ppds_and_preserves_inputs(root: Path) -> None:
    files = _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("MASSIVE_BASIC"), _entry("BOT_REFERENCE_FX")])
    transport = FakeTransport(ROUTES)
    service = _service(transport)
    http, out = _call(service, "POST", "refresh", {})
    assert http == 200, out
    assert out["status"] == "REFRESHED"
    assert out["valuation_status"] == "PARTIAL_INDICATIVE_VALUATION" and out["fx_status"] == "REFERENCE_FX_ON_MARKET_DATE"
    assert (out["requested_symbols_count"], out["priced_symbols_count"], out["stale_symbols_count"]) == (2, 1, 1)
    assert {"ALPACA_BASIC": "QUERIED", "MASSIVE_BASIC": "QUERIED", "BOT_REFERENCE_FX": "READY"}.items() <= out["provider_statuses"].items()
    assert all((root / "data" / "private" / n).read_bytes() == b for n, b in files.items())
    assert out["persisted"] is False and out["holdings_basis"] == "STATEMENT_BASELINE"
    market = root / "data" / "private" / "market"
    assert sorted(p.name for p in market.iterdir()) == [ms.ATTEMPT_FILE]
    attempt = (market / ms.ATTEMPT_FILE).read_text("utf-8")
    assert CRED[1] not in json.dumps(out) and CRED[1] not in attempt and "50.25" not in attempt
    view_status, view = _call(service, "GET", "view")
    assert view_status == 200 and view["data_mode"] == "OWNER_PRIVATE_READ_ONLY"
    status_http, status_doc = _call(service, "GET", "status")
    assert status_http == 200 and status_doc["last_success"]["valuation_status"] == "PARTIAL_INDICATIVE_VALUATION"
    assert {q["security_id"]: q["used"] for q in status_doc["last_success"]["quotes"]} == {"SYNIDX": True, "SYNBOND": False}
    assert status_doc["last_success"]["providers_used"] == ["ALPACA_BASIC", "BOT_REFERENCE_FX"]
    assert CRED[1] not in json.dumps(status_doc)
    assert service.eod_cache == {}


def test_holdings_rows_come_from_the_ppds_book(root: Path) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("BOT_REFERENCE_FX")])
    service = _service(FakeTransport(ROUTES))
    assert _call(service, "POST", "refresh", {})[0] == 200
    holdings = _call(service, "GET", "status")[1]["last_success"]["holdings"]
    assert holdings["weight_basis"] == "SHARE_OF_PRICED_SUBTOTAL_NOT_TOTAL_PORTFOLIO"
    (row,) = [r for r in holdings["rows"] if r["security_id"] == "SYNIDX"]
    assert (row["account_ref"], row["quantity"], row["price"], row["provider_id"]) == ("BROKER_D_MAIN", "12", "50.25", "ALPACA_BASIC")
    assert Decimal(row["market_value_local"]) == Decimal("603.00")
    assert Decimal(row["unrealized_pnl_local"]) == Decimal("603.00") - Decimal("1100.00")
    assert not any(r["security_id"] in ("SYNBOND", "SYNTHEME") for r in holdings["rows"])
    assert 0 < Decimal(row["weight_of_priced_subtotal"]) <= 1
    assert holdings["reporting_currency"] != row["price_currency"]
    assert Decimal(row["market_value_reporting"]) == (Decimal("603.00") * Decimal("33.10")).quantize(Decimal("0.01"))
    assert Decimal(row["weight_of_priced_subtotal"]) == (Decimal(row["market_value_reporting"]) / Decimal(holdings["priced_subtotal"])).quantize(Decimal("0.0001"))


def test_cache_permitted_generation_persists_and_revocation_discards_it(root: Path) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC", cache_permitted=True), _entry("BOT_REFERENCE_FX", cache_permitted=True)])
    service = _service(FakeTransport(ROUTES))
    assert _call(service, "POST", "refresh", {})[1]["persisted"] is True
    published = root / "data" / "private" / "market" / ms.PUBLISHED_FILE
    assert published.is_file() and "50.25" in published.read_text("utf-8")
    restarted = _service(FakeTransport())
    assert _call(restarted, "GET", "view")[0] == 200
    _odr4(root, scope=[_entry("ALPACA_BASIC", cache_permitted=False), _entry("BOT_REFERENCE_FX", cache_permitted=True)])
    assert _call(restarted, "GET", "view") == (404, {"status": "NO_REPORT"})
    assert not published.exists()


@pytest.mark.parametrize("revoke", ["odr", "provider"])
def test_revocation_discards_in_memory_generation(root: Path, revoke: str) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("BOT_REFERENCE_FX")])
    service = _service(FakeTransport(ROUTES))
    assert _call(service, "POST", "refresh", {})[0] == 200
    if revoke == "odr":
        _odr4(root, "REVOKED", [_entry("ALPACA_BASIC"), _entry("BOT_REFERENCE_FX")])
        assert _call(service, "GET", "view")[0] == 403
        _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("BOT_REFERENCE_FX")])
    else:
        _odr4(root, scope=[_entry("BOT_REFERENCE_FX")])
    assert _call(service, "GET", "view") == (404, {"status": "NO_REPORT"})
    assert service.memory_generation is None and _call(service, "GET", "status")[1]["last_success"] is None


def test_authorization_change_during_refresh_publishes_nothing(root: Path) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC", cache_permitted=True), _entry("BOT_REFERENCE_FX", cache_permitted=True)])
    inner = FakeTransport(ROUTES)

    def revoking(request: mp.HttpRequest) -> Tuple[int, bytes]:
        if "DAILY_AVG_EXG_RATE" in request.url:
            _odr4(root, scope=[_entry("BOT_REFERENCE_FX", cache_permitted=True)])
        return inner(request)
    http, out = _call(_service(revoking), "POST", "refresh", {})  # type: ignore[arg-type]
    assert (http, out["status"]) == (409, "AUTHORIZATION_CHANGED_DURING_REFRESH")
    assert not (root / "data" / "private" / "market" / ms.PUBLISHED_FILE).exists()


def test_publish_write_failure_keeps_previous_generation(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC", cache_permitted=True), _entry("BOT_REFERENCE_FX", cache_permitted=True)])
    service = _service(FakeTransport(ROUTES))
    assert _call(service, "POST", "refresh", {})[0] == 200
    published = root / "data" / "private" / "market" / ms.PUBLISHED_FILE
    before = published.read_bytes()
    original = pi._atomic_write

    def failing(path: Path, data: bytes) -> None:
        if path.name == ms.PUBLISHED_FILE:
            raise OSError("disk full")
        original(path, data)
    monkeypatch.setattr(pi, "_atomic_write", failing)
    assert _call(service, "POST", "refresh", {})[1]["status"] == "REFRESH_PUBLISH_FAILED"
    assert published.read_bytes() == before and not list(published.parent.glob("*.tmp"))


def test_quotes_retrieved_after_the_refresh_started_are_not_future(root: Path) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("MASSIVE_BASIC"), _entry("BOT_REFERENCE_FX")])
    ticks = iter(range(1000))

    def advancing() -> datetime:
        return NOW.replace(second=next(ticks) % 60)
    service = ms.MarketService(Store(), FakeTransport(ROUTES), advancing)
    http, out = _call(service, "POST", "refresh", {})
    assert http == 200 and out["priced_symbols_count"] == 1 and out["stale_symbols_count"] == 1


def test_failed_refresh_keeps_previous_published_view(root: Path) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("BOT_REFERENCE_FX")])
    service = _service(FakeTransport(ROUTES))
    assert _call(service, "POST", "refresh", {})[0] == 200
    before = _call(service, "GET", "view")[1]["view_sha256"]
    service.transport = FakeTransport({"trades/latest": (503, b"")})
    http, out = _call(service, "POST", "refresh", {})
    assert http == 200 and out["status"] == "REFRESHED_WITHOUT_VALUATION"
    assert out["provider_statuses"]["ALPACA_BASIC"] == "PROVIDER_UNAVAILABLE"
    assert _call(service, "GET", "view")[1]["view_sha256"] == before
    status = _call(service, "GET", "status")[1]
    assert status["last_attempt"]["status"] == "REFRESHED_WITHOUT_VALUATION"
    assert status["last_success"]["view_sha256"] == before


def test_missing_fx_publishes_prices_but_no_view(root: Path) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC")])
    service = _service(FakeTransport(ROUTES))
    http, out = _call(service, "POST", "refresh", {})
    assert http == 200 and out["fx_status"] == "FX_PROVIDER_NOT_READY"
    assert out["valuation_status"].startswith("PRICES_ONLY_")
    assert not (root / "data" / "private" / "market" / ms.PUBLISHED_FILE).exists()
    assert _call(service, "GET", "view") == (404, {"status": "NO_REPORT"})


@pytest.mark.parametrize("method, name, body, headers, http, code", [
    ("POST", "refresh", {}, {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN, "Content-Type": "application/json"}, 401, "SESSION_TOKEN_REQUIRED"),
    ("POST", "refresh", {}, {"Host": f"127.0.0.1:{PORT}", "Origin": "http://evil.example", srv.TOKEN_HEADER: TOKEN,
                             "Content-Type": "application/json"}, 403, "ORIGIN_NOT_ALLOWED"),
    ("POST", "refresh", {}, {"Host": "evil.example", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN}, 421, "HOST_NOT_ALLOWED"),
    ("POST", "refresh", {}, {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN,
                             "Content-Type": "text/plain"}, 415, "CONTENT_TYPE_NOT_ALLOWED"),
    ("GET", "refresh", None, None, 405, "METHOD_NOT_ALLOWED"),
    ("POST", "refresh", {"url": "https://evil.example", "provider": "X"}, None, 400, "REQUEST_FIELDS_INVALID"),
])
def test_routes_refuse_unauthenticated_cross_origin_and_injected_requests(
        root: Path, method: str, name: str, body: Any, headers: Optional[Dict[str, str]], http: int, code: str) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC")])
    transport = FakeTransport(ROUTES)
    assert _call(_service(transport), method, name, body, headers) == (http, {"status": code})
    assert transport.calls == []


def test_status_reports_backend_capabilities_without_secrets(root: Path) -> None:
    _odr4(root, "PROPOSED_NOT_RATIFIED")
    http, out = _call(_service(FakeTransport()), "GET", "status")
    assert http == 200 and out["odr_004"] == "PROPOSED_NOT_RATIFIED"
    assert out["last_attempt"] is None and out["last_success"] is None
    assert {p["provider_id"]: p["status"] for p in out["providers"]}["ALPACA_BASIC"] == "GOVERNANCE_REQUIRED"


def test_credit_view_reports_only_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The Dashboard budget comes from the persisted ledger: counts only, no prices, no guesses."""
    monkeypatch.setattr(mp, "MARKETDATA_CONTRACT_VERIFIED", True)
    monkeypatch.setattr(ms, "market_path", lambda name: tmp_path / name)
    empty = ms.credit_view(_clock)
    assert empty["limit"] == mp.MARKETDATA_CREDIT_LIMIT and empty["reserved"] == 0
    assert empty["ledger_present"] is False and empty["remaining"] == mp.MARKETDATA_CREDIT_LIMIT
    ledger = tmp_path / ms.CREDITS_FILE
    mp.MarketDataAppFreeProvider(CRED, FakeTransport({"quotes": (200, _MARKETDATA_OK)}), _allow, _clock,
                                 ledger_path=ledger).latest_prices(["SYNA", "SYNB"], date(2026, 11, 3))
    used = ms.credit_view(_clock)
    assert used["reserved"] == 2 and used["remaining"] == mp.MARKETDATA_CREDIT_LIMIT - 2
    assert used["ledger_present"] is True
    assert json.loads(ledger.read_text(encoding="utf-8"))["used"] == 2
    stale = {"window": "2020-01-01", "used": 99}
    ledger.write_text(json.dumps(stale), encoding="utf-8")
    assert ms.credit_view(_clock)["reserved"] == 0  # a window outside today never spends the budget


def test_market_modules_hold_no_trading_surface_and_no_test_uses_the_network(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in (mp, ma, ms):
        text = Path(str(module.__file__)).read_text(encoding="utf-8")
        for banned in ("/v2/orders", "/v2/account", "/v2/positions", "paper-api", "api.alpaca.markets", "transfer"):
            assert banned not in text
    assert set(mp.ENDPOINTS) == set(ma.ADAPTED_PROVIDERS)

    def blocked(*_: Any, **__: Any) -> None:
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "create_connection", blocked)
    with pytest.raises(DataContractError, match="ENDPOINT_NOT_ALLOWED"):
        mp.urllib_transport(mp.HttpRequest("MASSIVE_BASIC", "https://evil.example/v2/aggs/ticker/A/prev", {}))


def _bar(day: str, close: float = 200.0) -> Dict[str, Any]:
    stamp = int(datetime.fromisoformat(day + "T13:30:00+00:00").timestamp() * 1000)
    return {"t": stamp, "o": close - 1, "h": close + 1, "l": close - 2, "c": close, "v": 1000}


def test_massive_historical_daily_bars_are_bounded_and_labelled() -> None:
    t = FakeTransport({"range/1/day": (200, {"results": [_bar("2026-10-01"), _bar("2026-10-02", 201.5)],
                                              "resultsCount": 2, "status": "OK"})})
    provider = mp.MassiveEODMarketDataProvider(CRED, t, _allow, _clock)
    bars = provider.historical_daily(["AAPL"], date(2026, 10, 1), date(2026, 10, 2))
    assert [b["session_date"] for b in bars] == [date(2026, 10, 1), date(2026, 10, 2)]
    assert bars[0]["adjusted"] is False and bars[0]["provider"] == "MASSIVE_BASIC"
    assert Decimal(bars[1]["close"]) == Decimal("201.5")
    request = t.calls[0]
    assert "range/1/day/2026-10-01/2026-10-02" in request.url and "adjusted=false" in request.url
    assert request.headers["Authorization"].startswith("Bearer ")
    assert CRED[1] not in request.url


def test_massive_historical_daily_bars_reject_out_of_range_and_pagination() -> None:
    t = FakeTransport({"range/1/day": (200, {"results": [_bar("2026-09-01")], "resultsCount": 1})})
    provider = mp.MassiveEODMarketDataProvider(CRED, t, _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        provider.historical_daily(["AAPL"], date(2026, 10, 1), date(2026, 10, 2))

    paged = FakeTransport({"range/1/day": (200, {"results": [_bar("2026-10-01")], "next_url": "https://evil.example/x"})})
    provider = mp.MassiveEODMarketDataProvider(CRED, paged, _allow, _clock)
    with pytest.raises(DataContractError, match="PROVIDER_PAGINATION_UNSUPPORTED"):
        provider.historical_daily(["AAPL"], date(2026, 10, 1), date(2026, 10, 2))


def test_massive_historical_daily_bars_rate_limit_and_range_validation() -> None:
    provider = mp.MassiveEODMarketDataProvider(CRED, FakeTransport(), lambda: False, _clock)
    assert provider.historical_daily(["AAPL"], date(2026, 10, 1), date(2026, 10, 2)) == []
    assert provider.skipped == ["AAPL"]
    with pytest.raises(DataContractError, match="MASSIVE_RANGE_INVALID"):
        provider.historical_daily(["AAPL"], date(2026, 10, 2), date(2026, 10, 1))


# ---- research route ---------------------------------------------------------------------------

def test_research_route_reports_a_missing_run_without_inventing_numbers(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pi, "_private_dir", lambda *parts: tmp_path.joinpath(*parts))
    doc = ms.research_view()
    assert doc["status"] == "NO_RESEARCH_RUN"
    assert "note" in doc and doc["collector_health"] is None
    assert "proposal" not in doc


def test_research_route_projects_only_derived_fields(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pi, "_private_dir", lambda *parts: tmp_path.joinpath(*parts))
    directory = tmp_path / "market_warehouse"
    directory.mkdir(parents=True)
    report = {
        "generated_at": "2026-11-04T12:00:00+00:00",
        "job": {"requests": 26, "storage_rights": "UNESTABLISHED",
                "symbols": {"VOO": {"status": "COLLECTED"}}},
        "coverage": {"union_sessions": 402, "union_first": "2025-01-02", "union_last": "2026-11-03",
                     "covered": 24, "partial": 1, "missing": 1,
                     "symbols": {"VOO": {"sessions": 402, "status": "COVERED"}}},
        "panel": {"aligned_sessions": 401, "first": "2025-01-03", "last": "2026-11-03",
                  "eligible": ["VOO"], "excluded": {"NASA": {"reason": "SESSION_COVERAGE_BELOW_MINIMUM",
                                                              "sessions": 151}},
                  "weights": {"VOO": "0.5"}},
        "proposal": {"strategy_id": "EQUAL_WEIGHT",
                     "recommendation_status": "RESEARCH_ONLY_NOT_AUTHORIZED_FOR_EXECUTION",
                     "execution_authority": "NONE",
                     "cash_weight": "0.0500", "target_weights": {"VOO": "0.95"},
                     "proposed_actions": [{"symbol": "VOO", "action": "REDUCE", "from_weight": "1",
                                           "to_weight": "0.95"}],
                     "rank_scores": {"EQUAL_WEIGHT": "1.04"}, "modeled_risk": {"oos_sharpe": "0.6"},
                     "limitations": ["Historical evaluation does not predict future returns."]},
        "governance": {"execution_authority": "NONE", "real_capital_authority_usd": "0.00"},
        "bars": {"VOO": [{"close": "100"}]},
    }
    (directory / "backfill_report.json").write_text(json.dumps(report), encoding="utf-8")
    (directory / "health.json").write_text(json.dumps({"coverage": {"covered": 24}}), encoding="utf-8")
    doc = ms.research_view()
    assert doc["status"] == "RESEARCH_READY"
    assert doc["proposal"]["strategy_id"] == "EQUAL_WEIGHT"
    assert doc["universe"]["eligible"] == ["VOO"] and "NASA" in doc["universe"]["excluded"]
    assert doc["storage_rights"] == "UNESTABLISHED"
    # Raw observations must never be projected into a browser payload.
    assert "bars" not in json.dumps(doc)
    assert "close" not in json.dumps(doc)
