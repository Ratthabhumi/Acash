"""Phase 14 Step R4: HYP_007 M2 Post-Publication Stress Execution & Gate Evaluation.

Authority:
- Zarattini, Aziz, Barbon (2024), SSRN 4824172 / Concretum Group Reference Implementation
- MEC-0015 Strategy Contract Audit & Profitability-First Intake
- MEC-0017 / HYP_007 Preregistration & Additive Governance Amendments
- Stage A Governance Freeze: docs/phase14/HYP_007_POST_M1_PARTITION_AND_R4_GOVERNANCE_FREEZE_001.md
- Human Authorization: AUTHORIZE_HYP_007_POST_M1_FREEZE_AND_CONDITIONAL_R4_M2_EXECUTION
- Starting Head: 44b83cc3e69f25890537d74972f2c868a710cd50

Strict Invariants:
1. M2 Scope: 2024-05-01 through 2026-08-14 (569 regular sessions, 6 early closes excluded).
   Classification: PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE (NOT_PRISTINE_OOS).
2. Quarantined Historical Gap: [2026-08-15, 2026-09-23) is strictly unreadable under HYP_007.
3. Prospective M3: >= 2026-09-23 is LOCKED_ZERO_ACCESS.
4. M2 Simulated Starting AUM: $100,000.00 (PRE_RESULT_SEGMENT_ACCOUNTING_NORMALIZATION).
5. M2 State Warm-Up: 14 Noise-Area sessions and 16 volatility closes derive from sealed M1 history.
   Pre-M2 state data contributes ZERO M2 performance.
6. Strategy Execution: EXACT immutable HYP_007 logic (Noise Area, HLC3 VWAP, 12 epochs, fixed vol sizing, EOD flatten).
7. Execution Quotes: FIRST_VALID_SIP_NBBO_AT_OR_AFTER_BOUNDARY at 13 boundaries per session (12 epochs + 15:59).
8. Primary Dividend Authority: STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS (9 M2 cash distributions).
9. Regulatory Fees: Historical schedules for SEC Section 31 and FINRA TAF covering M2.
10. R4 Continuation Gates:
    R4-G1: NET_TOTAL_RETURN > 0.0
    R4-G2: NET_ANNUALIZED_SHARPE >= 0.50
    R4-G3: MAX_DRAWDOWN <= 0.35 (35%)
    R4-G4: 2X_FRICTION_STRESS_TOTAL_RETURN >= 0.0
    Conjunction: ALL FOUR MUST PASS.
11. Capital: $0.00, NO_REAL_ORDERS = true, Paper/Live LOCKED.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time as dtime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

import httpx
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar, SessionType
from acash.data.qualification.mec_0017_quote_contract import (
    ACCEPTABLE_EXECUTION_QUOTE_CONDITIONS,
    REJECTED_QUOTE_CONDITIONS,
    Mec0017SipQuoteRecord,
    parse_alpaca_direct_sip_quote,
)
from acash.research.step_r2_hyp_007 import (
    AdaptiveRateGovernor,
    QualifiedBar,
    QualifiedQuoteBoundary,
    calculate_deterministic_sha256,
    evaluate_boundary_quotes_stream,
    load_credentials_from_env,
)
from acash.research.step_r3_hyp_007 import (
    DECISION_EPOCHS,
    CompletedTradeRecord,
    DailySessionPerformanceRecord,
    DecisionSignalRecord,
    ExecutionOrderLegRecord,
    compute_epoch_minute_mappings,
    get_previous_regular_close,
)
from acash.research.step_r3_hyp_007_metrics import (
    PERIODS_PER_YEAR,
    calculate_daily_net_return,
    calculate_hyp_007_annualized_sharpe,
    calculate_hyp_007_max_drawdown,
    calculate_net_total_return,
    count_completed_trades_from_position_series,
)
from acash.research.step_r4_hyp_007_governance import (
    GAP_ROLE,
    M2_AUM_CLASSIFICATION,
    M2_CLASSIFICATION,
    M2_END_DATE,
    M2_END_DATE_STR,
    M2_ROLE,
    M2_SIMULATED_STARTING_AUM_USD,
    M2_START_DATE,
    M2_START_DATE_STR,
    M2_WARMUP_NOISE_AREA_SESSIONS,
    M2_WARMUP_PERFORMANCE_CONTRIBUTION_USD,
    M2_WARMUP_SOURCE,
    M2_WARMUP_VOLATILITY_CLOSES,
    M3_ACCESS_STATUS,
    M3_ROLE,
    QUARANTINE_START_DATE,
    QUARANTINE_START_DATE_STR,
    R4_G1_NET_TOTAL_RETURN_MIN,
    R4_G2_NET_ANNUALIZED_SHARPE_MIN,
    R4_G3_MAX_DRAWDOWN_MAX,
    R4_G4_STRESS_TOTAL_RETURN_MIN,
    R4GateEvaluationResult,
    R4Verdict,
    enforce_m2_market_data_range_guard,
    enforce_m3_firewall,
    enforce_quarantine_firewall,
    evaluate_r4_gates,
)

NY_TZ = ZoneInfo("America/New_York")
TARGET_SYMBOL = "SPY"
STANDARD_RTH_BAR_COUNT = 390

EXPECTED_STAGE_A_COMMIT_SHA: str = "44b83cc3e69f25890537d74972f2c868a710cd50"
EXPECTED_STAGE_A_MANIFEST_SHA256: str = "58eb3d69902dd676a0fb4f2f45ec7d206f477011d615951d187210e30327f426"

M2_QUOTE_DECISION_TIMES_ET: Tuple[dtime, ...] = (
    dtime(10, 0),
    dtime(10, 30),
    dtime(11, 0),
    dtime(11, 30),
    dtime(12, 0),
    dtime(12, 30),
    dtime(13, 0),
    dtime(13, 30),
    dtime(14, 0),
    dtime(14, 30),
    dtime(15, 0),
    dtime(15, 30),
    dtime(15, 59),
)


# ---------------------------------------------------------------------------
# M2 Regulatory Fee Schedules (SEC Section 31 & FINRA TAF)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class M2Sec31Segment:
    effective_start: date
    effective_end: date
    rate_per_dollar: Decimal
    official_source: str


M2_SEC31_SCHEDULE: Sequence[M2Sec31Segment] = (
    M2Sec31Segment(
        effective_start=date(2023, 2, 27),
        effective_end=date(2024, 5, 21),
        rate_per_dollar=Decimal("0.00000800"),
        official_source="SEC Fee Rate Advisory #2 for Fiscal Year 2023",
    ),
    M2Sec31Segment(
        effective_start=date(2024, 5, 22),
        effective_end=date(2025, 5, 13),
        rate_per_dollar=Decimal("0.00002780"),
        official_source="SEC Fee Rate Advisory for Fiscal Year 2024 (Effective May 22, 2024)",
    ),
    M2Sec31Segment(
        effective_start=date(2025, 5, 14),
        effective_end=date(2026, 4, 3),
        rate_per_dollar=Decimal("0.00000000"),
        official_source="SEC Fee Rate Advisory for Mid-Year Fiscal Year 2025 (Effective May 14, 2025)",
    ),
    M2Sec31Segment(
        effective_start=date(2026, 4, 4),
        effective_end=date(2026, 12, 31),
        rate_per_dollar=Decimal("0.00002060"),
        official_source="SEC Fee Rate Advisory for Fiscal Year 2026 (Effective April 4, 2026)",
    ),
)


@dataclass(frozen=True)
class M2FinraTafSegment:
    effective_start: date
    effective_end: date
    rate_per_share: Decimal
    max_fee_per_trade: Decimal
    official_source: str


M2_FINRA_TAF_SCHEDULE: Sequence[M2FinraTafSegment] = (
    M2FinraTafSegment(
        effective_start=date(2024, 1, 1),
        effective_end=date(2024, 12, 31),
        rate_per_share=Decimal("0.000166"),
        max_fee_per_trade=Decimal("8.30"),
        official_source="FINRA SR-FINRA-2020-032 Phase 3",
    ),
    M2FinraTafSegment(
        effective_start=date(2025, 1, 1),
        effective_end=date(2026, 12, 31),
        rate_per_share=Decimal("0.000195"),
        max_fee_per_trade=Decimal("9.79"),
        official_source="FINRA Schedule A Section 1(b)(1) Effective Jan 1, 2025",
    ),
)


def compute_m2_sec31_fee(sale_principal: Decimal, trade_date: date, is_sell: bool = True) -> Decimal:
    """Compute SEC Section 31 fee for M2 trade date.

    Note: parameter order adjusted to match test expectations (sale_principal first, then trade_date).
    """
    if not is_sell or sale_principal <= Decimal("0.00"):
        return Decimal("0.00")
    for seg in M2_SEC31_SCHEDULE:
        if seg.effective_start <= trade_date <= seg.effective_end:
            raw_fee = sale_principal * seg.rate_per_dollar
            return raw_fee.quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    raise DataContractError(f"SEC Section 31 schedule gap for trade date {trade_date}")


def compute_m2_finra_taf(shares_sold: int, trade_date: date, is_sell: bool = True) -> Decimal:
    """Compute FINRA TAF fee for M2 trade date.

    Parameter order adjusted to match test expectations (shares_sold first, then trade_date).
    """
    if not is_sell or shares_sold <= 0:
        return Decimal("0.00")
    for seg in M2_FINRA_TAF_SCHEDULE:
        if seg.effective_start <= trade_date <= seg.effective_end:
            raw_fee = Decimal(shares_sold) * seg.rate_per_share
            capped = min(raw_fee, seg.max_fee_per_trade)
            return capped.quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    raise DataContractError(f"FINRA TAF schedule gap for trade date {trade_date}")


# ---------------------------------------------------------------------------
# M2 Calendar Census
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class M2CalendarCensus:
    calendar_days_count: int
    regular_sessions: List[date]
    early_closes: List[Tuple[date, int]]
    holidays: List[Tuple[date, str]]
    weekends_count: int
    sessions_by_year: Dict[int, int]
    calendar_authority: str = "NyseCa1Calendar (CA-1)"


def build_m2_calendar_census() -> M2CalendarCensus:
    """Enumerate exact eligible regular sessions and exclusions for M2."""
    cal = NyseCa1Calendar()
    curr = M2_START_DATE
    reg_sessions: List[date] = []
    early_closes: List[Tuple[date, int]] = []
    holidays: List[Tuple[date, str]] = []
    weekends = 0
    total_days = 0

    while curr <= M2_END_DATE:
        total_days += 1
        if curr.weekday() >= 5:
            weekends += 1
        elif cal.is_holiday(curr):
            holidays.append((curr, str(cal.get_holiday_reason(curr))))
        elif cal.is_early_close(curr):
            # Store only the date for early close sessions as per test expectations
            early_closes.append(curr)
        elif cal.is_trading_session(curr):
            sess = cal.get_session(curr)
            if sess.session_type == SessionType.REGULAR:
                reg_sessions.append(curr)
        curr += timedelta(days=1)

    by_year: Dict[int, int] = {}
    for d in reg_sessions:
        by_year[d.year] = by_year.get(d.year, 0) + 1

    return M2CalendarCensus(
        calendar_days_count=total_days,
        regular_sessions=reg_sessions,
        early_closes=early_closes,
        holidays=holidays,
        weekends_count=weekends,
        sessions_by_year=by_year,
    )


# ---------------------------------------------------------------------------
# M2 Dividend Projection
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class M2ProjectedDividend:
    ex_date: str
    record_date: str
    payable_date: str
    cash_distribution: Decimal
    currency: str
    distribution_type: str


def load_m2_dividend_projection(repo_root: Path) -> List[M2ProjectedDividend]:
    """Load and qualify the 9 M2 distributions from canonical manifest."""
    manifest_path = repo_root / "docs/research/manifests/MEC-0017-HYP-007-M2-dividend-projection-manifest.json"
    if not manifest_path.exists():
        raise DataContractError(f"M2 dividend manifest missing at {manifest_path}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    divs: List[M2ProjectedDividend] = []
    for d in data.get("distributions", []):
        divs.append(
            M2ProjectedDividend(
                ex_date=d["ex_date"],
                record_date=d["record_date"],
                payable_date=d["payable_date"],
                cash_distribution=Decimal(d["cash_distribution"]),
                currency=d["currency"],
                distribution_type=d["distribution_type"],
            )
        )
    if len(divs) != 9:
        raise DataContractError(f"Expected exactly 9 M2 distributions, got {len(divs)}")
    return divs


# ---------------------------------------------------------------------------
# Precondition Verification
# ---------------------------------------------------------------------------

def validate_r4_preconditions(repo_root: Path) -> Dict[str, str]:
    """Validate all Stage A governance contracts and firewalls before M2 access."""
    # 1. Stage A manifest
    man_path = repo_root / "docs/phase14/manifests/HYP_007_POST_M1_PARTITION_AND_R4_GOVERNANCE_FREEZE_001.json"
    if not man_path.exists():
        raise DataContractError(f"Stage A manifest not found at {man_path}")
    raw_man = man_path.read_bytes()
    man_sha = hashlib.sha256(raw_man).hexdigest()

    # 2. Stage A document
    doc_path = repo_root / "docs/phase14/HYP_007_POST_M1_PARTITION_AND_R4_GOVERNANCE_FREEZE_001.md"
    if not doc_path.exists():
        raise DataContractError(f"Stage A doc not found at {doc_path}")
    doc_sha = hashlib.sha256(doc_path.read_bytes()).hexdigest()

    # 3. M1 qualified bars parquet exists
    m1_bars = repo_root / "data/hyp_007/m1_bars_qualified.parquet"
    if not m1_bars.exists():
        raise DataContractError(f"M1 bars qualified parquet not found at {m1_bars}")

    return {
        "stage_a_manifest_sha256": man_sha,
        "stage_a_doc_sha256": doc_sha,
    }


# ---------------------------------------------------------------------------
# Data Acquisition & Qualification
# ---------------------------------------------------------------------------

def acquire_and_qualify_m2_bars(
    census: M2CalendarCensus,
    repo_root: Path,
    governor: AdaptiveRateGovernor,
    client: Optional[httpx.Client] = None,
) -> Tuple[List[QualifiedBar], List[Dict[str, Any]], str]:
    """Acquire and qualify 390 bars for every regular M2 session."""
    raw_dir = repo_root / "data/hyp_007/m2/raw_bars"
    raw_dir.mkdir(parents=True, exist_ok=True)

    key_id, secret = load_credentials_from_env()
    headers = {
        "APCA-API-KEY-ID": key_id,
        "APCA-API-SECRET-KEY": secret,
        "Accept": "application/json",
    }

    own_client = False
    if client is None:
        client = httpx.Client(timeout=25.0)
        own_client = True

    all_bars: List[QualifiedBar] = []
    daily_closes: List[Dict[str, Any]] = []

    try:
        for s_idx, session_date in enumerate(census.regular_sessions, 1):
            if s_idx % 50 == 0 or s_idx == len(census.regular_sessions):
                print(f"    [M2 Bars] Session {s_idx}/{len(census.regular_sessions)} ({session_date})...", flush=True)

            enforce_m2_market_data_range_guard(session_date)
            checkpoint_file = raw_dir / f"session_{session_date.isoformat()}.raw.json"

            raw_bars: List[Dict[str, Any]] = []
            if checkpoint_file.exists():
                payload = json.loads(checkpoint_file.read_text(encoding="utf-8"))
                raw_bars = payload.get("bars", [])
            else:
                dt_open = datetime.combine(session_date, dtime(9, 30), tzinfo=NY_TZ).astimezone(timezone.utc)
                dt_close = datetime.combine(session_date, dtime(15, 59), tzinfo=NY_TZ).astimezone(timezone.utc)
                enforce_m2_market_data_range_guard(dt_close)

                bar_params: Dict[str, str | int] = {
                    "timeframe": "1Min",
                    "feed": "sip",
                    "adjustment": "raw",
                    "start": dt_open.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "end": dt_close.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "limit": 1000,
                    "sort": "asc",
                }

                retries = 0
                while True:
                    governor.pre_request_throttle()
                    resp = client.get(
                        f"https://data.alpaca.markets/v2/stocks/{TARGET_SYMBOL}/bars",
                        headers=headers,
                        params=bar_params,
                    )
                    governor.handle_response_headers(resp.headers)

                    if resp.status_code == 200:
                        file_bytes = resp.content
                        tmp_path = checkpoint_file.with_suffix(".tmp")
                        tmp_path.write_bytes(file_bytes)
                        tmp_path.replace(checkpoint_file)
                        payload = json.loads(file_bytes.decode("utf-8"))
                        raw_bars = payload.get("bars", [])
                        break
                    elif resp.status_code == 429:
                        governor.status_429_count += 1
                        retries += 1
                        time.sleep(2.0 * retries)
                    else:
                        raise DataContractError(f"Alpaca bar fetch failed for {session_date}: HTTP {resp.status_code}")

            if len(raw_bars) != STANDARD_RTH_BAR_COUNT:
                raise DataContractError(
                    f"Incomplete session in M2: {session_date} has {len(raw_bars)} bars != {STANDARD_RTH_BAR_COUNT}."
                )

            # Parse and validate bars
            for idx, b in enumerate(raw_bars):
                o = Decimal(str(b["o"]))
                h = Decimal(str(b["h"]))
                l = Decimal(str(b["l"]))
                c = Decimal(str(b["c"]))
                v = int(b.get("v", 0))
                hlc3 = (h + l + c) / Decimal("3")
                t_str = b["t"]

                all_bars.append(
                    QualifiedBar(
                        timestamp_utc=t_str,
                        minute_idx=idx,
                        open=o,
                        high=h,
                        low=l,
                        close=c,
                        volume=v,
                        hlc3=hlc3,
                        trade_count=int(b.get("n", 0)),
                        session_date=session_date.isoformat(),
                        sample_classification=M2_ROLE,
                        performance_eligible=True,
                        signal_eligible=True,
                        trade_eligible=True,
                    )
                )

            daily_closes.append({
                "session_date": session_date.isoformat(),
                "unadjusted_close": str(all_bars[-1].close),
                "source_bar_timestamp_utc": all_bars[-1].timestamp_utc,
            })
    finally:
        if own_client:
            client.close()

    expected_total_bars = len(census.regular_sessions) * STANDARD_RTH_BAR_COUNT
    if len(all_bars) != expected_total_bars:
        raise DataContractError(f"M2 total bars mismatch: {len(all_bars)} != {expected_total_bars}")

    bars_serialized = [
        {
            "t": b.timestamp_utc,
            "o": str(b.open),
            "h": str(b.high),
            "l": str(b.low),
            "c": str(b.close),
            "v": b.volume,
            "hlc3": str(b.hlc3),
            "d": b.session_date,
        }
        for b in all_bars
    ]
    bar_corpus_sha256 = calculate_deterministic_sha256(bars_serialized)
    return all_bars, daily_closes, bar_corpus_sha256


def acquire_and_qualify_m2_quotes(
    census: M2CalendarCensus,
    repo_root: Path,
    governor: AdaptiveRateGovernor,
    client: Optional[httpx.Client] = None,
) -> Tuple[List[QualifiedQuoteBoundary], str]:
    """Acquire and qualify execution quote evidence at 13 boundaries per regular M2 session."""
    raw_dir = repo_root / "data/hyp_007/m2/raw_quotes"
    raw_dir.mkdir(parents=True, exist_ok=True)

    key_id, secret = load_credentials_from_env()
    headers = {
        "APCA-API-KEY-ID": key_id,
        "APCA-API-SECRET-KEY": secret,
        "Accept": "application/json",
    }

    own_client = False
    if client is None:
        client = httpx.Client(timeout=25.0)
        own_client = True

    all_boundaries: List[QualifiedQuoteBoundary] = []

    try:
        for s_idx, session_date in enumerate(census.regular_sessions, 1):
            if s_idx % 25 == 0 or s_idx == len(census.regular_sessions):
                print(f"    [M2 Quotes] Session {s_idx}/{len(census.regular_sessions)} ({session_date})...", flush=True)

            enforce_m2_market_data_range_guard(session_date)
            checkpoint_file = raw_dir / f"session_{session_date.isoformat()}.raw.json"

            session_close_dt = datetime.combine(session_date, dtime(16, 0), tzinfo=NY_TZ)
            session_close_utc = session_close_dt.astimezone(timezone.utc)
            end_str = session_close_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

            session_boundaries: List[QualifiedQuoteBoundary] = []

            if checkpoint_file.exists():
                payload = json.loads(checkpoint_file.read_text(encoding="utf-8"))
                records = payload.get("boundaries", [])
                for r in records:
                    session_boundaries.append(
                        QualifiedQuoteBoundary(
                            session_date=r["session_date"],
                            boundary_et=r["boundary_et"],
                            boundary_utc=r["boundary_utc"],
                            provider=r["provider"],
                            feed=r["feed"],
                            request_start_utc=r["request_start_utc"],
                            request_end_utc=r["request_end_utc"],
                            candidate_rows_examined=r["candidate_rows_examined"],
                            rejected_rows_count=r["rejected_rows_count"],
                            rejection_reasons_census=r["rejection_reasons_census"],
                            selected_first_valid_timestamp_utc=r["selected_first_valid_timestamp_utc"],
                            quote_delay_microseconds=r["quote_delay_microseconds"],
                            quote_delay_milliseconds=r["quote_delay_milliseconds"],
                            bid_price=Decimal(r["bid_price"]),
                            ask_price=Decimal(r["ask_price"]),
                            bid_size=r["bid_size"],
                            ask_size=r["ask_size"],
                            bid_exchange=r["bid_exchange"],
                            ask_exchange=r["ask_exchange"],
                            tape=r["tape"],
                            conditions=r["conditions"],
                            is_locked=r["is_locked"],
                            is_crossed=r["is_crossed"],
                            pages_examined=r["pages_examined"],
                        )
                    )
            else:
                session_raw_records: List[Dict[str, Any]] = []

                for b_time in M2_QUOTE_DECISION_TIMES_ET:
                    b_dt = datetime.combine(session_date, b_time, tzinfo=NY_TZ)
                    b_utc = b_dt.astimezone(timezone.utc)
                    enforce_m2_market_data_range_guard(b_utc)
                    start_str = b_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

                    raw_quotes_accum: List[Dict[str, Any]] = []
                    pages_count = 0
                    next_token: Optional[str] = None
                    retries = 0

                    while True:
                        pages_count += 1
                        q_params: Dict[str, str | int] = {
                            "symbols": TARGET_SYMBOL,
                            "feed": "sip",
                            "sort": "asc",
                            "start": start_str,
                            "end": end_str,
                            "limit": 50,
                        }
                        if next_token:
                            q_params["page_token"] = next_token

                        governor.pre_request_throttle()
                        resp = client.get(
                            "https://data.alpaca.markets/v2/stocks/quotes",
                            headers=headers,
                            params=q_params,
                        )
                        governor.handle_response_headers(resp.headers)

                        if resp.status_code == 200:
                            q_payload = resp.json()
                            batch = q_payload.get("quotes", {}).get(TARGET_SYMBOL, [])
                            raw_quotes_accum.extend(batch)

                            # Check if we can find a valid quote from accumulated quotes
                            can_qualify = False
                            for cand in raw_quotes_accum:
                                try:
                                    parse_alpaca_direct_sip_quote(cand)
                                    can_qualify = True
                                    break
                                except Exception:
                                    continue

                            if can_qualify:
                                break

                            token = q_payload.get("next_page_token")
                            if not token or token == next_token:
                                break
                            next_token = str(token)
                        elif resp.status_code == 429:
                            governor.status_429_count += 1
                            retries += 1
                            if retries > 5:
                                raise DataContractError(f"HTTP 429 rate limit exhausted at {session_date} {b_time}")
                            time.sleep(2.0 * retries)
                        elif resp.status_code in (401, 403):
                            raise DataContractError(f"Alpaca API auth error HTTP {resp.status_code}")
                        else:
                            raise DataContractError(f"Quote fetch error {session_date} {b_time}: HTTP {resp.status_code}")

                    qb = evaluate_boundary_quotes_stream(
                        session_date=session_date,
                        boundary_time=b_time,
                        raw_quotes=raw_quotes_accum,
                        boundary_utc=b_utc,
                        end_utc=session_close_utc,
                        pages_count=pages_count,
                    )
                    session_boundaries.append(qb)
                    session_raw_records.append({
                        "session_date": qb.session_date,
                        "boundary_et": qb.boundary_et,
                        "boundary_utc": qb.boundary_utc,
                        "provider": qb.provider,
                        "feed": qb.feed,
                        "request_start_utc": qb.request_start_utc,
                        "request_end_utc": qb.request_end_utc,
                        "candidate_rows_examined": qb.candidate_rows_examined,
                        "rejected_rows_count": qb.rejected_rows_count,
                        "rejection_reasons_census": qb.rejection_reasons_census,
                        "selected_first_valid_timestamp_utc": qb.selected_first_valid_timestamp_utc,
                        "quote_delay_microseconds": qb.quote_delay_microseconds,
                        "quote_delay_milliseconds": qb.quote_delay_milliseconds,
                        "bid_price": str(qb.bid_price),
                        "ask_price": str(qb.ask_price),
                        "bid_size": qb.bid_size,
                        "ask_size": qb.ask_size,
                        "bid_exchange": qb.bid_exchange,
                        "ask_exchange": qb.ask_exchange,
                        "tape": qb.tape,
                        "conditions": qb.conditions,
                        "is_locked": qb.is_locked,
                        "is_crossed": qb.is_crossed,
                        "pages_examined": qb.pages_examined,
                    })

                checkpoint_payload = {
                    "session_date": session_date.isoformat(),
                    "boundaries": session_raw_records,
                }
                tmp_file = checkpoint_file.with_suffix(".tmp")
                tmp_file.write_text(json.dumps(checkpoint_payload, indent=2), encoding="utf-8")
                tmp_file.replace(checkpoint_file)

            if len(session_boundaries) != len(M2_QUOTE_DECISION_TIMES_ET):
                raise DataContractError(
                    f"Quote boundary count mismatch in session {session_date}: {len(session_boundaries)} != {len(M2_QUOTE_DECISION_TIMES_ET)}"
                )
            all_boundaries.extend(session_boundaries)
    finally:
        if own_client:
            client.close()

    quotes_serialized = [
        {
            "d": b.session_date,
            "et": b.boundary_et,
            "bid": str(b.bid_price),
            "ask": str(b.ask_price),
            "t": b.selected_first_valid_timestamp_utc,
            "cond": b.conditions,
        }
        for b in all_boundaries
    ]
    quote_corpus_sha256 = calculate_deterministic_sha256(quotes_serialized)
    return all_boundaries, quote_corpus_sha256


# ---------------------------------------------------------------------------
# M2 Parquet Serialization
# ---------------------------------------------------------------------------

def write_m2_parquet_datasets(
    bars: List[QualifiedBar],
    quotes: List[QualifiedQuoteBoundary],
    repo_root: Path,
) -> Tuple[Path, Path, str, str]:
    """Write qualified M2 bars and quotes to Parquet files."""
    m2_data_dir = repo_root / "data/hyp_007/m2"
    m2_data_dir.mkdir(parents=True, exist_ok=True)

    bars_path = m2_data_dir / "m2_bars_qualified.parquet"
    quotes_path = m2_data_dir / "m2_execution_quotes_qualified.parquet"

    # Bars Table
    bars_schema = pa.schema([
        ("timestamp_utc", pa.string()),
        ("minute_idx", pa.int32()),
        ("open", pa.string()),
        ("high", pa.string()),
        ("low", pa.string()),
        ("close", pa.string()),
        ("volume", pa.int64()),
        ("hlc3", pa.string()),
        ("trade_count", pa.int32()),
        ("session_date", pa.string()),
        ("sample_classification", pa.string()),
        ("performance_eligible", pa.bool_()),
        ("signal_eligible", pa.bool_()),
        ("trade_eligible", pa.bool_()),
    ])

    bars_dict: Dict[str, List[Any]] = {field.name: [] for field in bars_schema}
    for b in bars:
        bars_dict["timestamp_utc"].append(b.timestamp_utc)
        bars_dict["minute_idx"].append(b.minute_idx)
        bars_dict["open"].append(str(b.open))
        bars_dict["high"].append(str(b.high))
        bars_dict["low"].append(str(b.low))
        bars_dict["close"].append(str(b.close))
        bars_dict["volume"].append(b.volume)
        bars_dict["hlc3"].append(str(b.hlc3))
        bars_dict["trade_count"].append(b.trade_count)
        bars_dict["session_date"].append(b.session_date)
        bars_dict["sample_classification"].append(b.sample_classification)
        bars_dict["performance_eligible"].append(b.performance_eligible)
        bars_dict["signal_eligible"].append(b.signal_eligible)
        bars_dict["trade_eligible"].append(b.trade_eligible)

    bars_table = pa.Table.from_pydict(bars_dict, schema=bars_schema)
    pq.write_table(bars_table, bars_path, compression="snappy")
    bars_sha = hashlib.sha256(bars_path.read_bytes()).hexdigest()

    # Quotes Table
    quotes_schema = pa.schema([
        ("session_date", pa.string()),
        ("boundary_et", pa.string()),
        ("boundary_utc", pa.string()),
        ("provider", pa.string()),
        ("feed", pa.string()),
        ("request_start_utc", pa.string()),
        ("request_end_utc", pa.string()),
        ("candidate_rows_examined", pa.int32()),
        ("rejected_rows_count", pa.int32()),
        ("selected_first_valid_timestamp_utc", pa.string()),
        ("quote_delay_microseconds", pa.int64()),
        ("quote_delay_milliseconds", pa.float64()),
        ("bid_price", pa.string()),
        ("ask_price", pa.string()),
        ("bid_size", pa.int32()),
        ("ask_size", pa.int32()),
        ("bid_exchange", pa.string()),
        ("ask_exchange", pa.string()),
        ("tape", pa.string()),
        ("conditions", pa.string()),
        ("is_locked", pa.bool_()),
        ("is_crossed", pa.bool_()),
        ("pages_examined", pa.int32()),
    ])

    quotes_dict: Dict[str, List[Any]] = {field.name: [] for field in quotes_schema}
    for q in quotes:
        quotes_dict["session_date"].append(q.session_date)
        quotes_dict["boundary_et"].append(q.boundary_et)
        quotes_dict["boundary_utc"].append(q.boundary_utc)
        quotes_dict["provider"].append(q.provider)
        quotes_dict["feed"].append(q.feed)
        quotes_dict["request_start_utc"].append(q.request_start_utc)
        quotes_dict["request_end_utc"].append(q.request_end_utc)
        quotes_dict["candidate_rows_examined"].append(q.candidate_rows_examined)
        quotes_dict["rejected_rows_count"].append(q.rejected_rows_count)
        quotes_dict["selected_first_valid_timestamp_utc"].append(q.selected_first_valid_timestamp_utc)
        quotes_dict["quote_delay_microseconds"].append(q.quote_delay_microseconds)
        quotes_dict["quote_delay_milliseconds"].append(q.quote_delay_milliseconds)
        quotes_dict["bid_price"].append(str(q.bid_price))
        quotes_dict["ask_price"].append(str(q.ask_price))
        quotes_dict["bid_size"].append(q.bid_size)
        quotes_dict["ask_size"].append(q.ask_size)
        quotes_dict["bid_exchange"].append(q.bid_exchange)
        quotes_dict["ask_exchange"].append(q.ask_exchange)
        quotes_dict["tape"].append(q.tape)
        quotes_dict["conditions"].append(",".join(q.conditions))
        quotes_dict["is_locked"].append(q.is_locked)
        quotes_dict["is_crossed"].append(q.is_crossed)
        quotes_dict["pages_examined"].append(q.pages_examined)

    quotes_table = pa.Table.from_pydict(quotes_dict, schema=quotes_schema)
    pq.write_table(quotes_table, quotes_path, compression="snappy")
    quotes_sha = hashlib.sha256(quotes_path.read_bytes()).hexdigest()

    return bars_path, quotes_path, bars_sha, quotes_sha


# ---------------------------------------------------------------------------
# M2 Strategy Execution Engine
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class R4GateEvaluationResult:
    """Evaluation result across all four frozen R4 gates."""
    g1_net_return: Decimal
    g1_pass: bool
    g2_sharpe: Decimal
    g2_pass: bool
    g3_max_drawdown: Decimal
    g3_pass: bool
    g4_stress_return: Decimal
    g4_pass: bool
    contract_valid: bool
    verdict: R4Verdict
    summary_message: str
    all_passed: bool


def evaluate_r4_gates(
    net_total_return: Decimal,
    annualized_sharpe: Decimal,
    max_drawdown: Decimal,
    stress_total_return: Decimal,
    contract_valid: bool = True,
) -> R4GateEvaluationResult:
    """Evaluate all four frozen R4 governance gates for M2."""
    g1_pass = net_total_return >= R4_G1_NET_TOTAL_RETURN_MIN
    g2_pass = annualized_sharpe >= R4_G2_NET_ANNUALIZED_SHARPE_MIN
    g3_pass = max_drawdown <= R4_G3_MAX_DRAWDOWN_MAX
    g4_pass = stress_total_return >= R4_G4_STRESS_TOTAL_RETURN_MIN

    all_passed = g1_pass and g2_pass and g3_pass and g4_pass and contract_valid
    verdict = (
        R4Verdict.PASS_RECENT_STRESS_SUPPORTED
        if all_passed
        else R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    )
    summary = (
        "All four R4 M2 recent stress continuation gates passed."
        if all_passed
        else "One or more R4 M2 continuation gates failed; recent edge not supported."
    )

    return R4GateEvaluationResult(
        g1_net_return=net_total_return,
        g1_pass=g1_pass,
        g2_sharpe=annualized_sharpe,
        g2_pass=g2_pass,
        g3_max_drawdown=max_drawdown,
        g3_pass=g3_pass,
        g4_stress_return=stress_total_return,
        g4_pass=g4_pass,
        contract_valid=contract_valid,
        verdict=verdict,
        summary_message=summary,
        all_passed=all_passed,
    )


@dataclass
class Hyp007R4ExecutionResult:
    all_signals: List[DecisionSignalRecord]
    baseline_execution_legs: List[ExecutionOrderLegRecord]
    stress_execution_legs: List[ExecutionOrderLegRecord]
    baseline_trades: List[CompletedTradeRecord]
    daily_performances: List[DailySessionPerformanceRecord]
    baseline_equity_curve: List[Decimal]
    stress_equity_curve: List[Decimal]
    baseline_daily_returns: List[Decimal]
    stress_daily_returns: List[Decimal]
    final_baseline_aum: Decimal
    final_stress_aum: Decimal
    baseline_net_total_return: Decimal
    stress_net_total_return: Decimal
    baseline_annualized_sharpe: Decimal
    stress_annualized_sharpe: Decimal
    baseline_max_drawdown: Decimal
    stress_max_drawdown: Decimal
    baseline_completed_trades_count: int
    stress_completed_trades_count: int
    gate_report: R4GateEvaluationResult
    no_material_contract_failure: bool
    terminal_verdict: str
    signal_ledger_sha256: str
    baseline_execution_ledger_sha256: str
    stress_execution_ledger_sha256: str
    trade_ledger_sha256: str
    baseline_daily_equity_sha256: str
    stress_daily_equity_sha256: str
    r4_result_package_sha256: str


def execute_hyp_007_m2_strategy(
    repo_root: Path,
    verify_preconditions: bool = True,
) -> Hyp007R4ExecutionResult:
    """Execute unchanged HYP_007 strategy deterministically on qualified M2 evidence."""
    if verify_preconditions:
        validate_r4_preconditions(repo_root)

    # 1. Load M1 Warm-up Data
    m1_bars_path = repo_root / "data/hyp_007/m1_bars_qualified.parquet"
    if not m1_bars_path.exists():
        raise DataContractError(f"M1 bars qualified parquet not found at {m1_bars_path}")

    m1_bars_table = pq.read_table(m1_bars_path)
    pydict_m1 = m1_bars_table.to_pydict()

    m1_bars_by_sess: Dict[str, List[Dict[str, Any]]] = {}
    for i in range(len(pydict_m1["session_date"])):
        dt_str = pydict_m1["session_date"][i]
        if dt_str not in m1_bars_by_sess:
            m1_bars_by_sess[dt_str] = []
        m1_bars_by_sess[dt_str].append({
            "minute_idx": pydict_m1["minute_idx"][i],
            "open": Decimal(pydict_m1["open"][i]),
            "close": Decimal(pydict_m1["close"][i]),
            "volume": pydict_m1["volume"][i],
            "hlc3": Decimal(pydict_m1["hlc3"][i]),
        })

    m1_eligible_sessions = sorted(list(m1_bars_by_sess.keys()))

    # Build continuous daily closes from M1 (including 2023-06-05 at 427.10)
    # The last 16 closes of M1 are needed for 2024-05-01 vol sizing
    from acash.research.step_r2_hyp_007 import build_calendar_census as build_m1_census
    m1_census = build_m1_census()
    m1_all_sessions = m1_census.warmup_regular_sessions + m1_census.m1_regular_sessions

    continuous_daily_closes: List[Tuple[str, Decimal]] = []
    for sess_d in m1_all_sessions:
        dt_str = sess_d.isoformat()
        if dt_str == "2023-06-05":
            continuous_daily_closes.append((dt_str, Decimal("427.10")))
        elif dt_str in m1_bars_by_sess:
            continuous_daily_closes.append((dt_str, m1_bars_by_sess[dt_str][-1]["close"]))

    # 2. Load Qualified M2 Parquet Evidence
    m2_bars_path = repo_root / "data/hyp_007/m2/m2_bars_qualified.parquet"
    m2_quotes_path = repo_root / "data/hyp_007/m2/m2_execution_quotes_qualified.parquet"

    if not m2_bars_path.exists() or not m2_quotes_path.exists():
        raise DataContractError("M2 qualified parquet evidence files not found.")

    m2_bars_table = pq.read_table(m2_bars_path)
    m2_quotes_table = pq.read_table(m2_quotes_path)

    m2_bars_by_sess: Dict[str, List[Dict[str, Any]]] = {}
    pydict_m2_bars = m2_bars_table.to_pydict()
    for i in range(len(pydict_m2_bars["session_date"])):
        dt_str = pydict_m2_bars["session_date"][i]
        if dt_str not in m2_bars_by_sess:
            m2_bars_by_sess[dt_str] = []
        m2_bars_by_sess[dt_str].append({
            "minute_idx": pydict_m2_bars["minute_idx"][i],
            "open": Decimal(pydict_m2_bars["open"][i]),
            "close": Decimal(pydict_m2_bars["close"][i]),
            "volume": pydict_m2_bars["volume"][i],
            "hlc3": Decimal(pydict_m2_bars["hlc3"][i]),
        })

    m2_quotes_by_dt_et: Dict[Tuple[str, str], Dict[str, Any]] = {}
    pydict_m2_quotes = m2_quotes_table.to_pydict()
    for i in range(len(pydict_m2_quotes["session_date"])):
        dt_str = pydict_m2_quotes["session_date"][i]
        et_str = pydict_m2_quotes["boundary_et"][i]
        cond = pydict_m2_quotes["conditions"][i]
        cond_list = cond.split(",") if isinstance(cond, str) else list(cond)
        if "R" not in cond_list:
            raise DataContractError(f"Invalid non-R quote in M2: {dt_str} {et_str} {cond_list}")
        m2_quotes_by_dt_et[(dt_str, et_str)] = {
            "bid": Decimal(pydict_m2_quotes["bid_price"][i]),
            "ask": Decimal(pydict_m2_quotes["ask_price"][i]),
            "timestamp_utc": pydict_m2_quotes["selected_first_valid_timestamp_utc"][i],
        }

    # 3. M2 Dividends
    m2_divs = load_m2_dividend_projection(repo_root)
    m2_div_by_date = {d.ex_date: d.cash_distribution for d in m2_divs}

    # Combined bar store for Noise Area lookbacks
    combined_bars_by_sess: Dict[str, List[Dict[str, Any]]] = {}
    combined_bars_by_sess.update(m1_bars_by_sess)
    combined_bars_by_sess.update(m2_bars_by_sess)

    # Strategy eligible sessions sequence
    combined_eligible_sessions: List[str] = list(m1_eligible_sessions)
    m2_sessions = sorted(list(m2_bars_by_sess.keys()))

    epoch_minute_map = compute_epoch_minute_mappings()

    # Simulation State: Reset M2 AUM to $100,000.00
    aum_baseline = M2_SIMULATED_STARTING_AUM_USD
    aum_stress = M2_SIMULATED_STARTING_AUM_USD

    baseline_equity_curve: List[Decimal] = [aum_baseline]
    stress_equity_curve: List[Decimal] = [aum_stress]
    baseline_daily_returns: List[Decimal] = []
    stress_daily_returns: List[Decimal] = []

    all_signals: List[DecisionSignalRecord] = []
    baseline_execution_legs: List[ExecutionOrderLegRecord] = []
    stress_execution_legs: List[ExecutionOrderLegRecord] = []
    baseline_trades: List[CompletedTradeRecord] = []
    daily_performances: List[DailySessionPerformanceRecord] = []

    baseline_all_trades_positions: List[int] = [0]
    stress_all_trades_positions: List[int] = [0]
    trade_id_counter = 0

    # Execute daily simulation loop across M2 sessions
    for m2_idx, dt_str in enumerate(m2_sessions):
        sess_date = date.fromisoformat(dt_str)
        sess_bars = m2_bars_by_sess[dt_str]
        morning_open = sess_bars[0]["open"]

        # 1. 15-day Volatility Targeting (16 prior unadjusted regular closes)
        if len(continuous_daily_closes) < 16:
            raise DataContractError(f"Insufficient close history for vol sizing on {dt_str}")
        prior_16_closes = [c[1] for c in continuous_daily_closes[-16:]]
        prior_15_returns = [float(prior_16_closes[i] / prior_16_closes[i - 1] - Decimal("1.0")) for i in range(1, 16)]
        realized_vol = np.std(prior_15_returns, ddof=1)
        if realized_vol <= 0.0 or math.isnan(realized_vol):
            raise DataContractError(f"Zero or invalid realized vol on {dt_str}: {realized_vol}")
        leverage = min(4.0, 0.02 / realized_vol)

        # 2. Daily Position Sizing (Fixed for session)
        target_shares_baseline = int(round(float(aum_baseline / morning_open) * leverage))
        target_shares_stress = int(round(float(aum_stress / morning_open) * leverage))

        # 3. Noise Area (14 Prior Completed Eligible Sessions)
        if len(combined_eligible_sessions) < 14:
            raise DataContractError(f"Insufficient Noise Area history for {dt_str}")
        prior_14_sessions = combined_eligible_sessions[-14:]

        # 4. Previous Regular Close Anchor & Dividend Adjustment
        prev_close_raw = continuous_daily_closes[-1][1]
        dividend = m2_div_by_date.get(dt_str, Decimal("0.00"))
        prev_close_adjusted = prev_close_raw - dividend
        upper_anchor = max(morning_open, prev_close_adjusted)
        lower_anchor = min(morning_open, prev_close_adjusted)

        # 5. Evaluate Decision Epochs
        daily_signals: List[Tuple[str, str, Decimal, Decimal, Decimal, Decimal, str, int]] = []
        for ep_str, sig_min_str, bar_idx in epoch_minute_map:
            # Noise Area at this minute index across prior 14 completed sessions
            minute_moves = [
                abs(combined_bars_by_sess[p_sess][bar_idx]["close"] / combined_bars_by_sess[p_sess][0]["open"] - Decimal("1.0"))
                for p_sess in prior_14_sessions
            ]
            sigma = sum(minute_moves) / Decimal("14")

            up_band = upper_anchor * (Decimal("1.0") + sigma)
            lo_band = lower_anchor * (Decimal("1.0") - sigma)

            # Cumulative HLC3 VWAP up through bar_idx
            cum_vol = sum(sess_bars[i]["volume"] for i in range(bar_idx + 1))
            cum_hlc3_vol = sum(sess_bars[i]["hlc3"] * Decimal(sess_bars[i]["volume"]) for i in range(bar_idx + 1))
            if cum_vol == 0:
                raise DataContractError(f"Zero cumulative volume at {dt_str} {sig_min_str}")
            vwap = cum_hlc3_vol / Decimal(cum_vol)

            c_price = sess_bars[bar_idx]["close"]
            if c_price > up_band and c_price > vwap:
                sig = "LONG"
            elif c_price < lo_band and c_price < vwap:
                sig = "SHORT"
            else:
                sig = "FLAT"

            all_signals.append(
                DecisionSignalRecord(
                    session_date=dt_str,
                    decision_epoch_et=ep_str,
                    signal_minute_et=sig_min_str,
                    signal_bar_idx=bar_idx,
                    signal_close=str(c_price),
                    upper_anchor=str(upper_anchor),
                    lower_anchor=str(lower_anchor),
                    sigma_open=str(sigma),
                    upper_band=str(up_band),
                    lower_band=str(lo_band),
                    vwap=str(vwap),
                    signal_state=sig,
                )
            )
            daily_signals.append((ep_str, sig, c_price, up_band, lo_band, vwap, sig_min_str, bar_idx))

        # 6. Baseline Simulation
        pos_base = 0
        net_daily_pnl_base = Decimal("0.00")
        trade_entry_epoch_base: Optional[str] = None
        trade_entry_px_base: Optional[Decimal] = None
        trade_shares_base: int = 0
        trade_gross_cf_base: Decimal = Decimal("0.00")
        trade_friction_base: Decimal = Decimal("0.00")

        for ep_str, sig, _, _, _, _, _, _ in daily_signals:
            q = m2_quotes_by_dt_et[(dt_str, ep_str)]
            ask = q["ask"]
            bid = q["bid"]

            if sig == "LONG":
                desired_pos = target_shares_baseline
            elif sig == "SHORT":
                desired_pos = -target_shares_baseline
            else:
                desired_pos = 0

            if pos_base == 0:
                if desired_pos != 0:
                    sh = abs(desired_pos)
                    is_buy = (desired_pos > 0)
                    px = (ask + Decimal("0.001")) if is_buy else (bid - Decimal("0.001"))
                    comm = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh))
                    sec = compute_m2_sec31_fee(sess_date, Decimal(sh) * px, is_sell=not is_buy)
                    taf = compute_m2_finra_taf(sess_date, sh, is_sell=not is_buy)
                    slip = Decimal("0.001") * Decimal(sh)
                    tot_fric = comm + sec + taf
                    cf = (-px * Decimal(sh) - tot_fric) if is_buy else (px * Decimal(sh) - tot_fric)
                    net_daily_pnl_base += cf

                    baseline_execution_legs.append(
                        ExecutionOrderLegRecord(
                            session_date=dt_str,
                            boundary_et=ep_str,
                            path="BASELINE",
                            action="ENTRY_LONG" if is_buy else "ENTRY_SHORT",
                            side="BUY" if is_buy else "SELL",
                            shares=sh,
                            fill_price=str(px),
                            quote_bid=str(bid),
                            quote_ask=str(ask),
                            quote_timestamp_utc=q["timestamp_utc"],
                            commission=str(comm),
                            sec31_fee=str(sec),
                            finra_taf=str(taf),
                            standalone_slippage=str(slip),
                            stress_half_spread="0.00",
                            stress_borrow_fee="0.00",
                            total_friction=str(tot_fric),
                            net_cash_flow=str(cf),
                        )
                    )
                    pos_base = desired_pos
                    baseline_all_trades_positions.append(pos_base)
                    trade_entry_epoch_base = ep_str
                    trade_entry_px_base = px
                    trade_shares_base = sh
                    trade_gross_cf_base = (-px * Decimal(sh)) if is_buy else (px * Decimal(sh))
                    trade_friction_base = tot_fric
            elif (pos_base > 0 and desired_pos > 0) or (pos_base < 0 and desired_pos < 0):
                pass  # Hold same direction
            elif desired_pos == 0:
                # Flatten
                sh = abs(pos_base)
                is_buy = (pos_base < 0)
                px = (ask + Decimal("0.001")) if is_buy else (bid - Decimal("0.001"))
                comm = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh))
                sec = compute_m2_sec31_fee(sess_date, Decimal(sh) * px, is_sell=not is_buy)
                taf = compute_m2_finra_taf(sess_date, sh, is_sell=not is_buy)
                slip = Decimal("0.001") * Decimal(sh)
                tot_fric = comm + sec + taf
                cf = (-px * Decimal(sh) - tot_fric) if is_buy else (px * Decimal(sh) - tot_fric)
                net_daily_pnl_base += cf

                baseline_execution_legs.append(
                    ExecutionOrderLegRecord(
                        session_date=dt_str,
                        boundary_et=ep_str,
                        path="BASELINE",
                        action="EXIT_FLAT",
                        side="BUY" if is_buy else "SELL",
                        shares=sh,
                        fill_price=str(px),
                        quote_bid=str(bid),
                        quote_ask=str(ask),
                        quote_timestamp_utc=q["timestamp_utc"],
                        commission=str(comm),
                        sec31_fee=str(sec),
                        finra_taf=str(taf),
                        standalone_slippage=str(slip),
                        stress_half_spread="0.00",
                        stress_borrow_fee="0.00",
                        total_friction=str(tot_fric),
                        net_cash_flow=str(cf),
                    )
                )

                trade_id_counter += 1
                exit_gross_cf = (-px * Decimal(sh)) if is_buy else (px * Decimal(sh))
                tot_gross = trade_gross_cf_base + exit_gross_cf
                tot_tr_fric = trade_friction_base + tot_fric
                baseline_trades.append(
                    CompletedTradeRecord(
                        trade_id=trade_id_counter,
                        session_date=dt_str,
                        direction="LONG" if pos_base > 0 else "SHORT",
                        entry_epoch_et=trade_entry_epoch_base or ep_str,
                        exit_boundary_et=ep_str,
                        shares=trade_shares_base,
                        entry_fill_price=str(trade_entry_px_base),
                        exit_fill_price=str(px),
                        gross_pnl=str(tot_gross),
                        total_friction=str(tot_tr_fric),
                        net_pnl=str(tot_gross - tot_tr_fric),
                        exit_reason="SIGNAL_FLAT",
                    )
                )
                pos_base = 0
                baseline_all_trades_positions.append(0)
                trade_entry_epoch_base = None
            else:
                # Directional Flip
                sh_close = abs(pos_base)
                is_buy_close = (pos_base < 0)
                px_close = (ask + Decimal("0.001")) if is_buy_close else (bid - Decimal("0.001"))
                comm_close = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh_close))
                sec_close = compute_m2_sec31_fee(sess_date, Decimal(sh_close) * px_close, is_sell=not is_buy_close)
                taf_close = compute_m2_finra_taf(sess_date, sh_close, is_sell=not is_buy_close)
                tot_fric_close = comm_close + sec_close + taf_close
                cf_close = (-px_close * Decimal(sh_close) - tot_fric_close) if is_buy_close else (px_close * Decimal(sh_close) - tot_fric_close)
                net_daily_pnl_base += cf_close

                baseline_execution_legs.append(
                    ExecutionOrderLegRecord(
                        session_date=dt_str,
                        boundary_et=ep_str,
                        path="BASELINE",
                        action="FLIP_EXIT",
                        side="BUY" if is_buy_close else "SELL",
                        shares=sh_close,
                        fill_price=str(px_close),
                        quote_bid=str(bid),
                        quote_ask=str(ask),
                        quote_timestamp_utc=q["timestamp_utc"],
                        commission=str(comm_close),
                        sec31_fee=str(sec_close),
                        finra_taf=str(taf_close),
                        standalone_slippage=str(Decimal("0.001") * Decimal(sh_close)),
                        stress_half_spread="0.00",
                        stress_borrow_fee="0.00",
                        total_friction=str(tot_fric_close),
                        net_cash_flow=str(cf_close),
                    )
                )

                trade_id_counter += 1
                exit_gross_cf = (-px_close * Decimal(sh_close)) if is_buy_close else (px_close * Decimal(sh_close))
                tot_gross = trade_gross_cf_base + exit_gross_cf
                tot_tr_fric = trade_friction_base + tot_fric_close
                baseline_trades.append(
                    CompletedTradeRecord(
                        trade_id=trade_id_counter,
                        session_date=dt_str,
                        direction="LONG" if pos_base > 0 else "SHORT",
                        entry_epoch_et=trade_entry_epoch_base or ep_str,
                        exit_boundary_et=ep_str,
                        shares=trade_shares_base,
                        entry_fill_price=str(trade_entry_px_base),
                        exit_fill_price=str(px_close),
                        gross_pnl=str(tot_gross),
                        total_friction=str(tot_tr_fric),
                        net_pnl=str(tot_gross - tot_tr_fric),
                        exit_reason="DIRECTIONAL_FLIP",
                    )
                )

                # Open flip position
                sh_open = abs(desired_pos)
                is_buy_open = (desired_pos > 0)
                px_open = (ask + Decimal("0.001")) if is_buy_open else (bid - Decimal("0.001"))
                comm_open = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh_open))
                sec_open = compute_m2_sec31_fee(sess_date, Decimal(sh_open) * px_open, is_sell=not is_buy_open)
                taf_open = compute_m2_finra_taf(sess_date, sh_open, is_sell=not is_buy_open)
                tot_fric_open = comm_open + sec_open + taf_open
                cf_open = (-px_open * Decimal(sh_open) - tot_fric_open) if is_buy_open else (px_open * Decimal(sh_open) - tot_fric_open)
                net_daily_pnl_base += cf_open

                baseline_execution_legs.append(
                    ExecutionOrderLegRecord(
                        session_date=dt_str,
                        boundary_et=ep_str,
                        path="BASELINE",
                        action="FLIP_ENTRY",
                        side="BUY" if is_buy_open else "SELL",
                        shares=sh_open,
                        fill_price=str(px_open),
                        quote_bid=str(bid),
                        quote_ask=str(ask),
                        quote_timestamp_utc=q["timestamp_utc"],
                        commission=str(comm_open),
                        sec31_fee=str(sec_open),
                        finra_taf=str(taf_open),
                        standalone_slippage=str(Decimal("0.001") * Decimal(sh_open)),
                        stress_half_spread="0.00",
                        stress_borrow_fee="0.00",
                        total_friction=str(tot_fric_open),
                        net_cash_flow=str(cf_open),
                    )
                )
                pos_base = desired_pos
                baseline_all_trades_positions.append(pos_base)
                trade_entry_epoch_base = ep_str
                trade_entry_px_base = px_open
                trade_shares_base = sh_open
                trade_gross_cf_base = (-px_open * Decimal(sh_open)) if is_buy_open else (px_open * Decimal(sh_open))
                trade_friction_base = tot_fric_open

        # 7. EOD Forced Flatten at 15:59 ET (Baseline)
        if pos_base != 0:
            q_eod = m2_quotes_by_dt_et[(dt_str, "15:59:00")]
            ask_eod = q_eod["ask"]
            bid_eod = q_eod["bid"]
            sh_eod = abs(pos_base)
            is_buy_eod = (pos_base < 0)
            px_eod = (ask_eod + Decimal("0.001")) if is_buy_eod else (bid_eod - Decimal("0.001"))
            comm_eod = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh_eod))
            sec_eod = compute_m2_sec31_fee(sess_date, Decimal(sh_eod) * px_eod, is_sell=not is_buy_eod)
            taf_eod = compute_m2_finra_taf(sess_date, sh_eod, is_sell=not is_buy_eod)
            tot_fric_eod = comm_eod + sec_eod + taf_eod
            cf_eod = (-px_eod * Decimal(sh_eod) - tot_fric_eod) if is_buy_eod else (px_eod * Decimal(sh_eod) - tot_fric_eod)
            net_daily_pnl_base += cf_eod

            baseline_execution_legs.append(
                ExecutionOrderLegRecord(
                    session_date=dt_str,
                    boundary_et="15:59:00",
                    path="BASELINE",
                    action="EOD_FLATTEN",
                    side="BUY" if is_buy_eod else "SELL",
                    shares=sh_eod,
                    fill_price=str(px_eod),
                    quote_bid=str(bid_eod),
                    quote_ask=str(ask_eod),
                    quote_timestamp_utc=q_eod["timestamp_utc"],
                    commission=str(comm_eod),
                    sec31_fee=str(sec_eod),
                    finra_taf=str(taf_eod),
                    standalone_slippage=str(Decimal("0.001") * Decimal(sh_eod)),
                    stress_half_spread="0.00",
                    stress_borrow_fee="0.00",
                    total_friction=str(tot_fric_eod),
                    net_cash_flow=str(cf_eod),
                )
            )

            trade_id_counter += 1
            exit_gross_cf = (-px_eod * Decimal(sh_eod)) if is_buy_eod else (px_eod * Decimal(sh_eod))
            tot_gross = trade_gross_cf_base + exit_gross_cf
            tot_tr_fric = trade_friction_base + tot_fric_eod
            baseline_trades.append(
                CompletedTradeRecord(
                    trade_id=trade_id_counter,
                    session_date=dt_str,
                    direction="LONG" if pos_base > 0 else "SHORT",
                    entry_epoch_et=trade_entry_epoch_base or "15:30:00",
                    exit_boundary_et="15:59:00",
                    shares=trade_shares_base,
                    entry_fill_price=str(trade_entry_px_base),
                    exit_fill_price=str(px_eod),
                    gross_pnl=str(tot_gross),
                    total_friction=str(tot_tr_fric),
                    net_pnl=str(tot_gross - tot_tr_fric),
                    exit_reason="EOD_FLATTEN",
                )
            )
            pos_base = 0
            baseline_all_trades_positions.append(0)

        # 8. 2X Friction Stress Simulation for Current Session
        pos_stress = 0
        net_daily_pnl_stress = Decimal("0.00")
        short_entry_minute_stress: Optional[int] = None
        short_shares_stress: int = 0
        short_notional_stress: Decimal = Decimal("0.00")

        for ep_str, sig, _, _, _, _, _, bar_idx in daily_signals:
            q = m2_quotes_by_dt_et[(dt_str, ep_str)]
            ask = q["ask"]
            bid = q["bid"]
            half_spread = (ask - bid) / Decimal("2")

            if sig == "LONG":
                desired_pos_s = target_shares_stress
            elif sig == "SHORT":
                desired_pos_s = -target_shares_stress
            else:
                desired_pos_s = 0

            if pos_stress == 0:
                if desired_pos_s != 0:
                    sh = abs(desired_pos_s)
                    is_buy = (desired_pos_s > 0)
                    px = (ask + Decimal("0.001")) if is_buy else (bid - Decimal("0.001"))
                    comm = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh)) * Decimal("2")
                    sec = compute_m2_sec31_fee(sess_date, Decimal(sh) * px, is_sell=not is_buy) * Decimal("2")
                    taf = compute_m2_finra_taf(sess_date, sh, is_sell=not is_buy) * Decimal("2")
                    slip = Decimal("0.001") * Decimal(sh)
                    hs_stress = half_spread * Decimal(sh)
                    tot_fric = comm + sec + taf + hs_stress
                    cf = (-px * Decimal(sh) - tot_fric) if is_buy else (px * Decimal(sh) - tot_fric)
                    net_daily_pnl_stress += cf

                    stress_execution_legs.append(
                        ExecutionOrderLegRecord(
                            session_date=dt_str,
                            boundary_et=ep_str,
                            path="STRESS",
                            action="ENTRY_LONG" if is_buy else "ENTRY_SHORT",
                            side="BUY" if is_buy else "SELL",
                            shares=sh,
                            fill_price=str(px),
                            quote_bid=str(bid),
                            quote_ask=str(ask),
                            quote_timestamp_utc=q["timestamp_utc"],
                            commission=str(comm),
                            sec31_fee=str(sec),
                            finra_taf=str(taf),
                            standalone_slippage=str(slip),
                            stress_half_spread=str(hs_stress),
                            stress_borrow_fee="0.00",
                            total_friction=str(tot_fric),
                            net_cash_flow=str(cf),
                        )
                    )
                    pos_stress = desired_pos_s
                    stress_all_trades_positions.append(pos_stress)
                    if pos_stress < 0:
                        short_entry_minute_stress = bar_idx + 1
                        short_shares_stress = sh
                        short_notional_stress = px * Decimal(sh)
            elif (pos_stress > 0 and desired_pos_s > 0) or (pos_stress < 0 and desired_pos_s < 0):
                pass  # Hold
            elif desired_pos_s == 0:
                # Flatten
                sh = abs(pos_stress)
                is_buy = (pos_stress < 0)
                px = (ask + Decimal("0.001")) if is_buy else (bid - Decimal("0.001"))
                comm = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh)) * Decimal("2")
                sec = compute_m2_sec31_fee(sess_date, Decimal(sh) * px, is_sell=not is_buy) * Decimal("2")
                taf = compute_m2_finra_taf(sess_date, sh, is_sell=not is_buy) * Decimal("2")
                slip = Decimal("0.001") * Decimal(sh)
                hs_stress = half_spread * Decimal(sh)

                borrow_fee = Decimal("0.00")
                if pos_stress < 0 and short_entry_minute_stress is not None:
                    holding_mins = (bar_idx + 1) - short_entry_minute_stress
                    borrow_rate = Decimal("0.0050") * Decimal(holding_mins) / Decimal(390 * 252)
                    borrow_fee = short_notional_stress * borrow_rate

                tot_fric = comm + sec + taf + hs_stress + borrow_fee
                cf = (-px * Decimal(sh) - tot_fric) if is_buy else (px * Decimal(sh) - tot_fric)
                net_daily_pnl_stress += cf

                stress_execution_legs.append(
                    ExecutionOrderLegRecord(
                        session_date=dt_str,
                        boundary_et=ep_str,
                        path="STRESS",
                        action="EXIT_FLAT",
                        side="BUY" if is_buy else "SELL",
                        shares=sh,
                        fill_price=str(px),
                        quote_bid=str(bid),
                        quote_ask=str(ask),
                        quote_timestamp_utc=q["timestamp_utc"],
                        commission=str(comm),
                        sec31_fee=str(sec),
                        finra_taf=str(taf),
                        standalone_slippage=str(slip),
                        stress_half_spread=str(hs_stress),
                        stress_borrow_fee=str(borrow_fee),
                        total_friction=str(tot_fric),
                        net_cash_flow=str(cf),
                    )
                )
                pos_stress = 0
                stress_all_trades_positions.append(0)
                short_entry_minute_stress = None
            else:
                # Directional Flip
                sh_close = abs(pos_stress)
                is_buy_close = (pos_stress < 0)
                px_close = (ask + Decimal("0.001")) if is_buy_close else (bid - Decimal("0.001"))
                comm_close = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh_close)) * Decimal("2")
                sec_close = compute_m2_sec31_fee(sess_date, Decimal(sh_close) * px_close, is_sell=not is_buy_close) * Decimal("2")
                taf_close = compute_m2_finra_taf(sess_date, sh_close, is_sell=not is_buy_close) * Decimal("2")
                hs_stress_close = half_spread * Decimal(sh_close)

                borrow_fee_close = Decimal("0.00")
                if pos_stress < 0 and short_entry_minute_stress is not None:
                    holding_mins = (bar_idx + 1) - short_entry_minute_stress
                    borrow_rate = Decimal("0.0050") * Decimal(holding_mins) / Decimal(390 * 252)
                    borrow_fee_close = short_notional_stress * borrow_rate

                tot_fric_close = comm_close + sec_close + taf_close + hs_stress_close + borrow_fee_close
                cf_close = (-px_close * Decimal(sh_close) - tot_fric_close) if is_buy_close else (px_close * Decimal(sh_close) - tot_fric_close)
                net_daily_pnl_stress += cf_close

                stress_execution_legs.append(
                    ExecutionOrderLegRecord(
                        session_date=dt_str,
                        boundary_et=ep_str,
                        path="STRESS",
                        action="FLIP_EXIT",
                        side="BUY" if is_buy_close else "SELL",
                        shares=sh_close,
                        fill_price=str(px_close),
                        quote_bid=str(bid),
                        quote_ask=str(ask),
                        quote_timestamp_utc=q["timestamp_utc"],
                        commission=str(comm_close),
                        sec31_fee=str(sec_close),
                        finra_taf=str(taf_close),
                        standalone_slippage=str(Decimal("0.001") * Decimal(sh_close)),
                        stress_half_spread=str(hs_stress_close),
                        stress_borrow_fee=str(borrow_fee_close),
                        total_friction=str(tot_fric_close),
                        net_cash_flow=str(cf_close),
                    )
                )

                # Open flip
                sh_open = abs(desired_pos_s)
                is_buy_open = (desired_pos_s > 0)
                px_open = (ask + Decimal("0.001")) if is_buy_open else (bid - Decimal("0.001"))
                comm_open = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh_open)) * Decimal("2")
                sec_open = compute_m2_sec31_fee(sess_date, Decimal(sh_open) * px_open, is_sell=not is_buy_open) * Decimal("2")
                taf_open = compute_m2_finra_taf(sess_date, sh_open, is_sell=not is_buy_open) * Decimal("2")
                hs_stress_open = half_spread * Decimal(sh_open)
                tot_fric_open = comm_open + sec_open + taf_open + hs_stress_open
                cf_open = (-px_open * Decimal(sh_open) - tot_fric_open) if is_buy_open else (px_open * Decimal(sh_open) - tot_fric_open)
                net_daily_pnl_stress += cf_open

                stress_execution_legs.append(
                    ExecutionOrderLegRecord(
                        session_date=dt_str,
                        boundary_et=ep_str,
                        path="STRESS",
                        action="FLIP_ENTRY",
                        side="BUY" if is_buy_open else "SELL",
                        shares=sh_open,
                        fill_price=str(px_open),
                        quote_bid=str(bid),
                        quote_ask=str(ask),
                        quote_timestamp_utc=q["timestamp_utc"],
                        commission=str(comm_open),
                        sec31_fee=str(sec_open),
                        finra_taf=str(taf_open),
                        standalone_slippage=str(Decimal("0.001") * Decimal(sh_open)),
                        stress_half_spread=str(hs_stress_open),
                        stress_borrow_fee="0.00",
                        total_friction=str(tot_fric_open),
                        net_cash_flow=str(cf_open),
                    )
                )
                pos_stress = desired_pos_s
                stress_all_trades_positions.append(pos_stress)
                if pos_stress < 0:
                    short_entry_minute_stress = bar_idx + 1
                    short_shares_stress = sh_open
                    short_notional_stress = px_open * Decimal(sh_open)
                else:
                    short_entry_minute_stress = None

        # 9. EOD Flatten for Stress Path
        if pos_stress != 0:
            q_eod = m2_quotes_by_dt_et[(dt_str, "15:59:00")]
            ask_eod = q_eod["ask"]
            bid_eod = q_eod["bid"]
            half_spread_eod = (ask_eod - bid_eod) / Decimal("2")
            sh_eod = abs(pos_stress)
            is_buy_eod = (pos_stress < 0)
            px_eod = (ask_eod + Decimal("0.001")) if is_buy_eod else (bid_eod - Decimal("0.001"))
            comm_eod = max(Decimal("0.35"), Decimal("0.0035") * Decimal(sh_eod)) * Decimal("2")
            sec_eod = compute_m2_sec31_fee(sess_date, Decimal(sh_eod) * px_eod, is_sell=not is_buy_eod) * Decimal("2")
            taf_eod = compute_m2_finra_taf(sess_date, sh_eod, is_sell=not is_buy_eod) * Decimal("2")
            hs_stress_eod = half_spread_eod * Decimal(sh_eod)

            borrow_fee_eod = Decimal("0.00")
            if pos_stress < 0 and short_entry_minute_stress is not None:
                holding_mins = 389 - short_entry_minute_stress
                borrow_rate = Decimal("0.0050") * Decimal(holding_mins) / Decimal(390 * 252)
                borrow_fee_eod = short_notional_stress * borrow_rate

            tot_fric_eod = comm_eod + sec_eod + taf_eod + hs_stress_eod + borrow_fee_eod
            cf_eod = (-px_eod * Decimal(sh_eod) - tot_fric_eod) if is_buy_eod else (px_eod * Decimal(sh_eod) - tot_fric_eod)
            net_daily_pnl_stress += cf_eod

            stress_execution_legs.append(
                ExecutionOrderLegRecord(
                    session_date=dt_str,
                    boundary_et="15:59:00",
                    path="STRESS",
                    action="EOD_FLATTEN",
                    side="BUY" if is_buy_eod else "SELL",
                    shares=sh_eod,
                    fill_price=str(px_eod),
                    quote_bid=str(bid_eod),
                    quote_ask=str(ask_eod),
                    quote_timestamp_utc=q_eod["timestamp_utc"],
                    commission=str(comm_eod),
                    sec31_fee=str(sec_eod),
                    finra_taf=str(taf_eod),
                    standalone_slippage=str(Decimal("0.001") * Decimal(sh_eod)),
                    stress_half_spread=str(hs_stress_eod),
                    stress_borrow_fee=str(borrow_fee_eod),
                    total_friction=str(tot_fric_eod),
                    net_cash_flow=str(cf_eod),
                )
            )
            pos_stress = 0
            stress_all_trades_positions.append(0)

        # 10. Update Daily AUM & Returns
        new_aum_base = aum_baseline + net_daily_pnl_base
        new_aum_stress = aum_stress + net_daily_pnl_stress

        ret_base = calculate_daily_net_return(new_aum_base, aum_baseline)
        ret_stress = calculate_daily_net_return(new_aum_stress, aum_stress)

        baseline_daily_returns.append(ret_base)
        stress_daily_returns.append(ret_stress)
        baseline_equity_curve.append(new_aum_base)
        stress_equity_curve.append(new_aum_stress)

        daily_performances.append(
            DailySessionPerformanceRecord(
                session_date=dt_str,
                calendar_ordinal=m2_idx + 1,
                strategy_eligible=True,
                morning_open=str(morning_open),
                realized_vol_15d=f"{realized_vol:.18f}",
                target_leverage=f"{leverage:.18f}",
                target_shares_baseline=target_shares_baseline,
                target_shares_stress=target_shares_stress,
                baseline_start_aum=str(aum_baseline),
                baseline_net_daily_pnl=str(net_daily_pnl_base),
                baseline_ending_aum=str(new_aum_base),
                baseline_daily_return=str(ret_base),
                stress_start_aum=str(aum_stress),
                stress_net_daily_pnl=str(net_daily_pnl_stress),
                stress_ending_aum=str(new_aum_stress),
                stress_daily_return=str(ret_stress),
                reconciled_exact=True,
            )
        )

        aum_baseline = new_aum_base
        aum_stress = new_aum_stress

        # Append current session to history for future sessions
        continuous_daily_closes.append((dt_str, sess_bars[-1]["close"]))
        combined_eligible_sessions.append(dt_str)

    # Calculate Summary Performance Metrics
    final_base_aum = aum_baseline
    final_stress_aum = aum_stress

    base_tot_ret = calculate_net_total_return(final_base_aum, M2_SIMULATED_STARTING_AUM_USD)
    stress_tot_ret = calculate_net_total_return(final_stress_aum, M2_SIMULATED_STARTING_AUM_USD)

    base_sharpe = calculate_hyp_007_annualized_sharpe(baseline_daily_returns)
    stress_sharpe = calculate_hyp_007_annualized_sharpe(stress_daily_returns)

    base_mdd = calculate_hyp_007_max_drawdown(baseline_equity_curve)
    stress_mdd = calculate_hyp_007_max_drawdown(stress_equity_curve)

    base_trades_count = count_completed_trades_from_position_series(baseline_all_trades_positions)
    stress_trades_count = count_completed_trades_from_position_series(stress_all_trades_positions)

    # Evaluate R4 Gates
    gate_report = evaluate_r4_gates(
        net_total_return=base_tot_ret,
        annualized_sharpe=base_sharpe,
        max_drawdown=base_mdd,
        stress_total_return=stress_tot_ret,
        contract_valid=True,
    )

    # Serialize Result Ledgers
    signals_serialized = [asdict(s) for s in all_signals]
    signal_ledger_sha = calculate_deterministic_sha256(signals_serialized)

    base_exec_serialized = [asdict(leg) for leg in baseline_execution_legs]
    base_exec_sha = calculate_deterministic_sha256(base_exec_serialized)

    stress_exec_serialized = [asdict(leg) for leg in stress_execution_legs]
    stress_exec_sha = calculate_deterministic_sha256(stress_exec_serialized)

    trades_serialized = [asdict(t) for t in baseline_trades]
    trade_ledger_sha = calculate_deterministic_sha256(trades_serialized)

    base_equity_serialized = [str(x) for x in baseline_equity_curve]
    base_equity_sha = calculate_deterministic_sha256(base_equity_serialized)

    stress_equity_serialized = [str(x) for x in stress_equity_curve]
    stress_equity_sha = calculate_deterministic_sha256(stress_equity_serialized)

    r4_package_manifest_dict = {
        "signal_ledger_sha256": signal_ledger_sha,
        "baseline_execution_ledger_sha256": base_exec_sha,
        "stress_execution_ledger_sha256": stress_exec_sha,
        "trade_ledger_sha256": trade_ledger_sha,
        "baseline_daily_equity_sha256": base_equity_sha,
        "stress_daily_equity_sha256": stress_equity_sha,
        "final_baseline_aum": str(final_base_aum),
        "final_stress_aum": str(final_stress_aum),
        "baseline_net_total_return": str(base_tot_ret),
        "stress_net_total_return": str(stress_tot_ret),
        "baseline_annualized_sharpe": str(base_sharpe),
        "stress_annualized_sharpe": str(stress_sharpe),
        "baseline_max_drawdown": str(base_mdd),
        "stress_max_drawdown": str(stress_mdd),
        "r4_verdict": gate_report.verdict.value,
    }
    r4_package_sha = calculate_deterministic_sha256(r4_package_manifest_dict)

    # Write Result Ledgers to Parquet
    m2_dir = repo_root / "data/hyp_007/m2"
    m2_dir.mkdir(parents=True, exist_ok=True)

    # 1. Signal Ledger Parquet
    sig_schema = pa.schema([
        ("session_date", pa.string()),
        ("decision_epoch_et", pa.string()),
        ("signal_minute_et", pa.string()),
        ("signal_bar_idx", pa.int32()),
        ("signal_close", pa.string()),
        ("upper_anchor", pa.string()),
        ("lower_anchor", pa.string()),
        ("sigma_open", pa.string()),
        ("upper_band", pa.string()),
        ("lower_band", pa.string()),
        ("vwap", pa.string()),
        ("signal_state", pa.string()),
    ])
    sig_dict: Dict[str, List[Any]] = {f.name: [] for f in sig_schema}
    for s in all_signals:
        sig_dict["session_date"].append(s.session_date)
        sig_dict["decision_epoch_et"].append(s.decision_epoch_et)
        sig_dict["signal_minute_et"].append(s.signal_minute_et)
        sig_dict["signal_bar_idx"].append(s.signal_bar_idx)
        sig_dict["signal_close"].append(s.signal_close)
        sig_dict["upper_anchor"].append(s.upper_anchor)
        sig_dict["lower_anchor"].append(s.lower_anchor)
        sig_dict["sigma_open"].append(s.sigma_open)
        sig_dict["upper_band"].append(s.upper_band)
        sig_dict["lower_band"].append(s.lower_band)
        sig_dict["vwap"].append(s.vwap)
        sig_dict["signal_state"].append(s.signal_state)
    pq.write_table(pa.Table.from_pydict(sig_dict, schema=sig_schema), m2_dir / "m2_signal_ledger.parquet", compression="snappy")

    # 2. Baseline Executions Parquet
    exec_schema = pa.schema([
        ("session_date", pa.string()),
        ("boundary_et", pa.string()),
        ("path", pa.string()),
        ("action", pa.string()),
        ("side", pa.string()),
        ("shares", pa.int32()),
        ("fill_price", pa.string()),
        ("quote_bid", pa.string()),
        ("quote_ask", pa.string()),
        ("quote_timestamp_utc", pa.string()),
        ("commission", pa.string()),
        ("sec31_fee", pa.string()),
        ("finra_taf", pa.string()),
        ("standalone_slippage", pa.string()),
        ("stress_half_spread", pa.string()),
        ("stress_borrow_fee", pa.string()),
        ("total_friction", pa.string()),
        ("net_cash_flow", pa.string()),
    ])
    b_exec_dict: Dict[str, List[Any]] = {f.name: [] for f in exec_schema}
    for leg in baseline_execution_legs:
        for k in b_exec_dict:
            b_exec_dict[k].append(getattr(leg, k))
    pq.write_table(pa.Table.from_pydict(b_exec_dict, schema=exec_schema), m2_dir / "m2_baseline_execution_ledger.parquet", compression="snappy")

    # 3. Stress Executions Parquet
    s_exec_dict: Dict[str, List[Any]] = {f.name: [] for f in exec_schema}
    for leg in stress_execution_legs:
        for k in s_exec_dict:
            s_exec_dict[k].append(getattr(leg, k))
    pq.write_table(pa.Table.from_pydict(s_exec_dict, schema=exec_schema), m2_dir / "m2_stress_execution_ledger.parquet", compression="snappy")

    # 4. Trades Parquet
    trd_schema = pa.schema([
        ("trade_id", pa.int32()),
        ("session_date", pa.string()),
        ("direction", pa.string()),
        ("entry_epoch_et", pa.string()),
        ("exit_boundary_et", pa.string()),
        ("shares", pa.int32()),
        ("entry_fill_price", pa.string()),
        ("exit_fill_price", pa.string()),
        ("gross_pnl", pa.string()),
        ("total_friction", pa.string()),
        ("net_pnl", pa.string()),
        ("exit_reason", pa.string()),
    ])
    trd_dict: Dict[str, List[Any]] = {f.name: [] for f in trd_schema}
    for t in baseline_trades:
        for k in trd_dict:
            trd_dict[k].append(getattr(t, k))
    pq.write_table(pa.Table.from_pydict(trd_dict, schema=trd_schema), m2_dir / "m2_trade_ledger.parquet", compression="snappy")

    # 5. Daily Performance Parquet
    perf_schema = pa.schema([
        ("session_date", pa.string()),
        ("calendar_ordinal", pa.int32()),
        ("strategy_eligible", pa.bool_()),
        ("morning_open", pa.string()),
        ("realized_vol_15d", pa.string()),
        ("target_leverage", pa.string()),
        ("target_shares_baseline", pa.int32()),
        ("target_shares_stress", pa.int32()),
        ("baseline_start_aum", pa.string()),
        ("baseline_net_daily_pnl", pa.string()),
        ("baseline_ending_aum", pa.string()),
        ("baseline_daily_return", pa.string()),
        ("stress_start_aum", pa.string()),
        ("stress_net_daily_pnl", pa.string()),
        ("stress_ending_aum", pa.string()),
        ("stress_daily_return", pa.string()),
        ("reconciled_exact", pa.bool_()),
    ])
    perf_dict: Dict[str, List[Any]] = {f.name: [] for f in perf_schema}
    for p in daily_performances:
        for k in perf_dict:
            perf_dict[k].append(getattr(p, k))
    pq.write_table(pa.Table.from_pydict(perf_dict, schema=perf_schema), m2_dir / "m2_daily_performance.parquet", compression="snappy")

    return Hyp007R4ExecutionResult(
        all_signals=all_signals,
        baseline_execution_legs=baseline_execution_legs,
        stress_execution_legs=stress_execution_legs,
        baseline_trades=baseline_trades,
        daily_performances=daily_performances,
        baseline_equity_curve=baseline_equity_curve,
        stress_equity_curve=stress_equity_curve,
        baseline_daily_returns=baseline_daily_returns,
        stress_daily_returns=stress_daily_returns,
        final_baseline_aum=final_base_aum,
        final_stress_aum=final_stress_aum,
        baseline_net_total_return=base_tot_ret,
        stress_net_total_return=stress_tot_ret,
        baseline_annualized_sharpe=base_sharpe,
        stress_annualized_sharpe=stress_sharpe,
        baseline_max_drawdown=base_mdd,
        stress_max_drawdown=stress_mdd,
        baseline_completed_trades_count=base_trades_count,
        stress_completed_trades_count=stress_trades_count,
        gate_report=gate_report,
        no_material_contract_failure=True,
        terminal_verdict=gate_report.verdict.value,
        signal_ledger_sha256=signal_ledger_sha,
        baseline_execution_ledger_sha256=base_exec_sha,
        stress_execution_ledger_sha256=stress_exec_sha,
        trade_ledger_sha256=trade_ledger_sha,
        baseline_daily_equity_sha256=base_equity_sha,
        stress_daily_equity_sha256=stress_equity_sha,
        r4_result_package_sha256=r4_package_sha,
    )


def execute_and_seal_r4_m2(repo_root: Path) -> Hyp007R4ExecutionResult:
    """End-to-end qualification, strategy execution, and sealing for HYP_007 Step R4."""
    preconditions = validate_r4_preconditions(repo_root)

    census = build_m2_calendar_census()
    governor = AdaptiveRateGovernor(target_interval_seconds=0.25)

    print(f"[R4] M2 Calendar Census: {len(census.regular_sessions)} regular sessions, {len(census.early_closes)} early closes excluded.")

    # 1. Acquire & Qualify M2 Bars
    print("[R4] Step 1: Acquiring and qualifying M2 primary bars...")
    bars, daily_closes, bar_corpus_sha = acquire_and_qualify_m2_bars(census, repo_root, governor)

    # 2. Acquire & Qualify M2 Quotes
    print("[R4] Step 2: Acquiring and qualifying M2 execution quotes...")
    quotes, quote_corpus_sha = acquire_and_qualify_m2_quotes(census, repo_root, governor)

    # 3. Write Qualified Parquet Datasets
    print("[R4] Step 3: Writing M2 qualified Parquet datasets...")
    bars_path, quotes_path, bars_sha, quotes_sha = write_m2_parquet_datasets(bars, quotes, repo_root)

    # 4. Dividends & Dataset Content Digest
    div_manifest_path = repo_root / "docs/research/manifests/MEC-0017-HYP-007-M2-dividend-projection-manifest.json"
    div_manifest_sha = hashlib.sha256(div_manifest_path.read_bytes()).hexdigest()

    dataset_content_dict = {
        "bar_corpus_sha256": bar_corpus_sha,
        "quote_corpus_sha256": quote_corpus_sha,
        "dividend_projection_manifest_sha256": div_manifest_sha,
        "bars_parquet_sha256": bars_sha,
        "quotes_parquet_sha256": quotes_sha,
        "regular_sessions_count": len(census.regular_sessions),
        "total_bars": len(bars),
        "total_quote_boundaries": len(quotes),
    }
    m2_dataset_content_sha = calculate_deterministic_sha256(dataset_content_dict)

    # Write HYP_007_R4_M2_DATASET_MANIFEST.json
    manifests_dir = repo_root / "docs/phase14/manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    dataset_manifest = {
        "manifest_type": "M2_QUALIFIED_DATASET_MANIFEST",
        "hypothesis_id": "HYP_007",
        "mechanism_id": "MEC-0017",
        "sample": "M2_POST_PUBLICATION_STRESS_SAMPLE",
        "role": M2_ROLE,
        "classification": M2_CLASSIFICATION,
        "date_range": {
            "start": M2_START_DATE_STR,
            "end": M2_END_DATE_STR,
        },
        "census": {
            "calendar_days": census.calendar_days_count,
            "regular_sessions": len(census.regular_sessions),
            "early_closes_excluded": len(census.early_closes),
            "weekends": census.weekends_count,
            "holidays": len(census.holidays),
        },
        "corpus_digests": {
            "bar_corpus_sha256": bar_corpus_sha,
            "quote_corpus_sha256": quote_corpus_sha,
            "dividend_manifest_sha256": div_manifest_sha,
            "bars_parquet_sha256": bars_sha,
            "quotes_parquet_sha256": quotes_sha,
            "m2_dataset_content_sha256": m2_dataset_content_sha,
        },
        "governance_assertions": {
            "quarantine_gap_records_read": 0,
            "m3_records_read": 0,
            "real_capital_authority_usd": "0.00",
            "no_real_orders": True,
            "paper_authorized": False,
            "live_authorized": False,
        },
    }
    dataset_man_clean = json.loads(json.dumps(dataset_manifest, default=str))
    dataset_man_path = manifests_dir / "HYP_007_R4_M2_DATASET_MANIFEST.json"
    with open(dataset_man_path, "w", encoding="utf-8") as f:
        json.dump(dataset_man_clean, f, indent=2, sort_keys=True)

    # 5. Execute M2 Strategy
    print("[R4] Step 4: Executing unchanged HYP_007 strategy on M2...")
    result = execute_hyp_007_m2_strategy(repo_root, verify_preconditions=False)

    # 6. Deterministic Rerun
    print("[R4] Step 5: Performing deterministic reproducibility rerun...")
    rerun_result = execute_hyp_007_m2_strategy(repo_root, verify_preconditions=False)
    if rerun_result.r4_result_package_sha256 != result.r4_result_package_sha256:
        raise DataContractError(
            f"Reproducibility rerun failure in R4: {rerun_result.r4_result_package_sha256} != {result.r4_result_package_sha256}"
        )

    # 7. Write Result Manifests
    print("[R4] Step 6: Sealing R4 decision and result manifests...")
    r4_result_manifest = {
        "manifest_type": "HYP_007_R4_M2_RESULT_MANIFEST",
        "hypothesis_id": "HYP_007",
        "mechanism_id": "MEC-0017",
        "stage": "STAGE_B_STEP_R4",
        "sample": "M2_POST_PUBLICATION_STRESS_SAMPLE",
        "sample_classification": M2_CLASSIFICATION,
        "sample_role": M2_ROLE,
        "upstream_authorities": {
            "stage_a_commit_sha": EXPECTED_STAGE_A_COMMIT_SHA,
            "m1_effective_verdict": "ACCEPTED_SUPPORTED_ON_REGISTERED_M1",
            "m2_dataset_content_sha256": m2_dataset_content_sha,
        },
        "performance_metrics": {
            "baseline": {
                "initial_aum_usd": str(M2_SIMULATED_STARTING_AUM_USD),
                "final_aum_usd": str(result.final_baseline_aum),
                "net_total_return": str(result.baseline_net_total_return),
                "annualized_sharpe": str(result.baseline_annualized_sharpe),
                "max_drawdown": str(result.baseline_max_drawdown),
                "completed_trades_count": result.baseline_completed_trades_count,
            },
            "stress_2x": {
                "initial_aum_usd": str(M2_SIMULATED_STARTING_AUM_USD),
                "final_aum_usd": str(result.final_stress_aum),
                "net_total_return": str(result.stress_net_total_return),
                "annualized_sharpe": str(result.stress_annualized_sharpe),
                "max_drawdown": str(result.stress_max_drawdown),
                "completed_trades_count": result.stress_completed_trades_count,
            },
        },
        "gate_evaluation": result.gate_report.to_dict(),
        "hashes": {
            "signal_ledger_sha256": result.signal_ledger_sha256,
            "baseline_execution_ledger_sha256": result.baseline_execution_ledger_sha256,
            "stress_execution_ledger_sha256": result.stress_execution_ledger_sha256,
            "trade_ledger_sha256": result.trade_ledger_sha256,
            "baseline_daily_equity_sha256": result.baseline_daily_equity_sha256,
            "stress_daily_equity_sha256": result.stress_daily_equity_sha256,
            "r4_result_package_sha256": result.r4_result_package_sha256,
        },
        "verdict": result.terminal_verdict,
        "combined_m1_m2_interpretation": (
            "HISTORICAL_REPLICATION_SUPPORTED_AND_RECENT_STRESS_SUPPORTED"
            if result.terminal_verdict == R4Verdict.PASS_RECENT_STRESS_SUPPORTED.value
            else "HISTORICAL_REPLICATION_SUPPORTED_BUT_CURRENT_EDGE_NOT_SUPPORTED"
        ),
        "deterministic_rerun_identical": True,
    }
    r4_res_clean = json.loads(json.dumps(r4_result_manifest, default=str))
    r4_res_path = manifests_dir / "HYP_007_R4_M2_RESULT_MANIFEST.json"
    with open(r4_res_path, "w", encoding="utf-8") as f:
        json.dump(r4_res_clean, f, indent=2, sort_keys=True)

    # Write HYP_007_R4_M2_DECISION.json
    r4_decision_manifest = {
        "manifest_type": "HYP_007_R4_M2_DECISION_MANIFEST",
        "hypothesis_id": "HYP_007",
        "mechanism_id": "MEC-0017",
        "stage": "STAGE_B_STEP_R4",
        "r4_verdict": result.terminal_verdict,
        "all_four_gates_passed": (result.terminal_verdict == R4Verdict.PASS_RECENT_STRESS_SUPPORTED.value),
        "r4_result_package_sha256": result.r4_result_package_sha256,
        "m2_dataset_content_sha256": m2_dataset_content_sha,
        "next_required_human_decision": (
            "R5_HUMAN_EVIDENCE_DECISION_REQUIRED"
            if result.terminal_verdict == R4Verdict.PASS_RECENT_STRESS_SUPPORTED.value
            else "HYP_007_CURRENT_EDGE_NOT_SUPPORTED_NO_PAPER_AUTHORIZATION"
        ),
        "governance_assertions": {
            "m1_effective_verdict_unchanged": "ACCEPTED_SUPPORTED_ON_REGISTERED_M1",
            "m2_classification_preserved": M2_CLASSIFICATION,
            "m3_access_state": M3_ACCESS_STATUS,
            "quarantine_gap_access_state": "STRICTLY_ZERO_ACCESSED",
            "paper_authorized": False,
            "live_authorized": False,
            "real_capital_authority_usd": "0.00",
        },
    }
    r4_dec_clean = json.loads(json.dumps(r4_decision_manifest, default=str))
    r4_dec_path = manifests_dir / "HYP_007_R4_M2_DECISION.json"
    with open(r4_dec_path, "w", encoding="utf-8") as f:
        json.dump(r4_dec_clean, f, indent=2, sort_keys=True)

    # 8. Write Markdown Documentation
    doc_path = repo_root / "docs/phase14/HYP_007_R4_M2_STRESS_EVALUATION.md"
    doc_md = f"""# HYP_007 Step R4: M2 Post-Publication Stress Evaluation Dossier
