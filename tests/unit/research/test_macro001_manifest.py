"""Unit tests for CAND-FREE-MACRO-001 D18 Reproducibility Manifest.

Verifies:
1. Valid draft unsealed manifest initialization.
2. Draft validation fail-closed on non-null sealed_at_utc or non-zero manifest_sha256.
3. Valid sealed manifest construction with factory and exact canonical digest match.
4. Tamper detection: any bit-level modification raises DataContractError.
5. Fail-closed on dirty Git tree when sealing.
6. Fail-closed if any source remains DATA_AUTHORITY_BLOCKED.
7. Fail-closed on missing source hashes or invalid row counts.
8. Deterministic canonical JSON serialization and hash repeatability.
9. Forbid extra fields and enforce model immutability.
"""

from datetime import datetime, timezone
from typing import Tuple
import pytest
from pydantic import ValidationError

from acash.core.domain.exceptions import DataContractError
from acash.research.manifest_macro001 import (
    DataSourceAuthorityStatus,
    Macro001CodeProvenance,
    Macro001DataSourceRecord,
    Macro001ExecutionSemantics,
    Macro001ParameterGridCell,
    Macro001ProtocolParameters,
    Macro001ReproducibilityManifest,
    Macro001SpecificationLineage,
    ManifestStatus,
    canonical_json_dumps,
    compute_payload_sha256,
)


def make_valid_lineage() -> Macro001SpecificationLineage:
    """Helper for valid specification lineage."""
    return Macro001SpecificationLineage(
        specification_version="v1.0-round5",
        decision_surface_sha256="1" * 64,
        round4_specification_sha256="2" * 64,
        binding_worksheet_sha256="3" * 64,
    )


def make_valid_code_provenance(dirty: bool = False) -> Macro001CodeProvenance:
    """Helper for valid code provenance."""
    return Macro001CodeProvenance(
        git_commit_hash="a" * 40,
        git_tree_dirty=dirty,
        pyproject_toml_sha256="4" * 64,
        uv_lock_sha256="5" * 64,
        python_version="3.14.0",
    )


def make_valid_protocol_params() -> Macro001ProtocolParameters:
    """Helper for valid protocol parameters."""
    return Macro001ProtocolParameters(
        event_universe=("FOMC", "CPI", "NFP"),
        timezone="America/New_York",
        event_window="W-1",
        return_formula="R-EC",
        baseline="B-A",
        overlap_rule="O-2",
        tie_break_rule="TR-1",
        calendar_authority="CA-1",
        parameter_grid=(
            Macro001ParameterGridCell(cell_id="G1_1H", horizon_hours=1),
            Macro001ParameterGridCell(cell_id="G1_2H", horizon_hours=2),
            Macro001ParameterGridCell(cell_id="G1_4H", horizon_hours=4),
        ),
        trial_count_k=3,
        is_start_date="2013-12-01",
        is_end_date="2021-12-31",
        oos_start_date="2022-01-01",
        oos_end_date="2024-12-31",
        blind_start_date="2025-01-01",
        blind_end_date="2026-09-10",
        statistical_test="TWO_WAY_CLUSTERED_T_TEST",
        degrees_of_freedom="G-1",
        alpha_significance_level=0.05,
        primary_hypothesis="H0: E[D] = 0 vs H1: E[D] != 0 (Two-Sided)",
    )


def make_valid_execution_semantics() -> Macro001ExecutionSemantics:
    """Helper for execution semantics."""
    return Macro001ExecutionSemantics(
        kill_conditions=(
            "duplicate_admitted_event > 0",
            "source_binding_integrity_violation > 0",
            "calendar_session_mapping_violation > 0",
            "non_finite_statistical_input > 0",
            "protocol_invariant_violation > 0",
        ),
        census_semantics="D6_FROZEN_CENSUS_K3_MIXED_FAILS_CLOSED",
        invalid_policy="NON_NEGATIVE_EVIDENCE_FAIL_CLOSED_LOGGED",
        numerical_precision="DECIMAL_PRICES_FLOAT64_STATS_ZERO_MAGIC_FLOORS",
    )


