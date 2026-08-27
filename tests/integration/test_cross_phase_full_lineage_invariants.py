"""Cross-Phase End-to-End Invariant and Lineage Test Suite (Phases 1–5).

Enforces:
1. Identity Conservation: Same inputs, parameters, and seed guarantee identical cryptographic manifest identities.
2. Direction Conservation & Falsification: LONG/SHORT hypotheses enforce mathematical sign alignment.
3. Dispersion Target Consistency ($Y_t = |R_{t,H}|$): Dispersion hypothesis consistently evaluates absolute return magnitude.
4. Negative Dispersion Falsification: Features predicting compression/low volatility are falsified.
5. Microstructure Absorption Rejection: Verifies price non-continuation requirement for absorption classification.
6. Stream Scope 4-Tuple Isolation & String channel_id: Verifies (source, channel, symbol, date) partition splitting with string channels.
7. Negative Channel Rejection: Null/empty channel_id raises DataContractError.
8. Multi-Unit Explicit batch_id Rejection: Explicit batch_id on multi-unit tables raises DataContractError before write.
9. Deterministic Fallback Ordering & STATE_UNORDERABLE: Verifies content key permutation invariance and duplicate rejection.
10. 64-Hex Digest Enforcement: Verifies strict SHA-256 validation on all manifest fields.
11. Nautilus Substrate Separation: Verifies NautilusCatalogExporter and SubstrateRuntimeUnavailableError on missing runtime.
12. ACASH Sovereign Native Substrate & Shadow Accounting: Verifies independent shadow ledger equity reconciliation.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pyarrow as pa
import pytest

from acash.backtest.accounting import ShadowAccountingLedger
from acash.backtest.adapter import (
    BacktestEventType,
    BacktestMarketEvent,
    CanonicalDataAdapter,
)
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.nautilus_bridge import (
    ACASHNativeBacktestEngine,
    NautilusCatalogExporter,
    NautilusTraderSubstrate,
    SubstrateRuntimeUnavailableError,
    TradeIdMappingPolicy,
)

from acash.backtest.schema import (
    BacktestEngineConfig,
    BacktestManifest,
    OrderType,
    calculate_backtest_manifest_id,
    load_current_environment_provenance,
)
from acash.data.features.engine import calculate_footprint_analytics
from acash.data.features.schema import TradeFeaturesConfig
from acash.data.integrity import DataIntegrityValidator
from acash.data.orderbook.pipeline import OrderBookIngestionPipeline
from acash.data.orderbook.schema import CANONICAL_BOOK_SNAPSHOT_SCHEMA
from acash.data.orderbook.storage import OrderBookStorageEngine
from acash.data.schema import CANONICAL_ARROW_SCHEMA, DataContractError, IntegrityViolationError
from acash.data.trades.pipeline import TradesIngestionPipeline
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA
from acash.data.trades.storage import TradesStorageEngine
from acash.research.evaluation import (
    compute_ols_beta_and_hac,
    determine_hac_bandwidth,
    evaluate_hypothesis_relationship,
)
from acash.research.manifest import ResearchManifestEngine
from acash.research.pipeline import (
    AlphaResearchPipeline,
    calculate_canonical_feature_table_sha256,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    HacBandwidthMethod,
    HacInferencePolicy,
    HypothesisSpecification,
    InvalidationCriteria,
    SignalTransformConfig,
    SignalTransformMethod,
    SplitPolicy,
)
from acash.research.strategies import MicrostructureImbalanceStrategy


def test_cross_phase_identity_conservation() -> None:
    """Invariant 1: Same Data + Same Hypothesis + Same Config + Same Seed = Same Manifest Identity."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ResearchManifestEngine(manifests_dir=Path(tmp_dir) / "manifests")
        pipeline = AlphaResearchPipeline(manifest_engine=engine)

        num_bars = 60
        t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
        timestamps = [datetime.fromtimestamp(t0.timestamp() + i * 60, tz=timezone.utc) for i in range(num_bars)]
        feat_vals = [Decimal(f"{10.0 + (i * 0.1):.4f}") for i in range(num_bars)]
        prices = [Decimal(f"{100.0 + (i * 0.5):.4f}") for i in range(num_bars)]
        t_end_timestamps = [datetime.fromtimestamp(t0.timestamp() + (i + 1) * 60, tz=timezone.utc) for i in range(num_bars)]

        feat_table = pa.Table.from_pydict({
            "timestamp_utc": timestamps,
            "vwap_std": feat_vals,
        })
        bars_table = pa.Table.from_pydict({
            "timestamp_utc": timestamps,
            "bar_start_utc": timestamps,
            "bar_end_utc": t_end_timestamps,
            "open": prices,
            "high": [p + Decimal("1.0") for p in prices],
            "low": [p - Decimal("1.0") for p in prices],
            "close": prices,
            "volume": [Decimal("1000") for _ in prices],
        })

        hyp = HypothesisSpecification(
            hypothesis_id="HYP-CROSS-PHASE-01",
            hypothesis_version="1.0.0",
            economic_rationale="Cross-phase identity test.",
            target_symbol="ES.FUT",
            feature_dependencies=["vwap_std"],
            parameter_config_json='{"z_window": 20}',
            expected_direction=ExpectedDirection.LONG,
            target_horizons=[1, 5],
            primary_horizon=5,
            invalidation_criteria=InvalidationCriteria(
                min_in_sample_rank_ic=Decimal("0.01"),
                min_hac_t_stat=Decimal("1.5"),
            ),
            registered_at_utc="2026-08-28T00:00:00Z",
            author="Quant Lineage Lead",
        )

        # Run 1
        m1, r1, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_table,
            bars_table=bars_table,
            feature_name="vwap_std",
            hypothesis=hyp,
        )

        # Run 2 with identical inputs
        m2, r2, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_table,
            bars_table=bars_table,
            feature_name="vwap_std",
            hypothesis=hyp,
        )

        # Invariant: Bitwise-identical manifest_id and parameter_config_hash
        assert m1.manifest_id == m2.manifest_id
        assert m1.parameter_config_hash == m2.parameter_config_hash
        assert m1.input_feature_hashes == m2.input_feature_hashes


