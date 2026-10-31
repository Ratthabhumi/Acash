"""PPDS local-private observation path (read-only, offline, owner-controlled).

Trust boundary (docs/architecture/PRIVATE_PORTFOLIO_OBSERVATION_BOUNDARY.md):

- An owner snapshot is a personal decision-support observation. It is never
  D5 research data, never proof of acquisition history and never carries
  trading, transfer or capital authority.
- ``OWNER_PRIVATE_OBSERVATION`` files are only read from, and outputs only
  written to, locations outside the repository or under the git-ignored
  ``data/private/`` directory. Public fixtures must be ``SYNTHETIC_PUBLIC_FIXTURE``.
- Valuation reuses the PPDS ledger, account registry, base-currency valuation
  and consolidation. This module adds no second ledger and no FX inversion.
"""

from __future__ import annotations

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
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.lots import CashLot, PositionLot
from acash.ppds.registry import (
    AccountRegistration,
    AccountRegistry,
    ConsolidatedPortfolioValuation,
    consolidate_portfolio_valuations,
)

SCHEMA = "ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1"
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
# 28-digit Decimal context residual only; any economic break is at least one cent.
CONSERVATION_TOLERANCE = Decimal("1e-12")
DISPLAY_HALF_UNIT = Decimal("0.005")
STALE_AFTER_DAYS = 7
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
_TOP_FIELDS = {"schema", "data_class", "snapshot_id", "observed_at", "evidence_source", "reporting_currency",
               "report_currencies", "fx_rates", "prices", "securities", "accounts"}
_ACCOUNT_FIELDS = {"account_ref", "broker", "role", "base_currency", "cash", "positions"}
_CASH_FIELDS = {"currency", "amount", "kind", "sub_portfolio"}
_POSITION_FIELDS = {"security_id", "sub_portfolio", "quantity", "cost_basis_total", "observed_market_value"}
_FX_FIELDS = {"from", "to", "rate", "as_of", "source_id"}
_PRICE_FIELDS = {"security_id", "currency", "price", "as_of", "source_id"}
_SECURITY_FIELDS = {"security_id", "classification", "methodology", "evidence_ref"}
ZERO = Decimal("0")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def assert_private_location(path: Path, root: Optional[Path] = None) -> None:
    """Owner-private files must live outside the repository or under ``data/private/``."""
    resolved, base = Path(path).resolve(), (root or _repo_root()).resolve()
    try:
        rel = resolved.relative_to(base)
    except ValueError:
        return
    if rel.parts[:2] != ("data", "private"):
        raise DataContractError("PRIVATE_LOCATION_NOT_IGNORED: owner data must be outside the repo or under data/private/.")


def _fields(doc: Any, allowed: Set[str], ctx: str) -> Mapping[str, Any]:
    if not isinstance(doc, Mapping):
        raise DataContractError(f"PRIVATE_NOT_A_MAPPING: {ctx}.")
    unknown = set(doc) - allowed
    if unknown:
        raise DataContractError(f"PRIVATE_UNKNOWN_FIELDS: {ctx} {sorted(unknown)}.")
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
    observed_market_value: Optional[Decimal]


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
    evidence_source: str
    reporting_currency: str
    report_currencies: Tuple[str, ...]
    fx_rates: Tuple[FXRate, ...]
    prices: Tuple[PriceQuote, ...]
    securities: Tuple[SecurityClass, ...]
    accounts: Tuple[AccountObservation, ...]
    content_sha256: str

    @property
    def valuation_date(self) -> date:
        return self.observed_at.date()


