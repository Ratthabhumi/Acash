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