def test_cross_phase_direction_conservation_and_falsification() -> None:
    """Invariant 2: LONG hypothesis with negative beta is explicitly falsified, and SHORT passes."""
    x = [Decimal(str(10 + (i % 5))) for i in range(1, 51)]
    # Perfectly negative relationship: y = -2 * x
    y_neg = [Decimal(str(-2 * (10 + (i % 5)))) for i in range(1, 51)]

    hyp_long = HypothesisSpecification(
        hypothesis_id="HYP-DIR-LONG",
        hypothesis_version="1.0.0",
        economic_rationale="Expecting positive returns.",
        target_symbol="ES.FUT",
        feature_dependencies=["feat_x"],
        parameter_config_json="{}",
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.10"),
            min_hac_t_stat=Decimal("2.0"),
            max_feature_autocorrelation=Decimal("0.80"),
        ),
        registered_at_utc="2026-08-28T00:00:00Z",
        author="Quant",
    )

    hyp_short = HypothesisSpecification(
        hypothesis_id="HYP-DIR-SHORT",
        hypothesis_version="1.0.0",
        economic_rationale="Expecting negative returns.",
        target_symbol="ES.FUT",
        feature_dependencies=["feat_x"],
        parameter_config_json="{}",
        expected_direction=ExpectedDirection.SHORT,
        target_horizons=[1],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.10"),
            min_hac_t_stat=Decimal("2.0"),
            max_feature_autocorrelation=Decimal("0.80"),
        ),
        registered_at_utc="2026-08-28T00:00:00Z",
        author="Quant",
    )

    res_long = evaluate_hypothesis_relationship(
        features=x,
        forward_returns=y_neg,
        horizon=1,
        hypothesis=hyp_long,
    )

    res_short = evaluate_hypothesis_relationship(
        features=x,
        forward_returns=y_neg,
        horizon=1,
        hypothesis=hyp_short,
    )

    # Invariant: LONG is FALSIFIED because relationship is negative
    assert res_long.is_falsified is True
    # Invariant: SHORT is NOT FALSIFIED because negative relationship matches SHORT expectation
    assert res_short.is_falsified is False


