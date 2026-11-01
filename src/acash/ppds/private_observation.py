"""PPDS local-private observation path (read-only, offline, owner-controlled).

Trust boundary (docs/architecture/PRIVATE_PORTFOLIO_OBSERVATION_BOUNDARY.md):

- An owner snapshot is a personal decision-support observation. It is never
  D5 research data, never proof of acquisition history and never carries
  trading, transfer or capital authority.
- ``OWNER_PRIVATE_OBSERVATION`` data is processed only when the owner decision
  record ``docs/governance/ODR_UPI_PRIVATE_OBSERVATION_001.json`` is RATIFIED,
  and only from/to locations outside the repository or under ``data/private/``.
- Valuation reuses PPDS base-currency valuation and consolidation through a
  snapshot valuation view. Snapshot positions are not acquisition lots, so no
  cost basis or acquisition date is ever invented to build a ledger.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.ppds.exposure import FXRate, PortfolioValuation, PriceQuote, evaluate_portfolio_base_currency
from acash.ppds.registry import (
    AccountRegistration,
    AccountRegistry,
    ConsolidatedPortfolioValuation,
    consolidate_portfolio_valuations,
)

SCHEMA = "ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1_1"
DATA_CLASSES = ("SYNTHETIC_PUBLIC_FIXTURE", "OWNER_PRIVATE_OBSERVATION")
EVIDENCE_SOURCES = ("MANUAL_SNAPSHOT", "CSV_STATEMENT")
ACCOUNT_ROLES = ("LONG_TERM", "QUANT_RESEARCH", "CASH_RESERVE", "OTHER")
CASH_KINDS = ("SETTLED", "ACCRUED_INTEREST")
SUPPORT_STATES = (
    "SNAPSHOT_ONLY",
    "TRANSACTIONS_PARTIAL",
    "TRANSACTIONS_RECONCILED",
    "HISTORICAL_PERFORMANCE_QUALIFIED",
)
TAXONOMY = (
    "CORE_DIVERSIFIED",
    "CORE_CONCENTRATED",
    "SATELLITE",
    "THEMATIC",
    "SPECULATIVE",
    "CASH",
    "UNKNOWN",
)
# A classification is accepted only with a named methodology and an evidence reference.
METHODOLOGIES = {
    "OWNER_DECLARED_WITH_EVIDENCE": "Owner-assigned bucket backed by a cited document (factsheet, prospectus, index rules).",
    "CASH_BALANCE": "Cash balance line; assigned automatically to CASH.",
    "NOT_CLASSIFIED": "No evidence-backed classification supplied; bucket is UNKNOWN.",
}
ILLUSTRATIVE_STRESS = (
    ("EQUITY_DRAWDOWN_30", "All non-cash securities -30%."),
    ("THEMATIC_SPECULATIVE_DRAWDOWN_50", "THEMATIC and SPECULATIVE securities -50%; UNKNOWN excluded and reported."),
    ("REPORTING_CCY_APPRECIATION_10", "Foreign-currency exposure revalued -10% in reporting currency."),
    ("REPORTING_CCY_DEPRECIATION_10", "Foreign-currency exposure revalued +10% in reporting currency."),
)
STRESS_NOT_EVALUATED = {
    "TECH_SELLOFF": "NOT_EVALUATED_SECTOR_DATA_MISSING",
    "SMALL_CAP_GROWTH_DRAWDOWN": "NOT_EVALUATED_SIZE_STYLE_DATA_MISSING",
    "LIQUIDITY_STRESS": "NOT_EVALUATED_LIQUIDITY_DATA_MISSING",
}
# 28-digit Decimal context residual only; any economic break is at least one minor unit.
CONSERVATION_TOLERANCE = Decimal("1e-12")
STALE_AFTER_DAYS = 7
MAX_INPUT_BYTES = 2_000_000
AUTHORIZATION_RECORD = Path("docs/governance/ODR_UPI_PRIVATE_OBSERVATION_001.json")
AUTHORIZED_CAPABILITY = "OWNER_PRIVATE_OBSERVATION_AUTHORIZED"
GOVERNANCE_FLAGS = {
    "research_admission": "NOT_ADMITTED_PRIVATE_OBSERVATION",
    "d5_eligible": False,
    "trading_authority": "NONE",
    "capital_authority_usd": "0.00",
    "order_controls": None,
}

_REF = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
_SECURITY = re.compile(r"^[A-Z0-9][A-Z0-9._:\-]{0,23}$")
_DIGIT_RUN = re.compile(r"\d{6,}")
_LONG_DIGIT_RUN = re.compile(r"\d{9,}")
_TOP_FIELDS = {"schema", "data_class", "snapshot_id", "observed_at", "valuation_date", "evidence_source",
               "reporting_currency", "report_currencies", "fx_rates", "prices", "securities", "accounts"}
_ACCOUNT_FIELDS = {"account_ref", "broker", "role", "base_currency", "cash", "positions"}
_CASH_FIELDS = {"currency", "amount", "kind", "sub_portfolio"}
_POSITION_FIELDS = {"security_id", "sub_portfolio", "quantity", "cost_basis_total", "cost_basis_currency",
                    "observed_market_value", "observed_market_value_currency"}
_FX_FIELDS = {"from", "to", "rate", "as_of", "source_id"}
_PRICE_FIELDS = {"security_id", "currency", "price", "as_of", "published_at", "source_id"}
_SECURITY_FIELDS = {"security_id", "classification", "methodology", "evidence_ref"}
ZERO = Decimal("0")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def assert_private_location(path: Path, root: Optional[Path] = None) -> None:
    """Owner-private files must live outside the repository or under ``data/private/``.

    The path is resolved first, so symlinks and ``..`` segments are judged by their real target.
    """
    resolved, base = Path(path).resolve(), (root or _repo_root()).resolve()
    try:
        rel = resolved.relative_to(base)
    except ValueError:
        return
    if rel.parts[:2] != ("data", "private"):
        raise DataContractError("PRIVATE_LOCATION_NOT_IGNORED: owner data must be outside the repo or under data/private/.")


def private_observation_authorized(record: Optional[Path] = None) -> bool:
    """True only if the owner decision record is RATIFIED by the OWNER for this capability."""
    path = record or (_repo_root() / AUTHORIZATION_RECORD)
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (isinstance(doc, dict) and doc.get("capability") == AUTHORIZED_CAPABILITY
            and doc.get("status") == "RATIFIED" and doc.get("ratified_by") == "OWNER"
            and isinstance(doc.get("ratified_on"), str))


def assert_private_observation_authorized(data_class: str) -> None:
    if data_class == "OWNER_PRIVATE_OBSERVATION" and not private_observation_authorized():
        raise DataContractError(
            "PRIVATE_OBSERVATION_NOT_AUTHORIZED: owner decision record "
            f"{AUTHORIZATION_RECORD.as_posix()} is not RATIFIED; owner-private processing is disabled.")


def read_bounded_json(path: Path, code: str) -> Any:
    """Read a JSON input with a size bound; errors never echo file contents."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise DataContractError(f"{code}_UNREADABLE: {type(exc).__name__}.") from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise DataContractError(f"{code}_TOO_LARGE: limit {MAX_INPUT_BYTES} bytes.")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataContractError(f"{code}_MALFORMED_JSON: {type(exc).__name__}.") from exc


