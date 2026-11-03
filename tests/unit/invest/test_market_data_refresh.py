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


def _bot(rows: List[Tuple[str, str]]) -> Dict[str, Any]:
    return {"result": {"data": {"data_detail": [{"period": d, "rate": r} for d, r in rows]}}}


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
    ("BOT_REFERENCE_FX", "https://169.254.169.254/Stat-ReferenceRate/v2/DAILY_REF_RATE/"),
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
                       "DAILY_REF_RATE": (200, _bot([("2026-11-03", "33.10")]))})
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
    t = FakeTransport({"DAILY_REF_RATE": (200, _bot([("2026-10-30", "33.2000"), ("2026-11-02", ""), ("2026-11-03", "33.1000")]))})
    obs = mp.BOTReferenceFXProvider(CRED, t, _allow, _clock).reference_rates(date(2026, 11, 3))
    assert [(o.from_currency, o.to_currency, o.market_date.isoformat()) for o in obs][:2] == [
        ("USD", "THB", "2026-10-30"), ("THB", "USD", "2026-10-30")]
    assert len(obs) == 4 and all(o.kind == "REFERENCE_FX" for o in obs)
    assert obs[2].rate == Decimal("33.1000") and abs(obs[3].rate * obs[2].rate - 1) < Decimal("1e-9")


@pytest.mark.parametrize("body", [{"result": {}}, _bot([("2026-11-03", "abc")]), _bot([("2026-11-09", "33")]),
                                  _bot([("2026-11-03", "33"), ("2026-11-03", "33")]), _bot([("03/11/2026", "33")])])
def test_bot_rejects_malformed_or_out_of_range(body: Any) -> None:
    t = FakeTransport({"DAILY_REF_RATE": (200, body)})
    with pytest.raises(DataContractError, match="PROVIDER_RESPONSE_INVALID"):
        mp.BOTReferenceFXProvider(CRED, t, _allow, _clock).reference_rates(date(2026, 11, 3))


# ---- ODR-004 authority ------------------------------------------------------------------------

def _odr1(root: Path, status: str = "RATIFIED") -> None:
    record = root / po.AUTHORIZATION_RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"capability": po.AUTHORIZED_CAPABILITY, "status": status, "ratified_by": "OWNER",
                                  "ratified_on": "2026-11-02", "scope_schemas": [po.SCHEMA_V1_2, CAPACITY_SCHEMA]}),
                      encoding="utf-8")


def _entry(pid: str, **changes: Any) -> Dict[str, Any]:
    return {"provider_id": pid, "entitlement_verified": True, "display_permitted": True, "cache_permitted": False,
            "evidence": "synthetic test", **changes}


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
                         "BOT_REFERENCE_FX": "GOVERNANCE_REQUIRED", "WEBULL_TH_OPENAPI": "NOT_CONFIGURED"}
    _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("MASSIVE_BASIC", entitlement_verified=None),
                       _entry("BOT_REFERENCE_FX", display_permitted=False), _entry("WEBULL_TH_OPENAPI")])
    assert _status() == {"ALPACA_BASIC": "READY", "MASSIVE_BASIC": "ENTITLEMENT_REQUIRED",
                         "BOT_REFERENCE_FX": "DISPLAY_RIGHTS_UNVERIFIED", "WEBULL_TH_OPENAPI": "NOT_CONFIGURED"}
    assert _status(Store({}))["ALPACA_BASIC"] == "CREDENTIALS_REQUIRED"
    _odr4(root, scope=[_entry("ALPACA_BASIC"), _entry("ALPACA_BASIC")])
    assert _status()["ALPACA_BASIC"] == "GOVERNANCE_REQUIRED"


def test_repository_odr4_has_empty_scope() -> None:
    doc = json.loads((Path(".") / ma.RECORD).read_text(encoding="utf-8"))
    assert doc["scope_providers"] == [] and doc["decision_id"] == ma.DECISION_ID
    assert {"TRADING_AUTHORIZED", "BROKER_ACCOUNT_CONNECTIVITY", "MARKET_DATA_SUBSCRIPTION"} <= set(doc["independent_of"])


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
    fx = mp.BOTReferenceFXProvider(CRED, FakeTransport({"DAILY_REF_RATE": (200, _bot([("2026-11-03", "33.10")]))}),
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
          "DAILY_REF_RATE": (200, _bot([("2026-11-03", "33.10")]))}


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
    assert CRED[1] not in json.dumps(out) and CRED[1] not in (root / "data" / "private" / "market" / ms.RECORD_FILE).read_text("utf-8")
    view_status, view = _call(service, "GET", "view")
    assert view_status == 200 and view["data_mode"] == "OWNER_PRIVATE_READ_ONLY"
    status_http, status_doc = _call(service, "GET", "status")
    assert status_http == 200 and status_doc["last_refresh"]["valuation_status"] == "PARTIAL_INDICATIVE_VALUATION"
    assert {q["security_id"]: q["used"] for q in status_doc["last_refresh"]["quotes"]} == {"SYNIDX": True, "SYNBOND": False}
    assert CRED[1] not in json.dumps(status_doc)


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
    view_path = root / "data" / "private" / "market" / ms.VIEW_FILE
    before = view_path.read_bytes()
    service.transport = FakeTransport({"trades/latest": (503, b"")})
    http, out = _call(service, "POST", "refresh", {})
    assert http == 200 and out["status"] == "REFRESHED_WITHOUT_VALUATION"
    assert out["provider_statuses"]["ALPACA_BASIC"] == "PROVIDER_UNAVAILABLE"
    assert view_path.read_bytes() == before


def test_missing_fx_publishes_prices_but_no_view(root: Path) -> None:
    _install(root)
    _odr4(root, scope=[_entry("ALPACA_BASIC")])
    http, out = _call(_service(FakeTransport(ROUTES)), "POST", "refresh", {})
    assert http == 200 and out["fx_status"] == "FX_PROVIDER_NOT_READY"
    assert out["valuation_status"].startswith("PRICES_ONLY_")
    assert not (root / "data" / "private" / "market" / ms.VIEW_FILE).exists()


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
    assert http == 200 and out["odr_004"] == "PROPOSED_NOT_RATIFIED" and out["last_refresh"] is None
    assert {p["provider_id"]: p["status"] for p in out["providers"]}["ALPACA_BASIC"] == "GOVERNANCE_REQUIRED"


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
