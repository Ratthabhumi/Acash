"""ACASH Paper Trading — Observation Window Model & Deployment Interlock (E3.6).

DESIGN REFERENCE: E3.6-DESIGN.md §3 (D3.1–D3.5), §5 (D1.2–D1.5), §6 (D2.1–D2.5),
§9 (Window Manifest Schema), §10 (D10.1–D10.3), §11 (D4.1–D4.5), §15 (D6.1–D6.3),
§18 (D18.1–D18.2).

This module introduces the **observation window** as the evidence-of-record
aggregate above sessions (D3.1):

- One canonical ``window_id`` + one ``WindowManifest``.
- Aggregates one or more sealed sessions (each with journal + sealed session
  manifest); the engine's session model stays unchanged.
- Carries the D1 runtime-provenance record as an ordered list of **runtime
  segments**; a window may intentionally span multiple containers.
- Persists a two-file deployment interlock (D2.1): a window-state marker
  (``windows/<window_id>.state.json``) + the window manifest
  (``windows/<window_id>.manifest.json``) on the single mount root.
- The window manifest seal is a **fail-closed validator**: any blank
  provenance field, ``git_commit == "unknown"``, missing transition record,
  or missing clock attestation fails the seal (D1.4/D1.5, §9, D4.5).

GOVERNANCE (E3.6):
==================
- This is EXECUTION/PAPER INFRASTRUCTURE ONLY. It establishes no strategy
  qualification, no Paper authorization, no Live authorization (D20.1).
- ``auto_recovery_used`` MUST be False unless a future validated design
  decision permits it (D6.3 / O1). This validator rejects ``True``.
- No magic floors, no silent fallbacks: every failure is a
  ``DataContractError`` raised with a complete violation list.
- git_commit ``"unknown"`` is a fail-closed violation for window evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class WindowState(str, Enum):
    """Two-file deployment interlock states (D2.1).

    - ``OPEN``: one or more sessions belong to an unsealed window -> deploy of
      the paper service is BLOCKED.
    - ``SEALED``: the window was explicitly/regularly closed -> deploy allowed.
    - ``VOID``: explicit human-issued void (governed procedure only).
    """

    QUIESCENT = "QUIESCENT"
    OPEN = "OPEN"
    SEALED = "SEALED"
    VOID = "VOID"


class EvidenceStatus(str, Enum):
    """Window manifest evidence status (§9)."""

    OPEN = "OPEN"
    SEALED = "SEALED"
    VOID = "VOID"


class TransitionClassification(str, Enum):
    """Four-way runtime-identity classification (D1.3).

    - ``RECORDED_TRANSITION``: intentional sealed-session deployment or
      recorded crash/restart — admissible evidence.
    - ``VALIDATED_RECORDED_TRANSITION``: a recorded transition that has also
      been validated at segment open/close (digest pinned + attributable).
    - ``PROVENANCE_VIOLATION``: silent container replacement during an OPEN
      window with no transition record — inadmissible.
    - ``AMBIGUOUS``: a segment missing ``container_id``/``image_digest``/
      ``git_commit``/``transition_reason`` — fail closed until resolved.
    """

    RECORDED_TRANSITION = "RECORDED_TRANSITION"
    VALIDATED_RECORDED_TRANSITION = "VALIDATED_RECORDED_TRANSITION"
    PROVENANCE_VIOLATION = "PROVENANCE_VIOLATION"
    AMBIGUOUS = "AMBIGUOUS"


# ---------------------------------------------------------------------------
# Records inside the window manifest
# ---------------------------------------------------------------------------


class ClockAttestation(BaseModel):
    """Infra-supplied host clock/NTP attestation (D4.2 / D4.5).

    The attestation is *supplied by the infrastructure layer*; ACASH records
    and associates it with the window at segment open/close. The non-root
    ACASH container must NOT be required to access privileged host NTP state.
    """

    model_config = ConfigDict(extra="forbid")

    source: str = Field(description="Infra attestation source, e.g. host systemd-timesyncd.")
    captured_at_utc: datetime = Field(description="UTC capture time of the attestation.")
    ntp_synced: bool = Field(description="True when the infra reports NTP sync.")
    reported_skew_ms: Optional[int] = Field(
        default=None,
        description="Infra-reported max clock skew in ms (may be absent).",
    )
    ntp_drift_log_ref: Optional[str] = Field(default=None, description="Drift log reference.")


class RuntimeSegment(BaseModel):
    """One runtime segment (D1.2): attributable identity over a span of time.

    Every segment boundary (open/close/replace) is a transition record with
    exactly one attributable ``transition_reason`` (D1.5).
    """

    model_config = ConfigDict(extra="forbid")

    segment_id: str
    start_utc: datetime
    end_utc: Optional[datetime] = None
    container_id: str = Field(description="Container identity observed at segment open.")
    image_reference: str = Field(description="Registry/repo reference, e.g. acash:paper-v1.")
    image_digest: str = Field(description="SHA-256 image digest (@sha256:...).")
    git_commit: str = Field(description="ACASH source git commit for this segment.")
    member_session_ids: List[str] = Field(default_factory=list)
    transition_reason: str = Field(description="One permitted attributable reason (D1.5).")
    transition_recorded_at_utc: datetime = Field(
        description="UTC time the transition record was written (FIRST, D1.5)."
    )
    transition_recorded_by: str = Field(description="Harness/operator identity.")
    clock_attestation_open: Optional[ClockAttestation] = Field(default=None)
    clock_attestation_close: Optional[ClockAttestation] = Field(default=None)
    max_observed_skew_ms: Optional[int] = Field(default=None)

    @property
    def closed(self) -> bool:
        return self.end_utc is not None

    @property
    def classifiable(self) -> bool:
        """Ambiguity check (D1.3): any blank provenance field -> AMBIGUOUS."""
        return all(
            [
                bool(self.container_id),
                bool(self.image_digest),
                bool(self.git_commit),
                bool(self.transition_reason),
            ]
        )


class MemberSessionRef(BaseModel):
    """Window member session reference (D3.3): single-authority hash per session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    journal_final_hash: str = Field(description="The session journal chain tip hash.")
    session_manifest_hash: str = Field(description="The sealed PaperSessionManifest hash.")
    sealed_at_utc: datetime


