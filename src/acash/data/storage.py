"""Storage engine and DuckDB point-in-time analytical query layer.

Implements:
- Partitioned immutable Parquet parts: data/parquet/{symbol}/{timeframe}/year={YYYY}/part-{batch_id}.parquet
- Strict 1:1 Ingestion Unit mapping
- Recoverable Batch Commit Protocol with Commit-Intent Manifests
- Crash recovery and quarantine for orphan parts
- DuckDB Point-in-Time qualification queries partitioned by Event Observation Key
"""

import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from acash.data.provenance import (
    BatchLifecycleStatus,
    BatchManifest,
    ProvenanceRecord,
    ProvenanceTracker,
    calculate_canonical_batch_sha256,
    calculate_canonical_content_fingerprint,
)
from acash.data.schema import (
    BatchCollisionError,
    CANONICAL_ARROW_SCHEMA,
    IntegrityViolationError,
    OrphanPartError,
)



class ParquetStorageEngine:
    """Manages append-only immutable Parquet parts and the Recoverable Batch Commit Protocol."""

    def __init__(
        self,
        base_dir: Path = Path("data/parquet"),
        manifests_dir: Path = Path("data/manifests"),
        ledger_path: Path = Path("data/provenance_ledger.jsonl"),
        quarantine_dir: Path = Path("data/quarantine"),
    ) -> None:
        self.base_dir = Path(base_dir)
        self.manifests_dir = Path(manifests_dir)
        self.ledger_path = Path(ledger_path)
        self.quarantine_dir = Path(quarantine_dir)
        self.provenance_tracker = ProvenanceTracker(
            ledger_path=self.ledger_path,
            manifests_dir=self.manifests_dir,
        )

    def get_part_file_path(self, symbol: str, timeframe: str, year: int, batch_id: str) -> Path:
        """Get canonical 1:1 part path for a given ingestion unit."""
        normalized_symbol = symbol.replace("/", "-").upper()
        return self.base_dir / normalized_symbol / timeframe.upper() / f"year={year}" / f"part-{batch_id}.parquet"

    def get_existing_revisions_lookup(
        self,
        streams: Sequence[Tuple[str, str, str]],
        exclude_batch_ids: Optional[Sequence[str]] = None,
    ) -> Dict[Tuple[str, str, str, datetime, datetime], Tuple[int, str]]:
        """Scan existing Parquet parts and build an in-memory lookup of persisted revision contents:
        (source_id, symbol, timeframe, event_start_utc, knowledge_time_utc) -> (revision_seq, canonical_content_fingerprint)
        """
        lookup: Dict[Tuple[str, str, str, datetime, datetime], Tuple[int, str]] = {}
        excluded_set = set(exclude_batch_ids or [])

        for source_id, symbol, timeframe in streams:
            normalized_symbol = symbol.replace("/", "-").upper()
            stream_dir = self.base_dir / normalized_symbol / timeframe.upper()
            if not stream_dir.exists():
                continue
            for part_path in stream_dir.glob("year=*/*.parquet"):
                if part_path.name.startswith(".tmp_"):
                    continue
                # If part belongs to an excluded batch_id, skip for lookup
                part_stem = part_path.stem
                if any(part_stem == f"part-{ex_id}" for ex_id in excluded_set):
                    continue

                try:
                    tbl = pq.read_table(
                        part_path,
                        columns=[
                            "source_id", "symbol", "timeframe",
                            "event_start_utc", "knowledge_time_utc", "revision_seq",
                            "open", "high", "low", "close", "volume", "quote_volume", "trade_count",
                        ]
                    )
                except FileNotFoundError:
                    continue
                except Exception as exc:
                    raise IntegrityViolationError(
                        f"Corrupted or unreadable canonical Parquet part at '{part_path}': {exc}"
                    ) from exc

                rows = tbl.to_pylist()
                for r in rows:
                    estart = r["event_start_utc"]
                    know = r["knowledge_time_utc"]
                    if isinstance(estart, datetime) and estart.tzinfo is None:
                        estart = estart.replace(tzinfo=timezone.utc)
                    if isinstance(know, datetime) and know.tzinfo is None:
                        know = know.replace(tzinfo=timezone.utc)

                    from decimal import Decimal
                    fp = calculate_canonical_content_fingerprint(
                        open_price=Decimal(str(r["open"])),
                        high_price=Decimal(str(r["high"])),
                        low_price=Decimal(str(r["low"])),
                        close_price=Decimal(str(r["close"])),
                        volume=Decimal(str(r["volume"])),
                        quote_volume=Decimal(str(r["quote_volume"])),
                        trade_count=int(r["trade_count"]),
                    )
                    rev_key = (
                        str(r["source_id"]),
                        str(r["symbol"]),
                        str(r["timeframe"]),
                        estart,
                        know,
                    )
                    lookup[rev_key] = (int(r["revision_seq"]), fp)
        return lookup

    def get_existing_event_max_seq(
        self,
        streams: Sequence[Tuple[str, str, str]],
        exclude_batch_ids: Optional[Sequence[str]] = None,
    ) -> Dict[Tuple[str, str, str, datetime], int]:
        """Scan existing Parquet parts and compute max revision_seq for each Event Observation.

        NOTE: Ingestion operates under the Single-Writer Invariant per (symbol, timeframe) partition.
        Concurrent multi-writer processes targeting the same partition are prohibited without an
        explicit distributed coordinator lock.
        """
        max_seq_map: Dict[Tuple[str, str, str, datetime], int] = {}
        excluded_set = set(exclude_batch_ids or [])

        for source_id, symbol, timeframe in streams:
            normalized_symbol = symbol.replace("/", "-").upper()
            stream_dir = self.base_dir / normalized_symbol / timeframe.upper()
            if not stream_dir.exists():
                continue
            for part_path in stream_dir.glob("year=*/*.parquet"):
                if part_path.name.startswith(".tmp_"):
                    continue
                part_stem = part_path.stem
                if any(part_stem == f"part-{ex_id}" for ex_id in excluded_set):
                    continue

                try:
                    tbl = pq.read_table(
                        part_path,
                        columns=[
                            "source_id", "symbol", "timeframe",
                            "event_start_utc", "revision_seq",
                        ]
                    )
                except FileNotFoundError:
                    continue
                except (pa.ArrowInvalid, pa.ArrowIOError) as exc:
                    raise IntegrityViolationError(
                        f"Corrupted or structurally invalid canonical Parquet part at '{part_path}': {exc}"
                    ) from exc

                except PermissionError as exc:
                    raise DataContractError(
                        f"Filesystem permission denied while reading canonical Parquet part at '{part_path}': {exc}"
                    ) from exc
                except Exception as exc:
                    raise IntegrityViolationError(
                        f"Unreadable canonical Parquet part at '{part_path}': {exc}"
                    ) from exc

                rows = tbl.to_pylist()
                for r in rows:
                    estart = r["event_start_utc"]
                    if isinstance(estart, datetime) and estart.tzinfo is None:
                        estart = estart.replace(tzinfo=timezone.utc)
                    event_key = (
                        str(r["source_id"]),
                        str(r["symbol"]),
                        str(r["timeframe"]),
                        estart,
                    )
                    seq_val = int(r["revision_seq"])
                    if event_key not in max_seq_map or seq_val > max_seq_map[event_key]:
                        max_seq_map[event_key] = seq_val
        return max_seq_map


    def write_canonical_part(

        self,
        table: pa.Table,
        batch_id: str,
        source_id: str,
        source_uri_or_path: str,
        raw_source_sha256: str,
        schema_version: str = "1.16.0",
        transform_version: str = "normalize_ohlcv_v1",
        validation_status: str = "VALID",
        error_count: int = 0,
        warning_count: int = 0,
    ) -> Path:
        """Execute the Recoverable Batch Commit Protocol for a canonical 1:1 ingestion unit."""
        if table.num_rows == 0:
            raise ValueError("Cannot write an empty canonical batch.")

        # Extract partition coordinates
        first_row = table.slice(0, 1).to_pylist()[0]
        symbol = str(first_row["symbol"])
        timeframe = str(first_row["timeframe"])
        event_start = first_row["event_start_utc"]
        year = event_start.year if isinstance(event_start, datetime) else 2026

        target_part_path = self.get_part_file_path(symbol, timeframe, year, batch_id)
        target_part_path.parent.mkdir(parents=True, exist_ok=True)

        # Compute logical canonical batch hash
        canonical_batch_sha256 = calculate_canonical_batch_sha256(table)

        # Check for existing committed batch (Idempotency / Collision)
        if target_part_path.exists():
            existing_table = pq.read_table(target_part_path)
            existing_hash = calculate_canonical_batch_sha256(existing_table)
            if existing_hash == canonical_batch_sha256:
                # Idempotent match: ensure provenance ledger and manifest are complete
                existing_manifest = self.provenance_tracker.load_manifest(batch_id)
                if existing_manifest is None or existing_manifest.status != BatchLifecycleStatus.COMMITTED:
                    self._reconcile_recovery_state(batch_id, target_part_path, canonical_batch_sha256)
                return target_part_path
            else:
                raise BatchCollisionError(
                    f"Batch collision for batch_id '{batch_id}' at '{target_part_path}'. "
                    f"Existing hash: {existing_hash}, incoming hash: {canonical_batch_sha256}"
                )

        now_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Step 1: Write Commit-Intent Manifest with status = PREPARED
        min_ev = min(table["event_start_utc"].to_pylist())
        max_ev = max(table["event_end_utc"].to_pylist())
        min_ev_str = min_ev.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if isinstance(min_ev, datetime) else str(min_ev)
        max_ev_str = max_ev.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if isinstance(max_ev, datetime) else str(max_ev)

        manifest = BatchManifest(
            batch_id=batch_id,
            status=BatchLifecycleStatus.PREPARED,
            source_id=source_id,
            source_uri_or_path=source_uri_or_path,
            raw_source_sha256=raw_source_sha256,
            canonical_batch_sha256=canonical_batch_sha256,
            schema_version=schema_version,
            transform_version=transform_version,
            symbol=symbol,
            timeframe=timeframe,
            year_partition=year,
            part_file_path=str(target_part_path).replace("\\", "/"),
            row_count=table.num_rows,
            min_event_time_utc=min_ev_str,
            max_event_time_utc=max_ev_str,
            created_at_utc=now_utc_str,
            updated_at_utc=now_utc_str,
        )
        self.provenance_tracker.save_manifest(manifest)

        # Step 2: Write temporary staging Parquet file
        temp_part_path = target_part_path.parent / f".tmp_part_{batch_id}_{uuid.uuid4().hex[:8]}.parquet"
        try:
            pq.write_table(
                table,
                temp_part_path,
                compression="zstd",
            )
            # Step 3: Validate staged Parquet file
            staged_table = pq.read_table(temp_part_path)
            staged_hash = calculate_canonical_batch_sha256(staged_table)
            if staged_hash != canonical_batch_sha256:
                raise IOError(f"Staged parquet corrupted: expected {canonical_batch_sha256}, got {staged_hash}")

            # Step 4: Atomically publish canonical part
            os.replace(temp_part_path, target_part_path)

        except Exception:
            if temp_part_path.exists():
                try:
                    temp_part_path.unlink()
                except Exception:
                    pass
            raise

        # Step 5: Update manifest to PART_PUBLISHED
        self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.PART_PUBLISHED)

        # Step 6: Append provenance record idempotently to JSONL
        prov_record = ProvenanceRecord(
            provenance_id=f"prov_{batch_id}",
            batch_id=batch_id,
            source_id=source_id,
            source_uri_or_path=source_uri_or_path,
            part_file_path=str(target_part_path).replace("\\", "/"),
            ingest_time_utc=now_utc_str,
            raw_source_sha256=raw_source_sha256,
            canonical_batch_sha256=canonical_batch_sha256,
            schema_version=schema_version,
            transform_version=transform_version,
            symbol=symbol,
            timeframe=timeframe,
            row_count=table.num_rows,
            min_event_time_utc=min_ev_str,
            max_event_time_utc=max_ev_str,
            validation_status=validation_status,
            error_count=error_count,
            warning_count=warning_count,
        )
        self.provenance_tracker.append_provenance_record(prov_record)

        # Step 7: Update manifest to COMMITTED
        self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.COMMITTED)

        return target_part_path

    def run_crash_recovery_pass(self) -> Dict[str, str]:
        """Scan manifests and partition directories to resolve incomplete commit states."""
        results: Dict[str, str] = {}
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

        # 1. Inspect all existing manifests
        for manifest_file in self.manifests_dir.glob("manifest-*.json"):
            batch_id = manifest_file.stem.replace("manifest-", "")
            manifest = self.provenance_tracker.load_manifest(batch_id)
            if manifest is None:
                continue

            part_path = Path(manifest.part_file_path)

            if manifest.status == BatchLifecycleStatus.COMMITTED:
                # Fully committed
                results[batch_id] = "COMMITTED"
            elif manifest.status == BatchLifecycleStatus.PART_PUBLISHED:
                # Case A or B: Check if part exists and hash matches
                if part_path.exists():
                    table = pq.read_table(part_path)
                    recomputed_hash = calculate_canonical_batch_sha256(table)
                    if recomputed_hash == manifest.canonical_batch_sha256:
                        # Reconcile provenance
                        prov_record = ProvenanceRecord(
                            provenance_id=f"prov_{batch_id}",
                            batch_id=batch_id,
                            source_id=manifest.source_id,
                            source_uri_or_path=manifest.source_uri_or_path,
                            part_file_path=manifest.part_file_path,
                            ingest_time_utc=manifest.created_at_utc,
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
                        self.provenance_tracker.append_provenance_record(prov_record)
                        self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.COMMITTED)
                        results[batch_id] = "RECOVERED_COMMITTED"
                    else:
                        results[batch_id] = "CORRUPT_PART_DETECTED"
                else:
                    results[batch_id] = "PART_MISSING"
            elif manifest.status == BatchLifecycleStatus.PREPARED:
                if part_path.exists():
                    # Part was published before status updated
                    results[batch_id] = "PREPARED_WITH_PART"
                else:
                    results[batch_id] = "CLEANED_PREPARED"

        # 2. Check for orphan Parquet parts without manifests
        for parquet_path in self.base_dir.glob("**/*.parquet"):
            if parquet_path.name.startswith("part-"):
                b_id = parquet_path.stem.replace("part-", "")
                manifest = self.provenance_tracker.load_manifest(b_id)
                prov = self.provenance_tracker.get_provenance_record(b_id)
                if manifest is None and prov is None:
                    # Quarantine orphan part
                    self.quarantine_dir.mkdir(parents=True, exist_ok=True)
                    quarantine_dest = self.quarantine_dir / parquet_path.name
                    shutil.move(str(parquet_path), str(quarantine_dest))
                    results[b_id] = "ORPHAN_QUARANTINED"

        return results

    def _reconcile_recovery_state(self, batch_id: str, part_path: Path, expected_hash: str) -> None:
        """Helper to reconcile recovery state for an existing part."""
        manifest = self.provenance_tracker.load_manifest(batch_id)
        if manifest is not None and manifest.canonical_batch_sha256 == expected_hash:
            prov = self.provenance_tracker.get_provenance_record(batch_id)
            if prov is None:
                prov_record = ProvenanceRecord(
                    provenance_id=f"prov_{batch_id}",
                    batch_id=batch_id,
                    source_id=manifest.source_id,
                    source_uri_or_path=manifest.source_uri_or_path,
                    part_file_path=str(part_path).replace("\\", "/"),
                    ingest_time_utc=manifest.created_at_utc,
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
                self.provenance_tracker.append_provenance_record(prov_record)
            self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.COMMITTED)


