"""Reviewed external operator driver; copy outside Git and run on pinned runtime.

Persistent exclusive claims precede HTTP. Failed/partial claims are consumed;
never delete them to retry. No changes to pinned RI01 or scientific contracts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.core.runtime_identity import get_current_runtime_sha
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.evidence import content_sha256, validate_external_evidence_root, write_immutable_json
from acash.research.ri01.probe import RI01ProbeAuthority, RI01ProbeClient

PINNED_RUNTIME = "cf63f15800099967f4c45d3df66e87a66a012eac"


class _DispatchWindowEnforcingTransport(httpx.BaseTransport):
    """Fail-closed dispatch-time authority window enforcement before every HTTP request."""

    def __init__(
        self,
        inner: httpx.BaseTransport,
        authority: RI01ProbeAuthority,
        calendar: NyseCa1Calendar,
        runtime: str,
        clock: Callable[[], datetime],
    ) -> None:
        self._inner = inner
        self._authority = authority
        self._calendar = calendar
        self._runtime = runtime
        self._clock = clock

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        current_time = self._clock()
        self._authority.validate(current_time, self._runtime, self._calendar)
        return self._inner.handle_request(request)

    def close(self) -> None:
        self._inner.close()


def execute_once(
    authority: RI01ProbeAuthority,
    claims_dir: Path,
    expected_driver_sha256: str,
    *,
    transport: Optional[httpx.BaseTransport] = None,
    now: Optional[Union[datetime, Callable[[], datetime]]] = None,
) -> Dict[str, Any]:
    """One Canary2 operation. Claims persist across processes and all failures."""
    driver_path = Path(__file__).resolve()
    driver_sha = content_sha256(driver_path.read_bytes())
    if driver_sha != expected_driver_sha256:
        raise DataContractError("CANARY_DRIVER_HASH_MISMATCH")
    runtime = get_current_runtime_sha()
    if runtime != PINNED_RUNTIME or authority.runtime_sha != PINNED_RUNTIME:
        raise DataContractError("CANARY_RUNTIME_MISMATCH")

    clock: Callable[[], datetime]
    if callable(now):
        clock = now
    elif isinstance(now, datetime):
        clock = lambda: now
    else:
        clock = lambda: datetime.now(timezone.utc)

    instant = clock()
    calendar = NyseCa1Calendar()
    authority.validate(instant, runtime, calendar)
    if authority.session.isoformat() != "2018-06-01" or authority.capability != "bars" or authority.max_requests != 3:
        raise DataContractError("CANARY2_SCOPE_MISMATCH")
    root = validate_external_evidence_root(authority.evidence_root)
    claims = validate_external_evidence_root(claims_dir)
    if root == claims or root in claims.parents or claims in root.parents:
        raise DataContractError("CANARY_CLAIMS_ROOT_OVERLAP")
    if not root.is_dir() or any(root.iterdir()):
        raise DataContractError("CANARY_ROOT_NOT_EMPTY_OR_MISSING")
    receipt = {
        "status": "START_RESERVED_NOT_PROOF_OF_PROVIDER_RECEIPT",
        "authority_id": authority.authority_id, "authority_sha256": authority.authority_sha256,
        "runtime_sha": runtime, "evidence_root": str(root),
        "driver_path": str(driver_path), "driver_sha256": driver_sha,
        "reserved_at_utc": instant.isoformat(), "max_requests": 3,
    }
    # Identity blocks altered windows/root under the same ID. Root identity
    # blocks different authorities targeting the same canonical directory.
    # Exclusive writers are race-safe; no rollback permits a second attempt.
    identity_key = content_sha256(authority.authority_id)
    root_key = content_sha256(os.path.normcase(str(root)))
    write_immutable_json(claims / f"authority-id-{identity_key}.json", receipt)
    write_immutable_json(claims / f"authority-hash-{authority.authority_sha256}.json", receipt)
    write_immutable_json(claims / f"root-{root_key}.json", receipt)
    write_immutable_json(root / "single-operation-start.json", receipt)

    inner_transport = transport if transport is not None else httpx.HTTPTransport()
    enforcing_transport = _DispatchWindowEnforcingTransport(
        inner=inner_transport,
        authority=authority,
        calendar=calendar,
        runtime=runtime,
        clock=clock,
    )
    client = RI01ProbeClient(transport=enforcing_transport)
    failure: Optional[str] = None
    try:
        # Recheck the real clock immediately before HTTP, after reservations.
        authority.validate(clock(), runtime, calendar)
        client.fetch_bars(authority, calendar, clock())
    except Exception as exc:
        failure = type(exc).__name__  # Never persist arbitrary provider/error text.
    finally:
        client._http.close()

    target_dir = root / authority.session.isoformat() / "bars"
    manifest_path = target_dir / "manifest.json"
    qual_path = target_dir / "qualification.json"

    retrieval_status: Optional[str] = None
    if manifest_path.is_file():
        try:
            retrieval_status = json.loads(manifest_path.read_text()).get("status")
        except Exception:
            pass

    qualification_status: Optional[str] = None
    if client.last_qualification_record is not None:
        qualification_status = client.last_qualification_record.status
    elif qual_path.is_file():
        try:
            qualification_status = json.loads(qual_path.read_text()).get("status")
        except Exception:
            pass

    result: Dict[str, Any] = {
        "authority_sha256": authority.authority_sha256,
        "driver_sha256": driver_sha,
        "runtime_sha": runtime,
        "local_http_invocations": client.requests_issued,
        "failure_type": failure,
        "retrieval_status": retrieval_status,
        "qualification_status": qualification_status,
        "requires_independent_disk_audit": True,
    }
    write_immutable_json(root / "single-operation-result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority-file", required=True)
    parser.add_argument("--claims-dir", required=True)
    parser.add_argument("--expected-driver-sha256", required=True)
    parser.add_argument("--execute-approved", action="store_true")
    args = parser.parse_args()
    if not args.execute_approved:
        raise DataContractError("CANARY_EXPLICIT_APPROVAL_REQUIRED")
    if get_current_runtime_sha(Path.cwd()) != PINNED_RUNTIME:
        raise DataContractError("CANARY_CHECKOUT_NOT_PINNED")
    import subprocess
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise DataContractError("CANARY_CHECKOUT_DIRTY")
    authority = RI01ProbeAuthority.from_dict(json.loads(Path(args.authority_file).read_text()))
    result = execute_once(authority, Path(args.claims_dir), args.expected_driver_sha256)
    print(json.dumps(result))
    if result.get("failure_type") is not None or result.get("qualification_status") != "QUALIFIED":
        sys.exit(1)


if __name__ == "__main__":
    main()