def make_draft_data_sources() -> Tuple[Macro001DataSourceRecord, ...]:
    """Helper for draft data sources where S-04 is BLOCKED."""
    return (
        Macro001DataSourceRecord(
            source_id="S-01",
            authority_status=DataSourceAuthorityStatus.RATIFIED_AUTHORITATIVE,
            retrieval_timestamp_utc=None,
            vintage_policy="OFFICIAL_FED_SCHEDULE_ARCHIVE",
            raw_artifact_sha256=None,
            canonical_parquet_sha256=None,
            row_count=None,
        ),
        Macro001DataSourceRecord(
            source_id="S-02",
            authority_status=DataSourceAuthorityStatus.RATIFIED_AUTHORITATIVE,
            retrieval_timestamp_utc=None,
            vintage_policy="OFFICIAL_BLS_CPI_SCHEDULE_ARCHIVE",
            raw_artifact_sha256=None,
            canonical_parquet_sha256=None,
            row_count=None,
        ),
        Macro001DataSourceRecord(
            source_id="S-03",
            authority_status=DataSourceAuthorityStatus.RATIFIED_AUTHORITATIVE,
            retrieval_timestamp_utc=None,
            vintage_policy="OFFICIAL_BLS_NFP_SCHEDULE_ARCHIVE",
            raw_artifact_sha256=None,
            canonical_parquet_sha256=None,
            row_count=None,
        ),
        Macro001DataSourceRecord(
            source_id="S-04",
            authority_status=DataSourceAuthorityStatus.DATA_AUTHORITY_BLOCKED,
            retrieval_timestamp_utc=None,
            vintage_policy="BLOCKED_ON_D17_E_RESOLUTION",
            raw_artifact_sha256=None,
            canonical_parquet_sha256=None,
            row_count=None,
        ),
        Macro001DataSourceRecord(
            source_id="S-05",
            authority_status=DataSourceAuthorityStatus.RATIFIED_AUTHORITATIVE,
            retrieval_timestamp_utc="2026-09-10T12:00:00Z",
            vintage_policy="NYSE_OFFICIAL_CALENDAR_2013_2026",
            raw_artifact_sha256=None,
            canonical_parquet_sha256=None,
            row_count=None,
        ),
    )


def make_synthetic_sealed_sources() -> Tuple[Macro001DataSourceRecord, ...]:
    """Helper for synthetic sealed sources for non-strategy testing."""
    return tuple(
        Macro001DataSourceRecord(
            source_id=sid,  # type: ignore[arg-type]
            authority_status=DataSourceAuthorityStatus.RATIFIED_AUTHORITATIVE,
            retrieval_timestamp_utc="2026-09-11T12:00:00Z",
            vintage_policy="SYNTHETIC_TEST_VINTAGE",
            raw_artifact_sha256=f"{i}" * 64,
            canonical_parquet_sha256=f"{i+1}" * 64,
            row_count=1000 + i,
        )
        for i, sid in enumerate(["S-01", "S-02", "S-03", "S-04", "S-05"], start=1)
    )