def parse_snapshot(doc: Any) -> PortfolioSnapshot:
    """Validate a snapshot document; every amount is a decimal string, every field is known."""
    top = _fields(doc, _TOP_FIELDS, "snapshot")
    if top.get("schema") != SCHEMA:
        raise DataContractError(f"PRIVATE_SCHEMA_MISMATCH: expected {SCHEMA}.")
    data_class = top.get("data_class")
    if data_class not in DATA_CLASSES:
        raise DataContractError("PRIVATE_DATA_CLASS_INVALID.")
    snapshot_id = _ref(top.get("snapshot_id"), "snapshot_id")
    try:
        observed_at = datetime.fromisoformat(str(top.get("observed_at")))
    except ValueError as exc:
        raise DataContractError("PRIVATE_OBSERVED_AT_INVALID.") from exc
    if observed_at.tzinfo is None:
        raise DataContractError("PRIVATE_OBSERVED_AT_NAIVE: timezone offset required.")
    source = top.get("evidence_source")
    if source not in EVIDENCE_SOURCES:
        raise DataContractError("PRIVATE_EVIDENCE_SOURCE_INVALID.")
    reporting = _ccy(top.get("reporting_currency"), "reporting_currency")
    report_ccys = tuple(_ccy(c, "report_currencies") for c in top.get("report_currencies") or [reporting])
    if reporting not in report_ccys or len(set(report_ccys)) != len(report_ccys):
        raise DataContractError("PRIVATE_REPORT_CURRENCIES_INVALID: must be unique and include reporting_currency.")
    vdate = observed_at.date()

    fx: Dict[Tuple[str, str], FXRate] = {}
    for i, raw in enumerate(top.get("fx_rates") or []):
        row = _fields(raw, _FX_FIELDS, f"fx_rates[{i}]")
        key = (_ccy(row.get("from"), f"fx_rates[{i}].from"), _ccy(row.get("to"), f"fx_rates[{i}].to"))
        if key[0] == key[1] or key in fx:
            raise DataContractError(f"PRIVATE_FX_DUPLICATE_OR_IDENTITY: {key}.")
        fx[key] = FXRate(key[0], key[1], _dec(row.get("rate"), f"fx {key}", positive=True),
                         _date(row.get("as_of"), f"fx {key}"), _label(row.get("source_id"), f"fx {key} source", _LONG_DIGIT_RUN) or "")

    prices: Dict[str, PriceQuote] = {}
    for i, raw in enumerate(top.get("prices") or []):
        row = _fields(raw, _PRICE_FIELDS, f"prices[{i}]")
        sid = _security(row.get("security_id"), f"prices[{i}]")
        if sid in prices:
            raise DataContractError(f"PRIVATE_PRICE_DUPLICATE: {sid}.")
        prices[sid] = PriceQuote(sid, _dec(row.get("price"), f"price {sid}", positive=True),
                                 _date(row.get("as_of"), f"price {sid}"), _ccy(row.get("currency"), f"price {sid}"),
                                 _label(row.get("source_id"), f"price {sid} source", _LONG_DIGIT_RUN) or "")

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
            raise DataContractError(f"PRIVATE_PRICE_DATE_MISMATCH: {quote.symbol} must be dated {vdate.isoformat()}.")
    for rate in fx.values():
        if rate.as_of != vdate:
            raise DataContractError(f"PRIVATE_FX_DATE_MISMATCH: {rate.from_currency}->{rate.to_currency}.")

    return PortfolioSnapshot(
        data_class=str(data_class), snapshot_id=snapshot_id, observed_at=observed_at, evidence_source=str(source),
        reporting_currency=reporting, report_currencies=report_ccys,
        fx_rates=tuple(fx[k] for k in sorted(fx)), prices=tuple(prices[k] for k in sorted(prices)),
        securities=tuple(classes[k] for k in sorted(classes)), accounts=tuple(sorted(accounts, key=lambda a: a.account_ref)),
        content_sha256=CanonicalConfigSerializer.compute_sha256(json.loads(json.dumps(doc, sort_keys=True))),
    )


def _date(raw: Any, ctx: str) -> date:
    try:
        return date.fromisoformat(str(raw))
    except ValueError as exc:
        raise DataContractError(f"PRIVATE_DATE_INVALID: {ctx}.") from exc


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
        cost = prow.get("cost_basis_total")
        observed = prow.get("observed_market_value")
        positions.append(PositionLine(
            ref, sid, sub, _dec(prow.get("quantity"), f"{ref} {sid} quantity", positive=True),
            None if cost is None else _dec(cost, f"{ref} {sid} cost_basis_total", nonnegative=True),
            None if observed is None else _dec(observed, f"{ref} {sid} observed_market_value", nonnegative=True),
        ))
        used.add(sid)
    if not cash and not positions:
        raise DataContractError(f"PRIVATE_EMPTY_ACCOUNT: {ref}.")
    return AccountObservation(ref, broker, str(role), base, tuple(cash), tuple(positions))


