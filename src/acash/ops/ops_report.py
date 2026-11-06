"""Read-only operational acceptance report builder (used by scripts/ops_doctor.py and dashboard)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        doc: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc


def build_report(private_dir: Path) -> Dict[str, Any]:
    """Read-only operational acceptance report.

    ``private_dir`` is the ``data/private`` root. The report never contacts the collector,
    never restarts services and never writes anything.
    """
    private = private_dir.resolve()
    warehouse = private / "market_warehouse"
    health = _json(warehouse / "health.json") or {}
    manifest = _json(warehouse / "manifest.json") or {}
    sync = _json(warehouse / "sync_state.json") or {}
    shadow_protocol = _json(private / "shadow" / "protocol_v2.json") or {}
    journal = _json(private / "shadow" / "journal.json") or {}
    report = _json(warehouse / "backfill_report.json") or {}
    partitions = len(manifest.get("partitions") or {})
    signals = len(journal.get("signals") or [])
    outcomes = len(journal.get("outcomes") or [])
    scheduled = sync.get("scheduled_by") == "TASK_SCHEDULER"
    successful = sync.get("status") in ("SYNCED", "NO_CHANGE")
    return {
        "schema": "ACASH_OPS_READINESS_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "collector": {
            "storage_rights": health.get("storage_rights"),
            "covered": (health.get("coverage") or {}).get("covered"),
            "partial": (health.get("coverage") or {}).get("partial"),
            "next_run_ict": (health.get("next_run") or {}).get("next_run_ict"),
            "latest_eligible_session": (health.get("latest_eligible_session") or {}).get("session_date"),
            "note": "collector health is read from the last persisted run; this report does not contact the host",
        },
        "warehouse": {
            "partitions": partitions,
            "union_last": (report.get("coverage") or {}).get("union_last"),
            "research_covered": (report.get("coverage") or {}).get("covered"),
            "research_partial_limited_history": (report.get("coverage") or {}).get("partial_limited_history"),
            "research_partial": (report.get("coverage") or {}).get("partial"),
            "research_missing": (report.get("coverage") or {}).get("missing"),
        },
        "windows_sync": {
            "status": sync.get("status"),
            "synced_at": sync.get("synced_at"),
            "partitions_verified": sync.get("partitions_verified"),
            "scheduled_sync_accepted": bool(scheduled and successful),
            "note": ("a registered Task Scheduler job is not evidence of a scheduled run; acceptance needs a "
                     "sync record written by the scheduled execution"),
        },
        "shadow": {
            "protocol_sha256": shadow_protocol.get("sha256"),
            "registered_at": (shadow_protocol.get("protocol") or {}).get("registered_at"),
            "signals": signals,
            "outcomes": outcomes,
            "state": "FORWARD_OBSERVATIONS_PENDING" if outcomes == 0 else "FORWARD_OBSERVED",
        },
        "backup": {"status": "NOT_CONFIGURED",
                   "note": "no independent destination and no restore drill have been evidenced"},
    }