def test_cross_phase_dispersion_target_consistency_and_negative_falsification() -> None:
    """Invariant 3 & 4: DISPERSION targets |R_{t,H}|; passes on positive correlation, falsifies on negative."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ResearchManifestEngine(manifests_dir=Path(tmp_dir) / "manifests")
        pipeline = AlphaResearchPipeline(manifest_engine=engine)

        num_bars = 60
        t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
        timestamps = [datetime.fromtimestamp(t0.timestamp() + i * 60, tz=timezone.utc) for i in range(num_bars)]
        t_end_timestamps = [datetime.fromtimestamp(t0.timestamp() + (i + 1) * 60, tz=timezone.utc) for i in range(num_bars)]

        # Feature values with low autocorrelation: High volatility on even steps (10.0), low on odd steps (1.0)
        feat_vals = [Decimal("10.0") if (i % 4 in (0, 1)) else Decimal("1.0") for i in range(num_bars)]
        opens = [Decimal(f"{100.0 + (i * 0.5):.4f}") for i in range(num_bars)]
        closes: List[Decimal] = []
        for i in range(num_bars):
            # For bar i, price movement is large if feature at i-1 was high
            feat_prev = feat_vals[i - 1] if i > 0 else Decimal("10.0")
            delta = Decimal("5.00") if feat_prev == Decimal("10.0") else Decimal("0.05")
            closes.append(opens[i] + (delta if (i % 2 == 0) else -delta))

        feat_table = pa.Table.from_pydict({
            "timestamp_utc": timestamps,
            "vol_indicator": feat_vals,
        })
        bars_table = pa.Table.from_pydict({
            "timestamp_utc": timestamps,
            "bar_start_utc": timestamps,
            "bar_end_utc": t_end_timestamps,
            "open": opens,
            "high": [max(o, c) + Decimal("1.0") for o, c in zip(opens, closes)],
            "low": [min(o, c) - Decimal("1.0") for o, c in zip(opens, closes)],
            "close": closes,
            "volume": [Decimal("1000") for _ in opens],
        })



        hyp_disp = HypothesisSpecification(
            hypothesis_id="HYP-DISP-01",
            hypothesis_version="1.0.0",
            economic_rationale="High indicator predicts high return dispersion / magnitude.",
            target_symbol="ES.FUT",
            feature_dependencies=["vol_indicator"],
            parameter_config_json="{}",
            expected_direction=ExpectedDirection.DISPERSION,
            target_horizons=[1],
            primary_horizon=1,
            invalidation_criteria=InvalidationCriteria(
                min_in_sample_rank_ic=Decimal("0.05"),
                min_hac_t_stat=Decimal("1.5"),
                max_feature_autocorrelation=Decimal("0.80"),
            ),
            registered_at_utc="2026-08-28T00:00:00Z",
            author="Quant",
        )

        manifest, eval_res, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_table,
            bars_table=bars_table,
            feature_name="vol_indicator",
            hypothesis=hyp_disp,
        )

        # Invariants:
        # 1. Manifest records ABS_DISCRETE_FORWARD_RETURN_V1
        assert manifest.forward_return_definition == "ABS_DISCRETE_FORWARD_RETURN_V1"
        # 2. Positive dispersion predictive relationship
        assert eval_res.beta > Decimal("0")
        assert eval_res.is_falsified is False

        # Negative Test: Feature negatively correlated with dispersion (predicts low volatility)
        neg_feat_vals = [Decimal("1.0") if (i % 4 in (0, 1)) else Decimal("10.0") for i in range(num_bars)]
        neg_feat_table = pa.Table.from_pydict({
            "timestamp_utc": timestamps,
            "vol_indicator": neg_feat_vals,
        })
        manifest_neg, eval_neg, _ = pipeline.run_hypothesis_evaluation(
            features_table=neg_feat_table,
            bars_table=bars_table,
            feature_name="vol_indicator",
            hypothesis=hyp_disp,
        )
        # Falsified because beta <= 0
        assert eval_neg.beta <= Decimal("0")
        assert eval_neg.is_falsified is True



def test_cross_phase_microstructure_absorption_rejection_threshold() -> None:
    """Invariant 5: Extreme volume with pullback IS absorption; extreme volume without pullback IS NOT absorption."""
    cfg = TradeFeaturesConfig(
        absorption_volume_multiplier=Decimal("2.0"),
        absorption_rejection_ratio=Decimal("0.30"),
    )

    # Case A: High-side Absorption (Buyers absorbed by passive asks -> Close pulls back from High)
    trades_absorbed = [
        {"price": Decimal("100.00"), "size": Decimal("10.0"), "aggressor_side": "BUY"},
        {"price": Decimal("105.00"), "size": Decimal("10.0"), "aggressor_side": "BUY"},
        {"price": Decimal("110.00"), "size": Decimal("200.0"), "aggressor_side": "BUY"},  # Extreme volume at high
        {"price": Decimal("104.00"), "size": Decimal("10.0"), "aggressor_side": "SELL"},  # Close pulled back to 104
    ]
    res_absorbed = calculate_footprint_analytics(trades_absorbed, cfg)
    assert res_absorbed["is_absorption_bar"] is True

    # Case B: Breakout Continuation (Extreme volume at high, but Close closes right at High -> NOT absorption)
    trades_breakout = [
        {"price": Decimal("100.00"), "size": Decimal("10.0"), "aggressor_side": "BUY"},
        {"price": Decimal("105.00"), "size": Decimal("10.0"), "aggressor_side": "BUY"},
        {"price": Decimal("110.00"), "size": Decimal("200.0"), "aggressor_side": "BUY"},  # Extreme volume at high
        {"price": Decimal("110.00"), "size": Decimal("10.0"), "aggressor_side": "BUY"},  # Close remains at High 110
    ]
    res_breakout = calculate_footprint_analytics(trades_breakout, cfg)
    assert res_breakout["is_absorption_bar"] is False


def test_cross_phase_order_book_stream_scope_and_string_channels() -> None:
    """Invariant 6: OrderBookIngestionPipeline splits multi-channel table with string channel IDs."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = OrderBookStorageEngine(base_dir=Path(tmp_dir) / "orderbook")
        pipeline = OrderBookIngestionPipeline(storage_engine=storage)

        t_date = date(2026, 1, 19)
        t_utc = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)

        # Multi-channel table: Channel "CME_A" and Channel "CME_B" (arbitrary string names)
        table = pa.Table.from_pydict({
            "source_id": ["CME", "CME"],
            "channel_id": ["CME_A", "CME_B"],
            "symbol": ["ES.FUT", "ES.FUT"],
            "trading_date": [t_date, t_date],
            "exchange_time_utc": pa.array([t_utc, t_utc], type=pa.timestamp("ns", tz="UTC")),
            "feed_time_utc": pa.array([None, None], type=pa.timestamp("ns", tz="UTC")),
            "knowledge_time_utc": pa.array([t_utc, t_utc], type=pa.timestamp("ns", tz="UTC")),
            "source_seq_num": [100, 200],
            "source_order_key": ["00000000000000000100", "00000000000000000200"],
            "snapshot_id": ["snap_1", "snap_2"],
            "is_snapshot_complete": [True, True],
            "side": ["BID", "BID"],
            "level_idx": [0, 0],
            "price": [Decimal("5000.00"), Decimal("5000.00")],
            "size": [Decimal("10.0"), Decimal("20.0")],
            "order_count": [1, 1],
        }, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)

        result = pipeline.ingest_snapshots(
            raw_table=table,
            source_id="CME",
            source_uri="cme://test",
        )

        assert result.is_success is True
        assert len(result.batches_ingested) == 2
        batch_ids = [b.batch_id for b in result.batches_ingested]
        assert any("_chCME_A_" in b_id for b_id in batch_ids)
        assert any("_chCME_B_" in b_id for b_id in batch_ids)


