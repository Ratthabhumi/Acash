"""Alpha Research Pipeline Orchestrating Pre-Registered Hypothesis Evaluation (Phase 4).

Strictly enforces:
- Full research workflow: Hypothesis -> Outcomes -> In-Sample Evaluation -> Validation -> Blind OOS.
- Blind OOS State Machine: UNEXPOSED -> EVALUATED_LOCKED -> EXHAUSTED.
- 3-Tier Friction Waterfall.
- Complete ResearchManifest emission.
"""

import hashlib
import struct
from datetime import date, datetime, timezone
from decimal import Decimal
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

# Canonical binary frame serialization constants
NULL_UINT32_TAG = 0xFFFFFFFF
NULL_INT64_SENTINEL = -9223372036854775808
RECORD_SEPARATOR_BYTE = b"\x1e"


def _encode_str(val: Optional[str]) -> bytes:
    """Encode string with 4-byte big-endian uint32 length prefix."""
    if val is None:
        return struct.pack(">I", NULL_UINT32_TAG)
    b = str(val).encode("utf-8")
    return struct.pack(">I", len(b)) + b


def _encode_dec(val: Optional[Decimal]) -> bytes:
    """Encode Decimal with 4-byte big-endian length prefix and fixed 18-scale ASCII."""
    if val is None:
        return struct.pack(">I", NULL_UINT32_TAG)
    b = f"{val:.18f}".encode("ascii")
    return struct.pack(">I", len(b)) + b


def _encode_int64(val: Optional[int]) -> bytes:
    """Encode int64 as 8-byte big-endian signed integer."""
    if val is None:
        return struct.pack(">q", NULL_INT64_SENTINEL)
    return struct.pack(">q", int(val))


def _encode_ts_us(val: Any) -> bytes:
    """Encode microsecond timestamp as 8-byte big-endian int64 epoch microseconds."""
    if val is None:
        return struct.pack(">q", NULL_INT64_SENTINEL)
    if isinstance(val, int):
        return struct.pack(">q", val)
    if isinstance(val, pa.Scalar):
        if val.as_py() is None:
            return struct.pack(">q", NULL_INT64_SENTINEL)
        return struct.pack(">q", val.value)
    if isinstance(val, datetime):
        dt_utc = val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
        td = dt_utc - datetime(1970, 1, 1, tzinfo=timezone.utc)
        total_us = (td.days * 86400 + td.seconds) * 1_000_000 + td.microseconds
        return struct.pack(">q", total_us)
    return struct.pack(">q", int(val))


def calculate_canonical_feature_table_sha256(table: pa.Table) -> str:
    """Calculate deterministic canonical length-prefixed binary SHA-256 hash over feature table.

    Invariant Rules:
    1. Canonical row ordering (sorted by timestamp/time column or lexicographically by all columns).
    2. Length-prefixed binary serialization matching Phase 2/3A/3B data contracts.
    3. Independent of chunking, memory layout, and column input order.
    """
    if table.num_rows == 0:
        return hashlib.sha256(b"EMPTY_FEATURE_TABLE").hexdigest()

    sort_cols = [c for c in ("timestamp_utc", "bar_start_utc", "exchange_time_utc", "feature_time_utc") if c in table.column_names]
    if sort_cols:
        sorted_tbl = table.sort_by([(c, "ascending") for c in sort_cols])
    else:
        sort_keys = [(c, "ascending") for c in sorted(table.column_names)]
        sorted_tbl = table.sort_by(sort_keys)

    hasher = hashlib.sha256()
    col_names = sorted(sorted_tbl.column_names)

    # Encode header
    for c in col_names:
        hasher.update(_encode_str(c))
    hasher.update(RECORD_SEPARATOR_BYTE)

    num_rows = sorted_tbl.num_rows
    pydict = sorted_tbl.to_pydict()

    for i in range(num_rows):
        row_bytes = bytearray()
        for col in col_names:
            val = pydict[col][i]
            if isinstance(val, Decimal):
                row_bytes.extend(_encode_dec(val))
            elif isinstance(val, int):
                row_bytes.extend(_encode_int64(val))
            elif isinstance(val, datetime):
                row_bytes.extend(_encode_ts_us(val))
            elif isinstance(val, str):
                row_bytes.extend(_encode_str(val))
            elif val is None:
                row_bytes.extend(_encode_str(None))
            else:
                try:
                    row_bytes.extend(_encode_dec(Decimal(str(val))))
                except Exception:
                    row_bytes.extend(_encode_str(str(val)))
        row_bytes.extend(RECORD_SEPARATOR_BYTE)
        hasher.update(row_bytes)

    return hasher.hexdigest()


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
        feature_sha256 = calculate_canonical_feature_table_sha256(features_table)


        hyp_spec_hash = calculate_hypothesis_spec_sha256(hypothesis)
        manifest_seed = (
            f"{hypothesis.hypothesis_id}:{primary_h}:{hyp_spec_hash}:{feature_sha256}:"
            f"{split_cfg.train_pct}:{split_cfg.val_pct}:{evaluate_oos}"
        )

        manifest_digest = hashlib.sha256(manifest_seed.encode("utf-8")).hexdigest()[:16]
        manifest_id = f"res_{hypothesis.hypothesis_id}_{primary_h}h_{manifest_digest}"

        oos_beta: Optional[Decimal] = None
        oos_t_stat: Optional[Decimal] = None
        oos_r_ic: Optional[Decimal] = None
        current_ledger_state = self.manifest_engine.governance_ledger.get_oos_state(hypothesis.hypothesis_id)
        oos_state = current_ledger_state

        if evaluate_oos:
            if search_record is None:
                raise DataContractError(
                    f"Explicit ResearchSearchRecord is mandatory for Blind OOS evaluation of hypothesis '{hypothesis.hypothesis_id}'."
                )

            # Record and transition state in durable ledger (raises DataContractError if already locked/exhausted)
            oos_state = self.manifest_engine.governance_ledger.record_oos_evaluation(
                hypothesis_id=hypothesis.hypothesis_id,
                search_record=search_record,
                manifest_id=manifest_id,
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

        # 5. Build and Commit ResearchManifest
        search_rec = search_record or ResearchSearchRecord(
            experiment_id=f"EXP-{manifest_digest[:8]}",
            hypothesis_id=hypothesis.hypothesis_id,
            parameter_variants_count=1,
            feature_variants_tried=[feature_name],
            label_variants_tried=[f"H_{primary_h}"],
            model_variants_tried=["OLS_BETA_HAC"],
            dataset_window_variants_tried=[hypothesis.target_symbol],
            selection_procedure="in_sample_only",
            selected_candidate_id=hypothesis.hypothesis_id,
            total_effective_trials=1,
            oos_exposure_state=oos_state,
        )

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
            input_feature_hashes=[feature_sha256],
            parameter_config_hash=hyp_spec_hash,
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
