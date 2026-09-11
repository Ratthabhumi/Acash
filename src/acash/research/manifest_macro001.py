"""CAND-FREE-MACRO-001 D18 Reproducibility Manifest Domain Models & Validation.

Strictly enforces:
1. Pydantic v2 validation with ConfigDict(frozen=True, extra="forbid").
2. Single canonical cryptographic authority over specification lineage, code provenance,
   data sources, protocol parameters, and execution semantics.
3. Strict fail-closed boundary: zero silent floors, zero magic hashes, fail-closed on mismatch.
4. Sealed manifests require clean Git tree, sealed timestamp, and exact canonical SHA-256 match.
5. Draft manifests require status=DRAFT_UNSEALED, sealed_at_utc=None, manifest_sha256="0"*64.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError, DomainValidationError


def canonical_json_dumps(payload: Dict[str, Any]) -> str:
    """Serialize payload to deterministic canonical JSON (sorted keys, compact delimiters, UTF-8)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_payload_sha256(payload: Dict[str, Any]) -> str:
    """Compute SHA-256 digest over canonical JSON representation of payload."""
    canonical_str = canonical_json_dumps(payload)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


class ManifestStatus(str, Enum):
    """Lifecycle status of reproducibility manifest."""

    DRAFT_UNSEALED = "DRAFT_UNSEALED"
    SEALED_PRE_REGISTRATION = "SEALED_PRE_REGISTRATION"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"


class DataSourceAuthorityStatus(str, Enum):
    """Authority status classification for data sources."""

    RATIFIED_AUTHORITATIVE = "RATIFIED_AUTHORITATIVE"
    DATA_AUTHORITY_BLOCKED = "DATA_AUTHORITY_BLOCKED"


class Macro001SpecificationLineage(BaseModel):
    """Cryptographic lineage hashes of frozen specification markdown documents."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    specification_version: str = Field(min_length=1)
    decision_surface_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    round4_specification_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    binding_worksheet_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


class Macro001CodeProvenance(BaseModel):
    """Code and toolchain environment provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    git_commit_hash: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    git_tree_dirty: bool
    pyproject_toml_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    uv_lock_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    python_version: str = Field(min_length=1)


class Macro001DataSourceRecord(BaseModel):
    """Audit descriptor for an individual research data source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: Literal["S-01", "S-02", "S-03", "S-04", "S-05"]
    authority_status: DataSourceAuthorityStatus
    retrieval_timestamp_utc: Optional[str] = None
    vintage_policy: str = Field(min_length=1)
    raw_artifact_sha256: Optional[str] = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    canonical_parquet_sha256: Optional[str] = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    row_count: Optional[int] = Field(default=None, ge=0)


class Macro001ParameterGridCell(BaseModel):
    """Parameter cell in the declared K=3 grid."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cell_id: Literal["G1_1H", "G1_2H", "G1_4H"]
    horizon_hours: Literal[1, 2, 4]


class Macro001ProtocolParameters(BaseModel):
    """Immutable protocol parameters frozen across Rounds 0-5."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_universe: Tuple[str, ...] = Field(min_length=1)
    timezone: str = Field(default="America/New_York")
    event_window: str = Field(default="W-1")
    return_formula: str = Field(default="R-EC")
    baseline: str = Field(default="B-A")
    overlap_rule: str = Field(default="O-2")
    tie_break_rule: str = Field(default="TR-1")
    calendar_authority: str = Field(default="CA-1")
    parameter_grid: Tuple[Macro001ParameterGridCell, ...] = Field(min_length=3, max_length=3)
    trial_count_k: Literal[3] = 3
    is_start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    is_end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    oos_start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    oos_end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    blind_start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    blind_end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    statistical_test: str = Field(default="TWO_WAY_CLUSTERED_T_TEST")
    degrees_of_freedom: str = Field(default="G-1")
    alpha_significance_level: float = Field(default=0.05, ge=0.05, le=0.05)
    primary_hypothesis: str = Field(default="H0: E[D] = 0 vs H1: E[D] != 0 (Two-Sided)")


class Macro001ExecutionSemantics(BaseModel):
    """Execution, census, and numerical invariants."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kill_conditions: Tuple[str, ...] = Field(min_length=1)
    census_semantics: str = Field(default="D6_FROZEN_CENSUS_K3_MIXED_FAILS_CLOSED")
    invalid_policy: str = Field(default="NON_NEGATIVE_EVIDENCE_FAIL_CLOSED_LOGGED")
    numerical_precision: str = Field(default="DECIMAL_PRICES_FLOAT64_STATS_ZERO_MAGIC_FLOORS")


