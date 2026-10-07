"""Unit tests for PPDS synthetic statement import provenance integration."""

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.evidence import canonical_manifest_sha256, content_sha256
from acash.ppds.provenance import (
    BrokerStatementAdapter,
    ImportedStatementRecord,
    SyntheticCsvStatementAdapter,
    import_synthetic_statement,
)

SYNTHETIC_CSV_PAYLOAD = b"""record_type,symbol,currency,quantity,amount,cost_basis_per_share,acquired_on
CASH,,USD,,10000.50,,2026-10-01
POSITION,SPY,USD,50,,450.25,2026-10-02
POSITION,QQQ,USD,25,,380.10,2026-10-03
"""


def test_synthetic_statement_import_pipeline(tmp_path: Path) -> None:
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_SYNTH_001"
    runtime_sha = "a" * 40
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    record = import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_PAYLOAD,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha=runtime_sha,
    )

    # 1. Raw bytes immutable & match hash
    raw_file = external_root / "ppds" / as_of.isoformat() / source_id / "statement.raw"
    assert raw_file.is_file()
    assert raw_file.read_bytes() == SYNTHETIC_CSV_PAYLOAD
    assert record.raw_content_sha256 == content_sha256(SYNTHETIC_CSV_PAYLOAD)

    # 2. Manifest created & valid
    manifest_file = external_root / "ppds" / as_of.isoformat() / source_id / "manifest.json"
    assert manifest_file.is_file()
    manifest_doc = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert record.manifest_sha256 == canonical_manifest_sha256(manifest_doc)

    # 3. Normalized lots and ledger match exactly
    assert record.reconciliation.matched is True
    assert not record.reconciliation.breaks
    assert record.snapshot.cash_by_currency()["USD"] == Decimal("10000.50")
    assert record.ledger.cash_by_currency()["USD"] == Decimal("10000.50")
    assert record.snapshot.quantity_by_symbol()["SPY"] == Decimal("50")
    assert record.ledger.quantity_by_symbol()["SPY"] == Decimal("50")
    assert record.snapshot.quantity_by_symbol()["QQQ"] == Decimal("25")
    assert record.ledger.quantity_by_symbol()["QQQ"] == Decimal("25")

    # 4. Normalized import is source-bound
    assert len(record.bound_cash_lots) == 1
    assert record.bound_cash_lots[0].source_id == source_id
    assert record.bound_cash_lots[0].source_sha256 == record.raw_content_sha256
    assert len(record.bound_position_lots) == 2
    for b_lot in record.bound_position_lots:
        assert b_lot.source_id == source_id
        assert b_lot.source_sha256 == record.raw_content_sha256


def test_tamper_changes_digest(tmp_path: Path) -> None:
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_SYNTH_TAMPER"
    runtime_sha = "a" * 40
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    record = import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_PAYLOAD,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha=runtime_sha,
    )

    tampered_bytes = SYNTHETIC_CSV_PAYLOAD + b"# tampered\n"
    assert content_sha256(tampered_bytes) != record.raw_content_sha256


def test_reimport_cannot_overwrite_evidence(tmp_path: Path) -> None:
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_SYNTH_COLLISION"
    runtime_sha = "a" * 40
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_PAYLOAD,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha=runtime_sha,
    )

    # Attempting to re-import identical or different content under same key fails closed
    with pytest.raises(DataContractError, match="EVIDENCE_FILE_EXISTS_IMMUTABLE"):
        import_synthetic_statement(
            raw_bytes=SYNTHETIC_CSV_PAYLOAD,
            source_id=source_id,
            as_of=as_of,
            evidence_root=external_root,
            imported_at_utc=now_utc,
            runtime_sha=runtime_sha,
        )


def test_malformed_source_fails_closed(tmp_path: Path) -> None:
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    runtime_sha = "a" * 40

    # 1. Empty payload
    with pytest.raises(DataContractError, match="PPDS_IMPORT_EMPTY_BYTES"):
        import_synthetic_statement(
            raw_bytes=b"",
            source_id="EMPTY",
            as_of=as_of,
            evidence_root=external_root,
            runtime_sha=runtime_sha,
        )

    # 2. Corrupt non-UTF8 payload
    with pytest.raises(DataContractError, match="PPDS_ADAPTER_DECODE_ERROR"):
        import_synthetic_statement(
            raw_bytes=b"\xff\xfe\x00\x00\x80",
            source_id="NON_UTF8",
            as_of=as_of,
            evidence_root=external_root,
            runtime_sha=runtime_sha,
        )

    # 3. Missing required columns
    bad_csv = b"record_type,symbol,quantity\nPOSITION,SPY,10\n"
    with pytest.raises(DataContractError, match="PPDS_STATEMENT_MISSING_COLUMNS"):
        import_synthetic_statement(
            raw_bytes=bad_csv,
            source_id="MISSING_COLS",
            as_of=as_of,
            evidence_root=external_root,
            runtime_sha=runtime_sha,
        )


def test_repo_local_and_hyp011_root_rejections(tmp_path: Path) -> None:
    as_of = date(2026, 10, 5)
    repo_local = Path(__file__).resolve().parents[3] / "data"

    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_REPOSITORY_LOCAL"):
        import_synthetic_statement(
            raw_bytes=SYNTHETIC_CSV_PAYLOAD,
            source_id="REPO_LOCAL",
            as_of=as_of,
            evidence_root=repo_local,
            runtime_sha="a" * 40,
        )

    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_HYP011_COLLISION"):
        import_synthetic_statement(
            raw_bytes=SYNTHETIC_CSV_PAYLOAD,
            source_id="HYP011",
            as_of=as_of,
            evidence_root=Path("/var/lib/acash/hyp011/v2"),
            runtime_sha="a" * 40,
        )


def test_custom_adapter_protocol_compliance() -> None:
    class CustomMockAdapter:
        adapter_id = "CUSTOM_MOCK_ADAPTER"

        def parse(self, raw_bytes: bytes) -> list[Any]:
            return []

    assert isinstance(CustomMockAdapter(), BrokerStatementAdapter)
    assert isinstance(SyntheticCsvStatementAdapter(), BrokerStatementAdapter)