def test_cross_phase_negative_channel_id_and_multi_unit_batch_rejection() -> None:
    """Invariant 7 & 8: Reject null/empty channel_id and reject explicit batch_id on multi-unit payloads."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = OrderBookStorageEngine(base_dir=Path(tmp_dir) / "orderbook")
        pipeline = OrderBookIngestionPipeline(storage_engine=storage)

        t_date = date(2026, 1, 19)
        t_utc = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)

        # 1. Null / Empty channel_id rejection
        table_empty_ch = pa.Table.from_pydict({
            "source_id": ["CME"],
            "channel_id": [""],
            "symbol": ["ES.FUT"],
            "trading_date": [t_date],
            "exchange_time_utc": pa.array([t_utc], type=pa.timestamp("ns", tz="UTC")),
            "feed_time_utc": pa.array([None], type=pa.timestamp("ns", tz="UTC")),
            "knowledge_time_utc": pa.array([t_utc], type=pa.timestamp("ns", tz="UTC")),
            "source_seq_num": [100],
            "source_order_key": ["00000000000000000100"],
            "snapshot_id": ["snap_1"],
            "is_snapshot_complete": [True],
            "side": ["BID"],
            "level_idx": [0],
            "price": [Decimal("5000.00")],
            "size": [Decimal("10.0")],
            "order_count": [1],
        }, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)

        with pytest.raises(DataContractError, match="channel_id cannot be null or empty string"):
            pipeline.ingest_snapshots(raw_table=table_empty_ch, source_id="CME", source_uri="cme://test")

        # 2. Multi-Unit Explicit batch_id rejection in OrderBook Pipeline
        table_multi = pa.Table.from_pydict({
            "source_id": ["CME", "CME"],
            "channel_id": ["CH1", "CH2"],
            "symbol": ["ES.FUT", "ES.FUT"],
            "trading_date": [t_date, t_date],
            "exchange_time_utc": pa.array([t_utc, t_utc], type=pa.timestamp("ns", tz="UTC")),
            "feed_time_utc": pa.array([None, None], type=pa.timestamp("ns", tz="UTC")),
            "knowledge_time_utc": pa.array([t_utc, t_utc], type=pa.timestamp("ns", tz="UTC")),
            "source_seq_num": [100, 200],
            "source_order_key": ["00000000000000000100", "00000000000000000200"],
            "snapshot_id": ["snap_1", "snap_2"],
            "is_snapshot_complete": [True, True],
            "side": ["BID", "BID"],
            "level_idx": [0, 0],
            "price": [Decimal("5000.00"), Decimal("5000.00")],
            "size": [Decimal("10.0"), Decimal("20.0")],
            "order_count": [1, 1],
        }, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)

        with pytest.raises(DataContractError, match="Explicit batch_id 'EXPLICIT_BATCH' cannot be applied to a multi-unit payload"):
            pipeline.ingest_snapshots(
                raw_table=table_multi,
                source_id="CME",
                source_uri="cme://test",
                batch_id="EXPLICIT_BATCH",
            )

        # 3. Multi-Unit Explicit batch_id rejection in Trades Pipeline
        trades_storage = TradesStorageEngine(base_dir=Path(tmp_dir) / "trades")
        trades_pipeline = TradesIngestionPipeline(storage_engine=trades_storage)

        trades_multi = pa.Table.from_pydict({
            "source_id": ["CME", "CME"],
            "channel_id": ["CH1", "CH1"],
            "symbol": ["ES.FUT", "NQ.FUT"],  # Multi-symbol payload
            "trading_date": [t_date, t_date],
            "exchange_time_utc": pa.array([t_utc, t_utc], type=pa.timestamp("ns", tz="UTC")),
            "feed_time_utc": pa.array([None, None], type=pa.timestamp("ns", tz="UTC")),
            "knowledge_time_utc": pa.array([t_utc, t_utc], type=pa.timestamp("us", tz="UTC")),
            "source_seq_num": [1, 2],
            "source_order_key": ["00000000000000000001", "00000000000000000002"],
            "trade_id": ["T1", "T2"],
            "match_sub_idx": [0, 0],
            "price": [Decimal("5000.00"), Decimal("18000.00")],
            "size": [Decimal("10.0"), Decimal("20.0")],
            "aggressor_side": ["BUY", "SELL"],
            "trade_condition": ["REGULAR", "REGULAR"],
        }, schema=CANONICAL_TRADES_SCHEMA)


        with pytest.raises(DataContractError, match="Explicit batch_id 'EXPLICIT_TRADES' cannot be applied to a multi-unit payload"):
            trades_pipeline.ingest(
                raw_table=trades_multi,
                source_id="CME",
                source_uri="cme://test",
                batch_id="EXPLICIT_TRADES",
            )


def test_cross_phase_fallback_ordering_key_and_state_unorderable() -> None:
    """Invariant 9: Stable fallback keys under row permutation, and STATE_UNORDERABLE on identical duplicates."""
    t_utc = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)

    # Row 1 and Row 2 with distinct trade_id
    tbl_a = pa.Table.from_pydict({
        "timestamp_utc": [t_utc, t_utc],
        "trade_id": ["T1", "T2"],
        "price": [Decimal("100.00"), Decimal("101.00")],
        "size": [Decimal("10.0"), Decimal("20.0")],
        "aggressor_side": ["BUY", "SELL"],
    })

    # Permuted rows (T2 then T1)
    tbl_b = pa.Table.from_pydict({
        "timestamp_utc": [t_utc, t_utc],
        "trade_id": ["T2", "T1"],
        "price": [Decimal("101.00"), Decimal("100.00")],
        "size": [Decimal("20.0"), Decimal("10.0")],
        "aggressor_side": ["SELL", "BUY"],
    })

    events_a = CanonicalDataAdapter.from_trades_table(tbl_a, symbol="ES")
    events_b = CanonicalDataAdapter.from_trades_table(tbl_b, symbol="ES")

    # Sorted event streams must have identical order tuples
    sorted_a = sorted(events_a, key=lambda e: e.order_tuple)
    sorted_b = sorted(events_b, key=lambda e: e.order_tuple)
    assert [e.order_tuple for e in sorted_a] == [e.order_tuple for e in sorted_b]

    # Duplicate identical rows without unique discriminator must raise STATE_UNORDERABLE
    tbl_dup = pa.Table.from_pydict({
        "timestamp_utc": [t_utc, t_utc],
        "price": [Decimal("100.00"), Decimal("100.00")],
        "size": [Decimal("10.0"), Decimal("10.0")],
        "aggressor_side": ["BUY", "BUY"],
    })
    with pytest.raises(DataContractError, match="STATE_UNORDERABLE"):
        CanonicalDataAdapter.from_trades_table(tbl_dup, symbol="ES")


def test_cross_phase_manifest_64hex_regex_validation() -> None:
    """Invariant 10: BacktestManifest strictly enforces 64-hex lowercase hashes and rejects invalid digests."""
    from acash.backtest.schema import BacktestExecutionSummary, RealityGapSummary

    summary = BacktestExecutionSummary(
        total_orders=1,
        total_fills=1,
        total_volume_traded=Decimal("10.0"),
        total_fees_paid=Decimal("0.5"),
        realized_pnl=Decimal("100.0"),
        unrealized_pnl=Decimal("0.0"),
        ending_equity=Decimal("100100.0"),
        net_return_pct=Decimal("0.10"),
        max_drawdown_pct=Decimal("0.0"),
        win_rate_pct=Decimal("100.0"),
    )
    reality = RealityGapSummary(
        phase4_analytical_edge_bps=Decimal("5.0"),
        phase5_simulated_realized_bps=Decimal("4.5"),
        reality_gap_bps=Decimal("0.5"),
        spread_drag_bps=Decimal("0.3"),
        latency_slip_drag_bps=Decimal("0.2"),
        queue_position_drag_bps=Decimal("0.0"),
    )

    valid_sha = "0" * 64
    valid_git = "a" * 40

    # Valid manifest passes
    m = BacktestManifest(
        manifest_id="res_HYP-01_1h_abcdef1234567890",
        hypothesis_id="HYP-01",
        hypothesis_spec_sha256=valid_sha,
        canonical_data_hashes=[valid_sha],
        engine_config_hash=valid_sha,
        strategy_config_hash=valid_sha,
        prng_seed=42,
        pyproject_toml_sha256=valid_sha,
        git_commit_hash=valid_git,
        execution_summary=summary,
        reality_gap=reality,
        computed_at_utc="2026-08-28T00:00:00Z",
        wall_clock_duration_ms=10,
    )
    assert m is not None

    # Invalid non-hex / short SHA-256 raises DataContractError
    with pytest.raises(DataContractError, match="Invalid hypothesis_spec_sha256"):
        BacktestManifest(
            manifest_id="res_HYP-01_1h_abcdef1234567890",
            hypothesis_id="HYP-01",
            hypothesis_spec_sha256="not_a_valid_64_hex_sha256",
            canonical_data_hashes=[valid_sha],
            engine_config_hash=valid_sha,
            strategy_config_hash=valid_sha,
            prng_seed=42,
            pyproject_toml_sha256=valid_sha,
            git_commit_hash=valid_git,
            execution_summary=summary,
            reality_gap=reality,
            computed_at_utc="2026-08-28T00:00:00Z",
            wall_clock_duration_ms=10,
        )


def test_cross_phase_nautilus_substrate_separation_and_catalog_export() -> None:
    """Invariant 11: NautilusCatalogExporter writes valid catalog with exact nanoseconds, tests TradeIdMappingPolicy, and NautilusTraderSubstrate raises SubstrateRuntimeUnavailableError."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        exporter = NautilusCatalogExporter(
            catalog_root=Path(tmp_dir) / "catalog",
            trade_id_policy=TradeIdMappingPolicy.USE_CANONICAL_SOURCE_ORDER_KEY,
        )

        t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
        bars_table = pa.Table.from_pydict({
            "timestamp_utc": [t0],
            "bar_start_utc": [t0],
            "open": [Decimal("5000.25")],
            "high": [Decimal("5005.50")],
            "low": [Decimal("4995.00")],
            "close": [Decimal("5002.75")],
            "volume": [Decimal("100.5")],
        })

        # 1. Test Bars catalog export
        exported_bars_path = exporter.export_bars_table(bars_table, symbol="ES")
        assert exported_bars_path.exists()
        assert "ES.SIM" in str(exported_bars_path)

        # Verify exported Parquet has exact integer nanoseconds and exact values
        import pyarrow.parquet as pq_read
        bars_read = pq_read.read_table(exported_bars_path)
        assert bars_read["ts_event"][0].as_py() == 1768833000000000000
        assert bars_read["close"][0].as_py() == Decimal("5002.75")

        # 2. Test Trades export with USE_CANONICAL_SOURCE_ORDER_KEY fallback
        trades_table_null_tid = pa.Table.from_pydict({
            "exchange_time_utc": pa.array([t0], type=pa.timestamp("ns", tz="UTC")),
            "source_order_key": ["00000000000000000100"],
            "trade_id": pa.array([None], type=pa.string()),
            "price": [Decimal("5000.25")],
            "size": [Decimal("10.0")],
            "aggressor_side": ["BUY"],
        })
        exported_trades_path = exporter.export_trades_table(trades_table_null_tid, symbol="ES")
        assert exported_trades_path.exists()
        trades_read = pq_read.read_table(exported_trades_path)
        assert trades_read["trade_id"][0].as_py() == "ORDKEY_00000000000000000100"
        assert trades_read["ts_event"][0].as_py() == 1768833000000000000

        # 3. Test Trades export with REJECT_ON_NULL policy
        exporter_reject = NautilusCatalogExporter(
            catalog_root=Path(tmp_dir) / "catalog_reject",
            trade_id_policy=TradeIdMappingPolicy.REJECT_ON_NULL,
        )
        with pytest.raises(DataContractError, match="Null trade_id cannot be exported"):
            exporter_reject.export_trades_table(trades_table_null_tid, symbol="ES")

        # 4. Test Substrate Runtime Unavailable Error on uninstalled package
        substrate = NautilusTraderSubstrate()
        with pytest.raises(SubstrateRuntimeUnavailableError, match="NautilusTrader runtime package"):
            substrate.run_simulation(
                catalog_path=exported_bars_path,
                hypothesis_spec_sha256="0" * 64,
                strategy_config_hash="0" * 64,
                pyproject_toml_sha256="0" * 64,
                git_commit_hash="a" * 40,
            )



