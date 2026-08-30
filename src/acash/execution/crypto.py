"""Phase 7: Ed25519 TrustStore and Signing Utilities.

All signature operations use Ed25519 (RFC 8032). Signatures are represented as
raw 64-byte Ed25519 signatures, base64-encoded (standard alphabet).
Public keys are raw 32-byte Ed25519 public keys, base64-encoded.

Design invariants:
- REVOKED keys fail ALL verification attempts, past and present.
- ROTATED keys remain verifiable for historical signatures where at_time falls
  within their valid interval — this preserves audit integrity of archived certificates.
- TrustStore.resolve() / TrustStore.verify() are MANDATORY — no None bypass.
- Ed25519Signer is FOR TEST/CLI USE ONLY. Production signing must use HSM/KMS.
"""

import base64
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator

from acash.core.domain.exceptions import DomainValidationError


class TrustStoreEntryStatus(str, Enum):
    """Lifecycle status of a trust-store key entry."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    ROTATED = "ROTATED"


class Ed25519TrustStoreEntry(BaseModel):
    """Single trusted Ed25519 signing-key record in the TrustStore."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key_id: str = Field(description="Stable key identifier. Must match issuer_public_key_id in certificates.")
    issuer_id: str = Field(description="Trust-root entity name.")
    algorithm: Literal["Ed25519"] = Field(default="Ed25519")
    public_key_b64: str = Field(
        description="Raw 32-byte Ed25519 public key, standard base64-encoded."
    )
    valid_from: datetime = Field(description="UTC timestamp from which this key is valid.")
    valid_until: Optional[datetime] = Field(
        default=None,
        description=(
            "UTC expiry timestamp. None = key does not expire. "
            "ROTATED keys remain verifiable for historical at_time within their valid interval."
        ),
    )
    status: TrustStoreEntryStatus = Field(default=TrustStoreEntryStatus.ACTIVE)
    predecessor_key_id: Optional[str] = Field(
        default=None,
        description="Key ID this entry rotates from, for audit chain.",
    )

    @field_validator("key_id", "issuer_id", "public_key_b64")
    @classmethod
    def validate_non_empty(cls, v: str, info: object) -> str:
        field_name = getattr(info, "field_name", "field") or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    def was_valid_at(self, signing_time: datetime) -> bool:
        """True if this key was within its valid interval at signing_time."""
        signing_utc = (
            signing_time
            if signing_time.tzinfo
            else signing_time.replace(tzinfo=timezone.utc)
        )
        valid_from_utc = (
            self.valid_from
            if self.valid_from.tzinfo
            else self.valid_from.replace(tzinfo=timezone.utc)
        )
        if signing_utc < valid_from_utc:
            return False
        if self.valid_until is not None:
            valid_until_utc = (
                self.valid_until
                if self.valid_until.tzinfo
                else self.valid_until.replace(tzinfo=timezone.utc)
            )
            if signing_utc > valid_until_utc:
                return False
        return True

    def load_public_key(self) -> Ed25519PublicKey:
        """Deserialize the base64 raw public key into a cryptography Ed25519PublicKey."""
        try:
            raw = base64.b64decode(self.public_key_b64, validate=True)
            if len(raw) != 32:
                raise ValueError(
                    f"expected 32 decoded bytes for an Ed25519 public key, got {len(raw)}"
                )
            return Ed25519PublicKey.from_public_bytes(raw)
        except Exception as exc:
            raise DomainValidationError(
                f"TrustStoreEntry '{self.key_id}': invalid public_key_b64: {exc}"
            ) from exc


