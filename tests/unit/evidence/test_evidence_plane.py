"""Unit tests for the Retrieval Evidence Plane primitives (V1.1)."""

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
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


def _make_page_rec(
    page_index: int = 0,
    request_token: str | None = None,
    next_page_token: str | None = None,
    item_count: int = 10,
    raw_bytes: bytes = b"payload",
    retrieved_at_utc: str = "2026-10-07T12:00:00+00:00",
) -> RetrievalPageRecord:
    digest = hashlib.sha256(raw_bytes).hexdigest()
    return RetrievalPageRecord(
        page_index=page_index,
        request_token=request_token,
        next_page_token=next_page_token,
        item_count=item_count,
        raw_bytes_sha256=digest,
        page_file=f"page_{page_index:04d}.bin",
        rate_limit_headers={"x-ratelimit-remaining": "199"},
        retrieved_at_utc=retrieved_at_utc,
    )


def test_content_sha256_bytes_and_string() -> None:
    data_bytes = b"sample_payload"
    expected = hashlib.sha256(data_bytes).hexdigest()
    assert content_sha256(data_bytes) == expected
    assert content_sha256("sample_payload") == expected

    with pytest.raises(DataContractError, match="EVIDENCE_DIGEST_BAD_TYPE"):
        content_sha256(12345)  # type: ignore[arg-type]


