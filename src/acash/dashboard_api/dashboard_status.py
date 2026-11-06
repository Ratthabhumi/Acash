"""Read-only dashboard system status (``/api/upi/status/``).

This exposes sanitized operational status, framework integration matrix and Forward Shadow
progress to the authenticated dashboard. It never runs external framework processes, never
reveals private paths or secrets, and never fabricates a status.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from acash.core.domain.exceptions import DataContractError
from acash.dashboard_api import private_input as pi
from acash.integrations import framework_integration as fi
from acash.ops.ops_report import build_report
from acash.ppds.private_observation import SCHEMA_V1_2, odr_state

PREFIX = "/api/upi/status/"
ROUTES = {"system": ("GET",)}


def _private_dir() -> Path:
    return pi._private_dir()


def _ops_report() -> Dict[str, Any]:
    try:
        return build_report(_private_dir())
    except Exception as exc:
        return {"status": "OPS_REPORT_UNAVAILABLE", "code": type(exc).__name__}


def _count(v: Any) -> int:
    if isinstance(v, list):
        return len(v)
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    return 0


def _shadow_view() -> Dict[str, Any]:
    shadow_dir = _private_dir() / "shadow"
    protocol_path = shadow_dir / "protocol_v2.json"
    journal_path = shadow_dir / "journal.json"
    protocol: Dict[str, Any] = {}
    journal: Dict[str, Any] = {"signals": 0, "outcomes": 0}
    try:
        import json
        if protocol_path.is_file():
            protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        if journal_path.is_file():
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    prot = protocol.get("protocol") or {}
    return {
        "protocol_hash": protocol.get("sha256"),
        "registered_at": prot.get("registered_at"),
        "qualified_universe": prot.get("qualified_universe"),
        "first_eligible_session": prot.get("first_eligible_session"),
        "signals": _count(journal.get("signals")),
        "outcomes": _count(journal.get("outcomes")),
        "state": "FORWARD_OBSERVATIONS_PENDING" if not journal.get("outcomes") else "FORWARD_OBSERVED",
        "legacy_tournament_separate": True,
    }


def system() -> pi.Result:
    matrix = fi.acceptance_matrix()
    frameworks = []
    for row in matrix.get("frameworks", []):
        frameworks.append({
            "framework_id": row["framework_id"],
            "adapter_present": row.get("adapter_present"),
            "package_installed": row.get("package_installed"),
            "native_smoke_verified": row.get("native_smoke_verified"),
            "input_rights_qualified": row.get("input_rights_qualified"),
            "pit_validated": row.get("pit_validated"),
            "result_reconciled": row.get("result_reconciled"),
            "dashboard_connected": row.get("dashboard_connected"),
            "production_enabled": row.get("production_enabled"),
            "blocked_reason": row.get("blocked_reason"),
            "execution_authority": row.get("execution_authority"),
            "role": row.get("role"),
            "license": row.get("license"),
        })
    return 200, {
        "status": "OK",
        "ops": _ops_report(),
        "frameworks": frameworks,
        "shadow": _shadow_view(),
        "note": "All statuses are read-only evidence; no framework process was executed to render this page.",
    }


def handle(method: str, name: str, body: Any, service: Optional[pi.InputService] = None) -> pi.Result:
    observation = pi.authority()["odr_001"]
    if observation != "RATIFIED":
        return 403, {"status": "AUTHORIZATION_REQUIRED", "odr_001": observation}
    try:
        if name == "system":
            return system()
    except DataContractError as exc:
        return 422, {"status": "STATUS_REFUSED", **pi._code(exc)}
    return 404, {"status": "NOT_FOUND"}
