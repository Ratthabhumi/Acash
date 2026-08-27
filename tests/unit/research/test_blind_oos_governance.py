"""Unit tests for Blind Out-of-Sample (OOS) Governance and State Machine (Phase 4)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
from typing import Tuple
import pyarrow as pa

import pytest

from acash.data.schema import DataContractError
from acash.research.manifest import ResearchManifestEngine
from acash.research.pipeline import AlphaResearchPipeline
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
    OosExposureState,
    ResearchSearchRecord,
    SplitPolicy,
)



def _make_sample_dataset(num_bars: int = 100) -> Tuple[pa.Table, pa.Table]:

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
        "obi_top5": [Decimal(f"{0.01 * i:.4f}") for i in range(num_bars)],
    })

    return feat_tbl, bars_tbl


def test_blind_oos_state_machine_and_retuning_lock() -> None:
    """Verify OOS data transitions from UNEXPOSED to EVALUATED_LOCKED, and retuning is prohibited."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ResearchManifestEngine(manifests_dir=Path(tmp_dir) / "manifests")
        pipeline = AlphaResearchPipeline(manifest_engine=engine)

        feat_tbl, bars_tbl = _make_sample_dataset(num_bars=100)


        hyp = HypothesisSpecification(
            hypothesis_id="HYP-OOS-LOCK-TEST",
            hypothesis_version="1.2.0",
            economic_rationale="OOS Governance Verification.",
            target_symbol="ES.FUT",
            feature_dependencies=["obi_top5"],
            parameter_config_json="{}",
            expected_direction=ExpectedDirection.LONG,
            target_horizons=[1, 2],
            primary_horizon=2,
            invalidation_criteria=InvalidationCriteria(
                min_in_sample_rank_ic=Decimal("0.01"),
                min_hac_t_stat=Decimal("1.5"),
            ),
            registered_at_utc="2026-08-28T00:00:00Z",
            author="Quantitative Research",
        )

        search_record = ResearchSearchRecord(
            experiment_id="EXP-001",
            hypothesis_id=hyp.hypothesis_id,
            parameter_variants_count=1,
            feature_variants_tried=["obi_top5"],
            label_variants_tried=["H_2"],
            model_variants_tried=["OLS_BETA_HAC"],
            dataset_window_variants_tried=["ES.FUT"],
            selection_procedure="max_in_sample_rank_ic",
            selected_candidate_id=hyp.hypothesis_id,
            total_effective_trials=1,
            oos_exposure_state=OosExposureState.UNEXPOSED,
        )

        split_policy = SplitPolicy(train_pct=Decimal("0.60"), val_pct=Decimal("0.20"), oos_pct=Decimal("0.20"), embargo_bars=2)

        # 1. In-Sample Only Evaluation -> oos_exposure_state remains UNEXPOSED
        manifest1, res1, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_tbl,
            bars_table=bars_tbl,
            feature_name="obi_top5",
            hypothesis=hyp,
            split_policy=split_policy,
            search_record=search_record,
            evaluate_oos=False,
        )
        assert manifest1.oos_exposure_state == OosExposureState.UNEXPOSED

        # 2. Gate Evaluation with OOS -> state transitions to EVALUATED_LOCKED
        manifest2, res2, _ = pipeline.run_hypothesis_evaluation(
            features_table=feat_tbl,
            bars_table=bars_tbl,
            feature_name="obi_top5",
            hypothesis=hyp,
            split_policy=split_policy,
            search_record=search_record,
            evaluate_oos=True,
        )
        assert manifest2.oos_exposure_state == OosExposureState.EVALUATED_LOCKED

        # 3. Attempting to re-evaluate already locked OOS -> Must raise DataContractError
        search_record_locked = search_record.model_copy(
            update={"oos_exposure_state": OosExposureState.EVALUATED_LOCKED}
        )
        with pytest.raises(DataContractError, match="strictly prohibited"):
            pipeline.run_hypothesis_evaluation(
                features_table=feat_tbl,
                bars_table=bars_tbl,
                feature_name="obi_top5",
                hypothesis=hyp,
                split_policy=split_policy,
                search_record=search_record_locked,
                evaluate_oos=True,
            )

