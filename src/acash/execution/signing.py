"""Phase 7 & Phase 13: Ed25519 Signing and Key Generation Utilities.

Isolated strictly into this module to maintain the AST closure boundary of
the verify-only Gate B activation runner (Rev 10 Section 7.3).

FOR TEST, CLI, AND OFFLINE CEREMONY USE ONLY.
Production signing must use HSM/KMS. Never persist private key material in plaintext.
"""

import base64
from typing import Tuple

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

from acash.core.domain.exceptions import DomainValidationError


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


class StorageEngineSigner:
    """Storage engine trust anchor for signing pointer transition records (B88, B93)."""

    def __init__(self, key_id: str, private_key_b64: str) -> None:
        self.key_id = key_id
        self._private_key_b64 = private_key_b64

    def sign(self, payload_bytes: bytes) -> str:
        return Ed25519Signer.sign(self._private_key_b64, payload_bytes)
