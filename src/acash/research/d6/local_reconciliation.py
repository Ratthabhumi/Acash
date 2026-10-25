"""Reconcile LOCAL_EXPLORATORY distribution rows against issuer and cited evidence (offline).

Two overlays, each preserving the provider row's cash amount and identity:

- ``apply_issuer_records``: issuer rows (e.g. a State Street historical-distributions
  file) matched on symbol, CUSIP, ex-date and exact amount. Imputed payable dates are
  replaced by the issuer date; a provider payable date that disagrees fails closed.
- ``apply_reclassification``: cited evidence splitting one provider cash event into
  economic components (e.g. long- and short-term capital gain). Components must sum
  exactly to the provider amount, so the cash entitlement is counted once.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Mapping, Optional, Sequence, Tuple
from xml.etree import ElementTree

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.local_alpaca import DISTRIBUTION_COLUMNS

RECONCILED_COLUMNS = DISTRIBUTION_COLUMNS + ("evidence_class", "evidence_ref")
PROVIDER_ONLY = "PROVIDER_ONLY"
ISSUER_FILE_MATCHED = "ISSUER_FILE_MATCHED"
EVIDENCE_CLASSES = ("ISSUER_DOCUMENT", "OCC_MEMO_CORROBORATED", "SECONDARY_INDICATION_ONLY")
COMPONENT_TYPES = ("DIVIDEND_CASH", "CAPITAL_GAIN_LONG_TERM", "CAPITAL_GAIN_SHORT_TERM")
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_SSGA_HEADERS = ("TICKER", "CUSIP", "EX-DATE", "RECORD DATE", "PAYABLE DATE", "DIVIDEND ($)",
                 "SHORT TERM CAPITAL GAIN ($)", "LONG TERM CAPITAL GAIN ($)")


@dataclass(frozen=True)
class IssuerDistribution:
    symbol: str
    cusip: str
    ex_date: date
    record_date: Optional[date]
    payable_date: date
    dividend: Decimal
    short_term_gain: Decimal
    long_term_gain: Decimal

    @property
    def total(self) -> Decimal:
        return self.dividend + self.short_term_gain + self.long_term_gain


def _amount(raw: str, where: str) -> Decimal:
    text = raw.strip()
    if not text:
        return Decimal(0)
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise DataContractError(f"ISSUER_UNPARSEABLE_AMOUNT: {where} {raw!r}.") from exc
    if not value.is_finite() or value < 0:
        raise DataContractError(f"ISSUER_BAD_AMOUNT: {where} {raw!r}.")
    return value


def _us_date(raw: str, where: str) -> date:
    try:
        return datetime.strptime(raw.strip(), "%m/%d/%Y").date()
    except ValueError as exc:
        raise DataContractError(f"ISSUER_BAD_DATE: {where} {raw!r}.") from exc


def parse_ssga_distribution_xlsx(payload: bytes, symbols: Sequence[str]) -> List[IssuerDistribution]:
    """Rows for ``symbols`` from State Street's historical-distributions workbook (stdlib only)."""
    try:
        book = zipfile.ZipFile(io.BytesIO(payload))
        shared = [
            "".join(t.text or "" for t in si.iter(f"{_NS}t"))
            for si in ElementTree.fromstring(book.read("xl/sharedStrings.xml")).findall(f"{_NS}si")
        ]
        sheet = ElementTree.fromstring(book.read("xl/worksheets/sheet1.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise DataContractError(f"ISSUER_XLSX_UNREADABLE: {exc}.") from exc
    table: List[List[str]] = []
    for row in sheet.iter(f"{_NS}row"):
        values = []
        for cell in row.findall(f"{_NS}c"):
            node = cell.find(f"{_NS}v")
            text = "" if node is None or node.text is None else node.text
            values.append(shared[int(text)] if cell.get("t") == "s" and text else text)
        table.append(values)
    if not table:
        raise DataContractError("ISSUER_XLSX_EMPTY.")
    header = [h.strip().upper() for h in table[0]]
    missing = [h for h in _SSGA_HEADERS if h not in header]
    if missing:
        raise DataContractError(f"ISSUER_XLSX_HEADERS_MISSING: {missing}.")
    col = {h: header.index(h) for h in _SSGA_HEADERS}
    wanted = set(symbols)
    out: List[IssuerDistribution] = []
    for number, values in enumerate(table[1:], start=2):
        values = values + [""] * (len(header) - len(values))
        sym = values[col["TICKER"]].strip()
        if sym not in wanted:
            continue
        where = f"row {number}"
        record = values[col["RECORD DATE"]].strip()
        out.append(
            IssuerDistribution(
                symbol=sym,
                cusip=values[col["CUSIP"]].strip(),
                ex_date=_us_date(values[col["EX-DATE"]], where),
                record_date=_us_date(record, where) if record else None,
                payable_date=_us_date(values[col["PAYABLE DATE"]], where),
                dividend=_amount(values[col["DIVIDEND ($)"]], where),
                short_term_gain=_amount(values[col["SHORT TERM CAPITAL GAIN ($)"]], where),
                long_term_gain=_amount(values[col["LONG TERM CAPITAL GAIN ($)"]], where),
            )
        )
    return out


def _with_evidence(row: Mapping[str, str]) -> Dict[str, str]:
    out = {k: row.get(k, "") for k in RECONCILED_COLUMNS}
    if not out["evidence_class"]:
        out["evidence_class"] = PROVIDER_ONLY
    return out


@dataclass(frozen=True)
class IssuerReconciliation:
    rows: List[Dict[str, str]]
    matched: int
    payable_replaced: int
    payable_confirmed: int
    issuer_events_missing_from_provider: Tuple[str, ...]
    issuer_zero_amount_rows_without_provider_event: int = 0


def apply_issuer_records(
    rows: Sequence[Mapping[str, str]],
    issuer: Sequence[IssuerDistribution],
    *,
    symbol: str,
    cusip: str,
    window: Tuple[date, date],
    source_ref: str,
) -> IssuerReconciliation:
    """Every provider row of ``symbol`` in ``window`` must match exactly one issuer row."""
    start, end = window
    by_ex: Dict[date, IssuerDistribution] = {}
    for item in issuer:
        if item.symbol != symbol:
            continue
        if item.cusip != cusip:
            raise DataContractError(f"ISSUER_CUSIP_MISMATCH: {symbol} {item.cusip} != {cusip}.")
        if not start <= item.ex_date <= end:
            continue
        if item.ex_date in by_ex:
            raise DataContractError(f"ISSUER_DUPLICATE_EX_DATE: {symbol} {item.ex_date}.")
        if item.short_term_gain or item.long_term_gain:
            raise DataContractError(f"ISSUER_CAPITAL_GAIN_NEEDS_RECLASSIFICATION: {symbol} {item.ex_date}.")
        by_ex[item.ex_date] = item
    out: List[Dict[str, str]] = []
    matched = replaced = confirmed = 0
    seen: set[date] = set()
    for row in rows:
        new = _with_evidence(row)
        if row["symbol"] == symbol:
            ex = date.fromisoformat(row["ex_date"])
            hit = by_ex.get(ex)
            if hit is None:
                raise DataContractError(f"ISSUER_EVENT_NOT_FOUND: {symbol} {ex}.")
            if ex in seen:
                raise DataContractError(f"ISSUER_EVENT_MATCHED_TWICE: {symbol} {ex}.")
            seen.add(ex)
            if hit.total != Decimal(row["gross_amount"]):
                raise DataContractError(f"ISSUER_AMOUNT_MISMATCH: {symbol} {ex} {row['gross_amount']} != {hit.total}.")
            if row["payable_date_source"] == "PROVIDER":
                if row["payable_date"] != hit.payable_date.isoformat():
                    raise DataContractError(f"ISSUER_PROVIDER_PAYABLE_CONFLICT: {symbol} {ex}.")
                confirmed += 1
            else:
                new["payable_date"] = hit.payable_date.isoformat()
                new["payable_date_source"] = "ISSUER_FILE"
                replaced += 1
            new["evidence_class"] = ISSUER_FILE_MATCHED
            new["evidence_ref"] = source_ref
            matched += 1
        out.append(new)
    unmatched = [by_ex[d] for d in sorted(by_ex) if d not in seen]
    missing = tuple(i.ex_date.isoformat() for i in unmatched if i.total > 0)
    zero_rows = sum(1 for i in unmatched if i.total == 0)
    return IssuerReconciliation(out, matched, replaced, confirmed, missing, zero_rows)


def apply_reclassification(
    rows: Sequence[Mapping[str, str]], evidence: Sequence[Mapping[str, str]]
) -> List[Dict[str, str]]:
    """Replace each cited provider event by its components; cash total and payable date unchanged.

    Evidence columns: symbol, ex_date, provider_gross_amount, component_type, amount,
    payable_date, evidence_class, evidence_ref.
    """
    groups: Dict[Tuple[str, str, Decimal], List[Mapping[str, str]]] = {}
    for item in evidence:
        if item["component_type"] not in COMPONENT_TYPES:
            raise DataContractError(f"RECLASS_UNKNOWN_TYPE: {item['component_type']!r}.")
        if item["evidence_class"] not in EVIDENCE_CLASSES:
            raise DataContractError(f"RECLASS_UNKNOWN_EVIDENCE_CLASS: {item['evidence_class']!r}.")
        if not item["evidence_ref"].strip():
            raise DataContractError(f"RECLASS_EVIDENCE_REF_MISSING: {item['symbol']} {item['ex_date']}.")
        key = (item["symbol"], item["ex_date"], Decimal(item["provider_gross_amount"]))
        groups.setdefault(key, []).append(item)
    out = [_with_evidence(r) for r in rows]
    for (sym, ex, gross), components in groups.items():
        hits = [i for i, r in enumerate(out)
                if r["symbol"] == sym and r["ex_date"] == ex and Decimal(r["gross_amount"]) == gross]
        if len(hits) != 1:
            raise DataContractError(f"RECLASS_PROVIDER_EVENT_MATCHES_{len(hits)}: {sym} {ex} {gross}.")
        base = out[hits[0]]
        if base["evidence_class"] != PROVIDER_ONLY:
            raise DataContractError(f"RECLASS_ALREADY_RECONCILED: {sym} {ex}.")
        if sum((Decimal(c["amount"]) for c in components), Decimal(0)) != gross:
            raise DataContractError(f"RECLASS_COMPONENTS_DO_NOT_SUM: {sym} {ex} {gross}.")
        types = [c["component_type"] for c in components]
        if len(set(types)) != len(types):
            raise DataContractError(f"RECLASS_DUPLICATE_COMPONENT: {sym} {ex}.")
        replacement = []
        for c in components:
            if Decimal(c["amount"]) <= 0:
                raise DataContractError(f"RECLASS_NONPOSITIVE_COMPONENT: {sym} {ex}.")
            if c["payable_date"] and c["payable_date"] != base["payable_date"]:
                raise DataContractError(f"RECLASS_PAYABLE_CONFLICT: {sym} {ex}.")
            suffix = c["component_type"].removeprefix("CAPITAL_GAIN_").lower()
            replacement.append(dict(
                base,
                gross_amount=c["amount"],
                distribution_type=c["component_type"],
                event_id=f"{base['event_id']}#{suffix}" if len(components) > 1 else base["event_id"],
                evidence_class=c["evidence_class"],
                evidence_ref=c["evidence_ref"],
            ))
        out[hits[0]:hits[0] + 1] = replacement
    return out
