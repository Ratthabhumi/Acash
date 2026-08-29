"""End-to-End Ingestion Pipeline for the ACASH Trades Domain (Phase 3A).

Coordinates:
- Source data ingestion & raw SHA-256 calculation.
- Trade data integrity validation & anomaly preservation.
- Deterministic batch identity generation.
- Global Trade Row Identity duplicate checking against existing canonical Parquet parts.
- Recoverable Batch Commit Protocol execution.
- Safe idempotent replays and batch collision detection.
"""

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import pyarrow as pa
from pydantic import BaseModel, ConfigDict

from acash.data.provenance import calculate_raw_source_sha256
from acash.data.schema import (
    BatchCollisionError,
    DataContractError,
    IntegrityViolationError,
)
from acash.data.trades.hashing import calculate_canonical_trades_sha256
from acash.data.trades.integrity import (
    TradesIntegrityValidator,
    TradeValidationReport,
)
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA
from acash.data.trades.storage import TradesStorageEngine


class IngestedTradesBatchSummary(BaseModel):
    """Summary of an ingested trades batch."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    batch_id: str
    source_id: str
    symbol: str
    trading_date: str
    row_count: int
    raw_source_sha256: str
    canonical_trades_sha256: str
    part_file_path: str
    validation_status: str
    warning_count: int = 0


class TradesIngestionResult(BaseModel):
    """Result of an ingestion pipeline run."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_success: bool
    batches_ingested: List[IngestedTradesBatchSummary]
    total_rows: int
    error_message: Optional[str] = None


class TradesIngestionPipeline:
    """Orchestrates end-to-end ingestion, validation, and storage for trades datasets."""

    def __init__(
        self,
        storage_engine: Optional[TradesStorageEngine] = None,
        validator: Optional[TradesIntegrityValidator] = None,
    ) -> None:
        self.storage = storage_engine or TradesStorageEngine()
        self.validator = validator or TradesIntegrityValidator()

    def ingest(
        self,
        raw_table: pa.Table,
        source_id: str,
        source_uri: str,
        batch_id: Optional[str] = None,
        declared_resets: Optional[Set[Tuple[str, str, str, date]]] = None,
        schema_version: str = "1.3.0",
        transform_version: str = "1.0.0",
    ) -> TradesIngestionResult:
        """Ingest a trades table through the ACASH Trades Data Subsystem.

        Guarantees:
        - 1:1 Ingestion Unit mapping per (source_id, symbol, trading_date).
        - Replay idempotency: identical batch replay returns existing part without creating duplicate files.
        - Batch collision prevention: modified data under same batch_id raises BatchCollisionError.
        - Global trade duplicate prevention: duplicate Trade Row Identity under a different batch raises IntegrityViolationError.
        """
        if raw_table.num_rows == 0:
            report, _ = self.validator.validate_table(table=raw_table)
            if not report.is_valid:
                raise IntegrityViolationError("Empty Trades table has invalid canonical schema.")

            return TradesIngestionResult(
                is_success=True,
                batches_ingested=[],
                total_rows=0,
            )

        # 1. Group table by (symbol, trading_date) to ensure 1:1 Ingestion Unit batches
        symbol_col = raw_table["symbol"].to_pylist()
        date_col = raw_table["trading_date"].to_pylist()

        distinct_units: Dict[Tuple[str, date], List[int]] = {}
        for i in range(raw_table.num_rows):
            sym = str(symbol_col[i])
            t_d = date_col[i]
            t_d_val = t_d if isinstance(t_d, date) else date.fromisoformat(str(t_d))
            distinct_units.setdefault((sym, t_d_val), []).append(i)

        # Pre-commit check: Explicit batch_id is valid ONLY for single-unit payloads
        if batch_id is not None and len(distinct_units) > 1:
            raise DataContractError(
                f"Explicit batch_id '{batch_id}' cannot be applied to a multi-unit payload containing {len(distinct_units)} distinct stream units. Explicit batch_id is only valid for single-unit tables."
            )

        ingested_summaries: List[IngestedTradesBatchSummary] = []

        total_rows_ingested = 0

        for (sym, t_date_val), indices in distinct_units.items():
            unit_table = raw_table.take(indices)

            # Compute raw source sha256 via Arrow IPC serialization
            sink = pa.BufferOutputStream()
            with pa.ipc.new_stream(sink, unit_table.schema) as writer:
                writer.write_table(unit_table)
            raw_bytes = sink.getvalue().to_pybytes()
            raw_source_sha256 = calculate_raw_source_sha256(raw_bytes)


            # Derive deterministic batch_id if not provided
            date_str = t_date_val.isoformat()
            norm_sym = sym.replace("/", "-").upper()
            unit_batch_id = batch_id or f"batch_trades_{source_id}_{norm_sym}_{date_str}_{raw_source_sha256[:16]}"

            # Check existing trade identities from storage
            existing_identities = self.storage.get_existing_trade_identities_lookup(
                symbol=sym,
                trading_date_val=t_date_val,
                exclude_batch_ids=[unit_batch_id],
            )

            # Validate table
            report, validated_table = self.validator.validate_table(
                table=unit_table,
                declared_resets=declared_resets,
                existing_trade_identity_lookup=existing_identities,
            )

            # Commit batch
            part_path = self.storage.commit_batch(
                batch_id=unit_batch_id,
                table=validated_table,
                source_id=source_id,
                source_uri=source_uri,
                raw_source_sha256=raw_source_sha256,
                schema_version=schema_version,
                transform_version=transform_version,
                validation_status=report.status,
                error_count=report.metrics.error_count,
                warning_count=report.metrics.warning_count,
            )

            canonical_hash = calculate_canonical_trades_sha256(validated_table)

            summary = IngestedTradesBatchSummary(
                batch_id=unit_batch_id,
                source_id=source_id,
                symbol=sym,
                trading_date=date_str,
                row_count=validated_table.num_rows,
                raw_source_sha256=raw_source_sha256,
                canonical_trades_sha256=canonical_hash,
                part_file_path=str(part_path),
                validation_status=report.status,
                warning_count=report.metrics.warning_count,
            )
            ingested_summaries.append(summary)
            total_rows_ingested += validated_table.num_rows

        return TradesIngestionResult(
            is_success=True,
            batches_ingested=ingested_summaries,
            total_rows=total_rows_ingested,
        )