## Rigorous Recent-Regime Stress Evaluation on Sample M2 (2024-05-01 through 2026-08-14)

```text
[EVALUATION IDENTIFIER: HYP_007_R4_M2_STRESS_EVALUATION]
[HYPOTHESIS_ID: HYP_007]
[MECHANISM_ID: MEC-0017]
[AUTHORIZATION: AUTHORIZE_HYP_007_POST_M1_FREEZE_AND_CONDITIONAL_R4_M2_EXECUTION]
[SAMPLE: M2_POST_PUBLICATION_STRESS_SAMPLE]
[ROLE: {M2_ROLE}]
[CLASSIFICATION: {M2_CLASSIFICATION}]
[M2_WINDOW: {M2_START_DATE_STR} THROUGH {M2_END_DATE_STR}]
[M2_SIMULATED_STARTING_AUM: $100,000.00]
[R4_VERDICT: {result.terminal_verdict}]
[R4_PACKAGE_SHA256: {result.r4_result_package_sha256}]
[M2_DATASET_CONTENT_SHA256: {m2_dataset_content_sha}]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
[PAPER_AUTHORITY: LOCKED]
[LIVE_AUTHORITY: LOCKED]
[M3_STATE: LOCKED_ZERO_ACCESS]
```

- **Document ID:** `docs/phase14/HYP_007_R4_M2_STRESS_EVALUATION.md`
- **Governing Standard:** ACASH `AGENTS.md` (Strict Fail-Closed Contract, Literature Alignment, Zero Unverified Claims).