class CrossPhaseActor:
    """Actor placing simulated orders into sovereign ACASH backtest runner on market events."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.order_placed = False

    def on_bar(self, event: Any, runner: Any) -> None:
        if not self.order_placed:
            runner.submit_order(
                order_id="ORD-CROSS-001",
                symbol=self.symbol,
                order_type=OrderType.MARKET,
                side="BUY",
                quantity=Decimal("2.0"),
            )
            self.order_placed = True

    def on_trade(self, event: Any, runner: Any) -> None:
        pass


def test_cross_phase_sovereign_native_substrate_and_shadow_accounting() -> None:
    """Invariant 12: ACASHNativeBacktestEngine executes simulation and verifies shadow ledger cash conservation."""
    actor = CrossPhaseActor(symbol="ES.FUT")
    config = BacktestEngineConfig(engine_id="BKT-TEST-CROSS", symbol="ES.FUT", initial_cash=Decimal("100000.00"))
    runner = ACASHNativeBacktestEngine(config=config, strategy_actor=actor)

    t0_ns = 1768833000_000_000_000  # 2026-01-19T14:30:00Z

    # L2 Depth Snapshot event (Asks = 5001.00)
    snap_event = BacktestMarketEvent(
        event_type=BacktestEventType.DEPTH_SNAPSHOT,
        symbol="ES.FUT",
        event_timestamp_ns=t0_ns,
        source_order_key="ES.FUT:DEPTH:0:snap1",
        message_rank=0,
        stream_id="DEPTH",
        row_sub_index=0,
        payload={
            "bids": [(Decimal("5000.00"), Decimal("10.0")), (Decimal("4999.00"), Decimal("20.0"))],
            "asks": [(Decimal("5001.00"), Decimal("10.0")), (Decimal("5002.00"), Decimal("20.0"))],
        },
    )

    # Bar Event triggering actor on_bar
    bar_event = BacktestMarketEvent(
        event_type=BacktestEventType.BAR,
        symbol="ES.FUT",
        event_timestamp_ns=t0_ns + 60_000_000_000,
        source_order_key="ES.FUT:BARS:1",
        message_rank=10,
        stream_id="BARS",
        row_sub_index=0,
        payload={
            "open": Decimal("5001.00"),
            "high": Decimal("5005.00"),
            "low": Decimal("5000.00"),
            "close": Decimal("5004.00"),
            "volume": Decimal("500.0"),
            "bar_index": 0,
        },
    )

    events = [snap_event, bar_event]
    valid_sha = "0" * 64
    valid_git = "a" * 40

    manifest, fills_tbl, equity_tbl = runner.run_backtest(
        events=events,
        hypothesis_spec_sha256=valid_sha,
        strategy_config_hash=valid_sha,
        pyproject_toml_sha256=valid_sha,
        git_commit_hash=valid_git,
        canonical_data_hashes=[valid_sha],
    )

    # Invariants:
    # 1. Total fills executed
    assert manifest.execution_summary.total_fills == 1
    # 2. ACASH Shadow Ledger internal double-entry conservation verified
    runner.ledger.verify_internal_conservation()
    # 3. Position recorded accurately in shadow ledger
    pos = runner.ledger.positions.get("ES.FUT")
    assert pos is not None
    assert pos.quantity == Decimal("2.0")


def test_cross_phase_empty_table_schema_validation() -> None:
    """Invariant 13: DataIntegrityValidator validates schema for empty tables."""
    validator = DataIntegrityValidator()

    # Empty table with invalid schema (missing required columns)
    empty_invalid = pa.Table.from_pydict({"wrong_column": pa.array([], type=pa.string())})
    report, _ = validator.validate_table(empty_invalid)
    assert report.is_valid is False
    assert any(err.rule == "EMPTY_TABLE_SCHEMA_MISMATCH" for err in report.errors)

    # Empty table with correct canonical schema
    empty_valid = CANONICAL_ARROW_SCHEMA.empty_table()
    report_valid, _ = validator.validate_table(empty_valid)
    assert report_valid.is_valid is True
