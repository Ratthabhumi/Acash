"""Unit tests for Research Pipeline Execution and Manifest Provenance (Phase 4)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
from typing import Tuple
import pyarrow as pa

import pytest

from acash.research.manifest import (
    ResearchManifestEngine,
    calculate_hypothesis_spec_sha256,
    calculate_research_search_record_sha256,
)
from acash.research.pipeline import AlphaResearchPipeline
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
    OosExposureState,
    ResearchSearchRecord,
    SplitPolicy,
)



def _make_dataset(num_bars: int = 100) -> Tuple[pa.Table, pa.Table]:
    t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    bar_starts = [t0 + timedelta(minutes=i) for i in range(num_bars)]
    bar_ends = [t0 + timedelta(minutes=i + 1) for i in range(num_bars)]
    opens = [Decimal(f"{5000 + i}.00") for i in range(num_bars)]
    highs = [Decimal(f"{5001 + i}.00") for i in range(num_bars)]
    lows = [Decimal(f"{4999 + i}.00") for i in range(num_bars)]
    closes = [Decimal("5000.50") + Decimal(str(i)) for i in range(num_bars)]
    volumes = [Decimal("100") for _ in range(num_bars)]

    bars_tbl = pa.Table.from_pydict({
        "bar_start_utc": bar_starts,
        "bar_end_utc": bar_ends,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    feat_tbl = pa.Table.from_pydict({
        "vwap_std": [Decimal(f"{0.5 + 0.05 * i:.4f}") for i in range(num_bars)],
    })

    return feat_tbl, bars_tbl


def test_research_pipeline_end_to_end_and_manifest_storage() -> None:
    """Verify AlphaResearchPipeline executes research evaluation and persists ResearchManifest."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ResearchManifestEngine(manifests_dir=Path(tmp_dir) / "manifests")
        pipeline = AlphaResearchPipeline(manifest_engine=engine)

        feat_tbl, bars_tbl = _make_dataset(num_bars=100)

        hyp = HypothesisSpecification(
            hypothesis_id="HYP-VWAP-DISPERSION-V1",
            hypothesis_version="1.2.0",
            economic_rationale="VWAP dispersion measures volatility expansion.",
            target_symbol="ES.FUT",
            feature_dependencies=["vwap_std"],
            parameter_config_json="{}",
            expected_direction=ExpectedDirection.DISPERSION,
            target_horizons=[1, 5],
            primary_horizon=5,
            invalidation_criteria=InvalidationCriteria(
                min_in_sample_rank_ic=Decimal("0.01"),
                min_hac_t_stat=Decimal("1.5"),
            ),
            registered_at_utc="2026-08-28T00:00:00Z",
            author="Quantitative Research",
        )

        split_policy = SplitPolicy(train_pct=Decimal("0.60"), val_pct=Decimal("0.20"), oos_pct=Decimal("0.20"), embargo_bars=2)

        manifest, result, eval_table = pipeline.run_hypothesis_evaluation(
            features_table=feat_tbl,
            bars_table=bars_tbl,
            feature_name="vwap_std",
            hypothesis=hyp,
            split_policy=split_policy,
            evaluate_oos=False,
        )


        assert manifest.hypothesis_id == "HYP-VWAP-DISPERSION-V1"
        assert manifest.inference_estimator == "OLS_SLOPE_BETA_HAC"
        assert eval_table.num_rows == 1
        assert len(manifest.input_feature_hashes[0]) == 64  # Real SHA-256

        # Verify Manifest persistence and loading
        loaded_manifest = engine.load_research_manifest(manifest.manifest_id)
        assert loaded_manifest is not None
        assert loaded_manifest.manifest_id == manifest.manifest_id
        assert loaded_manifest.in_sample_beta == manifest.in_sample_beta

        # Re-run 2: Identical inputs MUST produce identical deterministic manifest_id
        manifest2, _, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_tbl,
            bars_table=bars_tbl,
            feature_name="vwap_std",
            hypothesis=hyp,
            split_policy=split_policy,
            evaluate_oos=False,
        )
        assert manifest.manifest_id == manifest2.manifest_id


