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
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.dashboard_api import private_input as pi
from acash.dashboard_api import private_transactions as pt
from acash.invest import market_authority as ma
from acash.invest.capacity_plan import load_capacity
from acash.market_data.providers import (
    AlpacaHistoricalSIPProvider,
    AlpacaIEXMarketDataProvider,
    BOTReferenceFXProvider,
    FrankfurterECBFxProvider,
    MARKETDATA_CREDIT_LIMIT,
    MarketDataAppFreeProvider,
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
ROUTES = {"status": ("GET",), "refresh": ("POST",), "view": ("GET",), "research": ("GET",), "session": ("GET",)}
MARKET_DIR = ("market",)
PUBLISHED_FILE = "market_published.json"
ATTEMPT_FILE = "market_last_attempt.json"
LEGACY_FILES = ("market_view.json", "market_refresh.json")
CREDITS_FILE = "marketdata_credits.json"
RESEARCH_DIR = ("market_warehouse",)
LIMITS = {"ALPACA_BASIC": (200, 60.0), "ALPACA_HISTORICAL": (200, 60.0),
          "MARKETDATA_APP_FREE": (100, 86400.0), "FRANKFURTER_ECB_FX": (200, 3600.0),
          "MASSIVE_BASIC": (5, 60.0), "BOT_REFERENCE_FX": (200, 3600.0)}
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
        self.memory_generation: Optional[Dict[str, Any]] = None

    def statuses(self) -> Dict[str, Any]:
        state, providers = ma.provider_statuses(self.store, self.record)
        return {"odr_004": state, "providers": providers, "marketdata_credits": credit_view(self.clock)}


def market_path(name: str) -> Path:
    return pi._private_dir(*MARKET_DIR) / name


def credit_view(clock: Callable[[], datetime]) -> Dict[str, Any]:
    """Free-tier budget for MarketData.app: counts only, no prices, readable without a request.

    The published window opens at 09:30 America/New_York; a missing or unreadable ledger is reported
    as an untouched budget rather than guessed, and the value never authorises a request by itself.
    """
    window = MarketDataAppFreeProvider.credit_window(clock())
    doc = _read_json(CREDITS_FILE) or {}
    used = doc.get("used")
    same_window = doc.get("window") == window.isoformat()
    reserved = used if same_window and isinstance(used, int) and not isinstance(used, bool) and used >= 0 else 0
    return {"window": window.isoformat(), "limit": MARKETDATA_CREDIT_LIMIT, "reserved": reserved,
            "remaining": max(0, MARKETDATA_CREDIT_LIMIT - reserved), "ledger_present": isinstance(used, int)}


def _read_json(name: str, directory: Optional[Tuple[str, ...]] = None) -> Optional[Dict[str, Any]]:
    path = market_path(name) if directory is None else pi._private_dir(*directory) / name
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "RECORD_UNREADABLE"}
    return doc if isinstance(doc, dict) else {"status": "RECORD_UNREADABLE"}


