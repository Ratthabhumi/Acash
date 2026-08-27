"""Ingestion pipeline orchestrating reading, validation, splitting, and recoverable batch commit."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pyarrow as pa

from acash.data.integrity import DataIntegrityValidator, ValidationReport
from acash.data.provenance import calculate_raw_source_sha256
from acash.data.schema import (
    CANONICAL_ARROW_SCHEMA,
    IntegrityViolationError,
)
from acash.data.sources.base import IDataSourceAdapter
from acash.data.storage import ParquetStorageEngine


@dataclass(frozen=True)
class IngestedBatchSummary:
    """Summary of an individually committed 1:1 Ingestion Unit batch."""
    batch_id: str
    source_id: str
    symbol: str
    timeframe: str
    year_partition: int
    part_file_path: Path
    row_count: int
    canonical_batch_sha256: str


@dataclass
class IngestionResult:
    """Overall outcome of the ingestion pipeline execution."""
    is_successful: bool
    source_uri_or_path: str
    raw_source_sha256: str
    ingested_batches: List[IngestedBatchSummary] = field(default_factory=list)
    committed_part_paths: List[Path] = field(default_factory=list)
    validation_report: Optional[ValidationReport] = None
    error_message: Optional[str] = None


class IngestionPipeline:
    """Orchestrates the entire market data ingestion workflow."""

    def __init__(
        self,
        storage_engine: Optional[ParquetStorageEngine] = None,
        validator: Optional[DataIntegrityValidator] = None,
    ) -> None:
        self.storage_engine = storage_engine or ParquetStorageEngine()
        self.validator = validator or DataIntegrityValidator()

    def ingest(
        self,
        source_path_or_uri: Union[str, Path],
        adapter: IDataSourceAdapter,
        batch_id: Optional[str] = None,
        batch_id_prefix: Optional[str] = None,
        abort_on_validation_error: bool = True,
    ) -> IngestionResult:
        """Ingest market data from a source adapter.

        Sequence:
        1. Read raw source bytes & table.
        2. Compute raw_source_sha256.
        3. Query existing canonical revisions for global duplicate identity prevention.
        4. Validate integrity, monotonicity, and assign deterministic revision sequences.
        5. Split into distinct 1:1 Ingestion Units by (source_id, symbol, timeframe, year_partition).
        6. Execute Recoverable Batch Commit Protocol with deterministic batch identity.
        """
        source_str = str(source_path_or_uri)
        raw_bytes, raw_table = adapter.read_source(source_path_or_uri)
        raw_sha256 = calculate_raw_source_sha256(raw_bytes)

        # Extract streams in raw table for global duplicate lookup
        candidate_batch_ids: List[str] = []
        if raw_table.num_rows > 0:
            raw_pylist = raw_table.to_pylist()
            unique_stream_years = list({
                (
                    str(r["source_id"]),
                    str(r["symbol"]),
                    str(r["timeframe"]),
                    r["event_start_utc"].year if hasattr(r["event_start_utc"], "year") else 2026
                )
                for r in raw_pylist
            })
            unique_streams = list({(s[0], s[1], s[2]) for s in unique_stream_years})

            # Calculate candidate batch_ids for idempotent replay exclusion
            for idx, (src, sym, tf, year) in enumerate(sorted(unique_stream_years)):
                norm_sym = sym.replace("/", "-")
                if batch_id:
                    b_id = batch_id if len(unique_stream_years) == 1 else f"{batch_id}_{year}_{idx+1:03d}"
                elif batch_id_prefix:
                    b_id = f"{batch_id_prefix}_{src}_{norm_sym}_{tf}_{year}_{raw_sha256[:12]}"
                else:
                    b_id = f"batch_{src}_{norm_sym}_{tf}_{year}_{raw_sha256[:16]}"
                candidate_batch_ids.append(b_id)

            existing_lookup = self.storage_engine.get_existing_revisions_lookup(
                unique_streams, exclude_batch_ids=candidate_batch_ids
            )
        else:
            existing_lookup = {}

        # Validate integrity with existing revisions lookup
        report, validated_table = self.validator.validate_table(
            raw_table, existing_revisions_lookup=existing_lookup
        )

        if not report.is_valid:
            error_msg = f"Validation failed with {report.error_count} fatal errors."
            if abort_on_validation_error:
                raise IntegrityViolationError(f"{error_msg} Errors: {report.errors}")
            return IngestionResult(
                is_successful=False,
                source_uri_or_path=source_str,
                raw_source_sha256=raw_sha256,
                validation_report=report,
                error_message=error_msg,
            )

        if validated_table.num_rows == 0:
            return IngestionResult(
                is_successful=True,
                source_uri_or_path=source_str,
                raw_source_sha256=raw_sha256,
                ingested_batches=[],
                committed_part_paths=[],
                validation_report=report,
            )

        # Split validated table into 1:1 Ingestion Units: (source_id, symbol, timeframe, year)
        rows = validated_table.to_pylist()
        split_groups: Dict[Tuple[str, str, str, int], List[Dict[str, Any]]] = {}

        for row in rows:
            src = str(row["source_id"])
            sym = str(row["symbol"])
            tf = str(row["timeframe"])
            estart = row["event_start_utc"]
            year = estart.year if isinstance(estart, datetime) else 2026

            group_key = (src, sym, tf, year)
            if group_key not in split_groups:
                split_groups[group_key] = []
            split_groups[group_key].append(row)

        ingested_batches: List[IngestedBatchSummary] = []
        committed_part_paths: List[Path] = []

        total_units = len(split_groups)

        # Process each 1:1 Ingestion Unit
        for idx, (group_key, group_rows) in enumerate(sorted(split_groups.items())):
            src, sym, tf, year = group_key
            group_pydict = {
                col: [r[col] for r in group_rows]
                for col in CANONICAL_ARROW_SCHEMA.names
            }
            group_table = pa.Table.from_pydict(group_pydict, schema=CANONICAL_ARROW_SCHEMA)

            # Deterministic batch_id assignment
            norm_sym = sym.replace("/", "-")
            if batch_id:
                if total_units == 1:
                    unit_batch_id = batch_id
                else:
                    unit_batch_id = f"{batch_id}_{year}_{idx+1:03d}"
            elif batch_id_prefix:
                unit_batch_id = f"{batch_id_prefix}_{src}_{norm_sym}_{tf}_{year}_{raw_sha256[:12]}"
            else:
                unit_batch_id = f"batch_{src}_{norm_sym}_{tf}_{year}_{raw_sha256[:16]}"

            part_path = self.storage_engine.write_canonical_part(
                table=group_table,
                batch_id=unit_batch_id,
                source_id=src,
                source_uri_or_path=source_str,
                raw_source_sha256=raw_sha256,
                validation_status="VALID_WITH_WARNINGS" if report.warning_count > 0 else "VALID",
                error_count=report.error_count,
                warning_count=report.warning_count,
            )

            manifest = self.storage_engine.provenance_tracker.load_manifest(unit_batch_id)
            c_hash = manifest.canonical_batch_sha256 if manifest else ""

            summary = IngestedBatchSummary(
                batch_id=unit_batch_id,
                source_id=src,
                symbol=sym,
                timeframe=tf,
                year_partition=year,
                part_file_path=part_path,
                row_count=group_table.num_rows,
                canonical_batch_sha256=c_hash,
            )
            ingested_batches.append(summary)
            committed_part_paths.append(part_path)


        return IngestionResult(
            is_successful=True,
            source_uri_or_path=source_str,
            raw_source_sha256=raw_sha256,
            ingested_batches=ingested_batches,
            committed_part_paths=committed_part_paths,
            validation_report=report,
        )
