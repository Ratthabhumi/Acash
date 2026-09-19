"""MEC-0014A: Alpaca SIP Transaction Contract Qualification.

Qualifies two remaining provider mappings required before MEC-0014A can be
preregistered:

  1. ALPACA_INTRADAY_ENDPOINT_MAPPING  — Can the Alpaca SIP historical trades
     endpoint deterministically deliver the "last observed SIP transaction price
     at or before a half-hour boundary" (10:00 ET, 15:30 ET) for each probe session?

  2. ALPACA_DAILY_TRADE_COUNT_MAPPING  — Can the Alpaca SIP raw regular-session
     trade-record count serve as an ACASH operationalisation of the Gao et al.
     (2018) >=500 daily-trade-count eligibility filter?

STRICT INVARIANTS:
1. Temporal Boundary: 2017-01-01 through 2022-12-31 ONLY.
   Any date >= 2023-01-01 fails closed with DataContractError BEFORE any
   network access is attempted.
2. Provider: Alpaca Historical Stock Trades (/v2/stocks/SPY/trades, feed=sip).
   Do NOT use: /trades/latest, minute bars, daily bars, quotes, auctions.
3. Zero Return Calculation: No r1, r13, price return, regression, beta, alpha,
   correlation, t-statistic, Sharpe, P&L, signal, or backtest.
4. Zero OOS Access: No market data from >= 2023-01-01.
5. Secret Non-Leakage: API credentials are never logged or serialised.
6. Pagination to Exhaustion: next_page_token must be None to declare completeness.
   A sub-limit response page does NOT imply exhaustion.
7. Fail Closed on Ambiguity: AMBIGUOUS/MISSING classifications raise DataContractError.
   Under no circumstances may speculative intra-timestamp sequencing (such as
   unverified max(trade_id) or exchange priority) be used to break distinct-price ties.
8. Trade-ID Ordering Authority: NOT_ESTABLISHED. Trade ID collisions are recorded
   diagnostically only and do NOT imply transport duplicates.

Literature Authority (Gao et al. 2018 — LITERATURE_EXPLICIT):
  GAO_ENDPOINT_SEMANTIC = POINT_TRANSACTION_PRICE_AT_HALF_HOUR_BOUNDARY
  GAO_DAILY_TRADE_FILTER = DAILY_SPY_TRADE_COUNT >= 500

ACASH Provider Candidate:
  Endpoint: last raw SIP transaction price at or before boundary within regular session
  Count:    ALPACA_RAW_REGULAR_SESSION_SIP_TRADE_RECORD_COUNT (count >= 500)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar, SessionType
from acash.data.qualification.mec_0014_close_contract import (
    IS_END_DATE,
    IS_START_DATE,
    OOS_FORBIDDEN_DATE,
    PROBE_YEARS,
    select_mec_0014_probe_dates,
)

NY_TZ: ZoneInfo = ZoneInfo("America/New_York")

# Half-hour boundary targets for intraday endpoint qualification
BOUNDARY_1000_ET: time = time(10, 0, 0)    # r1,t endpoint (open)
BOUNDARY_1530_ET: time = time(15, 30, 0)   # r13,t endpoint (close, open)
# Regular session canonical open
SESSION_OPEN_ET: time = time(9, 30, 0)

QUALIFIED_SYMBOL: str = "SPY"
QUALIFIED_FEED: str = "sip"

# Minimum daily trade count per Gao et al. (2018) — LITERATURE_EXPLICIT
GAO_MIN_DAILY_TRADE_COUNT: int = 500

# Trade ID ordering authority status
TRADE_ID_ORDERING_AUTHORITY: str = "NOT_ESTABLISHED"

# Tracked transport duplicate count observed in canonical probe
EXACT_TRANSPORT_DUPLICATES_OBSERVED: int = 0


# ---------------------------------------------------------------------------
# Boundary Classification
# ---------------------------------------------------------------------------

class BoundaryEndpointClassification(str, Enum):
    """Classification of endpoint determinism at a single half-hour boundary."""

    UNIQUE_BOUNDARY_PRICE = "UNIQUE_BOUNDARY_PRICE"
    """Exactly one trade is the chronological maximum at or before the boundary."""

    UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE = (
        "UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE"
    )
    """Multiple trades share the maximum observed timestamp <= boundary, but all have
    the identical execution price. Price authority is deterministic."""

    AMBIGUOUS_BOUNDARY_PRICE = "AMBIGUOUS_BOUNDARY_PRICE"
    """Multiple trades share the maximum observed timestamp <= boundary and have
    more than one distinct price. Price authority cannot be established without
    speculative intra-timestamp ordering. FAIL CLOSED."""

    MISSING_PRE_BOUNDARY_TRANSACTION = "MISSING_PRE_BOUNDARY_TRANSACTION"
    """No qualifying trade found with timestamp in [session_open, boundary]."""


class EndpointMappingProposedClassification(str, Enum):
    """Proposed overall qualification status for ALPACA_INTRADAY_ENDPOINT_MAPPING."""

    QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY = (
        "QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY"
    )
    UNRESOLVED_BOUNDARY_PRICE_AMBIGUITY = "UNRESOLVED_BOUNDARY_PRICE_AMBIGUITY"
    UNRESOLVED = "UNRESOLVED"


class TradeCountMappingProposedClassification(str, Enum):
    """Proposed overall qualification status for ALPACA_DAILY_TRADE_COUNT_MAPPING."""

    QUALIFIED_PROVIDER_OPERATIONALIZATION = "QUALIFIED_PROVIDER_OPERATIONALIZATION"
    UNRESOLVED = "UNRESOLVED"


# ---------------------------------------------------------------------------
# Raw trade record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RawSipTradeRecord:
    """Single raw trade record from Alpaca /v2/stocks/SPY/trades (feed=sip)."""

    timestamp_utc: str          # ISO-8601 string as returned by provider
    price: Decimal
    size: int
    exchange: str               # Exchange code (e.g. 'P', 'Q', 'N')
    conditions: List[str]       # SIP condition codes, unfiltered
    tape: str                   # SIP tape (A/B/C)
    trade_id: Optional[int]     # Alpaca trade ID field ('i'), if present
    symbol: str = "SPY"


# ---------------------------------------------------------------------------
# Boundary candidate record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BoundaryCandidate:
    """Diagnostic record for the candidate transaction at a single half-hour boundary."""

    session_date: str
    boundary_et: str                                  # e.g. "10:00:00"
    classification: BoundaryEndpointClassification

    # Selected boundary price (None if MISSING or AMBIGUOUS_BOUNDARY_PRICE)
    selected_price: Optional[Decimal]

    # Maximal observed timestamp at or before boundary (T*)
    max_timestamp_utc: Optional[str]
    max_timestamp_et: Optional[str]
    distance_to_boundary_seconds: Optional[str]       # str(Decimal) for JSON-safety
    exact_boundary_timestamp_match: bool              # True iff T*.time() == boundary_et exactly

    # Tie set evidence at T*
    boundary_tie_record_count: int                    # len(S*)
    distinct_boundary_price_count: int                # len(distinct_prices(S*))
    exchange_set: List[str]                           # sorted list of distinct exchanges in S*
    condition_set: List[str]                          # sorted list of distinct conditions in S*
    tie_trade_ids: List[Optional[int]]                # diagnostic trade IDs in S*

    # First trade strictly after boundary for boundary-closure proof
    first_after_boundary_ts: Optional[str]

    notes: List[str] = field(default_factory=list)

    # Backwards-compatibility properties
    @property
    def candidate_price(self) -> Optional[Decimal]:
        return self.selected_price

    @property
    def candidate_timestamp_utc(self) -> Optional[str]:
        return self.max_timestamp_utc

    @property
    def candidate_timestamp_et(self) -> Optional[str]:
        return self.max_timestamp_et

    @property
    def seconds_before_boundary(self) -> Optional[str]:
        return self.distance_to_boundary_seconds

    @property
    def at_boundary_count(self) -> int:
        return self.boundary_tie_record_count if self.exact_boundary_timestamp_match else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_date": self.session_date,
            "boundary_et": self.boundary_et,
            "classification": self.classification.value,
            "selected_price": str(self.selected_price) if self.selected_price is not None else None,
            "max_timestamp_utc": self.max_timestamp_utc,
            "max_timestamp_et": self.max_timestamp_et,
            "distance_to_boundary_seconds": self.distance_to_boundary_seconds,
            "exact_boundary_timestamp_match": self.exact_boundary_timestamp_match,
            "boundary_tie_record_count": self.boundary_tie_record_count,
            "distinct_boundary_price_count": self.distinct_boundary_price_count,
            "exchange_set": self.exchange_set,
            "condition_set": self.condition_set,
            "tie_trade_ids": self.tie_trade_ids,
            "first_after_boundary_ts": self.first_after_boundary_ts,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Session qualification result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionTransactionQualification:
    """Full transaction-contract qualification for a single regular session."""

    session_date: str
    total_raw_records: int
    regular_session_record_count: int             # timestamps in [09:30:00, 16:00:00] ET
    exact_transport_duplicates: int               # full-record duplicates (must be 0)
    trade_id_collision_diagnostics: Dict[str, Any] # non-authoritative diagnostics
    page_count: int
    pagination_complete: bool                     # next_page_token exhausted

    condition_census: Dict[str, int]              # condition_code -> record_count (diagnostic only)
    exchange_census: Dict[str, int]               # exchange -> record_count
    tape_census: Dict[str, int]                   # tape -> record_count

    boundary_1000: BoundaryCandidate
    boundary_1530: BoundaryCandidate

    # Backwards-compatibility property
    @property
    def duplicate_id_pairs_found(self) -> int:
        return int(self.trade_id_collision_diagnostics.get("global_trade_id_collision_count", 0))

    @property
    def duplicate_timestamp_groups(self) -> int:
        return int(self.trade_id_collision_diagnostics.get("duplicate_timestamp_groups", 0))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_date": self.session_date,
            "total_raw_records": self.total_raw_records,
            "regular_session_record_count": self.regular_session_record_count,
            "exact_transport_duplicates": self.exact_transport_duplicates,
            "trade_id_collision_diagnostics": self.trade_id_collision_diagnostics,
            "page_count": self.page_count,
            "pagination_complete": self.pagination_complete,
            "condition_census": self.condition_census,
            "exchange_census": self.exchange_census,
            "tape_census": self.tape_census,
            "boundary_1000": self.boundary_1000.to_dict(),
            "boundary_1530": self.boundary_1530.to_dict(),
        }


# ---------------------------------------------------------------------------
# Aggregate probe result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TransactionContractProbeResult:
    """Aggregate qualification result across all six probe sessions."""

    probe_dates: List[str]
    sessions: List[SessionTransactionQualification]

    endpoint_mapping_proposed: EndpointMappingProposedClassification
    trade_count_mapping_proposed: TradeCountMappingProposedClassification

    endpoint_blocker_notes: List[str]
    trade_count_blocker_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probe_dates": self.probe_dates,
            "sessions": [s.to_dict() for s in self.sessions],
            "endpoint_mapping_proposed": self.endpoint_mapping_proposed.value,
            "trade_count_mapping_proposed": self.trade_count_mapping_proposed.value,
            "endpoint_blocker_notes": self.endpoint_blocker_notes,
            "trade_count_blocker_notes": self.trade_count_blocker_notes,
        }


# ---------------------------------------------------------------------------
# Fail-closed guards
# ---------------------------------------------------------------------------

def assert_transaction_probe_date(d: date) -> None:
    """Enforce temporal boundary: 2017-01-01 <= date <= 2022-12-31 ONLY."""
    if d >= OOS_FORBIDDEN_DATE:
        raise DataContractError(
            f"OOS DATA ACCESS FORBIDDEN: Date {d.isoformat()} is on or after "
            f"sealed OOS boundary {OOS_FORBIDDEN_DATE.isoformat()}. "
            f"Execution halted before network access."
        )
    if d < IS_START_DATE or d > IS_END_DATE:
        raise DataContractError(
            f"OUT OF REPLICATION BOUNDS: Date {d.isoformat()} is outside "
            f"IS window [{IS_START_DATE.isoformat()}, {IS_END_DATE.isoformat()}]."
        )


def assert_qualified_symbol(symbol: str) -> None:
    """Enforce symbol: SPY ONLY."""
    if symbol != QUALIFIED_SYMBOL:
        raise DataContractError(
            f"INVALID SYMBOL: {symbol}. MEC-0014A is qualified exclusively for {QUALIFIED_SYMBOL}."
        )


def assert_qualified_feed(feed: str) -> None:
    """Enforce feed: sip ONLY."""
    if feed != QUALIFIED_FEED:
        raise DataContractError(
            f"INVALID FEED: '{feed}'. Must use consolidated SIP feed ('{QUALIFIED_FEED}')."
        )


def assert_response_symbol(symbol: str) -> None:
    """Validate that symbol returned in response matches SPY."""
    if symbol != QUALIFIED_SYMBOL:
        raise DataContractError(
            f"PROVIDER CONTRACT VIOLATION: Response returned symbol '{symbol}' "
            f"instead of expected '{QUALIFIED_SYMBOL}'."
        )


def assert_response_timestamp_in_bounds(ts_utc_str: str, session_date: date) -> None:
    """Validate that every trade timestamp belongs to the queried session date in ET."""
    dt_et = _dt_et(ts_utc_str)
    session_dt = date(session_date.year, session_date.month, session_date.day)
    if dt_et.date() != session_dt:
        raise DataContractError(
            f"TIMESTAMP CONTAMINATION: Trade timestamp {ts_utc_str} maps to ET date "
            f"{dt_et.date().isoformat()}, which does not match expected session date "
            f"{session_date.isoformat()}. Provider data leakage detected."
        )


# ---------------------------------------------------------------------------
# Page parser
# ---------------------------------------------------------------------------

def parse_trades_page(
    payload: Dict[str, Any],
    symbol: str = QUALIFIED_SYMBOL,
    session_date: Optional[date] = None,
) -> Tuple[List[RawSipTradeRecord], Optional[str]]:
    """Parse one page of the Alpaca /v2/stocks/{symbol}/trades response.

    Returns (records, next_page_token).
    Raises DataContractError if the response symbol is wrong or timestamps escape
    the expected session window (when session_date is provided).
    """
    raw_trades = payload.get("trades", [])
    # Multi-symbol map shape
    if isinstance(raw_trades, dict):
        for sym_key in raw_trades.keys():
            assert_response_symbol(sym_key)
        raw_trades = raw_trades.get(symbol, [])

    records: List[RawSipTradeRecord] = []
    for t in raw_trades:
        ts_utc = str(t["t"])
        if session_date is not None:
            assert_response_timestamp_in_bounds(ts_utc, session_date)
        conditions = [str(c) for c in t.get("c", [])]
        trade_id_raw = t.get("i")
        trade_id: Optional[int] = int(trade_id_raw) if trade_id_raw is not None else None
        records.append(
            RawSipTradeRecord(
                timestamp_utc=ts_utc,
                price=Decimal(str(t["p"])),
                size=int(t["s"]),
                exchange=str(t["x"]),
                conditions=conditions,
                tape=str(t.get("z", "")),
                trade_id=trade_id,
                symbol=symbol,
            )
        )

    next_token: Optional[str] = payload.get("next_page_token") or None
    return records, next_token


# ---------------------------------------------------------------------------
# Regular-session temporal filter
# ---------------------------------------------------------------------------

def _dt_et(ts_utc: str) -> datetime:
    """Parse a UTC ISO timestamp and convert to America/New_York."""
    return datetime.fromisoformat(ts_utc.replace("Z", "+00:00")).astimezone(NY_TZ)


SESSION_INTERVAL_PREDICATE: str = "09:30:00 <= timestamp <= 16:00:00 America/New_York"
SESSION_INTERVAL_CLASSIFICATION: str = "ACASH_PROVIDER_OPERATIONALIZATION_CHOICE"


def filter_regular_session_records(
    records: Sequence[RawSipTradeRecord],
    session_date: date,
    session_open_et: time = SESSION_OPEN_ET,
    session_close_et: time = time(16, 0, 0),
) -> List[RawSipTradeRecord]:
    """Return only records whose timestamps fall in [session_open, session_close] ET.

    Explicit Predicate (ACASH_PROVIDER_OPERATIONALIZATION_CHOICE):
        session_open_et <= trade_time_et <= session_close_et
        (09:30:00 <= t <= 16:00:00 America/New_York)

    This closed interval includes the 16:00:00.000000 boundary to capture any
    regular-session closing prints stamped at the scheduled close, while
    strictly excluding pre-market (< 09:30:00) and post-market (> 16:00:00).
    """
    result: List[RawSipTradeRecord] = []
    session_dt = date(session_date.year, session_date.month, session_date.day)
    for r in records:
        dt = _dt_et(r.timestamp_utc)
        if dt.date() != session_dt:
            continue
        t = dt.time()
        if t >= session_open_et and t <= session_close_et:
            result.append(r)
    return result


# ---------------------------------------------------------------------------
# Transport duplicate detection & trade ID diagnostics
# ---------------------------------------------------------------------------

def extract_transport_key(r: RawSipTradeRecord) -> Tuple[Any, ...]:
    """Extract candidate exact full-record identity tuple."""
    return (
        r.timestamp_utc,
        r.exchange,
        str(r.price),
        r.size,
        tuple(r.conditions),
        r.tape,
        r.trade_id,
        r.symbol,
    )


def detect_transport_duplicates(records: Sequence[RawSipTradeRecord]) -> int:
    """Count records with identical full-record transport identity.

    Candidate exact tuple:
        (timestamp, exchange, price, size, conditions, tape, trade_id, symbol)

    Returns the number of duplicate record instances observed (0 = clean).
    """
    seen: Set[Tuple[Any, ...]] = set()
    dup_count = 0
    for r in records:
        key = extract_transport_key(r)
        if key in seen:
            dup_count += 1
        else:
            seen.add(key)
    return dup_count


def detect_trade_id_collisions(records: Sequence[RawSipTradeRecord]) -> Dict[str, Any]:
    """Diagnostically tally trade_id collisions.

    NON-AUTHORITATIVE: trade_id is not established as globally unique or
    monotonically sequenced across exchanges. This is purely diagnostic evidence.
    """
    global_id_counts: Dict[int, int] = {}
    exchange_id_counts: Dict[Tuple[str, int], int] = {}
    ts_counts: Dict[str, int] = {}

    for r in records:
        ts_counts[r.timestamp_utc] = ts_counts.get(r.timestamp_utc, 0) + 1
        if r.trade_id is not None:
            global_id_counts[r.trade_id] = global_id_counts.get(r.trade_id, 0) + 1
            ex_key = (r.exchange, r.trade_id)
            exchange_id_counts[ex_key] = exchange_id_counts.get(ex_key, 0) + 1

    global_collisions = sum(1 for cnt in global_id_counts.values() if cnt > 1)
    exchange_collisions = sum(1 for cnt in exchange_id_counts.values() if cnt > 1)
    dup_ts_groups = sum(1 for cnt in ts_counts.values() if cnt > 1)

    return {
        "global_trade_id_collision_count": global_collisions,
        "exchange_scoped_trade_id_collision_count": exchange_collisions,
        "duplicate_timestamp_groups": dup_ts_groups,
        "trade_id_ordering_authority": TRADE_ID_ORDERING_AUTHORITY,
    }


# Backwards compatibility helper for existing test calls
def detect_duplicate_trade_ids(records: Sequence[RawSipTradeRecord]) -> int:
    """Non-authoritative legacy helper: counts global trade ID collisions."""
    return int(detect_trade_id_collisions(records)["global_trade_id_collision_count"])


def detect_duplicate_timestamp_groups(records: Sequence[RawSipTradeRecord]) -> int:
    """Count timestamp values that appear more than once in the session."""
    return int(detect_trade_id_collisions(records)["duplicate_timestamp_groups"])


# ---------------------------------------------------------------------------
# Condition, Exchange, Tape Censuses
# ---------------------------------------------------------------------------

def build_condition_census(records: Sequence[RawSipTradeRecord]) -> Dict[str, int]:
    """Build a diagnostic census of condition codes present in the session."""
    census: Dict[str, int] = {}
    for r in records:
        if not r.conditions:
            census["<no_condition>"] = census.get("<no_condition>", 0) + 1
        for c in r.conditions:
            census[c] = census.get(c, 0) + 1
    return dict(sorted(census.items()))


def build_exchange_census(records: Sequence[RawSipTradeRecord]) -> Dict[str, int]:
    """Build a diagnostic census of exchanges present in the session."""
    census: Dict[str, int] = {}
    for r in records:
        census[r.exchange] = census.get(r.exchange, 0) + 1
    return dict(sorted(census.items()))


def build_tape_census(records: Sequence[RawSipTradeRecord]) -> Dict[str, int]:
    """Build a diagnostic census of tape codes present in the session."""
    census: Dict[str, int] = {}
    for r in records:
        census[r.tape] = census.get(r.tape, 0) + 1
    return dict(sorted(census.items()))


# ---------------------------------------------------------------------------
# Boundary endpoint classification (Price-Authority Contract)
# ---------------------------------------------------------------------------

def classify_boundary_endpoint(
    session_date: date,
    session_records: Sequence[RawSipTradeRecord],
    boundary_et: time,
) -> BoundaryCandidate:
    """Classify the boundary price authority at target boundary B.

    The research object needed by Gao et al. (2018) is a transaction PRICE at
    each half-hour boundary.

    Algorithm:
    1. Filter all raw regular-session SIP trades with timestamp <= boundary_et.
    2. Find T* = max(timestamp <= boundary_et).
    3. Collect complete tie set S* = {all trades whose timestamp == T*}.
    4. Inspect distinct prices in S*:
       - Case A: len(S*) == 1 -> UNIQUE_BOUNDARY_PRICE, selected price = that trade's price.
       - Case B: len(S*) > 1 AND all trades have exactly the same price:
         -> UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE, selected price = common price.
       - Case C: len(distinct_prices(S*)) > 1 -> AMBIGUOUS_BOUNDARY_PRICE (FAIL CLOSED).
         Do NOT use trade ID, exchange priority, averaging, or record order to choose.
    """
    assert_transaction_probe_date(session_date)

    boundary_label = boundary_et.strftime("%H:%M:%S")

    # Build candidate list: session_open <= trade_time <= boundary
    candidates_at_or_before: List[Tuple[datetime, RawSipTradeRecord]] = []
    first_after: Optional[str] = None

    for r in session_records:
        dt = _dt_et(r.timestamp_utc)
        t = dt.time()
        if t < SESSION_OPEN_ET:
            continue
        if t <= boundary_et:
            candidates_at_or_before.append((dt, r))
        elif first_after is None:
            first_after = r.timestamp_utc

    if not candidates_at_or_before:
        return BoundaryCandidate(
            session_date=session_date.isoformat(),
            boundary_et=boundary_label,
            classification=BoundaryEndpointClassification.MISSING_PRE_BOUNDARY_TRANSACTION,
            selected_price=None,
            max_timestamp_utc=None,
            max_timestamp_et=None,
            distance_to_boundary_seconds=None,
            exact_boundary_timestamp_match=False,
            boundary_tie_record_count=0,
            distinct_boundary_price_count=0,
            exchange_set=[],
            condition_set=[],
            tie_trade_ids=[],
            first_after_boundary_ts=first_after,
            notes=["MISSING: no qualifying SIP trade at or before boundary within regular session."],
        )

    # Find maximal timestamp T*
    max_dt = max(dt for dt, _ in candidates_at_or_before)
    at_max: List[RawSipTradeRecord] = [r for dt, r in candidates_at_or_before if dt == max_dt]

    # Compute distance from boundary
    boundary_dt = datetime(
        max_dt.year, max_dt.month, max_dt.day,
        boundary_et.hour, boundary_et.minute, boundary_et.second,
        tzinfo=NY_TZ,
    )
    delta_seconds = Decimal(str((boundary_dt - max_dt).total_seconds()))
    exact_match = (max_dt.time() == boundary_et)

    distinct_prices = sorted(set(r.price for r in at_max))
    exchanges = sorted(set(r.exchange for r in at_max))
    all_conditions = sorted(set(c for r in at_max for c in r.conditions))
    tie_ids = [r.trade_id for r in at_max]

    # Case A: exactly one trade at T*
    if len(at_max) == 1:
        r = at_max[0]
        return BoundaryCandidate(
            session_date=session_date.isoformat(),
            boundary_et=boundary_label,
            classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE,
            selected_price=r.price,
            max_timestamp_utc=r.timestamp_utc,
            max_timestamp_et=max_dt.strftime("%Y-%m-%dT%H:%M:%S.%f %Z"),
            distance_to_boundary_seconds=str(delta_seconds),
            exact_boundary_timestamp_match=exact_match,
            boundary_tie_record_count=1,
            distinct_boundary_price_count=1,
            exchange_set=exchanges,
            condition_set=all_conditions,
            tie_trade_ids=tie_ids,
            first_after_boundary_ts=first_after,
            notes=[],
        )

    # Case B: multiple trades at T*, but all have identical price
    if len(distinct_prices) == 1:
        common_price = distinct_prices[0]
        return BoundaryCandidate(
            session_date=session_date.isoformat(),
            boundary_et=boundary_label,
            classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE,
            selected_price=common_price,
            max_timestamp_utc=at_max[0].timestamp_utc,
            max_timestamp_et=max_dt.strftime("%Y-%m-%dT%H:%M:%S.%f %Z"),
            distance_to_boundary_seconds=str(delta_seconds),
            exact_boundary_timestamp_match=exact_match,
            boundary_tie_record_count=len(at_max),
            distinct_boundary_price_count=1,
            exchange_set=exchanges,
            condition_set=all_conditions,
            tie_trade_ids=tie_ids,
            first_after_boundary_ts=first_after,
            notes=[
                f"Deterministic boundary price: {len(at_max)} trades share maximal "
                f"timestamp {max_dt.isoformat()} with identical execution price {common_price}."
            ],
        )

    # Case C: multiple distinct prices at T* -> AMBIGUOUS_BOUNDARY_PRICE -> FAIL CLOSED
    return BoundaryCandidate(
        session_date=session_date.isoformat(),
        boundary_et=boundary_label,
        classification=BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE,
        selected_price=None,
        max_timestamp_utc=at_max[0].timestamp_utc,
        max_timestamp_et=max_dt.strftime("%Y-%m-%dT%H:%M:%S.%f %Z"),
        distance_to_boundary_seconds=str(delta_seconds),
        exact_boundary_timestamp_match=exact_match,
        boundary_tie_record_count=len(at_max),
        distinct_boundary_price_count=len(distinct_prices),
        exchange_set=exchanges,
        condition_set=all_conditions,
        tie_trade_ids=tie_ids,
        first_after_boundary_ts=first_after,
        notes=[
            f"AMBIGUOUS_BOUNDARY_PRICE: {len(at_max)} trades share maximal timestamp "
            f"{max_dt.isoformat()} with {len(distinct_prices)} distinct prices "
            f"{[str(p) for p in distinct_prices]}. Fail-closed."
        ],
    )


# ---------------------------------------------------------------------------
# Session-level qualification
# ---------------------------------------------------------------------------

def qualify_session_transactions(
    session_date: date,
    all_records: Sequence[RawSipTradeRecord],
    page_count: int,
    pagination_complete: bool,
) -> SessionTransactionQualification:
    """Produce the full transaction qualification for one session.

    Raises DataContractError if:
    - pagination is not complete
    - exact transport duplicates are found (detect_transport_duplicates > 0)
    - any boundary is MISSING or AMBIGUOUS_BOUNDARY_PRICE
    """
    assert_transaction_probe_date(session_date)

    if not pagination_complete:
        raise DataContractError(
            f"Pagination incomplete for session {session_date.isoformat()}. "
            f"Cannot finalise trade count or endpoint classification."
        )

    # Filter to regular session only
    session_records = filter_regular_session_records(list(all_records), session_date)
    total_raw = len(all_records)
    regular_count = len(session_records)

    # Exact transport duplicate check
    exact_transport_dups = detect_transport_duplicates(session_records)
    if exact_transport_dups > 0:
        raise DataContractError(
            f"Session {session_date.isoformat()}: {exact_transport_dups} exact transport "
            f"duplicate(s) detected. Pagination overlap or record corruption. Fail-closed."
        )

    # Diagnostic trade ID collisions (non-authoritative)
    id_diagnostics = detect_trade_id_collisions(session_records)

    # Censuses (purely descriptive)
    condition_census = build_condition_census(session_records)
    exchange_census = build_exchange_census(session_records)
    tape_census = build_tape_census(session_records)

    # Boundary endpoint classification
    b1000 = classify_boundary_endpoint(session_date, session_records, BOUNDARY_1000_ET)
    b1530 = classify_boundary_endpoint(session_date, session_records, BOUNDARY_1530_ET)

    # Fail closed on unresolvable boundaries
    if b1000.classification == BoundaryEndpointClassification.MISSING_PRE_BOUNDARY_TRANSACTION:
        raise DataContractError(
            f"Session {session_date.isoformat()}: MISSING pre-boundary transaction at 10:00 ET. "
            f"Endpoint mapping cannot be established. Fail-closed."
        )
    if b1000.classification == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE:
        raise DataContractError(
            f"Session {session_date.isoformat()}: AMBIGUOUS_BOUNDARY_PRICE at 10:00 ET — "
            f"multiple distinct prices at maximal timestamp. Fail-closed."
        )
    if b1530.classification == BoundaryEndpointClassification.MISSING_PRE_BOUNDARY_TRANSACTION:
        raise DataContractError(
            f"Session {session_date.isoformat()}: MISSING pre-boundary transaction at 15:30 ET. "
            f"Endpoint mapping cannot be established. Fail-closed."
        )
    if b1530.classification == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE:
        raise DataContractError(
            f"Session {session_date.isoformat()}: AMBIGUOUS_BOUNDARY_PRICE at 15:30 ET — "
            f"multiple distinct prices at maximal timestamp. Fail-closed."
        )

    return SessionTransactionQualification(
        session_date=session_date.isoformat(),
        total_raw_records=total_raw,
        regular_session_record_count=regular_count,
        exact_transport_duplicates=exact_transport_dups,
        trade_id_collision_diagnostics=id_diagnostics,
        page_count=page_count,
        pagination_complete=pagination_complete,
        condition_census=condition_census,
        exchange_census=exchange_census,
        tape_census=tape_census,
        boundary_1000=b1000,
        boundary_1530=b1530,
    )


# ---------------------------------------------------------------------------
# Aggregate probe synthesis
# ---------------------------------------------------------------------------

def synthesize_probe_result(
    probe_dates: Sequence[date],
    session_qualifications: Sequence[SessionTransactionQualification],
) -> TransactionContractProbeResult:
    """Synthesise per-session qualifications into an aggregate probe verdict."""
    endpoint_blockers: List[str] = []
    count_blockers: List[str] = []

    deterministic_classes = {
        BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE,
        BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE,
    }

    for sq in session_qualifications:
        if not sq.pagination_complete:
            count_blockers.append(
                f"{sq.session_date}: pagination not complete."
            )
        if sq.exact_transport_duplicates > 0:
            count_blockers.append(
                f"{sq.session_date}: {sq.exact_transport_duplicates} exact transport duplicate(s)."
            )
        if sq.regular_session_record_count < GAO_MIN_DAILY_TRADE_COUNT:
            count_blockers.append(
                f"{sq.session_date}: trade count {sq.regular_session_record_count} < {GAO_MIN_DAILY_TRADE_COUNT}."
            )
        if sq.boundary_1000.classification not in deterministic_classes:
            endpoint_blockers.append(
                f"{sq.session_date} @ 10:00 ET: {sq.boundary_1000.classification.value}"
            )
        if sq.boundary_1530.classification not in deterministic_classes:
            endpoint_blockers.append(
                f"{sq.session_date} @ 15:30 ET: {sq.boundary_1530.classification.value}"
            )

    endpoint_proposed = (
        EndpointMappingProposedClassification.QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY
        if not endpoint_blockers
        else EndpointMappingProposedClassification.UNRESOLVED_BOUNDARY_PRICE_AMBIGUITY
    )
    count_proposed = (
        TradeCountMappingProposedClassification.QUALIFIED_PROVIDER_OPERATIONALIZATION
        if not count_blockers
        else TradeCountMappingProposedClassification.UNRESOLVED
    )

    return TransactionContractProbeResult(
        probe_dates=[d.isoformat() for d in probe_dates],
        sessions=list(session_qualifications),
        endpoint_mapping_proposed=endpoint_proposed,
        trade_count_mapping_proposed=count_proposed,
        endpoint_blocker_notes=endpoint_blockers,
        trade_count_blocker_notes=count_blockers,
    )


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------

def build_transaction_contract_manifest(
    source_git_sha: str,
    probe_dates: List[str],
    raw_file_hashes: Dict[str, str],
    probe_result: TransactionContractProbeResult,
    generated_at_utc: str,
) -> Dict[str, Any]:
    """Assemble tracked cryptographic manifest for the transaction contract probe."""
    return {
        "manifest_type": "MEC_0014A_TRANSACTION_CONTRACT_QUALIFICATION_MANIFEST",
        "mec_id": "MEC-0014A",
        "topic": "Market Intraday Momentum — Alpaca SIP Transaction Endpoint & Trade-Count Contract",
        "source_git_sha": source_git_sha,
        "probe_dates": probe_dates,
        "alpaca_endpoint": f"/v2/stocks/{QUALIFIED_SYMBOL}/trades",
        "feed": QUALIFIED_FEED,
        "symbol": QUALIFIED_SYMBOL,
        "temporal_bounds": {
            "is_start": IS_START_DATE.isoformat(),
            "is_end": IS_END_DATE.isoformat(),
            "oos_sealed_boundary": OOS_FORBIDDEN_DATE.isoformat(),
        },
        "literature_contract": {
            "gao_endpoint_semantic": "POINT_TRANSACTION_PRICE_AT_HALF_HOUR_BOUNDARY",
            "gao_daily_trade_filter": f"DAILY_SPY_TRADE_COUNT >= {GAO_MIN_DAILY_TRADE_COUNT}",
        },
        "provider_contract_authorities": {
            "trade_id_ordering_authority": TRADE_ID_ORDERING_AUTHORITY,
            "exact_transport_duplicates_observed": EXACT_TRANSPORT_DUPLICATES_OBSERVED,
            "session_interval_predicate": SESSION_INTERVAL_PREDICATE,
            "session_interval_classification": SESSION_INTERVAL_CLASSIFICATION,
        },
        "raw_file_sha256_hashes": raw_file_hashes,
        "endpoint_mapping_proposed": probe_result.endpoint_mapping_proposed.value,
        "trade_count_mapping_proposed": probe_result.trade_count_mapping_proposed.value,
        "endpoint_blocker_notes": probe_result.endpoint_blocker_notes,
        "trade_count_blocker_notes": probe_result.trade_count_blocker_notes,
        "sessions_evaluated": [s.to_dict() for s in probe_result.sessions],
        "governance_invariants": {
            "OOS_accessed": False,
            "return_computed": False,
            "regression_computed": False,
            "HYP_004_created": False,
            "paper_authorized": False,
            "live_authorized": False,
            "capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
        "generated_at_utc": generated_at_utc,
    }


def compute_file_sha256(path: Path) -> str:
    """Read a file from disk and return its SHA-256 hex digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
