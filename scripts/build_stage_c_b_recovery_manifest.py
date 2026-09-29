"""Deterministic builder utility for HYP_011 Stage C-B recovery binding manifest.

This script creates the post-merge Stage C-B operational re-activation binding.
DEFAULTS TO DRY-RUN (no write).
Requires separate explicit human authorization before writing to disk.

Strict invariants:
- Commit SHA must be a valid 40-character hex string.
- Commit SHA must exist in local Git object database.
- Commit timestamp must be read directly from Git (never manually typed).
- Activation session is derived via NyseCa1Calendar only.
- Missed sessions are derived via NyseCa1Calendar only, and must include 2026-09-28.
- Canonical JSON serialization with newline, hashed via SHA-256.
- Zero price data, zero Alpaca access, zero state.json modification, zero systemd changes.

Write Mode Strict Gates:
- Canonical branch must be 'main'.
- Local HEAD must match 'origin/main'.
- Supplied commit SHA must match 'origin/main'.
- Tracked working tree must be clean.
- Target Stage C-B manifest must be absent (create-once immutable semantics via 'xb').
- Canonical output path is strictly docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow import (
    FAILED_ACTIVATION_SESSION,
    FAILED_DISPATCH_ATTEMPT,
    FAILED_DISPATCH_AT_UTC,
    NEXT_DISPATCH_ATTEMPT,
    SCIENTIFIC_PROSPECTIVE_BOUNDARY,
    STAGE_C_RECOVERY_BINDING_ID,
    STAGE_C_RECOVERY_BINDING_PATH,
    derive_activation_session,
    missed_unobserved_sessions,
)


def get_git_commit_info(
    commit_sha: str,
    repo_root: Optional[Path] = None,
) -> datetime:
    """Validate Git commit existence; return committer UTC timestamp."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit_sha):
        raise DataContractError(f"INVALID_COMMIT_SHA_FORMAT: '{commit_sha}'. Must be 40 hex chars.")

    # 1. Verify existence in local git object database
    cat_res = subprocess.run(
        ["git", "cat-file", "-e", f"{commit_sha}^{{commit}}"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if cat_res.returncode != 0:
        raise DataContractError(f"GIT_COMMIT_NOT_FOUND: {commit_sha} does not exist in local Git DB.")

    # 2. Read machine-readable ISO commit timestamp
    show_res = subprocess.run(
        ["git", "show", "-s", "--format=%cI", commit_sha],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if show_res.returncode != 0:
        raise DataContractError(f"GIT_SHOW_FAILED: failed to inspect commit {commit_sha}.")

    ts_str = show_res.stdout.strip()
    if not ts_str:
        raise DataContractError(f"GIT_COMMIT_TIMESTAMP_EMPTY: commit {commit_sha}.")

    try:
        commit_dt = datetime.fromisoformat(ts_str)
    except Exception as exc:
        raise DataContractError(f"GIT_COMMIT_TIMESTAMP_INVALID: {ts_str} ({exc}).") from exc

    if commit_dt.tzinfo is None:
        raise DataContractError(f"GIT_COMMIT_TIMESTAMP_NAIVE: {ts_str}.")

    return commit_dt.astimezone(timezone.utc)


def build_stage_c_b_manifest(
    commit_sha: str,
    commit_utc: datetime,
    calendar: Optional[NyseCa1Calendar] = None,
) -> Dict[str, Any]:
    """Build the Stage C-B recovery manifest dictionary deterministically."""
    cal = calendar or NyseCa1Calendar()
    if commit_utc.tzinfo is None:
        raise DataContractError("COMMIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE.")
    utc_norm = commit_utc.astimezone(timezone.utc)

    derived_act = derive_activation_session(cal, utc_norm)
    if derived_act <= FAILED_ACTIVATION_SESSION:
        raise DataContractError(
            f"ACTIVATION_NOT_ADVANCED: derived {derived_act} <= failed {FAILED_ACTIVATION_SESSION}."
        )

    missed_sessions = missed_unobserved_sessions(cal, derived_act)
    if FAILED_ACTIVATION_SESSION not in missed_sessions:
        raise DataContractError(
            f"FAILED_SESSION_MISSING_FROM_UNOBSERVED: {FAILED_ACTIVATION_SESSION} not in {missed_sessions}."
        )

    manifest: Dict[str, Any] = {
        "manifest_version": 1,
        "binding_id": STAGE_C_RECOVERY_BINDING_ID,
        "description": "Post-merge Stage C-B operational re-activation binding for HYP_011 prospective shadow.",
        "scientific_prospective_boundary": SCIENTIFIC_PROSPECTIVE_BOUNDARY.isoformat(),
        "binding_commit_sha": commit_sha.lower(),
        "binding_commit_utc": utc_norm.isoformat(),
        "activation_session": derived_act.isoformat(),
        "failed_dispatch_session": FAILED_ACTIVATION_SESSION.isoformat(),
        "failed_dispatch_attempt": FAILED_DISPATCH_ATTEMPT,
        "failed_dispatch_at_utc": FAILED_DISPATCH_AT_UTC.isoformat(),
        "failed_session_classification": "MISSED_UNOBSERVED_DUE_TO_PROVIDER_ACCESS_BLOCK",
        "missed_unobserved_sessions": [s.isoformat() for s in missed_sessions],
        "next_observation_ordinal": 1,
        "next_dispatch_attempt": NEXT_DISPATCH_ATTEMPT,
        "backfill_allowed": False,
        "retry_failed_session_allowed": False,
        "locks": {
            "paper_trading": False,
            "live_trading": False,
            "real_capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
    }
    return manifest


def serialize_and_digest_manifest(manifest: Dict[str, Any]) -> tuple[bytes, str]:
    """Deterministically serialize manifest to bytes with trailing newline and compute SHA-256."""
    raw = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return raw, digest


def verify_write_preconditions(
    commit_sha: str,
    output_path: Path = STAGE_C_RECOVERY_BINDING_PATH,
    repo_root: Optional[Path] = None,
) -> None:
    """Verify strict fail-closed write-mode invariants before writing Stage C-B manifest.

    1. Current branch must be 'main'.
    2. Local HEAD must match 'origin/main'.
    3. Supplied commit SHA must match 'origin/main'.
    4. Tracked working tree must be clean.
    5. Target Stage C-B manifest must not already exist.
    """
    # 1. Current branch = main
    branch_res = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    current_branch = branch_res.stdout.strip()
    if current_branch != "main":
        raise DataContractError(
            f"WRITE_MODE_NOT_ON_MAIN_BRANCH: current branch is '{current_branch}'. "
            "Stage C-B manifest creation strictly requires current branch 'main'."
        )

    # 2. Resolve origin/main
    origin_res = subprocess.run(
        ["git", "rev-parse", "origin/main"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if origin_res.returncode != 0:
        raise DataContractError("WRITE_MODE_ORIGIN_MAIN_UNRESOLVED: cannot resolve 'origin/main'.")
    origin_main = origin_res.stdout.strip().lower()

    # 3. Local HEAD == origin/main
    head_res = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    local_head = head_res.stdout.strip().lower()
    if local_head != origin_main:
        raise DataContractError(
            f"WRITE_MODE_LOCAL_HEAD_DIVERGED: local HEAD ({local_head}) != origin/main ({origin_main})."
        )

    # 4. Supplied commit == origin/main
    if commit_sha.lower() != origin_main:
        raise DataContractError(
            f"WRITE_MODE_COMMIT_NOT_ORIGIN_MAIN: supplied commit {commit_sha.lower()} != origin/main ({origin_main}). "
            "Stage C-B binding must strictly bind the current canonical origin/main integration HEAD."
        )

    # 5. Tracked working tree clean
    status_res = subprocess.run(
        ["git", "status", "--porcelain", "-uno"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if status_res.stdout.strip():
        raise DataContractError(
            "WRITE_MODE_DIRTY_WORKING_TREE: tracked working tree is modified. "
            "Must be clean before Stage C-B creation."
        )

    # 6. Target file absent
    if output_path.exists():
        raise DataContractError(
            f"STAGE_C_B_ALREADY_EXISTS_IMMUTABLE: {output_path} already exists. "
            "Stage C-B manifest is create-once and cannot be overwritten."
        )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic builder for Stage C-B recovery binding manifest."
    )
    parser.add_argument(
        "--commit-sha",
        required=True,
        help="Canonical integration commit SHA (40 hex characters).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        default=False,
        help="Write manifest to disk. If not specified, performs DRY-RUN only.",
    )
    return parser.parse_args(argv)


def main(
    argv: Optional[List[str]] = None,
    _output_path: Optional[Path] = None,
    _repo_root: Optional[Path] = None,
) -> int:
    args = parse_args(argv)
    print("=== HYP_011 STAGE C-B BINDING BUILDER ===")

    target_path = _output_path or STAGE_C_RECOVERY_BINDING_PATH

    if args.write:
        # Steps 1 to 5: verify strict write-mode preconditions before any commit processing
        verify_write_preconditions(
            commit_sha=args.commit_sha,
            output_path=target_path,
            repo_root=_repo_root,
        )

    commit_utc = get_git_commit_info(
        commit_sha=args.commit_sha,
        repo_root=_repo_root,
    )
    print(f"Commit SHA:       {args.commit_sha}")
    print(f"Commit UTC:       {commit_utc.isoformat()}")

    calendar = NyseCa1Calendar()
    manifest = build_stage_c_b_manifest(args.commit_sha, commit_utc, calendar)
    raw_bytes, digest = serialize_and_digest_manifest(manifest)

    print(f"Activation:       {manifest['activation_session']}")
    print(f"Missed Sessions:  {manifest['missed_unobserved_sessions']}")
    print(f"Manifest Digest:  {digest}")

    if not args.write:
        print("\n--- MANIFEST JSON (DRY-RUN) ---")
        print(raw_bytes.decode("utf-8"))
        print("DRY-RUN: manifest not written to disk. Pass --write to execute creation.")
        print(f"TARGET_FILE_ABSENT = {not target_path.exists()}")
        return 0

    # Atomic create-exclusive write (mode 'xb')
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(target_path, "xb") as handle:
            handle.write(raw_bytes)
    except FileExistsError as exc:
        raise DataContractError(
            f"STAGE_C_B_ALREADY_EXISTS_IMMUTABLE: {target_path} exists and cannot be overwritten."
        ) from exc

    print(f"WROTE MANIFEST:   {target_path}")
    print(f"SHA-256:          {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
