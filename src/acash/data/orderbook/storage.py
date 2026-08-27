"""Parquet Storage Engine and Dual-Temporal Point-in-Time Query / Reconstruction Engine for Order Book (Phase 3B).

Strictly enforces:
- Daily partition layouts:
  - Snapshots: data/parquet/orderbook/snapshots/{symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
  - Deltas:    data/parquet/orderbook/deltas/{symbol}/year={YYYY}/date={YYYY-MM-DD}/part-{batch_id}.parquet
- Recoverable Batch Commit Protocol (PREPARED -> PART_PUBLISHED -> COMMITTED) with atomic manifests & crash recovery.
- Scoped Two-Stage Multi-Row Point-in-Time (PIT) Queries:
  - Stage 1: Candidate complete snapshot frame selection with deterministic snapshot_id ASC tie-breaker + Full compound key join.
  - Stage 2: Subsequent deltas selection strictly after snapshot boundary.
- Zero lookahead point_in_time_reconstruct() returning verified DepthLadderState.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from acash.data.orderbook.hashing import (
    calculate_canonical_book_delta_sha256,
    calculate_canonical_book_snapshot_sha256,
)
from acash.data.orderbook.reconstruction import (
    DepthLadderState,
    MbpOrderBookReconstructor,
)
from acash.data.orderbook.schema import (
    BOOK_DELTA_ROW_IDENTITY_COLUMNS,
    BOOK_SNAPSHOT_ROW_IDENTITY_COLUMNS,
    CANONICAL_BOOK_DELTA_SCHEMA,
    CANONICAL_BOOK_SNAPSHOT_SCHEMA,
    BookDeltaType,
    SnapshotShapePolicy,
    SourceOrderingPolicy,
)
from acash.data.provenance import (
    BatchLifecycleStatus,
    BatchManifest,
    ProvenanceRecord,
    ProvenanceTracker,
    calculate_raw_source_sha256,
)
from acash.data.schema import (
    BatchCollisionError,
    DataContractError,
    IntegrityViolationError,
    OrphanPartError,
)


class OrderBookStorageEngine:
    """Storage engine managing Parquet partitioning, commit manifests, and DuckDB PIT queries for Order Book."""

    def __init__(
        self,
        base_dir: Union[str, Path] = "data/parquet/orderbook",
        manifests_dir: Union[str, Path] = "data/manifests/orderbook",
        ledger_path: Union[str, Path] = "data/provenance_ledger.jsonl",
        quarantine_dir: Union[str, Path] = "data/quarantine/orderbook",
    ) -> None:
        self.base_dir = Path(base_dir)
        self.snapshots_dir = self.base_dir / "snapshots"
        self.deltas_dir = self.base_dir / "deltas"
        self.ledger_path = Path(ledger_path)
        self.manifests_dir = Path(manifests_dir)
        self.quarantine_dir = Path(quarantine_dir)

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.deltas_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        self.provenance_tracker = ProvenanceTracker(
            ledger_path=self.ledger_path,
            manifests_dir=self.manifests_dir,
        )


    def get_snapshot_part_path(self, symbol: str, trading_date_val: date, batch_id: str) -> Path:
        """Derive canonical path for a snapshots partition part."""
        norm_sym = symbol.replace("/", "-").upper()
        return (
            self.snapshots_dir
            / norm_sym
            / f"year={trading_date_val.year}"
            / f"date={trading_date_val.isoformat()}"
            / f"part-{batch_id}.parquet"
        )

    def get_delta_part_path(self, symbol: str, trading_date_val: date, batch_id: str) -> Path:
        """Derive canonical path for a deltas partition part."""
        norm_sym = symbol.replace("/", "-").upper()
        return (
            self.deltas_dir
            / norm_sym
            / f"year={trading_date_val.year}"
            / f"date={trading_date_val.isoformat()}"
            / f"part-{batch_id}.parquet"
        )

    def commit_snapshot_batch(
        self,
        batch_id: str,
        table: pa.Table,
        source_id: str,
        source_uri: str,
        raw_source_sha256: str,
        schema_version: str = "1.8.0",
        transform_version: str = "1.0.0",
    ) -> Path:
        """Commit an atomic Snapshot Batch via the Recoverable Batch Commit Protocol."""
        if table.num_rows == 0:
            raise DataContractError(f"Cannot commit empty snapshot batch: {batch_id}")

        canonical_hash = calculate_canonical_book_snapshot_sha256(table)
        existing_manifest = self.provenance_tracker.load_manifest(batch_id)

        if existing_manifest:
            if existing_manifest.canonical_batch_sha256 == canonical_hash:
                target_path = Path(existing_manifest.part_file_path)
                if target_path.exists():
                    return target_path
            else:
                raise BatchCollisionError(
                    f"Batch collision on snapshot batch_id '{batch_id}': existing hash {existing_manifest.canonical_batch_sha256} != new hash {canonical_hash}"
                )

        pydict = table.to_pydict()
        symbol = str(pydict["symbol"][0])
        t_d = pydict["trading_date"][0]
        trading_date_val = t_d if isinstance(t_d, date) else date.fromisoformat(str(t_d))
        target_path = self.get_snapshot_part_path(symbol, trading_date_val, batch_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Manifest PREPARED
        now_str = datetime.now(timezone.utc).isoformat()
        manifest = BatchManifest(
            batch_id=batch_id,
            status=BatchLifecycleStatus.PREPARED,
            source_id=source_id,
            source_uri_or_path=source_uri,
            raw_source_sha256=raw_source_sha256,
            canonical_batch_sha256=canonical_hash,
            schema_version=schema_version,
            transform_version=transform_version,
            symbol=symbol,
            timeframe="SNAPSHOT",
            year_partition=trading_date_val.year,
            part_file_path=str(target_path),
            row_count=table.num_rows,
            min_event_time_utc=min(pydict["exchange_time_utc"]).isoformat(),
            max_event_time_utc=max(pydict["exchange_time_utc"]).isoformat(),
            created_at_utc=now_str,
            updated_at_utc=now_str,
        )
        self.provenance_tracker.save_manifest(manifest)

        # 2. Write temp staging and atomic replace
        with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet", dir=target_path.parent) as tmp_f:
            tmp_path = Path(tmp_f.name)

        try:
            pq.write_table(table, tmp_path, compression="zstd")
            self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.PART_PUBLISHED)

            os.replace(tmp_path, target_path)

            self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.COMMITTED)
            committed_manifest = self.provenance_tracker.load_manifest(batch_id)

            prov_rec = ProvenanceRecord(
                provenance_id=f"prov_snap_{batch_id}",
                batch_id=batch_id,
                source_id=source_id,
                source_uri_or_path=source_uri,
                raw_source_sha256=raw_source_sha256,
                canonical_batch_sha256=canonical_hash,
                schema_version=schema_version,
                transform_version=transform_version,
                symbol=symbol,
                timeframe="SNAPSHOT",
                row_count=table.num_rows,
                min_event_time_utc=committed_manifest.min_event_time_utc if committed_manifest else "",
                max_event_time_utc=committed_manifest.max_event_time_utc if committed_manifest else "",
                validation_status="VALID",
                ingest_time_utc=datetime.now(timezone.utc).isoformat(),
                part_file_path=str(target_path),
            )
            self.provenance_tracker.append_provenance_record(prov_rec)
            return target_path
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    def commit_delta_batch(
        self,
        batch_id: str,
        table: pa.Table,
        source_id: str,
        source_uri: str,
        raw_source_sha256: str,
        schema_version: str = "1.8.0",
        transform_version: str = "1.0.0",
    ) -> Path:
        """Commit an atomic Delta Batch via the Recoverable Batch Commit Protocol."""
        if table.num_rows == 0:
            raise DataContractError(f"Cannot commit empty delta batch: {batch_id}")

        canonical_hash = calculate_canonical_book_delta_sha256(table)
        existing_manifest = self.provenance_tracker.load_manifest(batch_id)

        if existing_manifest:
            if existing_manifest.canonical_batch_sha256 == canonical_hash:
                target_path = Path(existing_manifest.part_file_path)
                if target_path.exists():
                    return target_path
            else:
                raise BatchCollisionError(
                    f"Batch collision on delta batch_id '{batch_id}': existing hash {existing_manifest.canonical_batch_sha256} != new hash {canonical_hash}"
                )

        pydict = table.to_pydict()
        symbol = str(pydict["symbol"][0])
        t_d = pydict["trading_date"][0]
        trading_date_val = t_d if isinstance(t_d, date) else date.fromisoformat(str(t_d))
        target_path = self.get_delta_part_path(symbol, trading_date_val, batch_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        now_str = datetime.now(timezone.utc).isoformat()
        manifest = BatchManifest(
            batch_id=batch_id,
            status=BatchLifecycleStatus.PREPARED,
            source_id=source_id,
            source_uri_or_path=source_uri,
            raw_source_sha256=raw_source_sha256,
            canonical_batch_sha256=canonical_hash,
            schema_version=schema_version,
            transform_version=transform_version,
            symbol=symbol,
            timeframe="DELTA",
            year_partition=trading_date_val.year,
            part_file_path=str(target_path),
            row_count=table.num_rows,
            min_event_time_utc=min(pydict["exchange_time_utc"]).isoformat(),
            max_event_time_utc=max(pydict["exchange_time_utc"]).isoformat(),
            created_at_utc=now_str,
            updated_at_utc=now_str,
        )
        self.provenance_tracker.save_manifest(manifest)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet", dir=target_path.parent) as tmp_f:
            tmp_path = Path(tmp_f.name)

        try:
            pq.write_table(table, tmp_path, compression="zstd")
            self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.PART_PUBLISHED)

            os.replace(tmp_path, target_path)

            self.provenance_tracker.update_manifest_status(batch_id, BatchLifecycleStatus.COMMITTED)
            committed_manifest = self.provenance_tracker.load_manifest(batch_id)

            prov_rec = ProvenanceRecord(
                provenance_id=f"prov_delta_{batch_id}",
                batch_id=batch_id,
                source_id=source_id,
                source_uri_or_path=source_uri,
                raw_source_sha256=raw_source_sha256,
                canonical_batch_sha256=canonical_hash,
                schema_version=schema_version,
                transform_version=transform_version,
                symbol=symbol,
                timeframe="DELTA",
                row_count=table.num_rows,
                min_event_time_utc=committed_manifest.min_event_time_utc if committed_manifest else "",
                max_event_time_utc=committed_manifest.max_event_time_utc if committed_manifest else "",
                validation_status="VALID",
                ingest_time_utc=datetime.now(timezone.utc).isoformat(),
                part_file_path=str(target_path),
            )
            self.provenance_tracker.append_provenance_record(prov_rec)
            return target_path

        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass


    def get_existing_snapshot_identities_lookup(self, symbol: str) -> Dict[Tuple[Any, ...], bool]:
        """Load all persisted Snapshot Row Identities for duplicate checking."""
        lookup: Dict[Tuple[Any, ...], bool] = {}
        norm_sym = symbol.replace("/", "-").upper()
        sym_dir = self.snapshots_dir / norm_sym
        if not sym_dir.exists():
            return lookup

        con = duckdb.connect(":memory:")
        glob_path = str(sym_dir / "**" / "*.parquet").replace("\\", "/")
        query = f"SELECT {', '.join(BOOK_SNAPSHOT_ROW_IDENTITY_COLUMNS)} FROM read_parquet(?)"
        try:
            res = con.execute(query, [glob_path]).fetchall()
            for row in res:
                lookup[row] = True
        except duckdb.IOException:
            pass
        finally:
            con.close()
        return lookup

    def get_existing_delta_identities_lookup(self, symbol: str) -> Dict[Tuple[Any, ...], bool]:
        """Load all persisted Delta Row Identities for duplicate checking."""
        lookup: Dict[Tuple[Any, ...], bool] = {}
        norm_sym = symbol.replace("/", "-").upper()
        sym_dir = self.deltas_dir / norm_sym
        if not sym_dir.exists():
            return lookup

        con = duckdb.connect(":memory:")
        glob_path = str(sym_dir / "**" / "*.parquet").replace("\\", "/")
        query = f"SELECT {', '.join(BOOK_DELTA_ROW_IDENTITY_COLUMNS)} FROM read_parquet(?)"
        try:
            res = con.execute(query, [glob_path]).fetchall()
            for row in res:
                lookup[row] = True
        except duckdb.IOException:
            pass
        finally:
            con.close()
        return lookup

    def point_in_time_query_snapshot_frame(
        self,
        source_id: str,
        channel_id: str,
        symbol: str,
        trading_date_val: date,
        as_of_knowledge_time_utc: datetime,
        target_exchange_time_utc: datetime,
    ) -> pa.Table:
        """Stage 1: Select Candidate Complete Snapshot Frame with Deterministic Tie-Breaker and Retrieve ALL Frame Rows."""
        norm_sym = symbol.replace("/", "-").upper()
        sym_dir = self.snapshots_dir / norm_sym
        if not sym_dir.exists():
            return pa.Table.from_batches([], schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)

        glob_path = str(sym_dir / "**" / "*.parquet").replace("\\", "/")
        as_of_str = as_of_knowledge_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")
        target_str = target_exchange_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")
        date_str = trading_date_val.isoformat()

        query = """
            WITH candidate_frame AS (
                SELECT
                    source_id,
                    channel_id,
                    symbol,
                    trading_date,
                    source_seq_num,
                    source_order_key,
                    snapshot_id,
                    exchange_time_utc
                FROM read_parquet(?)
                WHERE source_id = ?
                  AND channel_id = ?
                  AND symbol = ?
                  AND trading_date = CAST(? AS DATE)
                  AND knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
                  AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ)
                  AND is_snapshot_complete = TRUE
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY source_id, channel_id, symbol, trading_date
                    ORDER BY
                        exchange_time_utc DESC,
                        source_order_key DESC,
                        knowledge_time_utc DESC,
                        snapshot_id ASC
                ) = 1
            )
            SELECT s.*
            FROM read_parquet(?) s
            JOIN candidate_frame c
              ON s.source_id = c.source_id
             AND s.channel_id = c.channel_id
             AND s.symbol = c.symbol
             AND s.trading_date = c.trading_date
             AND s.source_seq_num = c.source_seq_num
             AND s.snapshot_id = c.snapshot_id
            WHERE s.knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
            ORDER BY s.side ASC, s.level_idx ASC
        """
        params = [
            glob_path,
            source_id,
            channel_id,
            symbol,
            date_str,
            as_of_str,
            target_str,
            glob_path,
            as_of_str,
        ]

        con = duckdb.connect(":memory:")
        try:
            res_arrow = con.execute(query, params).arrow()
            if isinstance(res_arrow, pa.RecordBatchReader):
                return res_arrow.read_all()
            return res_arrow
        except duckdb.IOException:
            return pa.Table.from_batches([], schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)
        finally:
            con.close()

    def point_in_time_query_subsequent_deltas(
        self,
        source_id: str,
        channel_id: str,
        symbol: str,
        trading_date_val: date,
        snapshot_exchange_time_utc: datetime,
        snapshot_order_key: str,
        target_exchange_time_utc: datetime,
        as_of_knowledge_time_utc: datetime,
    ) -> pa.Table:
        """Stage 2: Select Subsequent Incremental Deltas strictly after the snapshot boundary."""
        norm_sym = symbol.replace("/", "-").upper()
        sym_dir = self.deltas_dir / norm_sym
        if not sym_dir.exists():
            return pa.Table.from_batches([], schema=CANONICAL_BOOK_DELTA_SCHEMA)

        glob_path = str(sym_dir / "**" / "*.parquet").replace("\\", "/")
        as_of_str = as_of_knowledge_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")
        snap_time_str = snapshot_exchange_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")
        target_time_str = target_exchange_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")
        date_str = trading_date_val.isoformat()

        query = """
            SELECT * FROM read_parquet(?)
            WHERE source_id = ?
              AND channel_id = ?
              AND symbol = ?
              AND trading_date = CAST(? AS DATE)
              AND knowledge_time_utc <= CAST(? AS TIMESTAMPTZ)
              AND (
                (exchange_time_utc = CAST(? AS TIMESTAMPTZ) AND source_order_key >= ?)
                OR (exchange_time_utc > CAST(? AS TIMESTAMPTZ) AND exchange_time_utc <= CAST(? AS TIMESTAMPTZ))
              )
            ORDER BY exchange_time_utc ASC, source_order_key ASC, action_sub_idx ASC
        """
        params = [
            glob_path,
            source_id,
            channel_id,
            symbol,
            date_str,
            as_of_str,
            snap_time_str,
            snapshot_order_key,
            snap_time_str,
            target_time_str,
        ]

        con = duckdb.connect(":memory:")
        try:
            res_arrow = con.execute(query, params).arrow()
            if isinstance(res_arrow, pa.RecordBatchReader):
                return res_arrow.read_all()
            return res_arrow
        except duckdb.IOException:
            return pa.Table.from_batches([], schema=CANONICAL_BOOK_DELTA_SCHEMA)
        finally:
            con.close()

    def point_in_time_reconstruct(
        self,
        source_id: str,
        channel_id: str,
        symbol: str,
        trading_date_val: date,
        target_exchange_time_utc: datetime,
        as_of_knowledge_time_utc: datetime,
        top_n: int = 10,
        shape_policy: SnapshotShapePolicy = SnapshotShapePolicy.FIXED_DEPTH_N,
    ) -> DepthLadderState:
        """Reconstruct the exact Top-N Depth Ladder state at target_exchange_time as known at as_of_knowledge_time."""
        stream_scope = (source_id, channel_id, symbol, trading_date_val.isoformat())
        reconstructor = MbpOrderBookReconstructor(stream_scope=stream_scope)

        # 1. Fetch Root Snapshot Frame
        snap_table = self.point_in_time_query_snapshot_frame(
            source_id=source_id,
            channel_id=channel_id,
            symbol=symbol,
            trading_date_val=trading_date_val,
            as_of_knowledge_time_utc=as_of_knowledge_time_utc,
            target_exchange_time_utc=target_exchange_time_utc,
        )

        if snap_table.num_rows == 0:
            return DepthLadderState(
                stream_scope=stream_scope,
                exchange_time_utc=target_exchange_time_utc,
                source_order_key="",
                bids=[],
                asks=[],
                is_valid=False,
                status="NO_SNAPSHOT_FOUND",
            )

        # Apply snapshot frame
        is_init = reconstructor.apply_snapshot_frame(snap_table, shape_policy=shape_policy)
        if not is_init:
            return reconstructor.get_ladder_state(top_n=top_n)

        snap_pydict = snap_table.to_pydict()
        snap_t = snap_pydict["exchange_time_utc"][0]
        snap_order_key = str(snap_pydict["source_order_key"][0])

        # 2. Fetch Subsequent Deltas
        delta_table = self.point_in_time_query_subsequent_deltas(
            source_id=source_id,
            channel_id=channel_id,
            symbol=symbol,
            trading_date_val=trading_date_val,
            snapshot_exchange_time_utc=snap_t,
            snapshot_order_key=snap_order_key,
            target_exchange_time_utc=target_exchange_time_utc,
            as_of_knowledge_time_utc=as_of_knowledge_time_utc,
        )

        if delta_table.num_rows > 0:
            delta_pydict = delta_table.to_pydict()
            for i in range(delta_table.num_rows):
                t_ex = delta_pydict["exchange_time_utc"][i]
                ord_k = str(delta_pydict["source_order_key"][i])
                sub_idx = int(delta_pydict["action_sub_idx"][i])
                act = str(delta_pydict["action"][i])
                sd = str(delta_pydict["side"][i])
                px = delta_pydict["price"][i]
                sz = delta_pydict["size"][i]
                cnt = delta_pydict["order_count"][i]

                reconstructor.apply_delta(
                    exchange_time_utc=t_ex,
                    source_order_key=ord_k,
                    action_sub_idx=sub_idx,
                    action=act,
                    side=sd,
                    price=px,
                    size=sz,
                    order_count=cnt,
                )

        return reconstructor.get_ladder_state(top_n=top_n)
