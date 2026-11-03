"""Owner-declared cash held outside the brokerage, with explicit evidence and scope rules.

The Owner may declare a balance without a screenshot; that is recorded as an Owner declaration
(never as a bank API observation) and carries its own precision. External cash is a separate scope:
it never enters the broker NAV, the broker settled cash, the DIME_SECURITIES reconciliation, or the
brokerage P&L. Only the consolidated personal-wealth view may add it, and that view is labelled as
mixed evidence because the observation times differ.

The Owner's external-cash *target* is a different number from the expense-derived emergency-reserve
requirement. They are never combined automatically and never substituted for each other.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from acash.core.domain.exceptions import DataContractError

SCHEMA = "ACASH_EXTERNAL_CASH_V1"
DATA_CLASS = "OWNER_PRIVATE_OBSERVATION"
PRECISIONS = ("EXACT", "APPROXIMATE")
EVIDENCE = ("OWNER_DECLARED", "OWNER_ESTIMATE")
LIQUIDITY = ("WITHDRAWABLE", "SPENDING")
INCLUSION = ("WEALTH_ONLY", "BROKER_ONLY", "EXCLUDED")
SCOPE = "EXTERNAL_BANK_CASH"


@dataclass(frozen=True)
class ExternalAccount:
    account_ref: str
    institution: str
    owner_label: str
    balance: Decimal
    currency: str
    precision: str
    evidence_type: str
    liquidity_status: str
    reserve_eligible: bool
    inclusion_scope: str
    observed_at: datetime
    effective_date: date


@dataclass(frozen=True)
class ExternalCash:
    accounts: Sequence[ExternalAccount]
    target: Optional[Decimal]
    target_currency: str
    target_evidence: str

    def total(self, include_approximate: bool = True) -> Decimal:
        return sum((a.balance for a in self.accounts
                    if a.inclusion_scope == "WEALTH_ONLY"
                    and (include_approximate or a.precision == "EXACT")), Decimal(0))

    def approximate(self) -> Decimal:
        return sum((a.balance for a in self.accounts
                    if a.inclusion_scope == "WEALTH_ONLY" and a.precision == "APPROXIMATE"), Decimal(0))

    def gap(self) -> Optional[Decimal]:
        return None if self.target is None else self.target - self.total()

    def reserve_eligible_total(self) -> Decimal:
        return sum((a.balance for a in self.accounts if a.reserve_eligible), Decimal(0))


def _positive(value: Any, ctx: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except Exception:
        raise DataContractError(f"EXTERNAL_CASH_INVALID: {ctx}.") from None
    if not number.is_finite() or number < 0:
        raise DataContractError(f"EXTERNAL_CASH_INVALID: {ctx}.")
    return number


def _aware(text: Any, ctx: str) -> datetime:
    try:
        moment = datetime.fromisoformat(str(text))
    except ValueError:
        raise DataContractError(f"EXTERNAL_CASH_INVALID: {ctx}.") from None
    if moment.tzinfo is None:
        raise DataContractError(f"EXTERNAL_CASH_INVALID: {ctx} needs a timezone.")
    return moment


def load_external_cash(path: Path) -> ExternalCash:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or doc.get("data_class") != DATA_CLASS:
        raise DataContractError("EXTERNAL_CASH_SCHEMA_INVALID.")
    rows = doc.get("accounts")
    if not isinstance(rows, list) or not rows:
        raise DataContractError("EXTERNAL_CASH_NO_ACCOUNTS.")
    accounts: List[ExternalAccount] = []
    seen = set()
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise DataContractError(f"EXTERNAL_CASH_INVALID: accounts[{index}].")
        ref = str(raw.get("account_ref") or "")
        if not ref or ref in seen:
            raise DataContractError("EXTERNAL_CASH_DUPLICATE_ACCOUNT.")
        seen.add(ref)
        precision = raw.get("precision")
        evidence = raw.get("evidence_type")
        liquidity = raw.get("liquidity_status")
        inclusion = raw.get("inclusion_scope")
        if precision not in PRECISIONS or evidence not in EVIDENCE or liquidity not in LIQUIDITY \
                or inclusion not in INCLUSION:
            raise DataContractError(f"EXTERNAL_CASH_INVALID: accounts[{index}] enums.")
        if precision == "APPROXIMATE" and evidence != "OWNER_ESTIMATE":
            raise DataContractError("EXTERNAL_CASH_INVALID: an approximate balance is an Owner estimate.")
        if evidence == "OWNER_DECLARED" and precision != "EXACT":
            raise DataContractError("EXTERNAL_CASH_INVALID: a declared balance must be exact.")
        accounts.append(ExternalAccount(
            account_ref=ref, institution=str(raw.get("institution") or ""),
            owner_label=str(raw.get("owner_label") or ""),
            balance=_positive(raw.get("balance"), f"accounts[{index}].balance"),
            currency=str(raw.get("currency") or "THB"), precision=precision, evidence_type=evidence,
            liquidity_status=liquidity, reserve_eligible=raw.get("reserve_eligible") is True,
            inclusion_scope=inclusion, observed_at=_aware(raw.get("observed_at"), f"accounts[{index}].observed_at"),
            effective_date=date.fromisoformat(str(raw.get("effective_date")))))
    target = doc.get("target")
    return ExternalCash(accounts=tuple(accounts),
                        target=None if target is None else _positive(target.get("amount"), "target.amount"),
                        target_currency=str((target or {}).get("currency") or "THB"),
                        target_evidence=str((target or {}).get("evidence_type") or "OWNER_EXTERNAL_CASH_TARGET"))


def summary(cash: ExternalCash) -> Dict[str, Any]:
    """Sanitized shape for the dashboard; totals are amounts the Owner already declared."""
    total = cash.total()
    gap = cash.gap()
    return {
        "scope": SCOPE,
        "evidence_quality": "OWNER_DECLARED_AND_ESTIMATE",
        "accounts": [{"account_ref": a.account_ref, "institution": a.institution, "owner_label": a.owner_label,
                      "balance": format(a.balance, "f"), "currency": a.currency, "precision": a.precision,
                      "evidence_type": a.evidence_type, "liquidity_status": a.liquidity_status,
                      "reserve_eligible": a.reserve_eligible, "observed_at": a.observed_at.isoformat(),
                      "effective_date": a.effective_date.isoformat()} for a in cash.accounts],
        "total": format(total, "f"),
        "approximate_component": format(cash.approximate(), "f"),
        "target": None if cash.target is None else format(cash.target, "f"),
        "target_currency": cash.target_currency,
        "target_evidence": cash.target_evidence,
        "gap": None if gap is None else format(gap, "f"),
        "reserve_eligible_total": format(cash.reserve_eligible_total(), "f"),
        "notes": ["EXTERNAL_CASH_IS_NOT_BROKER_CASH",
                  "EXTERNAL_CASH_IS_NOT_AUTOMATICALLY_EMERGENCY_RESERVE",
                  "OWNER_TARGET_IS_NOT_THE_EXPENSE_DERIVED_RESERVE_REQUIREMENT"],
    }


def consolidated(broker_total: Optional[Decimal], broker_observed_at: Optional[datetime],
                 cash: ExternalCash) -> Dict[str, Any]:
    """Personal-wealth view: broker value + declared external cash, explicitly mixed evidence."""
    external = cash.total()
    if broker_total is None:
        return {"status": "BROKER_VALUE_UNAVAILABLE", "external_cash": format(external, "f"),
                "consolidated_total": None, "evidence_quality": "MIXED_EVIDENCE_MIXED_TIME"}
    return {"status": "MIXED_EVIDENCE_MIXED_TIME",
            "broker_total": format(broker_total, "f"),
            "broker_observed_at": None if broker_observed_at is None else broker_observed_at.isoformat(),
            "external_cash": format(external, "f"),
            "consolidated_total": format(broker_total + external, "f"),
            "evidence_quality": "MIXED_EVIDENCE_MIXED_TIME",
            "note": "Broker total and external cash were observed at different times and are not a "
                    "single synchronised verification. External cash never enters broker NAV."}
