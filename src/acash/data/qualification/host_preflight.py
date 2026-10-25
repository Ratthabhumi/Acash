"""Offline host preflight for a future acquisition host (no network, no secrets read).

Reports observations and explicit limitations; it never certifies durability.
The only filesystem mutation is one create-once probe file inside a dedicated
probe directory under the evidence root, removed after the check.
"""

from __future__ import annotations

import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from acash.core.domain.exceptions import DataContractError
from acash.evidence.roots import validate_external_evidence_root

PREFLIGHT_SCHEMA = "ACASH_OFFLINE_HOST_PREFLIGHT_V1"
_CREDENTIAL_ENV_PREFIXES = ("APCA_", "ALPACA_")

DURABILITY_LIMITATIONS: Mapping[str, str] = {
    "PROCESS_CRASH": "CREATE_ONCE_AND_FSYNC_ATTEMPTED_NOT_TESTED_UNDER_KILL",
    "OS_CRASH": "UNPROVEN",
    "POWER_LOSS": "UNPROVEN",
}


def run_offline_host_preflight(evidence_root: Path, *, required_free_bytes: int) -> dict[str, Any]:
    if not isinstance(required_free_bytes, int) or isinstance(required_free_bytes, bool) or required_free_bytes <= 0:
        raise DataContractError("PREFLIGHT_BAD_REQUIRED_BYTES.")
    root = validate_external_evidence_root(evidence_root)
    if not root.is_dir():
        raise DataContractError(f"PREFLIGHT_ROOT_NOT_DIRECTORY: {root}.")
    probe_dir = root / "preflight_probe"
    probe_dir.mkdir(exist_ok=True)
    probe = probe_dir / f"probe_{uuid.uuid4().hex}.tmp"
    fsync_ok = True
    try:
        with open(probe, "xb") as handle:
            handle.write(b"acash-preflight")
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                fsync_ok = False
        replaced = probe.with_suffix(".done")
        os.replace(probe, replaced)
        replaced.unlink()
    except OSError as exc:
        raise DataContractError(f"PREFLIGHT_NOT_WRITABLE: {exc}.") from exc
    free = shutil.disk_usage(root).free
    clock = time.get_clock_info("time")
    credential_env = sorted(
        key for key in os.environ if key.upper().startswith(_CREDENTIAL_ENV_PREFIXES)
    )
    return {
        "schema": PREFLIGHT_SCHEMA,
        "evidence_root_external": True,
        "writable_create_once": True,
        "file_fsync_call_succeeded": fsync_ok,
        "atomic_rename_same_directory": True,
        "free_bytes": free,
        "required_free_bytes": required_free_bytes,
        "storage_sufficient": free >= required_free_bytes,
        "clock_source": clock.implementation,
        "clock_resolution_s": clock.resolution,
        "clock_adjustable": clock.adjustable,
        "clock_trusted_timestamp": False,
        "credential_env_names_present": credential_env,
        "credential_values_read": False,
        "network_activation": "DISABLED_BY_CONSTRUCTION_MOCKTRANSPORT_ONLY",
        "restart_behavior": "RUN_ID_NOT_REUSABLE_INTERRUPTED_RUNS_NEVER_COMPLETE",
        "durability": dict(DURABILITY_LIMITATIONS),
        "ready_for_real_acquisition": False,
    }


__all__ = ["DURABILITY_LIMITATIONS", "PREFLIGHT_SCHEMA", "run_offline_host_preflight"]