def load_snapshot(path: Path) -> PortfolioSnapshot:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataContractError(f"PRIVATE_SNAPSHOT_UNREADABLE: {type(exc).__name__}.") from exc
    snapshot = parse_snapshot(doc)
    if snapshot.data_class == "OWNER_PRIVATE_OBSERVATION":
        assert_private_location(Path(path))
    return snapshot


def assert_no_duplicate_snapshots(snapshots: Sequence[PortfolioSnapshot]) -> None:
    ids = [s.snapshot_id for s in snapshots]
    digests = [s.content_sha256 for s in snapshots]
    if len(set(ids)) != len(ids) or len(set(digests)) != len(digests):
        raise DataContractError("PRIVATE_DUPLICATE_SNAPSHOT: identical snapshot_id or content.")


def _ledger(snapshot: PortfolioSnapshot, account: AccountObservation) -> NormalizedPortfolioLedger:
    """Snapshot lots: ``acquired_on`` is the OBSERVATION date; acquisition history is not established."""
    prices = {p.symbol: p for p in snapshot.prices}
    ledger = NormalizedPortfolioLedger(account_id=account.account_ref, as_of=snapshot.valuation_date)
    for c in account.cash:
        if c.kind == "SETTLED" and c.amount != ZERO:
            ledger = ledger.post_cash_lot(CashLot(c.currency, c.amount, snapshot.valuation_date))
    for p in account.positions:
        if p.cost_basis_total is None:
            raise DataContractError(f"PRIVATE_COST_BASIS_REQUIRED: {account.account_ref} {p.security_id}.")
        ledger = ledger.post_position_lot(PositionLot(
            p.security_id, p.quantity, p.cost_basis_total / p.quantity, snapshot.valuation_date, prices[p.security_id].currency,
        ))
    return ledger


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
    ledgers: Dict[str, NormalizedPortfolioLedger]
    valuations: Dict[str, PortfolioValuation]
    consolidated: Dict[str, ConsolidatedPortfolioValuation]


def build_book(snapshot: PortfolioSnapshot) -> PortfolioBook:
    """Value every account with PPDS and consolidate into each report currency."""
    fx = _fx_map(snapshot)
    prices = {p.symbol: p for p in snapshot.prices}
    ledgers, valuations = {}, {}
    registry = AccountRegistry(portfolio_id=snapshot.snapshot_id)
    for account in snapshot.accounts:
        ledger = _ledger(snapshot, account)
        ledgers[account.account_ref] = ledger
        valuations[account.account_ref] = evaluate_portfolio_base_currency(
            ledger, account.base_currency, snapshot.valuation_date, prices, fx)
        registry = registry.register(AccountRegistration(
            portfolio_id=snapshot.snapshot_id, account_id=account.account_ref, source_id=snapshot.snapshot_id,
            as_of=snapshot.valuation_date, base_currency=account.base_currency,
            evidence_refs=(f"{snapshot.snapshot_id}:{account.account_ref}:{snapshot.content_sha256[:16]}",),
        ))
    consolidated = {ccy: consolidate_portfolio_valuations(registry, valuations, ccy, fx) for ccy in snapshot.report_currencies}
    return PortfolioBook(snapshot, ledgers, valuations, consolidated)


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
    """Observed broker market value vs quantity x price (display-rounding bound assumes 2-dp display)."""
    prices = {p.symbol: p for p in book.snapshot.prices}
    checks = []
    for account in book.snapshot.accounts:
        for line in account.positions:
            computed = line.quantity * prices[line.security_id].price
            if line.observed_market_value is None:
                verdict, diff = "NOT_DISPLAYED", None
            else:
                diff = line.observed_market_value - computed
                bound = DISPLAY_HALF_UNIT + line.quantity * DISPLAY_HALF_UNIT
                verdict = "CONSISTENT_WITHIN_DISPLAY_ROUNDING" if abs(diff) <= bound else "UNEXPLAINED_DIFFERENCE"
            checks.append({"account_ref": account.account_ref, "security_id": line.security_id,
                           "sub_portfolio": line.sub_portfolio or "", "verdict": verdict,
                           "difference_local": "" if diff is None else str(diff)})
    return checks