def _fields(doc: Any, allowed: Set[str], ctx: str) -> Mapping[str, Any]:
    if not isinstance(doc, Mapping):
        raise DataContractError(f"PRIVATE_NOT_A_MAPPING: {ctx}.")
    unknown = set(doc) - allowed
    if unknown:
        raise DataContractError(f"PRIVATE_UNKNOWN_FIELDS: {ctx} {sorted(str(k) for k in unknown)}.")
    return doc


def _dec(raw: Any, ctx: str, *, positive: bool = False, nonnegative: bool = False) -> Decimal:
    if not isinstance(raw, str):
        raise DataContractError(f"PRIVATE_NUMBER_MUST_BE_STRING: {ctx}.")
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise DataContractError(f"PRIVATE_MALFORMED_DECIMAL: {ctx}.") from exc
    if not value.is_finite():
        raise DataContractError(f"PRIVATE_NONFINITE_DECIMAL: {ctx}.")
    if positive and value <= ZERO:
        raise DataContractError(f"PRIVATE_NONPOSITIVE_VALUE: {ctx}.")
    if nonnegative and value < ZERO:
        raise DataContractError(f"PRIVATE_NEGATIVE_VALUE: {ctx}.")
    return value


def _ccy(raw: Any, ctx: str) -> str:
    value = str(raw or "").strip().upper()
    if len(value) != 3 or not value.isalpha():
        raise DataContractError(f"PRIVATE_CURRENCY_INVALID: {ctx}.")
    return value


def _ref(raw: Any, ctx: str) -> str:
    value = str(raw or "")
    if not _REF.match(value) or _DIGIT_RUN.search(value):
        raise DataContractError(f"PRIVATE_REF_NOT_OPAQUE: {ctx} must match {_REF.pattern} without 6+ digit runs.")
    return value


def _label(raw: Any, ctx: str, digit_run: "re.Pattern[str]" = _DIGIT_RUN) -> Optional[str]:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value or len(value) > 64 or digit_run.search(value):
        raise DataContractError(f"PRIVATE_LABEL_INVALID: {ctx}.")
    return value


def _security(raw: Any, ctx: str) -> str:
    value = str(raw or "")
    if not _SECURITY.match(value):
        raise DataContractError(f"PRIVATE_SECURITY_ID_INVALID: {ctx}.")
    return value


def _date(raw: Any, ctx: str) -> date:
    try:
        return date.fromisoformat(str(raw))
    except ValueError as exc:
        raise DataContractError(f"PRIVATE_DATE_INVALID: {ctx}.") from exc


def _aware(raw: Any, ctx: str) -> datetime:
    try:
        value = datetime.fromisoformat(str(raw))
    except ValueError as exc:
        raise DataContractError(f"PRIVATE_TIMESTAMP_INVALID: {ctx}.") from exc
    if value.tzinfo is None:
        raise DataContractError(f"PRIVATE_TIMESTAMP_NAIVE: {ctx} requires a timezone offset.")
    return value