class Ed25519TrustStore(BaseModel):
    """Mandatory trust-root registry for Ed25519 issuer and authority keys.

    All signature verification in Phase 7 MUST go through this object.
    There is no bypass path.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    entries: Tuple[Ed25519TrustStoreEntry, ...] = Field(
        min_length=1,
        description="Registered trust-store entries. Must contain at least one entry.",
    )

    def resolve(
        self,
        key_id: str,
        at_time: Optional[datetime] = None,
    ) -> Ed25519TrustStoreEntry:
        """Resolve a key by ID. Fails closed on all error conditions.

        Fail conditions (all raise DomainValidationError):
        - key_id not in registry
        - key status is REVOKED (historical re-use also rejected)
        - key was not valid at at_time (if provided) — used for historical audit

        ROTATED keys are resolvable when at_time falls within their valid_from..valid_until
        interval, preserving historical signature audit integrity.
        """
        for entry in self.entries:
            if entry.key_id == key_id:
                if entry.status == TrustStoreEntryStatus.REVOKED:
                    raise DomainValidationError(
                        f"TrustStore: key '{key_id}' has been REVOKED. "
                        "All verifications fail closed, including historical."
                    )
                if at_time is not None and not entry.was_valid_at(at_time):
                    raise DomainValidationError(
                        f"TrustStore: key '{key_id}' was not valid at "
                        f"{at_time.isoformat()}. Verification fails closed."
                    )
                return entry
        raise DomainValidationError(
            f"TrustStore: unknown key_id '{key_id}'. Verification fails closed."
        )

    def verify(
        self,
        key_id: str,
        payload_bytes: bytes,
        signature_b64: str,
        at_time: Optional[datetime] = None,
    ) -> None:
        """Verify an Ed25519 signature. Raises DomainValidationError on any failure.

        at_time: if provided, ensures the key was within its valid interval at signing
        time. Pass the certificate.created_at or approval.approved_at here.
        """
        entry = self.resolve(key_id, at_time=at_time)
        try:
            sig_bytes = base64.b64decode(signature_b64, validate=True)
            if len(sig_bytes) != 64:
                raise ValueError(
                    f"expected 64 decoded bytes for an Ed25519 signature, got {len(sig_bytes)}"
                )
        except Exception as exc:
            raise DomainValidationError(
                f"TrustStore.verify: invalid base64 signature for key '{key_id}': {exc}"
            ) from exc
        try:
            pub_key = entry.load_public_key()
            pub_key.verify(sig_bytes, payload_bytes)
        except InvalidSignature:
            raise DomainValidationError(
                f"TrustStore.verify: Ed25519 signature FAILED for key '{key_id}'."
            )
        except DomainValidationError:
            raise
        except Exception as exc:
            raise DomainValidationError(
                f"TrustStore.verify: verification error for key '{key_id}': {exc}"
            ) from exc


class Ed25519Signer:
    """Ed25519 key generation and signing utility.

    FOR TEST AND CLI USE ONLY.
    Production signing MUST use HSM/KMS or secure key storage.
    Never persist private key material in plaintext in production systems.
    """

    @staticmethod
    def generate_key_pair() -> Tuple[str, str]:
        """Generate a new Ed25519 key pair.

        Returns:
            (private_key_b64, public_key_b64) — raw bytes, standard base64.
        """
        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        )
        public_bytes = private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        return (
            base64.b64encode(private_bytes).decode(),
            base64.b64encode(public_bytes).decode(),
        )

    @staticmethod
    def sign(private_key_b64: str, payload_bytes: bytes) -> str:
        """Sign payload_bytes with a raw Ed25519 private key.

        Args:
            private_key_b64: standard base64-encoded 32-byte raw Ed25519 private key.
            payload_bytes: canonical message bytes to sign.

        Returns:
            Standard base64-encoded 64-byte Ed25519 signature.
        """
        try:
            raw = base64.b64decode(private_key_b64, validate=True)
            if len(raw) != 32:
                raise ValueError(
                    f"expected 32 decoded bytes for an Ed25519 private key, got {len(raw)}"
                )
            private_key = Ed25519PrivateKey.from_private_bytes(raw)
            sig = private_key.sign(payload_bytes)
            return base64.b64encode(sig).decode()
        except DomainValidationError:
            raise
        except Exception as exc:
            raise DomainValidationError(
                f"Ed25519Signer.sign: failed to sign payload: {exc}"
            ) from exc