def test_canonical_manifest_sha256_matches_canonical_serializer() -> None:
    doc1 = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
    doc2 = {"nested": {"y": 20, "z": 10}, "a": 1, "b": 2}
    digest1 = canonical_manifest_sha256(doc1)
    digest2 = canonical_manifest_sha256(doc2)
    assert digest1 == digest2
    # Must match CanonicalConfigSerializer directly (single canonical authority)
    assert digest1 == CanonicalConfigSerializer.compute_sha256(doc1)

    with pytest.raises(DataContractError, match="EVIDENCE_MANIFEST_NOT_MAPPING"):
        canonical_manifest_sha256(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_ordered_page_chain_digest_independent_sensitivity() -> None:
    p0 = _make_page_rec(page_index=0, request_token=None, next_page_token="tok1", item_count=50, raw_bytes=b"p0")
    p1 = _make_page_rec(page_index=1, request_token="tok1", next_page_token=None, item_count=50, raw_bytes=b"p1")

    base_chain = ordered_page_chain_digest([p0, p1])

    # 1. Order sensitivity: [p1, p0] != [p0, p1]
    p0_swap = _make_page_rec(page_index=1, request_token=None, next_page_token="tok1", item_count=50, raw_bytes=b"p0")
    p1_swap = _make_page_rec(page_index=0, request_token="tok1", next_page_token=None, item_count=50, raw_bytes=b"p1")
    assert ordered_page_chain_digest([p1_swap, p0_swap]) != base_chain

    # 2. Raw bytes digest sensitivity
    p0_diff_bytes = _make_page_rec(page_index=0, request_token=None, next_page_token="tok1", item_count=50, raw_bytes=b"other")
    assert ordered_page_chain_digest([p0_diff_bytes, p1]) != base_chain

    # 3. Request token sensitivity (same raw bytes, different request_token)
    p1_diff_req = _make_page_rec(page_index=1, request_token="tok_different", next_page_token=None, item_count=50, raw_bytes=b"p1")
    assert ordered_page_chain_digest([p0, p1_diff_req]) != base_chain

    # 4. Next token sensitivity (same raw bytes, different next_page_token)
    p0_diff_next = _make_page_rec(page_index=0, request_token=None, next_page_token="tok_other", item_count=50, raw_bytes=b"p0")
    assert ordered_page_chain_digest([p0_diff_next, p1]) != base_chain

    # 5. Item count sensitivity
    p0_diff_count = _make_page_rec(page_index=0, request_token=None, next_page_token="tok1", item_count=99, raw_bytes=b"p0")
    assert ordered_page_chain_digest([p0_diff_count, p1]) != base_chain

    # 6. Page index sensitivity
    p0_diff_idx = _make_page_rec(page_index=9, request_token=None, next_page_token="tok1", item_count=50, raw_bytes=b"p0")
    assert ordered_page_chain_digest([p0_diff_idx, p1]) != base_chain

    # 7. Empty chain fails closed
    with pytest.raises(DataContractError, match="EVIDENCE_PAGE_CHAIN_EMPTY"):
        ordered_page_chain_digest([])

    # 8. Malformed element fails closed
    with pytest.raises(DataContractError, match="EVIDENCE_PAGE_RECORD_INVALID_TYPE"):
        ordered_page_chain_digest(["not_a_record"])


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
    doc = {"run_id": "RUN-01", "status": "RETRIEVED"}
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


def test_retrieval_run_manifest_v11_contracts(tmp_path: Path) -> None:
    rec1 = _make_page_rec(page_index=0, request_token=None, next_page_token="tok1", item_count=50, raw_bytes=b"page1")
    rec2 = _make_page_rec(page_index=1, request_token="tok1", next_page_token=None, item_count=50, raw_bytes=b"page2")
    chain = ordered_page_chain_digest([rec1, rec2])

    valid_manifest = RetrievalRunManifest(
        schema_version="1.1",
        run_id="RUN_20261007_001",
        consumer_id="ri01",
        operation="fetch_bars",
        subject_metadata={"symbol": "SPY", "session": "2021-06-01"},
        runtime_sha="a" * 40,
        authority_ref="AUTHORIZE_RI01_PROBE_R1_TEST",
        authority_sha256="c" * 64,
        page_records=(rec1, rec2),
        page_chain_sha256=chain,
        item_count=100,
        operation_count=2,
        status="RETRIEVED",
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
            schema_version="1.1",
            run_id="RUN_20261007_001",
            consumer_id="ri01",
            operation="fetch_bars",
            subject_metadata={"symbol": "SPY", "session": "2021-06-01"},
            runtime_sha="a" * 40,
            authority_ref="AUTHORIZE_RI01_PROBE_R1_TEST",
            authority_sha256="c" * 64,
            page_records=(rec1, rec2),
            page_chain_sha256="b" * 64,
            item_count=100,
            operation_count=2,
            status="RETRIEVED",
            error_message=None,
            created_at_utc="2026-10-07T12:02:00+00:00",
        )

    # Tampered item count fails closed
    with pytest.raises(DataContractError, match="RUN_MANIFEST_ITEM_COUNT_MISMATCH"):
        RetrievalRunManifest(
            schema_version="1.1",
            run_id="RUN_20261007_001",
            consumer_id="ri01",
            operation="fetch_bars",
            subject_metadata={"symbol": "SPY", "session": "2021-06-01"},
            runtime_sha="a" * 40,
            authority_ref="AUTHORIZE_RI01_PROBE_R1_TEST",
            authority_sha256="c" * 64,
            page_records=(rec1, rec2),
            page_chain_sha256=chain,
            item_count=999,
            operation_count=2,
            status="RETRIEVED",
            error_message=None,
            created_at_utc="2026-10-07T12:02:00+00:00",
        )


def test_ppds_has_zero_imports_from_research() -> None:
    """CRITICAL ARCHITECTURAL INVARIANT: acash.ppds MUST NOT import from acash.research."""
    ppds_dir = Path(__file__).resolve().parents[3] / "src" / "acash" / "ppds"
    assert ppds_dir.is_dir()

    for py_file in ppds_dir.glob("**/*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("acash.research"), (
                        f"Architecture violation in {py_file.name}: imports {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert not node.module.startswith("acash.research"), (
                        f"Architecture violation in {py_file.name}: imports from {node.module}"
                    )


def test_evidence_plane_has_zero_external_domain_imports() -> None:
    """CRITICAL ARCHITECTURAL INVARIANT: acash.evidence MUST NOT import from research or execution."""
    evidence_dir = Path(__file__).resolve().parents[3] / "src" / "acash" / "evidence"
    assert evidence_dir.is_dir()

    forbidden_prefixes = ("acash.research", "acash.execution", "acash.data")
    for py_file in evidence_dir.glob("**/*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_prefixes:
                        assert not alias.name.startswith(forbidden), (
                            f"Architecture violation in {py_file.name}: imports {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_prefixes:
                        assert not node.module.startswith(forbidden), (
                            f"Architecture violation in {py_file.name}: imports from {node.module}"
                        )
