"""Unit tests for Feature Storage Engine and Pipeline Reproducibility Replay (Phase 3C)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import pyarrow as pa
import pytest

from acash.data.features.pipeline import FeatureExtractionPipeline
from acash.data.features.storage import FeatureStorageEngine
from acash.data.orderbook.reconstruction import DepthLadderState, PriceLevel
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA


def _make_trades_batch() -> pa.Table:
    t = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [t, t + timedelta(seconds=15)],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [t + timedelta(seconds=1), t + timedelta(seconds=16)],
        "source_seq_num": [100, 101],
        "trade_id": ["T1", "T2"],
        "match_sub_idx": [0, 0],
        "price": [Decimal("5000.00"), Decimal("5000.50")],
        "size": [Decimal("10"), Decimal("20")],
        "aggressor_side": ["BUY", "SELL"],
        "trade_condition": ["REGULAR", "REGULAR"],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)


def test_feature_storage_and_duckdb_query() -> None:
    """Verify FeatureStorageEngine partitions feature files and enables DuckDB PIT queries."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = FeatureStorageEngine(
            base_dir=Path(tmp_dir) / "features",
            manifests_dir=Path(tmp_dir) / "manifests",
        )
        pipeline = FeatureExtractionPipeline(storage_engine=storage)

        trades_tbl = _make_trades_batch()
        decision_time = datetime(2026, 1, 19, 14, 31, 0, tzinfo=timezone.utc)
        knowledge_cutoff = datetime(2026, 1, 19, 14, 31, 1, tzinfo=timezone.utc)

        # 1. Extract Trade Features
        manifest, features_tbl = pipeline.extract_trade_features(
            trades_table=trades_tbl,
            symbol="ES.FUT",
            trading_date=date(2026, 1, 19),
            decision_time_utc=decision_time,
            knowledge_cutoff_utc=knowledge_cutoff,
        )

        assert manifest.row_count == 1
        loaded_manifest = storage.load_feature_manifest("trade_microstructure_v1", manifest.manifest_id)
        assert loaded_manifest is not None
        assert loaded_manifest.feature_output_sha256 == manifest.feature_output_sha256

        # 2. Query via DuckDB
        queried = storage.query_features(
            symbol="ES.FUT",
            feature_set="trade_microstructure_v1",
            start_time_utc=datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc),
            end_time_utc=datetime(2026, 1, 19, 14, 31, 0, tzinfo=timezone.utc),
        )
        assert queried.num_rows == 1
        assert queried["symbol"][0].as_py() == "ES.FUT"


def test_book_features_extraction_and_reproducibility() -> None:
    """Verify FeatureExtractionPipeline extracts book microstructure features deterministically."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = FeatureStorageEngine(
            base_dir=Path(tmp_dir) / "features",
            manifests_dir=Path(tmp_dir) / "manifests",
        )
        pipeline = FeatureExtractionPipeline(storage_engine=storage)

        ladder = DepthLadderState(
            stream_scope=("CME", "310", "ES.FUT", "2026-01-19"),
            exchange_time_utc=datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc),
            source_order_key="001",
            bids=[PriceLevel(price=Decimal("5000.00"), size=Decimal("50"))],
            asks=[PriceLevel(price=Decimal("5000.25"), size=Decimal("30"))],
        )

        decision_time = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
        knowledge_cutoff = datetime(2026, 1, 19, 14, 30, 1, tzinfo=timezone.utc)

        manifest1, tbl1 = pipeline.extract_book_features(
            ladder_states=[ladder],
            symbol="ES.FUT",
            trading_date=date(2026, 1, 19),
            decision_time_utc=decision_time,
            knowledge_cutoff_utc=knowledge_cutoff,
        )

        manifest2, tbl2 = pipeline.extract_book_features(
            ladder_states=[ladder],
            symbol="ES.FUT",
            trading_date=date(2026, 1, 19),
            decision_time_utc=decision_time,
            knowledge_cutoff_utc=knowledge_cutoff,
        )

        # Output hashes must be 100% identical
        assert manifest1.feature_output_sha256 == manifest2.feature_output_sha256
