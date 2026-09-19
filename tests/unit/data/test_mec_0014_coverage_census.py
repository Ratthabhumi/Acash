"""Unit tests for MEC-0014 SPY Primary Closing Auction Coverage Census.

Validates deterministic classification, hard OOS boundaries, fail-closed handling,
and non-substitution invariants.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.mec_0014_close_contract import AuctionRecord
from acash.data.qualification.mec_0014_coverage_census import (
    AuctionCoverageClassification,
    CoverageCensusResult,
    CoverageDecisionClassification,
    SessionAuctionCoverage,
    assert_in_sample_census_date,
    classify_session_auctions,
    enumerate_qualified_regular_sessions,
    evaluate_census_results,
)


def _make_auction(
    price: str = "243.36",
    size: int = 1000000,
    exchange: str = "P",
    condition: str = "6",
    auction_type: str = "c",
    timestamp: str = "2017-06-01T20:00:00.104Z",
) -> AuctionRecord:
    return AuctionRecord(
        timestamp_utc=timestamp,
        price=Decimal(price),
        size=size,
        exchange=exchange,
        condition=condition,
        auction_type=auction_type,
    )


class TestMec0014CoverageCensus:
    """Deterministic validation of coverage census classification and invariants."""

    def test_oos_hard_rejection(self) -> None:
        """Any date on or after 2023-01-01 MUST trigger DataContractError immediately."""
        with pytest.raises(DataContractError, match="violates OOS boundary"):
            assert_in_sample_census_date(date(2023, 1, 1))

        with pytest.raises(DataContractError, match="violates OOS boundary"):
            assert_in_sample_census_date(date(2024, 6, 1))

        with pytest.raises(DataContractError, match="violates OOS boundary"):
            classify_session_auctions(date(2023, 1, 3), [_make_auction()])

    def test_outside_is_range_rejection(self) -> None:
        """Dates prior to 2017-01-01 are outside authorized IS window."""
        with pytest.raises(DataContractError, match="outside authorized IS window"):
            assert_in_sample_census_date(date(2016, 12, 31))

    def test_unique_primary_auction_classification(self) -> None:
        """Exactly one x=P, c=6 closing auction yields UNIQUE_PRIMARY_AUCTION."""
        d = date(2017, 6, 1)
        auctions = [
            _make_auction(price="243.36", size=3929774, exchange="P", condition="6", auction_type="c"),
            _make_auction(price="243.30", size=1695, exchange="T", condition="6", auction_type="c"),
            _make_auction(price="241.97", size=158783, exchange="P", condition="O", auction_type="o"),
        ]
        cov = classify_session_auctions(d, auctions)
        assert cov.classification == AuctionCoverageClassification.UNIQUE_PRIMARY_AUCTION
        assert cov.candidate_count == 1
        assert cov.primary_candidate_price == "243.36"
        assert cov.primary_candidate_size == 3929774
        assert cov.primary_candidate_exchange == "P"
        assert cov.primary_candidate_condition == "6"
        assert cov.non_candidate_count == 2
        assert len(cov.anomalous_candidates) == 0

    def test_missing_primary_auction_classification(self) -> None:
        """Zero x=P, c=6 records yields MISSING_PRIMARY_AUCTION."""
        d = date(2017, 6, 1)
        # Only secondary venue or opening auctions
        auctions = [
            _make_auction(price="243.30", size=1695, exchange="T", condition="6", auction_type="c"),
            _make_auction(price="241.97", size=158783, exchange="P", condition="O", auction_type="o"),
        ]
        cov = classify_session_auctions(d, auctions)
        assert cov.classification == AuctionCoverageClassification.MISSING_PRIMARY_AUCTION
        assert cov.candidate_count == 0
        assert cov.primary_candidate_price is None
        assert len(cov.anomalous_candidates) == 2

    def test_ambiguous_primary_auction_classification(self) -> None:
        """Multiple x=P, c=6 records yields AMBIGUOUS_PRIMARY_AUCTION."""
        d = date(2017, 6, 1)
        auctions = [
            _make_auction(price="243.36", size=2000000, exchange="P", condition="6", auction_type="c", timestamp="2017-06-01T20:00:00.100Z"),
            _make_auction(price="243.37", size=1929774, exchange="P", condition="6", auction_type="c", timestamp="2017-06-01T20:00:00.200Z"),
        ]
        cov = classify_session_auctions(d, auctions)
        assert cov.classification == AuctionCoverageClassification.AMBIGUOUS_PRIMARY_AUCTION
        assert cov.candidate_count == 2
        assert cov.primary_candidate_price is None
        assert len(cov.anomalous_candidates) == 2

    def test_secondary_exchange_cannot_satisfy_primary(self) -> None:
        """NASDAQ (x=T) or other secondary auction cannot satisfy primary coverage."""
        d = date(2018, 6, 1)
        auctions = [
            _make_auction(price="273.50", size=5000, exchange="T", condition="6", auction_type="c"),
            _make_auction(price="273.49", size=1000, exchange="Q", condition="6", auction_type="c"),
        ]
        cov = classify_session_auctions(d, auctions)
        assert cov.classification == AuctionCoverageClassification.MISSING_PRIMARY_AUCTION
        assert cov.candidate_count == 0

    def test_condition_m_cannot_satisfy_closing_auction(self) -> None:
        """Condition 'M' (Market Center Official Close summary) cannot satisfy c=6 closing auction."""
        d = date(2019, 6, 3)
        auctions = [
            _make_auction(price="274.50", size=0, exchange="P", condition="M", auction_type="c"),
        ]
        cov = classify_session_auctions(d, auctions)
        assert cov.classification == AuctionCoverageClassification.MISSING_PRIMARY_AUCTION

    def test_opening_auction_cannot_satisfy_closing_auction(self) -> None:
        """Auction type 'o' (opening) with condition '6' or 'O' cannot satisfy closing cross."""
        d = date(2020, 6, 1)
        auctions = [
            _make_auction(price="305.00", size=100000, exchange="P", condition="6", auction_type="o"),
        ]
        cov = classify_session_auctions(d, auctions)
        assert cov.classification == AuctionCoverageClassification.MISSING_PRIMARY_AUCTION

    def test_deterministic_session_enumeration(self) -> None:
        """Calendar session enumeration produces deterministic 1498 regular sessions for 2017-2022."""
        cal = NyseCa1Calendar()
        sessions = enumerate_qualified_regular_sessions(calendar=cal, start_date=date(2017, 1, 1), end_date=date(2022, 12, 31))
        assert len(sessions) == 1498
        assert sessions[0] == date(2017, 1, 3)
        assert sessions[-1] == date(2022, 12, 30)
        # Verify all are strictly within IS
        for s in sessions:
            assert date(2017, 1, 1) <= s <= date(2022, 12, 31)

    def test_census_evaluation_complete_normal_path(self) -> None:
        """100% unique coverages synthesize into COMPLETE_NORMAL_PATH."""
        coverages = [
            SessionAuctionCoverage(
                session_date="2017-06-01",
                classification=AuctionCoverageClassification.UNIQUE_PRIMARY_AUCTION,
                candidate_count=1,
                primary_candidate_price="243.36",
                primary_candidate_size=3929774,
                primary_candidate_timestamp="2017-06-01T20:00:00.104Z",
                primary_candidate_exchange="P",
                primary_candidate_condition="6",
                non_candidate_count=2,
            ),
            SessionAuctionCoverage(
                session_date="2017-06-02",
                classification=AuctionCoverageClassification.UNIQUE_PRIMARY_AUCTION,
                candidate_count=1,
                primary_candidate_price="244.17",
                primary_candidate_size=2500000,
                primary_candidate_timestamp="2017-06-02T20:00:00.090Z",
                primary_candidate_exchange="P",
                primary_candidate_condition="6",
                non_candidate_count=1,
            ),
        ]
        res = evaluate_census_results(coverages, expected_session_count=2)
        assert res.total_qualified_sessions == 2
        assert res.unique_count == 2
        assert res.missing_count == 0
        assert res.ambiguous_count == 0
        assert res.coverage_percentage == "100.0000%"
        assert res.decision == CoverageDecisionClassification.COMPLETE_NORMAL_PATH
        assert res.historical_fallback_requirement == "NOT_REQUIRED_FOR_OBSERVED_2017_2022_SPY_SESSIONS"
        assert len(res.missing_dates) == 0
        assert len(res.ambiguous_dates) == 0

    def test_census_evaluation_incomplete_path(self) -> None:
        """Any missing session synthesizes into INCOMPLETE_REQUIRES_EXCEPTIONAL_PATH_AUDIT."""
        coverages = [
            SessionAuctionCoverage(
                session_date="2017-06-01",
                classification=AuctionCoverageClassification.UNIQUE_PRIMARY_AUCTION,
                candidate_count=1,
                primary_candidate_price="243.36",
                primary_candidate_size=3929774,
                primary_candidate_timestamp="2017-06-01T20:00:00.104Z",
                primary_candidate_exchange="P",
                primary_candidate_condition="6",
                non_candidate_count=2,
            ),
            SessionAuctionCoverage(
                session_date="2017-06-02",
                classification=AuctionCoverageClassification.MISSING_PRIMARY_AUCTION,
                candidate_count=0,
                primary_candidate_price=None,
                primary_candidate_size=None,
                primary_candidate_timestamp=None,
                primary_candidate_exchange=None,
                primary_candidate_condition=None,
                non_candidate_count=1,
            ),
        ]
        res = evaluate_census_results(coverages, expected_session_count=2)
        assert res.total_qualified_sessions == 2
        assert res.unique_count == 1
        assert res.missing_count == 1
        assert res.coverage_percentage == "50.0000%"
        assert res.decision == CoverageDecisionClassification.INCOMPLETE_REQUIRES_EXCEPTIONAL_PATH_AUDIT
        assert res.missing_dates == ["2017-06-02"]

    def test_no_secret_leakage_in_models(self) -> None:
        """Serialized models must not contain any API keys, secrets, or environment credentials."""
        cov = SessionAuctionCoverage(
            session_date="2017-06-01",
            classification=AuctionCoverageClassification.UNIQUE_PRIMARY_AUCTION,
            candidate_count=1,
            primary_candidate_price="243.36",
            primary_candidate_size=3929774,
            primary_candidate_timestamp="2017-06-01T20:00:00.104Z",
            primary_candidate_exchange="P",
            primary_candidate_condition="6",
            non_candidate_count=2,
        )
        as_json = json.dumps(cov.to_dict())
        assert "APCA" not in as_json
        assert "KEY" not in as_json
        assert "SECRET" not in as_json

    def test_exceptional_sessions_never_invoke_fallback(self) -> None:
        """Missing sessions must report classification MISSING without attempting fallback calculation."""
        cov = classify_session_auctions(date(2017, 6, 1), [])
        assert cov.classification == AuctionCoverageClassification.MISSING_PRIMARY_AUCTION
        # Fallback price is strictly None, never synthesized
        assert cov.primary_candidate_price is None
