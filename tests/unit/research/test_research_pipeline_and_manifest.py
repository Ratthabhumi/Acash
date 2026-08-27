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

        # Verify Manifest persistence and loading
        loaded_manifest = engine.load_research_manifest(manifest.manifest_id)
        assert loaded_manifest is not None
        assert loaded_manifest.manifest_id == manifest.manifest_id
        assert loaded_manifest.in_sample_beta == manifest.in_sample_beta
