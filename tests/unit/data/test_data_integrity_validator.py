"""Deterministic unit tests for DataIntegrityValidator."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List
import pyarrow as pa
import pytest

from acash.data.integrity import (
    DataIntegrityValidator,
    SessionProfile,
    ValidationErrorRecord,
)
from acash.data.schema import CANONICAL_ARROW_SCHEMA, MAX_DECIMAL128_38_18


def make_test_table(rows: List[Dict[str, Any]]) -> pa.Table:
    """Helper to construct a PyArrow table from a list of dicts."""
    pydict: Dict[str, list[Any]] = {
        "source_id": [r.get("source_id", "binance") for r in rows],
        "symbol": [r.get("symbol", "BTC/USDT") for r in rows],
        "timeframe": [r.get("timeframe", "M1") for r in rows],
        "event_start_utc": [r["event_start_utc"] for r in rows],
        "event_end_utc": [r["event_end_utc"] for r in rows],
        "knowledge_time_utc": [r.get("knowledge_time_utc", r["event_end_utc"]) for r in rows],
        "revision_seq": [r.get("revision_seq", 1) for r in rows],
        "open": [r.get("open", Decimal("100.0")) for r in rows],
        "high": [r.get("high", Decimal("105.0")) for r in rows],
        "low": [r.get("low", Decimal("95.0")) for r in rows],
        "close": [r.get("close", Decimal("102.0")) for r in rows],
        "volume": [r.get("volume", Decimal("10.0")) for r in rows],
        "quote_volume": [r.get("quote_volume", Decimal("1010.0")) for r in rows],
        "trade_count": [r.get("trade_count", 50) for r in rows],
    }
    return pa.Table.from_pydict(pydict, schema=CANONICAL_ARROW_SCHEMA)


class TestDataIntegrityValidator:
    """Comprehensive test suite for data validation rules."""

    @pytest.fixture
    def validator(self) -> DataIntegrityValidator:
        return DataIntegrityValidator(session_profile=SessionProfile.CRYPTO_24_7)

    def test_positive_prices_rejected_if_zero_or_negative(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        # Zero price
        table_zero = make_test_table([{
            "event_start_utc": t0, "event_end_utc": t1,
            "open": Decimal("0.0"), "high": Decimal("105.0"), "low": Decimal("0.0"), "close": Decimal("100.0")
        }])
        report, _ = validator.validate_table(table_zero)
        assert not report.is_valid
        assert any(e.rule == "POSITIVE_PRICE" for e in report.errors)

        # Negative price
        table_neg = make_test_table([{
            "event_start_utc": t0, "event_end_utc": t1,
            "open": Decimal("-10.0"), "high": Decimal("105.0"), "low": Decimal("-15.0"), "close": Decimal("100.0")
        }])
        report, _ = validator.validate_table(table_neg)
        assert not report.is_valid
        assert any(e.rule == "POSITIVE_PRICE" for e in report.errors)

    def test_negative_volume_rejected(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        table = make_test_table([{
            "event_start_utc": t0, "event_end_utc": t1,
            "volume": Decimal("-1.0")
        }])
        report, _ = validator.validate_table(table)
        assert not report.is_valid
        assert any(e.rule == "NON_NEGATIVE_VOLUME" for e in report.errors)

    def test_ohlc_geometry_violations_rejected(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        # High < Open
        t_high = make_test_table([{
            "event_start_utc": t0, "event_end_utc": t1,
            "open": Decimal("100.0"), "high": Decimal("99.0"), "low": Decimal("90.0"), "close": Decimal("95.0")
        }])
        report, _ = validator.validate_table(t_high)
        assert not report.is_valid
        assert any(e.rule == "OHLC_GEOMETRY_HIGH" for e in report.errors)

        # Low > Close
        t_low = make_test_table([{
            "event_start_utc": t0, "event_end_utc": t1,
            "open": Decimal("100.0"), "high": Decimal("110.0"), "low": Decimal("98.0"), "close": Decimal("95.0")
        }])
        report, _ = validator.validate_table(t_low)
        assert not report.is_valid
        assert any(e.rule == "OHLC_GEOMETRY_LOW" for e in report.errors)

    def test_intra_bar_and_knowledge_invariants(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        # Intra-bar: start >= end
        t_intra = make_test_table([{
            "event_start_utc": t1, "event_end_utc": t0, "knowledge_time_utc": t1
        }])
        report, _ = validator.validate_table(t_intra)
        assert not report.is_valid
        assert any(e.rule == "INTRA_BAR_INTERVAL" for e in report.errors)

        # Lookahead: knowledge < end
        t_lookahead = make_test_table([{
            "event_start_utc": t0, "event_end_utc": t1,
            "knowledge_time_utc": datetime(2026, 1, 1, 10, 0, 30, tzinfo=timezone.utc)
        }])
        report, _ = validator.validate_table(t_lookahead)
        assert not report.is_valid
        assert any(e.rule == "KNOWLEDGE_INVARIANT" for e in report.errors)

    def test_event_end_consistency_across_revisions(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)
        t_know1 = datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc)
        t_know2 = datetime(2026, 1, 1, 10, 10, tzinfo=timezone.utc)

        # Valid: Same event (10:00) + same event_end (10:01) + multiple revisions
        t_valid = make_test_table([
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know1, "revision_seq": 1, "close": Decimal("100.0")},
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know2, "revision_seq": 2, "close": Decimal("101.0")},
        ])
        report, out_tbl = validator.validate_table(t_valid)
        assert report.is_valid
        assert out_tbl.num_rows == 2

        # Invalid: Same event (10:00) + differing event_end (10:01 vs 10:02)
        t_invalid = make_test_table([
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know1, "revision_seq": 1, "close": Decimal("100.0")},
            {"event_start_utc": t0, "event_end_utc": t2, "knowledge_time_utc": t_know2, "revision_seq": 2, "close": Decimal("101.0")},
        ])
        report, _ = validator.validate_table(t_invalid)
        assert not report.is_valid
        assert any(e.rule == "EVENT_END_CONSISTENCY" for e in report.errors)

    def test_distinct_event_monotonicity(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t_overlap = datetime(2026, 1, 1, 10, 0, 30, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)

        # Distinct event overlap
        table = make_test_table([
            {"event_start_utc": t0, "event_end_utc": t1},
            {"event_start_utc": t_overlap, "event_end_utc": t2},
        ])
        report, _ = validator.validate_table(table)
        assert not report.is_valid
        assert any(e.rule == "DISTINCT_EVENT_MONOTONICITY" for e in report.errors)

    def test_append_only_revision_seq_assignment_and_tie_breaker(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t_know = datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc)

        # Same event + same knowledge + differing content -> deterministic tie breaker via fingerprint
        table = make_test_table([
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know, "close": Decimal("105.0"), "revision_seq": None},
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know, "close": Decimal("102.0"), "revision_seq": None},
        ])
        report, out_tbl = validator.validate_table(table)
        assert report.is_valid
        assert out_tbl.num_rows == 2
        seqs = out_tbl["revision_seq"].to_pylist()
        assert seqs == [1, 2]

        # Same event + same knowledge + identical content -> duplicate rejection
        table_dup = make_test_table([
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know, "close": Decimal("100.0"), "revision_seq": None},
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know, "close": Decimal("100.0"), "revision_seq": None},
        ])
        report_dup, _ = validator.validate_table(table_dup)
        assert not report_dup.is_valid
        assert any(e.rule == "DUPLICATE_REVISION_CONTENT" for e in report_dup.errors)

    def test_source_provided_revision_sequence_uniqueness(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t_know1 = datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc)
        t_know2 = datetime(2026, 1, 1, 10, 10, tzinfo=timezone.utc)

        # Duplicate revision_seq for same event
        table = make_test_table([
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know1, "revision_seq": 1},
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know2, "revision_seq": 1},
        ])
        report, _ = validator.validate_table(table)
        assert not report.is_valid
        assert any(e.rule == "DUPLICATE_REVISION_SEQ" for e in report.errors)

    def test_global_revision_identity_collision(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t_know = datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc)

        existing_lookup = {
            ("binance", "BTC/USDT", "M1", t0, t_know, 1): True
        }

        table = make_test_table([
            {"source_id": "binance", "symbol": "BTC/USDT", "timeframe": "M1",
             "event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t_know, "revision_seq": 1}
        ])
        report, _ = validator.validate_table(table, existing_revisions_lookup=existing_lookup)
        assert not report.is_valid
        assert any(e.rule == "GLOBAL_REVISION_IDENTITY_DUPLICATE" for e in report.errors)

    def test_anomaly_preservation_flags_warnings_without_invalidating(self, validator: DataIntegrityValidator) -> None:
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)

        # 50% price spike from 100 to 150
        table = make_test_table([
            {"event_start_utc": t0, "event_end_utc": t1, "open": Decimal("100.0"), "high": Decimal("105.0"), "low": Decimal("95.0"), "close": Decimal("100.0")},
            {"event_start_utc": t1, "event_end_utc": t2, "open": Decimal("145.0"), "high": Decimal("155.0"), "low": Decimal("140.0"), "close": Decimal("150.0")},
        ])
        report, out_tbl = validator.validate_table(table)
        assert report.is_valid
        assert report.warning_count > 0
        assert any(w.rule == "PRICE_RETURN_SPIKE" for w in report.warnings)
        assert out_tbl.num_rows == 2
