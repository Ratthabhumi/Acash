"""Manual "Refresh Prices" for the owner-private dashboard (``/api/upi/market/``).

Every request needs the server's Host, Origin and session checks plus ODR-001; a refresh also
needs ODR-004 (``OWNER_MARKET_DATA_RETRIEVAL_AUTHORIZED``) and at least one provider that
``market_authority`` reports READY. Only those providers are constructed, each behind its own
rate limit. A refresh never touches the saved snapshot, capacity or transaction files: it writes
a derived market view and a refresh record under ``data/private/market/``, view first, each
atomically; on any failure the previous pair stays published. Responses carry counts and status
codes only; credentials are read per refresh and never returned or logged.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from acash.core.domain.exceptions import DataContractError
from acash.dashboard_api import private_input as pi
from acash.invest import market_authority as ma
from acash.invest.capacity_plan import load_capacity
from acash.market_data.providers import (
    AlpacaIEXMarketDataProvider,
    BOTReferenceFXProvider,
    MassiveEODMarketDataProvider,
    Transport,
    urllib_transport,
)
from acash.invest.market_refresh import refresh_prices
from acash.invest.market_valuation import MarketDataProvider, PriceObservation
from acash.invest.upi_view import build_view
from acash.invest.wealth_pack import build_wealth_pack
from acash.ppds.private_observation import SCHEMA_V1_2, build_book, parse_snapshot, read_gated_json

PREFIX = "/api/upi/market/"
ROUTES = {"status": ("GET",), "refresh": ("POST",), "view": ("GET",)}
MARKET_DIR = ("market",)
VIEW_FILE = "market_view.json"
RECORD_FILE = "market_refresh.json"
LIMITS = {"ALPACA_BASIC": (200, 60.0), "MASSIVE_BASIC": (5, 60.0), "BOT_REFERENCE_FX": (200, 3600.0)}
REFRESHES_PER_MINUTE = 4


class MarketService:
    def __init__(self, store: Optional[ma.CredentialStore] = None, transport: Transport = urllib_transport,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 monotonic: Callable[[], float] = time.monotonic, record: Optional[Path] = None) -> None:
        self.store = store or ma.WindowsCredentialStore()
        self.transport, self.clock, self.record = transport, clock, record
        self.lock = threading.Lock()
        self.limiters = {pid: pi.RateLimiter(n, monotonic, window) for pid, (n, window) in LIMITS.items()}
        self.refreshes = pi.RateLimiter(REFRESHES_PER_MINUTE, monotonic)
        self.eod_cache: Dict[str, PriceObservation] = {}

    def statuses(self) -> Dict[str, Any]:
        state, providers = ma.provider_statuses(self.store, self.record)
        return {"odr_004": state, "providers": providers}


def market_path(name: str) -> Path:
    return pi._private_dir(*MARKET_DIR) / name


def _read_record() -> Optional[Dict[str, Any]]:
    path = market_path(RECORD_FILE)
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "RECORD_UNREADABLE"}
    return doc if isinstance(doc, dict) else {"status": "RECORD_UNREADABLE"}


def _providers(service: MarketService, ready: List[str]) -> Dict[str, Any]:
    built: Dict[str, Any] = {}
    for pid in ready:
        credential = service.store.lookup(pid)
        if credential is None:
            continue
        allow = service.limiters[pid].allow
        if pid == "ALPACA_BASIC":
            built[pid] = AlpacaIEXMarketDataProvider(credential, service.transport, allow, service.clock)
        elif pid == "MASSIVE_BASIC":
            built[pid] = MassiveEODMarketDataProvider(credential, service.transport, allow, service.clock,
                                                      cache=service.eod_cache)
        elif pid == "BOT_REFERENCE_FX":
            built[pid] = BOTReferenceFXProvider(credential, service.transport, allow, service.clock)
    return built


def refresh(service: MarketService) -> pi.Result:
    requested_at = service.clock()
    statuses = service.statuses()
    if statuses["odr_004"] != "RATIFIED":
        return 403, {"status": "MARKET_DATA_AUTHORIZATION_REQUIRED", **statuses}
    ready = [p["provider_id"] for p in statuses["providers"] if p["status"] == "READY"]
    providers = _providers(service, ready)
    price_providers: List[MarketDataProvider] = [providers[p] for p in ("ALPACA_BASIC", "MASSIVE_BASIC") if p in providers]
    if not price_providers:
        return 409, {"status": "NO_READY_PRICE_PROVIDER", **statuses}
    snapshot_path, capacity_path = pi._input_path("snapshot"), pi._input_path("capacity")
    if not snapshot_path.is_file() or not capacity_path.is_file():
        return 404, {"status": "NO_INPUT"}
    revisions = {kind: pi._revision(pi._input_path(kind)) for kind in pi.INPUTS}
    doc = read_gated_json(snapshot_path, "INPUT", schema=SCHEMA_V1_2)
    refresh_id = f"{requested_at.strftime('%Y%m%dT%H%M%SZ')}"
    result = refresh_prices(doc, price_providers, providers.get("BOT_REFERENCE_FX"), requested_at, "MARKET_REFRESH",
                            service.clock)
    meta = result["meta"]
    status = meta["valuation_status"]
    view = None
    if result["derived"] is not None:
        try:
            book = build_book(parse_snapshot(result["derived"]))
            pack = build_wealth_pack(book, load_capacity(capacity_path), None, requested_at.date())
            view = build_view(json.loads(json.dumps(pack)))
        except DataContractError as exc:
            status = "PRICES_ONLY_" + str(exc).split(":")[0].rstrip(".")
    if {kind: pi._revision(pi._input_path(kind)) for kind in pi.INPUTS} != revisions:
        return 409, {"status": "INPUTS_CHANGED_DURING_REFRESH"}
    provider_statuses = {**{p["provider_id"]: p["status"] for p in statuses["providers"]},
                         **result["provider_statuses"]}
    summary = {
        "refresh_id": refresh_id, "requested_at": requested_at.isoformat(timespec="seconds"),
        "completed_at": service.clock().isoformat(timespec="seconds"), "provider_statuses": provider_statuses,
        "requested_symbols_count": result["requested"], "priced_symbols_count": meta["coverage"]["priced"],
        "stale_symbols_count": meta["coverage"]["misaligned_date"],
        "unavailable_symbols_count": len(result["unpriced"]), "valuation_status": status,
        "fx_status": result["fx_status"], "report_generation_id": refresh_id if view else None,
    }
    record = {**summary, "meta": meta, "quotes": result["quotes"],
              "rejected_count": len(result["rejected"]), "view_sha256": view["view_sha256"] if view else None}
    directory = pi._private_dir(*MARKET_DIR)
    directory.mkdir(exist_ok=True)
    previous_view = market_path(VIEW_FILE).read_bytes() if market_path(VIEW_FILE).is_file() else None
    try:
        if view is not None:
            pi._atomic_write(market_path(VIEW_FILE), (json.dumps(view, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        pi._atomic_write(market_path(RECORD_FILE), (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except OSError as exc:
        if view is not None and previous_view is not None:
            pi._atomic_write(market_path(VIEW_FILE), previous_view)
        return 500, {"status": "REFRESH_PUBLISH_FAILED", "code": type(exc).__name__}
    return 200, {"status": "REFRESHED" if view else "REFRESHED_WITHOUT_VALUATION", **summary}


def handle(method: str, name: str, body: Any, service: MarketService) -> pi.Result:
    """Dispatch after the server's Host, Origin, session and body checks have passed."""
    observation = pi.authority()["odr_001"]
    if observation != "RATIFIED":
        return 403, {"status": "AUTHORIZATION_REQUIRED", "odr_001": observation}
    try:
        if name == "status":
            return 200, {"status": "OK", **service.statuses(), "last_refresh": _read_record()}
        if name == "refresh":
            if body != {}:
                return 400, {"status": "REQUEST_FIELDS_INVALID"}
            if not service.refreshes.allow():
                return 429, {"status": "RATE_LIMITED"}
            if not service.lock.acquire(blocking=False):
                return 409, {"status": "REFRESH_IN_PROGRESS"}
            try:
                return refresh(service)
            finally:
                service.lock.release()
    except DataContractError as exc:
        return 422, {"status": "REFRESH_FAILED", **pi._code(exc)}
    return 404, {"status": "NOT_FOUND"}
