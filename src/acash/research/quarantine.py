"""Phase 8.5 Research Governance: Cross-Hypothesis Data Quarantine & Execution Authorization.

Strictly enforces:
1. Separation of Dataset Planes:
   PHYSICAL_FILE_EXISTS != REPOSITORY_CATALOGED != AUTHORIZED_FOR_HYPOTHESIS != EXPOSED_PRIOR_LIFECYCLE.
2. Cross-Hypothesis Data Quarantine:
   A new hypothesis MUST NOT automatically inherit prior hypothesis datasets.
   Existing HYP_TSMOM_EURUSD_001 M5 validation/OOS partitions remain permanently QUARANTINED
   from future hypothesis research unless an explicit, sealed governance exception is created.
3. Epistemic Scope:
   UNEXPOSED_PRISTINE is strictly protocol-scoped: unexposed within the controlled ACASH
   research protocol. It does not assert or claim universal human ignorance of market data.
4. Fail-Closed Enforcement:
   UNKNOWN, REVOKED, or QUARANTINED states fail closed immediately with DataContractError.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification


# ---------------------------------------------------------------------------
# 1. Enums and Classification Types
# ---------------------------------------------------------------------------


class DatasetExposureState(str, Enum):
    """Protocol-scoped lifecycle and exposure state machine for research data partitions."""

    # Protocol-Scoped Pristine: Data partition has never been accessed by any empirical
    # search or evaluation within the controlled ACASH research protocol.
    UNEXPOSED_PRISTINE = "UNEXPOSED_PRISTINE"

    # Formally authorized and cryptographically bound to an active registered hypothesis.
    AUTHORIZED_FOR_HYPOTHESIS = "AUTHORIZED_FOR_HYPOTHESIS"

    # In-sample training partition authorized for the registered R3 search-trial census
    # sweep of a sealed hypothesis (H4 canonical partition state as written by R2/R3).
    UNLOCKED_FOR_R3_CENSUS = "UNLOCKED_FOR_R3_CENSUS"

    # Evaluated / accessed during empirical research execution within the protocol.
    EXPOSED = "EXPOSED"

    # Locked / quarantined due to prior hypothesis lifecycle exposure, sample awareness,
    # or research falsification. Strictly inaccessible to future hypotheses.
    QUARANTINED = "QUARANTINED"

    # Authorization formally rescinded by governance.
    REVOKED = "REVOKED"

    # Unknown / unclassified authorization state (fails closed unconditionally).
    UNKNOWN = "UNKNOWN"


class DatasetAvailabilityPlane(str, Enum):
    """Authoritative distinction between physical file existence and governance authorization."""

    # File physically exists on local disk storage.
    PHYSICAL_FILE_EXISTS = "PHYSICAL_FILE_EXISTS"

    # Dataset registered in repository catalog / shared infrastructure.
    REPOSITORY_CATALOGED = "REPOSITORY_CATALOGED"

    # Dataset explicitly authorized for execution by a specific hypothesis.
    AUTHORIZED_FOR_SPECIFIC_HYPOTHESIS = "AUTHORIZED_FOR_SPECIFIC_HYPOTHESIS"

    # Dataset exposed during a prior completed or falsified research lifecycle.
    EXPOSED_PRIOR_LIFECYCLE = "EXPOSED_PRIOR_LIFECYCLE"


# ---------------------------------------------------------------------------
# 2. Dataset Authorization Token / Binding DTO
# ---------------------------------------------------------------------------


class DatasetAuthorizationToken(BaseModel):
    """Immutable governance record authorizing a dataset for research execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: str
    canonical_parquet_path: str
    canonical_parquet_sha256: str
    bound_hypothesis_id: str
    bound_hypothesis_sha256: str
    exposure_state: DatasetExposureState = Field(default=DatasetExposureState.AUTHORIZED_FOR_HYPOTHESIS)
    allowed_hypothesis_ids: Tuple[str, ...] = Field(default_factory=tuple)
    quarantine_reason: Optional[str] = None
    governance_exception_id: Optional[str] = None
    authorized_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="before")
    @classmethod
    def validate_authorization_integrity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            state = data.get("exposure_state")
            if isinstance(state, str):
                try:
                    parsed_state = DatasetExposureState(state)
                except ValueError:
                    parsed_state = DatasetExposureState.UNKNOWN
                data["exposure_state"] = parsed_state
                if parsed_state in (DatasetExposureState.UNKNOWN, DatasetExposureState.REVOKED):
                    raise DataContractError(
                        f"DATASET_AUTHORIZATION_INVALID: Cannot create authorization token in '{parsed_state.value}' state."
                    )
        return data


# ---------------------------------------------------------------------------
# 3. Execution Authorization Validator
# ---------------------------------------------------------------------------


