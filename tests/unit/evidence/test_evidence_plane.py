"""Unit tests for the Retrieval Evidence Plane primitives."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.evidence import (
    RetrievalPageRecord,
    RetrievalRunManifest,
    canonical_manifest_sha256,
    content_sha256,
    ordered_page_chain_digest,
    validate_external_evidence_root,
    write_immutable_bytes,
    write_immutable_json,
)


def test_content_sha256_bytes_and_string() -> None:
    data_bytes = b"sample_payload"
    expected = hashlib.sha256(data_bytes).hexdigest()
    assert content_sha256(data_bytes) == expected
    assert content_sha256("sample_payload") == expected

    with pytest.raises(DataContractError, match="EVIDENCE_DIGEST_BAD_TYPE"):
        content_sha256(12345)  # type: ignore[arg-type]


def test_canonical_manifest_sha256_formatting() -> None:
    doc1 = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
    doc2 = {"nested": {"y": 20, "z": 10}, "a": 1, "b": 2}
    # Key ordering must produce identical canonical SHA-256
    digest1 = canonical_manifest_sha256(doc1)
    digest2 = canonical_manifest_sha256(doc2)
    assert digest1 == digest2

    with pytest.raises(DataContractError, match="EVIDENCE_MANIFEST_NOT_MAPPING"):
        canonical_manifest_sha256(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_ordered_page_chain_digest_sensitivity() -> None:
    d1 = hashlib.sha256(b"page1").hexdigest()
    d2 = hashlib.sha256(b"page2").hexdigest()
    d3 = hashlib.sha256(b"page3").hexdigest()

    chain1 = ordered_page_chain_digest([d1, d2, d3])
    chain2 = ordered_page_chain_digest([d2, d1, d3])
    assert chain1 != chain2

    # Empty chain fails closed
    with pytest.raises(DataContractError, match="EVIDENCE_PAGE_CHAIN_EMPTY"):
        ordered_page_chain_digest([])

    # Invalid sha fails closed
    with pytest.raises(DataContractError, match="EVIDENCE_PAGE_DIGEST_INVALID"):
        ordered_page_chain_digest([d1, "not-a-valid-sha"])


def test_validate_external_evidence_root_rejections(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # 1. Non-absolute path rejected
    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_NOT_ABSOLUTE"):
        validate_external_evidence_root(Path("relative/path"), repo_root=repo_root)

    # 2. Repo-local root rejected
    repo_local = repo_root / "data" / "evidence"
    repo_local.mkdir(parents=True)
    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_REPOSITORY_LOCAL"):
        validate_external_evidence_root(repo_local, repo_root=repo_root)

    # 3. HYP_011 runtime root rejected
    hyp011_root = Path("/var/lib/acash/hyp011/v2")
    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_HYP011_COLLISION"):
        validate_external_evidence_root(hyp011_root, repo_root=repo_root)

    # 4. Valid external root accepted
    external_root = tmp_path / "external_evidence"
    external_root.mkdir()
    validated = validate_external_evidence_root(external_root, repo_root=repo_root)
    assert validated == external_root.resolve()


def test_immutable_writers_enforce_create_once(tmp_path: Path) -> None:
    external_dir = tmp_path / "external"
    external_dir.mkdir()

    bin_file = external_dir / "artifact.bin"
    d1 = write_immutable_bytes(bin_file, b"immutable_content")
    assert bin_file.read_bytes() == b"immutable_content"
    assert d1 == hashlib.sha256(b"immutable_content").hexdigest()

    # Second write must fail closed
    with pytest.raises(DataContractError, match="EVIDENCE_FILE_EXISTS_IMMUTABLE"):
        write_immutable_bytes(bin_file, b"new_content")
    assert bin_file.read_bytes() == b"immutable_content"

    json_file = external_dir / "meta.json"
    doc = {"run_id": "RUN-01", "status": "COMPLETED"}
    d_json = write_immutable_json(json_file, doc)
    assert json.loads(json_file.read_text(encoding="utf-8")) == doc
    assert d_json == hashlib.sha256(json_file.read_bytes()).hexdigest()

    with pytest.raises(DataContractError, match="EVIDENCE_FILE_EXISTS_IMMUTABLE"):
        write_immutable_json(json_file, {"run_id": "OVERWRITE"})


def test_retrieval_page_record_contracts() -> None:
    digest = hashlib.sha256(b"test").hexdigest()
    rec = RetrievalPageRecord(
        page_index=0,
        request_token=None,
        next_page_token="tok_1",
        item_count=100,
        raw_bytes_sha256=digest,
        page_file="page_0000.bin",
        rate_limit_headers={"x-ratelimit-remaining": "199"},
        retrieved_at_utc="2026-10-07T12:00:00+00:00",
    )
    assert rec.to_dict()["page_index"] == 0

    with pytest.raises(DataContractError, match="PAGE_RECORD_INVALID_INDEX"):
        RetrievalPageRecord(
            page_index=-1,
            request_token=None,
            next_page_token=None,
            item_count=10,
            raw_bytes_sha256=digest,
            page_file="page_0000.bin",
            rate_limit_headers={},
            retrieved_at_utc="2026-10-07T12:00:00+00:00",
        )

    with pytest.raises(DataContractError, match="PAGE_RECORD_INVALID_TIMESTAMP"):
        RetrievalPageRecord(
            page_index=0,
            request_token=None,
            next_page_token=None,
            item_count=10,
            raw_bytes_sha256=digest,
            page_file="page_0000.bin",
            rate_limit_headers={},
            retrieved_at_utc="not-a-timestamp",
        )


def test_retrieval_run_manifest_contracts(tmp_path: Path) -> None:
    d1 = hashlib.sha256(b"page1").hexdigest()
    d2 = hashlib.sha256(b"page2").hexdigest()
    chain = ordered_page_chain_digest([d1, d2])

    rec1 = RetrievalPageRecord(
        page_index=0,
        request_token=None,
        next_page_token="next",
        item_count=50,
        raw_bytes_sha256=d1,
        page_file="page_0000.bin",
        rate_limit_headers={"x-ratelimit-remaining": "199"},
        retrieved_at_utc="2026-10-07T12:00:00+00:00",
    )
    rec2 = RetrievalPageRecord(
        page_index=1,
        request_token="next",
        next_page_token=None,
        item_count=50,
        raw_bytes_sha256=d2,
        page_file="page_0001.bin",
        rate_limit_headers={"x-ratelimit-remaining": "198"},
        retrieved_at_utc="2026-10-07T12:01:00+00:00",
    )

    valid_manifest = RetrievalRunManifest(
        run_id="RUN_20261007_001",
        authority_id="AUTHORIZE_RI01_PROBE_R1_TEST",
        session="2021-06-01",
        capability="bars",
        symbol="SPY",
        runtime_sha="a" * 40,
        page_records=(rec1, rec2),
        page_chain_sha256=chain,
        total_items=100,
        total_requests=2,
        status="COMPLETED",
        error_message=None,
        created_at_utc="2026-10-07T12:02:00+00:00",
    )

    manifest_file = tmp_path / "manifest.json"
    m_digest = valid_manifest.write_immutable(manifest_file)
    assert m_digest == content_sha256(manifest_file.read_bytes())
    assert valid_manifest.manifest_sha256() == canonical_manifest_sha256(valid_manifest.to_dict())

    # Tampered chain fails closed
    with pytest.raises(DataContractError, match="RUN_MANIFEST_CHAIN_DIGEST_MISMATCH"):
        RetrievalRunManifest(
            run_id="RUN_20261007_001",
            authority_id="AUTHORIZE_RI01_PROBE_R1_TEST",
            session="2021-06-01",
            capability="bars",
            symbol="SPY",
            runtime_sha="a" * 40,
            page_records=(rec1, rec2),
            page_chain_sha256="b" * 64,
            total_items=100,
            total_requests=2,
            status="COMPLETED",
            error_message=None,
            created_at_utc="2026-10-07T12:02:00+00:00",
        )

    # Tampered item count fails closed
    with pytest.raises(DataContractError, match="RUN_MANIFEST_ITEM_COUNT_MISMATCH"):
        RetrievalRunManifest(
            run_id="RUN_20261007_001",
            authority_id="AUTHORIZE_RI01_PROBE_R1_TEST",
            session="2021-06-01",
            capability="bars",
            symbol="SPY",
            runtime_sha="a" * 40,
            page_records=(rec1, rec2),
            page_chain_sha256=chain,
            total_items=999,
            total_requests=2,
            status="COMPLETED",
            error_message=None,
            created_at_utc="2026-10-07T12:02:00+00:00",
        )


def test_evidence_plane_does_not_import_hyp011() -> None:
    """CRITICAL ARCHITECTURAL INVARIANT: acash.evidence MUST NOT import HYP_011."""
    import acash.evidence

    for module_name in sys.modules:
        if module_name.startswith("acash.evidence"):
            mod = sys.modules[module_name]
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if hasattr(attr, "__module__") and attr.__module__:
                    assert not attr.__module__.startswith("acash.research.hyp011"), (
                        f"acash.evidence leaks import from {attr.__module__}"
                    )