def _write_json(name: str, doc: Dict[str, Any]) -> None:
    pi._private_dir(*MARKET_DIR).mkdir(parents=True, exist_ok=True)
    pi._atomic_write(market_path(name), (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _permits(statuses: Dict[str, Any], used: List[str], persisted: bool) -> bool:
    """Every provider whose data a generation contains is still READY (and cache-permitted if on disk)."""
    current = {p["provider_id"]: p for p in statuses["providers"]}
    return statuses["odr_004"] == "RATIFIED" and all(
        current.get(pid, {}).get("status") == "READY" and (not persisted or current[pid]["cache_permitted"])
        for pid in used)


def published(service: MarketService) -> Optional[Dict[str, Any]]:
    """The last successful generation if its providers still permit it; otherwise it is discarded.

    Discarding deletes the on-disk generation and the in-process copy, so revoking a provider (or its
    cache permission) stops every later reuse of its observations and of values derived from them.
    """
    statuses = service.statuses()
    path = market_path(PUBLISHED_FILE)
    generation = _read_json(PUBLISHED_FILE) if path.is_file() else service.memory_generation
    if generation is None:
        return None
    persisted = path.is_file()
    record = generation.get("record") if isinstance(generation.get("record"), dict) else None
    view = generation.get("view")
    used = record.get("providers_used") if record else None
    valid = (record is not None and isinstance(view, dict) and isinstance(used, list)
             and record.get("view_sha256") == view.get("view_sha256"))
    if not valid or not _permits(statuses, list(used or []), persisted):
        if persisted:
            path.unlink(missing_ok=True)
        service.memory_generation = None
        return None
    return generation


def _providers(service: MarketService, ready: List[Dict[str, Any]]) -> Dict[str, Any]:
    built: Dict[str, Any] = {}
    for status in ready:
        pid = status["provider_id"]
        credential = service.store.lookup(pid)
        allow = service.limiters[pid].allow
        # Keyless providers are built before the credential gate; everything else needs one.
        if pid in ma.KEYLESS_PROVIDERS:
            if pid == "FRANKFURTER_ECB_FX":
                built[pid] = FrankfurterECBFxProvider(service.transport, allow, service.clock)
            continue
        if credential is None:
            continue
        if pid == "ALPACA_BASIC":
            built[pid] = AlpacaIEXMarketDataProvider(credential, service.transport, allow, service.clock)
        elif pid == "ALPACA_HISTORICAL":
            built[pid] = AlpacaHistoricalSIPProvider(credential, service.transport, allow, service.clock)
        elif pid == "MARKETDATA_APP_FREE":
            built[pid] = MarketDataAppFreeProvider(credential, service.transport, allow, service.clock,
                                                   ledger_path=market_path(CREDITS_FILE))
        elif pid == "MASSIVE_BASIC":
            if not status["cache_permitted"]:
                service.eod_cache.clear()
            cache = service.eod_cache if status["cache_permitted"] else {}
            built[pid] = MassiveEODMarketDataProvider(credential, service.transport, allow, service.clock,
                                                      cache=cache)
        elif pid == "BOT_REFERENCE_FX":
            built[pid] = BOTReferenceFXProvider(credential, service.transport, allow, service.clock)
    return built


CENT = Decimal("0.01")
WEIGHT = Decimal("0.0001")


def _holdings(book: Any, derived: Dict[str, Any], quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-holding rows from the PPDS book, converted at the rate PPDS used for that currency;
    weights are shares of the priced subtotal only."""
    ccy = str(derived["reporting_currency"])
    consolidated = book.consolidated[ccy]
    subtotal = consolidated.consolidated_nav
    to_reporting = {e.currency: e.fx_rate_to_base for e in consolidated.currency_exposures}
    used = {q["security_id"]: q for q in quotes if q["used"]}
    cost = {(a["account_ref"], p["security_id"]): p for a in derived["accounts"] for p in a.get("positions", [])}
    rows = []
    for account, valuation in sorted(consolidated.account_valuations.items()):
        for pos in valuation.positions:
            line = cost.get((account, pos.symbol), {})
            quote = used.get(pos.symbol, {})
            local = book.valuations[account].positions
            value_local = next((p.net_market_value_local for p in local if p.symbol == pos.symbol), None)
            basis = line.get("cost_basis_total")
            pnl = (str((value_local - Decimal(str(basis))).quantize(CENT))
                   if basis is not None and value_local is not None and line.get("cost_basis_currency") == pos.pricing_currency
                   else None)
            rate = to_reporting.get(pos.pricing_currency)
            value_reporting = value_local * rate if value_local is not None and rate is not None else None
            rows.append({"account_ref": account, "security_id": pos.symbol, "quantity": str(pos.net_quantity),
                         "price": str(pos.price), "price_currency": pos.pricing_currency,
                         "provider_id": quote.get("provider_id"), "price_type": quote.get("price_type"),
                         "market_timestamp": quote.get("market_timestamp") or quote.get("market_date"),
                         "market_value_local": None if value_local is None else str(value_local),
                         "market_value_reporting": None if value_reporting is None else str(value_reporting.quantize(CENT)),
                         "weight_of_priced_subtotal": (str((value_reporting / subtotal).quantize(WEIGHT))
                                                       if value_reporting is not None and subtotal else None),
                         "unrealized_pnl_local": pnl,
                         "unrealized_status": "COMPUTED" if pnl is not None else "COST_NOT_ESTABLISHED"})
    return {"reporting_currency": ccy, "priced_subtotal": str(subtotal),
            "weight_basis": "SHARE_OF_PRICED_SUBTOTAL_NOT_TOTAL_PORTFOLIO", "rows": rows}


def _attempt(service: MarketService, requested_at: datetime, status: str, **extra: Any) -> None:
    """Price-free record of the latest attempt; never replaces the last successful generation."""
    _write_json(ATTEMPT_FILE, {"requested_at": requested_at.isoformat(timespec="seconds"),
                               "completed_at": service.clock().isoformat(timespec="seconds"),
                               "status": status, **extra})


def refresh(service: MarketService) -> pi.Result:
    requested_at = service.clock()
    statuses = service.statuses()
    if statuses["odr_004"] != "RATIFIED":
        service.eod_cache.clear()
        published(service)
        return 403, {"status": "MARKET_DATA_AUTHORIZATION_REQUIRED", **statuses}
    ready = [p for p in statuses["providers"] if p["status"] == "READY"]
    if not any(p["provider_id"] == "MASSIVE_BASIC" for p in ready):
        service.eod_cache.clear()
    providers = _providers(service, ready)
    # Priority order: real-time IEX, consolidated delayed SIP bars, delayed EOD, then EOD fallback.
    price_providers: List[MarketDataProvider] = [
        providers[p] for p in ("ALPACA_BASIC", "ALPACA_HISTORICAL", "MARKETDATA_APP_FREE", "MASSIVE_BASIC")
        if p in providers]
    if not price_providers:
        return 409, {"status": "NO_READY_PRICE_PROVIDER", **statuses}
    snapshot_path, capacity_path = pi._input_path("snapshot"), pi._input_path("capacity")
    if not snapshot_path.is_file() or not capacity_path.is_file():
        return 404, {"status": "NO_INPUT"}
    revisions = {kind: pi._revision(pi._input_path(kind)) for kind in pi.INPUTS}
    journal_revision = pt.journal_revision()
    doc = read_gated_json(snapshot_path, "INPUT", schema=SCHEMA_V1_2)
    doc, holdings_basis = pt.holdings_for_valuation(doc, requested_at.astimezone(timezone.utc).date())
    refresh_id = f"{requested_at.strftime('%Y%m%dT%H%M%SZ')}"
    try:
        fx_provider = providers.get("BOT_REFERENCE_FX") or providers.get("FRANKFURTER_ECB_FX")
        result = refresh_prices(doc, price_providers, fx_provider, requested_at,
                                "MARKET_REFRESH", service.clock)
    except DataContractError as exc:
        _attempt(service, requested_at, "REFRESH_FAILED", **pi._code(exc))
        raise
    meta = result["meta"]
    status = meta["valuation_status"]
    view = None
    holdings: Optional[Dict[str, Any]] = None
    if result["derived"] is not None:
        try:
            book = build_book(parse_snapshot(result["derived"]))
            pack = build_wealth_pack(book, load_capacity(capacity_path), None, requested_at.date())
            view = build_view(json.loads(json.dumps(pack)))
            holdings = _holdings(book, result["derived"], result["quotes"])
        except DataContractError as exc:
            status = "PRICES_ONLY_" + str(exc).split(":")[0].rstrip(".")
    if ({kind: pi._revision(pi._input_path(kind)) for kind in pi.INPUTS} != revisions
            or pt.journal_revision() != journal_revision):
        _attempt(service, requested_at, "INPUTS_CHANGED_DURING_REFRESH")
        return 409, {"status": "INPUTS_CHANGED_DURING_REFRESH"}
    provider_statuses = {**{p["provider_id"]: p["status"] for p in statuses["providers"]},
                         **result["provider_statuses"]}
    fx_provider_id = result["meta"].get("fx_provider_id")
    used = sorted({q["provider_id"] for q in result["quotes"] if q["used"]} | ({fx_provider_id} if fx_provider_id else set()))
    summary = {
        "refresh_id": refresh_id, "requested_at": requested_at.isoformat(timespec="seconds"),
        "completed_at": service.clock().isoformat(timespec="seconds"), "provider_statuses": provider_statuses,
        "requested_symbols_count": result["requested"], "priced_symbols_count": meta["coverage"]["priced"],
        "stale_symbols_count": meta["coverage"]["misaligned_date"],
        "unavailable_symbols_count": len(result["unpriced"]), "valuation_status": status,
        "fx_status": result["fx_status"], "report_generation_id": refresh_id if view else None,
        "holdings_basis": holdings_basis,
    }
    if view is None:
        _attempt(service, requested_at, "REFRESHED_WITHOUT_VALUATION", summary=summary)
        return 200, {"status": "REFRESHED_WITHOUT_VALUATION", **summary}
    after = service.statuses()
    current = {p["provider_id"]: p for p in after["providers"]}
    if not _permits(after, used, False):
        _attempt(service, requested_at, "AUTHORIZATION_CHANGED_DURING_REFRESH")
        return 409, {"status": "AUTHORIZATION_CHANGED_DURING_REFRESH", **after}
    persist = all(current[pid]["cache_permitted"] for pid in used)
    record = {**summary, "meta": meta, "quotes": result["quotes"], "holdings": holdings,
              "providers_used": used, "persisted": persist,
              "rejected_count": len(result["rejected"]), "view_sha256": view["view_sha256"]}
    generation = {"record": record, "view": view}
    try:
        if persist:
            _write_json(PUBLISHED_FILE, generation)
        else:
            service.memory_generation = generation
            market_path(PUBLISHED_FILE).unlink(missing_ok=True)
        for legacy in LEGACY_FILES:
            market_path(legacy).unlink(missing_ok=True)
        _attempt(service, requested_at, "REFRESHED", summary=summary)
    except OSError as exc:
        return 500, {"status": "REFRESH_PUBLISH_FAILED", "code": type(exc).__name__}
    service.memory_generation = None if persist else generation
    return 200, {"status": "REFRESHED", **summary, "persisted": persist}


def research_view() -> Dict[str, Any]:
    """Derived research output only: coverage, universe eligibility and the proposal payload.

    Reads the files written by ``scripts/backfill_massive_universe.py``. Raw bars are never stored
    there (retention is unestablished), so nothing here can expose provider market data, and a missing
    run is reported as such rather than reconstructed from memory.
    """
    report = _read_json("backfill_report.json", RESEARCH_DIR)
    health = _read_json("health.json", RESEARCH_DIR)
    if report is None or "coverage" not in report:
        return {"status": "NO_RESEARCH_RUN", "collector_health": health,
                "note": "Run scripts/backfill_massive_universe.py to produce derived research evidence."}
    matrix = report.get("coverage") or {}
    panel = report.get("panel") or {}
    proposal = report.get("proposal") or {}
    job = report.get("job") or {}
    return {
        "status": "RESEARCH_READY" if proposal.get("recommendation_status") else "RESEARCH_INCOMPLETE",
        "generated_at": report.get("generated_at"),
        "coverage": {key: matrix.get(key) for key in
                     ("union_sessions", "union_first", "union_last", "covered", "partial", "missing")},
        "symbols": matrix.get("symbols"),
        "universe": {"requested": len(job.get("symbols") or {}), "eligible": panel.get("eligible") or [],
                     "excluded": panel.get("excluded") or {}},
        "panel_sessions": panel.get("aligned_sessions"),
        "panel_range": {"first": panel.get("first"), "last": panel.get("last")},
        "panel_weights": panel.get("weights"),
        "proposal": {key: proposal.get(key) for key in
                     ("strategy_id", "recommendation_status", "governance_status", "execution_authority",
                      "cash_weight", "target_weights", "current_weights", "proposed_actions", "modeled_risk",
                      "rank_scores", "in_sample_period", "out_of_sample_period", "transaction_cost_status",
                      "turnover_required", "modeled_transaction_cost", "limitations", "missing_evidence",
                      "evaluated_strategies", "disclaimer")},
        "requests": job.get("requests"),
        "storage_rights": job.get("storage_rights"),
        "governance": report.get("governance"),
        "fx": _fx_view(),
        "collector_health": health,
    }


def _fx_view() -> Dict[str, Any]:
    """BOT reference FX series + THB decomposition, or an explicit absence (never a guess)."""
    from acash.invest import fx_series as fx
    series = fx.load_series()
    decomposition = fx.load_decomposition()
    if series is None:
        return {"status": "NO_FX_SERIES", "note": "Run scripts/fx_panel.py to build the BOT reference series."}
    summary = series.get("summary") or {}
    return {
        "status": "AVAILABLE" if decomposition else "SERIES_ONLY",
        "source": summary.get("source"),
        "rate_type": summary.get("rate_type"),
        "orientation": summary.get("orientation"),
        "executable": summary.get("executable"),
        "first": summary.get("first"),
        "last": summary.get("last"),
        "points": summary.get("points"),
        "weekday_gaps": summary.get("weekday_gaps"),
        "latest": summary.get("latest"),
        "decomposition": decomposition,
    }


def handle(method: str, name: str, body: Any, service: MarketService) -> pi.Result:
    """Dispatch after the server's Host, Origin, session and body checks have passed."""
    observation = pi.authority()["odr_001"]
    if observation != "RATIFIED":
        return 403, {"status": "AUTHORIZATION_REQUIRED", "odr_001": observation}
    try:
        if name == "status":
            generation = published(service)
            return 200, {"status": "OK", **service.statuses(), "last_attempt": _read_json(ATTEMPT_FILE),
                         "last_success": generation["record"] if generation else None}
        if name == "view":
            generation = published(service)
            if service.statuses()["odr_004"] != "RATIFIED":
                return 403, {"status": "MARKET_DATA_AUTHORIZATION_REQUIRED"}
            if generation is None:
                return 404, {"status": "NO_REPORT"}
            return 200, generation["view"]
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
        if name == "research":
            return 200, research_view()
        if name == "session":
            from acash.invest import market_calendar as mc
            try:
                return 200, mc.session_view(mc.load_calendar(), service.clock())
            except DataContractError as exc:
                return 409, {"status": "MARKET_CALENDAR_UNAVAILABLE", **pi._code(exc)}
    except DataContractError as exc:
        return 422, {"status": "REFRESH_FAILED", **pi._code(exc)}
    return 404, {"status": "NOT_FOUND"}