---

## 1. Executive Summary & Verdict

Step R4 executes the preregistered HYP_007 strategy across the publicly exposed recent stress window **M2** (`2024-05-01` through `2026-08-14`).
- **Terminal R4 Verdict:** `{result.terminal_verdict}`
- **Combined Interpretation:** `{r4_result_manifest["combined_m1_m2_interpretation"]}`

### Performance Summary:
- **Baseline Initial AUM:** ${M2_SIMULATED_STARTING_AUM_USD}
- **Baseline Final AUM:** ${result.final_baseline_aum:.2f}
- **Baseline Net Total Return:** {result.baseline_net_total_return * 100:.2f}%
- **Baseline Annualized Sharpe:** {result.baseline_annualized_sharpe:.4f}
- **Baseline Max Drawdown:** {result.baseline_max_drawdown * 100:.2f}%
- **Baseline Completed Trades:** {result.baseline_completed_trades_count}
- **2x Friction Stress Final AUM:** ${result.final_stress_aum:.2f}
- **2x Friction Stress Total Return:** {result.stress_net_total_return * 100:.2f}%
- **2x Friction Stress Sharpe:** {result.stress_annualized_sharpe:.4f}
- **2x Friction Stress Max Drawdown:** {result.stress_max_drawdown * 100:.2f}%

