"""PPDS synthetic statement import provenance integration with Evidence Plane."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol, Sequence, Tuple, runtime_checkable

from acash.core.domain.exceptions import DataContractError
from acash.core.runtime_identity import get_current_runtime_sha
from acash.evidence import (
    RetrievalPageRecord,
    RetrievalRunManifest,
    ordered_page_chain_digest,
    validate_external_evidence_root,
    write_immutable_bytes,
)
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.reconcile import ReconciliationResult, reconcile_snapshot_ledger
from acash.ppds.statement_ingest import AccountSnapshot, ingest_account_snapshot, parse_statement_csv


@runtime_checkable
class BrokerStatementAdapter(Protocol):
    """Generic protocol for broker-neutral statement parsers."""

    @property
    def adapter_id(self) -> str:
        """Unique authoritative identifier of this parser adapter."""
        ...

    def parse(self, raw_bytes: bytes) -> Sequence[Mapping[str, Any]]:
        """Parse raw statement payload bytes into normalized row mappings."""
        ...


class SyntheticCsvStatementAdapter:
    """Canonical synthetic reference adapter for comma-separated statement files."""

    adapter_id: str = "SYNTHETIC_CSV_REFERENCE_V1"

    def parse(self, raw_bytes: bytes) -> Sequence[Mapping[str, Any]]:
        if not isinstance(raw_bytes, (bytes, bytearray)):
            raise DataContractError(
                f"PPDS_ADAPTER_INVALID_BYTES: expected bytes, got {type(raw_bytes).__name__}."
            )
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DataContractError(f"PPDS_ADAPTER_DECODE_ERROR: UTF-8 decode failed: {exc}.") from exc

        return parse_statement_csv(text)


@dataclass(frozen=True)
class ProvenanceBoundLot:
    """A financial lot bound cryptographically to its raw ingestion provenance."""

    source_id: str
    as_of: date
    source_sha256: str
    lot: Any


@dataclass(frozen=True)
class ImportedStatementRecord:
    """Complete provenance envelope for an ingested synthetic statement."""

    source_id: str
    as_of: date
    raw_content_sha256: str
    manifest_sha256: str
    adapter_id: str
    snapshot: AccountSnapshot
    ledger: NormalizedPortfolioLedger
    reconciliation: ReconciliationResult
    evidence_path: Path
    bound_cash_lots: Tuple[ProvenanceBoundLot, ...]
    bound_position_lots: Tuple[ProvenanceBoundLot, ...]


def import_synthetic_statement(
    raw_bytes: bytes,
    source_id: str,
    as_of: date,
    evidence_root: Path,
    adapter: Optional[BrokerStatementAdapter] = None,
    imported_at_utc: Optional[datetime] = None,
    runtime_sha: Optional[str] = None,
) -> ImportedStatementRecord:
    """Import raw synthetic statement bytes into immutable Evidence Plane and normalize.

    Pipeline:
    1. Validate external evidence root (fail-closed against repo-local and HYP_011).
    2. Write raw payload immutably to Evidence Plane (never overwrite).
    3. Parse rows using adapter (Protocol-based, synthetic only).
    4. Normalize into AccountSnapshot and post sequentially to NormalizedPortfolioLedger.
    5. Reconcile snapshot against ledger (exact equality required).
    6. Seal provenance manifest immutably using neutral Evidence Plane V1.1 RetrievalRunManifest.
    """
    if not isinstance(raw_bytes, (bytes, bytearray)) or not raw_bytes:
        raise DataContractError("PPDS_IMPORT_EMPTY_BYTES: raw statement content is empty.")

    if not source_id or "/" in source_id or "\\" in source_id:
        raise DataContractError(f"PPDS_IMPORT_INVALID_SOURCE_ID: '{source_id}'.")

    if not isinstance(as_of, date):
        raise DataContractError(f"PPDS_IMPORT_INVALID_DATE: expected date, got {type(as_of)}.")

    validated_root = validate_external_evidence_root(evidence_root)
    active_adapter = adapter or SyntheticCsvStatementAdapter()
    now_utc = imported_at_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        raise DataContractError("PPDS_IMPORT_NAIVE_TIMESTAMP.")

    target_dir = validated_root / "ppds" / as_of.isoformat() / source_id
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_file = target_dir / "statement.raw"

    # Step 2: Write raw statement bytes immutably
    raw_sha = write_immutable_bytes(raw_file, bytes(raw_bytes))

    # Step 3: Parse via adapter
    rows = active_adapter.parse(bytes(raw_bytes))
    if not rows:
        raise DataContractError("PPDS_IMPORT_NO_DATA_ROWS.")

    # Step 4: Normalize lots and build snapshot
    snapshot = ingest_account_snapshot(rows, as_of)

    # Step 5: Post lots to normalized ledger
    ledger = NormalizedPortfolioLedger()
    for cash_lot in snapshot.cash_lots:
        ledger = ledger.post_cash_lot(cash_lot)
    for pos_lot in snapshot.position_lots:
        ledger = ledger.post_position_lot(pos_lot)

    # Step 6: Exact reconciliation
    reconciliation = reconcile_snapshot_ledger(snapshot, ledger)
    if not reconciliation.matched:
        raise DataContractError(
            f"PPDS_IMPORT_RECONCILIATION_FAILED: breaks={reconciliation.breaks}."
        )

    # Step 7: Seal provenance run manifest in Evidence Plane V1.1
    current_sha = runtime_sha or get_current_runtime_sha()
    page_rec = RetrievalPageRecord(
        page_index=0,
        request_token=None,
        next_page_token=None,
        item_count=len(rows),
        raw_bytes_sha256=raw_sha,
        page_file="statement.raw",
        rate_limit_headers={},
        retrieved_at_utc=now_utc.isoformat(),
    )
    chain_sha = ordered_page_chain_digest([page_rec])
    manifest = RetrievalRunManifest(
        schema_version="1.1",
        run_id=f"PPDS_{as_of.isoformat()}_{source_id}",
        consumer_id="ppds",
        operation="statement_import",
        subject_metadata={
            "source_id": source_id,
            "statement_as_of": as_of.isoformat(),
            "adapter_id": active_adapter.adapter_id,
            "ingestion_mode": "SYNTHETIC_INGESTION",
        },
        runtime_sha=current_sha,
        authority_ref=None,
        authority_sha256=None,
        page_records=(page_rec,),
        page_chain_sha256=chain_sha,
        item_count=len(rows),
        operation_count=1,
        status="RETRIEVED",
        error_message=None,
        created_at_utc=now_utc.isoformat(),
    )
    manifest.write_immutable(target_dir / "manifest.json")

    bound_cash = tuple(
        ProvenanceBoundLot(source_id=source_id, as_of=as_of, source_sha256=raw_sha, lot=lot)
        for lot in snapshot.cash_lots
    )
    bound_pos = tuple(
        ProvenanceBoundLot(source_id=source_id, as_of=as_of, source_sha256=raw_sha, lot=lot)
        for lot in snapshot.position_lots
    )

    return ImportedStatementRecord(
        source_id=source_id,
        as_of=as_of,
        raw_content_sha256=raw_sha,
        manifest_sha256=manifest.manifest_sha256(),
        adapter_id=active_adapter.adapter_id,
        snapshot=snapshot,
        ledger=ledger,
        reconciliation=reconciliation,
        evidence_path=target_dir,
        bound_cash_lots=bound_cash,
        bound_position_lots=bound_pos,
    )
