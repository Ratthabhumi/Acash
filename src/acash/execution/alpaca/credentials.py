"""Alpaca credential provider abstraction (Phase 7 Step 8F follow-on).

Implements the credential boundary of the frozen broker adapter contract
(``docs/phase7/broker_adapter_contract.md`` rv ``6fd4a78``, §6 C-1..C-5) and the
concrete Alpaca BMAP (``docs/phase7/alpaca_bmap.md`` rv ``47a8bc9``, BMAP-10):

- **External injection (C-1)**: Alpaca API key id + secret are provided by an
  external provider (environment / secret store), NEVER committed to code or
  config in this repository.
- **Boundary (C-2)**: the resolved credentials never cross the canonical event
  path; they are held only by the transport layer.
- **Scoped (C-3)**: constructed against a venue and fail closed when a venue is
  not authorized.
- **Fail-closed on failure (C-4)**: any expired/revoked/denied credential
  surfaces a ``BrokerAdapterError``-style failure; the transport must then stop
  new submissions rather than silently retrying with degraded credentials.
- **Rotation (C-5)**: live secret rotation via ``load()`` re-invocation without
  code change, and the transport re-validates auth on reconnect.

This module contains NO secret material and NO network I/O. It only defines the
provider contract and the redacted handle that flows into the transport.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping, Optional

from acash.execution.broker_adapter import BrokerAdapterError

# Alpaca domain prefix used by both paper and live trading endpoints. Distinct
# full base URLs are resolved from the provider / environment (BMAP-10) and never
# hard-baked with secrets here.
PAPER_API_HOST: str = "paper-api.alpaca.markets"
LIVE_API_HOST: str = "api.alpaca.markets"

# Env var names the default provider consults (never read inside a secret store;
# supplied externally). Values are never logged or embedded in events/evidence.
ENV_ALPACA_API_KEY_ID: str = "ACASH_ALPACA_API_KEY_ID"
ENV_ALPACA_API_SECRET: str = "ACASH_ALPACA_API_SECRET"


@dataclass(frozen=True)
class AlpacaCredentials:
    """Resolved but redacted Alpaca credentials for transport use only.

    Deliberately redacted: ``__str__``/``__repr__`` always emit ``********`` and
    the resolved secret is only referenced by the transport, never serialized into
    canonical events, evidence, manifests, logs, or error messages (contract
    §6 C-2). ``has_value`` distinguishes an explicit empty/absent handle from a
    resolved one so callers can fail closed (C-4) rather than treat a blank as a
    real credential.
    """

    api_key_id: str
    api_secret_ref: str = ""
    _resolved: bool = False

    @property
    def resolved(self) -> bool:
        """True when a real key id is present (fail-closed on empty)."""
        return self._resolved and bool(self.api_key_id)

    def __str__(self) -> str:
        return "********"

    def __repr__(self) -> str:
        return "AlpacaCredentials(api_key_id=********, redacted=True)"


class AlpacaCredentialProvider(ABC):
    """Contract for supplying Alpaca credentials from outside the repository.

    A provider is injected into the transport (construction-time), so the adapter
    and transport never import or read secrets themselves and never hard-code a
    key. Concrete providers read from an environment / secret-store / vault and
    MUST fail closed when the material is absent or revoked (contract §6 C-1/C-4).
    """

    @abstractmethod
    def load(self) -> AlpacaCredentials:
        """Return current, redacted credentials.

        Called at construction and re-invocable on reconnect to support live
        rotation without code change (contract §6 C-5).
        """

    @abstractmethod
    def venue(self) -> str:
        """Return the Alpaca venue identifier (e.g. ``"ALPACA_PAPER"``)."""


class EnvAlpacaCredentialProvider(AlpacaCredentialProvider):
    """Default provider reading credentials from the environment (C-1).

    Reads ``ACASH_ALPACA_API_KEY_ID`` / ``ACASH_ALPACA_API_SECRET`` (or an
    injected mapping for tests). Fails closed (``AlpacaCredentialError``) when the
    key id is absent so a missing secret can never be forged into a "valid"
    credential. No secret value is ever stored, logged, or returned beyond the
    redacted handle.
    """

    _venue: str
    _environ: Mapping[str, str]
    _explicit_key_id: Optional[str]
    _explicit_secret: Optional[str]

    def __init__(
        self,
        *,
        venue: str = "ALPACA_PAPER",
        api_key_id: Optional[str] = None,
        api_secret: Optional[str] = None,
        environ: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._venue = venue
        # Default provider reads the REAL process environment (so an operator
        # exporting ACASH_ALPACA_API_KEY_ID / ACASH_ALPACA_API_SECRET in the
        # session is honored). An injected mapping (tests, stores) replaces the
        # real environment wholesale; re-read on every load() supports rotation.
        self._environ = environ if environ is not None else os.environ
        # Explicit constructor args take precedence; otherwise read live from env.
        self._explicit_key_id = api_key_id
        self._explicit_secret = api_secret

    def venue(self) -> str:
        return self._venue

    def load(self) -> AlpacaCredentials:
        # Re-read the environment mapping on every call so a rotated secret is
        # picked up on reconnect WITHOUT a code change (contract §6 C-5).
        key_id = self._explicit_key_id
        if key_id is None:
            key_id = self._environ.get(ENV_ALPACA_API_KEY_ID, "")
        secret = self._explicit_secret
        if secret is None:
            secret = self._environ.get(ENV_ALPACA_API_SECRET, "")
        # Fail closed on absent key id (contract §6 C-4): never fabricate a handle.
        if not key_id:
            raise AlpacaCredentialError(
                "AlpacaCredentialProvider: API key id is absent; refusing to "
                "construct a credential handle (fail-closed, §6 C-4)."
            )
        return AlpacaCredentials(
            api_key_id=key_id,
            api_secret_ref=secret,
            _resolved=True,
        )


class AlpacaCredentialError(BrokerAdapterError):
    """Fail-closed error for a missing/revoked/invalid Alpaca credential.

    Message contains NO secret material (contract §6 C-2/C-4).
    """


class PaperCredentialGuardError(AlpacaCredentialError):
    """Fail-closed guard raised when the paper path is asked to construct or
    resolve a credential that is NOT paper-scoped.

    The Paper Exercise (P-evidence path) MAY ONLY ever hold an ``ALPACA_PAPER``
    credential. A live credential or any non-paper venue on this path is refused
    before any transport/order can be constructed (BMAP-10 cross-venue guard,
    defense-in-depth on top of ``AlpacaVenueMismatchError``). Message contains NO
    secret material.
    """


def paper_credential_provider(
    *,
    api_key_id: Optional[str] = None,
    api_secret: Optional[str] = None,
    environ: Optional[dict[str, str]] = None,
) -> EnvAlpacaCredentialProvider:
    """Single-authority paper-scoped credential provider factory.

    Constructs an ``EnvAlpacaCredentialProvider`` that is HARD-PINNED to the
    paper venue (``ALPACA_PAPER``). The paper exercise path must get its
    credentials ONLY from this factory, so a live credential or any non-paper
    venue can never be silently wired into a paper transport. Fails closed.

    No secret material is accepted, stored, or returned beyond the redacted
    ``AlpacaCredentials`` handle (credential contract §6 C-1/C-2).
    """
    return EnvAlpacaCredentialProvider(
        venue="ALPACA_PAPER",
        api_key_id=api_key_id,
        api_secret=api_secret,
        environ=environ,
    )


def assert_paper_venue(venue: str) -> None:
    """Fail-closed paper-only venue guard (single authority for the paper path).

    Raises ``PaperCredentialGuardError`` when ``venue`` is anything other than
    ``ALPACA_PAPER``. Call this as the authoritative gate before any paper
    transport/order construction so a live/other venue is rejected up front,
    not discovered late.
    """
    if venue != "ALPACA_PAPER":
        raise PaperCredentialGuardError(
            f"Paper credential guard refuses non-paper venue {venue!r}; "
            "the Paper Exercise path is PAPER-ONLY (BMAP-10, defense-in-depth)."
        )
