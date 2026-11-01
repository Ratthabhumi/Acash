"""PPDS canonical transaction accounting V2 (read-only, offline, broker-neutral).

Transactions are replayed into a derived state (cash, FIFO lots, realized P&L,
income and external flows). The state is valued through the same PPDS
``ValuationSource`` path as snapshots and exports to ``NormalizedPortfolioLedger``
only when full cost history exists, so there is still one book of record.

Not modelled (rejected): accrued interest, generic corporate actions and
security transfers. No native broker format is claimed; adapters map into
``ACASH_CANONICAL_TRANSACTIONS_V1`` only after a real export is documented.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Sequence, Set, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.lots import CashLot, PositionLot
from acash.ppds.private_observation import (
    DATA_CLASSES,
    PortfolioSnapshot,
    SnapshotValuationView,
    ValuationPosition,
    _ccy,
    _date,
    _dec,
    _fields,
    _half_unit,
    _label,
    _ref,
    _security,
    _LONG_DIGIT_RUN,
    assert_private_location,
    assert_private_observation_authorized,
    read_bounded_json,
)

SCHEMA = "ACASH_CANONICAL_TRANSACTIONS_V1"
LOT_METHOD = "FIFO_COST_INCLUDES_COMMISSION_FEES_AND_TAX"
LOT_METHOD_NOTE = "Analytical accounting assumption; not a jurisdictional tax method."
UNSUPPORTED = {
    "INTEREST_ACCRUED": "Non-cash accrual; report on snapshots as ACCRUED_INTEREST.",
    "CORPORATE_ACTION": "Generic corporate actions need an evidence-specific model.",
    "SECURITY_TRANSFER": "In-kind transfers need a cost-carryover model.",
}
ZERO = Decimal("0")
_COMMON_REQ = frozenset({"account_ref", "event_type", "trade_date"})
_COMMON_OPT = frozenset({"transaction_id", "sequence", "source_document_ref", "settlement_date"})
_TRADE = frozenset({"security_id", "quantity", "price", "gross_amount", "currency", "net_cash"})
_TRADE_OPT = frozenset({"commission", "fees", "tax"})
_CASH = frozenset({"currency", "net_cash"})
_SEC_CASH = frozenset({"security_id", "currency", "net_cash"})
# event -> (required, optional, net_cash sign)
RULES: Dict[str, Tuple[FrozenSet[str], FrozenSet[str], str]] = {
    "BUY": (_TRADE, _TRADE_OPT, "NEG"),
    "SELL": (_TRADE, _TRADE_OPT, "POS"),
    "DEPOSIT": (_CASH, frozenset(), "POS"),
    "WITHDRAWAL": (_CASH, frozenset(), "NEG"),
    "INTERNAL_TRANSFER": (_CASH | {"transfer_group_id"}, frozenset(), "NONZERO"),
    "FX_CONVERSION": (frozenset({"fx_from_currency", "fx_from_amount", "fx_to_currency", "fx_to_amount"}), frozenset(), "NONE"),
    "DIVIDEND": (_SEC_CASH, frozenset(), "POS"),
    "DIVIDEND_WITHHOLDING": (_SEC_CASH, frozenset(), "NEG"),
    "INTEREST_PAID": (_CASH, frozenset(), "POS"),
    "FEE": (_CASH, frozenset(), "NEG"),
    "TAX": (_CASH, frozenset(), "NEG"),
    "STOCK_SPLIT": (frozenset({"security_id", "split_ratio"}), frozenset(), "NONE"),
    "OPENING_CASH": (_CASH, frozenset(), "POS"),
    "OPENING_POSITION": (frozenset({"security_id", "quantity", "currency"}), frozenset({"cost_basis_total"}), "NONE"),
}
EVENT_TYPES = tuple(RULES)
_RANK = {"OPENING_CASH": 0, "OPENING_POSITION": 0, "STOCK_SPLIT": 1, "DEPOSIT": 2, "INTERNAL_TRANSFER": 2,
         "FX_CONVERSION": 3, "BUY": 4, "SELL": 4, "DIVIDEND": 5, "DIVIDEND_WITHHOLDING": 5, "INTEREST_PAID": 5,
         "FEE": 6, "TAX": 6, "WITHDRAWAL": 7}
_DECIMALS = ("quantity", "price", "gross_amount", "commission", "fees", "tax", "net_cash", "fx_from_amount",
             "fx_to_amount", "split_ratio", "cost_basis_total")
_ALL_FIELDS = set(_COMMON_REQ | _COMMON_OPT) | {f for req, opt, _ in RULES.values() for f in req | opt}


@dataclass(frozen=True)
class Transaction:
    key: str
    account_ref: str
    event_type: str
    trade_date: date
    settlement_date: Optional[date] = None
    security_id: Optional[str] = None
    currency: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    gross_amount: Optional[Decimal] = None
    commission: Decimal = ZERO
    fees: Decimal = ZERO
    tax: Decimal = ZERO
    net_cash: Optional[Decimal] = None
    fx_from_currency: Optional[str] = None
    fx_from_amount: Optional[Decimal] = None
    fx_to_currency: Optional[str] = None
    fx_to_amount: Optional[Decimal] = None
    transfer_group_id: Optional[str] = None
    split_ratio: Optional[Decimal] = None
    cost_basis_total: Optional[Decimal] = None
    source_document_ref: Optional[str] = None
    fingerprint: str = ""

    @property
    def cash_date(self) -> date:
        return self.settlement_date or self.trade_date

    @property
    def order_key(self) -> Tuple[date, int, str]:
        return (self.trade_date, _RANK[self.event_type], self.key)


def _fingerprint(row: Mapping[str, Any]) -> str:
    payload = {k: row[k] for k in sorted(row) if k != "transaction_id"}
    return CanonicalConfigSerializer.compute_sha256(payload)


def parse_transaction(raw: Any, index: int) -> Transaction:
    row = _fields(raw, _ALL_FIELDS, f"transactions[{index}]")
    row = {k: v for k, v in row.items() if v is not None}
    event = row.get("event_type")
    if event in UNSUPPORTED:
        raise DataContractError(f"TXN_EVENT_NOT_SUPPORTED_V2: {event}.")
    if event not in RULES:
        raise DataContractError(f"TXN_EVENT_TYPE_INVALID: transactions[{index}].")
    required, optional, sign = RULES[str(event)]
    missing = (required | _COMMON_REQ) - set(row)
    extra = set(row) - required - optional - _COMMON_REQ - _COMMON_OPT
    if missing or extra:
        raise DataContractError(f"TXN_FIELDS_INVALID: transactions[{index}] {event} missing {sorted(missing)} extra {sorted(extra)}.")
    ctx = f"transactions[{index}]"
    values: Dict[str, Any] = {}
    for name in _DECIMALS:
        if name in row:
            values[name] = _dec(row[name], f"{ctx}.{name}")
    for name in ("quantity", "price", "gross_amount", "fx_from_amount", "fx_to_amount", "split_ratio"):
        if name in values and values[name] <= ZERO:
            raise DataContractError(f"TXN_NONPOSITIVE_VALUE: {ctx}.{name}.")
    for name in ("commission", "fees", "tax", "cost_basis_total"):
        if name in values and values[name] < ZERO:
            raise DataContractError(f"TXN_NEGATIVE_VALUE: {ctx}.{name}.")
    net = values.get("net_cash")
    if (sign == "NEG" and not (net is not None and net < ZERO)) or (sign == "POS" and not (net is not None and net > ZERO)) \
            or (sign == "NONZERO" and not (net is not None and net != ZERO)):
        raise DataContractError(f"TXN_NET_CASH_SIGN_INVALID: {ctx} {event}.")
    trade_date = _date(row["trade_date"], f"{ctx}.trade_date")
    settlement = _date(row["settlement_date"], f"{ctx}.settlement_date") if "settlement_date" in row else None
    if settlement is not None and settlement < trade_date:
        raise DataContractError(f"TXN_SETTLEMENT_BEFORE_TRADE: {ctx}.")
    sequence = row.get("sequence")
    if sequence is not None and (not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0):
        raise DataContractError(f"TXN_SEQUENCE_INVALID: {ctx}.")
    fingerprint = _fingerprint(row)
    txn = Transaction(
        key=_ref(row["transaction_id"], f"{ctx}.transaction_id") if "transaction_id" in row else f"FP_{fingerprint[:24].upper()}",
        account_ref=_ref(row["account_ref"], f"{ctx}.account_ref"),
        event_type=str(event), trade_date=trade_date, settlement_date=settlement,
        security_id=_security(row["security_id"], ctx) if "security_id" in row else None,
        currency=_ccy(row["currency"], ctx) if "currency" in row else None,
        fx_from_currency=_ccy(row["fx_from_currency"], ctx) if "fx_from_currency" in row else None,
        fx_to_currency=_ccy(row["fx_to_currency"], ctx) if "fx_to_currency" in row else None,
        transfer_group_id=_ref(row["transfer_group_id"], f"{ctx}.transfer_group_id") if "transfer_group_id" in row else None,
        source_document_ref=_label(row.get("source_document_ref"), f"{ctx}.source_document_ref", _LONG_DIGIT_RUN),
        fingerprint=fingerprint, **values,
    )
    if txn.event_type == "FX_CONVERSION" and txn.fx_from_currency == txn.fx_to_currency:
        raise DataContractError(f"TXN_FX_SAME_CURRENCY: {ctx}.")
    if txn.event_type in ("BUY", "SELL"):
        _check_trade(txn, ctx)
    return txn


def _check_trade(txn: Transaction, ctx: str) -> None:
    assert txn.quantity is not None and txn.price is not None and txn.gross_amount is not None and txn.net_cash is not None
    bound = _half_unit(txn.gross_amount) + txn.quantity * _half_unit(txn.price)
    if abs(txn.gross_amount - txn.quantity * txn.price) > bound:
        raise DataContractError(f"TXN_GROSS_INCONSISTENT_WITH_QUANTITY_PRICE: {ctx}.")
    costs = txn.commission + txn.fees + txn.tax
    expected = -(txn.gross_amount + costs) if txn.event_type == "BUY" else txn.gross_amount - costs
    if txn.net_cash != expected:
        raise DataContractError(f"TXN_NET_CASH_INCONSISTENT: {ctx} {txn.event_type}.")


@dataclass(frozen=True)
class TransactionBatch:
    data_class: str
    batch_id: str
    transactions: Tuple[Transaction, ...]
    content_sha256: str


def parse_batch(doc: Any) -> TransactionBatch:
    top = _fields(doc, {"schema", "data_class", "batch_id", "transactions"}, "batch")
    if top.get("schema") != SCHEMA:
        raise DataContractError(f"TXN_SCHEMA_MISMATCH: expected {SCHEMA}.")
    if top.get("data_class") not in DATA_CLASSES:
        raise DataContractError("TXN_DATA_CLASS_INVALID.")
    raw = top.get("transactions")
    if not isinstance(raw, list) or not raw:
        raise DataContractError("TXN_BATCH_EMPTY.")
    txns = [parse_transaction(r, i) for i, r in enumerate(raw)]
    keys = [t.key for t in txns]
    if len(set(keys)) != len(keys):
        raise DataContractError("TXN_DUPLICATE_IN_BATCH: repeated transaction_id or identical record without sequence.")
    return TransactionBatch(str(top["data_class"]), _ref(top.get("batch_id"), "batch_id"),
                            tuple(sorted(txns, key=lambda t: t.order_key)),
                            CanonicalConfigSerializer.compute_sha256(doc))


def load_batch(path: Path) -> TransactionBatch:
    batch = parse_batch(read_bounded_json(Path(path), "TXN_BATCH"))
    if batch.data_class == "OWNER_PRIVATE_OBSERVATION":
        assert_private_observation_authorized(batch.data_class)
        assert_private_location(Path(path))
    return batch


def import_preview(existing: Sequence[Transaction], batch: TransactionBatch) -> Dict[str, Any]:
    known = {t.key: t for t in existing}
    new = [t.key for t in batch.transactions if t.key not in known]
    same = [t.key for t in batch.transactions if t.key in known and known[t.key] == t]
    conflicts = [t.key for t in batch.transactions if t.key in known and known[t.key] != t]
    return {"batch_id": batch.batch_id, "new": len(new), "already_imported": len(same), "conflicts": sorted(conflicts)}


def merge_batches(batches: Sequence[TransactionBatch]) -> Tuple[Transaction, ...]:
    """Idempotent merge: identical records are imported once; conflicting records fail closed."""
    if not batches:
        raise DataContractError("TXN_NO_BATCHES.")
    if len({b.data_class for b in batches}) != 1:
        raise DataContractError("TXN_DATA_CLASS_MIXED: synthetic and owner-private records cannot be merged.")
    merged: Dict[str, Transaction] = {}
    for batch in batches:
        for txn in batch.transactions:
            if txn.key in merged and merged[txn.key] != txn:
                raise DataContractError(f"TXN_ID_CONFLICT: {txn.key}.")
            merged[txn.key] = txn
    return tuple(sorted(merged.values(), key=lambda t: t.order_key))


@dataclass(frozen=True)
class Lot:
    quantity: Decimal
    cost_total: Optional[Decimal]
    currency: str
    acquired_on: Optional[date]
    origin: str


@dataclass(frozen=True)
class LedgerState:
    as_of: date
    cash: Dict[Tuple[str, str], Decimal]
    pending_cash: Dict[Tuple[str, str], Decimal]
    lots: Dict[Tuple[str, str], Tuple[Lot, ...]]
    realized: Tuple[Dict[str, str], ...]
    income: Dict[str, Dict[str, Decimal]]
    external_flows: Tuple[Tuple[date, str, str, Decimal], ...]
    opening_balances: Tuple[str, ...]
    history_start: date
    transaction_count: int = 0
    unknown_cost_positions: Tuple[str, ...] = field(default_factory=tuple)


def _validate_transfers(txns: Sequence[Transaction]) -> None:
    groups: Dict[str, List[Transaction]] = {}
    for t in txns:
        if t.event_type == "INTERNAL_TRANSFER":
            assert t.transfer_group_id is not None
            groups.setdefault(t.transfer_group_id, []).append(t)
    for gid, legs in sorted(groups.items()):
        nets = [leg.net_cash for leg in legs]
        if (len(legs) != 2 or legs[0].account_ref == legs[1].account_ref or legs[0].currency != legs[1].currency
                or sum((n for n in nets if n is not None), ZERO) != ZERO):
            raise DataContractError(f"TXN_TRANSFER_UNBALANCED: group {gid} needs two opposite equal legs in distinct accounts.")


def replay(txns: Sequence[Transaction], as_of: date) -> LedgerState:
    """Deterministic replay: positions move on trade date, cash on settlement date."""
    if not txns:
        raise DataContractError("TXN_NO_TRANSACTIONS.")
    _validate_transfers(txns)
    ordered = sorted(txns, key=lambda t: t.order_key)
    lots: Dict[Tuple[str, str], List[Lot]] = {}
    realized: List[Dict[str, str]] = []
    income: Dict[str, Dict[str, Decimal]] = {}
    openings: List[str] = []
    dividends: Set[Tuple[str, str, date]] = set()

    def book(bucket: str, ccy: str, amount: Decimal) -> None:
        income.setdefault(bucket, {})
        income[bucket][ccy] = income[bucket].get(ccy, ZERO) + amount

    for t in ordered:
        if t.trade_date > as_of:
            continue
        key = (t.account_ref, t.security_id or "")
        if t.event_type in ("BUY", "OPENING_POSITION"):
            assert t.quantity is not None and t.currency is not None
            if t.event_type == "BUY":
                assert t.gross_amount is not None
                lot = Lot(t.quantity, t.gross_amount + t.commission + t.fees + t.tax, t.currency, t.trade_date, "TRANSACTION")
            else:
                lot = Lot(t.quantity, t.cost_basis_total, t.currency, None, "OPENING")
                openings.append(f"{t.account_ref}:{t.security_id}")
            existing = lots.setdefault(key, [])
            if existing and existing[0].currency != lot.currency:
                raise DataContractError(f"TXN_POSITION_CURRENCY_CONFLICT: {t.key}.")
            existing.append(lot)
        elif t.event_type == "SELL":
            realized.append(_sell(lots.setdefault(key, []), t))
        elif t.event_type == "STOCK_SPLIT":
            assert t.split_ratio is not None
            if not lots.get(key):
                raise DataContractError(f"TXN_SPLIT_WITHOUT_POSITION: {t.key}.")
            lots[key] = [replace(lot, quantity=lot.quantity * t.split_ratio) for lot in lots[key]]
        elif t.event_type == "OPENING_CASH":
            openings.append(f"{t.account_ref}:{t.currency}")
        if t.event_type == "DIVIDEND":
            marker = (t.account_ref, t.security_id or "", t.trade_date)
            if marker in dividends:
                raise DataContractError(f"TXN_DIVIDEND_DOUBLE_COUNT_SUSPECTED: {t.key}.")
            dividends.add(marker)
        if t.event_type in ("BUY", "SELL") and t.currency:
            for bucket, amount in (("COMMISSION", t.commission), ("FEE", t.fees), ("TAX", t.tax)):
                if amount:
                    book(bucket, t.currency, amount)
        elif t.event_type in ("DIVIDEND", "DIVIDEND_WITHHOLDING", "INTEREST_PAID", "FEE", "TAX") and t.currency:
            assert t.net_cash is not None
            book(t.event_type, t.currency, abs(t.net_cash))

    cash, pending, flows = _cash_pass(ordered, as_of)
    clean_lots = {k: tuple(v) for k, v in sorted(lots.items()) if v}
    unknown = tuple(sorted(f"{a}:{s}" for (a, s), v in clean_lots.items() if any(l.cost_total is None for l in v)))
    return LedgerState(
        as_of=as_of, cash=cash, pending_cash=pending, lots=clean_lots, realized=tuple(realized), income=income,
        external_flows=flows, opening_balances=tuple(sorted(openings)), history_start=ordered[0].trade_date,
        transaction_count=sum(1 for t in ordered if t.trade_date <= as_of), unknown_cost_positions=unknown,
    )


def _sell(held: List[Lot], t: Transaction) -> Dict[str, str]:
    assert t.quantity is not None and t.gross_amount is not None and t.currency is not None
    remaining, cost, cost_known = t.quantity, ZERO, True
    if sum((lot.quantity for lot in held), ZERO) < t.quantity:
        raise DataContractError(f"TXN_POSITION_OVERSOLD: {t.key}.")
    while remaining > ZERO:
        lot = held[0]
        take = min(remaining, lot.quantity)
        if lot.cost_total is None or lot.currency != t.currency:
            cost_known = False
        else:
            cost += lot.cost_total * take / lot.quantity
        if take == lot.quantity:
            held.pop(0)
        else:
            held[0] = replace(lot, quantity=lot.quantity - take,
                              cost_total=None if lot.cost_total is None else lot.cost_total * (lot.quantity - take) / lot.quantity)
        remaining -= take
    proceeds = t.gross_amount - t.commission - t.fees - t.tax
    return {"transaction": t.key, "account_ref": t.account_ref, "security_id": t.security_id or "", "currency": t.currency,
            "trade_date": t.trade_date.isoformat(), "status": "REALIZED" if cost_known else "REALIZED_PNL_NOT_ESTABLISHED",
            "realized_pnl": str(proceeds - cost) if cost_known else ""}


def _cash_pass(ordered: Sequence[Transaction], as_of: date) -> Tuple[
        Dict[Tuple[str, str], Decimal], Dict[Tuple[str, str], Decimal], Tuple[Tuple[date, str, str, Decimal], ...]]:
    cash: Dict[Tuple[str, str], Decimal] = {}
    pending: Dict[Tuple[str, str], Decimal] = {}
    flows: List[Tuple[date, str, str, Decimal]] = []
    for t in sorted(ordered, key=lambda t: (t.cash_date, _RANK[t.event_type], t.key)):
        if t.trade_date > as_of:
            continue
        moves: List[Tuple[str, Decimal]] = []
        if t.event_type == "FX_CONVERSION":
            assert t.fx_from_currency and t.fx_to_currency and t.fx_from_amount is not None and t.fx_to_amount is not None
            moves = [(t.fx_from_currency, -t.fx_from_amount), (t.fx_to_currency, t.fx_to_amount)]
        elif t.net_cash is not None and t.currency is not None:
            moves = [(t.currency, t.net_cash)]
        target = cash if t.cash_date <= as_of else pending
        for ccy, amount in moves:
            k = (t.account_ref, ccy)
            target[k] = target.get(k, ZERO) + amount
            if target is cash and cash[k] < ZERO:
                raise DataContractError(f"TXN_CASH_NEGATIVE: {t.account_ref} {ccy} on {t.cash_date.isoformat()}.")
        if t.event_type in ("DEPOSIT", "WITHDRAWAL") and t.cash_date <= as_of:
            assert t.currency is not None and t.net_cash is not None
            flows.append((t.cash_date, t.account_ref, t.currency, t.net_cash))
    return dict(sorted(cash.items())), dict(sorted(pending.items())), tuple(flows)


def quantities(state: LedgerState) -> Dict[Tuple[str, str], Decimal]:
    return {k: sum((lot.quantity for lot in v), ZERO) for k, v in state.lots.items()}


def valuation_view(state: LedgerState, account_ref: str) -> SnapshotValuationView:
    """Value replayed holdings through the PPDS ``ValuationSource`` path."""
    return SnapshotValuationView(
        account_id=account_ref, as_of=state.as_of,
        cash=tuple((ccy, amt) for (acct, ccy), amt in state.cash.items() if acct == account_ref and amt != ZERO),
        position_lots=tuple(ValuationPosition(sec, sum((l.quantity for l in lots), ZERO), lots[0].currency)
                            for (acct, sec), lots in state.lots.items() if acct == account_ref),
    )


def to_ppds_ledger(state: LedgerState, account_ref: str) -> NormalizedPortfolioLedger:
    """Export one account to the PPDS ledger; requires complete cost and acquisition history."""
    ledger = NormalizedPortfolioLedger(account_id=account_ref, as_of=state.as_of)
    for (acct, ccy), amount in state.cash.items():
        if acct == account_ref and amount != ZERO:
            ledger = ledger.post_cash_lot(CashLot(ccy, amount, state.as_of))
    for (acct, sec), lots in state.lots.items():
        if acct != account_ref:
            continue
        for lot in lots:
            if lot.cost_total is None or lot.acquired_on is None:
                raise DataContractError(f"TXN_LEDGER_EXPORT_REQUIRES_FULL_COST_HISTORY: {acct}:{sec}.")
            ledger = ledger.post_position_lot(PositionLot(sec, lot.quantity, lot.cost_total / lot.quantity, lot.acquired_on, lot.currency))
    return ledger


def reconcile_with_snapshot(state: LedgerState, snapshot: PortfolioSnapshot) -> Dict[str, Any]:
    """Compare replayed quantities and settled cash with an observed snapshot at the same valuation date."""
    if state.as_of != snapshot.valuation_date:
        raise DataContractError("TXN_RECONCILE_DATE_MISMATCH: replay as_of must equal snapshot valuation_date.")
    snap_qty: Dict[Tuple[str, str], Decimal] = {}
    snap_cash: Dict[Tuple[str, str], Decimal] = {}
    for account in snapshot.accounts:
        for p in account.positions:
            snap_qty[(account.account_ref, p.security_id)] = snap_qty.get((account.account_ref, p.security_id), ZERO) + p.quantity
        for c in account.cash:
            if c.kind == "SETTLED":
                snap_cash[(account.account_ref, c.currency)] = snap_cash.get((account.account_ref, c.currency), ZERO) + c.amount
    breaks: List[Dict[str, str]] = []
    replay_qty = quantities(state)
    for key in sorted(set(replay_qty) | set(snap_qty)):
        if replay_qty.get(key, ZERO) != snap_qty.get(key, ZERO):
            breaks.append({"scope": "POSITION", "key": f"{key[0]}:{key[1]}", "status": "QUANTITY_BREAK",
                           "difference": str(replay_qty.get(key, ZERO) - snap_qty.get(key, ZERO))})
    for key in sorted(set(state.cash) | set(snap_cash)):
        observed = snap_cash.get(key, ZERO)
        diff = state.cash.get(key, ZERO) - observed
        if abs(diff) > (_half_unit(observed) if key in snap_cash else ZERO):
            breaks.append({"scope": "CASH", "key": f"{key[0]}:{key[1]}", "status": "CASH_BREAK", "difference": str(diff)})
    txn_accounts = {k[0] for k in state.cash} | {k[0] for k in state.lots}
    snap_accounts = {a.account_ref for a in snapshot.accounts}
    for acct in sorted(snap_accounts - txn_accounts):
        breaks.append({"scope": "ACCOUNT", "key": acct, "status": "ACCOUNT_WITHOUT_TRANSACTIONS", "difference": ""})
    for acct in sorted(txn_accounts - snap_accounts):
        breaks.append({"scope": "ACCOUNT", "key": acct, "status": "ACCOUNT_NOT_IN_SNAPSHOT", "difference": ""})
    return {
        "support_state": "TRANSACTIONS_RECONCILED" if not breaks else "TRANSACTIONS_PARTIAL",
        "breaks": breaks,
        "opening_balances": list(state.opening_balances),
        "history_note": (f"OPENING_BALANCES_PRESENT: history before {state.history_start.isoformat()} not established"
                         if state.opening_balances else "FULL_HISTORY_FROM_FIRST_TRANSACTION"),
        "unknown_cost_positions": list(state.unknown_cost_positions),
        "pending_settlement_cash": {f"{a}:{c}": str(v) for (a, c), v in state.pending_cash.items()},
        "lot_method": LOT_METHOD,
        "lot_method_note": LOT_METHOD_NOTE,
    }
