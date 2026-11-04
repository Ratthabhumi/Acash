"""ODR-004 gate, per-provider activation status and local credential lookup for market data.

A provider is READY only when ODR-004 is RATIFIED with ODR-001 as its ratified dependency, the
provider appears exactly once in ``scope_providers`` with the Owner's entitlement, display,
calculation and derived-value attestations, its adapter contract is verified, and a credential
exists in the Windows Credential Manager. Anything unknown is not permission. Credentials are read per request, handed only to the provider adapter and never
returned, logged or written by ACASH.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.ppds.private_observation import SCHEMA_V1_2, _repo_root, odr_state

RECORD = Path("docs/governance/ODR_UPI_MARKET_DATA_004.json")
DECISION_ID = "ODR_UPI_MARKET_DATA_004"
CAPABILITY = "OWNER_MARKET_DATA_RETRIEVAL_AUTHORIZED"
REQUIRES = ["ODR_UPI_PRIVATE_OBSERVATION_001"]
CREDENTIAL_TARGET_PREFIX = "ACASH/MARKET_DATA/"
ADAPTED_PROVIDERS = ("ALPACA_BASIC", "ALPACA_HISTORICAL", "MARKETDATA_APP_FREE", "FRANKFURTER_ECB_FX",
                     "MASSIVE_BASIC", "BOT_REFERENCE_FX")
KNOWN_PROVIDERS = ADAPTED_PROVIDERS + ("WEBULL_TH_OPENAPI",)
# Providers that authenticate without a stored credential (published keyless endpoints).
KEYLESS_PROVIDERS = frozenset({"FRANKFURTER_ECB_FX"})
# Identity providers are a separate authority from price/FX feeds: they return candidate FIGI
# metadata, never a quote, and reuse the same credential store under their own namespace.
IDENTITY_PROVIDERS = ("OPENFIGI_IDENTITY",)
IDENTITY_CREDENTIAL_TARGET_PREFIX = "ACASH/IDENTITY/"
# Bank of Thailand API products the Owner subscribes to. Each has its own credential target; none has
# a verified adapter/endpoint contract yet, so they are registered for credential management only and
# stay out of ADAPTED_PROVIDERS (which must mirror the implemented endpoint allowlist).
BOT_PRODUCTS = ("BOT_EXCHANGE_RATES", "BOT_INTEREST_RATES", "BOT_STATISTICS", "BOT_DEBT_AUCTION",
                "BOT_LICENSE_CHECK", "BOT_OTHERS")
# One Owner-supplied credential may serve several read-only feeds of the same vendor. The alias only
# reuses the secret: it never implies entitlement, display or derived-use rights, which each provider
# must still attest separately before it can become READY.
CREDENTIAL_ALIASES: Dict[str, str] = {"ALPACA_HISTORICAL": "ALPACA_BASIC"}
STATUSES = ("NOT_CONFIGURED", "GOVERNANCE_REQUIRED", "CONTRACT_UNVERIFIED", "CREDENTIALS_REQUIRED",
            "ENTITLEMENT_REQUIRED", "DISPLAY_RIGHTS_UNVERIFIED", "DERIVED_USE_UNVERIFIED", "READY",
            "RATE_LIMITED", "SERVICE_UNAVAILABLE")
# Canonical provider registry. ``contract_verified`` means the request/response contract comes from
# the provider's published documentation as supplied by research, not from a live response.
REGISTRY: Dict[str, Dict[str, Any]] = {
    "ALPACA_BASIC": {"role": "PRICE", "quote_type": "LAST_TRADE", "coverage": "IEX_ONLY", "label": "REALTIME_IEX_ONLY",
                     "contract_verified": True, "rate_limit": "200/min", "timestamp_policy": "TRADE_TIMESTAMP_RFC3339",
                     "known_restriction": None},
    "MASSIVE_BASIC": {"role": "PRICE", "quote_type": "EOD_CLOSE", "coverage": "UNKNOWN", "label": "PREVIOUS_ELIGIBLE_EOD",
                      "contract_verified": True, "rate_limit": "5/min", "timestamp_policy": "SESSION_EPOCH_MS",
                      "known_restriction": "TERMS_MAY_RESTRICT_DERIVED_WORKS_INCLUDING_NAV"},
    "BOT_REFERENCE_FX": {"role": "FX", "quote_type": "DAILY_REFERENCE_RATE", "coverage": "REFERENCE_FX_NOT_EXECUTABLE",
                         "label": "REFERENCE_FX_NOT_EXECUTABLE", "contract_verified": False, "rate_limit": "200/hour",
                         "timestamp_policy": "PERIOD_DATE_BANGKOK", "known_restriction": "RESPONSE_SCHEMA_UNVERIFIED"},
    "ALPACA_HISTORICAL": {"role": "PRICE", "quote_type": "HISTORICAL_BAR",
                          "coverage": "CONSOLIDATED", "label": "INTRADAY_BAR_CLOSE_OR_EOD_CLOSE",
                          "contract_verified": True, "rate_limit": "200/min",
                          "timestamp_policy": "BAR_OPEN_RFC3339",
                          "known_restriction": "BASIC_PLAN_SIP_DELAY_ENFORCED"},
    "MARKETDATA_APP_FREE": {"role": "PRICE", "quote_type": "HISTORICAL_DELAYED_LAST",
                            "coverage": "UNKNOWN", "label": "HISTORICAL_DELAYED_LAST",
                            "contract_verified": True, "rate_limit": "100_credits/day @ 09:30 ET",
                            "timestamp_policy": "UNIX_SECONDS_NEW_YORK",
                            "known_restriction": "EXCHANGE_AGREEMENT_AND_DERIVED_VALUE_RIGHTS_UNVERIFIED"},
    "FRANKFURTER_ECB_FX": {"role": "FX", "quote_type": "DAILY_REFERENCE_RATE",
                           "coverage": "REFERENCE_FX_NOT_EXECUTABLE", "label": "REFERENCE_FX_NOT_EXECUTABLE",
                           "contract_verified": True, "rate_limit": "UNKNOWN",
                           "timestamp_policy": "DATE_UTC",
                           "known_restriction": "REFERENCE_ONLY_NOT_EXECUTABLE"},
    "WEBULL_TH_OPENAPI": {"role": "PRICE", "quote_type": None, "coverage": "UNKNOWN", "label": None,
                          "contract_verified": False, "rate_limit": None, "timestamp_policy": None,
                          "known_restriction": "OPENAPI_ENTITLEMENT_PENDING"},
}
# Owner attestations a scope entry may carry; every one defaults to UNKNOWN.
ATTESTATIONS = ("entitlement_verified", "display_permitted", "calculation_permitted", "derived_value_permitted",
                "cache_permitted", "retention_policy_verified")

Credential = Tuple[str, str]


class CredentialStore(Protocol):
    def lookup(self, provider_id: str) -> Optional[Credential]: ...


def credential_target(provider_id: str) -> str:
    """The Windows Credential Manager target for one adapted market-data, identity or BOT product."""
    if provider_id in IDENTITY_PROVIDERS:
        return IDENTITY_CREDENTIAL_TARGET_PREFIX + provider_id
    if provider_id in BOT_PRODUCTS:
        return CREDENTIAL_TARGET_PREFIX + provider_id
    if provider_id not in ADAPTED_PROVIDERS:
        raise DataContractError(f"PROVIDER_NOT_ADAPTED: {provider_id}.")
    return CREDENTIAL_TARGET_PREFIX + provider_id


class WindowsCredentialStore:
    """Generic credentials named ``ACASH/MARKET_DATA/<PROVIDER_ID>`` (user name, secret).

    An aliased provider (``ALPACA_HISTORICAL`` -> ``ALPACA_BASIC``) reads the vendor's single
    read-only credential when it has no target of its own; this reuses the secret only and grants
    no entitlement or data-use right.
    """

    def lookup(self, provider_id: str) -> Optional[Credential]:
        if provider_id not in ADAPTED_PROVIDERS:
            return None
        found = _cred_read(CREDENTIAL_TARGET_PREFIX + provider_id)
        if found is None and provider_id in CREDENTIAL_ALIASES:
            return _cred_read(CREDENTIAL_TARGET_PREFIX + CREDENTIAL_ALIASES[provider_id])
        return found


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _Credential(ctypes.Structure):
        _fields_ = [("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
                    ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
                    ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                    ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
                    ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
                    ("UserName", wintypes.LPWSTR)]

    def _cred_read(target: str) -> Optional[Credential]:
        advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        pointer = ctypes.POINTER(_Credential)()
        if not advapi.CredReadW(target, 1, 0, ctypes.byref(pointer)):
            return None
        try:
            cred = pointer.contents
            secret = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize).decode("utf-16-le")
            return (cred.UserName or "", secret) if secret else None
        except UnicodeDecodeError:
            return None
        finally:
            advapi.CredFree(pointer)
else:
    def _cred_read(target: str) -> Optional[Credential]:
        return None


if sys.platform == "win32":
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2
    CRED_MAX_BLOB_BYTES = 2560
    ERROR_NOT_FOUND = 1168

    def _cred_write(target: str, username: str, secret: str) -> None:
        """Store one generic credential for the current Windows user through CredWriteW.

        The secret never passes through a command line: callers read it interactively and hand it
        straight to this function. Errors carry the Win32 code only, never the value.
        """
        blob = secret.encode("utf-16-le")
        if not blob or len(blob) > CRED_MAX_BLOB_BYTES:
            raise DataContractError("CREDENTIAL_INVALID: secret length.")
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        cred = _Credential()
        cred.Flags = 0
        cred.Type = CRED_TYPE_GENERIC
        cred.TargetName = target
        cred.Comment = None
        cred.LastWritten = wintypes.FILETIME()
        cred.CredentialBlobSize = len(blob)
        cred.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        cred.Persist = CRED_PERSIST_LOCAL_MACHINE
        cred.AttributeCount = 0
        cred.Attributes = None
        cred.TargetAlias = None
        cred.UserName = username
        advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        if not advapi.CredWriteW(ctypes.byref(cred), 0):
            raise DataContractError(f"CREDENTIAL_WRITE_FAILED: WinError {ctypes.get_last_error()}.")

    def _cred_delete(target: str) -> bool:
        advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        if advapi.CredDeleteW(target, CRED_TYPE_GENERIC, 0):
            return True
        return ctypes.get_last_error() == ERROR_NOT_FOUND
else:
    def _cred_write(target: str, username: str, secret: str) -> None:
        raise DataContractError("CREDENTIAL_STORE_UNSUPPORTED: Windows Credential Manager only.")

    def _cred_delete(target: str) -> bool:
        raise DataContractError("CREDENTIAL_STORE_UNSUPPORTED: Windows Credential Manager only.")


class WindowsCredentialWriter:
    """Write side of the same store the refresh path reads; values are never returned or logged."""

    def store(self, provider_id: str, credential: Credential) -> str:
        target = credential_target(provider_id)
        username, secret = credential
        if not secret:
            raise DataContractError("CREDENTIAL_INVALID: empty secret.")
        _cred_write(target, username, secret)
        return target

    def remove(self, provider_id: str) -> bool:
        return _cred_delete(credential_target(provider_id))


def identity_credential(provider_id: str = "OPENFIGI_IDENTITY") -> Optional[Credential]:
    """Read-only lookup for an identity provider; absence is not an error."""
    if provider_id not in IDENTITY_PROVIDERS:
        raise DataContractError(f"IDENTITY_PROVIDER_UNKNOWN: {provider_id}.")
    return _cred_read(IDENTITY_CREDENTIAL_TARGET_PREFIX + provider_id)


def record_state(record: Optional[Path] = None, observation_record: Optional[Path] = None) -> Tuple[str, Dict[str, Any]]:
    """(state, record) where state is an ``odr_state`` value or DEPENDENCY_NOT_RATIFIED."""
    path = record or (_repo_root() / RECORD)
    state = odr_state(path, None, CAPABILITY)
    if state != "RATIFIED":
        return state, {}
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("decision_id") != DECISION_ID or not isinstance(doc.get("scope_providers"), list):
        return "RECORD_INVALID", {}
    if doc.get("requires") != REQUIRES or odr_state(observation_record, SCHEMA_V1_2) != "RATIFIED":
        return "DEPENDENCY_NOT_RATIFIED", {}
    return state, doc


def _scope_entry(doc: Dict[str, Any], provider_id: str) -> Optional[Dict[str, Any]]:
    entries = [e for e in doc.get("scope_providers") or [] if isinstance(e, dict) and e.get("provider_id") == provider_id]
    return entries[0] if len(entries) == 1 else None


def provider_status(provider_id: str, state: str, doc: Dict[str, Any], store: CredentialStore) -> Dict[str, Any]:
    """Activation status before any request; READY still says nothing about a live response.

    ``capabilities`` reports each right independently (ATTESTED / DENIED / UNKNOWN / ESTABLISHED / MISSING /
    NOT_OBSERVED); READY needs governance, a verified contract, a credential and the entitlement,
    display, calculation and derived-value attestations. Authentication and real responses are
    never established here.
    """
    entry = _scope_entry(doc, provider_id) if state == "RATIFIED" else None
    reg = REGISTRY.get(provider_id, {})
    caps: Dict[str, str] = {
        "governance_authorized": "ESTABLISHED" if entry is not None else "MISSING",
        "contract_verified": "ESTABLISHED" if reg.get("contract_verified") is True else "UNKNOWN",
        "credentials_configured": "UNKNOWN",
        "authentication_verified": "NOT_OBSERVED",
        "real_response_verified": "NOT_OBSERVED",
    }
    for name in ATTESTATIONS:
        value = None if entry is None else entry.get(name)
        caps[name] = "ATTESTED" if value is True else "DENIED" if value is False else "UNKNOWN"
    out: Dict[str, Any] = {"provider_id": provider_id, "capabilities": caps,
                           "registry": {k: reg.get(k) for k in ("role", "quote_type", "coverage", "label",
                                                                 "rate_limit", "known_restriction")},
                           "cache_permitted": caps["cache_permitted"] == "ATTESTED"}

    def done(status: str, detail: str) -> Dict[str, Any]:
        out.update(status=status, detail=detail)
        return out

    if provider_id not in ADAPTED_PROVIDERS:
        return done("NOT_CONFIGURED", "NO_ADAPTER")
    if provider_id in KEYLESS_PROVIDERS:
        caps["credentials_configured"] = "ESTABLISHED"
    else:
        caps["credentials_configured"] = "ESTABLISHED" if store.lookup(provider_id) is not None else "MISSING"
    if state != "RATIFIED":
        return done("GOVERNANCE_REQUIRED", f"ODR_004_{state}")
    if entry is None:
        return done("GOVERNANCE_REQUIRED", "PROVIDER_NOT_IN_SCOPE")
    if caps["contract_verified"] != "ESTABLISHED":
        return done("CONTRACT_UNVERIFIED", "ADAPTER_CONTRACT_NOT_VERIFIED")
    if caps["credentials_configured"] != "ESTABLISHED":
        return done("CREDENTIALS_REQUIRED", "NO_LOCAL_CREDENTIAL")
    if caps["entitlement_verified"] != "ATTESTED":
        return done("ENTITLEMENT_REQUIRED", "ENTITLEMENT_NOT_ATTESTED")
    if caps["display_permitted"] != "ATTESTED":
        return done("DISPLAY_RIGHTS_UNVERIFIED", "DISPLAY_NOT_ATTESTED")
    if caps["calculation_permitted"] != "ATTESTED" or caps["derived_value_permitted"] != "ATTESTED":
        return done("DERIVED_USE_UNVERIFIED", "CALCULATION_OR_DERIVED_VALUE_NOT_ATTESTED")
    return done("READY", "ATTESTED_NOT_LIVE_VERIFIED")


def provider_statuses(store: CredentialStore, record: Optional[Path] = None,
                      observation_record: Optional[Path] = None) -> Tuple[str, List[Dict[str, Any]]]:
    state, doc = record_state(record, observation_record)
    return state, [provider_status(p, state, doc, store) for p in KNOWN_PROVIDERS]


def bot_product_credentials() -> Dict[str, str]:
    """Credential presence per BOT product (never the value)."""
    return {pid: ("CONFIGURED" if _cred_read(CREDENTIAL_TARGET_PREFIX + pid) is not None else "MISSING")
            for pid in BOT_PRODUCTS}
