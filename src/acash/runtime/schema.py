"""Phase 10: Canonical Operational Domain Contracts & Configuration (Slice 1).

Strictly enforces:
1. Five-Way Sovereign Separation:
   Research (8.5) != Allocation (8) != Runtime Orchestration (10) != Risk (9) != Execution (7).
2. Runtime Health != Kill Switch:
   RuntimeHealthStatus (Operational Health) is strictly separated from KillSwitchState (Risk Gate).
3. Dual-Clock & Idempotency Discipline:
   Logical evaluation time (as_of_utc) is strictly distinguished from system time (wall_clock_utc).
   No ambient datetime.now() inside deterministic calculations.
4. Historical Evidence Invariant:
   Research Qualification (Historical Dossier) != Current Runtime Health (Operating Status).
   Runtime degradation blocks execution without mutating historical Phase 8.5 dossiers.
5. Zero Direct Execution Authority:
   Phase 10 orchestrates flow; it has zero direct broker wire/socket methods.
"""

from datetime import datetime, timezone
from enum import Enum
import hashlib
import re
from typing import Any, Mapping, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.types import freeze_mapping
from acash.core.serialization import CanonicalConfigSerializer


SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _validate_sha256(v: str, field_name: str = "digest") -> str:
    """Validate 64-character lowercase hexadecimal SHA-256 string."""
    if not isinstance(v, str) or not SHA256_HEX_PATTERN.match(v):
        raise DataContractError(
            f"Invalid {field_name}: '{v}'. Expected 64-character lowercase hex SHA-256 digest."
        )
    return v


def _ensure_utc(dt: Any, field_name: str = "timestamp") -> datetime:
    """Validate and enforce timezone-aware UTC datetime."""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception as e:
            raise DataContractError(f"Invalid ISO format for {field_name}: '{dt}'.") from e

    if not isinstance(dt, datetime):
        raise DataContractError(f"{field_name} must be a datetime instance, got {type(dt)}.")

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise DataContractError(f"{field_name} must be timezone-aware UTC. Naive datetime is forbidden.")

    return dt.astimezone(timezone.utc)


# ============================================================================
# 1. ENUMS
# ============================================================================


class RuntimeRegime(str, Enum):
    """Authoritative operational regime of the ACASH runtime system."""

    PRE_MARKET = "PRE_MARKET"            # Health check, data sync, trust store loading
    MARKET_OPEN = "MARKET_OPEN"          # Continuous tick streaming, real-time heartbeat
    REBALANCE_PULSE = "REBALANCE_PULSE"  # Scheduled tournament, risk evaluation, admission dispatch
    POST_MARKET_CLOSE = "POST_MARKET_CLOSE"  # EOD equity snapshot, ledger sealing, metric reset
    MAINTENANCE = "MAINTENANCE"          # Off-hours integrity validation, archival


class RuntimeHealthStatus(str, Enum):
    """Operational health status of the runtime system.

    Strict Invariant: RuntimeHealthStatus != KillSwitchState.
    """

    RUNTIME_HEALTHY = "RUNTIME_HEALTHY"    # All feeds nominal, latency < 1500ms, full operation
    RUNTIME_DEGRADED = "RUNTIME_DEGRADED"  # Transient latency/data age warning, rebalance paused
    RUNTIME_PAUSED = "RUNTIME_PAUSED"      # Broker disconnect, operator pause, 0 orders admitted
    RUNTIME_HALTED = "RUNTIME_HALTED"      # Fatal integrity breach, unhandled crash, clock rollback


class CycleOutcome(str, Enum):
    """Deterministic terminal status of an individual operational cycle."""

    SUCCESS = "SUCCESS"
    RISK_REJECTED = "RISK_REJECTED"
    DATA_STALE = "DATA_STALE"
    DISPATCH_FAILED = "DISPATCH_FAILED"
    INTERRUPTED_CRASH = "INTERRUPTED_CRASH"
    IDEMPOTENT_SKIPPED = "IDEMPOTENT_SKIPPED"


# ============================================================================
# 2. CYCLE IDENTITY & DUAL-CLOCK CONTRACT
# ============================================================================


