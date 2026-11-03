"""Owner-entered completed transactions for the owner-private dashboard (``/api/upi/transactions/``).

The journal is one ``ACASH_CANONICAL_TRANSACTIONS_V1`` batch at ``data/private/transactions/journal.json``
and is append-only: a write must keep every earlier row byte-for-byte, carry the caller's base
revision and an explicit confirmation, and pass a full replay through ``acash.ppds.transactions``
together with an opening baseline derived from the saved snapshot. Events dated on or before the
snapshot's ``valuation_date`` are already reflected in that baseline and are never replayed again.
Recording needs ODR-001, ODR-002 and ODR-005 RATIFIED; reading needs ODR-001 and ODR-002. Nothing
here contacts a broker: BUY/SELL rows describe trades the Owner already executed elsewhere.
Corrections (reversal/supersession) are not enabled: the canonical schema has no correction
event, and adding one is a separate Owner decision.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.dashboard_api import private_input as pi
from acash.ppds import transactions as txn
from acash.ppds.private_observation import SCHEMA_V1_2, odr_state, read_gated_json

PREFIX = "/api/upi/transactions/"
ROUTES: Dict[str, Tuple[str, ...]] = {"state": ("GET",), "preview": ("POST",), "record": ("POST",)}
RECORD = Path("docs/governance/ODR_UPI_LOCAL_TRANSACTION_AUTHORING_005.json")
DECISION_ID = "ODR_UPI_LOCAL_TRANSACTION_AUTHORING_005"
CAPABILITY = "OWNER_LOCAL_TRANSACTION_AUTHORING_AUTHORIZED"
REQUIRES = ["ODR_UPI_PRIVATE_OBSERVATION_001", "ODR_UPI_PRIVATE_TRANSACTIONS_002"]
SCOPE_FILES = ["data/private/transactions/"]
JOURNAL_FILE = "journal.json"
BATCH_ID = "DASHBOARD_JOURNAL"
DATA_CLASS = "OWNER_PRIVATE_OBSERVATION"
AUTHORED_EVENTS = ("BUY", "SELL", "DEPOSIT", "WITHDRAWAL", "DIVIDEND", "FEE")
TRANSACTION_ID = re.compile(r"^TX_[A-Z]{8,28}$")
BACKUPS_KEPT = 20
CORRECTIONS = "NOT_ENABLED_PENDING_OWNER_DECISION"
CENT = Decimal("0.01")


def authoring_state() -> str:
    """ODR-005: RATIFIED only with exact identity, both dependencies and the fixed schema/file scope."""
    path = pi._root() / RECORD
    state = odr_state(path, txn.SCHEMA, CAPABILITY)
    if state != "RATIFIED":
        return state
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("decision_id") != DECISION_ID:
        return "RECORD_IDENTITY_MISMATCH"
    if doc.get("requires") != REQUIRES:
        return "RECORD_DEPENDENCY_INVALID"
    if doc.get("scope_schemas") != [txn.SCHEMA] or doc.get("scope_files") != SCOPE_FILES:
        return "RECORD_SCOPE_INVALID"
    return "RATIFIED"


def authority() -> Dict[str, str]:
    return {"odr_001": odr_state(None, SCHEMA_V1_2),
            "odr_002": odr_state(pi._root() / txn.AUTHORIZATION_RECORD, txn.SCHEMA, txn.AUTHORIZED_CAPABILITY),
            "odr_005": authoring_state()}


def _write_authorized() -> bool:
    return all(v == "RATIFIED" for v in authority().values())


def journal_path() -> Path:
    path = pi._private_dir("transactions") / JOURNAL_FILE
    if pi._is_link(path):
        raise DataContractError("TXN_PATH_LINK_REFUSED: journal.")
    return path


def journal_revision() -> str:
    return pi._revision(journal_path())


def load_rows() -> List[Dict[str, Any]]:
    path = journal_path()
    if not path.is_file():
        return []
    doc = read_gated_json(path, "TXN_BATCH", record=txn.AUTHORIZATION_RECORD, capability=txn.AUTHORIZED_CAPABILITY,
                          schema=txn.SCHEMA)
    batch = txn.parse_batch(doc)
    if batch.data_class != DATA_CLASS or batch.batch_id != BATCH_ID:
        raise DataContractError("TXN_JOURNAL_IDENTITY_INVALID.")
    return list(doc["transactions"])


def _snapshot() -> Optional[Dict[str, Any]]:
    path = pi._input_path("snapshot")
    if not path.is_file():
        return None
    doc = read_gated_json(path, "INPUT", schema=SCHEMA_V1_2)
    if not isinstance(doc, dict):
        raise DataContractError("TXN_SNAPSHOT_INVALID.")
    return doc


def _position_currency(doc: Dict[str, Any], security_id: str) -> Optional[str]:
    for sec in doc.get("securities", []):
        if sec.get("security_id") == security_id and sec.get("trading_currency"):
            return str(sec["trading_currency"])
    for price in doc.get("prices", []):
        if price.get("security_id") == security_id:
            return str(price["currency"])
    return None


def baseline(doc: Dict[str, Any]) -> Tuple[date, List[Dict[str, Any]], List[Dict[str, str]]]:
    """(cutoff, opening rows, excluded) from the snapshot's quantity positions and settled cash."""
    cutoff = date.fromisoformat(str(doc["valuation_date"]))
    rows: List[Dict[str, Any]] = []
    excluded: List[Dict[str, str]] = []
    for account in doc.get("accounts", []):
        ref = account["account_ref"]
        held: Dict[str, List[Dict[str, Any]]] = {}
        for pos in account.get("positions", []):
            if "quantity" in pos:
                held.setdefault(pos["security_id"], []).append(pos)
            else:
                excluded.append({"code": "VALUE_ONLY_POSITION_NOT_IN_BASELINE", "where": f"{ref}:{pos['security_id']}"})
        for sec, positions in sorted(held.items()):
            ccy = _position_currency(doc, sec) or positions[0].get("cost_basis_currency")
            if not ccy:
                excluded.append({"code": "POSITION_CURRENCY_UNKNOWN", "where": f"{ref}:{sec}"})
                continue
            row: Dict[str, Any] = {"transaction_id": f"OPEN_P{len(rows) + 1}", "account_ref": ref,
                                   "event_type": "OPENING_POSITION", "trade_date": cutoff.isoformat(),
                                   "security_id": sec, "currency": ccy,
                                   "quantity": format(sum((Decimal(str(p["quantity"])) for p in positions), Decimal(0)), "f")}
            if all("cost_basis_total" in p and p.get("cost_basis_currency") == ccy for p in positions):
                row["cost_basis_total"] = format(sum((Decimal(str(p["cost_basis_total"])) for p in positions), Decimal(0)), "f")
            rows.append(row)
        cash: Dict[str, Decimal] = {}
        for entry in account.get("cash", []):
            if entry.get("kind") == "SETTLED":
                cash[entry["currency"]] = cash.get(entry["currency"], Decimal(0)) + Decimal(str(entry["amount"]))
        for ccy, amount in sorted(cash.items()):
            if amount > 0:
                rows.append({"transaction_id": f"OPEN_C{len(rows) + 1}", "account_ref": ref, "event_type": "OPENING_CASH",
                             "trade_date": cutoff.isoformat(), "currency": ccy, "net_cash": format(amount, "f")})
            elif amount < 0:
                excluded.append({"code": "NEGATIVE_CASH_NOT_IN_BASELINE", "where": f"{ref}:{ccy}"})
    return cutoff, rows, excluded


