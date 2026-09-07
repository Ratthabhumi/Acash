"""Phase 14 Slice 2 Retrieval Layer: Source Identity, Request, Result & Evidence Schemas.

FAIL-CLOSED CONTRACT
--------------------
1. Every model is frozen and forbids extra fields (``ConfigDict(frozen=True, extra="forbid")``).
2. Retrieval SUCCESS is evidence COLLECTION, never VERIFIED knowledge:
   ``RetrievalResult.epistemic_classification`` defaults to REPORTED and can NEVER be VERIFIED.
3. Content identity is ``raw_content_sha256`` over the exact received bytes; timestamps
   (request ``created_at_utc``, ``retrieved_at_utc``, ``recorded_at_utc``) are metadata only
   and are excluded from content identity.
4. RAW content hash and NORMALIZED content hash are always kept distinct.
5. Cross-record binding (result <-> request <-> source) is validated at construction time.

Canonical JSON hashing reuses the SINGLE canonical dict-hash authority ``_canonical_sha256``
from the Slice 1 schema module (``acash.research.ai.schema``); no duplicate hashing helper
is introduced.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.research.ai.enums import EvidenceClassification, SourceType
from acash.research.ai.retrieval.enums import (
    NormalizationPolicy,
    RetrievalMode,
    RetrievalStatus,
)
from acash.research.ai.retrieval.exceptions import InvalidResultStateError, RetrievalError
from acash.research.ai.schema import _canonical_sha256

_SHA256_64: str = r"^[0-9a-fA-F]{64}$"
_SRC_ID: str = r"^SRC-[0-9a-fA-F]{8,32}$"
_REQ_ID: str = r"^RET-REQ-[0-9a-fA-F]{8,32}$"
_RES_ID: str = r"^RET-RES-[0-9a-fA-F]{8,32}$"
_EVID_ID: str = r"^EVID-[0-9a-fA-F]{8,32}$"


def utc_now_iso() -> str:
    """Current UTC timestamp as a deterministic ISO-8601 string (metadata only, never content)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


# ---------------------------------------------------------------------------
# 1. Source Identity
# ---------------------------------------------------------------------------


class SourceRetrievalPolicy(BaseModel):
    """Non-enforcing retrieval policy metadata for a source.

    These values describe known constraints and preferences. They carry ZERO authority:
    a ``RetrievalRequest`` always carries its own explicit, authoritative timeout,
    size and content-type constraints.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    preferred_timeout_seconds: Optional[float] = Field(default=None, ge=0)
    declared_max_content_bytes: Optional[int] = Field(default=None, gt=0)
    declared_content_types: Tuple[str, ...] = Field(default=())
    notes: Tuple[str, ...] = Field(default=())

    def compute_canonical_digest(self) -> str:
        payload: Dict[str, Any] = {
            "declared_content_types": list(self.declared_content_types),
            "declared_max_content_bytes": self.declared_max_content_bytes,
            "notes": list(self.notes),
            "preferred_timeout_seconds": self.preferred_timeout_seconds,
        }
        return _canonical_sha256(payload)


class SourceDescriptor(BaseModel):
    """Immutable identity descriptor of an external research source.

    Unknown metadata MUST remain explicitly unknown (None), never fabricated.
    This is a RETRIEVAL-FACING identity (how to fetch). Epistemic claim
    classification lives on the retrieval result (REPORTED-by-default), and evidence
    tri-axial classification lives in Slice 1's ``ResearchSourceMetadata``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(pattern=_SRC_ID)
    locator: str = Field(min_length=1, description="URL or canonical source reference")
    source_type: SourceType
    publisher_or_owner: Optional[str] = Field(default=None, description="None when unknown")
    title: Optional[str] = Field(default=None, description="None when unknown")
    recorded_at_utc: str
    retrieval_policy: SourceRetrievalPolicy = Field(default_factory=SourceRetrievalPolicy)

    def compute_canonical_digest(self) -> str:
        payload: Dict[str, Any] = {
            "locator": self.locator,
            "publisher_or_owner": self.publisher_or_owner,
            "recorded_at_utc": self.recorded_at_utc,
            "retrieval_policy": self.retrieval_policy.compute_canonical_digest(),
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "title": self.title,
        }
        return _canonical_sha256(payload)


# ---------------------------------------------------------------------------
# 2. Retrieval Request
# ---------------------------------------------------------------------------


