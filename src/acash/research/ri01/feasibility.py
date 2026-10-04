"""Pure zero-outcome helpers for RI-01 data feasibility (synthetic fixtures only).

Every function validates its inputs fail-closed with DataContractError and
computes NOTHING predictive: no returns, no PnL, no Sharpe, no hit-rate, no
thresholds. Time semantics reuse the canonical NYSE CA-1 calendar; hashing
reuses the canonical JSON serializer.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar

REQUIRED_BAR_FIELDS: tuple[str, ...] = ("timestamp", "open", "high", "low", "close", "volume")


def require_tz_aware(value: datetime, context: str) -> datetime:
    """Reject naive timestamps fail-closed; normalize aware ones to UTC."""
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise DataContractError(f"RI01_NAIVE_TIMESTAMP: {context}.")
    return value.astimezone(timezone.utc)


def parse_utc_timestamp(raw: Any, context: str) -> datetime:
    """Parse an ISO-8601 timestamp; naive values are rejected, never assumed."""
    try:
        parsed = datetime.fromisoformat(str(raw))
    except (ValueError, TypeError) as exc:
        raise DataContractError(f"RI01_MALFORMED_TIMESTAMP: {context}.") from exc
    return require_tz_aware(parsed, context)


def _require_finite_decimal(raw: Any, context: str) -> Decimal:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError, ArithmeticError) as exc:
        raise DataContractError(f"RI01_MALFORMED_DECIMAL: {context}.") from exc
    if not value.is_finite():
        raise DataContractError(f"RI01_NON_FINITE_DECIMAL: {context}.")
    return value


def validate_provider_bar(doc: Mapping[str, Any], context: str) -> Dict[str, Any]:
    """Validate one synthetic provider minute-bar mapping (schema only).

    Enforces required fields, left-edge timestamp semantics (documented by
    the caller), strictly positive prices, OHLC consistency, and
    non-negative volume. Zero volume is PRESERVED (halt evidence), never
    coerced. Returns a normalized mapping; computes no outcome.
    """
    if not isinstance(doc, Mapping):
        raise DataContractError(f"RI01_BAR_NOT_A_MAPPING: {context}.")
    for field in REQUIRED_BAR_FIELDS:
        if field not in doc:
            raise DataContractError(f"RI01_BAR_MISSING_FIELD: {context}.{field}.")
    timestamp = parse_utc_timestamp(doc["timestamp"], f"{context}.timestamp")
    open_px = _require_finite_decimal(doc["open"], f"{context}.open")
    high_px = _require_finite_decimal(doc["high"], f"{context}.high")
    low_px = _require_finite_decimal(doc["low"], f"{context}.low")
    close_px = _require_finite_decimal(doc["close"], f"{context}.close")
    volume = _require_finite_decimal(doc["volume"], f"{context}.volume")
    for name, px in (("open", open_px), ("high", high_px), ("low", low_px), ("close", close_px)):
        if px <= 0:
            raise DataContractError(f"RI01_BAR_NONPOSITIVE_PRICE: {context}.{name}.")
    if high_px < max(open_px, close_px) or low_px > min(open_px, close_px):
        raise DataContractError(f"RI01_BAR_OHLC_INCONSISTENT: {context}.")
    if volume < 0:
        raise DataContractError(f"RI01_BAR_NEGATIVE_VOLUME: {context}.")
    return {
        "timestamp": timestamp.isoformat(),
        "open": str(open_px),
        "high": str(high_px),
        "low": str(low_px),
        "close": str(close_px),
        "volume": str(volume),
    }


def validate_symbol_identity(doc: Mapping[str, Any], context: str) -> Dict[str, str]:
    """Validate a synthetic symbol-identity record (ticker/product/CUSIP/sponsor).

    Delisted or lifecycle-ambiguous records are rejected here; lifecycle
    EVENTS (halt/delist windows) are represented by the caller excluding the
    session, never by patching identity.
    """
    if not isinstance(doc, Mapping):
        raise DataContractError(f"RI01_IDENTITY_NOT_A_MAPPING: {context}.")
    out: Dict[str, str] = {}
    for field in ("ticker", "product_id", "cusip", "sponsor"):
        raw = doc.get(field)
        if not isinstance(raw, str) or not raw.strip():
            raise DataContractError(f"RI01_IDENTITY_BAD_FIELD: {context}.{field}.")
        out[field] = raw.strip()
    if doc.get("delisted") is True:
        raise DataContractError(f"RI01_IDENTITY_DELISTED: {context}.")
    return out


def opening_bar_index(
    bars: Sequence[Mapping[str, Any]], session_open_utc: datetime
) -> int:
    """Locate the opening bar: the bar whose left-edge timestamp EQUALS the session open.

    Timestamps are compared as instants (UTC-normalized). A missing opening
    bar is DATA_UNAVAILABLE (fail-closed), never forward-filled from a later
    bar. Returns the index; validates nothing predictive.
    """
    anchor = require_tz_aware(session_open_utc, "session_open_utc")
    for index, bar in enumerate(bars):
        if not isinstance(bar, Mapping) or "timestamp" not in bar:
            raise DataContractError(f"RI01_BAR_MISSING_FIELD: bars[{index}].timestamp.")
        if parse_utc_timestamp(bar["timestamp"], f"bars[{index}].timestamp") == anchor:
            return index
    raise DataContractError("RI01_OPENING_BAR_UNAVAILABLE: no bar at session open.")


def require_complete_rth_grid(
    bars: Sequence[Mapping[str, Any]],
    session_date: date,
    calendar: NyseCa1Calendar,
    context: str,
) -> None:
    """Enforce an exact canonical RTH minute grid for one trading session.

    The expected left-edge timestamps are DERIVED from the calendar
    (open_utc + k*60s), never operator-supplied: exact session open, exact
    minute increments, no duplicates, no gaps, no out-of-order records, no
    pre/post-market records, exact regular- or half-day count, exact final
    left-edge minute before close. Any deviation is DATA_UNAVAILABLE for the
    whole session (fail-closed session exclusion). Never imputes.
    """
    if not calendar.is_trading_session(session_date):
        raise DataContractError(
            f"RI01_NON_SESSION_GRID: {session_date.isoformat()} is not a trading session."
        )
    session = calendar.get_session(session_date)
    if session.open_utc is None or session.close_utc is None:
        raise DataContractError(
            f"RI01_SESSION_BOUNDS_MISSING: {session_date.isoformat()}."
        )
    open_utc = session.open_utc.astimezone(timezone.utc)
    close_utc = session.close_utc.astimezone(timezone.utc)
    span_seconds = (close_utc - open_utc).total_seconds()
    if span_seconds <= 0 or span_seconds % 60 != 0:
        raise DataContractError(
            f"RI01_SESSION_SPAN_NOT_MINUTE_ALIGNED: {session_date.isoformat()}."
        )
    expected_count = int(span_seconds // 60)
    if len(bars) != expected_count:
        raise DataContractError(
            f"RI01_INCOMPLETE_SESSION_GRID: {context} has {len(bars)} bars, "
            f"expected {expected_count}."
        )
    expected_ts = open_utc
    for index, bar in enumerate(bars):
        if not isinstance(bar, Mapping) or "timestamp" not in bar:
            raise DataContractError(
                f"RI01_BAR_MISSING_FIELD: {context}[{index}].timestamp."
            )
        actual = parse_utc_timestamp(bar["timestamp"], f"{context}[{index}].timestamp")
        if actual != expected_ts:
            raise DataContractError(
                f"RI01_SESSION_GRID_MISMATCH: {context}[{index}] is "
                f"{actual.isoformat()}, expected {expected_ts.isoformat()}."
            )
        expected_ts += timedelta(minutes=1)


def session_utc_bounds(session: date, calendar: NyseCa1Calendar) -> Dict[str, str]:
    """Return the canonical UTC open/close instants for a trading session.

    Non-sessions (weekends/holidays) fail closed via the calendar authority.
    DST handling is entirely calendar-derived.
    """
    trading_session = calendar.get_session(session)
    if trading_session.open_utc is None or trading_session.close_utc is None:
        raise DataContractError(f"RI01_SESSION_BOUNDS_MISSING: {session.isoformat()}.")
    return {
        "session": session.isoformat(),
        "open_utc": trading_session.open_utc.isoformat(),
        "close_utc": trading_session.close_utc.isoformat(),
    }


def evidence_digest(raw_bytes: bytes) -> str:
    """SHA-256 digest over exact raw evidence bytes (tamper-evident pin)."""
    if not isinstance(raw_bytes, bytes) or not raw_bytes:
        raise DataContractError("RI01_EVIDENCE_EMPTY_BYTES.")
    return hashlib.sha256(raw_bytes).hexdigest()


def canonical_evidence_digest(doc: Mapping[str, Any]) -> str:
    """Deterministic digest over a canonical-JSON evidence document."""
    if not isinstance(doc, Mapping):
        raise DataContractError("RI01_EVIDENCE_NOT_A_MAPPING.")
    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(dict(doc)).encode("utf-8")
    ).hexdigest()
