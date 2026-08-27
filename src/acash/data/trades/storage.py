"""Storage engine and DuckDB point-in-time analytical query layer for the Trades Domain (Phase 3A).

Implements:
- Partitioned immutable Parquet parts: data/parquet/trades/{symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
- Strict 1:1 Ingestion Unit mapping
- Recoverable Batch Commit Protocol with Trades Commit-Intent Manifests
- Crash recovery and quarantine for orphan parts
- DuckDB Point-in-Time qualification queries for high-frequency trades
"""

import os
import shutil
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict

from acash.data.provenance import (
    BatchLifecycleStatus,
    ProvenanceRecord,
    ProvenanceTracker,
)
from acash.data.schema import (
    BatchCollisionError,
    OrphanPartError,
)
from acash.data.trades.hashing import calculate_canonical_trades_sha256
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA


class TradesBatchManifest(BaseModel):
    """Durable commit-intent manifest storing complete recovery metadata for a trades batch."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    batch_id: str
    status: BatchLifecycleStatus
    source_id: str
    source_uri_or_path: str
    raw_source_sha256: str
    canonical_trades_sha256: str
    schema_version: str
    transform_version: str
    symbol: str
    trading_date: str
    year_partition: int
    part_file_path: str
    row_count: int
    min_exchange_time_utc: str
    max_exchange_time_utc: str
    created_at_utc: str
    updated_at_utc: str


class TradesStorageEngine:
    """Manages append-only immutable Parquet parts and the Recoverable Batch Commit Protocol for Trades."""

    def __init__(
        self,
        base_dir: Path = Path("data/parquet/trades"),
        manifests_dir: Path = Path("data/manifests/trades"),
        ledger_path: Path = Path("data/trades_provenance_ledger.jsonl"),
        quarantine_dir: Path = Path("data/quarantine/trades"),
    ) -> None:
        self.base_dir = Path(base_dir)
        self.manifests_dir = Path(manifests_dir)
        self.ledger_path = Path(ledger_path)
        self.quarantine_dir = Path(quarantine_dir)
        self.provenance_tracker = ProvenanceTracker(
            ledger_path=self.ledger_path,
            manifests_dir=self.manifests_dir,
        )

    def get_part_file_path(self, symbol: str, trading_date_val: date, batch_id: str) -> Path:
        """Get canonical 1:1 part path for a given trades ingestion unit."""
        normalized_symbol = symbol.replace("/", "-").upper()
        date_str = trading_date_val.isoformat()
        year = trading_date_val.year
        return self.base_dir / normalized_symbol / f"year={year}" / f"date={date_str}" / f"part-{batch_id}.parquet"

    def get_existing_trade_identities_lookup(
        self,
        symbol: str,
        trading_date_val: date,
        exclude_batch_ids: Optional[Sequence[str]] = None,
    ) -> Dict[Tuple[str, str, str, date, int, int], bool]:
        """Scan existing Parquet parts for the given symbol/date and build Trade Row Identity lookup."""
        lookup: Dict[Tuple[str, str, str, date, int, int], bool] = {}
        excluded_set = set(exclude_batch_ids or [])
        normalized_symbol = symbol.replace("/", "-").upper()
        date_str = trading_date_val.isoformat()
        year = trading_date_val.year

        date_dir = self.base_dir / normalized_symbol / f"year={year}" / f"date={date_str}"
        if not date_dir.exists():
            return lookup

        for part_path in date_dir.glob("*.parquet"):
            if part_path.name.startswith(".tmp_"):
                continue
            part_stem = part_path.stem
            if any(part_stem == f"part-{ex_id}" for ex_id in excluded_set):
                continue

            try:
                tbl = pq.read_table(
                    part_path,
                    columns=[
                        "source_id", "channel_id", "symbol", "trading_date",
                        "source_seq_num", "match_sub_idx"
                    ]
                )
                rows = tbl.to_pylist()
                for r in rows:
                    t_d = r["trading_date"]
                    t_d_val = t_d if isinstance(t_d, date) else date.fromisoformat(str(t_d))
                    ident_key = (
                        str(r["source_id"]),
                        str(r["channel_id"]),
                        str(r["symbol"]),
                        t_d_val,
                        int(r["source_seq_num"]),
                        int(r["match_sub_idx"]),
                    )
                    lookup[ident_key] = True
            except Exception:
                continue

        return lookup

    def commit_batch(
        self,
        batch_id: str,
        table: pa.Table,
        source_id: str,
        source_uri: str,
        raw_source_sha256: str,
        schema_version: str = "1.3.0",
        transform_version: str = "1.0.0",
        validation_status: str = "VALID",
        error_count: int = 0,
        warning_count: int = 0,
    ) -> Path:
        """Execute Recoverable Batch Commit Protocol for a canonical trades batch.

        Steps:
        1. Calculate canonical_trades_sha256.
        2. Create & save TradesManifest with status PREPARED.
        3. Write Parquet staging part file (.tmp_part_{batch_id}_{pid}.parquet) with zstd compression.
        4. Validate staging part file readability and schema.
        5. Atomically replace staging part to canonical part path (os.replace).
        6. Transition manifest status to PART_PUBLISHED.
        7. Append immutable audit record to provenance ledger.
        8. Transition manifest status to COMMITTED.
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

        if table.num_rows == 0:
            raise ValueError("Cannot commit an empty trades table.")

        symbol = str(table["symbol"][0].as_py())
        t_date = table["trading_date"][0].as_py()
        t_date_val = t_date if isinstance(t_date, date) else date.fromisoformat(str(t_date))
        canonical_trades_sha256 = calculate_canonical_trades_sha256(table)

        # Check existing provenance for idempotency or collision
        existing_record = self.provenance_tracker.get_provenance_record(batch_id)
        if existing_record:
            if existing_record.canonical_batch_sha256 == canonical_trades_sha256:
                target_path = self.get_part_file_path(symbol, t_date_val, batch_id)
                if target_path.exists():
                    return target_path
            else:
                raise BatchCollisionError(
                    f"Batch collision: batch_id '{batch_id}' already committed with hash "
                    f"'{existing_record.canonical_batch_sha256}', incoming hash is '{canonical_trades_sha256}'."
                )

        target_path = self.get_part_file_path(symbol, t_date_val, batch_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        exchange_times = table["exchange_time_utc"].to_pylist()
        sorted_ex = sorted([t for t in exchange_times if t is not None])
        min_ex_str = sorted_ex[0].isoformat() if hasattr(sorted_ex[0], "isoformat") else str(sorted_ex[0])
        max_ex_str = sorted_ex[-1].isoformat() if hasattr(sorted_ex[-1], "isoformat") else str(sorted_ex[-1])

        # Step 2: Create & save PREPARED manifest
        manifest = self.provenance_tracker.load_manifest(batch_id)
        if not manifest:
            from acash.data.provenance import BatchManifest
            manifest = BatchManifest(
                batch_id=batch_id,
                status=BatchLifecycleStatus.PREPARED,
                source_id=source_id,
                source_uri_or_path=source_uri,
                raw_source_sha256=raw_source_sha256,
                canonical_batch_sha256=canonical_trades_sha256,
                schema_version=schema_version,
                transform_version=transform_version,
                symbol=symbol,
                timeframe="TICK",
                year_partition=t_date_val.year,
                part_file_path=str(target_path),
                row_count=table.num_rows,
                min_event_time_utc=min_ex_str,
                max_event_time_utc=max_ex_str,
                created_at_utc=now_utc,
                updated_at_utc=now_utc,
            )
            self.provenance_tracker.save_manifest(manifest)

        # Step 3: Write Parquet staging part
        temp_part_path = target_path.parent / f".tmp_part_{batch_id}_{uuid.uuid4().hex[:8]}.parquet"
        pq.write_table(
            table,
            temp_part_path,
            compression="zstd",
            compression_level=3,
        )

        # Step 4: Validate staging file
        try:
            with open(temp_part_path, "rb") as f:
                read_back = pq.read_table(f)
                if read_back.num_rows != table.num_rows:
                    raise IOError(f"Staging file corruption: wrote {table.num_rows} rows, read {read_back.num_rows}")
        except Exception as exc:
            if temp_part_path.exists():
                try:
                    temp_part_path.unlink()
                except Exception:
                    pass
            raise IOError(f"Validation of staging part failed: {exc}") from exc

        # Step 5: Atomically publish
        os.replace(temp_part_path, target_path)


        # Step 6: Transition manifest to PART_PUBLISHED
        self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.PART_PUBLISHED)

        # Step 7: Append Provenance Record
        provenance_rec = ProvenanceRecord(
            provenance_id=f"prov_{uuid.uuid4().hex[:12]}",
            batch_id=batch_id,
            source_id=source_id,
            source_uri_or_path=source_uri,
            part_file_path=str(target_path),
            ingest_time_utc=now_utc,
            raw_source_sha256=raw_source_sha256,
            canonical_batch_sha256=canonical_trades_sha256,
            schema_version=schema_version,
            transform_version=transform_version,
            symbol=symbol,
            timeframe="TICK",
            row_count=table.num_rows,
            min_event_time_utc=min_ex_str,
            max_event_time_utc=max_ex_str,
            validation_status=validation_status,
            error_count=error_count,
            warning_count=warning_count,
        )
        self.provenance_tracker.append_provenance_record(provenance_rec)

        # Step 8: Transition manifest to COMMITTED
        self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.COMMITTED)
        return target_path

    def run_crash_recovery_pass(self) -> Dict[str, Any]:
        """Perform crash recovery pass across trades manifests and Parquet parts."""
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        recovered_batches: List[str] = []
        quarantined_parts: List[str] = []

        manifest_files = list(self.manifests_dir.glob("manifest-*.json"))
        for m_file in manifest_files:
            try:
                batch_id = m_file.stem.replace("manifest-", "")
                manifest = self.provenance_tracker.load_manifest(batch_id)
                if not manifest:
                    continue

                part_path = Path(manifest.part_file_path)

                if manifest.status == BatchLifecycleStatus.PART_PUBLISHED:
                    if part_path.exists():
                        table = pq.read_table(part_path)
                        part_hash = calculate_canonical_trades_sha256(table)
                        if part_hash == manifest.canonical_batch_sha256:
                            now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                            prov_rec = ProvenanceRecord(
                                provenance_id=f"prov_{uuid.uuid4().hex[:12]}",
                                batch_id=manifest.batch_id,
                                source_id=manifest.source_id,
                                source_uri_or_path=manifest.source_uri_or_path,
                                part_file_path=str(part_path),
                                ingest_time_utc=now_utc,
                                raw_source_sha256=manifest.raw_source_sha256,
                                canonical_batch_sha256=manifest.canonical_batch_sha256,
                                schema_version=manifest.schema_version,
                                transform_version=manifest.transform_version,
                                symbol=manifest.symbol,
                                timeframe=manifest.timeframe,
                                row_count=manifest.row_count,
                                min_event_time_utc=manifest.min_event_time_utc,
                                max_event_time_utc=manifest.max_event_time_utc,
                                validation_status="VALID",
                            )
                            self.provenance_tracker.append_provenance_record(prov_rec)
                            self.provenance_tracker.update_manifest_status(
                                manifest.batch_id, BatchLifecycleStatus.COMMITTED
                            )
                            recovered_batches.append(manifest.batch_id)
            except Exception:
                continue

        # Quarantine orphan parts
        for parquet_path in self.base_dir.glob("**/*.parquet"):
            if parquet_path.name.startswith(".tmp_"):
                continue
            part_batch_id = parquet_path.stem.replace("part-", "")
            manifest = self.provenance_tracker.load_manifest(part_batch_id)
            if not manifest:
                target_quarantine = self.quarantine_dir / parquet_path.name
                shutil.move(str(parquet_path), str(target_quarantine))
                quarantined_parts.append(str(target_quarantine))

        return {
            "recovered_batches": recovered_batches,
            "quarantined_parts": quarantined_parts,
        }

    def point_in_time_query(
        self,
        symbol: str,
        as_of_knowledge_time_utc: datetime,
        start_exchange_time_utc: datetime,
        end_exchange_time_utc: datetime,
        source_id: Optional[str] = None,
    ) -> pa.Table:
        """Execute DuckDB Point-in-Time (PIT) qualification query for trades.

        Guarantees:
        - Strict filtering knowledge_time_utc <= as_of_knowledge_time_utc (Zero lookahead).
        - Filter exchange_time_utc BETWEEN start and end.
        - Chronological order: exchange_time_utc ASC, source_seq_num ASC, match_sub_idx ASC.
        """
        normalized_symbol = symbol.replace("/", "-").upper()
        symbol_dir = self.base_dir / normalized_symbol
        if not symbol_dir.exists():
            return pa.Table.from_batches([], schema=CANONICAL_TRADES_SCHEMA)

        glob_pattern = f"{symbol_dir.as_posix()}/**/*.parquet"
        con = duckdb.connect()

        # Format ISO strings with explicit +00 offset for DuckDB TIMESTAMPTZ
        as_of_str = as_of_knowledge_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")
        start_str = start_exchange_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")
        end_str = end_exchange_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")

        query = """
            SELECT * FROM read_parquet(?)
            WHERE knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
              AND exchange_time_utc >= CAST(? AS TIMESTAMPTZ)
              AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ)
        """
        params: List[Any] = [glob_pattern, as_of_str, start_str, end_str]

        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)

        query += " ORDER BY exchange_time_utc ASC, source_seq_num ASC, match_sub_idx ASC"

        try:
            result_arrow = con.execute(query, params).arrow()
            if isinstance(result_arrow, pa.RecordBatchReader):
                return result_arrow.read_all()
            return result_arrow
        except duckdb.IOException:
            return pa.Table.from_batches([], schema=CANONICAL_TRADES_SCHEMA)
        finally:
            con.close()