class RetrievalRequest(BaseModel):
    """Immutable, deterministic, serializable request for a single source retrieval."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(pattern=_REQ_ID)
    source_id: str = Field(pattern=_SRC_ID, description="Must match a registered SourceDescriptor")
    locator: str = Field(min_length=1, description="Must equal the source descriptor locator")
    mode: RetrievalMode = RetrievalMode.FULL
    timeout_seconds: float = Field(gt=0)
    max_content_bytes: int = Field(gt=0)
    accepted_content_types: Tuple[str, ...] = Field(min_length=1)
    conditional_etag: Optional[str] = None
    conditional_last_modified_utc: Optional[str] = None
    created_at_utc: str

    def compute_canonical_digest(self) -> str:
        payload: Dict[str, Any] = {
            "accepted_content_types": list(self.accepted_content_types),
            "conditional_etag": self.conditional_etag,
            "conditional_last_modified_utc": self.conditional_last_modified_utc,
            "created_at_utc": self.created_at_utc,
            "locator": self.locator,
            "max_content_bytes": self.max_content_bytes,
            "mode": self.mode.value,
            "request_id": self.request_id,
            "source_id": self.source_id,
            "timeout_seconds": self.timeout_seconds,
        }
        return _canonical_sha256(payload)


# ---------------------------------------------------------------------------
# 3. Retrieval Provenance
# ---------------------------------------------------------------------------


class RetrievalProvenance(BaseModel):
    """Provenance record answering the eight audit questions:

    - What source was requested? ``source_id``
    - What locator was used? ``locator``
    - When was it retrieved? ``requested_at_utc`` / ``retrieved_at_utc``
    - What provider performed retrieval? ``provider_id``
    - What bytes/content were actually received? ``content_bytes_observed`` + ``content_ref``
    - What hash identifies the content? ``raw_content_sha256``
    - Was content normalized? ``normalization_policy`` + ``normalized_content_sha256``
    - What retrieval status occurred? ``retrieval_status`` + ``http_status``
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(pattern=_SRC_ID)
    locator: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    requested_at_utc: str
    retrieved_at_utc: str
    http_status: Optional[int] = None
    content_type_received: Optional[str] = None
    content_bytes_observed: int = Field(ge=0)
    raw_content_sha256: Optional[str] = Field(default=None, pattern=_SHA256_64)
    normalized_content_sha256: Optional[str] = Field(default=None, pattern=_SHA256_64)
    normalization_policy: NormalizationPolicy = NormalizationPolicy.NONE
    retrieval_mode: RetrievalMode
    retrieval_status: RetrievalStatus
    content_ref: str = Field(min_length=1, description="Location/key of the raw content bytes")

    def compute_canonical_digest(self) -> str:
        payload: Dict[str, Any] = {
            "content_bytes_observed": self.content_bytes_observed,
            "content_ref": self.content_ref,
            "content_type_received": self.content_type_received,
            "http_status": self.http_status,
            "locator": self.locator,
            "normalization_policy": self.normalization_policy.value,
            "normalized_content_sha256": self.normalized_content_sha256,
            "provider_id": self.provider_id,
            "raw_content_sha256": self.raw_content_sha256,
            "requested_at_utc": self.requested_at_utc,
            "retrieval_mode": self.retrieval_mode.value,
            "retrieval_status": self.retrieval_status.value,
            "retrieved_at_utc": self.retrieved_at_utc,
            "source_id": self.source_id,
        }
        return _canonical_sha256(payload)


# ---------------------------------------------------------------------------
# 4. Retrieval Result
# ---------------------------------------------------------------------------


