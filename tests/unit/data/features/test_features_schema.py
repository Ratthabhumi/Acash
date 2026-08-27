"""Unit tests for Canonical Feature Schemas, Models, and Manifests (Phase 3C)."""

from datetime import date, datetime, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.data.features.schema import (
    CANONICAL_BOOK_FEATURES_SCHEMA,
    CANONICAL_TRADE_FEATURES_SCHEMA,
    BookFeaturesConfig,
    FeatureManifest,
    TradeFeaturesConfig,
)


def test_canonical_trade_features_schema_types() -> None:
    """Verify PyArrow types and nullabilities in CANONICAL_TRADE_FEATURES_SCHEMA."""
    field_map = {f.name: f for f in CANONICAL_TRADE_FEATURES_SCHEMA}

    assert field_map["symbol"].type == pa.string()
    assert not field_map["symbol"].nullable

    assert field_map["trading_date"].type == pa.date32()
    assert not field_map["trading_date"].nullable

    assert field_map["bar_start_utc"].type == pa.timestamp("ns", tz="UTC")
    assert not field_map["bar_start_utc"].nullable

    assert field_map["bar_end_utc"].type == pa.timestamp("ns", tz="UTC")
    assert not field_map["bar_end_utc"].nullable

    assert field_map["open"].type == pa.decimal128(38, 18)
    assert not field_map["open"].nullable

    assert field_map["volume"].type == pa.decimal128(38, 18)
    assert not field_map["volume"].nullable

    assert field_map["delta"].type == pa.decimal128(38, 18)
    assert not field_map["delta"].nullable

    assert field_map["cvd"].type == pa.decimal128(38, 18)
    assert not field_map["cvd"].nullable

    # VWAP and Value Area fields are nullable when total volume == 0
    assert field_map["vwap"].type == pa.decimal128(38, 18)
    assert field_map["vwap"].nullable

    assert field_map["vwap_std"].type == pa.decimal128(38, 18)
    assert field_map["vwap_std"].nullable

    assert field_map["poc_price"].type == pa.decimal128(38, 18)
    assert field_map["poc_price"].nullable

    assert field_map["vah_price"].type == pa.decimal128(38, 18)
    assert field_map["vah_price"].nullable

    assert field_map["val_price"].type == pa.decimal128(38, 18)
    assert field_map["val_price"].nullable

    assert field_map["has_stacked_buy_imbalance"].type == pa.bool_()
    assert not field_map["has_stacked_buy_imbalance"].nullable

    assert field_map["is_absorption_bar"].type == pa.bool_()
    assert not field_map["is_absorption_bar"].nullable


def test_canonical_book_features_schema_types() -> None:
    """Verify PyArrow types and nullabilities in CANONICAL_BOOK_FEATURES_SCHEMA."""
    field_map = {f.name: f for f in CANONICAL_BOOK_FEATURES_SCHEMA}

    assert field_map["symbol"].type == pa.string()
    assert not field_map["symbol"].nullable

    assert field_map["trading_date"].type == pa.date32()
    assert not field_map["trading_date"].nullable

    assert field_map["exchange_time_utc"].type == pa.timestamp("ns", tz="UTC")
    assert not field_map["exchange_time_utc"].nullable

    assert field_map["spread"].type == pa.decimal128(38, 18)
    assert not field_map["spread"].nullable

    assert field_map["micro_price"].type == pa.decimal128(38, 18)
    assert field_map["micro_price"].nullable  # Nullable when total depth == 0

    assert field_map["obi_top1"].type == pa.decimal128(38, 18)
    assert not field_map["obi_top1"].nullable

    assert field_map["obi_top5"].type == pa.decimal128(38, 18)
    assert not field_map["obi_top5"].nullable

    assert field_map["total_bid_depth"].type == pa.decimal128(38, 18)
    assert not field_map["total_bid_depth"].nullable

    assert field_map["is_crossed"].type == pa.bool_()
    assert not field_map["is_crossed"].nullable


def test_feature_manifest_lineage_and_configs() -> None:
    """Verify FeatureManifest requires temporal coordinates and parameters serialize canonically."""
    trade_cfg = TradeFeaturesConfig(
        value_area_pct=Decimal("0.70"),
        imbalance_ratio=Decimal("3.0"),
        min_imbalance_volume_diff=Decimal("10.0"),
        stacked_imbalance_min_levels=3,
        absorption_volume_multiplier=Decimal("2.5"),
    )
    json_str = trade_cfg.to_canonical_json()
    assert '"imbalance_ratio": "3.0000"' in json_str
    assert '"value_area_pct": "0.7000"' in json_str

    manifest = FeatureManifest(
        manifest_id="manifest_001",
        feature_set_name="trade_microstructure_v1",
        feature_definition_version="1.1.0",
        symbol="ES.FUT",
        trading_date="2026-01-19",
        decision_time_utc="2026-01-19T14:30:00.000000Z",
        knowledge_cutoff_utc="2026-01-19T14:30:01.000000Z",
        input_event_start_utc="2026-01-19T14:00:00.000000Z",
        input_event_end_utc="2026-01-19T14:30:00.000000Z",
        input_trades_sha256="abc123trades",
        input_book_sha256=None,
        parameter_config_sha256="def456param",
        parameter_config_json=json_str,
        software_version="0.3.0",
        feature_output_sha256="789output",
        row_count=30,
        computed_at_utc="2026-01-19T14:30:05.000000Z",
    )
    assert manifest.feature_definition_version == "1.1.0"
    assert manifest.decision_time_utc.startswith("2026-01-19")
