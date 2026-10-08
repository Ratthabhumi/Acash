"""Adversarial tests for evidence-root boundary enforcement (symlink escape).

Proves the HYP_011 collision rule applies AFTER canonical path resolution:
a symlink whose unresolved spelling avoids the HYP_011 substring but whose
resolved target lands inside the HYP_011 runtime directory must fail closed.

Symlink creation requires OS privilege (Windows Developer Mode / elevated
rights, POSIX ownership rules). When the host refuses, the affected tests
skip with an explicit recorded reason — never silently. The pure rule logic
is covered separately without privileges.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.evidence.roots import (
    _detect_repository_root,
    _targets_hyp011_runtime,
    validate_external_evidence_root,
)


def _try_symlink(link: Path, target: Path) -> bool:
    """Attempt symlink creation; return False (skip signal) when refused."""
    try:
        link.symlink_to(target, target_is_directory=True)
        return True
    except OSError:
        return False


def test_direct_hyp011_spelling_still_blocked() -> None:
    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_HYP011_COLLISION"):
        validate_external_evidence_root(Path("/var/lib/acash/hyp011"))
    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_HYP011_COLLISION"):
        validate_external_evidence_root(Path("/var/lib/acash/hyp011/v2"))


def test_hyp011_rule_unit_strings() -> None:
    assert _targets_hyp011_runtime("/var/lib/acash/hyp011") is True
    assert _targets_hyp011_runtime("/var/lib/acash/hyp011/v2") is True
    # Conservative inherited substring semantics: a sibling whose spelling
    # merely embeds the canonical substring is also rejected (fail-closed;
    # pre-existing rule behavior, preserved unchanged by the resolve() fix).
    assert _targets_hyp011_runtime("/var/lib/acash/hyp011_evil") is True
    assert _targets_hyp011_runtime("/tmp/external_evidence") is False
    assert _targets_hyp011_runtime("C:/evidence/outside") is False


def test_plain_external_dir_accepted(tmp_path: Path) -> None:
    outside = tmp_path / "external_evidence"
    outside.mkdir()
    assert validate_external_evidence_root(outside) == outside.resolve()


def test_symlink_escape_blocked_after_resolve(tmp_path: Path) -> None:
    """A symlink whose spelling is clean but which resolves into HYP_011 storage fails closed.

    NOTE on the test name: it deliberately avoids the substring "hyp011"
    because pytest embeds the test name in tmp_path, and the unresolved
    spelling presented to the validator must be genuinely free of the
    HYP_011 marker for this test to exercise the post-resolution gate
    (rather than the pre-resolution string gate).
    """
    link = tmp_path / "outer_link"
    if not _try_symlink(link, Path("/var/lib/acash/hyp011")):
        pytest.skip("symlink creation refused by host; cannot stage escape")
    # Unresolved spelling carries no HYP_011 marker; resolution lands inside.
    assert "hyp011" not in str(link).lower()
    assert link.resolve() == Path("/var/lib/acash/hyp011")
    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_HYP011_COLLISION"):
        validate_external_evidence_root(link)


def test_symlink_into_repo_blocked(tmp_path: Path) -> None:
    repo_src = _detect_repository_root() / "src"
    link = tmp_path / "into_repo"
    if not _try_symlink(link, repo_src):
        pytest.skip("symlink creation refused by host; cannot stage escape")
    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_REPOSITORY_LOCAL"):
        validate_external_evidence_root(link)
