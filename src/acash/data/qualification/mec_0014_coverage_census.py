"""MEC-0014: SPY Primary Closing Auction Coverage Census (2017–2022).

Determines whether historical exceptional/fallback Official Closing Price logic
is required for the candidate 2017–2022 research window by verifying whether
every qualified regular session contains exactly one valid NYSE Arca closing cross.

STRICT INVARIANTS:
1. In-Sample Scope: 2017-01-01 through 2022-12-31 ONLY.
2. Hard OOS Block: >= 2023-01-01 aborts immediately with DataContractError.
3. Sovereign Calendar Authority: NyseCa1Calendar regular sessions only (390m).
4. Qualifying Candidate Definition:
   - Primary listing venue: 'P' (NYSE Arca)
   - Closing condition: '6' (Market Center Closing Trade)
   - Auction record type: 'c' (Closing auction)
5. Zero Price/Return/Strategy Logic: Pure data contract existence qualification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar, SessionType
from acash.data.qualification.mec_0014_close_contract import (
    IS_END_DATE,
    IS_START_DATE,
    OOS_FORBIDDEN_DATE,
    AuctionRecord,
)

PRIMARY_LISTING_EXCHANGE: str = "P"
PRIMARY_CLOSING_CONDITION: str = "6"
PRIMARY_AUCTION_TYPE: str = "c"


class AuctionCoverageClassification(str, Enum):
    """Classification of closing auction availability for a single session."""

    UNIQUE_PRIMARY_AUCTION = "UNIQUE_PRIMARY_AUCTION"
    MISSING_PRIMARY_AUCTION = "MISSING_PRIMARY_AUCTION"
    AMBIGUOUS_PRIMARY_AUCTION = "AMBIGUOUS_PRIMARY_AUCTION"


class CoverageDecisionClassification(str, Enum):
    """Aggregate decision on sample-wide closing auction sufficiency."""

    COMPLETE_NORMAL_PATH = "COMPLETE_NORMAL_PATH"
    INCOMPLETE_REQUIRES_EXCEPTIONAL_PATH_AUDIT = "INCOMPLETE_REQUIRES_EXCEPTIONAL_PATH_AUDIT"


@dataclass(frozen=True)
class SessionAuctionCoverage:
    """Coverage audit record for a single regular trading session."""

    session_date: str
    classification: AuctionCoverageClassification
    candidate_count: int
    primary_candidate_price: Optional[str]
    primary_candidate_size: Optional[int]
    primary_candidate_timestamp: Optional[str]
    primary_candidate_exchange: Optional[str]
    primary_candidate_condition: Optional[str]
    non_candidate_count: int
    anomalous_candidates: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_date": self.session_date,
            "classification": self.classification.value,
            "candidate_count": self.candidate_count,
            "primary_candidate_price": self.primary_candidate_price,
            "primary_candidate_size": self.primary_candidate_size,
            "primary_candidate_timestamp": self.primary_candidate_timestamp,
            "primary_candidate_exchange": self.primary_candidate_exchange,
            "primary_candidate_condition": self.primary_candidate_condition,
            "non_candidate_count": self.non_candidate_count,
            "anomalous_candidates": self.anomalous_candidates,
        }


@dataclass(frozen=True)
class CoverageCensusResult:
    """Deterministic summary of sample-wide auction coverage census."""

    total_qualified_sessions: int
    total_queried_sessions: int
    unique_count: int
    missing_count: int
    ambiguous_count: int
    coverage_percentage: str
    decision: CoverageDecisionClassification
    historical_fallback_requirement: str
    missing_dates: List[str]
    ambiguous_dates: List[str]
    anomalous_sessions: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_qualified_sessions": self.total_qualified_sessions,
            "total_queried_sessions": self.total_queried_sessions,
            "unique_count": self.unique_count,
            "missing_count": self.missing_count,
            "ambiguous_count": self.ambiguous_count,
            "coverage_percentage": self.coverage_percentage,
            "decision": self.decision.value,
            "historical_fallback_requirement": self.historical_fallback_requirement,
            "missing_dates": self.missing_dates,
            "ambiguous_dates": self.ambiguous_dates,
            "anomalous_sessions": self.anomalous_sessions,
        }


def assert_in_sample_census_date(d: date) -> None:
    """Fail-closed boundary check for census dates."""
    if d >= OOS_FORBIDDEN_DATE:
        raise DataContractError(
            f"Requested census date {d.isoformat()} violates OOS boundary >= {OOS_FORBIDDEN_DATE.isoformat()}."
        )
    if d < IS_START_DATE or d > IS_END_DATE:
        raise DataContractError(
            f"Requested census date {d.isoformat()} outside authorized IS window [{IS_START_DATE}, {IS_END_DATE}]."
        )


def enumerate_qualified_regular_sessions(
    calendar: Optional[NyseCa1Calendar] = None,
    start_date: date = IS_START_DATE,
    end_date: date = IS_END_DATE,
) -> List[date]:
    """Enumerate all regular 390-minute trading sessions within [start_date, end_date].

    Strictly adheres to sovereign NyseCa1Calendar authority. Excludes early closes
    and non-trading days. Enforces hard fail-closed OOS boundary.
    """
    cal = calendar or NyseCa1Calendar()
    assert_in_sample_census_date(start_date)
    assert_in_sample_census_date(end_date)

    if start_date > end_date:
        raise DataContractError(f"start_date ({start_date}) cannot be after end_date ({end_date}).")

    regular_sessions: List[date] = []
    curr = start_date
    while curr <= end_date:
        assert_in_sample_census_date(curr)
        if cal.is_trading_session(curr):
            sess = cal.get_session(curr)
            if sess.session_type == SessionType.REGULAR and sess.expected_minute_count == 390:
                regular_sessions.append(curr)
        curr = curr.fromordinal(curr.toordinal() + 1)

    return regular_sessions


def classify_session_auctions(
    session_date: date,
    auctions: Sequence[AuctionRecord],
    target_symbol: str = "SPY",
) -> SessionAuctionCoverage:
    """Classify the primary closing auction coverage for a single trading session.

    A qualifying candidate MUST satisfy:
    1. auction_type == 'c' (Closing auction)
    2. exchange == 'P' (NYSE Arca primary listing venue)
    3. condition == '6' (Market Center Closing Trade)

    All other records (e.g. 'o' opening auctions, secondary venue 'T' auctions,
    or condition 'M' official close summaries) do NOT satisfy primary closing cross.
    """
    assert_in_sample_census_date(session_date)

    primary_candidates: List[AuctionRecord] = []
    non_candidates: List[AuctionRecord] = []

    for auc in auctions:
        if (
            auc.auction_type == PRIMARY_AUCTION_TYPE
            and auc.exchange == PRIMARY_LISTING_EXCHANGE
            and auc.condition == PRIMARY_CLOSING_CONDITION
        ):
            primary_candidates.append(auc)
        else:
            non_candidates.append(auc)

    cand_count = len(primary_candidates)
    if cand_count == 1:
        cand = primary_candidates[0]
        return SessionAuctionCoverage(
            session_date=session_date.isoformat(),
            classification=AuctionCoverageClassification.UNIQUE_PRIMARY_AUCTION,
            candidate_count=1,
            primary_candidate_price=str(cand.price),
            primary_candidate_size=cand.size,
            primary_candidate_timestamp=cand.timestamp_utc,
            primary_candidate_exchange=cand.exchange,
            primary_candidate_condition=cand.condition,
            non_candidate_count=len(non_candidates),
            anomalous_candidates=[],
        )
    elif cand_count == 0:
        return SessionAuctionCoverage(
            session_date=session_date.isoformat(),
            classification=AuctionCoverageClassification.MISSING_PRIMARY_AUCTION,
            candidate_count=0,
            primary_candidate_price=None,
            primary_candidate_size=None,
            primary_candidate_timestamp=None,
            primary_candidate_exchange=None,
            primary_candidate_condition=None,
            non_candidate_count=len(non_candidates),
            anomalous_candidates=[
                {
                    "exchange": a.exchange,
                    "condition": a.condition,
                    "type": a.auction_type,
                    "price": str(a.price),
                    "size": a.size,
                    "timestamp": a.timestamp_utc,
                }
                for a in non_candidates
            ],
        )
    else:
        return SessionAuctionCoverage(
            session_date=session_date.isoformat(),
            classification=AuctionCoverageClassification.AMBIGUOUS_PRIMARY_AUCTION,
            candidate_count=cand_count,
            primary_candidate_price=None,
            primary_candidate_size=None,
            primary_candidate_timestamp=None,
            primary_candidate_exchange=None,
            primary_candidate_condition=None,
            non_candidate_count=len(non_candidates),
            anomalous_candidates=[
                {
                    "exchange": a.exchange,
                    "condition": a.condition,
                    "type": a.auction_type,
                    "price": str(a.price),
                    "size": a.size,
                    "timestamp": a.timestamp_utc,
                }
                for a in primary_candidates
            ],
        )


def evaluate_census_results(
    session_coverages: Sequence[SessionAuctionCoverage],
    expected_session_count: int,
) -> CoverageCensusResult:
    """Synthesize session-level coverages into sample-wide census decision."""
    total_queried = len(session_coverages)
    if total_queried != expected_session_count:
        raise DataContractError(
            f"Queried session count ({total_queried}) != expected session count ({expected_session_count})."
        )

    unique_count = 0
    missing_count = 0
    ambiguous_count = 0
    missing_dates: List[str] = []
    ambiguous_dates: List[str] = []
    anomalous_sessions: List[Dict[str, Any]] = []

    for sc in session_coverages:
        if sc.classification == AuctionCoverageClassification.UNIQUE_PRIMARY_AUCTION:
            unique_count += 1
        elif sc.classification == AuctionCoverageClassification.MISSING_PRIMARY_AUCTION:
            missing_count += 1
            missing_dates.append(sc.session_date)
            anomalous_sessions.append(sc.to_dict())
        elif sc.classification == AuctionCoverageClassification.AMBIGUOUS_PRIMARY_AUCTION:
            ambiguous_count += 1
            ambiguous_dates.append(sc.session_date)
            anomalous_sessions.append(sc.to_dict())

    if total_queried > 0:
        cov_pct = (Decimal(unique_count) / Decimal(total_queried) * Decimal(100)).quantize(
            Decimal("0.0001")
        )
    else:
        cov_pct = Decimal("0.0000")

    if unique_count == total_queried and total_queried > 0:
        decision = CoverageDecisionClassification.COMPLETE_NORMAL_PATH
        fallback_req = "NOT_REQUIRED_FOR_OBSERVED_2017_2022_SPY_SESSIONS"
    else:
        decision = CoverageDecisionClassification.INCOMPLETE_REQUIRES_EXCEPTIONAL_PATH_AUDIT
        fallback_req = "REQUIRED_FOR_UNCOVERED_SESSIONS"

    return CoverageCensusResult(
        total_qualified_sessions=expected_session_count,
        total_queried_sessions=total_queried,
        unique_count=unique_count,
        missing_count=missing_count,
        ambiguous_count=ambiguous_count,
        coverage_percentage=f"{cov_pct}%",
        decision=decision,
        historical_fallback_requirement=fallback_req,
        missing_dates=missing_dates,
        ambiguous_dates=ambiguous_dates,
        anomalous_sessions=anomalous_sessions,
    )
