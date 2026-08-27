"""Parquet Partitioned Storage and Manifest Engine for Microstructure Features (Phase 3C).

Strictly enforces:
- Storage layout:
  data/parquet/features/{symbol}/{feature_set}/year={YYYY}/date={YYYY-MM-DD}/part-{manifest_id}.parquet
- Durable, atomic Feature Manifest saving and loading.
- DuckDB Point-in-Time querying over computed features.
"""

from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Union
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from acash.data.features.hashing import (
    calculate_canonical_book_features_sha256,
    calculate_canonical_trade_features_sha256,
)
from acash.data.features.schema import (
    CANONICAL_BOOK_FEATURES_SCHEMA,
    CANONICAL_TRADE_FEATURES_SCHEMA,
    FeatureManifest,
)
from acash.data.schema import BatchCollisionError, DataContractError


class FeatureStorageEngine:
    """Storage engine for persisting and querying precomputed microstructure features."""

    def __init__(
        self,
        base_dir: Union[str, Path] = "data/parquet/features",
        manifests_dir: Union[str, Path] = "data/manifests/features",
    ) -> None:
        self.base_dir = Path(base_dir)
        self.manifests_dir = Path(manifests_dir)

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

    def get_feature_part_path(
        self,
        symbol: str,
        feature_set: str,
        trading_date_val: date,
        manifest_id: str,
    ) -> Path:
        """Derive canonical partition path for a feature part file."""
        norm_sym = symbol.replace("/", "-").upper()
        norm_set = feature_set.replace("/", "-").lower()
        return (
            self.base_dir
            / norm_sym
            / norm_set
            / f"year={trading_date_val.year}"
            / f"date={trading_date_val.isoformat()}"
            / f"part-{manifest_id}.parquet"
        )

    def get_manifest_path(self, feature_set: str, manifest_id: str) -> Path:
        """Derive canonical file path for a Feature Manifest."""
        norm_set = feature_set.replace("/", "-").lower()
        set_dir = self.manifests_dir / norm_set
        set_dir.mkdir(parents=True, exist_ok=True)
        return set_dir / f"manifest-{manifest_id}.json"

    def save_feature_manifest(self, manifest: FeatureManifest) -> Path:
        """Save a FeatureManifest atomically using a temp file + fsync + os.replace."""
        target_path = self.get_manifest_path(manifest.feature_set_name, manifest.manifest_id)
        temp_path = target_path.parent / f".tmp_manifest_{manifest.manifest_id}_{os.getpid()}.json"

        manifest_data = manifest.model_dump(mode="json")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, target_path)
        return target_path

    def load_feature_manifest(self, feature_set: str, manifest_id: str) -> Optional[FeatureManifest]:
        """Load an existing FeatureManifest by feature_set and manifest_id."""
        target_path = self.get_manifest_path(feature_set, manifest_id)
        if not target_path.exists():
            return None
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return FeatureManifest.model_validate(data)

    def save_feature_table(
        self,
        manifest: FeatureManifest,
        table: pa.Table,
    ) -> Path:
        """Save a computed feature table and its manifest atomically."""
        if table.num_rows == 0:
            raise DataContractError(f"Cannot save empty feature table for manifest {manifest.manifest_id}")

        # Compute output hash
        if "delta" in table.column_names:
            out_hash = calculate_canonical_trade_features_sha256(table)
        else:
            out_hash = calculate_canonical_book_features_sha256(table)

        if manifest.feature_output_sha256 != out_hash:
            raise DataContractError(
                f"Manifest feature_output_sha256 mismatch: manifest '{manifest.feature_output_sha256}' != computed '{out_hash}'"
            )

        trading_date_val = date.fromisoformat(manifest.trading_date)
        target_path = self.get_feature_part_path(
            symbol=manifest.symbol,
            feature_set=manifest.feature_set_name,
            trading_date_val=trading_date_val,
            manifest_id=manifest.manifest_id,
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Save manifest
        self.save_feature_manifest(manifest)

        # 2. Write Parquet part atomically
        with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet", dir=target_path.parent) as tmp_f:
            tmp_path = Path(tmp_f.name)

        try:
            pq.write_table(table, tmp_path, compression="zstd")
            os.replace(tmp_path, target_path)
            return target_path
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    def query_features(
        self,
        symbol: str,
        feature_set: str,
        start_time_utc: datetime,
        end_time_utc: datetime,
    ) -> pa.Table:
        """Query computed features for a symbol and timeframe window via DuckDB."""
        norm_sym = symbol.replace("/", "-").upper()
        norm_set = feature_set.replace("/", "-").lower()
        set_dir = self.base_dir / norm_sym / norm_set
        if not set_dir.exists():
            return pa.Table.from_batches([])

        glob_path = str(set_dir / "**" / "*.parquet").replace("\\", "/")
        start_str = start_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")
        end_str = end_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")

        # Determine if trade features (bar_start_utc) or book features (exchange_time_utc)
        con = duckdb.connect(":memory:")
        try:
            sample = con.execute("SELECT * FROM read_parquet(?) LIMIT 1", [glob_path]).arrow()
            col_names = sample.schema.names if hasattr(sample, "schema") else sample.column_names
            time_col = "bar_start_utc" if "bar_start_utc" in col_names else "exchange_time_utc"

            query = f"""
                SELECT * FROM read_parquet(?)
                WHERE symbol = ?
                  AND {time_col} >= CAST(? AS TIMESTAMPTZ)
                  AND {time_col} <= CAST(? AS TIMESTAMPTZ)
                ORDER BY {time_col} ASC
            """
            res_arrow = con.execute(query, [glob_path, symbol, start_str, end_str]).arrow()
            if isinstance(res_arrow, pa.RecordBatchReader):
                return res_arrow.read_all()
            return res_arrow
        except duckdb.IOException:
            return pa.Table.from_batches([])
        finally:
            con.close()