def _ledger(doc: Dict[str, Any], rows: List[Dict[str, Any]], as_of: date) -> Tuple[Optional[txn.LedgerState], Dict[str, Any]]:
    cutoff, openings, excluded = baseline(doc)
    events = [r for r in rows if date.fromisoformat(str(r["trade_date"])) > cutoff]
    info = {"cutoff": cutoff.isoformat(), "baseline_excluded": excluded, "applied": len(events),
            "before_cutoff": len(rows) - len(events)}
    parsed = [txn.parse_transaction(r, i) for i, r in enumerate(openings + events)]
    if len({t.key for t in parsed}) != len(parsed):
        raise DataContractError("TXN_DUPLICATE_ID.")
    return (txn.replay(parsed, as_of) if parsed else None), info


def _projection(state: Optional[txn.LedgerState]) -> Dict[str, Any]:
    if state is None:
        return {"positions": [], "cash": [], "pending_cash": [], "realized": []}
    positions = []
    for (account, security), lots in state.lots.items():
        known = all(lot.cost_total is not None for lot in lots)
        positions.append({"account_ref": account, "security_id": security, "currency": lots[0].currency,
                          "quantity": format(sum((lot.quantity for lot in lots), Decimal(0)), "f"),
                          "cost_total": format(sum((lot.cost_total or Decimal(0) for lot in lots), Decimal(0)).quantize(CENT), "f") if known else None,
                          "cost_status": "KNOWN" if known else "COST_NOT_ESTABLISHED"})
    return {"positions": positions,
            "cash": [{"account_ref": a, "currency": c, "amount": format(v, "f")} for (a, c), v in state.cash.items()],
            "pending_cash": [{"account_ref": a, "currency": c, "amount": format(v, "f")} for (a, c), v in state.pending_cash.items()],
            "realized": list(state.realized)}


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _validate(raw: Any, doc: Dict[str, Any], rows: List[Dict[str, Any]], today: date) -> Dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("event_type") not in AUTHORED_EVENTS:
        raise DataContractError("TXN_EVENT_NOT_AUTHORABLE: only BUY, SELL, DEPOSIT, WITHDRAWAL, DIVIDEND, FEE.")
    row = {k: v for k, v in raw.items() if v is not None}
    if not isinstance(row.get("transaction_id"), str) or not TRANSACTION_ID.match(row["transaction_id"]):
        raise DataContractError("TXN_ID_REQUIRED: transaction_id must match TX_ plus 8-28 capital letters.")
    parsed = txn.parse_transaction(row, 0)
    if parsed.account_ref not in {a["account_ref"] for a in doc.get("accounts", [])}:
        raise DataContractError("TXN_ACCOUNT_UNKNOWN: record the account in the Setup Wizard first.")
    if parsed.security_id is not None and parsed.security_id not in {s["security_id"] for s in doc.get("securities", [])}:
        raise DataContractError("TXN_SECURITY_UNKNOWN: add the security in the Setup Wizard first.")
    cutoff = date.fromisoformat(str(doc["valuation_date"]))
    if parsed.trade_date <= cutoff:
        raise DataContractError("TXN_BEFORE_BASELINE_CUTOFF: the snapshot already reflects this date.")
    if parsed.trade_date > today:
        raise DataContractError("TXN_FUTURE_TRADE_DATE: only completed transactions can be recorded.")
    if parsed.event_type in ("BUY", "SELL") and parsed.security_id is not None:
        expected = _position_currency(doc, parsed.security_id)
        if expected is not None and parsed.currency != expected:
            raise DataContractError("TXN_CURRENCY_MISMATCH: trade currency differs from the security's currency.")
    return row