class HaltEntry(BaseModel):
    """One entry in the feed-policy halted_reason_chronology (D6.2)."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    occurred_at_utc: datetime
    resumed_at_utc: Optional[datetime] = None


class DeploymentInterlockRecord(BaseModel):
    """Last deploy-pipeline interaction with this window (D2.1/D2.2)."""

    model_config = ConfigDict(extra="forbid")

    last_deploy_target_utc: Optional[datetime] = None
    last_deploy_stance: Optional[str] = None  # "BLOCKED" / "ALLOWED"
    blocked_at_utc: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    allowed_at_utc: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Window manifest (canonical schema, §9)
# ---------------------------------------------------------------------------


class WindowManifest(BaseModel):
    """The observation-window evidence manifest (§9).

    Sum-of-a-whole artifact, distinct from ``PaperSessionManifest``. Sealed by
    the window authoring step that pulls each member session's sealed manifest
    + hashes + integrity/review output. The seal is fail-closed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identity
    window_id: str
    window_manifest_id: str
    window_open_utc: datetime
    window_seal_utc: Optional[datetime] = None
    author: str = Field(description="Harness/operator identity that authored the window.")
    created_by_version: str = Field(description="ACASH component version that authored it.")

    # Recording target (fixed per window, D3.4)
    data_source: str
    instrument_universe: List[str]
    market_domain: str
    timeframe: str

    # Member sessions
    member_sessions: List[MemberSessionRef] = Field(default_factory=list)
    aggregate_event_count: int = Field(default=0)

    # Runtime provenance (D1)
    host_identity: str
    runtime_segments: List[RuntimeSegment] = Field(default_factory=list)
    watchtower_exclusion_verified: bool = Field(default=False)
    deployment_interlock: DeploymentInterlockRecord = Field(
        default_factory=DeploymentInterlockRecord
    )

    # Time integrity (D4)
    clock_source_utc: Optional[str] = None
    max_observed_skew_ms: Optional[int] = None
    ntp_drift_log_ref: Optional[str] = None

    # Feed policy (D6)
    feed_failure_events: int = Field(default=0)
    halted_reason_chronology: List[HaltEntry] = Field(default_factory=list)
    auto_recovery_used: bool = Field(default=False)

    # Evidence classification
    operational_vs_evidence_classification: str = "EVIDENCE_OF_RECORD"
    evidence_status: EvidenceStatus = EvidenceStatus.OPEN

    # Sealed aggregates
    total_sessions: int = Field(default=0)
    first_session_start_utc: Optional[datetime] = None
    last_session_end_utc: Optional[datetime] = None
    aggregate_reconciliation_status: str = "NOT_CHECKED"

    # Restore auditability (D18.2)
    restored_at_utc: Optional[datetime] = None
    restored_from_backup_ts: Optional[str] = None

    # Manifest integrity
    window_manifest_hash: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def enforce_paper_window_assertions(self) -> "WindowManifest":
        if self.instrument_universe == [] or len(self.instrument_universe) == 0:
            raise DataContractError("WindowManifest: instrument_universe must be non-empty.")
        if self.evidence_status == EvidenceStatus.SEALED:
            if not self.window_seal_utc:
                raise DataContractError("WindowManifest: sealed window must have window_seal_utc.")
            if not self.window_manifest_hash:
                raise DataContractError("WindowManifest: sealed window must have window_manifest_hash.")
        return self

    @staticmethod
    def compute_window_manifest_hash(
        window_id: str,
        window_manifest_id: str,
        window_open_utc: datetime,
        runtime_segments: List[RuntimeSegment],
        member_sessions: List[MemberSessionRef],
        aggregate_event_count: int,
        host_identity: str,
    ) -> str:
        """Single-authority window manifest hash (SHA-256 of canonical fields).

        NOTE: computed over the D1 runtime-provenance core + membership. The
        final sealed manifest binds this hash to the full record via the
        frozen model dump.
        """
        canonical: Dict[str, Any] = {
            "window_id": window_id,
            "window_manifest_id": window_manifest_id,
            "window_open_utc": window_open_utc.isoformat(),
            "host_identity": host_identity,
            "aggregate_event_count": aggregate_event_count,
            "member_sessions": [
                {
                    "session_id": m.session_id,
                    "journal_final_hash": m.journal_final_hash,
                    "session_manifest_hash": m.session_manifest_hash,
                }
                for m in member_sessions
            ],
            "runtime_segments": [
                {
                    "segment_id": s.segment_id,
                    "start_utc": s.start_utc.isoformat(),
                    "end_utc": s.end_utc.isoformat() if s.end_utc else None,
                    "container_id": s.container_id,
                    "image_reference": s.image_reference,
                    "image_digest": s.image_digest,
                    "git_commit": s.git_commit,
                    "transition_reason": s.transition_reason,
                }
                for s in runtime_segments
            ],
        }
        return CanonicalConfigSerializer.compute_sha256(canonical)

    def compute_hash(self) -> str:
        """Compute this manifest's hash via the single authoritative function."""
        if not self.runtime_segments:
            raise DataContractError("WindowManifest: no runtime segments to hash.")
        return type(self).compute_window_manifest_hash(
            window_id=self.window_id,
            window_manifest_id=self.window_manifest_id,
            window_open_utc=self.window_open_utc,
            runtime_segments=self.runtime_segments,
            member_sessions=self.member_sessions,
            aggregate_event_count=self.aggregate_event_count,
            host_identity=self.host_identity,
        )


