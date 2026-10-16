"""D3-00 offline approval-envelope contract (OFFLINE ONLY — NO AUTHORITY).

Bounded cryptographic verification contract for a future Lane A approval,
testable hermetically with EPHEMERAL TEST KEYS ONLY. Reuses the existing
Ed25519 primitives (``Ed25519Signer`` for signing, ``Ed25519TrustStore``
key loading) instead of inventing new crypto.

Design:
- ``ApprovalEnvelope``: frozen dataclass binding approval_ref,
  scope_digest, runtime_sha, validity window, budgets, and key_id, with
  ``canonical_message_bytes()`` under an explicit domain separator
  (``ACASH-LANE-A-APPROVAL/v1``) over sorted-JSON canonical form.
- ``InMemoryTrustRoot``: TEST-ONLY trust material (key_id -> public key
  plus a revocation set; no persistence, no production keys, never
  loaded from environment). ``verify_envelope`` fails closed on: unknown
  key, revoked key, expired/not-yet-valid window, malformed envelope,
  altered bytes, and invalid signatures.
- ``EnvelopeApprovalCheck``: adapter implementing the ``check(approval)``
  seam consumed by ``CanaryApproval.verify_approval``: it verifies the
  envelope signature AND binds envelope.approval_ref/scope/runtime to
  the presented approval. A reference string alone still proves nothing;
  only a verifying envelope under a configured trust root admits a plan.

What this does NOT establish: production trust-root custody, key
rotation ceremony, revocation distribution, clock authority, or any
operator approval. Those remain external human prerequisites.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from acash.core.domain.exceptions import DataContractError
from acash.execution.signing import Ed25519Signer

ENVELOPE_DOMAIN: bytes = b"ACASH-LANE-A-APPROVAL/v1"


def _require_aware_instant(value: str, context: str) -> datetime:
    try:
        moment = datetime.fromisoformat(str(value))
    except (ValueError, TypeError) as exc:
        raise DataContractError(
            f"D3_ENVELOPE_MALFORMED_TIME: {context}: {value!r}."
        ) from exc
    if moment.tzinfo is None:
        raise DataContractError(
            f"D3_ENVELOPE_NAIVE_TIME: {context} must be timezone-aware."
        )
    return moment


@dataclass(frozen=True)
class ApprovalEnvelope:
    """Signed approval envelope (offline verification contract)."""

    key_id: str
    approval_ref: str
    scope_digest: str
    runtime_sha: str
    valid_from_utc: str
    valid_until_utc: str
    max_operations: int
    max_bytes: int
    paid_budget_usd: str
    signature_b64: str = ""

    def __post_init__(self) -> None:
        if not self.key_id or not self.key_id.strip():
            raise DataContractError("D3_ENVELOPE_EMPTY_KEY_ID.")
        if not self.approval_ref or not self.approval_ref.strip():
            raise DataContractError("D3_ENVELOPE_EMPTY_REF.")
        if not isinstance(self.scope_digest, str) or len(self.scope_digest) != 64:
            raise DataContractError("D3_ENVELOPE_BAD_SCOPE_DIGEST.")
        start = _require_aware_instant(self.valid_from_utc, "valid_from_utc")
        end = _require_aware_instant(self.valid_until_utc, "valid_until_utc")
        if start >= end:
            raise DataContractError("D3_ENVELOPE_EMPTY_WINDOW.")
        if self.max_operations <= 0 or self.max_bytes <= 0:
            raise DataContractError("D3_ENVELOPE_NONPOSITIVE_BUDGET.")

    def canonical_message_bytes(self) -> bytes:
        """Domain-separated canonical bytes covered by the signature."""
        document = {
            "adjustment": None,
            "approval_ref": self.approval_ref,
            "domain": ENVELOPE_DOMAIN.decode("ascii"),
            "max_bytes": self.max_bytes,
            "max_operations": self.max_operations,
            "paid_budget_usd": self.paid_budget_usd,
            "runtime_sha": self.runtime_sha,
            "scope_digest": self.scope_digest,
            "valid_from_utc": self.valid_from_utc,
            "valid_until_utc": self.valid_until_utc,
        }
        return ENVELOPE_DOMAIN + b"." + json.dumps(
            document, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    def message_sha256(self) -> str:
        """Digest of the canonical signed message (audit linkage)."""
        return hashlib.sha256(self.canonical_message_bytes()).hexdigest()


def sign_envelope(envelope: ApprovalEnvelope, private_key_b64: str) -> ApprovalEnvelope:
    """Attach a signature using ephemeral test key material (offline only)."""
    import dataclasses

    signature = Ed25519Signer.sign(private_key_b64, envelope.canonical_message_bytes())
    return dataclasses.replace(envelope, signature_b64=signature)


class InMemoryTrustRoot:
    """TEST-ONLY trust material: key registry + revocation set.

    No persistence, no environment loading, no production keys. A real
    deployment needs a separately governed trust-root ceremony; this class
    proves the verification LOGIC only.
    """

    def __init__(self) -> None:
        self._keys: Dict[str, str] = {}
        self._revoked: set[str] = set()

    def register(self, key_id: str, public_key_b64: str) -> None:
        """Register a test public key (explicit test act, never implicit)."""
        if not key_id or not key_id.strip():
            raise DataContractError("D3_TRUST_EMPTY_KEY_ID.")
        try:
            raw = base64.b64decode(public_key_b64, validate=True)
        except Exception as exc:
            raise DataContractError(
                f"D3_TRUST_MALFORMED_KEY: {key_id!r}."
            ) from exc
        if len(raw) != 32:
            raise DataContractError(
                f"D3_TRUST_MALFORMED_KEY: {key_id!r} must decode to 32 bytes."
            )
        if key_id in self._keys:
            raise DataContractError(
                f"D3_TRUST_DUP_KEY: {key_id!r} already registered."
            )
        self._keys[key_id] = public_key_b64

    def revoke(self, key_id: str) -> None:
        """Revoke a registered key (fail-closed on unknown identity)."""
        if key_id not in self._keys:
            raise DataContractError(
                f"D3_TRUST_UNKNOWN_KEY: {key_id!r}."
            )
        self._revoked.add(key_id)

    def verify_envelope(self, envelope: ApprovalEnvelope, now_utc: str) -> None:
        """Verify envelope against this trust root; fail closed on any gap."""
        if envelope.key_id not in self._keys:
            raise DataContractError(
                f"D3_VERIFY_UNTRUSTED_KEY: {envelope.key_id!r}."
            )
        if envelope.key_id in self._revoked:
            raise DataContractError(
                f"D3_VERIFY_REVOKED_KEY: {envelope.key_id!r}."
            )
        moment = _require_aware_instant(now_utc, "now_utc")
        start = _require_aware_instant(envelope.valid_from_utc, "valid_from_utc")
        end = _require_aware_instant(envelope.valid_until_utc, "valid_until_utc")
        if not (start <= moment <= end):
            raise DataContractError("D3_VERIFY_EXPIRED.")
        if not envelope.signature_b64:
            raise DataContractError("D3_VERIFY_MISSING_SIGNATURE.")
        try:
            public_bytes = base64.b64decode(self._keys[envelope.key_id], validate=True)
            signature = base64.b64decode(envelope.signature_b64, validate=True)
        except Exception as exc:
            raise DataContractError(
                "D3_VERIFY_MALFORMED_MATERIAL."
            ) from exc
        try:
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(
                signature, envelope.canonical_message_bytes()
            )
        except InvalidSignature as exc:
            raise DataContractError(
                "D3_VERIFY_BAD_SIGNATURE: envelope bytes differ from signed content."
            ) from exc


class EnvelopeApprovalCheck:
    """Adapter for the ``check(approval)`` verifier seam.

    Binds a verified envelope to a presented canary approval: envelope
    signature valid AND approval_ref/scope_digest/runtime_sha identical.
    Anything less fails closed. This adapter plus an explicitly configured
    trust root is what future offline tests pass as the verifier plug.
    """

    def __init__(
        self, envelope: ApprovalEnvelope, trust_root: InMemoryTrustRoot, now_utc: str
    ) -> None:
        self._envelope = envelope
        self._trust_root = trust_root
        self._now_utc = now_utc

    def check(self, approval: Any) -> bool:
        """Return True only for a fully bound, verified approval."""
        self._trust_root.verify_envelope(self._envelope, self._now_utc)
        approval_ref = getattr(approval, "approval_ref", None)
        scope_digest = getattr(approval, "scope_digest", None)
        runtime_sha = getattr(approval, "runtime_sha", None)
        return (
            approval_ref == self._envelope.approval_ref
            and scope_digest == self._envelope.scope_digest
            and runtime_sha == self._envelope.runtime_sha
        )


def admit_byte_population(
    content_encoding: str, wire_len: int, decoded_len: int
) -> str:
    """Classify which byte population a cap governs (offline contract).

    - ``IDENTITY_SINGLE_POPULATION``: no content coding; wire bytes ==
      decoded bytes == stored bytes; one cap and one digest suffice.
    - ``DUAL_POPULATION_REQUIRED``: content coding active; wire and decoded
      populations differ, so a single cap/hash cannot honestly cover both.
      Real dispatch must then either enforce identity encoding or ratify a
      dual-evidence contract. Returns the classification; never silently
      picks a population.
    """
    if not isinstance(wire_len, int) or not isinstance(decoded_len, int):
        raise DataContractError("D3_BYTE_POPULATION_BAD_LENGTH.")
    if wire_len < 0 or decoded_len < 0:
        raise DataContractError("D3_BYTE_POPULATION_NEGATIVE.")
    coding = (content_encoding or "").strip().lower()
    if coding in ("", "identity"):
        if wire_len != decoded_len:
            raise DataContractError(
                "D3_BYTE_POPULATION_CONTRADICTION: identity coding requires "
                "wire_len == decoded_len."
            )
        return "IDENTITY_SINGLE_POPULATION"
    return "DUAL_POPULATION_REQUIRED"
