"""HYP_011 V2 segment activation authority (final pre-deployment gate).

V2 MUST NOT derive its first target from the V1 Stage-B / Stage-C recovery
machinery. The first V2 observation is a fresh human-authorized FUTURE
session bound by a SegmentActivationAuthority document that names the exact
segment, activation session, runtime commit, economic locks, and authorizing
identity. Malformed, mismatched, stale, or non-prospective authorities fail
closed before any network call.

V2 session one additionally requires the strong ordinal-1 ceremony
(RegisteredIntent + DispatchAuthority) even though it holds no prior
position: the dispatch CA binding for session one is the deterministic
``CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS`` digest defined here, so
no economic event is ever invented.

Timer scheduling is derived from the canonical
``candidate_schedule_time()`` (session.close_utc + 15-minute SIP delay +
5-minute operational margin). The helper below renders the exact UTC
``OnCalendar=`` expression; operators validate it with
``systemd-analyze calendar`` at activation time.

No network in this module. No broker access. No capital authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow import candidate_schedule_time

SEGMENT_ID_V2: str = "HYP_011_PROSPECTIVE_V2"
SEGMENT_ACTIVATION_SCHEMA_VERSION: int = 1

SESSION_ONE_CA_STATUS: str = "CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS"

_SHA40 = re.compile(r"[0-9a-fA-F]{40}")


def session_one_ca_binding_sha256() -> str:
    """Deterministic CA binding for V2 session one (no prior holdings).

    Binds the explicit session-one non-event representation so a V2
    DispatchAuthority still carries a deterministic CA contract digest
    without inventing any economic distribution event.
    """
    doc = {
        "scope": "NO_PRIOR_HOLDINGS_NO_ENTITLEMENT_POSSIBLE",
        "status": SESSION_ONE_CA_STATUS,
    }
    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(doc).encode("utf-8")
    ).hexdigest()


def systemd_oncalendar_expression(
    session_date: date, calendar: NyseCa1Calendar
) -> str:
    """Render the exact UTC ``OnCalendar=`` expression for a target session.

    Derived from canonical ``candidate_schedule_time()`` (close_utc +
    provider delay + operational margin). The expression is UTC-normalized so
    no ``Timezone=`` timer directive is required.
    """
    dispatch_at = candidate_schedule_time(session_date, calendar)
    dispatch_utc = dispatch_at.astimezone(timezone.utc)
    return f"{dispatch_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC"


@dataclass(frozen=True)
class SegmentActivationAuthority:
    """Fresh human-authorized activation of the V2 prospective segment."""

    segment_id: str
    hypothesis_id: str
    activation_session: date
    runtime_commit_sha: str
    starting_aum: str
    paper_trading: bool
    live_trading: bool
    real_capital_authority_usd: str
    no_real_orders: bool
    authorized_at_utc: datetime
    authority_identity: str

    def canonical_doc(self) -> Dict[str, Any]:
        return {
            "schema_version": SEGMENT_ACTIVATION_SCHEMA_VERSION,
            "segment_id": self.segment_id,
            "hypothesis_id": self.hypothesis_id,
            "activation_session": self.activation_session.isoformat(),
            "runtime_commit_sha": self.runtime_commit_sha,
            "starting_aum": self.starting_aum,
            "paper_trading": self.paper_trading,
            "live_trading": self.live_trading,
            "real_capital_authority_usd": self.real_capital_authority_usd,
            "no_real_orders": self.no_real_orders,
            "authorized_at_utc": self.authorized_at_utc.isoformat(),
            "authority_identity": self.authority_identity,
        }


def validate_segment_activation_authority(
    doc: Mapping[str, Any],
    calendar: NyseCa1Calendar,
    now_utc: datetime,
    runtime_sha: str,
) -> SegmentActivationAuthority:
    """Validate a V2 SegmentActivationAuthority document (fail closed).

    Every binding is checked BEFORE any market-data network call. The
    activation session must be a real NYSE trading session that is still
    prospective at authorization time; it is never derived from V1
    Stage-B/Stage-C machinery.
    """
    if not isinstance(doc, Mapping):
        raise DataContractError("SHADOW_V2_ACTIVATION_NOT_A_MAPPING.")
    if doc.get("schema_version") != SEGMENT_ACTIVATION_SCHEMA_VERSION:
        raise DataContractError("SHADOW_V2_ACTIVATION_SCHEMA_VERSION.")
    if doc.get("segment_id") != SEGMENT_ID_V2:
        raise DataContractError("SHADOW_V2_ACTIVATION_SEGMENT_MISMATCH.")
    if doc.get("hypothesis_id") != "HYP_011":
        raise DataContractError("SHADOW_V2_ACTIVATION_HYPOTHESIS_ID.")
    try:
        activation_session = date.fromisoformat(str(doc.get("activation_session")))
    except (ValueError, TypeError) as exc:
        raise DataContractError("SHADOW_V2_ACTIVATION_BAD_SESSION.") from exc
    if not calendar.is_trading_session(activation_session):
        raise DataContractError(
            f"SHADOW_V2_ACTIVATION_NON_SESSION: {activation_session.isoformat()} "
            "is not a valid NYSE trading session."
        )
    try:
        authorized_at = datetime.fromisoformat(str(doc.get("authorized_at_utc")))
    except (ValueError, TypeError) as exc:
        raise DataContractError("SHADOW_V2_ACTIVATION_MALFORMED_TIME.") from exc
    if authorized_at.tzinfo is None:
        raise DataContractError("SHADOW_V2_ACTIVATION_NAIVE_TIME.")
    authorized_at = authorized_at.astimezone(timezone.utc)
    if now_utc.tzinfo is None:
        raise DataContractError("SHADOW_NOW_MUST_BE_TIMEZONE_AWARE.")
    now = now_utc.astimezone(timezone.utc)
    if authorized_at > now:
        raise DataContractError(
            "SHADOW_V2_ACTIVATION_FUTURE_AUTHORIZATION: authority cannot be "
            "authorized in the future."
        )
    session_open = calendar.get_session(activation_session).open_utc
    if session_open is None:
        raise DataContractError(
            f"SHADOW_NO_OPEN_TIME: {activation_session.isoformat()}."
        )
    if not authorized_at < session_open:
        raise DataContractError(
            "SHADOW_V2_ACTIVATION_NOT_PROSPECTIVE: activation session "
            f"{activation_session.isoformat()} opened at "
            f"{session_open.isoformat()}; authorization at "
            f"{authorized_at.isoformat()} is not prospective."
        )
    bound_runtime = doc.get("runtime_commit_sha")
    if (
        not isinstance(bound_runtime, str)
        or not _SHA40.fullmatch(bound_runtime)
        or bound_runtime.lower() != runtime_sha.lower()
    ):
        raise DataContractError(
            "SHADOW_V2_ACTIVATION_RUNTIME_MISMATCH: authority binds a "
            "different runtime commit than this checkout."
        )
    if str(doc.get("starting_aum")) != "100000.00":
        raise DataContractError("SHADOW_V2_ACTIVATION_AUM_MISMATCH.")
    if doc.get("paper_trading") is not False:
        raise DataContractError("SHADOW_V2_ACTIVATION_LOCKS_INVALID: paper_trading.")
    if doc.get("live_trading") is not False:
        raise DataContractError("SHADOW_V2_ACTIVATION_LOCKS_INVALID: live_trading.")
    if str(doc.get("real_capital_authority_usd")) != "0.00":
        raise DataContractError("SHADOW_V2_ACTIVATION_LOCKS_INVALID: capital.")
    if doc.get("no_real_orders") is not True:
        raise DataContractError("SHADOW_V2_ACTIVATION_LOCKS_INVALID: no_real_orders.")
    identity = doc.get("authority_identity")
    if not isinstance(identity, str) or not identity.strip():
        raise DataContractError("SHADOW_V2_ACTIVATION_BAD_IDENTITY.")
    return SegmentActivationAuthority(
        segment_id=SEGMENT_ID_V2,
        hypothesis_id="HYP_011",
        activation_session=activation_session,
        runtime_commit_sha=runtime_sha.lower(),
        starting_aum="100000.00",
        paper_trading=False,
        live_trading=False,
        real_capital_authority_usd="0.00",
        no_real_orders=True,
        authorized_at_utc=authorized_at,
        authority_identity=identity.strip(),
    )


def load_segment_activation_authority(
    path: Path,
    calendar: NyseCa1Calendar,
    now_utc: datetime,
    runtime_sha: str,
) -> Tuple[SegmentActivationAuthority, str]:
    """Load and validate a V2 activation authority file.

    Returns the validated authority plus the SHA-256 digest of the raw file
    bytes. The file digest (not just the parsed fields) is what gets recorded
    in V2 state identity, so the exact authorized bytes are bound.
    """
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise DataContractError(
            f"SHADOW_V2_ACTIVATION_FILE_UNREADABLE: {exc}."
        ) from exc
    try:
        loaded = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        raise DataContractError(
            f"SHADOW_V2_ACTIVATION_FILE_CORRUPT: {exc}."
        ) from exc
    if not isinstance(loaded, dict):
        raise DataContractError("SHADOW_V2_ACTIVATION_FILE_MALFORMED.")
    authority = validate_segment_activation_authority(
        loaded, calendar, now_utc, runtime_sha
    )
    file_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    return authority, file_sha256


def resolve_v2_activation_session(
    authority: SegmentActivationAuthority,
) -> date:
    """The V2 activation session is the validated authority's session.

    This is the ONLY sanctioned source of the V2 first target. Callers must
    never substitute ``resolve_operational_activation()`` (V1 Stage-B/Stage-C
    machinery) on the V2 path.
    """
    return authority.activation_session
