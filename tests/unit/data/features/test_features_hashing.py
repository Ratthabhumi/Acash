"""Unit tests for Feature Hashing, Binary Serialization, and Reproducibility (Phase 3C)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import io
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from acash.data.features.hashing import (
    calculate_canonical_book_features_sha256,
    calculate_canonical_trade_features_sha256,
    calculate_parameter_config_sha256,
)
from acash.data.features.schema import (
    CANONICAL_BOOK_FEATURES_SCHEMA,
    CANONICAL_TRADE_FEATURES_SCHEMA,
    TradeFeaturesConfig,
)


def _make_sample_trade_features_table() -> pa.Table:
    t1 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 19, 14, 31, 0, tzinfo=timezone.utc)
    data = {
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "bar_start_utc": [t1, t2],
        "bar_end_utc": [t1 + timedelta(seconds=60), t2 + timedelta(seconds=60)],
        "open": [Decimal("5000.00"), Decimal("5001.00")],
        "high": [Decimal("5002.00"), Decimal("5003.00")],
        "low": [Decimal("4999.00"), Decimal("5000.00")],
        "close": [Decimal("5001.00"), Decimal("5002.50")],
        "volume": [Decimal("100"), Decimal("150")],
        "buy_volume": [Decimal("60"), Decimal("90")],
        "sell_volume": [Decimal("40"), Decimal("60")],
        "delta": [Decimal("20"), Decimal("30")],
        "cvd": [Decimal("20"), Decimal("50")],
        "vwap": [Decimal("5000.50"), Decimal("5001.25")],
        "vwap_std": [Decimal("0.75"), Decimal("0.85")],
        "poc_price": [Decimal("5000.25"), Decimal("5001.50")],
        "vah_price": [Decimal("5001.00"), Decimal("5002.25")],
        "val_price": [Decimal("4999.50"), Decimal("5000.75")],
        "has_stacked_buy_imbalance": [True, False],
        "has_stacked_sell_imbalance": [False, False],
        "is_absorption_bar": [False, True],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_TRADE_FEATURES_SCHEMA)


def _make_sample_book_features_table() -> pa.Table:
    t1 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 19, 14, 30, 1, tzinfo=timezone.utc)
    data = {
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [t1, t2],
        "knowledge_time_utc": [t1, t2],
        "spread": [Decimal("0.25"), Decimal("0.50")],
        "micro_price": [Decimal("5000.35"), Decimal("5000.40")],
        "obi_top1": [Decimal("0.20"), Decimal("-0.10")],
        "obi_top5": [Decimal("0.15"), Decimal("-0.05")],
        "obi_top10": [Decimal("0.10"), Decimal("0.00")],
        "total_bid_depth": [Decimal("100"), Decimal("120")],
        "total_ask_depth": [Decimal("80"), Decimal("130")],
        "is_crossed": [False, False],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_BOOK_FEATURES_SCHEMA)


def test_trade_features_hash_permutation_and_codec_invariance() -> None:
    """Verify permuting trade feature rows and changing compression codecs yields identical logical SHA-256."""
    table = _make_sample_trade_features_table()
    hash_orig = calculate_canonical_trade_features_sha256(table)

    permuted = table.take([1, 0])
    assert calculate_canonical_trade_features_sha256(permuted) == hash_orig

    # Parquet zstd vs snappy codec invariance
    buf_zstd = io.BytesIO()
    pq.write_table(table, buf_zstd, compression="zstd")
    buf_zstd.seek(0)
    assert calculate_canonical_trade_features_sha256(pq.read_table(buf_zstd)) == hash_orig


def test_book_features_hash_permutation_and_codec_invariance() -> None:
    """Verify permuting book feature rows yields identical logical SHA-256."""
    table = _make_sample_book_features_table()
    hash_orig = calculate_canonical_book_features_sha256(table)

    permuted = table.take([1, 0])
    assert calculate_canonical_book_features_sha256(permuted) == hash_orig


def test_parameter_config_hash_sensitivity() -> None:
    """Verify modifying any feature parameter alters the cryptographic hash."""
    cfg1 = TradeFeaturesConfig(imbalance_ratio=Decimal("3.0"))
    cfg2 = TradeFeaturesConfig(imbalance_ratio=Decimal("3.5"))
    assert calculate_parameter_config_sha256(cfg1) != calculate_parameter_config_sha256(cfg2)
