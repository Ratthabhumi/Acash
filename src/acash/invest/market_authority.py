"""ODR-004 gate, per-provider activation status and local credential lookup for market data.

A provider is READY only when ODR-004 is RATIFIED with ODR-001 as its ratified dependency, the
provider appears exactly once in ``scope_providers`` with the Owner's entitlement and display
attestations, and a credential exists in the Windows Credential Manager. Anything unknown is not
permission. Credentials are read per request, handed only to the provider adapter and never
returned, logged or written by ACASH.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

from acash.ppds.private_observation import SCHEMA_V1_2, _repo_root, odr_state

RECORD = Path("docs/governance/ODR_UPI_MARKET_DATA_004.json")
DECISION_ID = "ODR_UPI_MARKET_DATA_004"
CAPABILITY = "OWNER_MARKET_DATA_RETRIEVAL_AUTHORIZED"
REQUIRES = ["ODR_UPI_PRIVATE_OBSERVATION_001"]
CREDENTIAL_TARGET_PREFIX = "ACASH/MARKET_DATA/"
ADAPTED_PROVIDERS = ("ALPACA_BASIC", "MASSIVE_BASIC", "BOT_REFERENCE_FX")
KNOWN_PROVIDERS = ADAPTED_PROVIDERS + ("WEBULL_TH_OPENAPI",)
STATUSES = ("NOT_CONFIGURED", "GOVERNANCE_REQUIRED", "CREDENTIALS_REQUIRED", "ENTITLEMENT_REQUIRED",
            "DISPLAY_RIGHTS_UNVERIFIED", "READY", "RATE_LIMITED", "SERVICE_UNAVAILABLE")

Credential = Tuple[str, str]


class CredentialStore(Protocol):
    def lookup(self, provider_id: str) -> Optional[Credential]: ...


class WindowsCredentialStore:
    """Generic credentials named ``ACASH/MARKET_DATA/<PROVIDER_ID>`` (user name, secret)."""

    def lookup(self, provider_id: str) -> Optional[Credential]:
        if provider_id not in ADAPTED_PROVIDERS:
            return None
        return _cred_read(CREDENTIAL_TARGET_PREFIX + provider_id)


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
    """Activation status before any request; READY still says nothing about a live response."""
    if provider_id not in ADAPTED_PROVIDERS:
        return {"provider_id": provider_id, "status": "NOT_CONFIGURED", "detail": "NO_ADAPTER"}
    if state != "RATIFIED":
        return {"provider_id": provider_id, "status": "GOVERNANCE_REQUIRED", "detail": f"ODR_004_{state}"}
    entry = _scope_entry(doc, provider_id)
    if entry is None:
        return {"provider_id": provider_id, "status": "GOVERNANCE_REQUIRED", "detail": "PROVIDER_NOT_IN_SCOPE"}
    if store.lookup(provider_id) is None:
        return {"provider_id": provider_id, "status": "CREDENTIALS_REQUIRED", "detail": "NO_LOCAL_CREDENTIAL"}
    if entry.get("entitlement_verified") is not True:
        return {"provider_id": provider_id, "status": "ENTITLEMENT_REQUIRED", "detail": "ENTITLEMENT_NOT_ATTESTED"}
    if entry.get("display_permitted") is not True:
        return {"provider_id": provider_id, "status": "DISPLAY_RIGHTS_UNVERIFIED", "detail": "DISPLAY_NOT_ATTESTED"}
    return {"provider_id": provider_id, "status": "READY", "detail": "ATTESTED_NOT_LIVE_VERIFIED",
            "cache_permitted": entry.get("cache_permitted") is True}


def provider_statuses(store: CredentialStore, record: Optional[Path] = None,
                      observation_record: Optional[Path] = None) -> Tuple[str, List[Dict[str, Any]]]:
    state, doc = record_state(record, observation_record)
    return state, [provider_status(p, state, doc, store) for p in KNOWN_PROVIDERS]
