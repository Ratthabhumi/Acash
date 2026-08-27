"""Unit tests for Trade Data Integrity Validator (Phase 3A)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.data.schema import IntegrityViolationError
from acash.data.trades.integrity import TradesIntegrityValidator
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA


def _make_valid_trades_table() -> pa.Table:
    """Helper to build a valid sample trades table."""
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 500, tzinfo=timezone.utc),
        ],
        "feed_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 10, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 510, tzinfo=timezone.utc),
        ],
        "knowledge_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 20, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 520, tzinfo=timezone.utc),
        ],
        "source_seq_num": [100, 101],
        "trade_id": ["TRD_1", "TRD_2"],
        "match_sub_idx": [0, 0],
        "price": [Decimal("5000.250000000000000000"), Decimal("5000.500000000000000000")],
        "size": [Decimal("10.000000000000000000"), Decimal("5.000000000000000000")],
        "aggressor_side": ["BUY", "SELL"],
        "trade_condition": ["REGULAR", "REGULAR"],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)


def test_valid_trades_validation() -> None:
    """Verify that a valid trades table passes validation."""
    validator = TradesIntegrityValidator()
    table = _make_valid_trades_table()
    report, validated = validator.validate_table(table)

    assert report.is_valid
    assert report.status == "VALID"
    assert report.metrics.total_rows == 2
    assert report.metrics.valid_rows == 2
    assert len(report.errors) == 0


def test_invalid_price_and_size_rejected() -> None:
    """Verify non-positive price or size raises IntegrityViolationError."""
    validator = TradesIntegrityValidator()
    base_data = _make_valid_trades_table().to_pydict()

    # Zero price
    data_zero_price = dict(base_data)
    data_zero_price["price"] = [Decimal("0"), Decimal("5000.50")]
    tbl_zero_price = pa.Table.from_pydict(data_zero_price, schema=CANONICAL_TRADES_SCHEMA)
    with pytest.raises(IntegrityViolationError, match="Price must be > 0"):
        validator.validate_table(tbl_zero_price)

    # Negative size
    data_neg_size = dict(base_data)
    data_neg_size["size"] = [Decimal("10"), Decimal("-5")]
    tbl_neg_size = pa.Table.from_pydict(data_neg_size, schema=CANONICAL_TRADES_SCHEMA)
    with pytest.raises(IntegrityViolationError, match="Size must be > 0"):
        validator.validate_table(tbl_neg_size)


def test_invalid_aggressor_side_and_condition_rejected() -> None:
    """Verify invalid aggressor side or condition raises IntegrityViolationError."""
    validator = TradesIntegrityValidator()
    base_data = _make_valid_trades_table().to_pydict()

    data_bad_side = dict(base_data)
    data_bad_side["aggressor_side"] = ["BUY", "INVALID_SIDE"]
    tbl_bad_side = pa.Table.from_pydict(data_bad_side, schema=CANONICAL_TRADES_SCHEMA)
    with pytest.raises(IntegrityViolationError, match="aggressor_side"):
        validator.validate_table(tbl_bad_side)

    data_bad_cond = dict(base_data)
    data_bad_cond["trade_condition"] = ["REGULAR", "INVALID_COND"]
    tbl_bad_cond = pa.Table.from_pydict(data_bad_cond, schema=CANONICAL_TRADES_SCHEMA)
    with pytest.raises(IntegrityViolationError, match="trade_condition"):
        validator.validate_table(tbl_bad_cond)


def test_declared_sequence_reset_accepted() -> None:
    """Verify that a declared sequence reset is accepted as EXPECTED_RESET without error."""
    validator = TradesIntegrityValidator()
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc),
        ],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 10, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 1, 10, tzinfo=timezone.utc),
        ],
        "source_seq_num": [5000, 1],  # Sequence reset from 5000 to 1
        "trade_id": ["TRD_1", "TRD_2"],
        "match_sub_idx": [0, 0],
        "price": [Decimal("5000.25"), Decimal("5000.50")],
        "size": [Decimal("10"), Decimal("5")],
        "aggressor_side": ["BUY", "SELL"],
        "trade_condition": ["REGULAR", "REGULAR"],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)
    declared_resets = {("CME", "310", "ES.FUT", date(2026, 1, 19))}

    report, validated = validator.validate_table(table, declared_resets=declared_resets)
    assert report.is_valid
    assert any(a.anomaly_type == "EXPECTED_RESET" for a in report.anomalies)


def test_sequence_gap_emits_warning() -> None:
    """Verify that an undeclared sequence jump emits PACKET_GAP_DETECTED warning."""
    validator = TradesIntegrityValidator()
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc),
        ],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 10, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 1, 10, tzinfo=timezone.utc),
        ],
        "source_seq_num": [100, 105],  # Jumped from 100 to 105
        "trade_id": ["TRD_1", "TRD_2"],
        "match_sub_idx": [0, 0],
        "price": [Decimal("5000.25"), Decimal("5000.50")],
        "size": [Decimal("10"), Decimal("5")],
        "aggressor_side": ["BUY", "SELL"],
        "trade_condition": ["REGULAR", "REGULAR"],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)
    report, validated = validator.validate_table(table)

    assert report.is_valid
    assert report.status == "VALID_WITH_WARNINGS"
    assert any(a.anomaly_type == "PACKET_GAP_DETECTED" for a in report.anomalies)


def test_multi_trade_message_expansion() -> None:
    """Verify that a single sequence_num containing multiple matches is valid with unique match_sub_idx."""
    validator = TradesIntegrityValidator()
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc),
        ],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 10, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 10, tzinfo=timezone.utc),
        ],
        "source_seq_num": [100, 100],  # Same packet sequence
        "trade_id": ["TRD_1", "TRD_2"],
        "match_sub_idx": [0, 1],       # Distinct sub-indices
        "price": [Decimal("5000.25"), Decimal("5000.25")],
        "size": [Decimal("10"), Decimal("5")],
        "aggressor_side": ["BUY", "BUY"],
        "trade_condition": ["REGULAR", "REGULAR"],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)
    report, validated = validator.validate_table(table)
    assert report.is_valid


def test_different_channel_same_seq_num_no_collision() -> None:
    """Verify that identical source_seq_num occurring on different channel_id do NOT collide."""
    validator = TradesIntegrityValidator()
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "311"],  # Channel 310 (ES) vs Channel 311 (NQ)
        "symbol": ["ES.FUT", "NQ.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc),
        ],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 10, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 10, tzinfo=timezone.utc),
        ],
        "source_seq_num": [100, 100],  # Same sequence number
        "trade_id": [None, None],
        "match_sub_idx": [0, 0],
        "price": [Decimal("5000.25"), Decimal("18000.50")],
        "size": [Decimal("10"), Decimal("5")],
        "aggressor_side": ["BUY", "SELL"],
        "trade_condition": ["REGULAR", "REGULAR"],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)
    report, validated = validator.validate_table(table)
    assert report.is_valid


def test_intra_batch_duplicate_identity_rejected() -> None:
    """Verify that duplicate Trade Row Identity within the same batch raises IntegrityViolationError."""
    validator = TradesIntegrityValidator()
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc),
        ],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 10, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 10, tzinfo=timezone.utc),
        ],
        "source_seq_num": [100, 100],
        "trade_id": ["TRD_1", "TRD_1"],
        "match_sub_idx": [0, 0],       # Duplicate Identity!
        "price": [Decimal("5000.25"), Decimal("5000.25")],
        "size": [Decimal("10"), Decimal("10")],
        "aggressor_side": ["BUY", "BUY"],
        "trade_condition": ["REGULAR", "REGULAR"],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)
    with pytest.raises(IntegrityViolationError, match="BATCH_TRADE_IDENTITY_DUPLICATE"):
        validator.validate_table(table)


def test_global_duplicate_identity_rejected() -> None:
    """Verify that Trade Row Identity matching an already-persisted record is rejected."""
    validator = TradesIntegrityValidator()
    table = _make_valid_trades_table()

    existing_lookup = {
        ("CME", "310", "ES.FUT", date(2026, 1, 19), 100, 0): True,
    }

    with pytest.raises(IntegrityViolationError, match="GLOBAL_TRADE_IDENTITY_DUPLICATE"):
        validator.validate_table(table, existing_trade_identity_lookup=existing_lookup)


def test_clock_skew_warning_emitted() -> None:
    """Verify that clock skew exceeding threshold emits CLOCK_SKEW_WARNING without fatal error."""
    validator = TradesIntegrityValidator(max_clock_skew_ms=1000)
    data = {
        "source_id": ["CME"],
        "channel_id": ["310"],
        "symbol": ["ES.FUT"],
        "trading_date": [date(2026, 1, 19)],
        "exchange_time_utc": [datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc)],
        "feed_time_utc": [None],
        "knowledge_time_utc": [datetime(2026, 1, 19, 14, 30, 10, 0, tzinfo=timezone.utc)],  # 10s skew (> 1s)
        "source_seq_num": [100],
        "trade_id": [None],
        "match_sub_idx": [0],
        "price": [Decimal("5000.25")],
        "size": [Decimal("10")],
        "aggressor_side": ["BUY"],
        "trade_condition": ["REGULAR"],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)
    report, validated = validator.validate_table(table)

    assert report.is_valid
    assert any(a.anomaly_type == "CLOCK_SKEW_WARNING" for a in report.anomalies)
