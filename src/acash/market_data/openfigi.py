"""OpenFIGI identity discovery (candidate FIGI data), never a price, FX or execution provider.

The connector is deliberately narrow: one HTTPS host, POST only to ``/v3/mapping``, the API key in
the ``X-OPENFIGI-APIKEY`` header (never a URL), at most 100 jobs per request and a conservative
local limiter. A single returned candidate is **not** an Owner-confirmed identity; the caller must
keep the states distinct and never merge securities from a ticker alone.

No request is made by importing or constructing this module: callers gate on the identity provider's
configured credential and on the Owner's explicit choice to run a connectivity test.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError

HOST = "api.openfigi.com"
MAPPING_PATH = "/v3/mapping"
MAX_JOBS = 100
MAX_RESPONSE_BYTES = 1_000_000
TIMEOUT_SECONDS = 10.0
X_OPENFIGI_APIKEY = "X-OPENFIGI-APIKEY"
_ID_VALUE = re.compile(r"^[A-Za-z0-9._:\-]{1,32}$")
ID_TYPES = frozenset({"TICKER", "ISIN", "CUSIP", "SEDOL", "FIGI", "COMMON"})

NO_CANDIDATE = "NO_CANDIDATE"
SINGLE_CANDIDATE = "SINGLE_CANDIDATE"
MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
CANDIDATE_REVIEW_REQUIRED = "CANDIDATE_REVIEW_REQUIRED"
OWNER_CONFIRMED = "OWNER_CONFIRMED"
UNVERIFIED = "UNVERIFIED"

JsonPost = Callable[[str, Mapping[str, str], bytes], Tuple[int, bytes]]


@dataclass(frozen=True)
class IdentityCandidate:
    ticker: Optional[str]
    name: Optional[str]
    figi: Optional[str]
    composite_figi: Optional[str]
    share_class_figi: Optional[str]
    exch_code: Optional[str]
    security_type: Optional[str]
    security_type2: Optional[str]
    market_sector: Optional[str]
    security_description: Optional[str]


@dataclass(frozen=True)
class MappingResult:
    job: Dict[str, str]
    status: str                      # NO_CANDIDATE | SINGLE_CANDIDATE | MULTIPLE_CANDIDATES
    candidates: Tuple[IdentityCandidate, ...]
    code: Optional[str] = None

    @property
    def owner_confirmation_required(self) -> bool:
        return self.status != NO_CANDIDATE


def urllib_post(url: str, headers: Mapping[str, str], body: bytes) -> Tuple[int, bytes]:
    """POST only to the fixed OpenFIGI mapping endpoint: TLS verified, no proxy, no redirect."""
    from urllib.parse import urlsplit

    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != HOST or parsed.port is not None or parsed.query
            or parsed.fragment or parsed.path != MAPPING_PATH or parsed.username or parsed.password):
        raise DataContractError("IDENTITY_ENDPOINT_NOT_ALLOWED: OPENFIGI_IDENTITY.")
    if set(headers) - {"Content-Type", X_OPENFIGI_APIKEY}:
        raise DataContractError("IDENTITY_HEADER_NOT_ALLOWED: OPENFIGI_IDENTITY.")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            return int(response.status), response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        return int(exc.code), b""
    except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError):
        raise DataContractError("IDENTITY_UNREACHABLE: OPENFIGI_IDENTITY.") from None


def _status_error(status: int) -> DataContractError:
    if status in (401, 403):
        return DataContractError(f"IDENTITY_ACCESS_DENIED: OPENFIGI_IDENTITY HTTP {status}.")
    if status == 429:
        return DataContractError("IDENTITY_RATE_LIMITED: OPENFIGI_IDENTITY.")
    if status == 413:
        return DataContractError("IDENTITY_REQUEST_TOO_LARGE: OPENFIGI_IDENTITY.")
    if status in (500, 502, 503, 504):
        return DataContractError(f"IDENTITY_UNAVAILABLE: OPENFIGI_IDENTITY HTTP {status}.")
    return DataContractError(f"IDENTITY_REQUEST_INVALID: OPENFIGI_IDENTITY HTTP {status}.")


@dataclass
class OpenFIGIIdentityProvider:
    """Identifier mapping against the documented V3 API. No price semantics whatsoever."""

    credential: Tuple[str, str]      # (provider_id, api_key)
    post: JsonPost
    allow: Callable[[], bool]
    clock: Callable[[], datetime]
    provider_id: str = "OPENFIGI_IDENTITY"
    limit: int = MAX_JOBS

    @property
    def api_key(self) -> str:
        return self.credential[1] or self.credential[0]

    def _jobs(self, id_type: str, values: Sequence[str], **extra: str) -> List[Dict[str, str]]:
        if id_type not in ID_TYPES:
            raise DataContractError(f"IDENTITY_ID_TYPE_UNSUPPORTED: {id_type}.")
        jobs = []
        seen = set()
        for value in values:
            text = str(value).strip()
            if not _ID_VALUE.match(text):
                raise DataContractError("IDENTITY_ID_VALUE_INVALID.")
            if text in seen:
                continue
            seen.add(text)
            jobs.append({"idType": id_type, "idValue": text, **extra})
        return jobs

    def map_identifiers(self, id_type: str, values: Sequence[str], **filters: str) -> List[MappingResult]:
        jobs = self._jobs(id_type, values, **filters)
        results: List[MappingResult] = []
        for start in range(0, len(jobs), self.limit):
            results.extend(self._map_batch(jobs[start:start + self.limit]))
        return results

    def _map_batch(self, jobs: List[Dict[str, str]]) -> List[MappingResult]:
        if not jobs:
            return []
        if not self.allow():
            raise DataContractError("IDENTITY_RATE_LIMITED: OPENFIGI_IDENTITY.")
        body = json.dumps([{k: v for k, v in job.items() if v is not None} for job in jobs]).encode("utf-8")
        headers = {"Content-Type": "application/json", X_OPENFIGI_APIKEY: self.api_key}
        status, payload = self.post(f"https://{HOST}{MAPPING_PATH}", headers, body)
        if status != 200:
            raise _status_error(status)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise DataContractError("IDENTITY_RESPONSE_INVALID: OPENFIGI_IDENTITY too large.")
        try:
            doc = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise DataContractError("IDENTITY_RESPONSE_INVALID: OPENFIGI_IDENTITY malformed JSON.") from None
        if not isinstance(doc, list) or len(doc) != len(jobs):
            raise DataContractError("IDENTITY_RESPONSE_INVALID: OPENFIGI_IDENTITY envelope.")
        out: List[MappingResult] = []
        for job, entry in zip(jobs, doc):
            if not isinstance(entry, dict):
                raise DataContractError("IDENTITY_RESPONSE_INVALID: OPENFIGI_IDENTITY entry.")
            if "error" in entry:
                out.append(MappingResult(job, NO_CANDIDATE, (), code=str(entry["error"])[:80]))
                continue
            data = entry.get("data")
            if not isinstance(data, list):
                raise DataContractError("IDENTITY_RESPONSE_INVALID: OPENFIGI_IDENTITY data.")
            candidates = tuple(self._candidate(row) for row in data if isinstance(row, dict))
            state = NO_CANDIDATE if not candidates else SINGLE_CANDIDATE if len(candidates) == 1 else MULTIPLE_CANDIDATES
            out.append(MappingResult(job, state, candidates))
        return out

    @staticmethod
    def _candidate(row: Mapping[str, Any]) -> IdentityCandidate:
        def text(key: str) -> Optional[str]:
            value = row.get(key)
            return None if value is None else str(value)[:128]
        figi = text("figi")
        if figi is not None and not re.match(r"^BBG[A-Z0-9]{9}$", figi):
            figi = None
        return IdentityCandidate(ticker=text("ticker"), name=text("name"), figi=figi,
                                 composite_figi=text("compositeFIGI"), share_class_figi=text("shareClassFIGI"),
                                 exch_code=text("exchCode"), security_type=text("securityType"),
                                 security_type2=text("securityType2"), market_sector=text("marketSector"),
                                 security_description=text("securityDescription"))


def confirm_candidate(result: MappingResult, figi: str, *, owner_confirmed: bool) -> str:
    """Owner confirmation is explicit; a single API hit is still only a candidate."""
    if not owner_confirmed or result.status == NO_CANDIDATE:
        return UNVERIFIED if result.status == NO_CANDIDATE else CANDIDATE_REVIEW_REQUIRED
    return OWNER_CONFIRMED if any(c.figi == figi for c in result.candidates) else UNVERIFIED
