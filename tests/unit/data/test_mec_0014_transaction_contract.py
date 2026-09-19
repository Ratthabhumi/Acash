"""Unit tests for MEC-0014A Alpaca SIP Transaction Contract Qualification.

Covers:
1. Temporal boundary guards (OOS fail closed before network access).
2. Feed & symbol validation.
3. Timestamp bounds validation.
4. Boundary endpoint classification (Price-Authority Contract):
   - UNIQUE_BOUNDARY_PRICE (single trade at max timestamp T*)
   - UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE (multiple trades at T*, all same price)
   - AMBIGUOUS_BOUNDARY_PRICE (multiple trades at T*, distinct prices -> fail-closed)
   - max(trade_id) is NOT used as a tie-breaker
   - Terminology: exact_boundary_timestamp_match vs pre-boundary T*
   - MISSING_PRE_BOUNDARY_TRANSACTION
5. Duplicate detection & trade ID semantics:
   - detect_transport_duplicates (exact full-record equality; must be 0)
   - Duplicate trade IDs across exchanges do NOT equal transport duplicate
   - Duplicate trade IDs on same exchange do NOT provide sequencing authority
   - TRADE_ID_ORDERING_AUTHORITY = NOT_ESTABLISHED
6. Daily trade count mapping:
   - Condition 'I' (odd lots) retained in raw count
   - Pre-market / after-hours excluded
   - GAO_MIN_DAILY_TRADE_COUNT == 500 (never 10)
7. Session-level qualification integration (zero return computation invariant).
8. Aggregate probe synthesis (price-authority & provider operationalization).
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import List, Optional

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0014_transaction_contract import (
    BOUNDARY_1000_ET,
    BOUNDARY_1530_ET,
    BoundaryCandidate,
    BoundaryEndpointClassification,
    EndpointMappingProposedClassification,
    EXACT_TRANSPORT_DUPLICATES_OBSERVED,
    GAO_MIN_DAILY_TRADE_COUNT,
    QUALIFIED_FEED,
    QUALIFIED_SYMBOL,
    TRADE_ID_ORDERING_AUTHORITY,
    TradeCountMappingProposedClassification,
    RawSipTradeRecord,
    SessionTransactionQualification,
    TransactionContractProbeResult,
    assert_qualified_feed,
    assert_qualified_symbol,
    assert_response_symbol,
    assert_response_timestamp_in_bounds,
    assert_transaction_probe_date,
    build_condition_census,
    build_exchange_census,
    build_tape_census,
    classify_boundary_endpoint,
    detect_trade_id_collisions,
    detect_transport_duplicates,
    filter_regular_session_records,
    parse_trades_page,
    qualify_session_transactions,
    synthesize_probe_result,
)

_D = date(2020, 6, 1)


def _make_trade(
    timestamp_et_str: str,
    price: str = "450.00",
    size: int = 100,
    exchange: str = "P",
    conditions: Optional[List[str]] = None,
    tape: str = "B",
    trade_id: Optional[int] = 1,
    symbol: str = QUALIFIED_SYMBOL,
    session_date: date = _D,
) -> RawSipTradeRecord:
    """Helper: construct RawSipTradeRecord from ET time string like '2020-06-01T10:00:00'."""
    dt_et = datetime.fromisoformat(timestamp_et_str)
    # Convert EDT to UTC: 10:00 EDT = 14:00 UTC
    dt_utc = dt_et.replace(tzinfo=timezone.utc)
    # June is EDT (UTC-4), so UTC hour = ET hour + 4
    utc_hour = dt_et.hour + 4
    ts_utc = f"{session_date.isoformat()}T{utc_hour:02d}:{dt_et.minute:02d}:{dt_et.second:02d}.{dt_et.microsecond:06d}Z"
    return RawSipTradeRecord(
        timestamp_utc=ts_utc,
        price=Decimal(price),
        size=size,
        exchange=exchange,
        conditions=conditions if conditions is not None else [" "],
        tape=tape,
        trade_id=trade_id,
        symbol=symbol,
    )


# ---------------------------------------------------------------------------
# 1. Temporal Boundary & Guard Tests
# ---------------------------------------------------------------------------

class TestTemporalBoundaryGuards:
    def test_oos_boundary_raises_before_network(self) -> None:
        """Date on or after 2023-01-01 must raise DataContractError."""
        with pytest.raises(DataContractError, match="OOS DATA ACCESS FORBIDDEN"):
            assert_transaction_probe_date(date(2023, 1, 1))

    def test_oos_future_date_raises(self) -> None:
        with pytest.raises(DataContractError, match="OOS DATA ACCESS FORBIDDEN"):
            assert_transaction_probe_date(date(2024, 6, 1))

    def test_pre_is_date_raises(self) -> None:
        with pytest.raises(DataContractError, match="OUT OF REPLICATION BOUNDS"):
            assert_transaction_probe_date(date(2016, 12, 31))

    def test_is_boundary_start_valid(self) -> None:
        assert_transaction_probe_date(date(2017, 1, 1))

    def test_is_boundary_end_valid(self) -> None:
        assert_transaction_probe_date(date(2022, 12, 31))


# ---------------------------------------------------------------------------
# 2. Feed & Symbol Guards
# ---------------------------------------------------------------------------

class TestFeedAndSymbolGuards:
    def test_spy_is_valid_symbol(self) -> None:
        assert_qualified_symbol("SPY")

    def test_non_spy_raises(self) -> None:
        with pytest.raises(DataContractError, match="INVALID SYMBOL"):
            assert_qualified_symbol("QQQ")

    def test_sip_feed_is_valid(self) -> None:
        assert_qualified_feed("sip")

    def test_iex_feed_raises(self) -> None:
        with pytest.raises(DataContractError, match="INVALID FEED"):
            assert_qualified_feed("iex")

    def test_response_symbol_validation(self) -> None:
        assert_response_symbol("SPY")
        with pytest.raises(DataContractError, match="PROVIDER CONTRACT VIOLATION"):
            assert_response_symbol("AAPL")


# ---------------------------------------------------------------------------
# 3. Response Timestamp Bounds
# ---------------------------------------------------------------------------

class TestResponseTimestampBounds:
    def test_valid_timestamp_passes(self) -> None:
        # 2020-06-01 10:00 ET = 14:00 UTC
        assert_response_timestamp_in_bounds("2020-06-01T14:00:00.000000Z", _D)

    def test_wrong_date_timestamp_raises(self) -> None:
        # 2020-06-02 10:00 ET = 14:00 UTC
        with pytest.raises(DataContractError, match="TIMESTAMP CONTAMINATION"):
            assert_response_timestamp_in_bounds("2020-06-02T14:00:00.000000Z", _D)


# ---------------------------------------------------------------------------
# 4. Boundary Endpoint Classification (Price-Authority Contract)
# ---------------------------------------------------------------------------

class TestBoundaryEndpointClassification:
    def test_unique_last_trade_exactly_at_1000(self) -> None:
        """Single last trade exactly at 10:00:00 -> UNIQUE_BOUNDARY_PRICE with exact match."""
        records = [
            _make_trade("2020-06-01T09:30:00", session_date=_D),
            _make_trade("2020-06-01T10:00:00", price="451.00", session_date=_D),
            _make_trade("2020-06-01T10:00:01", session_date=_D),
        ]
        session_records = filter_regular_session_records(records, _D)
        candidate = classify_boundary_endpoint(_D, session_records, BOUNDARY_1000_ET)
        assert candidate.classification == BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE
        assert candidate.selected_price == Decimal("451.00")
        assert candidate.candidate_price == Decimal("451.00")
        assert candidate.exact_boundary_timestamp_match is True
        assert candidate.boundary_tie_record_count == 1
        assert candidate.distinct_boundary_price_count == 1
        assert Decimal(candidate.distance_to_boundary_seconds or "1") == Decimal("0")

    def test_unique_last_trade_strictly_before_1000(self) -> None:
        """Last trade at 09:59:58 (before boundary) -> UNIQUE_BOUNDARY_PRICE with exact match = False."""
        records = [
            _make_trade("2020-06-01T09:45:00", session_date=_D),
            _make_trade("2020-06-01T09:59:58", price="452.00", session_date=_D),
            _make_trade("2020-06-01T10:00:01", session_date=_D),
        ]
        session_records = filter_regular_session_records(records, _D)
        candidate = classify_boundary_endpoint(_D, session_records, BOUNDARY_1000_ET)
        assert candidate.classification == BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE
        assert candidate.selected_price == Decimal("452.00")
        assert candidate.exact_boundary_timestamp_match is False
        assert candidate.boundary_tie_record_count == 1
        assert Decimal(candidate.distance_to_boundary_seconds or "0") == Decimal("2")

    def test_multi_trade_same_price_at_maximal_timestamp(self) -> None:
        """Multiple trades at max timestamp T* with identical price -> UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE."""
        records = [
            _make_trade("2020-06-01T09:59:59.858000", price="241.96", exchange="K", trade_id=27997, session_date=_D),
            _make_trade("2020-06-01T09:59:59.858000", price="241.96", exchange="K", trade_id=27998, session_date=_D),
        ]
        session_records = filter_regular_session_records(records, _D)
        candidate = classify_boundary_endpoint(_D, session_records, BOUNDARY_1000_ET)
        assert candidate.classification == BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE
        assert candidate.selected_price == Decimal("241.96")
        assert candidate.boundary_tie_record_count == 2
        assert candidate.distinct_boundary_price_count == 1
        assert candidate.exchange_set == ["K"]
        assert candidate.exact_boundary_timestamp_match is False

    def test_multi_trade_distinct_prices_is_ambiguous_fail_closed(self) -> None:
        """Multiple trades at T* with different prices -> AMBIGUOUS_BOUNDARY_PRICE (fail-closed).

        Must NOT use max(trade_id), exchange priority, or record order to break the tie.
        """
        records = [
            _make_trade("2020-06-01T10:00:00", price="450.10", exchange="P", trade_id=1001, session_date=_D),
            _make_trade("2020-06-01T10:00:00", price="450.20", exchange="P", trade_id=1002, session_date=_D),
        ]
        session_records = filter_regular_session_records(records, _D)
        candidate = classify_boundary_endpoint(_D, session_records, BOUNDARY_1000_ET)
        assert candidate.classification == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE
        assert candidate.selected_price is None
        assert candidate.boundary_tie_record_count == 2
        assert candidate.distinct_boundary_price_count == 2

    def test_max_trade_id_never_used_to_break_price_ambiguity(self) -> None:
        """Assert that higher trade_id (2000 vs 1000) does NOT select the price."""
        records = [
            _make_trade("2020-06-01T15:30:00", price="300.00", trade_id=1000, session_date=_D),
            _make_trade("2020-06-01T15:30:00", price="300.05", trade_id=2000, session_date=_D),
        ]
        session_records = filter_regular_session_records(records, _D)
        candidate = classify_boundary_endpoint(_D, session_records, BOUNDARY_1530_ET)
        assert candidate.classification == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE
        assert candidate.selected_price is None

    def test_trade_immediately_after_boundary_not_eligible(self) -> None:
        records = [
            _make_trade("2020-06-01T09:59:00", price="449.00", session_date=_D),
            _make_trade("2020-06-01T10:00:01", price="455.00", session_date=_D),
        ]
        session_records = filter_regular_session_records(records, _D)
        candidate = classify_boundary_endpoint(_D, session_records, BOUNDARY_1000_ET)
        assert candidate.selected_price == Decimal("449.00")
        assert candidate.first_after_boundary_ts is not None

    def test_missing_pre_boundary_gives_missing(self) -> None:
        records = [
            _make_trade("2020-06-01T10:00:01", session_date=_D),
        ]
        session_records = filter_regular_session_records(records, _D)
        candidate = classify_boundary_endpoint(_D, session_records, BOUNDARY_1000_ET)
        assert candidate.classification == BoundaryEndpointClassification.MISSING_PRE_BOUNDARY_TRANSACTION
        assert candidate.selected_price is None


# ---------------------------------------------------------------------------
# 5. Transport Duplicate & Trade ID Semantics
# ---------------------------------------------------------------------------

class TestTransportAndTradeIdSemantics:
    def test_clean_transport_gives_zero(self) -> None:
        records = [
            _make_trade("2020-06-01T09:35:00", exchange="P", trade_id=1, session_date=_D),
            _make_trade("2020-06-01T09:36:00", exchange="P", trade_id=2, session_date=_D),
        ]
        assert detect_transport_duplicates(records) == 0

    def test_exact_full_record_duplicate_detected(self) -> None:
        """Exact match on all fields -> transport duplicate."""
        t1 = _make_trade("2020-06-01T09:35:00", price="450.00", size=100, exchange="P", trade_id=1, session_date=_D)
        t2 = _make_trade("2020-06-01T09:35:00", price="450.00", size=100, exchange="P", trade_id=1, session_date=_D)
        assert detect_transport_duplicates([t1, t2]) == 1

    def test_duplicate_trade_ids_across_exchanges_not_transport_duplicates(self) -> None:
        """Same trade_id on different exchanges -> NOT a transport duplicate."""
        t1 = _make_trade("2020-06-01T09:35:00", price="450.00", exchange="P", trade_id=999, session_date=_D)
        t2 = _make_trade("2020-06-01T11:00:00", price="451.00", exchange="Z", trade_id=999, session_date=_D)
        assert detect_transport_duplicates([t1, t2]) == 0
        diag = detect_trade_id_collisions([t1, t2])
        assert diag["global_trade_id_collision_count"] == 1
        assert diag["exchange_scoped_trade_id_collision_count"] == 0

    def test_duplicate_trade_ids_on_same_exchange_not_transport_duplicates_if_fields_differ(self) -> None:
        """Same trade_id and same exchange, but different timestamps/prices -> NOT transport duplicates."""
        t1 = _make_trade("2020-06-01T09:35:00", price="450.00", exchange="D", trade_id=12345, session_date=_D)
        t2 = _make_trade("2020-06-01T15:00:00", price="453.00", exchange="D", trade_id=12345, session_date=_D)
        assert detect_transport_duplicates([t1, t2]) == 0
        diag = detect_trade_id_collisions([t1, t2])
        assert diag["exchange_scoped_trade_id_collision_count"] == 1

    def test_trade_id_ordering_authority_is_not_established(self) -> None:
        assert TRADE_ID_ORDERING_AUTHORITY == "NOT_ESTABLISHED"


# ---------------------------------------------------------------------------
# 6. Trade Count Mapping & Gao Threshold
# ---------------------------------------------------------------------------

class TestDailyTradeCountMapping:
    def test_gao_threshold_is_500_never_10(self) -> None:
        assert GAO_MIN_DAILY_TRADE_COUNT == 500

    def test_condition_i_odd_lot_retained_in_raw_count(self) -> None:
        """Condition 'I' (odd lots) must remain counted in regular session count."""
        records = [
            _make_trade("2020-06-01T09:35:00", conditions=[" ", "I"], session_date=_D),
            _make_trade("2020-06-01T09:36:00", conditions=[" "], session_date=_D),
        ]
        session_records = filter_regular_session_records(records, _D)
        assert len(session_records) == 2
        census = build_condition_census(session_records)
        assert census["I"] == 1

    def test_premarket_and_afterhours_excluded_from_count(self) -> None:
        records = [
            _make_trade("2020-06-01T09:00:00", session_date=_D),   # pre-market
            _make_trade("2020-06-01T10:00:00", session_date=_D),   # regular
            _make_trade("2020-06-01T15:30:00", session_date=_D),   # regular
            _make_trade("2020-06-01T16:30:00", session_date=_D),   # after-hours
        ]
        session_records = filter_regular_session_records(records, _D)
        assert len(session_records) == 2

    def test_exact_session_open_boundary_inclusivity(self) -> None:
        """Trade exactly at 09:30:00.000000 is included; trade at 09:29:59.999999 is excluded."""
        included_open = _make_trade("2020-06-01T09:30:00.000000", session_date=_D)
        # Pre-market trade at 09:29:59.999999 ET = 13:29:59.999999 UTC
        excluded_pre = RawSipTradeRecord(
            timestamp_utc="2020-06-01T13:29:59.999999Z",
            price=Decimal("450.00"),
            size=100,
            exchange="P",
            conditions=[" "],
            tape="B",
            trade_id=1,
            symbol=QUALIFIED_SYMBOL,
        )
        records = [excluded_pre, included_open]
        filtered = filter_regular_session_records(records, _D)
        assert len(filtered) == 1
        assert filtered[0].timestamp_utc == included_open.timestamp_utc

    def test_exact_session_close_boundary_inclusivity(self) -> None:
        """Trade exactly at 16:00:00.000000 is included; trade at 16:00:00.000001 is excluded."""
        # Exact close trade: 16:00:00.000000 ET = 20:00:00.000000 UTC
        included_close = RawSipTradeRecord(
            timestamp_utc="2020-06-01T20:00:00.000000Z",
            price=Decimal("450.00"),
            size=100,
            exchange="P",
            conditions=[" "],
            tape="B",
            trade_id=1,
            symbol=QUALIFIED_SYMBOL,
        )
        # Post-market trade: 16:00:00.000001 ET = 20:00:00.000001 UTC
        excluded_post = RawSipTradeRecord(
            timestamp_utc="2020-06-01T20:00:00.000001Z",
            price=Decimal("450.00"),
            size=100,
            exchange="P",
            conditions=[" "],
            tape="B",
            trade_id=2,
            symbol=QUALIFIED_SYMBOL,
        )
        records = [included_close, excluded_post]
        filtered = filter_regular_session_records(records, _D)
        assert len(filtered) == 1
        assert filtered[0].timestamp_utc == included_close.timestamp_utc


# ---------------------------------------------------------------------------
# 7. qualify_session_transactions Integration
# ---------------------------------------------------------------------------

class TestQualifySessionTransactions:
    def _make_minimal_valid_session(self) -> List[RawSipTradeRecord]:
        return [
            _make_trade("2020-06-01T09:30:00", session_date=_D, trade_id=1),
            _make_trade("2020-06-01T09:45:00", session_date=_D, trade_id=2),
            _make_trade("2020-06-01T10:00:00", price="450.10", session_date=_D, trade_id=3),
            _make_trade("2020-06-01T10:01:00", session_date=_D, trade_id=4),
            _make_trade("2020-06-01T15:29:00", session_date=_D, trade_id=5),
            _make_trade("2020-06-01T15:30:00", price="451.00", session_date=_D, trade_id=6),
            _make_trade("2020-06-01T15:35:00", session_date=_D, trade_id=7),
        ]

    def test_happy_path(self) -> None:
        records = self._make_minimal_valid_session()
        result = qualify_session_transactions(_D, records, page_count=1, pagination_complete=True)
        assert result.pagination_complete is True
        assert result.boundary_1000.classification == BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE
        assert result.boundary_1530.classification == BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE
        assert result.boundary_1000.selected_price == Decimal("450.10")
        assert result.boundary_1530.selected_price == Decimal("451.00")
        assert result.exact_transport_duplicates == 0

    def test_transport_duplicate_raises(self) -> None:
        records = self._make_minimal_valid_session()
        # Duplicate exact trade 3
        records.append(records[2])
        with pytest.raises(DataContractError, match="exact transport duplicate"):
            qualify_session_transactions(_D, records, page_count=1, pagination_complete=True)

    def test_pagination_incomplete_raises(self) -> None:
        records = self._make_minimal_valid_session()
        with pytest.raises(DataContractError, match="Pagination incomplete"):
            qualify_session_transactions(_D, records, page_count=1, pagination_complete=False)

    def test_ambiguous_boundary_price_raises(self) -> None:
        records = self._make_minimal_valid_session()
        # Add a conflicting price at 10:00:00
        records.append(_make_trade("2020-06-01T10:00:00", price="450.99", session_date=_D, trade_id=99))
        with pytest.raises(DataContractError, match="AMBIGUOUS_BOUNDARY_PRICE"):
            qualify_session_transactions(_D, records, page_count=1, pagination_complete=True)

    def test_no_return_field_in_result(self) -> None:
        records = self._make_minimal_valid_session()
        result = qualify_session_transactions(_D, records, page_count=1, pagination_complete=True)
        result_dict = result.to_dict()
        forbidden_keys = {
            "r1", "r13", "return", "log_return", "simple_return",
            "price_diff", "price_difference", "beta", "alpha", "sharpe",
        }
        for key in forbidden_keys:
            assert key not in result_dict


# ---------------------------------------------------------------------------
# 8. synthesize_probe_result
# ---------------------------------------------------------------------------

class TestSynthesizeProbeResult:
    def _make_sq(
        self,
        session_date: date,
        b1000_cls: BoundaryEndpointClassification = BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE,
        b1530_cls: BoundaryEndpointClassification = BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE,
        pagination_complete: bool = True,
        transport_dups: int = 0,
        reg_count: int = 1000,
    ) -> SessionTransactionQualification:
        def _bc(cls: BoundaryEndpointClassification, bnd: str) -> BoundaryCandidate:
            return BoundaryCandidate(
                session_date=session_date.isoformat(),
                boundary_et=bnd,
                classification=cls,
                selected_price=Decimal("450.00") if cls in {
                    BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE,
                    BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE,
                } else None,
                max_timestamp_utc="2020-06-01T14:00:00Z",
                max_timestamp_et="2020-06-01T10:00:00 EDT",
                distance_to_boundary_seconds="0",
                exact_boundary_timestamp_match=True,
                boundary_tie_record_count=1,
                distinct_boundary_price_count=1,
                exchange_set=["P"],
                condition_set=[" "],
                tie_trade_ids=[1],
                first_after_boundary_ts=None,
                notes=[],
            )

        return SessionTransactionQualification(
            session_date=session_date.isoformat(),
            total_raw_records=reg_count,
            regular_session_record_count=reg_count,
            exact_transport_duplicates=transport_dups,
            trade_id_collision_diagnostics={"global_trade_id_collision_count": 0, "exchange_scoped_trade_id_collision_count": 0},
            page_count=1,
            pagination_complete=pagination_complete,
            condition_census={},
            exchange_census={},
            tape_census={},
            boundary_1000=_bc(b1000_cls, "10:00:00"),
            boundary_1530=_bc(b1530_cls, "15:30:00"),
        )

    def test_all_unique_yields_qualified(self) -> None:
        sqs = [self._make_sq(date(2017, 6, 1)), self._make_sq(date(2018, 6, 1))]
        result = synthesize_probe_result([date(2017, 6, 1), date(2018, 6, 1)], sqs)
        assert result.endpoint_mapping_proposed == EndpointMappingProposedClassification.QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY
        assert result.trade_count_mapping_proposed == TradeCountMappingProposedClassification.QUALIFIED_PROVIDER_OPERATIONALIZATION

    def test_multi_trade_same_price_yields_qualified(self) -> None:
        sqs = [
            self._make_sq(
                date(2017, 6, 1),
                b1000_cls=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE,
            ),
            self._make_sq(date(2018, 6, 1)),
        ]
        result = synthesize_probe_result([date(2017, 6, 1), date(2018, 6, 1)], sqs)
        assert result.endpoint_mapping_proposed == EndpointMappingProposedClassification.QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY

    def test_ambiguous_yields_unresolved(self) -> None:
        sqs = [
            self._make_sq(date(2017, 6, 1)),
            self._make_sq(
                date(2018, 6, 1),
                b1000_cls=BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE,
            ),
        ]
        result = synthesize_probe_result([date(2017, 6, 1), date(2018, 6, 1)], sqs)
        assert result.endpoint_mapping_proposed == EndpointMappingProposedClassification.UNRESOLVED_BOUNDARY_PRICE_AMBIGUITY

    def test_sub_500_trade_count_yields_unresolved_count_mapping(self) -> None:
        sqs = [self._make_sq(date(2017, 6, 1), reg_count=499)]
        result = synthesize_probe_result([date(2017, 6, 1)], sqs)
        assert result.trade_count_mapping_proposed == TradeCountMappingProposedClassification.UNRESOLVED
        assert len(result.trade_count_blocker_notes) == 1