class Macro001ReproducibilityManifest(BaseModel):
    """Canonical D18 Reproducibility Manifest for CAND-FREE-MACRO-001."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str = Field(pattern=r"^MANIFEST_MACRO_001_\d{8}_[0-9a-fA-F]{8}$")
    schema_version: Literal["v1.0.0"] = "v1.0.0"
    candidate_id: Literal["CAND-FREE-MACRO-001"] = "CAND-FREE-MACRO-001"
    status: ManifestStatus
    created_at_utc: str
    sealed_at_utc: Optional[str] = None
    specification_lineage: Macro001SpecificationLineage
    code_provenance: Macro001CodeProvenance
    data_sources: Tuple[Macro001DataSourceRecord, ...] = Field(min_length=5, max_length=5)
    protocol_parameters: Macro001ProtocolParameters
    execution_semantics: Macro001ExecutionSemantics
    manifest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")

    def to_canonical_dict(self) -> Dict[str, Any]:
        """Convert manifest to raw dictionary suitable for canonical serialization."""
        return {
            "candidate_id": self.candidate_id,
            "code_provenance": self.code_provenance.model_dump(),
            "created_at_utc": self.created_at_utc,
            "data_sources": [s.model_dump() for s in self.data_sources],
            "execution_semantics": self.execution_semantics.model_dump(),
            "manifest_id": self.manifest_id,
            "protocol_parameters": self.protocol_parameters.model_dump(),
            "schema_version": self.schema_version,
            "sealed_at_utc": self.sealed_at_utc,
            "specification_lineage": self.specification_lineage.model_dump(),
            "status": self.status.value,
        }

    def compute_canonical_digest(self) -> str:
        """Compute deterministic SHA-256 digest over the canonical payload excluding manifest_sha256."""
        payload = self.to_canonical_dict()
        return compute_payload_sha256(payload)

    def to_canonical_json(self) -> str:
        """Serialize complete manifest to canonical JSON string including manifest_sha256."""
        full_payload = self.to_canonical_dict()
        full_payload["manifest_sha256"] = self.manifest_sha256
        return canonical_json_dumps(full_payload)

    @model_validator(mode="after")
    def validate_manifest_contract(self) -> "Macro001ReproducibilityManifest":
        """Strict fail-closed verification of lifecycle status, git cleanliness, and cryptographic digest."""
        if self.status == ManifestStatus.DRAFT_UNSEALED:
            if self.sealed_at_utc is not None:
                raise DataContractError(
                    "DRAFT_UNSEALED manifest must have sealed_at_utc=None."
                )
            if self.manifest_sha256 != "0" * 64:
                raise DataContractError(
                    f"DRAFT_UNSEALED manifest must have manifest_sha256='{'0'*64}', got '{self.manifest_sha256}'."
                )
            return self

        if self.status == ManifestStatus.SEALED_PRE_REGISTRATION:
            if self.sealed_at_utc is None:
                raise DataContractError(
                    "SEALED_PRE_REGISTRATION manifest must have a valid sealed_at_utc timestamp."
                )
            if self.code_provenance.git_tree_dirty:
                raise DataContractError(
                    "SEALED_PRE_REGISTRATION manifest rejected: git_tree_dirty must be False."
                )

            # Check that all 5 sources are present and verified
            source_ids = {s.source_id for s in self.data_sources}
            expected_sources = {"S-01", "S-02", "S-03", "S-04", "S-05"}
            if source_ids != expected_sources:
                raise DataContractError(
                    f"SEALED_PRE_REGISTRATION manifest missing required sources: {expected_sources - source_ids}"
                )

            for s in self.data_sources:
                if s.authority_status == DataSourceAuthorityStatus.DATA_AUTHORITY_BLOCKED:
                    raise DataContractError(
                        f"Cannot seal manifest: source {s.source_id} remains DATA_AUTHORITY_BLOCKED."
                    )

            for s in self.data_sources:
                if not s.raw_artifact_sha256 or not s.canonical_parquet_sha256 or s.row_count is None or s.row_count <= 0:
                    raise DataContractError(
                        f"Cannot seal manifest: source {s.source_id} missing verified hashes or valid row count."
                    )

            # Verify cryptographic digest bit-for-bit
            expected_digest = self.compute_canonical_digest()
            if self.manifest_sha256 != expected_digest:
                raise DataContractError(
                    f"Macro001ReproducibilityManifest digest mismatch: stored '{self.manifest_sha256}' "
                    f"!= computed '{expected_digest}'."
                )

        return self

    @classmethod
    def create_sealed(
        cls,
        manifest_id: str,
        created_at_utc: str,
        sealed_at_utc: str,
        specification_lineage: Macro001SpecificationLineage,
        code_provenance: Macro001CodeProvenance,
        data_sources: Sequence[Macro001DataSourceRecord],
        protocol_parameters: Macro001ProtocolParameters,
        execution_semantics: Macro001ExecutionSemantics,
    ) -> "Macro001ReproducibilityManifest":
        """Factory method to construct, compute digest, and seal a manifest instance."""
        unhashed_payload = {
            "candidate_id": "CAND-FREE-MACRO-001",
            "code_provenance": code_provenance.model_dump(),
            "created_at_utc": created_at_utc,
            "data_sources": [s.model_dump() for s in data_sources],
            "execution_semantics": execution_semantics.model_dump(),
            "manifest_id": manifest_id,
            "protocol_parameters": protocol_parameters.model_dump(),
            "schema_version": "v1.0.0",
            "sealed_at_utc": sealed_at_utc,
            "specification_lineage": specification_lineage.model_dump(),
            "status": ManifestStatus.SEALED_PRE_REGISTRATION.value,
        }
        computed_sha = compute_payload_sha256(unhashed_payload)

        return cls(
            manifest_id=manifest_id,
            schema_version="v1.0.0",
            candidate_id="CAND-FREE-MACRO-001",
            status=ManifestStatus.SEALED_PRE_REGISTRATION,
            created_at_utc=created_at_utc,
            sealed_at_utc=sealed_at_utc,
            specification_lineage=specification_lineage,
            code_provenance=code_provenance,
            data_sources=tuple(data_sources),
            protocol_parameters=protocol_parameters,
            execution_semantics=execution_semantics,
            manifest_sha256=computed_sha,
        )
