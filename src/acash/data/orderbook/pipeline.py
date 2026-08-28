"""Ingestion Pipeline for Order Book Snapshots and Deltas (Phase 3B).

Strictly enforces:
- 1:1 Ingestion Unit mapping per (source_id, channel_id, symbol, trading_date).
- Pre-commit validation preventing multi-unit batch_id collision.
- String-typed channel_id validation (no integer casting or silent empty fallback).
- Replay idempotency: identical batch replay returns existing part path.
- Batch collision prevention: modified data under same batch_id raises BatchCollisionError.
- Global duplicate prevention: duplicate Snapshot/Delta Row Identity raises IntegrityViolationError.
- Strict data contract validation prior to commit.
"""

from dataclasses import dataclass
from datetime import date
import hashlib
from typing import Dict, List, Optional, Set, Tuple
import pyarrow as pa

from acash.data.orderbook.integrity import OrderBookIntegrityValidator
from acash.data.orderbook.schema import SnapshotShapePolicy
from acash.data.orderbook.storage import OrderBookStorageEngine
from acash.data.provenance import calculate_raw_source_sha256
from acash.data.schema import BatchCollisionError, DataContractError, IntegrityViolationError


@dataclass
class IngestedBookBatchSummary:
    """Summary of an ingested Order Book batch."""
    batch_id: str
    part_type: str  # "SNAPSHOT" or "DELTA"
    symbol: str
    trading_date: date
    canonical_sha256: str
    part_file_path: str
    row_count: int


@dataclass
class BookIngestionResult:
    """Result of an Order Book ingestion execution."""
    is_success: bool
    batches_ingested: List[IngestedBookBatchSummary]
    total_rows: int


