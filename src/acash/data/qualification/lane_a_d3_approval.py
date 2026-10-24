"""D3-00 offline approval-envelope contract (OFFLINE ONLY — NO AUTHORITY).

Bounded cryptographic verification contract for a future Lane A approval,
testable hermetically with EPHEMERAL TEST KEYS ONLY. Reuses the existing
Ed25519 primitives (``Ed25519Signer`` for signing, ``Ed25519TrustStore``
key loading) instead of inventing new crypto.

Design:
- ``ApprovalEnvelope``: frozen dataclass binding approval_ref,
  scope_digest, runtime_sha, validity window, budgets, and key_id, with
  ``canonical_message_bytes()`` under an explicit domain separator
  (``ACASH-LANE-A-APPROVAL/v2``; v1 was never merged) over sorted-JSON
  canonical form.
- ``InMemoryTrustRoot``: TEST-ONLY trust material (key_id -> public key
  plus a revocation set; no persistence, no production keys, never
  loaded from environment). Key identity is established on DECODED key
  bytes (Base64 text aliasing rejected). ``verify_envelope`` fails
  closed on: unknown key, revoked key, expired/not-yet-valid window,
  malformed envelope, altered bytes, and invalid signatures.
- ``EnvelopeApprovalCheck``: adapter implementing the ``check(approval)``
  seam consumed by ``CanaryApproval.verify_approval``: it verifies the
  envelope signature AND binds all eight signed claims
  (approval_ref, scope_digest, runtime_sha, validity window, both
  budgets, paid budget) to the presented approval. A reference string
  alone still proves nothing; only a verifying envelope under a
  configured trust root admits a plan.

What this does NOT establish: production trust-root custody, key
rotation ceremony, revocation distribution, clock authority, or any
operator approval. Those remain external human prerequisites.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from acash.core.domain.exceptions import DataContractError
from acash.execution.signing import Ed25519Signer

ENVELOPE_DOMAIN: bytes = b"ACASH-LANE-A-APPROVAL/v2"

_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")


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
        """Domain-separated canonical bytes covered by the signature.

        Schema v2 (v1 was never merged or ratified): binds key_id so a
        signature cannot be transplanted across signer identities.
        """
        document = {
            "adjustment": None,
            "approval_ref": self.approval_ref,
            "domain": ENVELOPE_DOMAIN.decode("ascii"),
            "key_id": self.key_id,
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


def verify_ed25519_signature(
    public_key_b64: str, message: bytes, signature_b64: str
) -> None:
    """Verify one Ed25519 signature over ``message``; fail closed on any gap."""
    if not signature_b64:
        raise DataContractError("D3_VERIFY_MISSING_SIGNATURE.")
    try:
        public_bytes = base64.b64decode(public_key_b64, validate=True)
        signature = base64.b64decode(signature_b64, validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
    except Exception as exc:
        raise DataContractError("D3_VERIFY_MALFORMED_MATERIAL.") from exc
    try:
        public_key.verify(signature, message)
    except InvalidSignature as exc:
        raise DataContractError(
            "D3_VERIFY_BAD_SIGNATURE: envelope bytes differ from signed content."
        ) from exc


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
        """Register a test public key (explicit test act, never implicit).

        Identity is established on DECODED key bytes, never on Base64
        text: distinct Base64 strings can decode to identical bytes when
        pad bits are noncanonical, so string comparison alone would admit
        the same key under two identities and make revocation ambiguous.
        """
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
        registered_bytes = {
            base64.b64decode(known, validate=True)
            for known in self._keys.values()
        }
        if raw in registered_bytes:
            raise DataContractError(
                "D3_TRUST_KEY_ALIAS: these public-key bytes are already "
                "registered under a different identity; aliasing would make "
                "revocation ambiguous."
            )
        self._keys[key_id] = public_key_b64

    def revoke(self, key_id: str) -> None:
        """Revoke a registered key (fail-closed on unknown identity)."""
        if key_id not in self._keys:
            raise DataContractError(
                f"D3_TRUST_UNKNOWN_KEY: {key_id!r}."
            )
        self._revoked.add(key_id)

    def verify_signature(
        self,
        *,
        key_id: str,
        message: bytes,
        signature_b64: str,
        now_utc: str,
        valid_from_utc: str,
        valid_until_utc: str,
    ) -> None:
        """Verify a domain-separated signed message against this trust root.

        This is the shared primitive used by both the Lane A approval
        envelope and the D5 evidence envelope. It checks key trust,
        revocation, the signed validity window, signature presence, and the
        Ed25519 signature itself. It does not interpret the message.
        """
        if key_id not in self._keys:
            raise DataContractError(f"D3_VERIFY_UNTRUSTED_KEY: {key_id!r}.")
        if key_id in self._revoked:
            raise DataContractError(f"D3_VERIFY_REVOKED_KEY: {key_id!r}.")
        moment = _require_aware_instant(now_utc, "now_utc")
        start = _require_aware_instant(valid_from_utc, "valid_from_utc")
        end = _require_aware_instant(valid_until_utc, "valid_until_utc")
        if not (start <= moment <= end):
            raise DataContractError("D3_VERIFY_EXPIRED.")
        verify_ed25519_signature(self._keys[key_id], message, signature_b64)

    def verify_envelope(self, envelope: ApprovalEnvelope, now_utc: str) -> None:
        """Verify envelope against this trust root; fail closed on any gap."""
        self.verify_signature(
            key_id=envelope.key_id,
            message=envelope.canonical_message_bytes(),
            signature_b64=envelope.signature_b64,
            now_utc=now_utc,
            valid_from_utc=envelope.valid_from_utc,
            valid_until_utc=envelope.valid_until_utc,
        )


class EnvelopeApprovalCheck:
    """Adapter for the ``check(approval)`` verifier seam.

    Binds a verified envelope to a presented canary approval across EVERY
    signed claim: approval_ref, scope_digest (64-hex), runtime_sha,
    valid_from_utc, valid_until_utc, max_operations, max_bytes (positive
    ints, bools rejected), and paid_budget_usd. Anything less fails
    closed. The constructor ``now_utc`` is the check instant the caller
    supplies per invocation (normally the dispatch instant); a stale
    instant is a caller fault, and expiry is evaluated against it — never
    against a wall clock read here. This adapter plus an explicitly
    configured trust root is what future offline tests pass as the
    verifier plug.
    """

    CLAIM_FIELDS: tuple[str, ...] = (
        "approval_ref",
        "scope_digest",
        "runtime_sha",
        "valid_from_utc",
        "valid_until_utc",
        "max_operations",
        "max_bytes",
        "paid_budget_usd",
    )

    def __init__(
        self, envelope: ApprovalEnvelope, trust_root: InMemoryTrustRoot, now_utc: str
    ) -> None:
        self._envelope = envelope
        self._trust_root = trust_root
        self._now_utc = now_utc

    def check(self, approval: Any) -> bool:
        """Return True only for a fully bound, verified approval."""
        self._trust_root.verify_envelope(self._envelope, self._now_utc)
        for field_name in self.CLAIM_FIELDS:
            if getattr(approval, field_name, None) != getattr(self._envelope, field_name):
                return False
        scope_digest = getattr(approval, "scope_digest", None)
        if not isinstance(scope_digest, str) or not _HEX64_PATTERN.match(scope_digest):
            return False
        runtime_sha = getattr(approval, "runtime_sha", None)
        if not isinstance(runtime_sha, str) or not _HEX40_PATTERN.match(runtime_sha):
            return False
        for budget_field in ("max_operations", "max_bytes"):
            budget = getattr(approval, budget_field, None)
            if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
                return False
        return True


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