# ---------------------------------------------------------------------------
# Interlock marker (two-file deployment interlock, D2.1)
# ---------------------------------------------------------------------------


class WindowInterlockMarker(BaseModel):
    """State file ``windows/<window_id>.state.json`` (D2.1 / D10.1)."""

    model_config = ConfigDict(extra="forbid")

    window_id: str
    state: WindowState
    updated_at_utc: datetime
    updated_by: str = Field(description="Harness/operator identity that last updated the marker.")
    reason: str = Field(default="", description="Last transition attributable reason.")


# ---------------------------------------------------------------------------
# Fail-closed window manifest validator (the seal)
# ---------------------------------------------------------------------------


def validate_window_manifest(manifest: WindowManifest) -> List[str]:
    """Fail-closed validation of a window manifest (D1.4/D1.5, §9, D4.5, D6.3).

    Returns a list of violations; an empty list means admissible. Every failure
    is explicit — no silent floors, no neutral defaults.

    Violations checked:
    0. The window must contain at least one runtime segment (D3.1).
    1. ``git_commit == "unknown"`` in ANY segment (D1.4) -> violation.
    2. Any segment without ``container_id``/``image_digest``/``git_commit``/
       ``transition_reason`` (D1.3 AMBIGUOUS) -> violation.
    3. ``transition_reason`` must be one of the permitted set (D1.5).
    4. ``auto_recovery_used == True`` (D6.3/O1 -> must be False) -> violation.
    5. On ``SEALED``: every segment must be closed (end_utc set) (D2.1).
    6. Clock attestation present at segment open AND close when the segment is
       closed (D4.5 / G15).
    7. ``watchtower_exclusion_verified`` must be True for a SEALED window.
    """
    violations: List[str] = []

    if manifest.runtime_segments == []:
        violations.append("window must contain at least one runtime segment (D3.1).")

    permitted_reasons = {
        "WINDOW_OPEN",
        "GOVERNED_DEPLOYMENT",
        "OPERATOR_STOP_RESUME",
        "CRASH_RESTART_RECORDED",
        "WINDOW_SEAL",
        "HUMAN_VOID",
    }

    for seg in manifest.runtime_segments:
        if seg.git_commit == "unknown":
            violations.append(
                f"segment {seg.segment_id}: git_commit='unknown' is a fail-closed violation (D1.4)."
            )
        if not seg.classifiable:
            missing = [
                name
                for name, val in (
                    ("container_id", seg.container_id),
                    ("image_digest", seg.image_digest),
                    ("git_commit", seg.git_commit),
                    ("transition_reason", seg.transition_reason),
                )
                if not val
            ]
            violations.append(
                f"segment {seg.segment_id}: AMBIGUOUS provenance, missing {missing} (D1.3)."
            )
        if seg.transition_reason not in permitted_reasons:
            violations.append(
                f"segment {seg.segment_id}: transition_reason {seg.transition_reason!r} "
                f"not in permitted set {sorted(permitted_reasons)} (D1.5)."
            )
        if seg.closed:
            if seg.clock_attestation_close is None:
                violations.append(
                    f"segment {seg.segment_id}: closed segment missing close clock attestation (D4.5/G15)."
                )
            if seg.clock_attestation_open is None:
                violations.append(
                    f"segment {seg.segment_id}: closed segment missing open clock attestation (D4.5/G15)."
                )
        else:
            if seg.clock_attestation_open is None:
                violations.append(
                    f"segment {seg.segment_id}: missing open clock attestation (D4.5/G15)."
                )

    if manifest.auto_recovery_used:
        violations.append(
            "auto_recovery_used=True rejected: automatic feed recovery is NOT adopted (D6.3/O1)."
        )

    if manifest.evidence_status == EvidenceStatus.SEALED:
        open_segments = [s.segment_id for s in manifest.runtime_segments if not s.closed]
        if open_segments:
            violations.append(
                f"SEALED window has unclosed segments: {open_segments} (D2.1)."
            )
        if not manifest.watchtower_exclusion_verified:
            violations.append(
                "SEALED window requires watchtower_exclusion_verified=True (C2/D2.4)."
            )

    return violations


