"""Evidence root directory boundaries and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from acash.core.domain.exceptions import DataContractError

_HYP011_ROOT_CANONICAL = "/var/lib/acash/hyp011"


def _targets_hyp011_runtime(posix_lower_path: str) -> bool:
    """Single authority for the HYP_011 runtime collision rule.

    Matches the canonical runtime directory itself, anything beneath it, or
    any path embedding the canonical substring (conservative against `..`
    segments in unresolved spellings).
    """
    return (
        posix_lower_path == _HYP011_ROOT_CANONICAL
        or posix_lower_path.startswith(_HYP011_ROOT_CANONICAL + "/")
        or "/var/lib/acash/hyp011" in posix_lower_path
    )


def _detect_repository_root() -> Path:
    """Locate the repository root by walking up from current module until pyproject.toml."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    return Path(__file__).resolve().parents[3]


def validate_external_evidence_root(
    root_path: Path,
    repo_root: Optional[Path] = None,
) -> Path:
    """Validate that evidence root is an absolute, external directory outside the repository and HYP_011.

    Enforces:
    1. Must be an absolute path.
    2. Must NOT be inside the Git repository working tree.
    3. Must NOT target or be inside the HYP_011 runtime directory (/var/lib/acash/hyp011).
    """
    if not isinstance(root_path, Path):
        try:
            root_path = Path(root_path)
        except Exception as exc:
            raise DataContractError(
                f"EVIDENCE_ROOT_INVALID_TYPE: cannot convert {type(root_path)} to Path."
            ) from exc

    posix_str = str(root_path).replace("\\", "/").lower()
    if _targets_hyp011_runtime(posix_str):
        raise DataContractError(
            f"EVIDENCE_ROOT_HYP011_COLLISION: evidence root {root_path} must not target HYP_011 runtime storage."
        )

    if not root_path.is_absolute():
        raise DataContractError(
            f"EVIDENCE_ROOT_NOT_ABSOLUTE: evidence root must be an absolute path, got {root_path}."
        )

    resolved_root = root_path.resolve()

    # Re-apply the HYP_011 collision rule AFTER canonical resolution. The
    # unresolved-string check above cannot see through symlinks (or
    # equivalent indirection): e.g. /tmp/outer_link resolving to
    # /var/lib/acash/hyp011 must fail closed here even though its spelling
    # avoids the HYP_011 substring.
    if _targets_hyp011_runtime(str(resolved_root).replace("\\", "/").lower()):
        raise DataContractError(
            f"EVIDENCE_ROOT_HYP011_COLLISION: resolved evidence root {resolved_root} targets HYP_011 runtime storage."
        )

    # Reject repository-local root
    resolved_repo = (repo_root or _detect_repository_root()).resolve()
    if resolved_root == resolved_repo or resolved_repo in resolved_root.parents:
        raise DataContractError(
            f"EVIDENCE_ROOT_REPOSITORY_LOCAL: evidence root {resolved_root} must be external to repository {resolved_repo}."
        )

    return resolved_root
