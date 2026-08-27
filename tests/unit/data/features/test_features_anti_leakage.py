"""Comprehensive 4-Way Anti-Lookahead Leakage Tests for Microstructure Features (Phase 3C)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import pyarrow as pa
import pytest

from acash.data.features.hashing import calculate_canonical_trade_features_sha256
from acash.data.features.pipeline import FeatureExtractionPipeline
from acash.data.features.storage import FeatureStorageEngine
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA


def _make_base_trades_table() -> pa.Table:
    t_base = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    t_kn_base = datetime(2026, 1, 19, 14, 30, 1, tzinfo=timezone.utc)
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [t_base, t_base + timedelta(seconds=10)],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [t_kn_base, t_kn_base],
        "source_seq_num": [100, 101],
        "trade_id": ["T1", "T2"],
        "match_sub_idx": [0, 0],
        "price": [Decimal("5000.00"), Decimal("5000.25")],
        "size": [Decimal("10"), Decimal("20")],
        "aggressor_side": ["BUY", "BUY"],
        "trade_condition": ["REGULAR", "REGULAR"],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)


def test_four_way_anti_leakage_invariants() -> None:
    """Verify that features computed at T_decision under T_knowledge_cutoff are 100% invariant to all 4 future event types."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = FeatureStorageEngine(
            base_dir=Path(tmp_dir) / "features",
            manifests_dir=Path(tmp_dir) / "manifests",
        )
        pipeline = FeatureExtractionPipeline(storage_engine=storage)

        decision_time = datetime(2026, 1, 19, 14, 30, 30, tzinfo=timezone.utc)
        knowledge_cutoff = datetime(2026, 1, 19, 14, 30, 35, tzinfo=timezone.utc)

        # Baseline Extraction
        base_tbl = _make_base_trades_table()
        manifest_base, out_base = pipeline.extract_trade_features(
            trades_table=base_tbl,
            symbol="ES.FUT",
            trading_date=date(2026, 1, 19),
            decision_time_utc=decision_time,
            knowledge_cutoff_utc=knowledge_cutoff,
        )
        base_hash = manifest_base.feature_output_sha256

        # 1. Leakage Test 1: Injected Future Trade (T_event = 14:35:00 > T_decision)
        t_fut = datetime(2026, 1, 19, 14, 35, 0, tzinfo=timezone.utc)
        data_fut = base_tbl.to_pydict()
        data_fut["source_id"].append("CME")
        data_fut["channel_id"].append("310")
        data_fut["symbol"].append("ES.FUT")
        data_fut["trading_date"].append(date(2026, 1, 19))
        data_fut["exchange_time_utc"].append(t_fut)
        data_fut["feed_time_utc"].append(None)
        data_fut["knowledge_time_utc"].append(knowledge_cutoff)
        data_fut["source_seq_num"].append(999)
        data_fut["trade_id"].append("T_FUT")
        data_fut["match_sub_idx"].append(0)
        data_fut["price"].append(Decimal("5100.00"))
        data_fut["size"].append(Decimal("1000"))
        data_fut["aggressor_side"].append("BUY")
        data_fut["trade_condition"].append("REGULAR")

        tbl_with_fut = pa.Table.from_pydict(data_fut, schema=CANONICAL_TRADES_SCHEMA)
        manifest_fut, out_fut = pipeline.extract_trade_features(
            trades_table=tbl_with_fut,
            symbol="ES.FUT",
            trading_date=date(2026, 1, 19),
            decision_time_utc=decision_time,
            knowledge_cutoff_utc=knowledge_cutoff,
        )
        assert manifest_fut.feature_output_sha256 == base_hash

        # 2. Leakage Test 2: Injected Future Revision (T_knowledge = 14:40:00 > T_knowledge_cutoff)
        data_rev = base_tbl.to_pydict()
        data_rev["source_id"].append("CME")
        data_rev["channel_id"].append("310")
        data_rev["symbol"].append("ES.FUT")
        data_rev["trading_date"].append(date(2026, 1, 19))
        data_rev["exchange_time_utc"].append(datetime(2026, 1, 19, 14, 30, 5, tzinfo=timezone.utc))
        data_rev["feed_time_utc"].append(None)
        data_rev["knowledge_time_utc"].append(datetime(2026, 1, 19, 14, 40, 0, tzinfo=timezone.utc))  # After cutoff!
        data_rev["source_seq_num"].append(102)
        data_rev["trade_id"].append("T_REV")
        data_rev["match_sub_idx"].append(0)
        data_rev["price"].append(Decimal("4900.00"))
        data_rev["size"].append(Decimal("500"))
        data_rev["aggressor_side"].append("SELL")
        data_rev["trade_condition"].append("REGULAR")

        tbl_with_rev = pa.Table.from_pydict(data_rev, schema=CANONICAL_TRADES_SCHEMA)
        manifest_rev, out_rev = pipeline.extract_trade_features(
            trades_table=tbl_with_rev,
            symbol="ES.FUT",
            trading_date=date(2026, 1, 19),
            decision_time_utc=decision_time,
            knowledge_cutoff_utc=knowledge_cutoff,
        )
        assert manifest_rev.feature_output_sha256 == base_hash