# ---------------------------------------------------------------------------
# Window authoring service (window supervisor harness — design-level)
# ---------------------------------------------------------------------------


class WindowAuthoringService:
    """Small harness that authors/owns one observation window (D3.3).

    Delegated lifecycle (all fail-closed):
    - ``open_window``: writes the marker OPEN FIRST (D2.1) and creates the
      initial runtime segment with a ``WINDOW_OPEN`` transition record.
    - ``open_runtime_segment`` / ``close_runtime_segment``: governed
      transitions that write the transition record BEFORE any container change
      is possible (D1.5), preserving RUNTIME PROVENANCE (D1.2).
    - ``attach_session``: records a member session (D3.3) after it has sealed.
    - ``seal``: fail-closed validator -> SEALED marker + sealed manifest file.
    - ``void``: governed human-issued VOID only.
    - ``deploy_allowance``: the interlock read for a deploy pipeline (D2.2).

    Storage conventions (D10.3): single mount root. ``windows/`` owns interlock
    state + window manifests; ``sessions/`` owns the session evidence tier.
    """

    def __init__(
        self,
        *,
        storage_root: Path,
        window_id: str,
        author: str,
        created_by_version: str,
        data_source: str,
        instrument_universe: List[str],
        market_domain: str,
        timeframe: str,
        host_identity: str,
    ) -> None:
        self._root = Path(storage_root)
        windows_dir = self._root / "windows"
        windows_dir.mkdir(parents=True, exist_ok=True)
        self._windows_dir = windows_dir
        self._window_id = window_id
        self._author = author
        self._created_by_version = created_by_version
        self._data_source = data_source
        self._instrument_universe = list(instrument_universe)
        self._market_domain = market_domain
        self._timeframe = timeframe
        self._host_identity = host_identity

        self._manifest = WindowManifest(
            window_id=window_id,
            window_manifest_id=f"{window_id}-mh-01",
            window_open_utc=datetime.now(timezone.utc),
            author=author,
            created_by_version=created_by_version,
            data_source=data_source,
            instrument_universe=list(instrument_universe),
            market_domain=market_domain,
            timeframe=timeframe,
            host_identity=host_identity,
            runtime_segments=[],
        )
        self._marker = WindowInterlockMarker(
            window_id=window_id,
            state=WindowState.QUIESCENT,
            updated_at_utc=datetime.now(timezone.utc),
            updated_by=author,
            reason="NO_WINDOW",
        )

    # -- paths ----------------------------------------------------------

    @property
    def marker_path(self) -> Path:
        return self._windows_dir / f"{self._window_id}.state.json"

    @property
    def manifest_path(self) -> Path:
        return self._windows_dir / f"{self._window_id}.manifest.json"

    @staticmethod
    def session_storage_dir(storage_root: Path) -> Path:
        """D10.3: session evidence tier lives under ``sessions/`` of the root."""
        d = Path(storage_root) / "sessions"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # -- persistence ----------------------------------------------------

    def _persist_marker(self) -> None:
        payload = self._marker.model_dump_json(indent=2) + "\n"
        try:
            self.marker_path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            raise DataContractError(
                f"WindowAuthoringService: marker persistence failure: {exc}"
            ) from exc

    def _persist_manifest(self) -> None:
        payload = self._manifest.model_dump_json(indent=2) + "\n"
        try:
            self.manifest_path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            raise DataContractError(
                f"WindowAuthoringService: manifest persistence failure: {exc}"
            ) from exc

    # -- interlock -------------------------------------------------------

    def state(self) -> WindowState:
        return self._marker.state

    def open_window(
        self,
        *,
        container_id: str,
        image_reference: str,
        image_digest: str,
        git_commit: str,
        transition_recorded_by: str,
    ) -> RuntimeSegment:
        """Open the observation window + write the initial runtime segment.

        Guard: the marker must be QUIESCENT; ``git_commit`` must not be
        ``"unknown"`` (D1.4). The marker is written OPEN FIRST so that any
        concurrent deploy pipeline is BLOCKED before the segment record.
        """
        if self._marker.state != WindowState.QUIESCENT:
            raise DataContractError(
                f"WindowAuthoringService: cannot open window in state "
                f"{self._marker.state.value!r}; expected QUIESCENT."
            )
        if git_commit == "unknown":
            raise DataContractError(
                "WindowAuthoringService: git_commit='unknown' is a fail-closed "
                "violation for window evidence (D1.4)."
            )

        now_utc = datetime.now(timezone.utc)
        self._marker = WindowInterlockMarker(
            window_id=self._window_id,
            state=WindowState.OPEN,
            updated_at_utc=now_utc,
            updated_by=transition_recorded_by,
            reason="WINDOW_OPEN",
        )
        # Marker OPEN written FIRST (D2.1). If this fails we fail closed.
        self._persist_marker()

        segment = RuntimeSegment(
            segment_id=f"{self._window_id}-seg-01",
            start_utc=now_utc,
            container_id=container_id,
            image_reference=image_reference,
            image_digest=image_digest,
            git_commit=git_commit,
            transition_reason="WINDOW_OPEN",
            transition_recorded_at_utc=now_utc,
            transition_recorded_by=transition_recorded_by,
        )
        self._manifest = self._manifest.model_copy(
            update={"runtime_segments": [segment]},
            deep=True,
        )
        self._persist_manifest()
        return segment

    def open_runtime_segment(
        self,
        *,
        container_id: str,
        image_reference: str,
        image_digest: str,
        git_commit: str,
        transition_reason: str,
        transition_recorded_by: str,
    ) -> RuntimeSegment:
        """Governed runtime transition: close current, open a new segment (D1.5).

        The transition record must be written FIRST — this method appends the
        new segment closure/open pair before returning, so a stopped container
        cannot be replaced without an attributable record.
        """
        if self._marker.state != WindowState.OPEN:
            raise DataContractError(
                f"WindowAuthoringService: runtime transition requires OPEN window, "
                f"got {self._marker.state.value!r}."
            )
        if git_commit == "unknown":
            raise DataContractError(
                "WindowAuthoringService: git_commit='unknown' is a fail-closed "
                "violation (D1.4)."
            )
        if transition_reason == "HUMAN_VOID" or transition_reason == "WINDOW_SEAL":
            raise DataContractError(
                f"WindowAuthoringService: transition_reason {transition_reason!r} "
                "is not a runtime-segment transition reason."
            )

        now_utc = datetime.now(timezone.utc)
        segments = list(self._manifest.runtime_segments)
        current = segments[-1]
        if not current.closed:
            # Close the old segment: end_utc + close attestation are recorded
            # as NO fabricated value — the close clock attestation stays None
            # until the infra supplies it via record_clock_attestation(..., at_open=False).
            # The transition boundary itself (D1.5) is written FIRST.
            current = current.model_copy(update={"end_utc": now_utc}, deep=True)
            segments[-1] = current

        new_segment = RuntimeSegment(
            segment_id=f"{self._window_id}-seg-{len(segments) + 1:02d}",
            start_utc=now_utc,
            container_id=container_id,
            image_reference=image_reference,
            image_digest=image_digest,
            git_commit=git_commit,
            transition_reason=transition_reason,
            transition_recorded_at_utc=now_utc,
            transition_recorded_by=transition_recorded_by,
        )
        segments.append(new_segment)
        self._manifest = self._manifest.model_copy(
            update={"runtime_segments": segments},
            deep=True,
        )
        # Transition record persisted FIRST (D1.5).
        self._persist_manifest()
        return new_segment

    def close_runtime_segment(
        self, *, transition_reason: str, transition_recorded_by: str
    ) -> RuntimeSegment:
        if self._marker.state != WindowState.OPEN:
            raise DataContractError(
                f"WindowAuthoringService: close requires OPEN window, got "
                f"{self._marker.state.value!r}."
            )
        segments = list(self._manifest.runtime_segments)
        current = segments[-1]
        if current.closed:
            raise DataContractError(
                "WindowAuthoringService: current runtime segment already closed."
            )
        now_utc = datetime.now(timezone.utc)
        closed = current.model_copy(
            update={
                "end_utc": now_utc,
                "transition_reason": transition_reason,
                "transition_recorded_at_utc": now_utc,
                "transition_recorded_by": transition_recorded_by,
                # close attestation stays None until infra supplies it (D4.5);
                # a sealed window with a missing close attestation fails closed.
            },
            deep=True,
        )
        segments[-1] = closed
        self._manifest = self._manifest.model_copy(
            update={"runtime_segments": segments},
            deep=True,
        )
        self._persist_manifest()
        return closed

    def attach_session(
        self,
        *,
        session_id: str,
        journal_final_hash: str,
        session_manifest_hash: str,
        sealed_at_utc: datetime,
        event_count: int,
    ) -> None:
        """Attach a sealed member session (D3.3/D3.4).

        Fail-closed: rejects sessions with blank hashes or idempotent
        duplicates. Recording-target consistency (D3.4) is enforced by the
        caller at the session-manifest level via the review package.
        """
        if not session_id or not journal_final_hash or not session_manifest_hash:
            raise DataContractError(
                "WindowAuthoringService: attach_session requires non-blank "
                "session_id/journal_final_hash/session_manifest_hash."
            )
        existing = {m.session_id for m in self._manifest.member_sessions}
        if session_id in existing:
            raise DataContractError(
                f"WindowAuthoringService: session {session_id!r} already attached."
            )
        ref = MemberSessionRef(
            session_id=session_id,
            journal_final_hash=journal_final_hash,
            session_manifest_hash=session_manifest_hash,
            sealed_at_utc=sealed_at_utc,
        )
        members = list(self._manifest.member_sessions) + [ref]
        self._manifest = self._manifest.model_copy(
            update={
                "member_sessions": members,
                "aggregate_event_count": self._manifest.aggregate_event_count + event_count,
                "total_sessions": len(members),
            },
            deep=True,
        )
        segment = self._manifest.runtime_segments[-1]
        if session_id not in segment.member_session_ids:
            segment = segment.model_copy(
                update={"member_session_ids": list(segment.member_session_ids) + [session_id]},
                deep=True,
            )
            segments = list(self._manifest.runtime_segments)
            segments[-1] = segment
            self._manifest = self._manifest.model_copy(
                update={"runtime_segments": segments},
                deep=True,
            )
        self._persist_manifest()

    # -- watchtower exclusion (D2.4/C2) ---------------------------------

    def verify_watchtower_exclusion(self, *, verified: bool) -> None:
        """Record Watchtower exclusion verification for this window.

        C2/D2.4: the paper container gets the label
        ``com.centurylinklabs.watchtower.enable=false``. The harness verifies
        the label is honored and records the result here.
        """
        self._manifest = self._manifest.model_copy(
            update={"watchtower_exclusion_verified": verified},
            deep=True,
        )
        self._persist_manifest()

    # -- feed policy accounting (D6.2 / WS7) -----------------------------

    def record_feed_failure(self, *, reason: str, occurred_at_utc: Optional[datetime] = None) -> None:
        ts = occurred_at_utc or datetime.now(timezone.utc)
        self._manifest = self._manifest.model_copy(
            update={"feed_failure_events": self._manifest.feed_failure_events + 1},
            deep=True,
        )
        chronology = list(self._manifest.halted_reason_chronology) + [
            HaltEntry(reason=reason, occurred_at_utc=ts)
        ]
        self._manifest = self._manifest.model_copy(
            update={"halted_reason_chronology": chronology},
            deep=True,
        )
        self._persist_manifest()

    # -- clock attestation (D4.2/D4.5, WS6) ------------------------------

    def record_clock_attestation(
        self,
        *,
        source: str,
        captured_at_utc: datetime,
        ntp_synced: bool,
        reported_skew_ms: Optional[int] = None,
        ntp_drift_log_ref: Optional[str] = None,
        at_open: bool = True,
    ) -> None:
        """Attach an infra-supplied clock attestation to the current segment."""
        if self._manifest.runtime_segments == []:
            raise DataContractError(
                "WindowAuthoringService: no runtime segment to attest."
            )
        attestation = ClockAttestation(
            source=source,
            captured_at_utc=captured_at_utc,
            ntp_synced=ntp_synced,
            reported_skew_ms=reported_skew_ms,
            ntp_drift_log_ref=ntp_drift_log_ref,
        )
        segments = list(self._manifest.runtime_segments)
        current = segments[-1]
        current = current.model_copy(
            update={
                "clock_attestation_open" if at_open else "clock_attestation_close": attestation,
                "max_observed_skew_ms": (
                    max(
                        current.max_observed_skew_ms or 0,
                        reported_skew_ms or 0,
                    )
                    if reported_skew_ms is not None
                    else current.max_observed_skew_ms
                ),
            },
            deep=True,
        )
        segments[-1] = current
        self._manifest = self._manifest.model_copy(
            update={"runtime_segments": segments},
            deep=True,
        )
        self._persist_manifest()

    # -- seal / void ------------------------------------------------------

    def seal(self, *, aggregate_reconciliation_status: str) -> WindowManifest:
        """Fail-closed seal: validate, hash, persist, flip marker to SEALED.

        SEALED must not leave open segments; the marker stays OPEN (deploy
        BLOCKED) until the manifest file itself is durable and valid.
        """
        violations = validate_window_manifest(self._manifest)
        if violations:
            raise DataContractError(
                "WindowAuthoringService: window seal failed (fail-closed): "
                + "; ".join(violations)
            )

        first_session_start = (
            min(m.sealed_at_utc for m in self._manifest.member_sessions)
            if self._manifest.member_sessions
            else None
        )
        last_session_end = (
            max(m.sealed_at_utc for m in self._manifest.member_sessions)
            if self._manifest.member_sessions
            else None
        )
        hash_value = self._manifest.compute_hash()
        now_utc = datetime.now(timezone.utc)

        sealed = self._manifest.model_copy(
            update={
                "window_seal_utc": now_utc,
                "evidence_status": EvidenceStatus.SEALED,
                "window_manifest_hash": hash_value,
                "first_session_start_utc": first_session_start,
                "last_session_end_utc": last_session_end,
                "aggregate_reconciliation_status": aggregate_reconciliation_status,
                "max_observed_skew_ms": max(
                    (s.max_observed_skew_ms or 0) for s in self._manifest.runtime_segments
                ),
            },
            deep=True,
        )
        # Re-validate the sealed copy (frozen model enforces SEALED invariant).
        rerun = validate_window_manifest(sealed)
        if rerun:
            raise DataContractError(
                "WindowAuthoringService: sealed manifest invalid: " + "; ".join(rerun)
            )
        self._manifest = sealed
        self._persist_manifest()

        self._marker = WindowInterlockMarker(
            window_id=self._window_id,
            state=WindowState.SEALED,
            updated_at_utc=now_utc,
            updated_by=self._author,
            reason="WINDOW_SEAL",
        )
        self._persist_marker()
        return sealed

    def void(self, *, reason: str, transition_recorded_by: str) -> WindowManifest:
        """Governed human-issued VOID (D2.1): requires explicit record."""
        if reason == "":
            raise DataContractError(
                "WindowAuthoringService: void requires a recorded reason (D2.1 goverened procedure)."
            )
        if self._marker.state not in (WindowState.OPEN, WindowState.SEALED):
            raise DataContractError(
                f"WindowAuthoringService: cannot VOID window in state {self._marker.state.value!r}."
            )
        now_utc = datetime.now(timezone.utc)
        self._manifest = self._manifest.model_copy(
            update={
                "evidence_status": EvidenceStatus.VOID,
                "window_seal_utc": self._manifest.window_seal_utc or now_utc,
            },
            deep=True,
        )
        self._persist_manifest()
        self._marker = WindowInterlockMarker(
            window_id=self._window_id,
            state=WindowState.VOID,
            updated_at_utc=now_utc,
            updated_by=transition_recorded_by,
            reason=reason[:200],
        )
        self._persist_marker()
        return self._manifest

    # -- deploy pipeline interlock read (D2.2 / O4) -----------------------

    def deploy_allowance(self) -> DeploymentInterlockRecord:
        """Interlock read for a deploy pipeline.

        Per the state machine (D2.1): an ``OPEN`` marker BLOCKS deploy of the
        paper service. ``SEALED``/``VOID``/``QUIESCENT`` are non-blocking
        leaves (no unsealed active window).
        """
        record = self._manifest.deployment_interlock
        stance: str
        reason: str
        blocked_at: Optional[datetime]
        allowed_at: Optional[datetime]
        now_utc = datetime.now(timezone.utc)
        if self._marker.state == WindowState.OPEN:
            stance = "BLOCKED"
            reason = f"window {self._window_id} is OPEN; deploy BLOCKED (D2.1/D2.2)"
            blocked_at = now_utc
            allowed_at = record.allowed_at_utc
        else:
            stance = "ALLOWED"
            reason = (
                f"window {self._window_id} is {self._marker.state.value}; "
                "no active OPEN window (D2.1)"
            )
            blocked_at = record.blocked_at_utc
            allowed_at = now_utc

        new_record = record.model_copy(
            update={
                "last_deploy_target_utc": now_utc,
                "last_deploy_stance": stance,
                "blocked_at_utc": blocked_at,
                "blocked_reason": reason if stance == "BLOCKED" else record.blocked_reason,
                "allowed_at_utc": allowed_at,
            },
            deep=True,
        )
        self._manifest = self._manifest.model_copy(
            update={"deployment_interlock": new_record},
            deep=True,
        )
        self._persist_manifest()
        return new_record

    def assert_deploy_allowed(self) -> None:
        """Fail-closed: raise DataContractError when any window is OPEN (O4)."""
        record = self.deploy_allowance()
        if record.last_deploy_stance == "BLOCKED":
            raise DataContractError(
                f"deploy-pipeline interlock: {record.blocked_reason} "
                "(abort-all stance, O4)."
            )

    # -- provenance violation (G13) --------------------------------------

    def detect_provenance_violation(self, *, details: str) -> WindowManifest:
        """Mark an OPEN window as provenance-violated (D1.3) -> fail-closed.

        A silent container replacement during OPEN with no transition record
        renders the window inadmissible as evidence.
        """
        if self._marker.state != WindowState.OPEN:
            raise DataContractError(
                "WindowAuthoringService: provenance violation can only be detected "
                "on an OPEN window."
            )
        now_utc = datetime.now(timezone.utc)
        self._manifest = self._manifest.model_copy(
            update={
                "evidence_status": EvidenceStatus.VOID,
                "operational_vs_evidence_classification": "PROVENANCE_VIOLATION",
                "window_seal_utc": now_utc,
            },
            deep=True,
        )
        self._persist_manifest()
        self._marker = WindowInterlockMarker(
            window_id=self._window_id,
            state=WindowState.VOID,
            updated_at_utc=now_utc,
            updated_by=f"violation-detector-{details[:80]}",
            reason="PROVENANCE_VIOLATION",
        )
        self._persist_marker()
        # Note: a VOID window is not deploy-blocked; revisit if policy changes.
        return self._manifest