def _half_unit(value: Decimal) -> Decimal:
    """Half of the last displayed digit, taken from the value's own precision."""
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int):
        raise DataContractError("PRIVATE_NONFINITE_DECIMAL: precision.")
    return Decimal(1).scaleb(exponent) / 2


@dataclass(frozen=True)
class CashLine:
    account_ref: str
    currency: str
    amount: Decimal
    kind: str
    sub_portfolio: Optional[str]


@dataclass(frozen=True)
class PositionLine:
    account_ref: str
    security_id: str
    sub_portfolio: Optional[str]
    quantity: Decimal
    cost_basis_total: Optional[Decimal]
    cost_basis_currency: Optional[str]
    observed_market_value: Optional[Decimal]
    observed_market_value_currency: Optional[str]


@dataclass(frozen=True)
class AccountObservation:
    account_ref: str
    broker: str
    role: str
    base_currency: str
    cash: Tuple[CashLine, ...]
    positions: Tuple[PositionLine, ...]


@dataclass(frozen=True)
class SecurityClass:
    security_id: str
    classification: str
    methodology: str
    evidence_ref: Optional[str]


@dataclass(frozen=True)
class PortfolioSnapshot:
    data_class: str
    snapshot_id: str
    observed_at: datetime
    valuation_date: date
    evidence_source: str
    reporting_currency: str
    report_currencies: Tuple[str, ...]
    fx_rates: Tuple[FXRate, ...]
    prices: Tuple[PriceQuote, ...]
    published_at: Tuple[Tuple[str, str], ...]
    securities: Tuple[SecurityClass, ...]
    accounts: Tuple[AccountObservation, ...]
    content_sha256: str


