"""Prospective corporate-action authority interfaces (mock-only this task).

Official sponsor mapping is frozen. A no-event determination requires a
successful official-scope query proving no target-ex-date event — never the
mere absence of a parsed row. Live sponsor calls need a future authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

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