def _grouped(pairs: Sequence[Tuple[str, Decimal]], nav: Decimal) -> Dict[str, Dict[str, str]]:
    totals: Dict[str, Decimal] = {}
    for key, value in pairs:
        totals[key] = totals.get(key, ZERO) + value
    return {k: {"value": _q(v), "weight": _w(v / nav)} for k, v in sorted(totals.items())}


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
        raise DataContractError(f"PRIVATE_CONSERVATION_BREAK: line totals differ from PPDS NAV by {residual}.")

    by_class = [(_classification(book, line.security_id).classification, v) for _, line, _, v in positions]
    by_class += [("CASH", v) for *_, v in cash]
    by_security: Dict[str, Decimal] = {}
    for _, line, _, v in positions:
        by_security[line.security_id] = by_security.get(line.security_id, ZERO) + v
    weights = sorted(((v / nav, k) for k, v in by_security.items()), reverse=True)
    sub_portfolios = [(f"{a.account_ref}/{line.sub_portfolio or '(unassigned)'}", v) for a, line, _, v in positions]
    sub_portfolios += [(f"{a.account_ref}/{line.sub_portfolio or '(account cash)'}", v) for a, line, v in cash]

    pnl: Dict[str, Decimal] = {}
    for _, line, local, _ in positions:
        quote_ccy = next(p.currency for p in book.snapshot.prices if p.symbol == line.security_id)
        assert line.cost_basis_total is not None
        pnl[quote_ccy] = pnl.get(quote_ccy, ZERO) + local - line.cost_basis_total

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
        "unrealized_pnl_security_currency": {k: _q(v) for k, v in sorted(pnl.items())},
        "unrealized_pnl_status": "OBSERVED_COST_BASIS; FX_COMPONENT_NOT_ESTABLISHED; ACQUISITION_HISTORY_NOT_ESTABLISHED",
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


def book_summary(book: PortfolioBook, report_date: Optional[date] = None) -> Dict[str, Any]:
    snap = book.snapshot
    freshness = valuation_age_days(book, report_date or snap.valuation_date)
    return {
        "schema": SCHEMA,
        "data_class": snap.data_class,
        "snapshot_id": snap.snapshot_id,
        "snapshot_content_sha256": snap.content_sha256,
        "observed_at": snap.observed_at.isoformat(),
        "valuation_date": snap.valuation_date.isoformat(),
        "evidence_source": snap.evidence_source,
        "support_state": "SNAPSHOT_ONLY",
        "performance_status": "PERFORMANCE_NOT_ESTABLISHED",
        "performance_reason": "SNAPSHOT_ONLY: no contribution, withdrawal or transfer history; TWR/XIRR undefined.",
        "stale_after_days": STALE_AFTER_DAYS,
        "valuation_age_days": freshness["valuation_age_days"],
        "valuation_stale": freshness["stale"],
        "accounts": [{"account_ref": a.account_ref, "broker": a.broker, "role": a.role, "base_currency": a.base_currency,
                      "ledger_head_sha256": book.ledgers[a.account_ref].head_sha256,
                      "ledger_entry_count": book.ledgers[a.account_ref].entry_count} for a in snap.accounts],
        "fx_rates": [{"pair": f"{r.from_currency}->{r.to_currency}", "rate": str(r.rate), "source_id": r.source_id}
                     for r in snap.fx_rates],
        "classification_methodologies": dict(METHODOLOGIES),
        "governance": dict(GOVERNANCE_FLAGS),
        "reconciliation": reconciliation_checks(book),
        "analytics": {ccy: book_analytics(book, ccy) for ccy in snap.report_currencies},
    }


def valuation_age_days(book: PortfolioBook, report_date: date) -> Dict[str, Any]:
    age = (report_date - book.snapshot.valuation_date).days
    if age < 0:
        raise DataContractError("PRIVATE_REPORT_DATE_BEFORE_VALUATION.")
    return {"valuation_age_days": age, "stale": age > STALE_AFTER_DAYS}
