"""Feature Extraction Pipeline Orchestrating Anti-Leakage Execution (Phase 3C).

Strictly enforces:
- Zero Lookahead: Filters incoming market data by T_event <= T_decision AND T_knowledge <= T_as_of.
- Complete Temporal Lineage: Builds and commits FeatureManifest for every extraction run.
- Zero Strategy / Signal logic.
"""

from datetime import date, datetime, timezone
import hashlib
from typing import List, Optional, Sequence, Tuple
import uuid
import pyarrow as pa

from acash.data.features.engine import (
    compute_book_features_table,
    compute_trade_features_table,
)
from acash.data.features.hashing import (
    calculate_canonical_book_features_sha256,
    calculate_canonical_trade_features_sha256,
    calculate_parameter_config_sha256,
)
from acash.data.features.schema import (
    BookFeaturesConfig,
    FeatureManifest,
    TradeFeaturesConfig,
)
from acash.data.features.storage import FeatureStorageEngine
from acash.data.orderbook.hashing import calculate_canonical_book_snapshot_sha256
from acash.data.orderbook.reconstruction import DepthLadderState
from acash.data.trades.hashing import calculate_canonical_trades_sha256


class FeatureExtractionPipeline:
    """Orchestrates microstructure feature extraction with strict temporal boundaries and lineage tracking."""

    def __init__(self, storage_engine: Optional[FeatureStorageEngine] = None) -> None:
        self.storage_engine = storage_engine or FeatureStorageEngine()

    def extract_trade_features(
        self,
        trades_table: pa.Table,
        symbol: str,
        trading_date: date,
        decision_time_utc: datetime,
        knowledge_cutoff_utc: datetime,
        config: Optional[TradeFeaturesConfig] = None,
        feature_set_name: str = "trade_microstructure_v1",
        software_version: str = "0.3.0",
    ) -> Tuple[FeatureManifest, pa.Table]:
        """Extract trade flow features with strict dual-temporal boundary filtering."""
        cfg = config or TradeFeaturesConfig()

        # Filter strictly by (exchange_time_utc <= decision_time_utc) AND (knowledge_time_utc <= knowledge_cutoff_utc)
        if trades_table.num_rows > 0:
            pydict = trades_table.to_pydict()
            valid_indices = []
            for i in range(trades_table.num_rows):
                t_ex = pydict["exchange_time_utc"][i]
                t_kn = pydict["knowledge_time_utc"][i]
                if t_ex <= decision_time_utc and t_kn <= knowledge_cutoff_utc:
                    valid_indices.append(i)
            filtered_trades = trades_table.take(valid_indices)
        else:
            filtered_trades = trades_table

        input_trades_hash = (
            calculate_canonical_trades_sha256(filtered_trades) if filtered_trades.num_rows > 0 else None
        )

        # Compute Features Table
        features_table = compute_trade_features_table(
            trades_table=filtered_trades,
            symbol=symbol,
            trading_date=trading_date,
            config=cfg,
        )

        out_hash = calculate_canonical_trade_features_sha256(features_table)
        param_hash = calculate_parameter_config_sha256(cfg)

        min_ex_str = (
            min(filtered_trades["exchange_time_utc"].to_pylist()).isoformat()
            if filtered_trades.num_rows > 0
            else ""
        )
        max_ex_str = (
            max(filtered_trades["exchange_time_utc"].to_pylist()).isoformat()
            if filtered_trades.num_rows > 0
            else ""
        )

        manifest_id = f"feat_trd_{symbol.replace('/', '-')}_{trading_date.isoformat()}_{out_hash[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()

        manifest = FeatureManifest(
            manifest_id=manifest_id,
            feature_set_name=feature_set_name,
            feature_definition_version="1.1.0",
            symbol=symbol,
            trading_date=trading_date.isoformat(),
            decision_time_utc=decision_time_utc.isoformat(),
            knowledge_cutoff_utc=knowledge_cutoff_utc.isoformat(),
            input_event_start_utc=min_ex_str,
            input_event_end_utc=max_ex_str,
            input_trades_sha256=input_trades_hash,
            input_book_sha256=None,
            parameter_config_sha256=param_hash,
            parameter_config_json=cfg.to_canonical_json(),
            software_version=software_version,
            feature_output_sha256=out_hash,
            row_count=features_table.num_rows,
            computed_at_utc=now_str,
        )

        if features_table.num_rows > 0:
            self.storage_engine.save_feature_table(manifest, features_table)

        return manifest, features_table

    def extract_book_features(
        self,
        ladder_states: Sequence[DepthLadderState],
        symbol: str,
        trading_date: date,
        decision_time_utc: datetime,
        knowledge_cutoff_utc: datetime,
        config: Optional[BookFeaturesConfig] = None,
        feature_set_name: str = "book_microstructure_v1",
        software_version: str = "0.3.0",
    ) -> Tuple[FeatureManifest, pa.Table]:
        """Extract order book microstructure features with strict decision time filtering."""
        cfg = config or BookFeaturesConfig()

        # Filter ladder states strictly <= decision_time_utc
        filtered_states = [s for s in ladder_states if s.exchange_time_utc <= decision_time_utc]

        features_table = compute_book_features_table(
            ladder_states=filtered_states,
            config=cfg,
        )

        out_hash = calculate_canonical_book_features_sha256(features_table)
        param_hash = calculate_parameter_config_sha256(cfg)

        min_ex_str = min(s.exchange_time_utc for s in filtered_states).isoformat() if filtered_states else ""
        max_ex_str = max(s.exchange_time_utc for s in filtered_states).isoformat() if filtered_states else ""

        manifest_id = f"feat_book_{symbol.replace('/', '-')}_{trading_date.isoformat()}_{out_hash[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()

        manifest = FeatureManifest(
            manifest_id=manifest_id,
            feature_set_name=feature_set_name,
            feature_definition_version="1.1.0",
            symbol=symbol,
            trading_date=trading_date.isoformat(),
            decision_time_utc=decision_time_utc.isoformat(),
            knowledge_cutoff_utc=knowledge_cutoff_utc.isoformat(),
            input_event_start_utc=min_ex_str,
            input_event_end_utc=max_ex_str,
            input_trades_sha256=None,
            input_book_sha256=None,
            parameter_config_sha256=param_hash,
            parameter_config_json=cfg.to_canonical_json(),
            software_version=software_version,
            feature_output_sha256=out_hash,
            row_count=features_table.num_rows,
            computed_at_utc=now_str,
        )

        if features_table.num_rows > 0:
            self.storage_engine.save_feature_table(manifest, features_table)

        return manifest, features_table
