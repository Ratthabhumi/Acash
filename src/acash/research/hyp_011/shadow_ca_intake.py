"""Offline operator-prepared corporate-action determination intake (F10).

The prospective runner never scrapes sponsor sites. Official determinations
are prepared OFFLINE by the operator from official sponsor evidence, bound to
that evidence by SHA-256 over raw bytes, and validated here before they can
reach CADetermination.from_dict on the runner path.

Rules enforced here (fail closed, no silent defaults):

- Sponsor must equal the frozen SPONSOR_BY_SYMBOL mapping.
- Event determinations REQUIRE an exact official amount_per_share (> 0,
  finite, exact decimal — never invented, never a prior-month guess).
  A missing amount refuses the build: Observation #2 stays BLOCKED until
  the official amount is in hand.
- No-event determinations REQUIRE explicit scope evidence (an official
  schedule/scope query proving coverage). Bare absence of a parsed row is
  never sufficient.
- ex_date must be a real NYSE trading session; payable_date must be a real
  date on or after ex_date.
- retrieved_at_utc must be timezone-aware and causally precede processing.
- Every built document round-trips through CADetermination.from_dict as a
  self-consistency proof of runner-path acceptance.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Mapping, Optional

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow_ca import (
    CADetermination,
    SPONSOR_BY_SYMBOL,
)

_SHA64 = re.compile(r"[0-9a-fA-F]{64}")


@dataclass(frozen=True)
class ScopeEvidence:
    """Official-scope support for a no-event determination.

    Identifies the official schedule/scope query whose successful execution
    proves the session was covered (e.g. an iShares distribution schedule or
    State Street distribution calendar), bound by SHA-256 over the raw
    evidence bytes preserved by the operator.
    """

    schedule_id: str
    schedule_sha256: str
    scope_note: str
    retrieved_at_utc: str

    def validated(self, processing_utc: datetime) -> "ScopeEvidence":
        if not self.schedule_id.strip():
            raise DataContractError("CA_SCOPE_SCHEDULE_ID_MISSING.")
        if not _SHA64.fullmatch(self.schedule_sha256 or ""):
            raise DataContractError("CA_SCOPE_SHA_INVALID.")
        if not self.scope_note.strip():
            raise DataContractError("CA_SCOPE_NOTE_MISSING.")
        try:
            retrieved = datetime.fromisoformat(self.retrieved_at_utc)
        except (ValueError, TypeError) as exc:
            raise DataContractError("CA_SCOPE_RETRIEVED_MALFORMED.") from exc
        if retrieved.tzinfo is None:
            raise DataContractError("CA_SCOPE_RETRIEVED_NAIVE.")
        if processing_utc.tzinfo is None:
            raise DataContractError("CA_PROCESSING_TS_MUST_BE_TIMEZONE_AWARE.")
        if retrieved.astimezone(timezone.utc) > processing_utc.astimezone(timezone.utc):
            raise DataContractError("CA_SCOPE_FUTURE_RETRIEVAL.")
        return self


def _check_sponsor(symbol: str, authority_source: str) -> str:
    expected = SPONSOR_BY_SYMBOL.get(symbol)
    if not expected or authority_source != expected:
        raise DataContractError(
            f"CA_SPONSOR_MISMATCH: {symbol} requires {expected}, "
            f"got {authority_source!r}."
        )
    return expected


def _check_causality(retrieved_at_utc: str, processing_utc: datetime) -> str:
    try:
        retrieved = datetime.fromisoformat(retrieved_at_utc)
    except (ValueError, TypeError) as exc:
        raise DataContractError("CA_RETRIEVED_AT_MALFORMED.") from exc
    if retrieved.tzinfo is None:
        raise DataContractError("CA_RETRIEVED_AT_NAIVE.")
    if processing_utc.tzinfo is None:
        raise DataContractError("CA_PROCESSING_TS_MUST_BE_TIMEZONE_AWARE.")
    if retrieved.astimezone(timezone.utc) > processing_utc.astimezone(timezone.utc):
        raise DataContractError("CA_FUTURE_RETRIEVAL.")
    return retrieved.isoformat()


def _evidence_sha256(evidence_bytes: bytes, evidence_ref: str) -> str:
    if not evidence_ref.strip():
        raise DataContractError("CA_EVIDENCE_REF_MISSING.")
    if not isinstance(evidence_bytes, (bytes, bytearray)) or len(evidence_bytes) == 0:
        raise DataContractError("CA_EVIDENCE_BYTES_EMPTY.")
    return hashlib.sha256(bytes(evidence_bytes)).hexdigest()


def _require_trading_ex_date(
    ex_date: date, calendar: NyseCa1Calendar, symbol: str
) -> date:
    if not calendar.is_trading_session(ex_date):
        raise DataContractError(
            f"CA_EX_DATE_NON_SESSION: {symbol} ex-date {ex_date.isoformat()} "
            f"is not an NYSE trading session."
        )
    return ex_date


def _require_exact_amount(raw_amount: Any, symbol: str) -> Decimal:
    """Require an exact official per-share amount (never invented).

    Accepts exact decimal strings, ints, or Decimals. Rejects None, bools,
    floats, non-positive, and non-finite values fail-closed.
    """
    if raw_amount is None or isinstance(raw_amount, bool) or isinstance(raw_amount, float):
        raise DataContractError(
            f"CA_EVENT_AMOUNT_REQUIRED: {symbol} amount_per_share must be an "
            f"exact official decimal, got {type(raw_amount).__name__}."
        )
    try:
        amount = Decimal(str(raw_amount)) if not isinstance(raw_amount, Decimal) else raw_amount
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise DataContractError(
            f"CA_EVENT_AMOUNT_MALFORMED for {symbol}: {exc}."
        ) from exc
    if not amount.is_finite():
        raise DataContractError(f"CA_EVENT_AMOUNT_NONFINITE for {symbol}.")
    if amount <= Decimal("0"):
        raise DataContractError(f"CA_EVENT_NONPOSITIVE_AMOUNT for {symbol}.")
    return amount


def build_event_determination(
    symbol: str,
    session: date,
    ex_date: date,
    amount_per_share: Any,
    payable_date: date,
    authority_source: str,
    retrieved_at_utc: str,
    evidence_bytes: bytes,
    evidence_ref: str,
    processing_utc: datetime,
    record_date: Optional[date] = None,
    calendar: Optional[NyseCa1Calendar] = None,
) -> Dict[str, Any]:
    """Build a canonical event determination from official evidence (offline).

    Fails closed when the exact official amount is unavailable: callers must
    NOT substitute guesses or prior-period values. The returned document is
    round-tripped through CADetermination.from_dict as a runner-path proof.
    """
    cal = calendar or NyseCa1Calendar()
    _check_sponsor(symbol, authority_source)
    _require_trading_ex_date(ex_date, cal, symbol)
    amount = _require_exact_amount(amount_per_share, symbol)
    if payable_date < ex_date:
        raise DataContractError(
            f"CA_PAYABLE_BEFORE_EX: {symbol} payable {payable_date.isoformat()} "
            f"precedes ex-date {ex_date.isoformat()}."
        )
    retrieved_iso = _check_causality(retrieved_at_utc, processing_utc)
    sha = _evidence_sha256(evidence_bytes, evidence_ref)
    doc: Dict[str, Any] = {
        "symbol": symbol,
        "session": session.isoformat(),
        "has_event": True,
        "ex_date": ex_date.isoformat(),
        "amount_per_share": str(amount),
        "payable_date": payable_date.isoformat(),
        "record_date": record_date.isoformat() if record_date is not None else None,
        "authority_source": authority_source,
        "retrieved_at_utc": retrieved_iso,
        "source_sha256": sha,
        "evidence_ref": evidence_ref,
    }
    # Self-consistency proof: the runner path must accept this document.
    CADetermination.from_dict(doc, symbol, session, processing_utc)
    return doc


def build_no_event_determination(
    symbol: str,
    session: date,
    authority_source: str,
    retrieved_at_utc: str,
    scope: ScopeEvidence,
    evidence_bytes: bytes,
    evidence_ref: str,
    processing_utc: datetime,
) -> Dict[str, Any]:
    """Build a canonical no-event determination backed by scope evidence.

    Bare absence of a parsed row is never sufficient: a validated
    ScopeEvidence (official schedule/scope query proving coverage) is
    required, else CA_NO_EVENT_SCOPE_REQUIRED.
    """
    _check_sponsor(symbol, authority_source)
    scope.validated(processing_utc)
    retrieved_iso = _check_causality(retrieved_at_utc, processing_utc)
    sha = _evidence_sha256(evidence_bytes, evidence_ref)
    doc: Dict[str, Any] = {
        "symbol": symbol,
        "session": session.isoformat(),
        "has_event": False,
        "ex_date": None,
        "amount_per_share": None,
        "payable_date": None,
        "record_date": None,
        "authority_source": authority_source,
        "retrieved_at_utc": retrieved_iso,
        "source_sha256": sha,
        "evidence_ref": evidence_ref,
        "scope_evidence": {
            "schedule_id": scope.schedule_id,
            "schedule_sha256": scope.schedule_sha256.lower(),
            "scope_note": scope.scope_note,
            "retrieved_at_utc": scope.retrieved_at_utc,
        },
    }
    # Self-consistency proof: the runner path must accept this document.
    CADetermination.from_dict(doc, symbol, session, processing_utc)
    return doc


def intake_doc_to_determination(
    doc: Mapping[str, Any], symbol: str, session: date, processing_utc: datetime
) -> CADetermination:
    """Runner-side entry: parse an intake document through the canonical parser."""
    if not isinstance(doc, Mapping):
        raise DataContractError("CA_DETERMINATION_NOT_A_MAPPING.")
    return CADetermination.from_dict(doc, symbol, session, processing_utc)
