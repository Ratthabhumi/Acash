"""MEC-0014 Previous-Close and Market-Close Auction Data Contract Qualification.

This module implements the deterministic, fail-closed data contract qualification
probe for MEC-0014 (Market Intraday Momentum).

Contract Invariants:
1. Temporal Boundary: 2017-01-01 through 2022-12-31 ONLY. Any date >= 2023-01-01
   triggers an immediate fail-closed DataContractError.
2. Zero Strategy / Return Calculation: Strictly diagnostic price-equality analysis.
   Zero return (r1, r13), regression, breakout, signal, trade, or Sharpe calculations.
3. Deterministic Sample Selection: Uses NyseCa1Calendar exclusively. The sample consists
   of exactly the first regular 390-minute session of June for each year 2017–2022.
4. Provider Multi-Candidate Preservation: Alpaca historical auctions, daily SIP bars,
   and trade conditions (6, M, 9, X) are parsed without silent preference or truncation.
5. Secret Non-Leakage: API keys and secret tokens are never logged or serialized.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar, SessionType
from acash.execution.alpaca.credentials import AlpacaCredentials

NY_TZ = ZoneInfo("America/New_York")
IS_START_DATE: date = date(2017, 1, 1)
IS_END_DATE: date = date(2022, 12, 31)
OOS_FORBIDDEN_DATE: date = date(2023, 1, 1)

PROBE_YEARS: Tuple[int, ...] = (2017, 2018, 2019, 2020, 2021, 2022)


class CloseAuthorityClassification(str, Enum):
    """Authoritative classification of closing price candidates."""

    RESOLVED_FOR_SPY_TO_PRIMARY_LISTING_OFFICIAL_CLOSE = (
        "RESOLVED_FOR_SPY_TO_PRIMARY_LISTING_OFFICIAL_CLOSE"
    )
    RESOLVED_AUCTION_AUTHORITY = "RESOLVED_AUCTION_AUTHORITY"
    RESOLVED_DAILY_BAR_AUTHORITY = "RESOLVED_DAILY_BAR_AUTHORITY"
    RESOLVED_CLOSING_TRADE_AUTHORITY = "RESOLVED_CLOSING_TRADE_AUTHORITY"
    PARTIALLY_RESOLVED_MULTIPLE_EQUIVALENT_AUTHORITIES = (
        "PARTIALLY_RESOLVED_MULTIPLE_EQUIVALENT_AUTHORITIES"
    )
    UNRESOLVED_PROVIDER_SEMANTIC_AMBIGUITY = "UNRESOLVED_PROVIDER_SEMANTIC_AMBIGUITY"


@dataclass(frozen=True)
class AuctionRecord:
    """Parsed auction record from Alpaca Historical Auctions endpoint."""

    timestamp_utc: str
    price: Decimal
    size: int
    exchange: str
    condition: str
    auction_type: str  # 'c' for closing, 'o' for opening


@dataclass(frozen=True)
class ClosingTradeRecord:
    """Parsed raw trade record around market close."""

    timestamp_utc: str
    price: Decimal
    size: int
    exchange: str
    conditions: List[str]
    tape: str
    trade_id: int


@dataclass(frozen=True)
class MinuteBarRecord:
    """Parsed 1-minute SIP bar around market close."""

    timestamp_utc: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    trade_count: int
    vwap: Optional[Decimal]


@dataclass(frozen=True)
class DailyBarRecord:
    """Parsed 1-day SIP bar."""

    timestamp_utc: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    trade_count: int
    vwap: Optional[Decimal]


def assert_in_sample_probe_date(d: date) -> None:
    """Strictly fail-closed boundary enforcement on probe dates."""
    if d >= OOS_FORBIDDEN_DATE:
        raise DataContractError(
            f"Requested probe date {d.isoformat()} violates OOS boundary >= {OOS_FORBIDDEN_DATE.isoformat()}."
        )
    if d < IS_START_DATE or d > IS_END_DATE:
        raise DataContractError(
            f"Requested probe date {d.isoformat()} outside authorized IS window [{IS_START_DATE}, {IS_END_DATE}]."
        )


def select_mec_0014_probe_dates(
    calendar: Optional[NyseCa1Calendar] = None,
    years: Sequence[int] = PROBE_YEARS,
) -> List[date]:
    """Select the first valid regular 390-minute CA-1 session in June for each specified year.

    Pure deterministic calendar authority selection. Does not depend on market data,
    price, volatility, or external flags.
    """
    cal = calendar or NyseCa1Calendar()
    selected_dates: List[date] = []

    for year in years:
        if year < 2013 or year > 2026:
            raise DataContractError(f"Year {year} outside CA-1 calendar authority range.")
        curr = date(year, 6, 1)
        found = False
        while curr.month == 6:
            assert_in_sample_probe_date(curr)
            if cal.is_trading_session(curr):
                sess = cal.get_session(curr)
                if sess.session_type == SessionType.REGULAR and sess.expected_minute_count == 390:
                    selected_dates.append(curr)
                    found = True
                    break
            curr += timedelta(days=1)
        if not found:
            raise DataContractError(
                f"Failed to locate a regular 390-minute CA-1 session in June for year {year}."
            )

    if len(selected_dates) != len(years):
        raise DataContractError(
            f"Expected {len(years)} probe dates, got {len(selected_dates)}."
        )
    return selected_dates


def parse_auction_response(payload: Dict[str, Any]) -> List[AuctionRecord]:
    """Parse raw payload from Alpaca /v2/stocks/{symbol}/auctions endpoint.

    Preserves both closing ('c') and opening ('o') auctions without truncation.
    """
    records: List[AuctionRecord] = []
    auctions_list = payload.get("auctions", [])
    if isinstance(auctions_list, dict):
        # Fallback for multi-symbol shape
        for sym_auctions in auctions_list.values():
            if isinstance(sym_auctions, list):
                auctions_list = sym_auctions
                break

    for entry in auctions_list:
        if not isinstance(entry, dict):
            continue
        # Closing auctions
        for c_auc in entry.get("c") or []:
            records.append(
                AuctionRecord(
                    timestamp_utc=str(c_auc["t"]),
                    price=Decimal(str(c_auc["p"])),
                    size=int(c_auc["s"]),
                    exchange=str(c_auc["x"]),
                    condition=str(c_auc.get("c", "")),
                    auction_type="c",
                )
            )
        # Opening auctions
        for o_auc in entry.get("o") or []:
            records.append(
                AuctionRecord(
                    timestamp_utc=str(o_auc["t"]),
                    price=Decimal(str(o_auc["p"])),
                    size=int(o_auc["s"]),
                    exchange=str(o_auc["x"]),
                    condition=str(o_auc.get("c", "")),
                    auction_type="o",
                )
            )
    return records


def parse_daily_bar_response(payload: Dict[str, Any], symbol: str = "SPY") -> DailyBarRecord:
    """Parse raw payload from Alpaca /v2/stocks/{symbol}/bars?timeframe=1Day endpoint."""
    bars = payload.get("bars", [])
    if isinstance(bars, dict):
        bars = bars.get(symbol, [])
    if not bars:
        raise DataContractError(f"No daily bar returned in payload for symbol {symbol}.")
    b = bars[0]
    return DailyBarRecord(
        timestamp_utc=str(b["t"]),
        open=Decimal(str(b["o"])),
        high=Decimal(str(b["h"])),
        low=Decimal(str(b["l"])),
        close=Decimal(str(b["c"])),
        volume=int(b["v"]),
        trade_count=int(b.get("n", 0)),
        vwap=Decimal(str(b["vw"])) if "vw" in b and b["vw"] is not None else None,
    )


def parse_minute_bars_response(
    payload: Dict[str, Any], symbol: str = "SPY"
) -> List[MinuteBarRecord]:
    """Parse raw payload from Alpaca /v2/stocks/{symbol}/bars?timeframe=1Min endpoint."""
    bars = payload.get("bars", [])
    if isinstance(bars, dict):
        bars = bars.get(symbol, [])
    records: List[MinuteBarRecord] = []
    for b in bars:
        records.append(
            MinuteBarRecord(
                timestamp_utc=str(b["t"]),
                open=Decimal(str(b["o"])),
                high=Decimal(str(b["h"])),
                low=Decimal(str(b["l"])),
                close=Decimal(str(b["c"])),
                volume=int(b["v"]),
                trade_count=int(b.get("n", 0)),
                vwap=Decimal(str(b["vw"])) if "vw" in b and b["vw"] is not None else None,
            )
        )
    return records


def parse_trades_response(payload: Dict[str, Any], symbol: str = "SPY") -> List[ClosingTradeRecord]:
    """Parse raw payload from Alpaca /v2/stocks/{symbol}/trades endpoint."""
    trades = payload.get("trades", [])
    if isinstance(trades, dict):
        trades = trades.get(symbol, [])
    records: List[ClosingTradeRecord] = []
    for t in trades:
        conditions = [str(c).strip() for c in t.get("c", []) if str(c).strip()]
        records.append(
            ClosingTradeRecord(
                timestamp_utc=str(t["t"]),
                price=Decimal(str(t["p"])),
                size=int(t["s"]),
                exchange=str(t["x"]),
                conditions=conditions,
                tape=str(t.get("z", "")),
                trade_id=int(t.get("i", 0)),
            )
        )
    return records


def compute_pairwise_diagnostic(
    name_a: str, price_a: Optional[Decimal], name_b: str, price_b: Optional[Decimal]
) -> Dict[str, Any]:
    """Compute price equality, absolute difference, and basis points difference.

    Strictly price-space diagnostic. Does NOT calculate returns or strategy metrics.
    """
    if price_a is None or price_b is None:
        return {
            "pair": f"{name_a} vs {name_b}",
            "available": False,
            "exact_equality": False,
            "price_a": str(price_a) if price_a is not None else None,
            "price_b": str(price_b) if price_b is not None else None,
            "abs_difference": None,
            "difference_bps": None,
        }

    exact_equality = (price_a == price_b)
    abs_diff = abs(price_a - price_b)
    # Basis point difference relative to price_a
    ref_price = price_a if price_a != Decimal("0") else Decimal("1")
    bps = (abs_diff / ref_price) * Decimal("10000")
    bps_rounded = bps.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    return {
        "pair": f"{name_a} vs {name_b}",
        "available": True,
        "exact_equality": exact_equality,
        "price_a": str(price_a),
        "price_b": str(price_b),
        "abs_difference": str(abs_diff),
        "difference_bps": str(bps_rounded),
    }


@dataclass
class SessionContractComparison:
    """Full contract comparison diagnostics for a single regular session."""

    session_date: str
    p_1559_close: Optional[Decimal]
    p_1600_minute_close: Optional[Decimal]
    p_daily_close: Decimal
    auction_closing_candidates: List[Dict[str, Any]]
    condition6_candidates: List[Dict[str, Any]]
    conditionM_candidates: List[Dict[str, Any]]
    condition9_candidates: List[Dict[str, Any]]
    cross_trade_candidates: List[Dict[str, Any]]
    minute_bar_1559_found: bool
    minute_bar_1600_found: bool
    comparisons: Dict[str, Dict[str, Any]]
    notes: List[str]


def compare_session_close_contract(
    session_date: date,
    daily_bar: DailyBarRecord,
    minute_bars: Sequence[MinuteBarRecord],
    auctions: Sequence[AuctionRecord],
    trades: Sequence[ClosingTradeRecord],
) -> SessionContractComparison:
    """Execute exhaustive contract price-equality diagnostics for one session."""
    assert_in_sample_probe_date(session_date)

    # 1. Extract 15:59 and 16:00 minute bars in local ET
    # Minute bars are tagged with start timestamp in UTC.
    # Regular close is 16:00 ET. In EDT (June), 15:59 ET is 19:59:00 UTC, 16:00 ET is 20:00:00 UTC.
    p_1559: Optional[Decimal] = None
    p_1600: Optional[Decimal] = None
    bar_1559_found = False
    bar_1600_found = False

    for mb in minute_bars:
        # Convert timestamp to NY local
        dt = datetime.fromisoformat(mb.timestamp_utc.replace("Z", "+00:00")).astimezone(NY_TZ)
        if dt.time() == time(15, 59, 0):
            p_1559 = mb.close
            bar_1559_found = True
        elif dt.time() == time(16, 0, 0):
            p_1600 = mb.close
            bar_1600_found = True

    # 2. Extract closing auction candidates
    closing_auctions = [a for a in auctions if a.auction_type == "c"]
    auction_dicts: List[Dict[str, Any]] = [
        {
            "timestamp": a.timestamp_utc,
            "price": str(a.price),
            "size": a.size,
            "exchange": a.exchange,
            "condition": a.condition,
        }
        for a in closing_auctions
    ]

    # Primary auction candidate (listing exchange P = NYSE Arca for SPY)
    # Prioritize condition '6' (actual closing auction trade) over off-hours/midnight summary reports
    primary_auction_price: Optional[Decimal] = None
    for a in closing_auctions:
        if a.exchange == "P" and a.condition == "6":
            primary_auction_price = a.price
            break
    if primary_auction_price is None:
        for a in closing_auctions:
            if a.exchange == "P" and "T00:00" not in a.timestamp_utc:
                primary_auction_price = a.price
                break
    if primary_auction_price is None and closing_auctions:
        primary_auction_price = closing_auctions[0].price

    # 3. Extract trade candidates by condition
    c6_trades = [t for t in trades if "6" in t.conditions]
    cM_trades = [t for t in trades if "M" in t.conditions]
    c9_trades = [t for t in trades if "9" in t.conditions]
    cX_trades = [t for t in trades if "X" in t.conditions]

    c6_dicts = [
        {"timestamp": t.timestamp_utc, "price": str(t.price), "size": t.size, "exchange": t.exchange, "conditions": t.conditions}
        for t in c6_trades
    ]
    cM_dicts = [
        {"timestamp": t.timestamp_utc, "price": str(t.price), "size": t.size, "exchange": t.exchange, "conditions": t.conditions}
        for t in cM_trades
    ]
    c9_dicts = [
        {"timestamp": t.timestamp_utc, "price": str(t.price), "size": t.size, "exchange": t.exchange, "conditions": t.conditions}
        for t in c9_trades
    ]
    cX_dicts = [
        {"timestamp": t.timestamp_utc, "price": str(t.price), "size": t.size, "exchange": t.exchange, "conditions": t.conditions}
        for t in cX_trades
    ]

    p_c6: Optional[Decimal] = None
    # Prioritize listing market exchange P
    for t in c6_trades:
        if t.exchange == "P":
            p_c6 = t.price
            break
    if p_c6 is None and c6_trades:
        p_c6 = c6_trades[0].price

    p_cM: Optional[Decimal] = None
    for t in cM_trades:
        if t.exchange == "P":
            p_cM = t.price
            break
    if p_cM is None and cM_trades:
        p_cM = cM_trades[0].price

    p_c9: Optional[Decimal] = c9_trades[0].price if c9_trades else None

    # 4. Pairwise diagnostics
    comparisons: Dict[str, Dict[str, Any]] = {
        "daily_vs_1559": compute_pairwise_diagnostic("daily_close", daily_bar.close, "1559_close", p_1559),
        "daily_vs_1600_minute": compute_pairwise_diagnostic("daily_close", daily_bar.close, "1600_minute_close", p_1600),
        "daily_vs_auction": compute_pairwise_diagnostic("daily_close", daily_bar.close, "auction_primary", primary_auction_price),
        "daily_vs_condition6": compute_pairwise_diagnostic("daily_close", daily_bar.close, "condition6_primary", p_c6),
        "daily_vs_conditionM": compute_pairwise_diagnostic("daily_close", daily_bar.close, "conditionM_primary", p_cM),
        "daily_vs_condition9": compute_pairwise_diagnostic("daily_close", daily_bar.close, "condition9", p_c9),
        "auction_vs_1559": compute_pairwise_diagnostic("auction_primary", primary_auction_price, "1559_close", p_1559),
        "auction_vs_condition6": compute_pairwise_diagnostic("auction_primary", primary_auction_price, "condition6_primary", p_c6),
        "auction_vs_conditionM": compute_pairwise_diagnostic("auction_primary", primary_auction_price, "conditionM_primary", p_cM),
        "auction_vs_condition9": compute_pairwise_diagnostic("auction_primary", primary_auction_price, "condition9", p_c9),
    }

    notes: List[str] = []
    if len(closing_auctions) > 1:
        notes.append(f"Multiple closing auction candidates found: {len(closing_auctions)} venues.")
    if c9_trades:
        notes.append(f"Condition 9 (Corrected Close) trades observed: {len(c9_trades)} records.")
    if bar_1600_found:
        notes.append("Minute bar at 16:00 ET is present.")
    if not bar_1559_found:
        notes.append("WARNING: 15:59 ET minute bar missing.")

    return SessionContractComparison(
        session_date=session_date.isoformat(),
        p_1559_close=p_1559,
        p_1600_minute_close=p_1600,
        p_daily_close=daily_bar.close,
        auction_closing_candidates=auction_dicts,
        condition6_candidates=c6_dicts,
        conditionM_candidates=cM_dicts,
        condition9_candidates=c9_dicts,
        cross_trade_candidates=cX_dicts,
        minute_bar_1559_found=bar_1559_found,
        minute_bar_1600_found=bar_1600_found,
        comparisons=comparisons,
        notes=notes,
    )


def compute_raw_evidence_sha256(raw_bytes_list: Sequence[bytes]) -> str:
    """Compute deterministic SHA-256 over combined raw response payloads."""
    hasher = hashlib.sha256()
    for b in sorted(raw_bytes_list):
        hasher.update(b)
    return hasher.hexdigest()


def build_mec_0014_manifest(
    source_git_sha: str,
    selected_six_dates: List[str],
    alpaca_endpoints: List[str],
    response_schemas: Dict[str, List[str]],
    raw_evidence_aggregate_hash: str,
    comparison_result_hash: str,
    previous_close_authority: CloseAuthorityClassification,
    target_close_authority: CloseAuthorityClassification,
    generated_at_utc: str,
) -> Dict[str, Any]:
    """Assemble tracked cryptographic manifest for MEC-0014 close contract probe."""
    return {
        "manifest_type": "MEC_0014_CLOSE_AUCTION_CONTRACT_MANIFEST",
        "mec_id": "MEC-0014",
        "topic": "Market Intraday Momentum — Previous-Close / Auction Contract Qualification",
        "source_git_sha": source_git_sha,
        "selected_six_dates": selected_six_dates,
        "alpaca_endpoint_names": alpaca_endpoints,
        "feed": "sip",
        "adjustment": "raw",
        "response_schema_fingerprints": response_schemas,
        "raw_evidence_aggregate_hash": raw_evidence_aggregate_hash,
        "comparison_result_hash": comparison_result_hash,
        "previous_close_authority": previous_close_authority.value,
        "target_close_authority": target_close_authority.value,
        "temporal_bounds": {
            "is_start": IS_START_DATE.isoformat(),
            "is_end": IS_END_DATE.isoformat(),
            "oos_sealed_boundary": OOS_FORBIDDEN_DATE.isoformat(),
        },
        "governance_invariants": {
            "OOS_accessed": False,
            "empirical_strategy_calculation": False,
            "paper_authorized": False,
            "live_authorized": False,
            "capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
        "generated_at_utc": generated_at_utc,
    }