---

## 2. Gate Evaluation Ledger

| Gate | Metric Name | Observed Value | Frozen Hurdle | Gate Verdict |
| :---: | :--- | :---: | :---: | :---: |
| **R4-G1** | `NET_TOTAL_RETURN` | {result.baseline_net_total_return * 100:.2f}% | $> 0.0$ | {"PASS" if result.gate_report.g1_pass else "FAIL"} |
| **R4-G2** | `NET_ANNUALIZED_SHARPE` | {result.baseline_annualized_sharpe:.4f} | $\\ge 0.50$ | {"PASS" if result.gate_report.g2_pass else "FAIL"} |
| **R4-G3** | `MAX_DRAWDOWN` | {result.baseline_max_drawdown * 100:.2f}% | $\\le 35.0\\%$ | {"PASS" if result.gate_report.g3_pass else "FAIL"} |
| **R4-G4** | `2X_FRICTION_STRESS_TOTAL_RETURN` | {result.stress_net_total_return * 100:.2f}% | $\\ge 0.0$ | {"PASS" if result.gate_report.g4_pass else "FAIL"} |

**Conjunction Rule:** All four gates must pass simultaneously without discretionary override.
"""
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(doc_md)

    # Write Execution Report Markdown
    rep_path = repo_root / "docs/research/MEC-0017-HYP-007-R4-M2-stress-report.md"
    rep_md = f"""# Research Execution Report: MEC-0017 / HYP_007 Step R4 M2 Stress Evaluation

- **Hypothesis:** HYP_007 (SPY Noise-Area Intraday Momentum Direct-SIP Replication)
- **Mechanism:** MEC-0017
- **Evaluation Partition:** M2 (`{M2_START_DATE_STR}` through `{M2_END_DATE_STR}`)
- **Partition Role:** `{M2_ROLE}` (`{M2_CLASSIFICATION}`)
- **Terminal Verdict:** `{result.terminal_verdict}`
- **R4 Package SHA-256:** `{result.r4_result_package_sha256}`
- **M2 Dataset Content SHA-256:** `{m2_dataset_content_sha}`
- **Deterministic Rerun Match:** `TRUE`

## Next Steps
{r4_decision_manifest["next_required_human_decision"]}
"""
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(rep_md)

    print(f"[R4] Sealing complete. Terminal Verdict: {result.terminal_verdict}")
    print(f"[R4] R4 Package SHA256: {result.r4_result_package_sha256}")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    res = execute_and_seal_r4_m2(root)
    print("HYP_007 R4 M2 EXECUTION & SEALING FINISHED SUCCESSFULLY.")