class OrderBookIngestionPipeline:
    """End-to-end ingestion pipeline for Order Book Snapshots and Deltas."""

    def __init__(
        self,
        storage_engine: Optional[OrderBookStorageEngine] = None,
        validator: Optional[OrderBookIntegrityValidator] = None,
    ) -> None:
        self.storage_engine = storage_engine or OrderBookStorageEngine()
        self.validator = validator or OrderBookIntegrityValidator()

    def ingest_snapshots(
        self,
        raw_table: pa.Table,
        source_id: str,
        source_uri: str,
        batch_id: Optional[str] = None,
        shape_policy: SnapshotShapePolicy = SnapshotShapePolicy.FIXED_DEPTH_N,
        schema_version: str = "1.8.0",
        transform_version: str = "1.0.0",
    ) -> BookIngestionResult:
        """Ingest a table of Order Book Snapshots."""
        if raw_table.num_rows == 0:
            report, _ = self.validator.validate_snapshot_table(table=raw_table)
            if not report.is_valid:
                raise IntegrityViolationError("Empty Order Book Snapshot table has invalid canonical schema.")
            return BookIngestionResult(is_success=True, batches_ingested=[], total_rows=0)

        # 1. Group table by (source_id, channel_id, symbol, trading_date) Stream Scope
        if "channel_id" not in raw_table.column_names:
            raise DataContractError("Missing mandatory 'channel_id' column in Order Book Snapshot table.")

        symbol_col = raw_table["symbol"].to_pylist()
        date_col = raw_table["trading_date"].to_pylist()
        channel_col = raw_table["channel_id"].to_pylist()

        distinct_units: Dict[Tuple[str, str, str, date], List[int]] = {}
        for i in range(raw_table.num_rows):
            sym = str(symbol_col[i]) if symbol_col[i] is not None else ""
            if not sym or sym.strip() == "":
                raise DataContractError(f"Row {i}: symbol cannot be null or empty string.")

            raw_ch = channel_col[i]
            if raw_ch is None or str(raw_ch).strip() == "":
                raise DataContractError(f"Row {i}: channel_id cannot be null or empty string.")
            ch = str(raw_ch).strip()

            t_d = date_col[i]
            if t_d is None:
                raise DataContractError(f"Row {i}: trading_date cannot be null.")
            t_d_val = t_d if isinstance(t_d, date) else date.fromisoformat(str(t_d))
            distinct_units.setdefault((source_id, ch, sym, t_d_val), []).append(i)

        # Pre-commit check: Explicit batch_id is valid ONLY for single-unit payloads
        if batch_id is not None and len(distinct_units) > 1:
            raise DataContractError(
                f"Explicit batch_id '{batch_id}' cannot be applied to a multi-unit payload containing {len(distinct_units)} distinct stream units. Explicit batch_id is only valid for single-unit tables."
            )

        ingested_summaries: List[IngestedBookBatchSummary] = []
        total_rows_ingested = 0

        for (src, ch, sym, t_date_val), indices in distinct_units.items():
            unit_table = raw_table.take(indices)

            # Compute raw source sha256 via IPC serialization
            sink = pa.BufferOutputStream()
            with pa.ipc.new_stream(sink, unit_table.schema) as writer:
                writer.write_table(unit_table)
            raw_bytes = sink.getvalue().to_pybytes()
            raw_source_sha256 = calculate_raw_source_sha256(raw_bytes)

            date_str = t_date_val.isoformat()
            norm_sym = sym.replace("/", "-").upper()
            norm_src = src.replace("/", "-").upper()
            norm_ch = ch.replace("/", "-").upper()
            target_batch_id = batch_id or f"batch_book_snap_{norm_src}_ch{norm_ch}_{norm_sym}_{date_str}_{raw_source_sha256[:16]}"

            # Check existing manifest for idempotency
            existing_manifest = self.storage_engine.provenance_tracker.load_manifest(target_batch_id)
            existing_lookup = (
                None if existing_manifest else self.storage_engine.get_existing_snapshot_identities_lookup(sym)
            )

            # Validate
            report, validated_table = self.validator.validate_snapshot_table(
                table=unit_table,
                existing_snapshot_identity_lookup=existing_lookup,
            )

            if not report.is_valid:
                raise IntegrityViolationError(f"Snapshot Validation failed for batch '{target_batch_id}'")

            # Commit
            part_path = self.storage_engine.commit_snapshot_batch(
                batch_id=target_batch_id,
                table=validated_table,
                source_id=source_id,
                source_uri=source_uri,
                raw_source_sha256=raw_source_sha256,
                schema_version=schema_version,
                transform_version=transform_version,
            )

            manifest = self.storage_engine.provenance_tracker.load_manifest(target_batch_id)
            canonical_hash = manifest.canonical_batch_sha256 if manifest else ""

            ingested_summaries.append(
                IngestedBookBatchSummary(
                    batch_id=target_batch_id,
                    part_type="SNAPSHOT",
                    symbol=sym,
                    trading_date=t_date_val,
                    canonical_sha256=canonical_hash,
                    part_file_path=str(part_path),
                    row_count=validated_table.num_rows,
                )
            )
            total_rows_ingested += validated_table.num_rows

        return BookIngestionResult(
            is_success=True,
            batches_ingested=ingested_summaries,
            total_rows=total_rows_ingested,
        )

    def ingest_deltas(
        self,
        raw_table: pa.Table,
        source_id: str,
        source_uri: str,
        batch_id: Optional[str] = None,
        schema_version: str = "1.8.0",
        transform_version: str = "1.0.0",
    ) -> BookIngestionResult:
        """Ingest a table of Order Book Incremental Deltas."""
        if raw_table.num_rows == 0:
            report, _ = self.validator.validate_delta_table(table=raw_table)
            if not report.is_valid:
                raise IntegrityViolationError("Empty Order Book Delta table has invalid canonical schema.")
            return BookIngestionResult(is_success=True, batches_ingested=[], total_rows=0)

        # 1. Group table by (source_id, channel_id, symbol, trading_date) Stream Scope
        if "channel_id" not in raw_table.column_names:
            raise DataContractError("Missing mandatory 'channel_id' column in Order Book Delta table.")

        symbol_col = raw_table["symbol"].to_pylist()
        date_col = raw_table["trading_date"].to_pylist()
        channel_col = raw_table["channel_id"].to_pylist()

        distinct_units: Dict[Tuple[str, str, str, date], List[int]] = {}
        for i in range(raw_table.num_rows):
            sym = str(symbol_col[i]) if symbol_col[i] is not None else ""
            if not sym or sym.strip() == "":
                raise DataContractError(f"Row {i}: symbol cannot be null or empty string.")

            raw_ch = channel_col[i]
            if raw_ch is None or str(raw_ch).strip() == "":
                raise DataContractError(f"Row {i}: channel_id cannot be null or empty string.")
            ch = str(raw_ch).strip()

            t_d = date_col[i]
            if t_d is None:
                raise DataContractError(f"Row {i}: trading_date cannot be null.")
            t_d_val = t_d if isinstance(t_d, date) else date.fromisoformat(str(t_d))
            distinct_units.setdefault((source_id, ch, sym, t_d_val), []).append(i)

        # Pre-commit check: Explicit batch_id is valid ONLY for single-unit payloads
        if batch_id is not None and len(distinct_units) > 1:
            raise DataContractError(
                f"Explicit batch_id '{batch_id}' cannot be applied to a multi-unit payload containing {len(distinct_units)} distinct stream units. Explicit batch_id is only valid for single-unit tables."
            )

        ingested_summaries: List[IngestedBookBatchSummary] = []
        total_rows_ingested = 0

        for (src, ch, sym, t_date_val), indices in distinct_units.items():
            unit_table = raw_table.take(indices)

            sink = pa.BufferOutputStream()
            with pa.ipc.new_stream(sink, unit_table.schema) as writer:
                writer.write_table(unit_table)
            raw_bytes = sink.getvalue().to_pybytes()
            raw_source_sha256 = calculate_raw_source_sha256(raw_bytes)

            date_str = t_date_val.isoformat()
            norm_sym = sym.replace("/", "-").upper()
            norm_src = src.replace("/", "-").upper()
            norm_ch = ch.replace("/", "-").upper()
            target_batch_id = batch_id or f"batch_book_delta_{norm_src}_ch{norm_ch}_{norm_sym}_{date_str}_{raw_source_sha256[:16]}"

            existing_manifest = self.storage_engine.provenance_tracker.load_manifest(target_batch_id)
            existing_lookup = (
                None if existing_manifest else self.storage_engine.get_existing_delta_identities_lookup(sym)
            )

            # Validate
            report, validated_table = self.validator.validate_delta_table(
                table=unit_table,
                existing_delta_identity_lookup=existing_lookup,
            )

            if not report.is_valid:
                raise IntegrityViolationError(f"Delta Validation failed for batch '{target_batch_id}'")

            # Commit
            part_path = self.storage_engine.commit_delta_batch(
                batch_id=target_batch_id,
                table=validated_table,
                source_id=source_id,
                source_uri=source_uri,
                raw_source_sha256=raw_source_sha256,
                schema_version=schema_version,
                transform_version=transform_version,
            )

            manifest = self.storage_engine.provenance_tracker.load_manifest(target_batch_id)
            canonical_hash = manifest.canonical_batch_sha256 if manifest else ""

            ingested_summaries.append(
                IngestedBookBatchSummary(
                    batch_id=target_batch_id,
                    part_type="DELTA",
                    symbol=sym,
                    trading_date=t_date_val,
                    canonical_sha256=canonical_hash,
                    part_file_path=str(part_path),
                    row_count=validated_table.num_rows,
                )
            )
            total_rows_ingested += validated_table.num_rows

        return BookIngestionResult(
            is_success=True,
            batches_ingested=ingested_summaries,
            total_rows=total_rows_ingested,
        )