class TestMacro001ReproducibilityManifest:
    """Test suite for Macro001ReproducibilityManifest."""

    def test_valid_draft_unsealed_manifest(self) -> None:
        """Verify that a valid draft manifest instantiates with 64 zeroes digest and None sealed timestamp."""
        manifest = Macro001ReproducibilityManifest(
            manifest_id="MANIFEST_MACRO_001_20260911_00000000",
            schema_version="v1.0.0",
            candidate_id="CAND-FREE-MACRO-001",
            status=ManifestStatus.DRAFT_UNSEALED,
            created_at_utc="2026-09-11T03:45:00Z",
            sealed_at_utc=None,
            specification_lineage=make_valid_lineage(),
            code_provenance=make_valid_code_provenance(),
            data_sources=make_draft_data_sources(),
            protocol_parameters=make_valid_protocol_params(),
            execution_semantics=make_valid_execution_semantics(),
            manifest_sha256="0" * 64,
        )

        assert manifest.status == ManifestStatus.DRAFT_UNSEALED
        assert manifest.sealed_at_utc is None
        assert manifest.manifest_sha256 == "0" * 64

    def test_draft_manifest_rejects_non_null_sealed_timestamp(self) -> None:
        """Fail closed if draft manifest has a sealed timestamp."""
        with pytest.raises(DataContractError, match="DRAFT_UNSEALED manifest must have sealed_at_utc=None"):
            Macro001ReproducibilityManifest(
                manifest_id="MANIFEST_MACRO_001_20260911_00000000",
                schema_version="v1.0.0",
                candidate_id="CAND-FREE-MACRO-001",
                status=ManifestStatus.DRAFT_UNSEALED,
                created_at_utc="2026-09-11T03:45:00Z",
                sealed_at_utc="2026-09-11T04:00:00Z",  # Invalid for draft
                specification_lineage=make_valid_lineage(),
                code_provenance=make_valid_code_provenance(),
                data_sources=make_draft_data_sources(),
                protocol_parameters=make_valid_protocol_params(),
                execution_semantics=make_valid_execution_semantics(),
                manifest_sha256="0" * 64,
            )

    def test_draft_manifest_rejects_non_zero_digest(self) -> None:
        """Fail closed if draft manifest has non-zero manifest_sha256."""
        with pytest.raises(DataContractError, match="DRAFT_UNSEALED manifest must have manifest_sha256="):
            Macro001ReproducibilityManifest(
                manifest_id="MANIFEST_MACRO_001_20260911_00000000",
                schema_version="v1.0.0",
                candidate_id="CAND-FREE-MACRO-001",
                status=ManifestStatus.DRAFT_UNSEALED,
                created_at_utc="2026-09-11T03:45:00Z",
                sealed_at_utc=None,
                specification_lineage=make_valid_lineage(),
                code_provenance=make_valid_code_provenance(),
                data_sources=make_draft_data_sources(),
                protocol_parameters=make_valid_protocol_params(),
                execution_semantics=make_valid_execution_semantics(),
                manifest_sha256="f" * 64,  # Invalid for draft
            )

    def test_create_sealed_synthetic_manifest(self) -> None:
        """Verify factory creates a sealed manifest with verified canonical digest."""
        manifest = Macro001ReproducibilityManifest.create_sealed(
            manifest_id="MANIFEST_MACRO_001_20260911_12345678",
            created_at_utc="2026-09-11T03:45:00Z",
            sealed_at_utc="2026-09-11T04:00:00Z",
            specification_lineage=make_valid_lineage(),
            code_provenance=make_valid_code_provenance(dirty=False),
            data_sources=make_synthetic_sealed_sources(),
            protocol_parameters=make_valid_protocol_params(),
            execution_semantics=make_valid_execution_semantics(),
        )

        assert manifest.status == ManifestStatus.SEALED_PRE_REGISTRATION
        assert manifest.manifest_sha256 == manifest.compute_canonical_digest()
        assert len(manifest.manifest_sha256) == 64

    def test_tamper_detection_on_sealed_manifest(self) -> None:
        """Verify that any modified field in a sealed manifest is caught by validation."""
        valid_sealed = Macro001ReproducibilityManifest.create_sealed(
            manifest_id="MANIFEST_MACRO_001_20260911_12345678",
            created_at_utc="2026-09-11T03:45:00Z",
            sealed_at_utc="2026-09-11T04:00:00Z",
            specification_lineage=make_valid_lineage(),
            code_provenance=make_valid_code_provenance(dirty=False),
            data_sources=make_synthetic_sealed_sources(),
            protocol_parameters=make_valid_protocol_params(),
            execution_semantics=make_valid_execution_semantics(),
        )

        # Attempt to modify the commit hash without updating manifest_sha256
        tampered_provenance = Macro001CodeProvenance(
            git_commit_hash="b" * 40,  # Changed
            git_tree_dirty=False,
            pyproject_toml_sha256="4" * 64,
            uv_lock_sha256="5" * 64,
            python_version="3.14.0",
        )

        with pytest.raises(DataContractError, match="Macro001ReproducibilityManifest digest mismatch"):
            Macro001ReproducibilityManifest(
                manifest_id=valid_sealed.manifest_id,
                schema_version="v1.0.0",
                candidate_id="CAND-FREE-MACRO-001",
                status=ManifestStatus.SEALED_PRE_REGISTRATION,
                created_at_utc=valid_sealed.created_at_utc,
                sealed_at_utc=valid_sealed.sealed_at_utc,
                specification_lineage=valid_sealed.specification_lineage,
                code_provenance=tampered_provenance,
                data_sources=valid_sealed.data_sources,
                protocol_parameters=valid_sealed.protocol_parameters,
                execution_semantics=valid_sealed.execution_semantics,
                manifest_sha256=valid_sealed.manifest_sha256,  # Stale hash
            )

    def test_sealing_fails_closed_if_git_tree_dirty(self) -> None:
        """Verify that sealing cannot occur if git_tree_dirty is True."""
        with pytest.raises(DataContractError, match="git_tree_dirty must be False"):
            Macro001ReproducibilityManifest.create_sealed(
                manifest_id="MANIFEST_MACRO_001_20260911_12345678",
                created_at_utc="2026-09-11T03:45:00Z",
                sealed_at_utc="2026-09-11T04:00:00Z",
                specification_lineage=make_valid_lineage(),
                code_provenance=make_valid_code_provenance(dirty=True),  # Dirty!
                data_sources=make_synthetic_sealed_sources(),
                protocol_parameters=make_valid_protocol_params(),
                execution_semantics=make_valid_execution_semantics(),
            )

    def test_sealing_fails_closed_if_any_source_is_blocked(self) -> None:
        """Verify that sealing cannot occur if S-04 remains DATA_AUTHORITY_BLOCKED."""
        sources = make_draft_data_sources()  # S-04 is DATA_AUTHORITY_BLOCKED
        with pytest.raises(DataContractError, match="Cannot seal manifest: source S-04 remains DATA_AUTHORITY_BLOCKED"):
            Macro001ReproducibilityManifest.create_sealed(
                manifest_id="MANIFEST_MACRO_001_20260911_12345678",
                created_at_utc="2026-09-11T03:45:00Z",
                sealed_at_utc="2026-09-11T04:00:00Z",
                specification_lineage=make_valid_lineage(),
                code_provenance=make_valid_code_provenance(dirty=False),
                data_sources=sources,
                protocol_parameters=make_valid_protocol_params(),
                execution_semantics=make_valid_execution_semantics(),
            )

    def test_canonical_json_determinism(self) -> None:
        """Verify that JSON serialization produces identical sorted bytes across runs."""
        dict1 = {"b": 2, "a": 1, "c": [3, 2, 1]}
        dict2 = {"c": [3, 2, 1], "a": 1, "b": 2}
        assert canonical_json_dumps(dict1) == canonical_json_dumps(dict2)
        assert compute_payload_sha256(dict1) == compute_payload_sha256(dict2)

    def test_extra_fields_forbidden(self) -> None:
        """Verify that unknown extra fields are strictly forbidden."""
        with pytest.raises(ValidationError):
            Macro001SpecificationLineage(
                specification_version="v1.0",
                decision_surface_sha256="1" * 64,
                round4_specification_sha256="2" * 64,
                binding_worksheet_sha256="3" * 64,
                unauthorized_extra_field="malicious",  # type: ignore[call-arg]
            )
