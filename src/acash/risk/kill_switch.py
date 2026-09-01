"""Phase 9: Sovereign Kill Switch Controller & Hardened State Machine (Slice 3).

Strictly enforces:
1. Sovereign Veto Authority: TRIPPED / PERSISTENTLY_BLOCKED => Execution Admission BLOCKED (0 Orders).
2. Separation of Concerns:
   - Trigger Detection (Phase 7 evaluate_kill_switch_triggers) != Kill Switch Controller (Phase 9).
   - Kill Switch Trip != Position Flatten Completion (Phase 9 requests; Phase 7 reconciles).
   - Zero Direct Broker Transmission Authority in Phase 9.
3. Strict 5-Stage Lifecycle State Machine:
   DETECT -> DECIDE -> TRIP -> PERSIST -> BLOCK -> RESET
4. Persistent, Tamper-Evident Ledger:
   - Append-only disk persistence with SHA-256 cryptographic event chaining.
   - Process restart recovery: recovers TRIPPED / PERSISTENTLY_BLOCKED state.
   - Corrupted or tampered ledger fails closed.
5. Multi-Sig Quorum Reset:
   - Reset requires Ed25519TrustStore cryptographic signature verification.
   - Requires non-empty root-cause analysis summary.
   - Replay protection & distinct approver quorum enforcement.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.domain.types import freeze_mapping
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.crypto import Ed25519TrustStore
from acash.execution.schema import ApproverRole, AuthorizationApproval
from acash.risk.risk_schema import (
    KillSwitchResetEvent,
    KillSwitchState,
    RiskPolicyConfig,
    _ensure_utc,
    _validate_sha256,
)


# ============================================================================
# 1. KILL SWITCH EVENT CONTRACT
# ============================================================================


class KillSwitchEvent(BaseModel):
    """Immutable forensic evidence event recording state transitions in the Kill Switch Controller."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(description="Unique deterministic kill switch event identifier.")
    previous_state: KillSwitchState = Field(description="Controller state immediately prior to transition.")
    resulting_state: KillSwitchState = Field(description="Controller state resulting from this transition.")
    trigger_reason: str = Field(description="Forensic explanation / trigger reason for transition.")
    trigger_evidence: Mapping[str, str] = Field(
        default_factory=dict, description="Structured key-value forensic telemetry evidence."
    )
    policy_version: str = Field(description="Active RiskPolicyConfig version string.")
    policy_digest: str = Field(description="Active RiskPolicyConfig SHA-256 fingerprint.")
    previous_event_digest: str = Field(
        default="0" * 64, description="SHA-256 fingerprint of preceding event for tamper-evident chaining."
    )
    timestamp_utc: datetime = Field(description="Strict UTC timestamp of state transition.")
    event_digest: str = Field(
        default="", description="Canonical SHA-256 fingerprint of this kill switch event."
    )

    @model_validator(mode="before")
    @classmethod
    def validate_and_compute_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            _validate_sha256(data.get("policy_digest", ""), "policy_digest")
            prev_digest = data.get("previous_event_digest", "0" * 64)
            _validate_sha256(prev_digest, "previous_event_digest")

            ts = _ensure_utc(data.get("timestamp_utc", datetime.now(timezone.utc)))
            raw_evidence = data.get("trigger_evidence", {})
            cleaned_evidence = {str(k): str(v) for k, v in raw_evidence.items()} if isinstance(raw_evidence, Mapping) else {}

            prev_st = data["previous_state"].value if isinstance(data.get("previous_state"), KillSwitchState) else str(data.get("previous_state", ""))
            res_st = data["resulting_state"].value if isinstance(data.get("resulting_state"), KillSwitchState) else str(data.get("resulting_state", ""))

            payload = {
                "event_id": str(data.get("event_id", "")),
                "previous_state": prev_st,
                "resulting_state": res_st,
                "trigger_reason": str(data.get("trigger_reason", "")).strip(),
                "trigger_evidence": {k: cleaned_evidence[k] for k in sorted(cleaned_evidence.keys())},
                "policy_version": str(data.get("policy_version", "")),
                "policy_digest": str(data.get("policy_digest", "")),
                "previous_event_digest": prev_digest,
                "timestamp_utc": ts.isoformat(),
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
            event_digest = hashlib.sha256(canonical_bytes).hexdigest()

            data["trigger_evidence"] = freeze_mapping(cleaned_evidence)
            data["timestamp_utc"] = ts
            data["event_digest"] = event_digest
        return data


# Strict Permitted Forward State Transitions
ALLOWED_KILL_SWITCH_TRANSITIONS: Mapping[KillSwitchState, Set[KillSwitchState]] = {
    KillSwitchState.ACTIVE: {KillSwitchState.TRIPPED},
    KillSwitchState.TRIPPED: {KillSwitchState.PERSISTENTLY_BLOCKED},
    KillSwitchState.PERSISTENTLY_BLOCKED: {KillSwitchState.RESET_PENDING, KillSwitchState.TRIPPED},
    KillSwitchState.RESET_PENDING: {KillSwitchState.ACTIVE, KillSwitchState.TRIPPED},
}


# ============================================================================
# 2. SOVEREIGN KILL SWITCH CONTROLLER
# ============================================================================


class SovereignKillSwitchController:
    """Authoritative Sovereign Kill Switch state machine and admission controller."""

    def __init__(
        self,
        trust_store: Ed25519TrustStore,
        policy_config: Optional[RiskPolicyConfig] = None,
        persistence_path: Optional[Path] = None,
        initial_state: KillSwitchState = KillSwitchState.ACTIVE,
    ) -> None:
        self._trust_store = trust_store
        self._policy = policy_config or RiskPolicyConfig()
        self._persistence_path = persistence_path
        self._state = initial_state
        self._latest_event: Optional[KillSwitchEvent] = None
        self._consumed_approval_digests: Set[str] = set()

        # If persistence path provided, recover state from disk ledger
        if self._persistence_path is not None:
            self._recover_from_persistence()

    @property
    def state(self) -> KillSwitchState:
        """Current authoritative controller state."""
        return self._state

    @property
    def is_blocked(self) -> bool:
        """Indicates whether execution admission is locked out."""
        return self._state in (
            KillSwitchState.TRIPPED,
            KillSwitchState.PERSISTENTLY_BLOCKED,
            KillSwitchState.RESET_PENDING,
        )

    @property
    def latest_event(self) -> Optional[KillSwitchEvent]:
        """Latest recorded kill switch forensic transition event."""
        return self._latest_event

    def assert_admission_allowed(self) -> None:
        """Sovereign admission gate. Raises DataContractError fail-closed if blocked."""
        if self.is_blocked:
            raise DataContractError(
                f"EXECUTION_ADMISSION_BLOCKED: Sovereign kill switch is active in state '{self._state.value}'."
            )

    def trip(
        self,
        reason: str,
        evidence: Optional[Mapping[str, Any]] = None,
        as_of: Optional[datetime] = None,
    ) -> KillSwitchEvent:
        """Sovereign Trip: Immediately transition controller to TRIPPED -> PERSISTENTLY_BLOCKED."""
        if not reason or not reason.strip():
            raise DataContractError("Kill switch trip requires a non-empty reason.")

        now = _ensure_utc(as_of or datetime.now(timezone.utc))
        cleaned_evidence = {str(k): str(v) for k, v in (evidence or {}).items()}

        prev_state = self._state
        prev_digest = self._latest_event.event_digest if self._latest_event else "0" * 64

        # Validate permitted transition to TRIPPED
        if KillSwitchState.TRIPPED not in ALLOWED_KILL_SWITCH_TRANSITIONS.get(prev_state, set()):
            # Re-tripping while already in TRIPPED / PERSISTENTLY_BLOCKED is idempotent
            if prev_state in (KillSwitchState.TRIPPED, KillSwitchState.PERSISTENTLY_BLOCKED):
                pass
            else:
                raise DataContractError(
                    f"Illegal state transition from '{prev_state.value}' to '{KillSwitchState.TRIPPED.value}'."
                )

        # Stage 1: TRIP
        trip_event = KillSwitchEvent(
            event_id=f"KILL_TRIP_{int(now.timestamp() * 1000)}",
            previous_state=prev_state,
            resulting_state=KillSwitchState.TRIPPED,
            trigger_reason=reason.strip(),
            trigger_evidence=cleaned_evidence,
            policy_version=self._policy.policy_version,
            policy_digest=self._policy.policy_digest,
            previous_event_digest=prev_digest,
            timestamp_utc=now,
        )
        self._state = KillSwitchState.TRIPPED
        self._latest_event = trip_event

        # Stage 2: PERSIST -> PERSISTENTLY_BLOCKED
        persist_event = KillSwitchEvent(
            event_id=f"KILL_PERSIST_{int(now.timestamp() * 1000)}",
            previous_state=KillSwitchState.TRIPPED,
            resulting_state=KillSwitchState.PERSISTENTLY_BLOCKED,
            trigger_reason=f"Hardened to persistence ledger: {reason.strip()}",
            trigger_evidence=cleaned_evidence,
            policy_version=self._policy.policy_version,
            policy_digest=self._policy.policy_digest,
            previous_event_digest=trip_event.event_digest,
            timestamp_utc=now,
        )
        self._state = KillSwitchState.PERSISTENTLY_BLOCKED
        self._latest_event = persist_event

        # Write both events to append-only persistence ledger
        self._persist_event(trip_event)
        self._persist_event(persist_event)

        return persist_event

    def submit_reset(
        self,
        reset_event: KillSwitchResetEvent,
        as_of: Optional[datetime] = None,
    ) -> KillSwitchEvent:
        """Authorized Reset: Verify multi-sig quorum and transition PERSISTENTLY_BLOCKED -> RESET_PENDING -> ACTIVE."""
        if not self.is_blocked:
            raise DataContractError(
                f"Cannot reset kill switch when controller is already in ACTIVE state."
            )

        if self._latest_event is None:
            raise DataContractError(
                "Cannot reset kill switch without recorded historical trip event."
            )

        # Target KillSwitchEvent ID must match latest active trip event
        if reset_event.kill_switch_event_id != self._latest_event.event_id:
            raise DataContractError(
                f"Stale or mismatched reset proposal: targets '{reset_event.kill_switch_event_id}' "
                f"but current active trip is '{self._latest_event.event_id}'."
            )

        # 1. Validate Non-Empty Root Cause
        if not reset_event.root_cause_summary.strip():
            raise DataContractError("Kill switch reset requires non-empty root_cause_summary.")

        # 2. Validate Quorum Count
        if len(reset_event.approvals) < reset_event.required_approvals:
            raise DataContractError(
                f"Insufficient reset approvals: received {len(reset_event.approvals)}, "
                f"required {reset_event.required_approvals}."
            )

        # 3. Validate Distinct Approvers & Replay Protection
        seen_approver_ids: Set[str] = set()
        seen_key_ids: Set[str] = set()

        for approval in reset_event.approvals:
            if approval.approval_digest in self._consumed_approval_digests:
                raise DataContractError(
                    f"Replayed approval detected: digest '{approval.approval_digest}' was already consumed."
                )

            if approval.approver_id in seen_approver_ids:
                raise DataContractError(
                    f"Duplicate approver '{approval.approver_id}' detected in reset proposal."
                )
            seen_approver_ids.add(approval.approver_id)

            if approval.public_key_id in seen_key_ids:
                raise DataContractError(
                    f"Duplicate key '{approval.public_key_id}' detected in reset proposal."
                )
            seen_key_ids.add(approval.public_key_id)

            # Role check: only RISK_OFFICER or COMPLIANCE_OFFICER authorized to clear kill switch
            if approval.role not in (ApproverRole.RISK_OFFICER, ApproverRole.COMPLIANCE_OFFICER):
                raise DataContractError(
                    f"Unauthorized approver role '{approval.role.value}' for kill switch reset. "
                    "Must be RISK_OFFICER or COMPLIANCE_OFFICER."
                )

            # Cryptographic signature verification via Ed25519TrustStore
            try:
                self._trust_store.verify(
                    key_id=approval.public_key_id,
                    payload_bytes=approval.compute_canonical_payload_bytes(),
                    signature_b64=approval.approval_signature,
                    at_time=approval.approved_at,
                )
            except DomainValidationError as e:
                raise DataContractError(
                    f"Cryptographic signature verification failed for approver '{approval.approver_id}': {e}"
                ) from e

        now = _ensure_utc(as_of or datetime.now(timezone.utc))

        # Stage 1: Transition to RESET_PENDING
        pending_event = KillSwitchEvent(
            event_id=f"KILL_PENDING_{int(now.timestamp() * 1000)}",
            previous_state=self._state,
            resulting_state=KillSwitchState.RESET_PENDING,
            trigger_reason=f"Multi-sig quorum verified: {reset_event.root_cause_summary.strip()}",
            trigger_evidence={"reset_event_id": reset_event.event_id, "approver_count": str(len(reset_event.approvals))},
            policy_version=self._policy.policy_version,
            policy_digest=self._policy.policy_digest,
            previous_event_digest=self._latest_event.event_digest,
            timestamp_utc=now,
        )
        self._state = KillSwitchState.RESET_PENDING
        self._latest_event = pending_event
        self._persist_event(pending_event)

        # Stage 2: Transition to ACTIVE (Operational Recovery)
        active_event = KillSwitchEvent(
            event_id=f"KILL_RESET_{int(now.timestamp() * 1000)}",
            previous_state=KillSwitchState.RESET_PENDING,
            resulting_state=KillSwitchState.ACTIVE,
            trigger_reason=f"Kill switch deactivated. Root cause: {reset_event.root_cause_summary.strip()}",
            trigger_evidence={"reset_event_id": reset_event.event_id},
            policy_version=self._policy.policy_version,
            policy_digest=self._policy.policy_digest,
            previous_event_digest=pending_event.event_digest,
            timestamp_utc=now,
        )
        self._state = KillSwitchState.ACTIVE
        self._latest_event = active_event
        self._persist_event(active_event)

        # Mark approvals as consumed to prevent replay
        for approval in reset_event.approvals:
            self._consumed_approval_digests.add(approval.approval_digest)

        return active_event

    def _persist_event(self, event: KillSwitchEvent) -> None:
        """Append event to disk ledger if persistence path is configured."""
        if self._persistence_path is None:
            return

        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        raw_json = CanonicalConfigSerializer.to_canonical_json(event.model_dump(mode="json"))
        with open(self._persistence_path, "a", encoding="utf-8") as f:
            f.write(raw_json + "\n")

    def _recover_from_persistence(self) -> None:
        """Recover state from append-only disk ledger with cryptographic chain validation."""
        if self._persistence_path is None or not self._persistence_path.exists():
            return

        try:
            with open(self._persistence_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            if not lines:
                return

            expected_prev_digest = "0" * 64
            recovered_state = KillSwitchState.ACTIVE
            recovered_event: Optional[KillSwitchEvent] = None

            for line_idx, line in enumerate(lines):
                event_dict = json.loads(line)
                event = KillSwitchEvent.model_validate(event_dict)

                # Validate cryptographic hash chain
                if event.previous_event_digest != expected_prev_digest and line_idx > 0:
                    raise DataContractError(
                        f"Ledger tampering detected at entry {line_idx}: previous_event_digest mismatch."
                    )

                expected_prev_digest = event.event_digest
                recovered_state = event.resulting_state
                recovered_event = event

            self._state = recovered_state
            self._latest_event = recovered_event

        except Exception as exc:
            # Corrupted ledger MUST fail closed to PERSISTENTLY_BLOCKED
            self._state = KillSwitchState.PERSISTENTLY_BLOCKED
            raise DataContractError(
                f"PERSISTENCE_RECOVERY_FAILED: Corrupted kill switch ledger at '{self._persistence_path}': {exc}"
            ) from exc