def parse_snapshot(doc: Any) -> PortfolioSnapshot:
    """Validate a snapshot document; every amount is a decimal string, every field is known.

    ``valuation_date`` is the market-session date all prices and FX rates are pinned to; it may
    precede the local date of ``observed_at`` (e.g. a Bangkok morning after the US close) but
    never follow it.
    """
    top = _fields(doc, _TOP_FIELDS, "snapshot")
    if top.get("schema") != SCHEMA:
        raise DataContractError(f"PRIVATE_SCHEMA_MISMATCH: expected {SCHEMA}.")
    data_class = top.get("data_class")
    if data_class not in DATA_CLASSES:
        raise DataContractError("PRIVATE_DATA_CLASS_INVALID.")
    snapshot_id = _ref(top.get("snapshot_id"), "snapshot_id")
    observed_at = _aware(top.get("observed_at"), "observed_at")
    vdate = _date(top.get("valuation_date"), "valuation_date")
    if vdate > observed_at.date():
        raise DataContractError("PRIVATE_VALUATION_DATE_AFTER_OBSERVATION.")
    source = top.get("evidence_source")
    if source not in EVIDENCE_SOURCES:
        raise DataContractError("PRIVATE_EVIDENCE_SOURCE_INVALID.")
    reporting = _ccy(top.get("reporting_currency"), "reporting_currency")
    report_ccys = tuple(_ccy(c, "report_currencies") for c in top.get("report_currencies") or [reporting])
    if reporting not in report_ccys or len(set(report_ccys)) != len(report_ccys):
        raise DataContractError("PRIVATE_REPORT_CURRENCIES_INVALID: must be unique and include reporting_currency.")

    fx: Dict[Tuple[str, str], FXRate] = {}
    for i, raw in enumerate(top.get("fx_rates") or []):
        row = _fields(raw, _FX_FIELDS, f"fx_rates[{i}]")
        key = (_ccy(row.get("from"), f"fx_rates[{i}].from"), _ccy(row.get("to"), f"fx_rates[{i}].to"))
        if key[0] == key[1] or key in fx:
            raise DataContractError(f"PRIVATE_FX_DUPLICATE_OR_IDENTITY: {key}.")
        fx[key] = FXRate(key[0], key[1], _dec(row.get("rate"), f"fx {key}", positive=True),
                         _date(row.get("as_of"), f"fx {key}"),
                         _label(row.get("source_id"), f"fx {key} source", _LONG_DIGIT_RUN) or "")

    prices: Dict[str, PriceQuote] = {}
    published: Dict[str, str] = {}
    for i, raw in enumerate(top.get("prices") or []):
        row = _fields(raw, _PRICE_FIELDS, f"prices[{i}]")
        sid = _security(row.get("security_id"), f"prices[{i}]")
        if sid in prices:
            raise DataContractError(f"PRIVATE_PRICE_DUPLICATE: {sid}.")
        prices[sid] = PriceQuote(sid, _dec(row.get("price"), f"price {sid}", positive=True),
                                 _date(row.get("as_of"), f"price {sid}"), _ccy(row.get("currency"), f"price {sid}"),
                                 _label(row.get("source_id"), f"price {sid} source", _LONG_DIGIT_RUN) or "")
        if row.get("published_at") is not None:
            stamp = _aware(row.get("published_at"), f"price {sid} published_at")
            if stamp > observed_at:
                raise DataContractError(f"PRIVATE_PRICE_PUBLISHED_AFTER_OBSERVATION: {sid}.")
            published[sid] = stamp.isoformat()

    classes: Dict[str, SecurityClass] = {}
    for i, raw in enumerate(top.get("securities") or []):
        row = _fields(raw, _SECURITY_FIELDS, f"securities[{i}]")
        sid = _security(row.get("security_id"), f"securities[{i}]")
        cls, method = row.get("classification"), row.get("methodology")
        evidence = _label(row.get("evidence_ref"), f"securities {sid} evidence_ref", _LONG_DIGIT_RUN)
        if sid in classes or cls not in TAXONOMY or method not in METHODOLOGIES:
            raise DataContractError(f"PRIVATE_CLASSIFICATION_INVALID: {sid}.")
        if method == "OWNER_DECLARED_WITH_EVIDENCE" and (evidence is None or cls in ("UNKNOWN", "CASH")):
            raise DataContractError(f"PRIVATE_CLASSIFICATION_EVIDENCE_REQUIRED: {sid}.")
        if method != "OWNER_DECLARED_WITH_EVIDENCE" and cls != "UNKNOWN":
            raise DataContractError(f"PRIVATE_CLASSIFICATION_WITHOUT_METHODOLOGY: {sid}.")
        classes[sid] = SecurityClass(sid, str(cls), str(method), evidence)

    accounts: List[AccountObservation] = []
    used_prices: Set[str] = set()
    for i, raw in enumerate(top.get("accounts") or []):
        accounts.append(_parse_account(raw, i, prices, used_prices))
    if not accounts:
        raise DataContractError("PRIVATE_NO_ACCOUNTS.")
    refs = [a.account_ref for a in accounts]
    if len(set(refs)) != len(refs):
        raise DataContractError("PRIVATE_DUPLICATE_ACCOUNT_REF.")
    unused = sorted(set(prices) - used_prices)
    if unused:
        raise DataContractError(f"PRIVATE_UNUSED_PRICE: {unused}.")
    unknown_class = sorted(set(classes) - used_prices)
    if unknown_class:
        raise DataContractError(f"PRIVATE_CLASSIFICATION_FOR_UNHELD_SECURITY: {unknown_class}.")
    for quote in prices.values():
        if quote.as_of != vdate:
            raise DataContractError(f"PRIVATE_PRICE_DATE_MISMATCH: {quote.symbol} must be dated valuation_date.")
    for rate in fx.values():
        if rate.as_of != vdate:
            raise DataContractError(f"PRIVATE_FX_DATE_MISMATCH: {rate.from_currency}->{rate.to_currency}.")

    return PortfolioSnapshot(
        data_class=str(data_class), snapshot_id=snapshot_id, observed_at=observed_at, valuation_date=vdate,
        evidence_source=str(source), reporting_currency=reporting, report_currencies=report_ccys,
        fx_rates=tuple(fx[k] for k in sorted(fx)), prices=tuple(prices[k] for k in sorted(prices)),
        published_at=tuple(sorted(published.items())),
        securities=tuple(classes[k] for k in sorted(classes)), accounts=tuple(sorted(accounts, key=lambda a: a.account_ref)),
        content_sha256=CanonicalConfigSerializer.compute_sha256(json.loads(json.dumps(doc, sort_keys=True))),
    )


def _optional_amount(prow: Mapping[str, Any], amount_key: str, ccy_key: str, ctx: str) -> Tuple[Optional[Decimal], Optional[str]]:
    amount, ccy = prow.get(amount_key), prow.get(ccy_key)
    if amount is None and ccy is None:
        return None, None
    if amount is None or ccy is None:
        raise DataContractError(f"PRIVATE_AMOUNT_CURRENCY_PAIR_INCOMPLETE: {ctx} {amount_key}.")
    return _dec(amount, f"{ctx} {amount_key}", nonnegative=True), _ccy(ccy, f"{ctx} {ccy_key}")