class RetrievalResult(BaseModel):
    """Immutable outcome of a single retrieval attempt.

    INVARIANTS:
    - ``epistemic_classification`` can never be VERIFIED: retrieval success is evidence
      collection, not verification.
    - SUCCESS requires a raw content hash, a positive observed byte count, and a content ref.
    - A normalized hash is only admissible together with a non-NONE normalization policy.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    result_id: str = Field(pattern=_RES_ID)
    request_id: str = Field(pattern=_REQ_ID)
    source_id: str = Field(pattern=_SRC_ID)
    retrieval_status: RetrievalStatus
    retrieved_at_utc: str
    http_status: Optional[int] = None
    returned_content_type: Optional[str] = None
    content_length_bytes: int = Field(default=0, ge=0)
    raw_content_sha256: Optional[str] = Field(default=None, pattern=_SHA256_64)
    normalized_content_sha256: Optional[str] = Field(default=None, pattern=_SHA256_64)
    normalization_policy: NormalizationPolicy = NormalizationPolicy.NONE
    raw_content_ref: Optional[str] = Field(default=None, description="None when no content acquired")
    error_detail: Optional[str] = None
    provenance: RetrievalProvenance
    epistemic_classification: EvidenceClassification = EvidenceClassification.REPORTED

    @field_validator("epistemic_classification")
    @classmethod
    def forbid_verified_epistemic_state(cls, v: Any) -> Any:
        if v == EvidenceClassification.VERIFIED:
            raise RetrievalError(
                "Retrieved content cannot be classified VERIFIED. "
                "Retrieval success is evidence collection, not independent verification."
            )
        return v

    @model_validator(mode="after")
    def validate_status_consistency(self) -> "RetrievalResult":
        if self.retrieval_status == RetrievalStatus.SUCCESS:
            if self.raw_content_sha256 is None or self.content_length_bytes <= 0 or self.raw_content_ref is None:
                raise InvalidResultStateError(
                    "SUCCESS retrieval requires raw_content_sha256, positive content_length_bytes, and raw_content_ref."
                )
        if self.normalized_content_sha256 is not None and self.normalization_policy == NormalizationPolicy.NONE:
            raise InvalidResultStateError(
                "normalized_content_sha256 requires a non-NONE normalization_policy."
            )
        if self.normalization_policy != NormalizationPolicy.NONE and self.normalized_content_sha256 is None:
            raise InvalidResultStateError(
                "Non-NONE normalization_policy requires normalized_content_sha256."
            )
        return self

    def compute_canonical_digest(self) -> str:
        payload: Dict[str, Any] = {
            "content_length_bytes": self.content_length_bytes,
            "epistemic_classification": self.epistemic_classification.value,
            "error_detail": self.error_detail,
            "http_status": self.http_status,
            "normalization_policy": self.normalization_policy.value,
            "normalized_content_sha256": self.normalized_content_sha256,
            "provenance": self.provenance.compute_canonical_digest(),
            "raw_content_ref": self.raw_content_ref,
            "raw_content_sha256": self.raw_content_sha256,
            "request_id": self.request_id,
            "result_id": self.result_id,
            "retrieved_at_utc": self.retrieved_at_utc,
            "returned_content_type": self.returned_content_type,
            "retrieval_status": self.retrieval_status.value,
            "source_id": self.source_id,
        }
        return _canonical_sha256(payload)


# ---------------------------------------------------------------------------
# 5. Immutable Evidence Record
# ---------------------------------------------------------------------------


class EvidenceRecord(BaseModel):
    """Immutable evidence record binding a source descriptor, request and result.

    The record digest covers the full event (identity of this specific evidence event).
    Content identity is the raw content hash on the result, which is independent of
    timestamps by construction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(pattern=_EVID_ID)
    source: SourceDescriptor
    request: RetrievalRequest
    result: RetrievalResult
    recorded_at_utc: str

    @property
    def content_identity_sha256(self) -> Optional[str]:
        """Content identity: raw content hash (timestamps excluded by construction)."""
        return self.result.raw_content_sha256

    @field_validator("result")
    @classmethod
    def forbid_verified_epistemic_result(cls, result: RetrievalResult) -> RetrievalResult:
        # Pydantic model_copy(update=...) defaults to validate=False, so the
        # RetrievalResult __init__ validator is NOT the enforceable boundary.
        # This validator re-arms the invariant at the EvidenceRecord boundary:
        # a VERIFIED result (however constructed) is rejected at record creation.
        if result.epistemic_classification == EvidenceClassification.VERIFIED:
            raise RetrievalError(
                "An evidence record cannot wrap VERIFIED retrieved content. "
                "Retrieval success is evidence collection, not independent verification."
            )
        return result

    @model_validator(mode="after")
    def verify_cross_references(self) -> "EvidenceRecord":
        def _require(condition: bool, message: str) -> None:
            if not condition:
                raise InvalidResultStateError(message)

        _require(
            self.request.source_id == self.source.source_id,
            f"request.source_id '{self.request.source_id}' != source.source_id '{self.source.source_id}'.",
        )
        _require(
            self.request.locator == self.source.locator,
            "request.locator does not match source descriptor locator.",
        )
        _require(
            self.result.request_id == self.request.request_id,
            "result.request_id does not match request.request_id.",
        )
        _require(
            self.result.source_id == self.request.source_id,
            "result.source_id does not match request.source_id.",
        )
        _require(
            self.result.provenance.source_id == self.source.source_id,
            "provenance.source_id does not match source.source_id.",
        )
        _require(
            self.result.provenance.locator == self.request.locator,
            "provenance.locator does not match request.locator.",
        )
        _require(
            self.result.provenance.locator == self.source.locator,
            "provenance.locator does not match source descriptor locator.",
        )
        _require(
            self.result.provenance.retrieved_at_utc == self.result.retrieved_at_utc,
            "provenance.retrieved_at_utc does not match result.retrieved_at_utc.",
        )
        _require(
            self.result.provenance.raw_content_sha256 == self.result.raw_content_sha256,
            "provenance.raw_content_sha256 does not match result.raw_content_sha256.",
        )
        _require(
            self.result.provenance.normalized_content_sha256 == self.result.normalized_content_sha256,
            "provenance.normalized_content_sha256 does not match result.normalized_content_sha256.",
        )
        _require(
            self.result.provenance.content_bytes_observed == self.result.content_length_bytes,
            "provenance.content_bytes_observed does not match result.content_length_bytes.",
        )
        _require(
            self.result.provenance.http_status == self.result.http_status,
            "provenance.http_status does not match result.http_status.",
        )
        _require(
            self.result.provenance.content_type_received == self.result.returned_content_type,
            "provenance.content_type_received does not match result.returned_content_type.",
        )
        _require(
            self.result.provenance.retrieval_status == self.result.retrieval_status,
            "provenance.retrieval_status does not match result.retrieval_status.",
        )
        _require(
            self.result.provenance.requested_at_utc == self.request.created_at_utc,
            "provenance.requested_at_utc does not match request.created_at_utc.",
        )
        return self

    def compute_record_digest(self) -> str:
        payload: Dict[str, Any] = {
            "evidence_id": self.evidence_id,
            "recorded_at_utc": self.recorded_at_utc,
            "request": self.request.compute_canonical_digest(),
            "result": self.result.compute_canonical_digest(),
            "source": self.source.compute_canonical_digest(),
        }
        return _canonical_sha256(payload)