def _effect(doc: Dict[str, Any], rows: List[Dict[str, Any]], row: Dict[str, Any], today: date) -> Dict[str, Any]:
    before, _ = _ledger(doc, rows, today)
    after, info = _ledger(doc, rows + [row], today)
    return {"before": _projection(before), "after": _projection(after), "cutoff": info["cutoff"]}


def state() -> pi.Result:
    doc = _snapshot()
    if doc is None:
        return 404, {"status": "NO_INPUT", **authority()}
    rows = load_rows()
    ledger, info = _ledger(doc, rows, _today())
    cutoff = date.fromisoformat(info["cutoff"])
    entries = [{**r, "status": "APPLIED" if date.fromisoformat(str(r["trade_date"])) > cutoff else "BEFORE_BASELINE_CUTOFF"}
               for r in rows]
    return 200, {"status": "OK", **authority(), "revision": journal_revision(), "baseline": info,
                 "entries": entries, "projection": _projection(ledger), "corrections": CORRECTIONS,
                 "authored_events": list(AUTHORED_EVENTS)}


def _duplicate(rows: List[Dict[str, Any]], row: Dict[str, Any]) -> Optional[str]:
    """ALREADY_RECORDED, TXN_ID_CONFLICT, POSSIBLE_DUPLICATE or None."""
    for existing in rows:
        if existing.get("transaction_id") == row["transaction_id"]:
            return "ALREADY_RECORDED" if existing == row else "TXN_ID_CONFLICT"
    fingerprint = txn.parse_transaction(row, 0).fingerprint
    if any(txn.parse_transaction(r, i).fingerprint == fingerprint for i, r in enumerate(rows)):
        return "POSSIBLE_DUPLICATE"
    return None


