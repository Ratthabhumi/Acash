"""Two-stage dispatch authority: ObservationIntent + DispatchAuthority + attempt ledger (F15).

Evolution from bare authorization tokens:

  ObservationIntent   ratified BEFORE the target session opens; binds the
                      scientific inclusion decision (session, ordinal,
                      previous-chain head, no-backfill, no-skip).
  DispatchAuthority   bound to one intent + exact runtime commit + CA evidence
                      manifest + validity window + trading locks.
  DispatchAttemptLedger  append-only, atomically consumed single-use record
                      written BEFORE any market-data network call.

A crash or failure never permits reuse of the same authority: a new attempt,
if governance ever allows one, requires a NEW explicit DispatchAuthority with
a NEW attempt number. Retries are never auto-authorized.

No network in this module. No broker access. No capital authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar

INTENT_SCHEMA_VERSION: int = 1
AUTHORITY_SCHEMA_VERSION: int = 1
LEDGER_DIRNAME: str = "dispatch_ledger"
_SHA40 = re.compile(r"[0-9a-fA-F]{40}")
_SHA64 = re.compile(r"[0-9a-fA-F]{64}")


def _canonical_sha256(doc: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(dict(doc)).encode("utf-8")
    ).hexdigest()


def _require_tz_aware(value: datetime, context: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise DataContractError(f"SHADOW_AUTHORITY_NAIVE_TIME: {context}.")
    return value.astimezone(timezone.utc)


def _parse_utc(value: Any, context: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (ValueError, TypeError) as exc:
        raise DataContractError(f"SHADOW_AUTHORITY_MALFORMED_TIME: {context}.") from exc
    return _require_tz_aware(parsed, context)


@dataclass(frozen=True)
class ObservationIntent:
    """Scientific inclusion decision, locked before the target session opens."""

    hypothesis_id: str
    target_session: date
    observation_ordinal: int
    scientific_inclusion_intent: str
    previous_observation_sha256: Optional[str]
    backfill_allowed: bool
    automatic_skip_allowed: bool
    created_at_utc: datetime
    authority_identity: str

    def canonical_doc(self) -> Dict[str, Any]:
        return {
            "schema_version": INTENT_SCHEMA_VERSION,
            "hypothesis_id": self.hypothesis_id,
            "target_session": self.target_session.isoformat(),
            "observation_ordinal": self.observation_ordinal,
            "scientific_inclusion_intent": self.scientific_inclusion_intent,
            "previous_observation_sha256": self.previous_observation_sha256,
            "backfill_allowed": self.backfill_allowed,
            "automatic_skip_allowed": self.automatic_skip_allowed,
            "created_at_utc": self.created_at_utc.isoformat(),
            "authority_identity": self.authority_identity,
        }

    def intent_sha256(self) -> str:
        return _canonical_sha256(self.canonical_doc())


def validate_observation_intent(
    doc: Mapping[str, Any],
    calendar: NyseCa1Calendar,
    now_utc: datetime,
) -> ObservationIntent:
    """Validate an intent document (fail closed). Does NOT check chain state."""
    if not isinstance(doc, Mapping):
        raise DataContractError("SHADOW_INTENT_NOT_A_MAPPING.")
    if doc.get("schema_version") != INTENT_SCHEMA_VERSION:
        raise DataContractError("SHADOW_INTENT_SCHEMA_VERSION.")
    if doc.get("hypothesis_id") != "HYP_011":
        raise DataContractError("SHADOW_INTENT_HYPOTHESIS_ID.")
    try:
        target = date.fromisoformat(str(doc.get("target_session")))
    except (ValueError, TypeError) as exc:
        raise DataContractError("SHADOW_INTENT_BAD_TARGET_SESSION.") from exc
    ordinal = doc.get("observation_ordinal")
    if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 1:
        raise DataContractError("SHADOW_INTENT_BAD_ORDINAL.")
    inclusion = doc.get("scientific_inclusion_intent")
    if not isinstance(inclusion, str) or not inclusion.strip():
        raise DataContractError("SHADOW_INTENT_BAD_INCLUSION_INTENT.")
    prev_sha = doc.get("previous_observation_sha256")
    if prev_sha is not None and (
        not isinstance(prev_sha, str) or not _SHA64.fullmatch(prev_sha)
    ):
        raise DataContractError("SHADOW_INTENT_BAD_PREVIOUS_SHA.")
    if doc.get("backfill_allowed") is not False:
        raise DataContractError("SHADOW_INTENT_BACKFILL_NOT_FORBIDDEN.")
    if doc.get("automatic_skip_allowed") is not False:
        raise DataContractError("SHADOW_INTENT_SKIP_NOT_FORBIDDEN.")
    created = _parse_utc(doc.get("created_at_utc"), "intent created_at_utc")
    identity = doc.get("authority_identity")
    if not isinstance(identity, str) or not identity.strip():
        raise DataContractError("SHADOW_INTENT_BAD_IDENTITY.")
    now = _require_tz_aware(now_utc, "intent validation now_utc")
    if created > now:
        raise DataContractError("SHADOW_INTENT_FUTURE_CREATION.")
    # Inclusion intent MUST be locked before the target session opens:
    # the operator cannot decide inclusion after seeing the session return.
    target_open = calendar.get_session(target).open_utc
    if target_open is None:
        raise DataContractError(f"SHADOW_NO_OPEN_TIME: {target.isoformat()}.")
    if not created < target_open:
        raise DataContractError(
            f"SHADOW_INTENT_NOT_PRE_LOCKED: intent created at "
            f"{created.isoformat()} is not strictly before target open "
            f"{target_open.isoformat()}."
        )
    return ObservationIntent(
        hypothesis_id="HYP_011",
        target_session=target,
        observation_ordinal=ordinal,
        scientific_inclusion_intent=inclusion.strip(),
        previous_observation_sha256=prev_sha,
        backfill_allowed=False,
        automatic_skip_allowed=False,
        created_at_utc=created,
        authority_identity=identity.strip(),
    )


@dataclass(frozen=True)
class DispatchAuthority:
    """Single-use dispatch binding for one (ordinal, attempt, target) triple."""

    intent_sha256: str
    intent: ObservationIntent
    runtime_commit_sha: str
    target_session: date
    observation_ordinal: int
    dispatch_attempt: int
    valid_after_utc: datetime
    expires_at_utc: datetime
    ca_manifest_sha256: str
    paper_trading: bool
    live_trading: bool
    real_capital_authority_usd: str
    no_real_orders: bool
    authority_identity: str

    def canonical_doc(self) -> Dict[str, Any]:
        return {
            "schema_version": AUTHORITY_SCHEMA_VERSION,
            "intent_sha256": self.intent_sha256,
            "intent": self.intent.canonical_doc(),
            "runtime_commit_sha": self.runtime_commit_sha,
            "target_session": self.target_session.isoformat(),
            "observation_ordinal": self.observation_ordinal,
            "dispatch_attempt": self.dispatch_attempt,
            "valid_after_utc": self.valid_after_utc.isoformat(),
            "expires_at_utc": self.expires_at_utc.isoformat(),
            "ca_manifest_sha256": self.ca_manifest_sha256,
            "paper_trading": self.paper_trading,
            "live_trading": self.live_trading,
            "real_capital_authority_usd": self.real_capital_authority_usd,
            "no_real_orders": self.no_real_orders,
            "authority_identity": self.authority_identity,
        }

    def authority_sha256(self) -> str:
        return _canonical_sha256(self.canonical_doc())


def resolve_runtime_sha(explicit: Optional[str] = None) -> str:
    """Resolve the running checkout's commit SHA for runtime binding checks.

    An explicitly supplied SHA (operator pin / test injection) wins. Otherwise
    the local git checkout is queried. Unverifiable checkouts fail closed.
    """
    if explicit is not None:
        if not isinstance(explicit, str) or not _SHA40.fullmatch(explicit):
            raise DataContractError("SHADOW_RUNTIME_SHA_MALFORMED.")
        return explicit.lower()
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        sha = completed.stdout.strip().lower()
    except Exception as exc:
        raise DataContractError(
            "SHADOW_RUNTIME_SHA_UNVERIFIABLE: git checkout SHA unavailable."
        ) from exc
    if not _SHA40.fullmatch(sha):
        raise DataContractError("SHADOW_RUNTIME_SHA_MALFORMED.")
    return sha


def validate_dispatch_authority(
    doc: Mapping[str, Any],
    calendar: NyseCa1Calendar,
    now_utc: datetime,
    target_session: date,
    observation_ordinal: int,
    dispatch_attempt: int,
    state_prev_sha256: Optional[str],
    runtime_sha: str,
    ca_file_sha256: str,
) -> DispatchAuthority:
    """Fully validate a DispatchAuthority document against live invocation facts.

    Every binding is checked BEFORE any market-data network call. Any mismatch
    fails closed; malformed authorities never reach the attempt ledger.
    """
    if not isinstance(doc, Mapping):
        raise DataContractError("SHADOW_AUTHORITY_NOT_A_MAPPING.")
    if doc.get("schema_version") != AUTHORITY_SCHEMA_VERSION:
        raise DataContractError("SHADOW_AUTHORITY_SCHEMA_VERSION.")
    now = _require_tz_aware(now_utc, "authority validation now_utc")

    intent_doc = doc.get("intent")
    if not isinstance(intent_doc, Mapping):
        raise DataContractError("SHADOW_AUTHORITY_INTENT_MISSING.")
    intent = validate_observation_intent(intent_doc, calendar, now)
    declared_intent_sha = doc.get("intent_sha256")
    if not isinstance(declared_intent_sha, str) or (
        declared_intent_sha.lower() != intent.intent_sha256()
    ):
        raise DataContractError("SHADOW_AUTHORITY_INTENT_SHA_MISMATCH.")

    bound_runtime = doc.get("runtime_commit_sha")
    if not isinstance(bound_runtime, str) or bound_runtime.lower() != runtime_sha.lower():
        raise DataContractError(
            "SHADOW_AUTHORITY_RUNTIME_MISMATCH: authority binds a different "
            "runtime commit than this checkout."
        )
    try:
        bound_target = date.fromisoformat(str(doc.get("target_session")))
    except (ValueError, TypeError) as exc:
        raise DataContractError("SHADOW_AUTHORITY_BAD_TARGET.") from exc
    if bound_target != target_session:
        raise DataContractError("SHADOW_AUTHORITY_TARGET_MISMATCH.")
    if intent.target_session != target_session:
        raise DataContractError("SHADOW_INTENT_TARGET_MISMATCH.")
    bound_ordinal = doc.get("observation_ordinal")
    if bound_ordinal != observation_ordinal or intent.observation_ordinal != observation_ordinal:
        raise DataContractError("SHADOW_AUTHORITY_ORDINAL_MISMATCH.")
    bound_attempt = doc.get("dispatch_attempt")
    if (
        not isinstance(bound_attempt, int)
        or isinstance(bound_attempt, bool)
        or bound_attempt != dispatch_attempt
    ):
        raise DataContractError("SHADOW_AUTHORITY_ATTEMPT_MISMATCH.")
    if intent.previous_observation_sha256 != state_prev_sha256:
        raise DataContractError("SHADOW_AUTHORITY_CHAIN_HEAD_MISMATCH.")
    valid_after = _parse_utc(doc.get("valid_after_utc"), "authority valid_after_utc")
    expires_at = _parse_utc(doc.get("expires_at_utc"), "authority expires_at_utc")
    if not valid_after < expires_at:
        raise DataContractError("SHADOW_AUTHORITY_WINDOW_INVERTED.")
    if not valid_after <= now < expires_at:
        raise DataContractError(
            "SHADOW_AUTHORITY_OUTSIDE_VALIDITY_WINDOW: attempt is not valid now."
        )
    bound_ca_sha = doc.get("ca_manifest_sha256")
    if (
        not isinstance(bound_ca_sha, str)
        or not _SHA64.fullmatch(bound_ca_sha)
        or bound_ca_sha.lower() != ca_file_sha256.lower()
    ):
        raise DataContractError(
            "SHADOW_AUTHORITY_CA_SHA_MISMATCH: CA evidence file bytes differ "
            "from the bound manifest digest."
        )
    if doc.get("paper_trading") is not False:
        raise DataContractError("SHADOW_AUTHORITY_LOCKS_INVALID: paper_trading.")
    if doc.get("live_trading") is not False:
        raise DataContractError("SHADOW_AUTHORITY_LOCKS_INVALID: live_trading.")
    if str(doc.get("real_capital_authority_usd")) != "0.00":
        raise DataContractError("SHADOW_AUTHORITY_LOCKS_INVALID: capital.")
    if doc.get("no_real_orders") is not True:
        raise DataContractError("SHADOW_AUTHORITY_LOCKS_INVALID: no_real_orders.")
    identity = doc.get("authority_identity")
    if not isinstance(identity, str) or not identity.strip():
        raise DataContractError("SHADOW_AUTHORITY_BAD_IDENTITY.")
    return DispatchAuthority(
        intent_sha256=intent.intent_sha256(),
        intent=intent,
        runtime_commit_sha=runtime_sha.lower(),
        target_session=target_session,
        observation_ordinal=observation_ordinal,
        dispatch_attempt=dispatch_attempt,
        valid_after_utc=valid_after,
        expires_at_utc=expires_at,
        ca_manifest_sha256=ca_file_sha256.lower(),
        paper_trading=False,
        live_trading=False,
        real_capital_authority_usd="0.00",
        no_real_orders=True,
        authority_identity=identity.strip(),
    )


def attempt_ledger_key(
    authority_sha256: Optional[str],
    authorization: str,
    observation_ordinal: int,
    dispatch_attempt: int,
    target_session: date,
) -> str:
    """Deterministic single-use key for one authorized dispatch attempt."""
    return _canonical_sha256(
        {
            "authority_sha256": authority_sha256,
            "authorization": authorization,
            "observation_ordinal": observation_ordinal,
            "dispatch_attempt": dispatch_attempt,
            "target_session": target_session.isoformat(),
        }
    )


def consume_dispatch_attempt(
    state_dir: Path,
    ledger_key: str,
    record: Mapping[str, Any],
) -> Path:
    """Atomically record attempt consumption BEFORE any market-data network call.

    Uses O_EXCL create-once semantics: a second consumption of the same key
    (replay, crash-retry with identical authority, duplicate dispatch) fails
    closed with BLOCK_DISPATCH_AUTHORITY_REPLAY. The ledger directory holds
    operational consumption records only; it is not part of the scientific
    observation hash chain.
    """
    ledger_dir = state_dir / LEDGER_DIRNAME
    ledger_dir.mkdir(parents=True, exist_ok=True)
    entry_path = ledger_dir / f"{ledger_key}.json"
    payload = json.dumps(dict(record), indent=2, sort_keys=True)
    try:
        fd = os.open(str(entry_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise DataContractError(
            "BLOCK_DISPATCH_AUTHORITY_REPLAY: this dispatch attempt was "
            "already consumed; a new attempt requires a new explicit "
            "DispatchAuthority."
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except OSError as exc:
        raise DataContractError(
            f"BLOCK_DISPATCH_ATTEMPT_LEDGER_WRITE: {exc}."
        ) from exc
    return entry_path
