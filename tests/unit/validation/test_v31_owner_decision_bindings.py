"""V31 owner-decision record: bound digests must match the bound files."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from acash.data.qualification.lane_b_d5_rehearsal import D5_ADMISSION_TRUST_ANCHORS

REPO_ROOT = Path(__file__).resolve().parents[3]
RECORD = REPO_ROOT / "docs/governance/V31_OWNER_DECISION_AND_EVIDENCE_REGISTRY_20261025.md"
_BINDING_ROW = re.compile(r"^\| [^|]*?\| ?`?([\w./-]+\.(?:md|py))`? \|.*`([0-9a-f]{64})`", re.M)
_DRAFT_ROW = re.compile(r"^\| `([\w./-]+\.(?:md|py))` \|.*`([0-9a-f]{64})`", re.M)


def _lf_sha256(path: Path) -> str:
    # Digests are over committed LF blobs; Windows checkouts may materialise CRLF.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _bindings() -> dict[str, str]:
    text = RECORD.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for pattern in (_BINDING_ROW, _DRAFT_ROW):
        for rel, digest in pattern.findall(text):
            assert found.get(rel, digest) == digest, f"conflicting digests for {rel}"
            found[rel] = digest
    return found


def test_record_binds_exactly_the_six_artifacts() -> None:
    assert set(_bindings()) == {
        "docs/research/D6_PREREGISTERED_CONTRACT_20261023.md",
        "docs/research/D6_AMENDMENT_A1_DESCRIPTIVE_COMPARISON_UNRATIFIED_20261025.md",
        "docs/research/D6_AMENDMENT_A2_CAUSAL_EXECUTION_TIMING_UNRATIFIED_20261025.md",
        "src/acash/data/qualification/lane_a_d3_streaming.py",
        "tests/unit/data/test_lane_a_d3_streaming_v2.py",
        "tests/unit/data/test_lane_a_d3_streaming.py",
    }


def test_bound_digests_match_files() -> None:
    for rel, digest in _bindings().items():
        assert _lf_sha256(REPO_ROOT / rel) == digest, f"digest drift: {rel}"


def test_record_claims_no_signature_and_no_anchor() -> None:
    text = RECORD.read_text(encoding="utf-8")
    assert "OWNER_APPROVED_PENDING_FORMAL_ATTESTATION" in text
    assert "Owner signature / signed-commit SHA / PR review URL: ____________________" in text
    assert "D5_REAL_DATA_NOT_ADMITTED" in text
    assert len(D5_ADMISSION_TRUST_ANCHORS) == 0