def preview(body: Any) -> pi.Result:
    if not isinstance(body, dict) or set(body) != {"transaction"}:
        return 400, {"status": "REQUEST_FIELDS_INVALID"}
    doc = _snapshot()
    if doc is None:
        return 404, {"status": "NO_INPUT"}
    rows, today = load_rows(), _today()
    row = _validate(body["transaction"], doc, rows, today)
    duplicate = _duplicate(rows, row)
    return 200, {"status": "PREVIEW", "duplicate": duplicate, "revision": journal_revision(),
                 "effect": _effect(doc, [r for r in rows if r.get("transaction_id") != row["transaction_id"]], row, today)}


def _backup(path: Path, revision: str) -> None:
    backups = pi._private_dir("transactions", "backups")
    backups.mkdir(parents=True, exist_ok=True)
    name = f"journal-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{revision[:12]}.json"
    pi._atomic_write(backups / name, path.read_bytes())
    for old in sorted(backups.glob("journal-*.json"))[:-BACKUPS_KEPT]:
        old.unlink()


def record(body: Any, service: pi.InputService) -> pi.Result:
    """Append one confirmed completed event; idempotent on an identical resubmission."""
    if not isinstance(body, dict) or not {"base_revision", "confirm", "transaction"} <= set(body) \
            or set(body) - {"base_revision", "confirm", "transaction", "confirm_duplicate"}:
        return 400, {"status": "REQUEST_FIELDS_INVALID"}
    if body["confirm"] is not True:
        return 400, {"status": "CONFIRMATION_REQUIRED"}
    with service.write_lock:
        doc = _snapshot()
        if doc is None:
            return 404, {"status": "NO_INPUT"}
        path = journal_path()
        current = pi._revision(path)
        rows, today = load_rows(), _today()
        row = _validate(body["transaction"], doc, rows, today)
        duplicate = _duplicate(rows, row)
        if duplicate == "ALREADY_RECORDED":
            return 200, {"status": "ALREADY_RECORDED", "revision": current}
        if current != body["base_revision"]:
            return 409, {"status": "REVISION_CONFLICT", "revision": current}
        if duplicate == "TXN_ID_CONFLICT":
            return 409, {"status": "TXN_ID_CONFLICT"}
        if duplicate == "POSSIBLE_DUPLICATE":
            if body.get("confirm_duplicate") is not True:
                return 409, {"status": "POSSIBLE_DUPLICATE"}
            row["sequence"] = sum(1 for r in rows if "sequence" in r) + 1
        ledger, _ = _ledger(doc, rows + [row], today)
        new_doc = {"schema": txn.SCHEMA, "data_class": DATA_CLASS, "batch_id": BATCH_ID, "transactions": rows + [row]}
        txn.parse_batch(copy.deepcopy(new_doc))
        data = (json.dumps(new_doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        if not _write_authorized():
            return 403, {"status": "TRANSACTION_AUTHORING_AUTHORIZATION_REQUIRED", **authority()}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if current != pi.ABSENT:
                _backup(path, current)
            pi._atomic_write(path, data)
        except OSError as exc:
            return 500, {"status": "WRITE_FAILED", "code": type(exc).__name__}
        if load_rows()[:-1] != rows:
            raise DataContractError("TXN_JOURNAL_NOT_APPEND_ONLY.")
        return 200, {"status": "RECORDED", "revision": pi._revision(path), "projection": _projection(ledger)}


def holdings_for_valuation(doc: Dict[str, Any], today: date) -> Tuple[Dict[str, Any], str]:
    """Snapshot document with quantities and settled cash projected through the journal.

    Returns the snapshot unchanged (``STATEMENT_BASELINE``) unless ODR-002 is RATIFIED and the
    journal holds events after the cutoff; then positions with quantity and settled cash come from
    the replay (``STATEMENT_BASELINE_PLUS_JOURNAL``). Value-only positions are left as they are.
    """
    if authority()["odr_002"] != "RATIFIED" or not journal_path().is_file():
        return doc, "STATEMENT_BASELINE"
    rows = load_rows()
    ledger, info = _ledger(doc, rows, today)
    if not info["applied"] or ledger is None:
        return doc, "STATEMENT_BASELINE"
    out = copy.deepcopy(doc)
    for account in out["accounts"]:
        ref = account["account_ref"]
        original = {p["security_id"]: p for p in account.get("positions", []) if "quantity" in p}
        positions = [p for p in account.get("positions", []) if "quantity" not in p]
        for (acct, security), lots in ledger.lots.items():
            if acct != ref:
                continue
            pos: Dict[str, Any] = {"security_id": security,
                                   "quantity": format(sum((lot.quantity for lot in lots), Decimal(0)), "f")}
            if original.get(security, {}).get("sub_portfolio") is not None:
                pos["sub_portfolio"] = original[security]["sub_portfolio"]
            if all(lot.cost_total is not None for lot in lots):
                pos["cost_basis_total"] = format(sum((lot.cost_total or Decimal(0) for lot in lots), Decimal(0)), "f")
                pos["cost_basis_currency"] = lots[0].currency
            positions.append(pos)
        account["positions"] = positions
        ledgered = {c: v for (a, c), v in ledger.cash.items() if a == ref}
        for line in account.get("cash", []):
            if line.get("kind") == "SETTLED" and line["currency"] in ledgered and Decimal(str(line["amount"])) < 0:
                raise DataContractError(f"TXN_NEGATIVE_BASELINE_CASH_NOT_PROJECTABLE: {ref} {line['currency']}.")
        cash = [c for c in account.get("cash", []) if c.get("kind") != "SETTLED" or c["currency"] not in ledgered]
        cash += [{"currency": c, "amount": format(v, "f"), "kind": "SETTLED"} for c, v in ledgered.items()]
        account["cash"] = cash
    return out, "STATEMENT_BASELINE_PLUS_JOURNAL"


def handle(method: str, name: str, body: Any, service: pi.InputService) -> pi.Result:
    """Dispatch after the server's Host, Origin, session and body checks have passed."""
    if not service.requests.allow():
        return 429, {"status": "RATE_LIMITED"}
    auth = authority()
    if auth["odr_001"] != "RATIFIED" or auth["odr_002"] != "RATIFIED":
        return 403, {"status": "AUTHORIZATION_REQUIRED", **auth}
    try:
        if name == "state":
            return state()
        if auth["odr_005"] != "RATIFIED":
            return 403, {"status": "TRANSACTION_AUTHORING_AUTHORIZATION_REQUIRED", **auth}
        if name == "preview":
            return preview(body)
        if not service.writes.allow():
            return 429, {"status": "RATE_LIMITED"}
        return record(body, service)
    except DataContractError as exc:
        return 422, {"status": "TRANSACTION_REFUSED", **pi._code(exc)}
