"""Provenance tracking, logical data hashing, and commit-intent manifest engine.

Implements:
- raw_source_sha256 (SHA-256 over raw input payload bytes)
- canonical_content_fingerprint (deterministic SHA-256 over canonical revision fields)
- canonical_batch_sha256 (file-layout invariant logical hash over canonical columns sorted by Revision Identity)
- Recoverable Batch Commit Protocol with durable Manifest Lifecycle States (PREPARED -> PART_PUBLISHED -> COMMITTED)
- Idempotent append-only JSONL provenance ledger
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Sequence
import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field

from acash.data.schema import (
    BatchCollisionError,
    CANONICAL_COLUMN_NAMES,
)


class BatchLifecycleStatus(str, Enum):
    """Durable lifecycle states for the Commit-Intent Manifest."""
    PREPARED = "PREPARED"
    PART_PUBLISHED = "PART_PUBLISHED"
    COMMITTED = "COMMITTED"


class BatchManifest(BaseModel):
    """Durable commit-intent manifest storing complete recovery metadata."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    batch_id: str
    status: BatchLifecycleStatus
    source_id: str
    source_uri_or_path: str
    raw_source_sha256: str
    canonical_batch_sha256: str
    schema_version: str
    transform_version: str
    symbol: str
    timeframe: str
    year_partition: int
    part_file_path: str
    row_count: int
    min_event_time_utc: str
    max_event_time_utc: str
    created_at_utc: str
    updated_at_utc: str


class ProvenanceRecord(BaseModel):
    """Immutable audit record appended to the JSONL provenance ledger."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    provenance_id: str
    batch_id: str
    source_id: str
    source_uri_or_path: str
    part_file_path: str
    ingest_time_utc: str
    raw_source_sha256: str
    canonical_batch_sha256: str
    schema_version: str
    transform_version: str
    symbol: str
    timeframe: str
    row_count: int
    min_event_time_utc: str
    max_event_time_utc: str
    validation_status: str
    error_count: int = 0
    warning_count: int = 0


def calculate_raw_source_sha256(raw_bytes: bytes) -> str:
    """Calculate SHA-256 hash over raw input payload bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()


def calculate_canonical_content_fingerprint(
    open_price: Decimal,
    high_price: Decimal,
    low_price: Decimal,
    close_price: Decimal,
    volume: Decimal,
    quote_volume: Decimal,
    trade_count: int,
) -> str:
    """Calculate deterministic SHA-256 fingerprint over canonical revision fields.

    Used strictly as an intra-batch tie-breaker for newly accepted revisions sharing
    the same knowledge_time_utc in the same acceptance operation.
    """
    hasher = hashlib.sha256()
    # Normalize decimals to 18 scale fixed decimal strings
    for dec in (open_price, high_price, low_price, close_price, volume, quote_volume):
        norm_str = f"{dec:.18f}".encode("utf-8")
        hasher.update(norm_str)
        hasher.update(b"|")
    hasher.update(str(trade_count).encode("utf-8"))
    return hasher.hexdigest()


def calculate_canonical_batch_sha256(table: pa.Table) -> str:
    """Calculate deterministic logical canonical batch SHA-256 hash.

    Invariant Rules:
    1. Sorts all rows strictly by Revision Identity:
       (source_id, symbol, timeframe, event_start_utc, knowledge_time_utc, revision_seq)
    2. Encodes each canonical column in fixed binary representation.
    3. Independent of Parquet compression, page/chunk layout, row group boundaries,
       or input row ordering.
    """
    if table.num_rows == 0:
        return hashlib.sha256(b"EMPTY_TABLE").hexdigest()

    # Fail-fast if any canonical schema columns are missing
    missing_columns = [col for col in CANONICAL_COLUMN_NAMES if col not in table.column_names]
    if missing_columns:
        from acash.data.schema import DataContractError
        raise DataContractError(
            f"Cannot compute canonical batch hash: table is missing required canonical columns: {missing_columns}"
        )

    # Sort table strictly by Revision Identity
    sort_keys = [
        ("source_id", "ascending"),
        ("symbol", "ascending"),
        ("timeframe", "ascending"),
        ("event_start_utc", "ascending"),
        ("knowledge_time_utc", "ascending"),
        ("revision_seq", "ascending"),
    ]
    sorted_table = table.sort_by(sort_keys)

    hasher = hashlib.sha256()

    # Extract columns in canonical order
    source_ids = sorted_table["source_id"].to_pylist()
    symbols = sorted_table["symbol"].to_pylist()
    timeframes = sorted_table["timeframe"].to_pylist()
    event_starts = sorted_table["event_start_utc"].to_pylist()
    event_ends = sorted_table["event_end_utc"].to_pylist()
    knowledge_times = sorted_table["knowledge_time_utc"].to_pylist()
    revision_seqs = sorted_table["revision_seq"].to_pylist()
    opens = sorted_table["open"].to_pylist()
    highs = sorted_table["high"].to_pylist()
    lows = sorted_table["low"].to_pylist()
    closes = sorted_table["close"].to_pylist()
    volumes = sorted_table["volume"].to_pylist()
    quote_volumes = sorted_table["quote_volume"].to_pylist()
    trade_counts = sorted_table["trade_count"].to_pylist()

    num_rows = sorted_table.num_rows
    for i in range(num_rows):
        # Format timestamps in UTC ISO microseconds
        def ts_to_bytes(ts: Any) -> bytes:
            if isinstance(ts, datetime):
                dt_utc: datetime = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
                ts_str: str = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                return ts_str.encode("utf-8")
            return str(ts).encode("utf-8")

        # Format Decimals to fixed 18 scale
        def dec_to_bytes(dec: Any) -> bytes:
            if isinstance(dec, Decimal):
                dec_str: str = f"{dec:.18f}"
                return dec_str.encode("utf-8")
            return str(dec).encode("utf-8")


        row_payload = b":".join([
            str(source_ids[i]).encode("utf-8"),
            str(symbols[i]).encode("utf-8"),
            str(timeframes[i]).encode("utf-8"),
            ts_to_bytes(event_starts[i]),
            ts_to_bytes(event_ends[i]),
            ts_to_bytes(knowledge_times[i]),
            str(revision_seqs[i]).encode("utf-8"),
            dec_to_bytes(opens[i]),
            dec_to_bytes(highs[i]),
            dec_to_bytes(lows[i]),
            dec_to_bytes(closes[i]),
            dec_to_bytes(volumes[i]),
            dec_to_bytes(quote_volumes[i]),
            str(trade_counts[i]).encode("utf-8"),
        ])
        hasher.update(row_payload)
        hasher.update(b"\n")

    return hasher.hexdigest()


