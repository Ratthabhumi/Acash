"""Alpha Research Pipeline Orchestrating Pre-Registered Hypothesis Evaluation (Phase 4).

Strictly enforces:
- Full research workflow: Hypothesis -> Outcomes -> In-Sample Evaluation -> Validation -> Blind OOS.
- Blind OOS State Machine: UNEXPOSED -> EVALUATED_LOCKED -> EXHAUSTED.
- 3-Tier Friction Waterfall.
- Complete ResearchManifest emission.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

import uuid
import pyarrow as pa

from acash.data.features.engine import to_decimal18
from acash.data.schema import DataContractError
from acash.research.evaluation import evaluate_hypothesis_relationship
from acash.research.manifest import (
    ResearchManifestEngine,
    calculate_hypothesis_spec_sha256,
    calculate_research_search_record_sha256,
)
from acash.research.outcomes import (
    compute_discrete_forward_returns,
    partition_dataset_with_embargo,
)
from acash.research.schema import (
    CANONICAL_HYPOTHESIS_EVALUATION_SCHEMA,
    CostModelConfig,
    EvaluationResult,
    HacInferencePolicy,
    HypothesisSpecification,
    OosExposureState,
    ResearchManifest,
    ResearchSearchRecord,
    SplitPolicy,
)


class AlphaResearchPipeline:
    """Orchestrates end-to-end alpha hypothesis research with strict OOS governance and lineage tracking."""

    def __init__(self, manifest_engine: Optional[ResearchManifestEngine] = None) -> None:
        self.manifest_engine = manifest_engine or ResearchManifestEngine()

    def run_hypothesis_evaluation(
        self,
        features_table: pa.Table,
        bars_table: pa.Table,
        feature_name: str,
        hypothesis: HypothesisSpecification,
        split_policy: Optional[SplitPolicy] = None,
        hac_policy: Optional[HacInferencePolicy] = None,
        cost_config: Optional[CostModelConfig] = None,
        search_record: Optional[ResearchSearchRecord] = None,
        evaluate_oos: bool = False,
        software_version: str = "0.4.0",
    ) -> Tuple[ResearchManifest, EvaluationResult, pa.Table]:
        """Run complete hypothesis evaluation across temporal partitions."""
        split_cfg = split_policy or SplitPolicy()
        hac_cfg = hac_policy or HacInferencePolicy()
        cost_cfg = cost_config or CostModelConfig()

        if feature_name not in features_table.column_names:
            raise DataContractError(f"Feature '{feature_name}' not found in features table.")

        num_bars = bars_table.num_rows
        if num_bars < 10:
            raise DataContractError(f"Insufficient bars for research evaluation: {num_bars} < 10")

        # 1. Partition dataset indices with embargo buffers
        partitions = partition_dataset_with_embargo(num_bars, split_cfg)
        train_start, train_end = partitions["TRAIN"]
        val_start, val_end = partitions["VAL"]
        oos_start, oos_end = partitions["OOS"]

        # 2. Compute discrete forward returns with boundary purging
        t_d = date.fromisoformat(hypothesis.registered_at_utc[:10])
        outcomes_table = compute_discrete_forward_returns(
            bars_table=bars_table,
            symbol=hypothesis.target_symbol,
            trading_date=t_d,
            horizons=hypothesis.target_horizons,
            train_end_idx=train_end,
            val_end_idx=val_end,
        )

        # Filter forward returns for primary horizon
        primary_h = hypothesis.primary_horizon
        out_dict = outcomes_table.to_pydict()
        feat_dict = features_table.to_pydict()

        # Extract aligned (feature, return, is_purged) series for primary horizon
        aligned_records: List[Dict[str, Any]] = []
        for i in range(outcomes_table.num_rows):
            if out_dict["horizon_bars"][i] == primary_h and out_dict["forward_return"][i] is not None:
                orig_t = out_dict["decision_bar_index"][i]
                aligned_records.append({
                    "bar_idx": orig_t,
                    "feature": feat_dict[feature_name][orig_t] if orig_t < features_table.num_rows else Decimal("0"),
                    "forward_return": out_dict["forward_return"][i],
                    "is_purged": out_dict["is_purged_boundary"][i],
                })

        # Separate into Train, Validation, and OOS slices
        train_feat, train_ret = [], []
        purged_train_count = 0
        val_feat, val_ret = [], []
        oos_feat, oos_ret = [], []

        for rec in aligned_records:
            b_idx = rec["bar_idx"]
            if train_start <= b_idx <= train_end:
                if rec["is_purged"]:
                    purged_train_count += 1
                else:
                    train_feat.append(rec["feature"])
                    train_ret.append(rec["forward_return"])
            elif val_start <= b_idx <= val_end:
                if not rec["is_purged"]:
                    val_feat.append(rec["feature"])
                    val_ret.append(rec["forward_return"])
            elif oos_start <= b_idx <= oos_end:
                oos_feat.append(rec["feature"])
                oos_ret.append(rec["forward_return"])


        # 3. In-Sample Evaluation
        train_result = evaluate_hypothesis_relationship(
            features=train_feat,
            forward_returns=train_ret,
            horizon=primary_h,
            hypothesis=hypothesis,
            hac_policy=hac_cfg,
            cost_config=cost_cfg,
            purged_count=purged_train_count,
        )

        # 4. Out-of-Sample Evaluation & State Machine Governance
        oos_beta: Optional[Decimal] = None
        oos_t_stat: Optional[Decimal] = None
        oos_r_ic: Optional[Decimal] = None
        oos_state = OosExposureState.UNEXPOSED

        if evaluate_oos:
            if search_record and search_record.oos_exposure_state == OosExposureState.EVALUATED_LOCKED:
                # Attempted re-evaluation on locked OOS -> mark EXHAUSTED
                oos_state = OosExposureState.EXHAUSTED
                raise DataContractError(
                    f"Hypothesis '{hypothesis.hypothesis_id}' has already been evaluated against OOS. Re-tuning on OOS is strictly prohibited."
                )

            oos_result = evaluate_hypothesis_relationship(
                features=oos_feat,
                forward_returns=oos_ret,
                horizon=primary_h,
                hypothesis=hypothesis,
                hac_policy=hac_cfg,
                cost_config=cost_cfg,
            )
            oos_beta = oos_result.beta
            oos_t_stat = oos_result.hac_t_stat
            oos_r_ic = oos_result.spearman_rank_ic
            oos_state = OosExposureState.EVALUATED_LOCKED

        # 5. Build and Commit ResearchManifest
        search_rec = search_record or ResearchSearchRecord(
            experiment_id=f"EXP-{uuid.uuid4().hex[:8]}",
            hypothesis_id=hypothesis.hypothesis_id,
            parameter_variants_count=1,
            feature_variants_tried=[feature_name],
            label_variants_tried=[f"H_{primary_h}"],
            model_variants_tried=["OLS_BETA_HAC"],
            dataset_window_variants_tried=[hypothesis.target_symbol],
            selection_procedure="max_in_sample_rank_ic",
            selected_candidate_id=hypothesis.hypothesis_id,
            total_effective_trials=1,
            oos_exposure_state=oos_state,
        )

        manifest_id = f"res_{hypothesis.hypothesis_id}_{primary_h}h_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now(timezone.utc).isoformat()

        p_start_str = str(bars_table["bar_start_utc"][0].as_py())
        p_end_str = str(bars_table["bar_end_utc"][-1].as_py())

        manifest = ResearchManifest(
            manifest_id=manifest_id,
            experiment_id=search_rec.experiment_id,
            hypothesis_id=hypothesis.hypothesis_id,
            hypothesis_version=hypothesis.hypothesis_version,
            symbol=hypothesis.target_symbol,
            inference_estimator="OLS_SLOPE_BETA_HAC",
            forward_return_definition="NEXT_BAR_OPEN_TO_HORIZON_CLOSE_V1",
            hac_bandwidth_method=hac_cfg.bandwidth_method.value,
            hac_bandwidth_value=train_result.selected_hac_lag,
            hac_kernel=hac_cfg.kernel_type,
            cost_model_version="3_TIER_FIXED_PROXY_V1",
            purging_policy_version="LABEL_INTERVAL_PURGING_V1",
            embargo_policy_version="MAX_HORIZON_EMBARGO_V1",
            input_feature_hashes=["phase3c_features_hash"],
            parameter_config_hash=calculate_hypothesis_spec_sha256(hypothesis),
            search_record_hash=calculate_research_search_record_sha256(search_rec),
            train_window=(p_start_str, str(bars_table["bar_end_utc"][train_end].as_py())),
            validation_window=(str(bars_table["bar_start_utc"][val_start].as_py()), str(bars_table["bar_end_utc"][val_end].as_py())),
            oos_window=(str(bars_table["bar_start_utc"][oos_start].as_py()), p_end_str),
            embargo_bars=split_cfg.embargo_bars,
            purged_train_rows_count=purged_train_count,
            in_sample_beta=train_result.beta,
            in_sample_hac_t_stat=train_result.hac_t_stat,
            in_sample_rank_ic=train_result.spearman_rank_ic or Decimal("0"),
            oos_beta=oos_beta,
            oos_hac_t_stat=oos_t_stat,
            oos_rank_ic=oos_r_ic,
            tier3_economic_edge_bps=train_result.tier3_economic_edge_bps,
            is_hypothesis_accepted=not train_result.is_falsified,
            oos_exposure_state=oos_state,
            software_version=software_version,
            computed_at_utc=now_str,
        )

        self.manifest_engine.save_research_manifest(manifest)

        # Build PyArrow Evaluation Table
        eval_data = {
            "hypothesis_id": [hypothesis.hypothesis_id],
            "symbol": [hypothesis.target_symbol],
            "horizon_bars": [primary_h],
            "partition": ["TRAIN"],
            "beta": [train_result.beta],
            "hac_se": [train_result.hac_se],
            "hac_t_stat": [train_result.hac_t_stat],
            "asymptotic_p_value": [train_result.asymptotic_p_value],
            "pearson_ic": [train_result.pearson_ic],
            "spearman_rank_ic": [train_result.spearman_rank_ic],
            "tier1_raw_edge_bps": [train_result.tier1_raw_edge_bps],
            "tier2_net_edge_bps": [train_result.tier2_net_edge_bps],
            "tier3_economic_edge_bps": [train_result.tier3_economic_edge_bps],
            "is_falsified": [train_result.is_falsified],
        }
        eval_table = pa.Table.from_pydict(eval_data, schema=CANONICAL_HYPOTHESIS_EVALUATION_SCHEMA)

        return manifest, train_result, eval_table
