"""Authoritative Git runtime identity resolution for the ACASH Architecture.

Single canonical authority for resolving repository HEAD commit SHA.
Independent consumers (such as Evidence Plane, PPDS, and RI-01) must resolve
runtime Git identity through this generic module, never across domain boundaries.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

from acash.core.domain.exceptions import DataContractError

_HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def get_current_runtime_sha(repo_root: Optional[Path] = None) -> str:
    """Read HEAD commit SHA from git repository.

    Fails closed if the repository commit SHA cannot be authoritatively resolved
    or does not match exact 40-character lowercase hex format.
    """
    try:
        resolved_repo = repo_root or Path(__file__).resolve().parents[3]
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=resolved_repo,
        )
        sha = result.stdout.strip().lower()
        if len(sha) == 40 and _HEX40_PATTERN.match(sha):
            return sha
    except Exception as exc:
        raise DataContractError(
            f"CANNOT_RESOLVE_RUNTIME_SHA: HEAD commit SHA unavailable: {exc}."
        ) from exc
    raise DataContractError("CANNOT_RESOLVE_RUNTIME_SHA: invalid SHA format.")
