"""Deterministic builder utility for HYP_011 Stage C-B recovery binding manifest.

This script creates the post-merge Stage C-B operational re-activation binding.
DEFAULTS TO DRY-RUN (no write).
Requires separate explicit human authorization before writing to disk.

Strict invariants:
- Commit SHA must be a valid 40-character hex string.
- Commit SHA must exist in local Git object database.
- Commit SHA must be an ancestor of the canonical integration ref.
- Commit timestamp must be read directly from Git (never manually typed).
- Activation session is derived via NyseCa1Calendar only.
- Missed sessions are derived via NyseCa1Calendar only, and must include 2026-09-28.
- Canonical JSON serialization with newline, hashed via SHA-256.
- Zero price data, zero Alpaca access, zero state.json modification, zero systemd changes.
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
    canonical_ref: Optional[str] = "origin/main",
    skip_ancestor_check: bool = False,
) -> datetime:
    """Validate Git commit existence and ancestry; return author/committer UTC timestamp."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit_sha):
        raise DataContractError(f"INVALID_COMMIT_SHA_FORMAT: '{commit_sha}'. Must be 40 hex chars.")

    # 1. Verify existence in local git object database
    cat_res = subprocess.run(
        ["git", "cat-file", "-e", f"{commit_sha}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if cat_res.returncode != 0:
        raise DataContractError(f"GIT_COMMIT_NOT_FOUND: {commit_sha} does not exist in local Git DB.")

    # 2. Verify ancestry from canonical_ref if requested
    if not skip_ancestor_check and canonical_ref:
        anc_res = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit_sha, canonical_ref],
            capture_output=True,
            text=True,
        )
        if anc_res.returncode != 0:
            raise DataContractError(
                f"GIT_COMMIT_NOT_ANCESTOR: {commit_sha} is not an ancestor of {canonical_ref}."
            )

    # 3. Read machine-readable ISO commit timestamp
    show_res = subprocess.run(
        ["git", "show", "-s", "--format=%cI", commit_sha],
        capture_output=True,
        text=True,
        check=True,
    )
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
        "--canonical-ref",
        default="origin/main",
        help="Canonical branch ref to verify commit ancestry against (default: origin/main).",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=STAGE_C_RECOVERY_BINDING_PATH,
        help="Target output manifest path.",
    )
    parser.add_argument(
        "--skip-ancestor-check",
        action="store_true",
        help="Skip git ancestry check (strictly for unit tests in temporary repos).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        default=False,
        help="Write manifest to disk. If not specified, performs DRY-RUN only.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    print("=== HYP_011 STAGE C-B BINDING BUILDER ===")

    commit_utc = get_git_commit_info(
        commit_sha=args.commit_sha,
        canonical_ref=args.canonical_ref,
        skip_ancestor_check=args.skip_ancestor_check,
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
        print(f"TARGET_FILE_ABSENT = {not args.output_path.exists()}")
        return 0

    # Write under authorization
    target_path = Path(args.output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(raw_bytes)
    print(f"WROTE MANIFEST:   {target_path}")
    print(f"SHA-256:          {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