class DuckDBStorage:
    """Analytical Point-in-Time query layer executing over immutable Parquet parts."""

    def __init__(self, base_dir: Path = Path("data/parquet")) -> None:
        self.base_dir = Path(base_dir)

    def query_point_in_time(
        self,
        symbol: str,
        timeframe: str,
        as_of_knowledge_time_utc: datetime,
        start_utc: Optional[datetime] = None,
        end_utc: Optional[datetime] = None,
    ) -> pa.Table:
        """Execute Point-in-Time qualification query selecting authoritative revisions as of T_as_of.

        Query Standard:
        PARTITION BY source_id, symbol, timeframe, event_start_utc
        ORDER BY knowledge_time_utc DESC, revision_seq DESC
        """
        normalized_symbol = symbol.replace("/", "-").upper()
        glob_path = str(self.base_dir / normalized_symbol / timeframe.upper() / "**" / "*.parquet").replace("\\", "/")

        # Check if any parquet files exist matching the glob
        matching_files = list(self.base_dir.glob(f"{normalized_symbol}/{timeframe.upper()}/**/*.parquet"))
        if not matching_files:
            # Return empty Arrow table with canonical schema
            return pa.Table.from_batches([], schema=CANONICAL_ARROW_SCHEMA)

        # Normalize datetimes to UTC ISO
        def to_iso(dt: datetime) -> str:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")

        as_of_str = to_iso(as_of_knowledge_time_utc)

        where_clauses = ["knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)"]
        params: List[Any] = [as_of_str]

        if start_utc is not None:
            where_clauses.append("event_start_utc >= CAST(? AS TIMESTAMPTZ)")
            params.append(to_iso(start_utc))
        if end_utc is not None:
            where_clauses.append("event_end_utc <= CAST(? AS TIMESTAMPTZ)")
            params.append(to_iso(end_utc))

        where_sql = " AND ".join(where_clauses)

        sql = f"""
        WITH eligible_revisions AS (
            SELECT *
            FROM read_parquet('{glob_path}')
            WHERE {where_sql}
        )
        SELECT *
        FROM eligible_revisions
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY source_id, symbol, timeframe, event_start_utc
            ORDER BY knowledge_time_utc DESC, revision_seq DESC
        ) = 1
        ORDER BY source_id ASC, event_start_utc ASC;
        """

        con = duckdb.connect()
        try:
            arrow_res = con.execute(sql, params).to_arrow_table()
            return arrow_res
        finally:
            con.close()