class CycleIdentity(BaseModel):
    """Immutable, deterministic identity of a single operational cycle pulse."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cycle_id: str = Field(description="Deterministic unique cycle identifier.")
    as_of_utc: datetime = Field(description="Logical evaluation timestamp (discrete data time).")
    regime: RuntimeRegime = Field(description="Operational regime for this cycle.")
    sequence_number: int = Field(default=0, ge=0, description="Monotonically increasing sequence index.")
    cycle_digest: str = Field(default="", description="Canonical SHA-256 digest of this cycle identity.")

    @model_validator(mode="before")
    @classmethod
    def validate_identity_and_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_cid = str(data.get("cycle_id", "")).strip()
            if not raw_cid:
                raise DataContractError("cycle_id must be a non-empty string.")

            as_of = _ensure_utc(data.get("as_of_utc"), "as_of_utc")
            regime = data.get("regime")
            if isinstance(regime, str):
                try:
                    regime = RuntimeRegime(regime)
                except ValueError as e:
                    raise DataContractError(f"Invalid regime: '{regime}'.") from e
            elif not isinstance(regime, RuntimeRegime):
                raise DataContractError(f"regime must be a RuntimeRegime enum, got {type(regime)}.")

            seq = int(data.get("sequence_number", 0))
            if seq < 0:
                raise DataContractError("sequence_number must be non-negative.")

            payload = {
                "cycle_id": raw_cid,
                "as_of_utc": as_of.isoformat(),
                "regime": regime.value,
                "sequence_number": seq,
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
            computed_digest = hashlib.sha256(canonical_bytes).hexdigest()

            data["cycle_id"] = raw_cid
            data["as_of_utc"] = as_of
            data["regime"] = regime
            data["sequence_number"] = seq
            data["cycle_digest"] = computed_digest
        return data


# ============================================================================
# 3. RUNTIME POLICY CONFIGURATION
# ============================================================================


class RuntimePolicyConfig(BaseModel):
    """Immutable, validated runtime orchestration policy configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_version: str = Field(default="v1.0.0", description="Semantic policy version.")
    rebalance_cron: str = Field(default="0 14 * * 1-5", description="Rebalance cadence cron.")
    heartbeat_interval_seconds: int = Field(default=5, ge=1, description="Telemetry heartbeat interval.")
    max_market_data_age_ms: int = Field(default=1500, ge=100, description="Data freshness threshold.")
    max_clock_drift_ms: int = Field(default=500, ge=50, description="Maximum wall-clock drift tolerance.")
    cycle_timeout_seconds: int = Field(default=30, ge=1, description="Maximum execution timeout per pulse.")
    max_degraded_cycles_before_pause: int = Field(default=3, ge=1, description="Degraded hysteresis threshold.")
    persistence_path: str = Field(default="data/runtime/operational_ledger.jsonl", description="Ledger path.")
    policy_digest: str = Field(default="", description="Canonical SHA-256 digest of this policy.")

    @model_validator(mode="before")
    @classmethod
    def validate_policy_and_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            p_ver = str(data.get("policy_version", "v1.0.0")).strip()
            if not p_ver:
                raise DataContractError("policy_version must be a non-empty string.")

            r_cron = str(data.get("rebalance_cron", "0 14 * * 1-5")).strip()
            if not r_cron:
                raise DataContractError("rebalance_cron must be a non-empty string.")

            hb_sec = int(data.get("heartbeat_interval_seconds", 5))
            max_age = int(data.get("max_market_data_age_ms", 1500))
            max_drift = int(data.get("max_clock_drift_ms", 500))
            timeout_sec = int(data.get("cycle_timeout_seconds", 30))
            max_deg = int(data.get("max_degraded_cycles_before_pause", 3))
            p_path = str(data.get("persistence_path", "data/runtime/operational_ledger.jsonl")).strip()

            if hb_sec < 1 or max_age < 100 or max_drift < 50 or timeout_sec < 1 or max_deg < 1:
                raise DataContractError("Numeric runtime policy parameters violate required positive bounds.")

            payload = {
                "policy_version": p_ver,
                "rebalance_cron": r_cron,
                "heartbeat_interval_seconds": hb_sec,
                "max_market_data_age_ms": max_age,
                "max_clock_drift_ms": max_drift,
                "cycle_timeout_seconds": timeout_sec,
                "max_degraded_cycles_before_pause": max_deg,
                "persistence_path": p_path,
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
            computed_digest = hashlib.sha256(canonical_bytes).hexdigest()

            data["policy_version"] = p_ver
            data["rebalance_cron"] = r_cron
            data["heartbeat_interval_seconds"] = hb_sec
            data["max_market_data_age_ms"] = max_age
            data["max_clock_drift_ms"] = max_drift
            data["cycle_timeout_seconds"] = timeout_sec
            data["max_degraded_cycles_before_pause"] = max_deg
            data["persistence_path"] = p_path
            data["policy_digest"] = computed_digest
        return data


# ============================================================================
# 4. OPERATIONAL EVENT ENVELOPE
# ============================================================================


class OperationalCycleEvent(BaseModel):
    """Immutable ledger record representing an executed operational pulse cycle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cycle_identity: CycleIdentity = Field(description="Deterministic cycle identity.")
    wall_clock_utc: datetime = Field(description="Actual system observation timestamp (NTP synchronized).")
    runtime_health: RuntimeHealthStatus = Field(description="Operational health status during cycle.")

    # Cross-Phase Cryptographic Lineage Digests
    active_dossier_digests: Tuple[str, ...] = Field(default=(), description="Active Phase 8.5 Strategy Dossier hashes.")
    portfolio_state_digest: str = Field(default="", description="Phase 1/8 PortfolioState hash.")
    account_state_digest: str = Field(default="", description="Phase 1/8 AccountState hash.")
    allocation_decision_digest: str = Field(default="", description="Phase 8 AllocationDecision hash.")
    risk_report_digest: str = Field(default="", description="Phase 9 RiskEvaluationReport hash.")
    execution_manifest_digests: Tuple[str, ...] = Field(default=(), description="Phase 7 ExecutionManifest hashes.")

    # State & Outcome
    kill_switch_state_val: str = Field(default="ACTIVE", description="Observed KillSwitchState value.")
    cycle_outcome: CycleOutcome = Field(description="Terminal status of this cycle.")
    error_message: Optional[str] = Field(default=None, description="Error details if cycle failed.")

    # Cryptographic Hash Chaining
    previous_event_digest: str = Field(default="0" * 64, description="Digest of preceding ledger record.")
    event_digest: str = Field(default="", description="Canonical SHA-256 digest of this event.")

    @model_validator(mode="before")
    @classmethod
    def validate_event_and_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            identity = data.get("cycle_identity")
            if isinstance(identity, dict):
                identity = CycleIdentity(**identity)
            elif not isinstance(identity, CycleIdentity):
                raise DataContractError(f"cycle_identity must be a CycleIdentity instance, got {type(identity)}.")

            wall_clock = _ensure_utc(data.get("wall_clock_utc"), "wall_clock_utc")

            # Temporal invariant: wall_clock_utc cannot be arbitrarily before as_of_utc (reject inverted time)
            if wall_clock < identity.as_of_utc:
                raise DataContractError(
                    f"Temporal Inversion: wall_clock_utc ({wall_clock.isoformat()}) cannot precede as_of_utc ({identity.as_of_utc.isoformat()})."
                )

            r_health = data.get("runtime_health")
            if isinstance(r_health, str):
                try:
                    r_health = RuntimeHealthStatus(r_health)
                except ValueError as e:
                    raise DataContractError(f"Invalid runtime_health: '{r_health}'.") from e
            elif not isinstance(r_health, RuntimeHealthStatus):
                raise DataContractError(f"runtime_health must be RuntimeHealthStatus, got {type(r_health)}.")

            outcome = data.get("cycle_outcome")
            if isinstance(outcome, str):
                try:
                    outcome = CycleOutcome(outcome)
                except ValueError as e:
                    raise DataContractError(f"Invalid cycle_outcome: '{outcome}'.") from e
            elif not isinstance(outcome, CycleOutcome):
                raise DataContractError(f"cycle_outcome must be CycleOutcome, got {type(outcome)}.")

            prev_digest = str(data.get("previous_event_digest", "0" * 64)).strip()
            _validate_sha256(prev_digest, "previous_event_digest")

            # Validate digests if present
            port_digest = str(data.get("portfolio_state_digest", "")).strip()
            if port_digest:
                _validate_sha256(port_digest, "portfolio_state_digest")

            acc_digest = str(data.get("account_state_digest", "")).strip()
            if acc_digest:
                _validate_sha256(acc_digest, "account_state_digest")

            alloc_digest = str(data.get("allocation_decision_digest", "")).strip()
            if alloc_digest:
                _validate_sha256(alloc_digest, "allocation_decision_digest")

            risk_digest = str(data.get("risk_report_digest", "")).strip()
            if risk_digest:
                _validate_sha256(risk_digest, "risk_report_digest")

            dossier_digests = tuple(sorted(str(d).strip() for d in data.get("active_dossier_digests", ())))
            for d in dossier_digests:
                _validate_sha256(d, "active_dossier_digest")

            manifest_digests = tuple(sorted(str(m).strip() for m in data.get("execution_manifest_digests", ())))
            for m in manifest_digests:
                _validate_sha256(m, "execution_manifest_digest")

            payload = {
                "cycle_identity_digest": identity.cycle_digest,
                "wall_clock_utc": wall_clock.isoformat(),
                "runtime_health": r_health.value,
                "active_dossier_digests": dossier_digests,
                "portfolio_state_digest": port_digest,
                "account_state_digest": acc_digest,
                "allocation_decision_digest": alloc_digest,
                "risk_report_digest": risk_digest,
                "execution_manifest_digests": manifest_digests,
                "kill_switch_state_val": str(data.get("kill_switch_state_val", "ACTIVE")),
                "cycle_outcome": outcome.value,
                "error_message": str(data.get("error_message")) if data.get("error_message") else None,
                "previous_event_digest": prev_digest,
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
            event_digest = hashlib.sha256(canonical_bytes).hexdigest()

            provided_digest = str(data.get("event_digest", "")).strip()
            if provided_digest and provided_digest != event_digest:
                raise DataContractError(
                    f"Event Digest Mismatch: provided '{provided_digest}' != computed '{event_digest}'. Event payload has been tampered with."
                )

            data["cycle_identity"] = identity
            data["wall_clock_utc"] = wall_clock
            data["runtime_health"] = r_health
            data["active_dossier_digests"] = dossier_digests
            data["portfolio_state_digest"] = port_digest
            data["account_state_digest"] = acc_digest
            data["allocation_decision_digest"] = alloc_digest
            data["risk_report_digest"] = risk_digest
            data["execution_manifest_digests"] = manifest_digests
            data["cycle_outcome"] = outcome
            data["previous_event_digest"] = prev_digest
            data["event_digest"] = event_digest
        return data