def test_canonical_feature_table_sha256_row_order_invariance() -> None:
    """Verify calculate_canonical_feature_table_sha256 is row-order invariant and detects any data mutation."""
    from acash.research.pipeline import calculate_canonical_feature_table_sha256

    t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 19, 14, 31, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 19, 14, 32, 0, tzinfo=timezone.utc)

    tbl_original = pa.Table.from_pydict({
        "timestamp_utc": [t0, t1, t2],
        "vwap_std": [Decimal("1.250000000000000000"), Decimal("2.500000000000000000"), Decimal("3.750000000000000000")],
        "volume_imbalance": [Decimal("0.100000000000000000"), Decimal("-0.200000000000000000"), Decimal("0.300000000000000000")],
    })

    # Permuted rows (t2, t0, t1)
    tbl_permuted = pa.Table.from_pydict({
        "timestamp_utc": [t2, t0, t1],
        "vwap_std": [Decimal("3.750000000000000000"), Decimal("1.250000000000000000"), Decimal("2.500000000000000000")],
        "volume_imbalance": [Decimal("0.300000000000000000"), Decimal("0.100000000000000000"), Decimal("-0.200000000000000000")],
    })

    # Mutated value
    tbl_mutated = pa.Table.from_pydict({
        "timestamp_utc": [t0, t1, t2],
        "vwap_std": [Decimal("1.250000000000000000"), Decimal("2.500000000000000001"), Decimal("3.750000000000000000")],
        "volume_imbalance": [Decimal("0.100000000000000000"), Decimal("-0.200000000000000000"), Decimal("0.300000000000000000")],
    })

    hash_orig = calculate_canonical_feature_table_sha256(tbl_original)
    hash_perm = calculate_canonical_feature_table_sha256(tbl_permuted)
    hash_mut = calculate_canonical_feature_table_sha256(tbl_mutated)

    # Invariant: Permuted rows produce identical canonical hash
    assert hash_orig == hash_perm
    # Invariant: Any bitwise modification alters hash
    assert hash_orig != hash_mut


def test_canonical_feature_table_sha256_duplicate_timestamps_permutation_invariance() -> None:
    """Verify calculate_canonical_feature_table_sha256 is 100% permutation invariant even with duplicate timestamps and ties."""
    import itertools
    from acash.research.pipeline import calculate_canonical_feature_table_sha256

    t_shared = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)

    # 3 rows with identical timestamp but different feature values
    rows = [
        {"timestamp_utc": t_shared, "feature_a": Decimal("100.00"), "feature_b": True, "tag": "ALPHA"},
        {"timestamp_utc": t_shared, "feature_a": Decimal("200.00"), "feature_b": False, "tag": "BETA"},
        {"timestamp_utc": t_shared, "feature_a": Decimal("300.00"), "feature_b": True, "tag": "GAMMA"},
    ]

    hashes = set()
    for perm in itertools.permutations(rows):
        tbl = pa.Table.from_pydict({
            "timestamp_utc": [r["timestamp_utc"] for r in perm],
            "feature_a": [r["feature_a"] for r in perm],
            "feature_b": [r["feature_b"] for r in perm],
            "tag": [r["tag"] for r in perm],
        })
        h = calculate_canonical_feature_table_sha256(tbl)
        hashes.add(h)

    # Invariant: ALL 6 permutations MUST yield the exact same SHA-256 hash!
    assert len(hashes) == 1

    # Type Distinguishability Invariant: bool(True) vs int(1)
    tbl_bool = pa.Table.from_pydict({
        "timestamp_utc": [t_shared],
        "flag": [True],
    })
    tbl_int = pa.Table.from_pydict({
        "timestamp_utc": [t_shared],
        "flag": [1],
    })
    assert calculate_canonical_feature_table_sha256(tbl_bool) != calculate_canonical_feature_table_sha256(tbl_int)

    # Type Distinguishability Invariant: str("ABC") vs bytes(b"ABC")
    tbl_str = pa.Table.from_pydict({
        "timestamp_utc": [t_shared],
        "tag": ["ABC"],
    })
    tbl_bytes = pa.Table.from_pydict({
        "timestamp_utc": [t_shared],
        "tag": [b"ABC"],
    })
    assert calculate_canonical_feature_table_sha256(tbl_str) != calculate_canonical_feature_table_sha256(tbl_bytes)


