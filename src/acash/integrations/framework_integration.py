"""Provider-neutral framework integration boundary.

Each adapter emits the same versioned result and never gains execution authority. ACASH remains the only
authority for accounting, validation and readiness. Third-party runtimes are optional: when a package or
service is not installed the adapter reports a blocked reason instead of pretending a native run happened.

All adapters are offline by default: no network request, no model call and no order endpoint is reachable
from this module.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError

SCHEMA = "ACASH_FRAMEWORK_RESULT_V1"
MATRIX_SCHEMA = "ACASH_FRAMEWORK_MATRIX_V1"
NO_EXECUTION = "NONE"

FRAMEWORKS: Dict[str, Dict[str, Any]] = {
    "NAUTILUS_TRADER": {"version": "1.231.0", "license": "LGPL-3.0", "module": "nautilus_trader",
                        "role": "Event-driven offline backtest and fill/accounting verification",
                        "isolation": "in-process pinned dependency (existing bridge)"},
    "OPENBB": {"version": "5.x", "license": "Apache-2.0", "module": "openbb",
               "role": "Read-only fundamentals, filings and macro evidence",
               "isolation": "optional dependency; provider calls disabled by default"},
    "TRADINGAGENTS": {"version": "0.x", "license": "Apache-2.0", "module": "tradingagents",
                      "role": "Validate ChatGPT research packets; no autonomous inference",
                      "isolation": "optional dependency; LLM calls disabled by default"},
    "FREQTRADE": {"version": "2024.x", "license": "GPL-3.0", "module": "freqtrade",
                  "role": "Crypto-only offline backtest sandbox via subprocess",
                  "isolation": "separate process/venv; no GPL code copied into the core"},
    "QUANTDINGER": {"version": "API v1", "license": "Apache-2.0 (backend)",
                    "module": "quantdinger", "role": "Read-only experiment/backtest result import",
                    "isolation": "remote/isolated service; read scope only"},
}


@dataclass(frozen=True)
class FrameworkResult:
    framework_id: str
    adapter_version: str
    integration_status: str
    native_runtime: str
    input_scope: str
    input_sha256: Optional[str]
    pit_qualified: bool
    rights: str
    result_type: str
    execution_authority: str = NO_EXECUTION
    blocked_reason: Optional[str] = None
    limitations: Sequence[str] = field(default_factory=tuple)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA, "framework_id": self.framework_id, "adapter_version": self.adapter_version,
            "integration_status": self.integration_status, "native_runtime": self.native_runtime,
            "input_scope": self.input_scope, "input_sha256": self.input_sha256,
            "pit_qualified": self.pit_qualified, "rights": self.rights, "result_type": self.result_type,
            "execution_authority": self.execution_authority, "blocked_reason": self.blocked_reason,
            "limitations": list(self.limitations), "diagnostics": dict(self.diagnostics),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def runtime_available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


class NautilusAdapter:
    """Existing bridge only: reports availability and refuses to fabricate a native run."""

    framework_id = "NAUTILUS_TRADER"
    adapter_version = "acash.bridge.v1"

    def status(self) -> FrameworkResult:
        installed = runtime_available("nautilus_trader")
        return FrameworkResult(
            self.framework_id, self.adapter_version,
            "ADAPTER_IMPLEMENTED" if installed else "BLOCKED",
            "PINNED_1_231_0" if installed else "NOT_INSTALLED", "none", None, False,
            "ACASH_QUALIFIED_ONLY",
            "NATIVE_RUNTIME_STATUS" if installed else "BLOCKED",
            blocked_reason=None if installed else "NAUTILUS_RUNTIME_NOT_INSTALLED",
            limitations=("offline replay must use qualified or synthetic data", "no broker dispatch"))


class OpenBBAdapter:
    """Normalise one issuer fact into evidence; provider access stays disabled."""

    framework_id = "OPENBB"
    adapter_version = "acash.openbb.v5"

    def normalise_issuer_fact(self, fact: Mapping[str, Any]) -> FrameworkResult:
        required = ("symbol", "concept", "value", "unit", "source_url", "published_at", "available_at")
        missing = [key for key in required if not fact.get(key)]
        if missing:
            return FrameworkResult(self.framework_id, self.adapter_version, "BLOCKED",
                                   "NOT_INVOKED", "issuer_fact", None, False, "UNKNOWN",
                                   "BLOCKED", blocked_reason=f"OPENBB_EVIDENCE_INCOMPLETE: {missing}")
        published = datetime.fromisoformat(str(fact["published_at"]))
        available = datetime.fromisoformat(str(fact["available_at"]))
        if published.tzinfo is None or available.tzinfo is None or available < published:
            raise DataContractError("OPENBB_PIT_INVALID: timestamps must be aware and available >= published.")
        record = {"symbol": fact["symbol"], "concept": fact["concept"], "value": str(fact["value"]),
                  "unit": fact["unit"], "source_url": fact["source_url"],
                  "published_at": published.isoformat(), "available_at": available.isoformat(),
                  "provider": fact.get("provider", "UNSPECIFIED")}
        return FrameworkResult(self.framework_id, self.adapter_version, "ADAPTER_IMPLEMENTED",
                               "NOT_INVOKED", f"issuer:{fact['symbol']}", _digest(record), True,
                               "READ_ONLY_DOCUMENTED_SOURCE", "FUNDAMENTAL_EVIDENCE",
                               limitations=("provider rights remain independent of the OpenBB licence",),
                               diagnostics={"record": record})


class TradingAgentsAdapter:
    """Validate a ChatGPT research packet; never call a model or an external tool."""

    framework_id = "TRADINGAGENTS"
    adapter_version = "acash.packet.v1"

    def validate_packet(self, packet: Mapping[str, Any]) -> FrameworkResult:
        required = ("issuer", "as_of", "thesis", "citations", "available_at")
        missing = [key for key in required if key not in packet or (key != "citations" and not packet.get(key))]
        if missing:
            return FrameworkResult(self.framework_id, self.adapter_version, "BLOCKED", "NOT_INVOKED",
                                   "research_packet", None, False, "CHATGPT_SUPPLIED", "BLOCKED",
                                   blocked_reason=f"RESEARCH_PACKET_INCOMPLETE: {missing}")
        if not isinstance(packet["citations"], list) or not packet["citations"]:
            raise DataContractError("RESEARCH_PACKET_CITATIONS_REQUIRED.")
        available = datetime.fromisoformat(str(packet["available_at"]))
        as_of = datetime.fromisoformat(str(packet["as_of"]))
        if available.tzinfo is None or as_of.tzinfo is None or available < as_of:
            raise DataContractError("RESEARCH_PACKET_PIT_INVALID.")
        record = {"issuer": packet["issuer"], "as_of": as_of.isoformat(), "thesis": packet["thesis"],
                  "citations": list(packet["citations"]), "available_at": available.isoformat()}
        return FrameworkResult(self.framework_id, self.adapter_version, "ADAPTER_IMPLEMENTED",
                               "NOT_INVOKED", f"issuer:{packet['issuer']}", _digest(record), True,
                               "OWNER_SUPPLIED_RESEARCH", "EXTERNAL_RESEARCH_OPINION",
                               limitations=("not canonical investment evidence", "autonomous agents disabled",
                                            "mocked-compatibility only, no live inference"),
                               diagnostics={"record": record, "autonomous_research": "DISABLED"})


class FreqtradeAdapter:
    """Parse a native backtest artifact produced by an isolated process; never run the binary here."""

    framework_id = "FREQTRADE"
    adapter_version = "acash.backtest.v1"

    def import_backtest(self, artifact: Mapping[str, Any]) -> FrameworkResult:
        required = ("strategy", "pairs", "timerange", "total_trades", "profit_total", "backtest_start")
        missing = [key for key in required if key not in artifact]
        if missing:
            return FrameworkResult(self.framework_id, self.adapter_version, "BLOCKED", "NOT_INVOKED",
                                   "crypto_backtest", None, False, "SYNTHETIC_ONLY", "BLOCKED",
                                   blocked_reason=f"FREQTRADE_ARTIFACT_INCOMPLETE: {missing}")
        record = {key: artifact[key] for key in required}
        return FrameworkResult(self.framework_id, self.adapter_version, "ADAPTER_IMPLEMENTED",
                               "SUBPROCESS_REQUIRED", "crypto_only", _digest(record), False,
                               "SYNTHETIC_ONLY", "EXTERNAL_ENGINE_RESULT",
                               limitations=("crypto-only", "GPL isolated process", "not applicable to Dime! holdings"),
                               diagnostics={"record": record, "execution_enabled": False})


class QuantDingerAdapter:
    """Read-only result import through an injected transport; T-scope endpoints are refused."""

    framework_id = "QUANTDINGER"
    adapter_version = "acash.qd.v1"
    BASE = "/api/agent/v1"
    ALLOWED = ("/api/agent/v1/experiments", "/api/agent/v1/backtests")

    def __init__(self, transport: Optional[Callable[[str], Mapping[str, Any]]] = None) -> None:
        self.transport = transport

    def read_result(self, path: str) -> FrameworkResult:
        if path not in self.ALLOWED and not any(path.startswith(prefix + "/") for prefix in self.ALLOWED):
            raise DataContractError("QUANTDINGER_SCOPE_REFUSED: only exact read-only agent paths are allowed.")
        if self.transport is None:
            return FrameworkResult(self.framework_id, self.adapter_version, "BLOCKED", "NOT_CONNECTED",
                                   path, None, False, "READ_SCOPE_ONLY", "BLOCKED",
                                   blocked_reason="NATIVE_RUNTIME_NOT_CONNECTED")
        payload = self.transport(path)
        item_id = payload.get("id") or payload.get("experiment_id")
        return FrameworkResult(self.framework_id, self.adapter_version, "ADAPTER_IMPLEMENTED",
                               "REMOTE_READ_ONLY", path, _digest(payload), False, "READ_SCOPE_ONLY",
                               "EXTERNAL_ENGINE_RESULT",
                               limitations=("third-party metrics are not ACASH-qualified performance",),
                               diagnostics={"id": item_id, "keys": sorted(payload)[:10]})


def acceptance_matrix(smoke_evidence: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Dict[str, Any]:
    """Independent dimensions; nothing is promoted because another dimension is true.

    ``smoke_evidence`` must be a recorded native execution (command/API, version, input and output hash).
    Package availability, a fixture test or a timestamp never sets ``native_smoke_verified``.
    """
    evidence = dict(smoke_evidence or {})
    rows: List[Dict[str, Any]] = []
    for framework_id, meta in FRAMEWORKS.items():
        installed = runtime_available(meta["module"])
        record = evidence.get(framework_id) or {}
        recorded = bool(record.get("command") and record.get("version") and record.get("output_sha256"))
        rows.append({
            "framework_id": framework_id,
            "adapter_version": FRAMEWORKS[framework_id]["version"],
            "adapter_present": True,
            "package_installed": installed,
            "native_smoke_verified": recorded,
            "native_smoke": record or None,
            "input_rights_qualified": False,
            "pit_validated": False,
            "result_reconciled": False,
            "dashboard_connected": False,
            "production_enabled": False,
            "blocked_reason": None if recorded else
            ("NATIVE_SMOKE_NOT_RECORDED" if installed else "RUNTIME_NOT_INSTALLED_OR_NOT_CONNECTED"),
            "execution_authority": NO_EXECUTION,
            "license": meta["license"], "isolation": meta["isolation"], "role": meta["role"],
        })
    return {"schema": MATRIX_SCHEMA, "frameworks": rows,
            "note": ("Dimensions are independent: installed != executed != reconciled != production. "
                     "No framework has execution authority.")}