def _parse_account(raw: Any, index: int, prices: Mapping[str, PriceQuote], used: Set[str]) -> AccountObservation:
    row = _fields(raw, _ACCOUNT_FIELDS, f"accounts[{index}]")
    ref = _ref(row.get("account_ref"), f"accounts[{index}].account_ref")
    broker = _ref(row.get("broker"), f"{ref}.broker")
    role = row.get("role")
    if role not in ACCOUNT_ROLES:
        raise DataContractError(f"PRIVATE_ACCOUNT_ROLE_INVALID: {ref}.")
    base = _ccy(row.get("base_currency"), f"{ref}.base_currency")
    cash: List[CashLine] = []
    seen_cash: Set[Tuple[str, str, Optional[str]]] = set()
    for j, c in enumerate(row.get("cash") or []):
        crow = _fields(c, _CASH_FIELDS, f"{ref}.cash[{j}]")
        kind = crow.get("kind")
        if kind not in CASH_KINDS:
            raise DataContractError(f"PRIVATE_CASH_KIND_INVALID: {ref}.cash[{j}].")
        line = CashLine(ref, _ccy(crow.get("currency"), f"{ref}.cash[{j}]"),
                        _dec(crow.get("amount"), f"{ref}.cash[{j}]", nonnegative=True), str(kind),
                        _label(crow.get("sub_portfolio"), f"{ref}.cash[{j}].sub_portfolio"))
        key = (line.currency, line.kind, line.sub_portfolio)
        if key in seen_cash:
            raise DataContractError(f"PRIVATE_DUPLICATE_CASH_LINE: {ref}.cash[{j}].")
        seen_cash.add(key)
        cash.append(line)
    positions: List[PositionLine] = []
    seen_pos: Set[Tuple[str, Optional[str]]] = set()
    for j, p in enumerate(row.get("positions") or []):
        prow = _fields(p, _POSITION_FIELDS, f"{ref}.positions[{j}]")
        sid = _security(prow.get("security_id"), f"{ref}.positions[{j}]")
        if sid not in prices:
            raise DataContractError(f"PRIVATE_PRICE_MISSING: {sid}.")
        sub = _label(prow.get("sub_portfolio"), f"{ref}.positions[{j}].sub_portfolio")
        if (sid, sub) in seen_pos:
            raise DataContractError(f"PRIVATE_DUPLICATE_POSITION_LINE: {ref} {sid}.")
        seen_pos.add((sid, sub))
        cost, cost_ccy = _optional_amount(prow, "cost_basis_total", "cost_basis_currency", f"{ref} {sid}")
        observed, observed_ccy = _optional_amount(prow, "observed_market_value", "observed_market_value_currency", f"{ref} {sid}")
        positions.append(PositionLine(ref, sid, sub, _dec(prow.get("quantity"), f"{ref} {sid} quantity", positive=True),
                                      cost, cost_ccy, observed, observed_ccy))
        used.add(sid)
    if not cash and not positions:
        raise DataContractError(f"PRIVATE_EMPTY_ACCOUNT: {ref}.")
    return AccountObservation(ref, broker, str(role), base, tuple(cash), tuple(positions))


def load_snapshot(path: Path) -> PortfolioSnapshot:
    snapshot = parse_snapshot(read_bounded_json(Path(path), "PRIVATE_SNAPSHOT"))
    if snapshot.data_class == "OWNER_PRIVATE_OBSERVATION":
        assert_private_observation_authorized(snapshot.data_class)
        assert_private_location(Path(path))
    return snapshot


def assert_no_duplicate_snapshots(snapshots: Sequence[PortfolioSnapshot]) -> None:
    ids = [s.snapshot_id for s in snapshots]
    digests = [s.content_sha256 for s in snapshots]
    if len(set(ids)) != len(ids) or len(set(digests)) != len(digests):
        raise DataContractError("PRIVATE_DUPLICATE_SNAPSHOT: identical snapshot_id or content.")


@dataclass(frozen=True)
class ValuationPosition:
    """Quantity observed at the valuation date; deliberately carries no cost or acquisition date."""

    symbol: str
    quantity: Decimal
    currency: str