class DatasetQuarantineValidator:
    """Master validator enforcing cross-hypothesis quarantine and execution authorization."""

    # Permanent quarantine registry for prior lifecycle holdouts
    PERMANENTLY_QUARANTINED_HOLDOUTS: Mapping[str, Tuple[int, int]] = {
        # HYP_TSMOM_EURUSD_001 M5 Validation + OOS bars (6060 to 9999) are permanently quarantined
        "HYP_TSMOM_EURUSD_001": (6060, 9999),
        # HYP_TSMOM_EURUSD_HTF_002 H4 Validation (3751..4996) + second embargo (4997..5008)
        # + Blind OOS (5009..6230) protected span is permanently quarantined (3751 to 6230).
        # NOT REUSABLE for any future hypothesis (e.g. HYP_003) by default.
        "HYP_TSMOM_EURUSD_HTF_002": (3751, 6230),
    }

    @classmethod
    def validate_dataset_binding_for_execution(
        cls,
        spec: HypothesisSpecification,
        dataset_manifest: Mapping[str, Any],
        requested_partition: str = "train",
        governance_exception_id: Optional[str] = None,
    ) -> None:
        """Validate that a dataset is explicitly authorized for the specified hypothesis.

        Strictly enforces:
        1. Authorization state != UNKNOWN, REVOKED, or QUARANTINED.
        2. Execution authorization binding: dataset must explicitly authorize spec.hypothesis_id.
        3. Hypothesis digest match: prevents parameter mutation under existing hypothesis ID.
        4. Cross-hypothesis quarantine: historical holdouts from prior hypotheses are blocked.
        5. Partition access boundaries.

        Raises:
            DataContractError: If any authorization or quarantine check fails (fail-closed).
        """
        # 1. Inspect Exposure / Quarantine State
        raw_state = dataset_manifest.get("exposure_state")
        if raw_state is None:
            # Check partition-specific exposure state if top-level is absent
            split_policy = dataset_manifest.get("split_policy", {})
            partition_info = split_policy.get(requested_partition.lower(), {})
            raw_state = partition_info.get("exposure_state", DatasetExposureState.AUTHORIZED_FOR_HYPOTHESIS.value)

        try:
            exposure_state = DatasetExposureState(raw_state)
        except (ValueError, TypeError):
            exposure_state = DatasetExposureState.UNKNOWN

        if exposure_state == DatasetExposureState.UNKNOWN:
            raise DataContractError(
                f"DATASET_AUTHORIZATION_UNKNOWN: Dataset '{dataset_manifest.get('dataset_id', 'UNKNOWN')}' "
                f"has UNKNOWN authorization state. Access blocked fail-closed."
            )

        if exposure_state == DatasetExposureState.REVOKED:
            raise DataContractError(
                f"DATASET_AUTHORIZATION_REVOKED: Dataset '{dataset_manifest.get('dataset_id', 'UNKNOWN')}' "
                f"authorization was revoked. Access blocked fail-closed."
            )

        if exposure_state == DatasetExposureState.QUARANTINED and not governance_exception_id:
            reason = dataset_manifest.get("quarantine_reason", "Quarantined by governance rule.")
            raise DataContractError(
                f"DATASET_QUARANTINED_ERROR: Dataset partition '{requested_partition}' for "
                f"hypothesis '{spec.hypothesis_id}' is QUARANTINED. Reason: {reason}."
            )

        # 2. Check Execution Authorization Binding (Amendment 1)
        manifest_hyp_id = dataset_manifest.get("hypothesis_id")
        allowed_hyp_ids = set(dataset_manifest.get("allowed_hypothesis_ids", []))
        if manifest_hyp_id:
            allowed_hyp_ids.add(manifest_hyp_id)

        if spec.hypothesis_id not in allowed_hyp_ids:
            raise DataContractError(
                f"CROSS_HYPOTHESIS_CONTAMINATION_ERROR: Dataset '{dataset_manifest.get('dataset_id', 'UNKNOWN')}' "
                f"is authorized only for {sorted(list(allowed_hyp_ids))}, but execution was requested by '{spec.hypothesis_id}'. "
                f"Implicit cross-hypothesis dataset inheritance is strictly forbidden."
            )

        # 3. Check Hypothesis Digest Binding (Anti-HARKing / Mutation Protection)
        manifest_hyp_digest = dataset_manifest.get("hypothesis_sha256")
        if manifest_hyp_id == spec.hypothesis_id and manifest_hyp_digest:
            calculated_digest = calculate_hypothesis_spec_sha256(spec)
            if calculated_digest != manifest_hyp_digest:
                raise DataContractError(
                    f"HYPOTHESIS_DIGEST_MISMATCH_ERROR: Dataset '{dataset_manifest.get('dataset_id', 'UNKNOWN')}' "
                    f"is bound to hypothesis digest '{manifest_hyp_digest}', but provided hypothesis '{spec.hypothesis_id}' "
                    f"has digest '{calculated_digest}'. Parameter mutation under an existing hypothesis ID is forbidden."
                )

        # 4. Check Prior Lifecycle Quarantined Holdouts
        req_lower = requested_partition.lower()
        if req_lower in ("validation", "oos", "oos_held_out"):
            # If dataset originated from a terminally closed hypothesis, holdout is quarantined
            if manifest_hyp_id in cls.PERMANENTLY_QUARANTINED_HOLDOUTS:
                if spec.hypothesis_id != manifest_hyp_id or not governance_exception_id:
                    raise DataContractError(
                        f"DATASET_QUARANTINED_ERROR: Holdout partition '{requested_partition}' from "
                        f"prior lifecycle '{manifest_hyp_id}' is permanently QUARANTINED against new research. "
                        f"De novo research requires a distinct dataset window."
                    )