class ProvenanceTracker:
    """Manages Commit-Intent Manifests and the append-only JSONL Provenance Ledger."""

    def __init__(
        self,
        ledger_path: Path = Path("data/provenance_ledger.jsonl"),
        manifests_dir: Path = Path("data/manifests"),
    ) -> None:
        self.ledger_path = Path(ledger_path)
        self.manifests_dir = Path(manifests_dir)

    def ensure_directories(self) -> None:
        """Ensure storage and manifests parent directories exist."""
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

    def get_manifest_path(self, batch_id: str) -> Path:
        """Get canonical file path for a batch's commit-intent manifest."""
        return self.manifests_dir / f"manifest-{batch_id}.json"

    def save_manifest(self, manifest: BatchManifest) -> Path:
        """Save a Commit-Intent Manifest atomically using staging file + fsync + os.replace."""
        self.ensure_directories()
        target_path = self.get_manifest_path(manifest.batch_id)
        temp_path = self.manifests_dir / f".tmp_manifest_{manifest.batch_id}_{os.getpid()}.json"

        manifest_data = manifest.model_dump(mode="json")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, target_path)
        return target_path

    def load_manifest(self, batch_id: str) -> Optional[BatchManifest]:
        """Load an existing Commit-Intent Manifest by batch_id."""
        manifest_path = self.get_manifest_path(batch_id)
        if not manifest_path.exists():
            return None
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return BatchManifest.model_validate(data)

    def update_manifest_status(
        self, batch_id: str, new_status: BatchLifecycleStatus
    ) -> BatchManifest:
        """Atomically transition a manifest to a new lifecycle status."""
        manifest = self.load_manifest(batch_id)
        if manifest is None:
            raise KeyError(f"Manifest for batch_id {batch_id} not found.")

        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        updated_dict = manifest.model_dump()
        updated_dict["status"] = new_status
        updated_dict["updated_at_utc"] = now_utc

        updated_manifest = BatchManifest.model_validate(updated_dict)
        self.save_manifest(updated_manifest)
        return updated_manifest

    def append_provenance_record(self, record: ProvenanceRecord) -> None:
        """Idempotently append a provenance audit record to the JSONL ledger.

        If a record with matching batch_id already exists:
        - If canonical_batch_sha256 matches: safe no-op.
        - If canonical_batch_sha256 differs: raises BatchCollisionError.
        """
        self.ensure_directories()

        # Check existing records for idempotency / collision
        existing_records = self.read_provenance_records()
        for existing in existing_records:
            if existing.batch_id == record.batch_id:
                if existing.canonical_batch_sha256 == record.canonical_batch_sha256:
                    # Idempotent match - do not duplicate
                    return
                else:
                    raise BatchCollisionError(
                        f"Batch collision detected for batch_id '{record.batch_id}'. "
                        f"Existing hash: {existing.canonical_batch_sha256}, incoming hash: {record.canonical_batch_sha256}"
                    )

        # Append new record
        line = record.model_dump_json() + "\n"
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    def read_provenance_records(self) -> list[ProvenanceRecord]:
        """Read all provenance records from the JSONL ledger."""
        if not self.ledger_path.exists():
            return []

        records: list[ProvenanceRecord] = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(ProvenanceRecord.model_validate_json(line))
        return records

    def get_provenance_record(self, batch_id: str) -> Optional[ProvenanceRecord]:
        """Retrieve the provenance record for a specific batch_id if it exists."""
        for record in self.read_provenance_records():
            if record.batch_id == batch_id:
                return record
        return None