@dataclass(frozen=True)
class SnapshotValuationView:
    """Observation-to-valuation adapter satisfying ``ppds.exposure.ValuationSource``."""

    account_id: str
    as_of: date
    cash: Tuple[Tuple[str, Decimal], ...]
    position_lots: Tuple[ValuationPosition, ...]

    def cash_by_currency(self) -> Dict[str, Decimal]:
        totals: Dict[str, Decimal] = {}
        for currency, amount in self.cash:
            totals[currency] = totals.get(currency, ZERO) + amount
        return totals

    def quantity_by_symbol(self) -> Dict[str, Decimal]:
        totals: Dict[str, Decimal] = {}
        for lot in self.position_lots:
            totals[lot.symbol] = totals.get(lot.symbol, ZERO) + lot.quantity
        return totals

    @property
    def sha256(self) -> str:
        payload = {"account_id": self.account_id, "as_of": self.as_of.isoformat(),
                   "cash": [[c, str(a)] for c, a in self.cash],
                   "positions": [[p.symbol, str(p.quantity), p.currency] for p in self.position_lots]}
        return hashlib.sha256(CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")).hexdigest()


def _view(snapshot: PortfolioSnapshot, account: AccountObservation) -> SnapshotValuationView:
    prices = {p.symbol: p for p in snapshot.prices}
    return SnapshotValuationView(
        account_id=account.account_ref,
        as_of=snapshot.valuation_date,
        cash=tuple((c.currency, c.amount) for c in account.cash if c.kind == "SETTLED"),
        position_lots=tuple(ValuationPosition(p.security_id, p.quantity, prices[p.security_id].currency)
                            for p in account.positions),
    )


def _fx_map(snapshot: PortfolioSnapshot) -> Dict[Tuple[str, str], FXRate]:
    return {(r.from_currency, r.to_currency): r for r in snapshot.fx_rates}


def _rate(fx: Mapping[Tuple[str, str], FXRate], src: str, dst: str) -> Decimal:
    if src == dst:
        return Decimal("1")
    if (src, dst) not in fx:
        raise DataContractError(f"PRIVATE_FX_RATE_MISSING: {src}->{dst}.")
    return fx[(src, dst)].rate


@dataclass(frozen=True)
class PortfolioBook:
    snapshot: PortfolioSnapshot
    views: Dict[str, SnapshotValuationView]
    valuations: Dict[str, PortfolioValuation]
    consolidated: Dict[str, ConsolidatedPortfolioValuation]


def build_book(snapshot: PortfolioSnapshot) -> PortfolioBook:
    """Value every account with PPDS and consolidate into each report currency."""
    assert_private_observation_authorized(snapshot.data_class)
    fx = _fx_map(snapshot)
    prices = {p.symbol: p for p in snapshot.prices}
    views: Dict[str, SnapshotValuationView] = {}
    valuations: Dict[str, PortfolioValuation] = {}
    registry = AccountRegistry(portfolio_id=snapshot.snapshot_id)
    for account in snapshot.accounts:
        view = _view(snapshot, account)
        views[account.account_ref] = view
        valuations[account.account_ref] = evaluate_portfolio_base_currency(
            view, account.base_currency, snapshot.valuation_date, prices, fx)
        registry = registry.register(AccountRegistration(
            portfolio_id=snapshot.snapshot_id, account_id=account.account_ref, source_id=snapshot.snapshot_id,
            as_of=snapshot.valuation_date, base_currency=account.base_currency,
            evidence_refs=(f"{snapshot.snapshot_id}:{account.account_ref}:{snapshot.content_sha256[:16]}",),
        ))
    consolidated = {ccy: consolidate_portfolio_valuations(registry, valuations, ccy, fx) for ccy in snapshot.report_currencies}
    return PortfolioBook(snapshot, views, valuations, consolidated)


def _q(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _w(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001")))


def _position_values(book: PortfolioBook, ccy: str) -> List[Tuple[AccountObservation, PositionLine, Decimal, Decimal]]:
    """(account, line, local market value, reporting value) via the same PPDS FX path."""
    fx = _fx_map(book.snapshot)
    prices = {p.symbol: p for p in book.snapshot.prices}
    rows = []
    for account in book.snapshot.accounts:
        to_rep = _rate(fx, account.base_currency, ccy)
        for line in account.positions:
            quote = prices[line.security_id]
            local = line.quantity * quote.price
            rows.append((account, line, local, local * _rate(fx, quote.currency, account.base_currency) * to_rep))
    return rows


def _cash_values(book: PortfolioBook, ccy: str, kind: str) -> List[Tuple[AccountObservation, CashLine, Decimal]]:
    fx = _fx_map(book.snapshot)
    rows = []
    for account in book.snapshot.accounts:
        to_rep = _rate(fx, account.base_currency, ccy)
        for line in account.cash:
            if line.kind == kind:
                rows.append((account, line, line.amount * _rate(fx, line.currency, account.base_currency) * to_rep))
    return rows


def _classification(book: PortfolioBook, security_id: str) -> SecurityClass:
    for cls in book.snapshot.securities:
        if cls.security_id == security_id:
            return cls
    return SecurityClass(security_id, "UNKNOWN", "NOT_CLASSIFIED", None)


def reconciliation_checks(book: PortfolioBook) -> List[Dict[str, str]]:
    """Observed broker market value vs quantity x price, in the observed value's own currency.

    Tolerance comes from displayed precision: half a unit of the observed value's last digit plus
    quantity x half a unit of the price's last digit (converted at the snapshot rate when the
    currencies differ). A cross-currency comparison relies on the snapshot FX source, which may
    differ from the broker's display rate.
    """
    prices = {p.symbol: p for p in book.snapshot.prices}
    fx = _fx_map(book.snapshot)
    checks = []
    for account in book.snapshot.accounts:
        for line in account.positions:
            quote = prices[line.security_id]
            row = {"account_ref": account.account_ref, "security_id": line.security_id,
                   "sub_portfolio": line.sub_portfolio or "", "currency": line.observed_market_value_currency or "",
                   "difference": "", "tolerance": "", "tolerance_source": "DISPLAYED_PRECISION"}
            if line.observed_market_value is None or line.observed_market_value_currency is None:
                row["verdict"] = "NOT_DISPLAYED"
            elif (quote.currency != line.observed_market_value_currency
                  and (quote.currency, line.observed_market_value_currency) not in fx):
                row["verdict"] = "CURRENCY_CONVERSION_NOT_AVAILABLE"
            else:
                rate = _rate(fx, quote.currency, line.observed_market_value_currency)
                diff = line.observed_market_value - line.quantity * quote.price * rate
                bound = _half_unit(line.observed_market_value) + line.quantity * _half_unit(quote.price) * rate
                cross = quote.currency != line.observed_market_value_currency
                if abs(diff) <= bound:
                    row["verdict"] = "CONSISTENT_WITHIN_DISPLAY_ROUNDING"
                else:
                    row["verdict"] = "UNEXPLAINED_DIFFERENCE_FX_SOURCE_MAY_DIFFER" if cross else "UNEXPLAINED_DIFFERENCE"
                row["difference"], row["tolerance"] = str(diff), str(bound)
            checks.append(row)
    return sorted(checks, key=lambda r: (r["account_ref"], r["security_id"], r["sub_portfolio"]))


def _grouped(pairs: Sequence[Tuple[str, Decimal]], nav: Decimal) -> Dict[str, Dict[str, str]]:
    totals: Dict[str, Decimal] = {}
    for key, value in pairs:
        totals[key] = totals.get(key, ZERO) + value
    return {k: {"value": _q(v), "weight": _w(v / nav)} for k, v in sorted(totals.items())}


def _pnl(book: PortfolioBook, positions: Sequence[Tuple[AccountObservation, PositionLine, Decimal, Decimal]]) -> Dict[str, Any]:
    prices = {p.symbol: p for p in book.snapshot.prices}
    totals: Dict[str, Decimal] = {}
    lines: List[Dict[str, str]] = []
    known_value, all_value = ZERO, ZERO
    for account, line, local, rep in positions:
        quote_ccy = prices[line.security_id].currency
        all_value += rep
        if line.cost_basis_total is None:
            status = "COST_BASIS_UNKNOWN"
        elif line.cost_basis_currency != quote_ccy:
            status = "COST_CURRENCY_DIFFERS_PNL_NOT_ESTABLISHED"
        else:
            status = "OBSERVED_COST_BASIS"
            totals[quote_ccy] = totals.get(quote_ccy, ZERO) + local - line.cost_basis_total
            known_value += rep
        lines.append({"account_ref": account.account_ref, "security_id": line.security_id,
                      "sub_portfolio": line.sub_portfolio or "", "status": status})
    if known_value == ZERO:
        overall = "NAV_ONLY"
    elif known_value == all_value:
        overall = "OBSERVED_COST_BASIS"
    else:
        overall = "PARTIAL_COST_BASIS"
    return {
        "status": overall,
        "unrealized_pnl_security_currency_known_cost_subset": {k: _q(v) for k, v in sorted(totals.items())},
        "cost_basis_value_coverage": _w(known_value / all_value) if all_value > ZERO else "0.0000",
        "lines": sorted(lines, key=lambda r: (r["account_ref"], r["security_id"], r["sub_portfolio"])),
        "limitations": ["UNREALIZED_PNL_NOT_ESTABLISHED for COST_BASIS_UNKNOWN lines",
                        "FX_COMPONENT_NOT_ESTABLISHED", "ACQUISITION_HISTORY_NOT_ESTABLISHED"],
    }


def book_analytics(book: PortfolioBook, ccy: Optional[str] = None) -> Dict[str, Any]:
    """Allocation, concentration, P&L status and illustrative stress in one report currency."""
    ccy = ccy or book.snapshot.reporting_currency
    if ccy not in book.consolidated:
        raise DataContractError(f"PRIVATE_REPORT_CURRENCY_NOT_BUILT: {ccy}.")
    nav = book.consolidated[ccy].consolidated_nav
    if nav <= ZERO:
        raise DataContractError("PRIVATE_NAV_NONPOSITIVE: allocation weights undefined.")
    positions = _position_values(book, ccy)
    cash = _cash_values(book, ccy, "SETTLED")
    accrued = _cash_values(book, ccy, "ACCRUED_INTEREST")

    residual = sum((v for *_, v in positions), ZERO) + sum((v for *_, v in cash), ZERO) - nav
    if abs(residual) > CONSERVATION_TOLERANCE:
        raise DataContractError("PRIVATE_CONSERVATION_BREAK: line totals differ from PPDS NAV.")

    by_class = [(_classification(book, line.security_id).classification, v) for _, line, _, v in positions]
    by_class += [("CASH", v) for *_, v in cash]
    by_security: Dict[str, Decimal] = {}
    for _, line, _, v in positions:
        by_security[line.security_id] = by_security.get(line.security_id, ZERO) + v
    weights = sorted(((v / nav, k) for k, v in by_security.items()), reverse=True)
    sub_portfolios = [(f"{a.account_ref}/{line.sub_portfolio or '(unassigned)'}", v) for a, line, _, v in positions]
    sub_portfolios += [(f"{a.account_ref}/{line.sub_portfolio or '(account cash)'}", v) for a, line, v in cash]

    return {
        "report_currency": ccy,
        "nav": _q(nav),
        "nav_exact": str(nav),
        "settled_cash": _q(sum((v for *_, v in cash), ZERO)),
        "accrued_interest_excluded_from_nav": _q(sum((v for *_, v in accrued), ZERO)),
        "securities_value": _q(sum((v for *_, v in positions), ZERO)),
        "allocation_by_classification": _grouped(by_class, nav),
        "allocation_by_broker": _grouped([(a.broker, v) for a, _, _, v in positions] + [(a.broker, v) for a, _, v in cash], nav),
        "allocation_by_role": _grouped([(a.role, v) for a, _, _, v in positions] + [(a.role, v) for a, _, v in cash], nav),
        "allocation_by_sub_portfolio": _grouped(sub_portfolios, nav),
        "allocation_by_currency": {e.currency: {"value": _q(e.net_base_amount), "weight": _w(e.weight_of_nav)}
                                   for e in book.consolidated[ccy].currency_exposures},
        "concentration": {
            "basis": "DIRECT_HOLDINGS_ONLY",
            "look_through_status": "OVERLAP_NOT_ESTABLISHED",
            "underlying_holdings": "UNDERLYING_HOLDINGS_INCOMPLETE",
            "top_holdings": [{"security_id": k, "weight": _w(w)} for w, k in weights[:5]],
            "top1_weight": _w(weights[0][0]) if weights else "0.0000",
            "top5_weight": _w(sum((w for w, _ in weights[:5]), ZERO)),
            "hhi_securities_of_nav": _w(sum((w * w for w, _ in weights), ZERO)),
        },
        "unrealized_pnl": _pnl(book, positions),
        "stress_illustrative": _stress(book, ccy, nav, positions),
        "conservation_residual": str(residual),
    }


def _stress(book: PortfolioBook, ccy: str, nav: Decimal,
            positions: Sequence[Tuple[AccountObservation, PositionLine, Decimal, Decimal]]) -> Dict[str, Any]:
    securities = sum((v for *_, v in positions), ZERO)
    risky = sum((v for _, line, _, v in positions
                 if _classification(book, line.security_id).classification in ("THEMATIC", "SPECULATIVE")), ZERO)
    unknown = sum((v for _, line, _, v in positions
                   if _classification(book, line.security_id).classification == "UNKNOWN"), ZERO)
    foreign = sum((e.net_base_amount for e in book.consolidated[ccy].currency_exposures if e.currency != ccy), ZERO)
    deltas = {
        "EQUITY_DRAWDOWN_30": -Decimal("0.30") * securities,
        "THEMATIC_SPECULATIVE_DRAWDOWN_50": -Decimal("0.50") * risky,
        "REPORTING_CCY_APPRECIATION_10": -Decimal("0.10") * foreign,
        "REPORTING_CCY_DEPRECIATION_10": Decimal("0.10") * foreign,
    }
    return {
        "label": "ILLUSTRATIVE_NOT_FORECAST",
        "scenarios": [{"scenario": name, "definition": text, "nav_delta": _q(deltas[name]),
                       "nav_delta_share": _w(deltas[name] / nav)} for name, text in ILLUSTRATIVE_STRESS],
        "unknown_classified_value_excluded_from_thematic": _q(unknown),
        "not_evaluated": dict(STRESS_NOT_EVALUATED),
    }


def valuation_age_days(book: PortfolioBook, report_date: date) -> Dict[str, Any]:
    age = (report_date - book.snapshot.valuation_date).days
    if age < 0:
        raise DataContractError("PRIVATE_REPORT_DATE_BEFORE_VALUATION.")
    return {"valuation_age_days": age, "stale": age > STALE_AFTER_DAYS}


def time_alignment(snapshot: PortfolioSnapshot) -> Dict[str, Any]:
    return {
        "observed_at": snapshot.observed_at.isoformat(),
        "valuation_date": snapshot.valuation_date.isoformat(),
        "observation_lag_days": (snapshot.observed_at.date() - snapshot.valuation_date).days,
        "price_and_fx_dates": "SINGLE_VALUATION_DATE",
        "price_published_at": dict(snapshot.published_at),
        "market_session_calendar_check": "NOT_PERFORMED_NO_CALENDAR_AUTHORITY",
        "asynchronous_prices": "NOT_SUPPORTED_V1_1",
    }


def book_summary(book: PortfolioBook, report_date: Optional[date] = None) -> Dict[str, Any]:
    snap = book.snapshot
    freshness = valuation_age_days(book, report_date or snap.valuation_date)
    return {
        "schema": SCHEMA,
        "data_class": snap.data_class,
        "snapshot_id": snap.snapshot_id,
        "snapshot_content_sha256": snap.content_sha256,
        "valuation_date": snap.valuation_date.isoformat(),
        "time_alignment": time_alignment(snap),
        "evidence_source": snap.evidence_source,
        "support_state": "SNAPSHOT_ONLY",
        "performance_status": "PERFORMANCE_NOT_ESTABLISHED",
        "performance_reason": "SNAPSHOT_ONLY: no contribution, withdrawal or transfer history; TWR/XIRR undefined.",
        "stale_after_days": STALE_AFTER_DAYS,
        "valuation_age_days": freshness["valuation_age_days"],
        "valuation_stale": freshness["stale"],
        "accounts": [{"account_ref": a.account_ref, "broker": a.broker, "role": a.role, "base_currency": a.base_currency,
                      "valuation_view_sha256": book.views[a.account_ref].sha256} for a in snap.accounts],
        "fx_rates": [{"pair": f"{r.from_currency}->{r.to_currency}", "rate": str(r.rate), "source_id": r.source_id}
                     for r in snap.fx_rates],
        "classification_methodologies": dict(METHODOLOGIES),
        "governance": dict(GOVERNANCE_FLAGS),
        "reconciliation": reconciliation_checks(book),
        "analytics": {ccy: book_analytics(book, ccy) for ccy in snap.report_currencies},
    }