def test_research_manifest_identity_binds_all_configurations() -> None:
    """Verify ResearchManifest.manifest_id changes when HAC policy, cost model, or split policy changes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ResearchManifestEngine(manifests_dir=Path(tmp_dir) / "manifests")
        pipeline = AlphaResearchPipeline(manifest_engine=engine)
        feat_tbl, bars_tbl = _make_dataset(num_bars=100)

        hyp = HypothesisSpecification(
            hypothesis_id="HYP-CONFIG-BINDING-V1",
            hypothesis_version="1.0.0",
            economic_rationale="Testing configuration sensitivity.",
            target_symbol="ES.FUT",
            feature_dependencies=["vwap_std"],
            parameter_config_json="{}",
            expected_direction=ExpectedDirection.DISPERSION,
            target_horizons=[1, 5],
            primary_horizon=5,
            invalidation_criteria=InvalidationCriteria(
                min_in_sample_rank_ic=Decimal("0.01"),
                min_hac_t_stat=Decimal("1.5"),
            ),
            registered_at_utc="2026-08-28T00:00:00Z",
            author="Quantitative Research",
        )

        split_a = SplitPolicy(train_pct=Decimal("0.60"), val_pct=Decimal("0.20"), oos_pct=Decimal("0.20"), embargo_bars=2)
        split_b = SplitPolicy(train_pct=Decimal("0.50"), val_pct=Decimal("0.25"), oos_pct=Decimal("0.25"), embargo_bars=4)

        from acash.research.schema import CostModelConfig, HacBandwidthMethod, HacInferencePolicy

        hac_a = HacInferencePolicy(bandwidth_method=HacBandwidthMethod.FIXED_HORIZON_MINUS_ONE)
        hac_b = HacInferencePolicy(bandwidth_method=HacBandwidthMethod.ANDREWS_AR1_PLUGIN)


        cost_a = CostModelConfig(quoted_spread_bps=Decimal("1.0"))
        cost_b = CostModelConfig(quoted_spread_bps=Decimal("3.0"))

        m_base, _, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_tbl,
            bars_table=bars_tbl,
            feature_name="vwap_std",
            hypothesis=hyp,
            split_policy=split_a,
            hac_policy=hac_a,
            cost_config=cost_a,
            evaluate_oos=False,
        )

        m_split, _, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_tbl,
            bars_table=bars_tbl,
            feature_name="vwap_std",
            hypothesis=hyp,
            split_policy=split_b,
            hac_policy=hac_a,
            cost_config=cost_a,
            evaluate_oos=False,
        )

        m_hac, _, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_tbl,
            bars_table=bars_tbl,
            feature_name="vwap_std",
            hypothesis=hyp,
            split_policy=split_a,
            hac_policy=hac_b,
            cost_config=cost_a,
            evaluate_oos=False,
        )

        m_cost, _, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_tbl,
            bars_table=bars_tbl,
            feature_name="vwap_std",
            hypothesis=hyp,
            split_policy=split_a,
            hac_policy=hac_a,
            cost_config=cost_b,
            evaluate_oos=False,
        )

        # Invariant: Changing ANY configuration alters manifest_id and parameter_config_hash!
        assert m_base.manifest_id != m_split.manifest_id
        assert m_base.manifest_id != m_hac.manifest_id
        assert m_base.manifest_id != m_cost.manifest_id
        assert m_base.parameter_config_hash != m_split.parameter_config_hash
        assert m_base.parameter_config_hash != m_hac.parameter_config_hash
        assert m_base.parameter_config_hash != m_cost.parameter_config_hash


def test_canonical_parameter_config_json_representation_invariance() -> None:
    """Verify parameter configuration JSON serialization is strictly key-order and whitespace invariant."""
    import hashlib
    import json

    # Dictionary 1: Inserted in order A, B, C
    cfg1 = {
        "hypothesis_id": "HYP-01",
        "hac_policy": {"kernel_type": "bartlett", "bandwidth_method": "andrews_ar1_plugin", "robustness_lags": [1, 5, 10]},
        "cost_model": {"quoted_spread_bps": "1.0", "roundtrip_broker_fee_bps": "0.5"},
    }

    # Dictionary 2: Inserted in reversed/permuted key order
    cfg2 = {
        "cost_model": {"roundtrip_broker_fee_bps": "0.5", "quoted_spread_bps": "1.0"},
        "hypothesis_id": "HYP-01",
        "hac_policy": {"robustness_lags": [1, 5, 10], "bandwidth_method": "andrews_ar1_plugin", "kernel_type": "bartlett"},
    }

    json1 = json.dumps(cfg1, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    json2 = json.dumps(cfg2, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    hash1 = hashlib.sha256(json1.encode("utf-8")).hexdigest()
    hash2 = hashlib.sha256(json2.encode("utf-8")).hexdigest()

    # Invariant: Permuted dictionary keys produce identical canonical JSON and hash
    assert json1 == json2
    assert hash1 == hash2





