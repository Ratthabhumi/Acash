"""Phase 14 Step R3: HYP_004 / MEC-0014A Primary Econometric Replication.

Executes the single preregistered primary econometric replication of Gao et al. (2018)
baseline predictive relation on SPY (2017-01-01 to 2022-12-31).

MODEL:
    r_{13, t} = alpha + beta * r_{1, t} + epsilon_t
where:
    r_{1, t}  = p1_1000_price / p0_previous_primary_close - 1
    r_{13, t} = p13_current_primary_close / p12_1530_price - 1

BINDING ACCEPTANCE CRITERION:
    beta_hat > 0 AND two-sided Newey-West HAC p-value < 0.05 (L = 7 for T = 1489).

STRICT BOUNDARIES:
- K = 1: exactly one primary model, zero model search, zero alternate predictors.
- No generic evaluate_hypothesis_relationship() calls.
- Zero secondary analyses (no r12, no log returns, no bid/ask, no VIX/volume conditioning).
- Zero 2023+ holdout access (>= 2023-01-01 remains sealed).
- Zero network calls (reads only sealed local R2 endpoint dataset).
- Capital = $0.00, NO_REAL_ORDERS = true, Paper/Live locked.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.features.engine import to_decimal18
from acash.data.qualification.mec_0014_close_contract import (
    IS_END_DATE,
    IS_START_DATE,
    OOS_FORBIDDEN_DATE,
)
from acash.research.evaluation import (
    compute_ols_beta_and_hac,
    determine_hac_bandwidth,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HacBandwidthMethod, HypothesisSpecification

# Pinned Canonical Digests
CANONICAL_STARTING_HEAD_SHA: str = "6d8a1aa3728bc93cee4197f386671a717164443f"
EXPECTED_HYP_004_SHA256: str = "fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d"
EXPECTED_R1_MANIFEST_SHA256: str = "eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b"
EXPECTED_PREREG_SHA256: str = "1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce"
EXPECTED_R2_MANIFEST_SHA256: str = "25b5ae6c4769064459709bb09bbc759e02f7b340c4d4e94b4ff9442e3082ef71"
EXPECTED_R2_PARQUET_SHA256: str = "096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776"

TOTAL_EXPECTED_REGULAR_SESSIONS: int = 1498
EXPECTED_ELIGIBLE_OBSERVATIONS: int = 1489
EXPECTED_EXCLUDED_OBSERVATIONS: int = 9
EXPECTED_HAC_LAG: int = 7


class PrimaryReplicationOutcome(str, Enum):
    """Binding binary scientific outcome label for HYP_004 MEC-0014A primary replication."""
    PRIMARY_REPLICATION_ACCEPTED = "PRIMARY_REPLICATION_ACCEPTED"
    PRIMARY_REPLICATION_NOT_ACCEPTED = "PRIMARY_REPLICATION_NOT_ACCEPTED"


@dataclass(frozen=True)
class PrimaryReturnRow:
    """Deterministic single-session simple return observation."""
    trading_date: str
    calendar_session_ordinal: int
    p0_previous_primary_close: Decimal
    p1_1000_price: Decimal
    p12_1530_price: Decimal
    p13_current_primary_close: Decimal
    r1_simple_return: Decimal
    r13_simple_return: Decimal
    source_r2_dataset_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trading_date": self.trading_date,
            "calendar_session_ordinal": self.calendar_session_ordinal,
            "p0_previous_primary_close": str(self.p0_previous_primary_close),
            "p1_1000_price": str(self.p1_1000_price),
            "p12_1530_price": str(self.p12_1530_price),
            "p13_current_primary_close": str(self.p13_current_primary_close),
            "r1_simple_return": str(self.r1_simple_return),
            "r13_simple_return": str(self.r13_simple_return),
            "source_r2_dataset_sha256": self.source_r2_dataset_sha256,
        }


@dataclass(frozen=True)
class PrimaryRegressionResult:
    """Exact primary econometric replication estimation results."""
    sample_size_t: int
    hac_lag_l: int
    alpha_hat: Decimal
    beta_hat: Decimal
    hac_se_beta: Decimal
    hac_t_stat: Decimal
    two_sided_p_value: Decimal
    r_squared: Decimal
    binding_acceptance_rule: str
    is_accepted: bool
    outcome_label: PrimaryReplicationOutcome
    source_r2_parquet_sha256: str
    derived_r3_parquet_sha256: str
    earliest_trading_date: str
    latest_trading_date: str


# PyArrow Schema for R3 Derived Returns Dataset
R3_PRIMARY_RETURNS_ARROW_SCHEMA = pa.schema([
    ("trading_date", pa.string()),
    ("calendar_session_ordinal", pa.int32()),
    ("p0_previous_primary_close", pa.decimal128(18, 4)),
    ("p1_1000_price", pa.decimal128(18, 4)),
    ("p12_1530_price", pa.decimal128(18, 4)),
    ("p13_current_primary_close", pa.decimal128(18, 4)),
    ("r1_simple_return", pa.decimal128(38, 18)),
    ("r13_simple_return", pa.decimal128(38, 18)),
    ("source_r2_dataset_sha256", pa.string()),
])


def validate_r3_preconditions(repo_root: Optional[Path] = None) -> Dict[str, str]:
    """Verify all upstream governance artifacts, hashes, and census before Step R3 execution."""
    root = repo_root or Path(".")

    # 1. Sealed HYP_004
    hyp_path = root / "docs/phase14/hypotheses/HYP_004.json"
    if not hyp_path.exists():
        raise DataContractError(f"Precondition failed: Sealed HYP_004 not found at {hyp_path}")
    hyp_data = json.loads(hyp_path.read_text(encoding="utf-8"))
    spec = HypothesisSpecification.model_validate(hyp_data)
    computed_hyp_sha = calculate_hypothesis_spec_sha256(spec)
    if computed_hyp_sha != EXPECTED_HYP_004_SHA256:
        raise DataContractError(
            f"Precondition failed: HYP_004 SHA-256 mismatch: {computed_hyp_sha} != {EXPECTED_HYP_004_SHA256}"
        )

    # 2. Frozen Pre-registration
    prereg_path = root / "docs/research/MEC-0014A-statistical-preregistration-draft.md"
    if not prereg_path.exists():
        raise DataContractError(f"Precondition failed: Pre-registration not found at {prereg_path}")
    computed_prereg_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    if computed_prereg_sha != EXPECTED_PREREG_SHA256:
        raise DataContractError(
            f"Precondition failed: Pre-registration SHA-256 mismatch: {computed_prereg_sha} != {EXPECTED_PREREG_SHA256}"
        )

    # 3. Tracked R1 Manifest
    r1_path = root / "docs/phase14/manifests/manifest_r1_HYP_004.json"
    if not r1_path.exists():
        raise DataContractError(f"Precondition failed: R1 Manifest not found at {r1_path}")
    r1_data = json.loads(r1_path.read_text(encoding="utf-8"))
    computed_r1_sha = r1_data.get("manifest_sha256")
    if computed_r1_sha != EXPECTED_R1_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R1 Manifest SHA-256 mismatch: {computed_r1_sha} != {EXPECTED_R1_MANIFEST_SHA256}"
        )

    # 4. Tracked R2 Manifest
    r2_path = root / "docs/phase14/manifests/manifest_r2_HYP_004.json"
    if not r2_path.exists():
        raise DataContractError(f"Precondition failed: R2 Manifest not found at {r2_path}")
    r2_data = json.loads(r2_path.read_text(encoding="utf-8"))
    computed_r2_sha = r2_data.get("manifest_sha256")
    if computed_r2_sha != EXPECTED_R2_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R2 Manifest SHA-256 mismatch: {computed_r2_sha} != {EXPECTED_R2_MANIFEST_SHA256}"
        )

    # 5. Local R2 Parquet Dataset Hash Pin
    r2_parquet_path = root / "data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet"
    if not r2_parquet_path.exists():
        raise DataContractError(f"Precondition failed: R2 Parquet dataset not found at {r2_parquet_path}")
    computed_parquet_sha = hashlib.sha256(r2_parquet_path.read_bytes()).hexdigest()
    if computed_parquet_sha != EXPECTED_R2_PARQUET_SHA256:
        raise DataContractError(
            f"Precondition failed: R2 Parquet dataset SHA-256 mismatch: {computed_parquet_sha} != {EXPECTED_R2_PARQUET_SHA256}"
        )

    return {
        "hyp_004_sha256": computed_hyp_sha,
        "preregistration_sha256": computed_prereg_sha,
        "r1_manifest_sha256": computed_r1_sha,
        "r2_manifest_sha256": computed_r2_sha,
        "r2_parquet_sha256": computed_parquet_sha,
    }


def compute_simple_returns_from_r2(
    r2_parquet_path: Path,
) -> Tuple[List[PrimaryReturnRow], List[str]]:
    """Load R2 Parquet dataset, filter eligible rows, and calculate exact simple returns r1 and r13.

    Invariants enforced:
    - Zero network queries.
    - Zero access to >= 2023-01-01.
    - Exactly 1,498 total rows in R2 dataset.
    - Exactly 1,489 primary_regression_eligible rows.
    - Excluded rows are strictly quarantined and never enter the primary return series.
    - Simple return formulas:
        r1_t  = p1_1000_price / p0_previous_primary_close - 1
        r13_t = p13_current_primary_close / p12_1530_price - 1
    - No log transformation, no clipping, no winsorizing, no demeaning, no dividend adjustment.
    """
    if not r2_parquet_path.is_file():
        raise DataContractError(f"R2 Parquet file not found: {r2_parquet_path}")

    r2_parquet_bytes = r2_parquet_path.read_bytes()
    computed_r2_sha = hashlib.sha256(r2_parquet_bytes).hexdigest()
    if computed_r2_sha != EXPECTED_R2_PARQUET_SHA256:
        raise DataContractError(
            f"R2 Parquet dataset hash mismatch: {computed_r2_sha} != {EXPECTED_R2_PARQUET_SHA256}"
        )

    table = pq.read_table(r2_parquet_path)
    if table.num_rows != TOTAL_EXPECTED_REGULAR_SESSIONS:
        raise DataContractError(
            f"R2 dataset total rows violation: {table.num_rows} != {TOTAL_EXPECTED_REGULAR_SESSIONS}"
        )

    pydict = table.to_pydict()
    trading_dates = pydict["trading_date"]
    ordinals = pydict["calendar_session_ordinal"]
    p0_prices = pydict["p0_previous_primary_close"]
    p1_prices = pydict["p1_1000_price"]
    p12_prices = pydict["p12_1530_price"]
    p13_prices = pydict["p13_current_primary_close"]
    eligibilities = pydict["primary_regression_eligible"]
    exclusion_codes_list = pydict["exclusion_reason_codes"]

    return_rows: List[PrimaryReturnRow] = []
    excluded_dates: List[str] = []

    for i in range(len(trading_dates)):
        d_str = str(trading_dates[i])
        s_date = date.fromisoformat(d_str)

        # Fail-closed temporal boundary check
        if s_date >= OOS_FORBIDDEN_DATE:
            raise DataContractError(f"CRITICAL OOS VIOLATION: observation date {d_str} >= {OOS_FORBIDDEN_DATE}")
        if s_date < IS_START_DATE or s_date > IS_END_DATE:
            raise DataContractError(f"CRITICAL IN-SAMPLE VIOLATION: observation date {d_str} out of bounds")

        is_eligible = bool(eligibilities[i])

        if not is_eligible:
            excluded_dates.append(d_str)
            continue

        # For eligible rows, all four prices must be strictly positive Decimals
        p0_raw = p0_prices[i]
        p1_raw = p1_prices[i]
        p12_raw = p12_prices[i]
        p13_raw = p13_prices[i]

        if p0_raw is None or p1_raw is None or p12_raw is None or p13_raw is None:
            raise DataContractError(f"Eligible row {d_str} contains null price: p0={p0_raw}, p1={p1_raw}, p12={p12_raw}, p13={p13_raw}")

        p0 = Decimal(str(p0_raw))
        p1 = Decimal(str(p1_raw))
        p12 = Decimal(str(p12_raw))
        p13 = Decimal(str(p13_raw))

        if p0 <= 0 or p1 <= 0 or p12 <= 0 or p13 <= 0:
            raise DataContractError(f"Eligible row {d_str} contains non-positive price: p0={p0}, p1={p1}, p12={p12}, p13={p13}")

        # Exact Simple Return Formulas with canonical 18-decimal quantization
        r1_raw = (p1 / p0) - Decimal("1")
        r13_raw = (p13 / p12) - Decimal("1")
        r1 = to_decimal18(r1_raw)
        r13 = to_decimal18(r13_raw)
        if r1 is None or r13 is None:
            raise DataContractError(f"Failed to quantize simple returns for session {d_str}")

        return_rows.append(
            PrimaryReturnRow(
                trading_date=d_str,
                calendar_session_ordinal=int(ordinals[i]),
                p0_previous_primary_close=p0,
                p1_1000_price=p1,
                p12_1530_price=p12,
                p13_current_primary_close=p13,
                r1_simple_return=r1,
                r13_simple_return=r13,
                source_r2_dataset_sha256=computed_r2_sha,
            )
        )

    # Sort deterministically by trading_date ascending
    return_rows.sort(key=lambda r: r.trading_date)

    if len(return_rows) != EXPECTED_ELIGIBLE_OBSERVATIONS:
        raise DataContractError(
            f"Eligible return count mismatch: {len(return_rows)} != {EXPECTED_ELIGIBLE_OBSERVATIONS}"
        )

    if len(excluded_dates) != EXPECTED_EXCLUDED_OBSERVATIONS:
        raise DataContractError(
            f"Excluded count mismatch: {len(excluded_dates)} != {EXPECTED_EXCLUDED_OBSERVATIONS}"
        )

    return return_rows, excluded_dates


def build_canonical_primary_returns_parquet(
    rows: Sequence[PrimaryReturnRow],
    output_path: Path,
) -> Path:
    """Build and write the deterministic derived primary returns Parquet dataset."""
    if len(rows) != EXPECTED_ELIGIBLE_OBSERVATIONS:
        raise DataContractError(
            f"Derived dataset cardinality violation: expected {EXPECTED_ELIGIBLE_OBSERVATIONS} rows, got {len(rows)}"
        )

    pydict: Dict[str, List[Any]] = {field.name: [] for field in R3_PRIMARY_RETURNS_ARROW_SCHEMA}

    for r in rows:
        pydict["trading_date"].append(r.trading_date)
        pydict["calendar_session_ordinal"].append(r.calendar_session_ordinal)
        pydict["p0_previous_primary_close"].append(r.p0_previous_primary_close)
        pydict["p1_1000_price"].append(r.p1_1000_price)
        pydict["p12_1530_price"].append(r.p12_1530_price)
        pydict["p13_current_primary_close"].append(r.p13_current_primary_close)
        pydict["r1_simple_return"].append(r.r1_simple_return)
        pydict["r13_simple_return"].append(r.r13_simple_return)
        pydict["source_r2_dataset_sha256"].append(r.source_r2_dataset_sha256)

    table = pa.Table.from_pydict(pydict, schema=R3_PRIMARY_RETURNS_ARROW_SCHEMA)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path, compression="snappy")
    return output_path


def execute_primary_replication_regression(
    return_rows: Sequence[PrimaryReturnRow],
    r2_parquet_sha256: str,
    r3_parquet_sha256: str,
) -> PrimaryRegressionResult:
    """Execute the single authorized OLS regression with Newey-West HAC inference.

    Specification:
        Model: r_{13, t} = alpha + beta * r_{1, t} + eps_t
        Sample Size: T = 1489
        HAC Kernel: Bartlett
        HAC Lag: L = floor(4 * (T / 100)^(2/9)) = 7
        alpha_hat: mean(r13) - beta_hat * mean(r1)
        R^2: 1 - SSE / SST
        Binding Acceptance Rule: beta_hat > 0 AND two-sided Newey-West HAC p-value < 0.05
    """
    n = len(return_rows)
    if n != EXPECTED_ELIGIBLE_OBSERVATIONS:
        raise DataContractError(f"Regression sample size violation: {n} != {EXPECTED_ELIGIBLE_OBSERVATIONS}")

    # 1. Determine HAC Bandwidth using canonical formula
    lag_l = determine_hac_bandwidth(
        method=HacBandwidthMethod.NEWEY_WEST_PLUGIN,
        sample_size=n,
        horizon=1,
    )
    if lag_l != EXPECTED_HAC_LAG:
        raise DataContractError(f"HAC lag mismatch: computed {lag_l} != expected {EXPECTED_HAC_LAG}")

    r1_dec = [r.r1_simple_return for r in return_rows]
    r13_dec = [r.r13_simple_return for r in return_rows]

    # 2. Compute OLS slope beta, HAC SE, HAC t-stat, and asymptotic two-sided p-value
    beta_hat_dec, se_beta_dec, t_stat_dec, p_val_dec = compute_ols_beta_and_hac(
        x=r1_dec,
        y=r13_dec,
        lag_bandwidth=lag_l,
    )

    # 3. Compute OLS intercept alpha deterministically on the same float64 basis
    r1_arr = np.array([float(v) for v in r1_dec], dtype=np.float64)
    r13_arr = np.array([float(v) for v in r13_dec], dtype=np.float64)

    mean_r1 = float(np.mean(r1_arr))
    mean_r13 = float(np.mean(r13_arr))
    beta_hat_float = float(beta_hat_dec)

    alpha_hat_float = mean_r13 - beta_hat_float * mean_r1
    alpha_hat_dec = to_decimal18(Decimal(f"{alpha_hat_float:.18f}"))
    if alpha_hat_dec is None:
        alpha_hat_dec = Decimal("0")

    # 4. Compute ordinary unadjusted in-sample R^2
    y_pred = alpha_hat_float + beta_hat_float * r1_arr
    residuals = r13_arr - y_pred
    sse = float(np.sum(residuals ** 2))
    sst = float(np.sum((r13_arr - mean_r13) ** 2))

    if sst <= 0.0:
        raise DataContractError(f"SST non-positive in R^2 calculation: SST={sst}")

    r2_float = 1.0 - (sse / sst)
    r2_dec = to_decimal18(Decimal(f"{r2_float:.18f}"))
    if r2_dec is None:
        r2_dec = Decimal("0")

    # 5. Evaluate binding acceptance rule
    is_accepted = (beta_hat_dec > Decimal("0")) and (p_val_dec < Decimal("0.05"))
    outcome = (
        PrimaryReplicationOutcome.PRIMARY_REPLICATION_ACCEPTED
        if is_accepted
        else PrimaryReplicationOutcome.PRIMARY_REPLICATION_NOT_ACCEPTED
    )

    binding_rule_str = "beta_hat > 0 AND two-sided Newey-West HAC p-value < 0.05 (L = 7, T = 1489)"

    return PrimaryRegressionResult(
        sample_size_t=n,
        hac_lag_l=lag_l,
        alpha_hat=alpha_hat_dec,
        beta_hat=beta_hat_dec,
        hac_se_beta=se_beta_dec,
        hac_t_stat=t_stat_dec,
        two_sided_p_value=p_val_dec,
        r_squared=r2_dec,
        binding_acceptance_rule=binding_rule_str,
        is_accepted=is_accepted,
        outcome_label=outcome,
        source_r2_parquet_sha256=r2_parquet_sha256,
        derived_r3_parquet_sha256=r3_parquet_sha256,
        earliest_trading_date=return_rows[0].trading_date,
        latest_trading_date=return_rows[-1].trading_date,
    )


def build_r3_manifest(
    result: PrimaryRegressionResult,
    source_git_sha: str,
) -> Dict[str, Any]:
    """Assemble tracked JSON manifest for Phase 14 Step R3 primary econometric replication."""
    payload: Dict[str, Any] = {
        "manifest_type": "PRIMARY_ECONOMETRIC_REPLICATION_MANIFEST",
        "hypothesis_id": "HYP_004",
        "hypothesis_ordinal": 4,
        "mechanism_id": "MEC-0014A",
        "hypothesis_sha256": EXPECTED_HYP_004_SHA256,
        "r1_manifest_sha256": EXPECTED_R1_MANIFEST_SHA256,
        "r2_manifest_sha256": EXPECTED_R2_MANIFEST_SHA256,
        "preregistration_sha256": EXPECTED_PREREG_SHA256,
        "source_git_sha": source_git_sha,
        "dataset_lineage": {
            "source_r2_parquet_sha256": result.source_r2_parquet_sha256,
            "derived_r3_parquet_sha256": result.derived_r3_parquet_sha256,
            "sample_size_t": result.sample_size_t,
            "date_range": {
                "start": result.earliest_trading_date,
                "end": result.latest_trading_date,
            },
        },
        "model_specification": {
            "model_type": "OLS_UNIVARIATE_WITH_INTERCEPT",
            "dependent_variable": "r13_simple_return (15:30 to 16:00 close)",
            "independent_variable": "r1_simple_return (previous close to 10:00)",
            "hac_family": "NEWEY_WEST_BARTLETT_KERNEL",
            "hac_lag_l": result.hac_lag_l,
            "hac_bandwidth_rule": "floor(4 * (T / 100)^(2/9))",
        },
        "econometric_estimates": {
            "alpha_hat": str(result.alpha_hat),
            "beta_hat": str(result.beta_hat),
            "hac_se_beta": str(result.hac_se_beta),
            "hac_t_stat": str(result.hac_t_stat),
            "two_sided_p_value": str(result.two_sided_p_value),
            "r_squared": str(result.r_squared),
        },
        "primary_acceptance_evaluation": {
            "criterion": result.binding_acceptance_rule,
            "direction_pass": bool(result.beta_hat > Decimal("0")),
            "significance_pass": bool(result.two_sided_p_value < Decimal("0.05")),
            "is_accepted": result.is_accepted,
            "outcome_label": result.outcome_label.value,
        },
        "execution_governance_invariants": {
            "single_model_k_equals_1": True,
            "secondary_analyses_executed": False,
            "recursive_internal_oos_executed": False,
            "oos_2023_2026_accessed": False,
            "trading_authorized": False,
            "capital_authority_usd": "0.00",
        },
        "status": "STEP_R3_PRIMARY_REPLICATION_SEALED",
        "next_required_action": "HUMAN_AUDIT_OF_PRIMARY_REPLICATION_RESULT",
    }

    manifest_json = CanonicalConfigSerializer.to_canonical_json(payload)
    manifest_bytes = manifest_json.encode("utf-8")
    payload["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    return payload
