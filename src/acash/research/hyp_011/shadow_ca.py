"""Prospective corporate-action authority interfaces (mock-only this task).

Official sponsor mapping is frozen. A no-event determination requires a
successful official-scope query proving no target-ex-date event — never the
mere absence of a parsed row. Live sponsor calls need a future authorization.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional

from acash.core.domain.exceptions import DataContractError

SPONSOR_BY_SYMBOL: Dict[str, str] = {
    "ACWI": "BLACKROCK_ISHARES_OFFICIAL",
    "AGG": "BLACKROCK_ISHARES_OFFICIAL",
    "SPY": "STATE_STREET_SPDR_OFFICIAL",
}

OFFICIAL_DOMAIN_FRAGMENTS: Dict[str, str] = {
    "BLACKROCK_ISHARES_OFFICIAL": "ishares.com",
    "STATE_STREET_SPDR_OFFICIAL": "ssga.com",
}


@dataclass(frozen=True)
class CADetermination:
    symbol: str
    session: date
    has_event: bool
    ex_date: Optional[date] = None
    amount_per_share: Optional[Decimal] = None
    payable_date: Optional[date] = None
    record_date: Optional[date] = None
    authority_source: str = ""
    retrieved_at_utc: str = ""
    source_sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "session": self.session.isoformat(),
            "has_event": self.has_event,
            "ex_date": self.ex_date.isoformat() if self.ex_date else None,
            "amount_per_share": str(self.amount_per_share)
            if self.amount_per_share is not None
            else None,
            "payable_date": self.payable_date.isoformat() if self.payable_date else None,
            "record_date": self.record_date.isoformat() if self.record_date else None,
            "authority_source": self.authority_source,
            "retrieved_at_utc": self.retrieved_at_utc,
            "source_sha256": self.source_sha256,
        }

    @classmethod
    def from_dict(
        cls, doc: Mapping[str, Any], symbol: str, session: date,
        processing_utc: datetime,
    ) -> "CADetermination":
        """Parse + fully validate one canonical CA determination (runner path)."""
        if not isinstance(doc, Mapping):
            raise DataContractError("CA_DETERMINATION_NOT_A_MAPPING.")
        if doc.get("symbol") != symbol:
            raise DataContractError(f"CA_SYMBOL_MISMATCH: {doc.get('symbol')} != {symbol}.")
        if doc.get("session") != session.isoformat():
            raise DataContractError(f"CA_SESSION_MISMATCH for {symbol}.")
        expected_sponsor = SPONSOR_BY_SYMBOL.get(symbol)
        if not expected_sponsor or doc.get("authority_source") != expected_sponsor:
            raise DataContractError(f"CA_SPONSOR_MISMATCH for {symbol}.")
        try:
            retrieved = datetime.fromisoformat(str(doc.get("retrieved_at_utc")))
        except (ValueError, TypeError) as exc:
            raise DataContractError(f"CA_RETRIEVED_AT_MALFORMED for {symbol}.") from exc
        if retrieved.tzinfo is None:
            raise DataContractError(f"CA_RETRIEVED_AT_NAIVE for {symbol}.")
        if processing_utc.tzinfo is None:
            raise DataContractError("CA_PROCESSING_TS_MUST_BE_TIMEZONE_AWARE.")
        if retrieved.astimezone(timezone.utc) > processing_utc.astimezone(timezone.utc):
            raise DataContractError(f"CA_FUTURE_RETRIEVAL for {symbol}.")
        sha = str(doc.get("source_sha256") or "")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", sha):
            raise DataContractError(f"CA_SOURCE_SHA_INVALID for {symbol}.")
        has_event = doc.get("has_event")
        if not isinstance(has_event, bool):
            raise DataContractError(f"CA_HAS_EVENT_NOT_BOOL for {symbol}.")
        if not has_event:
            return cls(
                symbol=symbol, session=session, has_event=False,
                authority_source=str(doc.get("authority_source")),
                retrieved_at_utc=retrieved.isoformat(), source_sha256=sha.lower(),
            )
        try:
            ex_date = date.fromisoformat(str(doc["ex_date"]))
            amount = Decimal(str(doc["amount_per_share"]))
            payable = date.fromisoformat(str(doc["payable_date"]))
        except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
            raise DataContractError(f"CA_EVENT_INCOMPLETE for {symbol}: {exc}.") from exc
        if not amount.is_finite():
            raise DataContractError(f"CA_EVENT_AMOUNT_NONFINITE for {symbol}.")
        if amount <= Decimal("0"):
            raise DataContractError(f"CA_EVENT_NONPOSITIVE_AMOUNT for {symbol}.")
        record = doc.get("record_date")
        return cls(
            symbol=symbol, session=session, has_event=True, ex_date=ex_date,
            amount_per_share=amount, payable_date=payable,
            record_date=date.fromisoformat(str(record)) if record else None,
            authority_source=str(doc.get("authority_source")),
            retrieved_at_utc=retrieved.isoformat(), source_sha256=sha.lower(),
        )


class SponsorAuthorityAdapter:
    """Base adapter: official-sponsor-only, causality-enforced, mock-driven."""

    sponsor_identity: str = ""
    official_domain_fragment: str = ""

    def __init__(self) -> None:
        self.calls: List[Dict[str, str]] = []

    def query(
        self, symbol: str, session: date, processing_utc: datetime
    ) -> CADetermination:
        raise NotImplementedError

    def _check_symbol(self, symbol: str) -> None:
        expected = SPONSOR_BY_SYMBOL.get(symbol)
        if expected != self.sponsor_identity or not expected:
            raise DataContractError(
                f"CA_SPONSOR_MISMATCH: {symbol} not served by {self.sponsor_identity}."
            )

    def _check_causality(self, processing_utc: datetime) -> datetime:
        if processing_utc.tzinfo is None:
            raise DataContractError("CA_PROCESSING_TS_MUST_BE_TIMEZONE_AWARE.")
        return processing_utc.astimezone(timezone.utc)


class MockSponsorAuthorityAdapter(SponsorAuthorityAdapter):
    """Deterministic fixture adapter: canned official-shaped determinations."""

    def __init__(
        self,
        sponsor_identity: str,
        domain_fragment: str,
        events: Dict[str, Dict[str, str]],
        no_event_sessions: List[str],
        ambiguous_sessions: Optional[List[str]] = None,
    ) -> None:
        super().__init__()
        self.sponsor_identity = sponsor_identity
        self.official_domain_fragment = domain_fragment
        self._events = events
        self._no_event = set(no_event_sessions)
        self._ambiguous = set(ambiguous_sessions or [])

    def query(
        self, symbol: str, session: date, processing_utc: datetime
    ) -> CADetermination:
        now = self._check_causality(processing_utc)
        self._check_symbol(symbol)
        iso = session.isoformat()
        self.calls.append({"symbol": symbol, "session": iso})
        if iso in self._ambiguous:
            raise DataContractError(
                f"BLOCK_PROSPECTIVE_CORPORATE_ACTION_AUTHORITY: ambiguous {symbol} {iso}."
            )
        if iso in self._events:
            record = self._events[iso]
            return CADetermination(
                symbol=symbol, session=session, has_event=True,
                ex_date=date.fromisoformat(record["ex_date"]),
                amount_per_share=Decimal(record["amount"]),
                payable_date=date.fromisoformat(record["payable_date"]),
                record_date=date.fromisoformat(record["record_date"])
                if record.get("record_date")
                else None,
                authority_source=self.sponsor_identity,
                retrieved_at_utc=now.isoformat(),
                source_sha256=record.get("source_sha256", "MOCK_FIXTURE_SHA"),
            )
        if iso in self._no_event:
            return CADetermination(
                symbol=symbol, session=session, has_event=False,
                authority_source=self.sponsor_identity,
                retrieved_at_utc=now.isoformat(),
                source_sha256="MOCK_FIXTURE_NO_EVENT_SHA",
            )
        raise DataContractError(
            f"BLOCK_PROSPECTIVE_CORPORATE_ACTION_AUTHORITY: no official "
            f"determination for {symbol} {iso}."
        )
