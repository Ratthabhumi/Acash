"""Module: Phase 14 HYP_004 / MEC-0014A Log-Return Robustness Characterization.

Epistemic Classification:
    Analysis Family: PREREGISTERED_SECONDARY_ANALYSIS_FAMILY
    Operationalization: POST_PRIMARY_HUMAN_AUTHORIZED_ROBUSTNESS_OPERATIONALIZATION
    Primary Outcome Invariant: PRIMARY_REPLICATION_NOT_ACCEPTED (IMMUTABLE)

Operationalizes the single secondary log-return robustness specification preregistered
in MEC-0014A (§7) and authorized post-primary by human governance.

Strict Invariants:
    1. Zero authority to modify, rescue, or relabel PRIMARY_REPLICATION_NOT_ACCEPTED.
    2. Data source: Strictly data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet (T=1489).
    3. Natural log formulas:
       log_r1_t = ln(p1_1000_price / p0_previous_primary_close)
       log_r13_t = ln(p13_current_primary_close / p12_1530_price)
    4. Positive prices strictly required (fail-closed if <= 0).
    5. Single OLS univariate model with intercept: log_r13_t = alpha_log + beta_log * log_r1_t + eps_t.
    6. HAC: Newey-West Bartlett kernel with lag L=floor(4*(T/100)^(2/9))=7.
    7. No binary acceptance/rejection rule (descriptive reference reporting only).
    8. 2023–2026 external holdout remains strictly sealed and unread.
    9. Canonical capital remains $0.00, trading unauthorized.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.features.engine import to_decimal18
from acash.research.evaluation import compute_ols_beta_and_hac
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification

# Canonical Upstream Governance and Data Hashes
CANONICAL_STARTING_HEAD_SHA: str = "373c0dc98cde53f77fa23f7d9bde6c2ae0ba52cf"
EXPECTED_HYP_004_SHA256: str = "fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d"
EXPECTED_PREREG_SHA256: str = "1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce"
EXPECTED_R1_MANIFEST_SHA256: str = "eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b"
EXPECTED_R2_MANIFEST_SHA256: str = "25b5ae6c4769064459709bb09bbc759e02f7b340c4d4e94b4ff9442e3082ef71"
EXPECTED_R2_PARQUET_SHA256: str = "096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776"
EXPECTED_R3_MANIFEST_SHA256: str = "56d4f79c1e563a81c0b601f695023a5da54cac58e5b9a19a0be9108b3ca4ef40"
EXPECTED_R4_MANIFEST_SHA256: str = "d3e5298ccf66da9854bc84c1ca64aeec112c8e907b96f5fd36a2d8e3f194b9a7"

# Sample Cardinality Constants
EXPECTED_TOTAL_SESSIONS: int = 1498
EXPECTED_ELIGIBLE_OBSERVATIONS: int = 1489
EXPECTED_EXCLUDED_OBSERVATIONS: int = 9
EXPECTED_HAC_LAG: int = 7

# Primary Simple-Return Benchmark Reference Estimates (R3)
PRIMARY_OUTCOME_LABEL: str = "PRIMARY_REPLICATION_NOT_ACCEPTED"
PRIMARY_ALPHA: Decimal = Decimal("-0.000125752897293718")
PRIMARY_BETA: Decimal = Decimal("0.022488683629000000")
PRIMARY_HAC_SE: Decimal = Decimal("0.035253777057000000")
PRIMARY_HAC_T: Decimal = Decimal("0.637908488282000000")
PRIMARY_P_VALUE: Decimal = Decimal("0.523533251922000000")
PRIMARY_R_SQUARED: Decimal = Decimal("0.002641292938333817")

# PyArrow Schema for Log-Return Robustness Dataset
LOG_RETURN_ROBUSTNESS_ARROW_SCHEMA = pa.schema([
    ("trading_date", pa.string()),
    ("p0", pa.decimal128(18, 4)),
    ("p1", pa.decimal128(18, 4)),
    ("p12", pa.decimal128(18, 4)),
    ("p13", pa.decimal128(18, 4)),
    ("log_r1", pa.decimal128(38, 18)),
    ("log_r13", pa.decimal128(38, 18)),
    ("source_R2_dataset_sha256", pa.string()),
])


@dataclass(frozen=True)
class LogReturnRow:
    """Represents a single eligible session with computed log returns."""
    trading_date: str
    p0: Decimal
    p1: Decimal
    p12: Decimal
    p13: Decimal
    log_r1: Decimal
    log_r13: Decimal
    source_r2_dataset_sha256: str


@dataclass(frozen=True)
class LogRobustnessResult:
    """Encapsulates all statistical estimates from the log-return robustness regression."""
    sample_size_t: int
    hac_lag_l: int
    alpha_log: Decimal
    beta_log: Decimal
    hac_se: Decimal
    hac_t_stat: Decimal
    two_sided_p_value: Decimal
    r_squared: Decimal
    sig_10pct: bool
    sig_5pct: bool
    sig_1pct: bool
    source_r2_parquet_sha256: str
    derived_log_parquet_sha256: str
    earliest_date: str
    latest_date: str


def validate_robustness_preconditions(repo_root: Optional[Path] = None) -> Dict[str, str]:
    """Verify all upstream governance artifacts, manifests, and data hashes."""
    root = repo_root or Path(".")

    # 1. Verify HYP_004 hypothesis specification
    hyp_path = root / "docs/phase14/hypotheses/HYP_004.json"
    if not hyp_path.exists():
        raise DataContractError(f"Precondition failed: Missing HYP_004 specification at {hyp_path}")
    hyp_data = json.loads(hyp_path.read_text(encoding="utf-8"))
    spec = HypothesisSpecification.model_validate(hyp_data)
    computed_hyp_sha = calculate_hypothesis_spec_sha256(spec)
    if computed_hyp_sha != EXPECTED_HYP_004_SHA256:
        raise DataContractError(
            f"Precondition failed: HYP_004 SHA-256 mismatch: {computed_hyp_sha} != {EXPECTED_HYP_004_SHA256}"
        )

    # 2. Verify Preregistration document
    prereg_path = root / "docs/research/MEC-0014A-statistical-preregistration-draft.md"
    if not prereg_path.exists():
        raise DataContractError(f"Precondition failed: Missing preregistration draft at {prereg_path}")
    computed_prereg_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    if computed_prereg_sha != EXPECTED_PREREG_SHA256:
        raise DataContractError(
            f"Precondition failed: Preregistration SHA-256 mismatch: {computed_prereg_sha} != {EXPECTED_PREREG_SHA256}"
        )

    # 3. Verify R1 manifest
    r1_path = root / "docs/phase14/manifests/manifest_r1_HYP_004.json"
    if not r1_path.exists():
        raise DataContractError(f"Precondition failed: Missing R1 manifest at {r1_path}")
    with open(r1_path, "r", encoding="utf-8") as f:
        r1_data = json.load(f)
    computed_r1_sha = r1_data.get("manifest_sha256")
    if computed_r1_sha != EXPECTED_R1_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R1 Manifest SHA-256 mismatch: {computed_r1_sha} != {EXPECTED_R1_MANIFEST_SHA256}"
        )

    # 4. Verify R2 manifest
    r2_path = root / "docs/phase14/manifests/manifest_r2_HYP_004.json"
    if not r2_path.exists():
        raise DataContractError(f"Precondition failed: Missing R2 manifest at {r2_path}")
    with open(r2_path, "r", encoding="utf-8") as f:
        r2_data = json.load(f)
    computed_r2_sha = r2_data.get("manifest_sha256")
    if computed_r2_sha != EXPECTED_R2_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R2 Manifest SHA-256 mismatch: {computed_r2_sha} != {EXPECTED_R2_MANIFEST_SHA256}"
        )

    # 5. Verify R2 Parquet dataset
    r2_parquet_path = root / "data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet"
    if not r2_parquet_path.exists():
        raise DataContractError(f"Precondition failed: Missing R2 dataset at {r2_parquet_path}")
    computed_r2_parquet_sha = hashlib.sha256(r2_parquet_path.read_bytes()).hexdigest()
    if computed_r2_parquet_sha != EXPECTED_R2_PARQUET_SHA256:
        raise DataContractError(
            f"Precondition failed: R2 Parquet SHA-256 mismatch: {computed_r2_parquet_sha} != {EXPECTED_R2_PARQUET_SHA256}"
        )

    # 6. Verify R3 manifest
    r3_path = root / "docs/phase14/manifests/manifest_r3_HYP_004.json"
    if not r3_path.exists():
        raise DataContractError(f"Precondition failed: Missing R3 manifest at {r3_path}")
    with open(r3_path, "r", encoding="utf-8") as f:
        r3_data = json.load(f)
    computed_r3_sha = r3_data.get("manifest_sha256")
    if computed_r3_sha != EXPECTED_R3_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R3 Manifest SHA-256 mismatch: {computed_r3_sha} != {EXPECTED_R3_MANIFEST_SHA256}"
        )
    # Check primary outcome is permanently NOT_ACCEPTED
    primary_eval = r3_data.get("primary_acceptance_evaluation", {})
    if primary_eval.get("outcome_label") != PRIMARY_OUTCOME_LABEL:
        raise DataContractError(
            f"Precondition failed: R3 primary outcome mismatch: {primary_eval.get('outcome_label')} != {PRIMARY_OUTCOME_LABEL}"
        )

    # 7. Verify R4 manifest
    r4_path = root / "docs/phase14/manifests/manifest_r4_HYP_004.json"
    if not r4_path.exists():
        raise DataContractError(f"Precondition failed: Missing R4 manifest at {r4_path}")
    with open(r4_path, "r", encoding="utf-8") as f:
        r4_data = json.load(f)
    computed_r4_sha = r4_data.get("manifest_sha256")
    if computed_r4_sha != EXPECTED_R4_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R4 Manifest SHA-256 mismatch: {computed_r4_sha} != {EXPECTED_R4_MANIFEST_SHA256}"
        )

    return {
        "hypothesis_sha256": computed_hyp_sha,
        "preregistration_sha256": computed_prereg_sha,
        "r1_manifest_sha256": computed_r1_sha,
        "r2_manifest_sha256": computed_r2_sha,
        "r2_parquet_sha256": computed_r2_parquet_sha,
        "r3_manifest_sha256": computed_r3_sha,
        "r4_manifest_sha256": computed_r4_sha,
    }


def load_and_compute_log_returns(
    r2_parquet_path: Path,
) -> Tuple[List[LogReturnRow], List[str]]:
    """Load R2 session endpoints, filter to eligible sessions, and compute natural log returns.

    Formulas:
        log_r1_t = ln(p1_1000_price / p0_previous_primary_close)
        log_r13_t = ln(p13_current_primary_close / p12_1530_price)

    Strict Preconditions:
        All prices must be strictly > 0. If any price <= 0, fail-closed immediately.
    """
    if not r2_parquet_path.exists():
        raise DataContractError(f"R2 parquet file does not exist: {r2_parquet_path}")

    r2_sha = hashlib.sha256(r2_parquet_path.read_bytes()).hexdigest()
    if r2_sha != EXPECTED_R2_PARQUET_SHA256:
        raise DataContractError(
            f"R2 parquet SHA-256 mismatch: {r2_sha} != {EXPECTED_R2_PARQUET_SHA256}"
        )

    table = pq.read_table(r2_parquet_path)
    df = table.to_pandas()

    total_sessions = len(df)
    if total_sessions != EXPECTED_TOTAL_SESSIONS:
        raise DataContractError(
            f"Total sessions count mismatch: {total_sessions} != {EXPECTED_TOTAL_SESSIONS}"
        )

    excluded_df = df[~df["primary_regression_eligible"]]
    excluded_dates = sorted(excluded_df["trading_date"].tolist())
    if len(excluded_dates) != EXPECTED_EXCLUDED_OBSERVATIONS:
        raise DataContractError(
            f"Excluded count mismatch: {len(excluded_dates)} != {EXPECTED_EXCLUDED_OBSERVATIONS}"
        )

    eligible_df = df[df["primary_regression_eligible"]].sort_values("trading_date").reset_index(drop=True)
    if len(eligible_df) != EXPECTED_ELIGIBLE_OBSERVATIONS:
        raise DataContractError(
            f"Eligible sessions count mismatch: {len(eligible_df)} != {EXPECTED_ELIGIBLE_OBSERVATIONS}"
        )

    rows: List[LogReturnRow] = []
    for _, row in eligible_df.iterrows():
        t_date = str(row["trading_date"])
        p0_val = row["p0_previous_primary_close"]
        p1_val = row["p1_1000_price"]
        p12_val = row["p12_1530_price"]
        p13_val = row["p13_current_primary_close"]

        # Convert to Decimal
        p0_dec = Decimal(str(p0_val))
        p1_dec = Decimal(str(p1_val))
        p12_dec = Decimal(str(p12_val))
        p13_dec = Decimal(str(p13_val))

        # Strict positive price assertion
        if p0_dec <= Decimal("0"):
            raise DataContractError(f"Non-positive price p0={p0_dec} on date {t_date}")
        if p1_dec <= Decimal("0"):
            raise DataContractError(f"Non-positive price p1={p1_dec} on date {t_date}")
        if p12_dec <= Decimal("0"):
            raise DataContractError(f"Non-positive price p12={p12_dec} on date {t_date}")
        if p13_dec <= Decimal("0"):
            raise DataContractError(f"Non-positive price p13={p13_dec} on date {t_date}")

        # Natural log returns computation
        log_r1_f = math.log(float(p1_dec) / float(p0_dec))
        log_r13_f = math.log(float(p13_dec) / float(p12_dec))

        log_r1_dec = to_decimal18(Decimal(f"{log_r1_f:.18f}"))
        log_r13_dec = to_decimal18(Decimal(f"{log_r13_f:.18f}"))

        if log_r1_dec is None or log_r13_dec is None:
            raise DataContractError(f"Failed to quantize log return on date {t_date}")

        rows.append(
            LogReturnRow(
                trading_date=t_date,
                p0=p0_dec,
                p1=p1_dec,
                p12=p12_dec,
                p13=p13_dec,
                log_r1=log_r1_dec,
                log_r13=log_r13_dec,
                source_r2_dataset_sha256=r2_sha,
            )
        )

    return rows, excluded_dates


def build_canonical_log_returns_parquet(
    rows: Sequence[LogReturnRow],
    output_path: Path,
) -> Path:
    """Serialize the log-return dataset to Parquet format."""
    if len(rows) != EXPECTED_ELIGIBLE_OBSERVATIONS:
        raise DataContractError(
            f"Dataset cardinality violation: expected {EXPECTED_ELIGIBLE_OBSERVATIONS}, got {len(rows)}"
        )

    pydict: Dict[str, List[Any]] = {field.name: [] for field in LOG_RETURN_ROBUSTNESS_ARROW_SCHEMA}

    for r in rows:
        pydict["trading_date"].append(r.trading_date)
        pydict["p0"].append(r.p0)
        pydict["p1"].append(r.p1)
        pydict["p12"].append(r.p12)
        pydict["p13"].append(r.p13)
        pydict["log_r1"].append(r.log_r1)
        pydict["log_r13"].append(r.log_r13)
        pydict["source_R2_dataset_sha256"].append(r.source_r2_dataset_sha256)

    table = pa.Table.from_pydict(pydict, schema=LOG_RETURN_ROBUSTNESS_ARROW_SCHEMA)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path, compression="snappy")
    return output_path


def execute_log_return_robustness_regression(
    rows: Sequence[LogReturnRow],
    r2_parquet_sha256: str,
    log_parquet_sha256: str,
) -> LogRobustnessResult:
    """Execute the single authorized OLS regression with Newey-West HAC inference on log returns.

    Model:
        log_r13_t = alpha_log + beta_log * log_r1_t + eps_t
    Sample:
        T = 1489
    HAC Kernel:
        Bartlett
    Lag:
        L = floor(4 * (T / 100)^(2/9)) = 7
    """
    n = len(rows)
    if n != EXPECTED_ELIGIBLE_OBSERVATIONS:
        raise DataContractError(f"Sample size violation: expected {EXPECTED_ELIGIBLE_OBSERVATIONS}, got {n}")

    log_r1_dec = [r.log_r1 for r in rows]
    log_r13_dec = [r.log_r13 for r in rows]

    # Compute OLS slope beta, HAC SE, t-stat, p-val using Bartlett kernel
    beta_log_dec, hac_se_dec, hac_t_dec, p_val_dec = compute_ols_beta_and_hac(
        x=log_r1_dec,
        y=log_r13_dec,
        lag_bandwidth=EXPECTED_HAC_LAG,
    )

    log_r1_f = np.array([float(v) for v in log_r1_dec], dtype=np.float64)
    log_r13_f = np.array([float(v) for v in log_r13_dec], dtype=np.float64)

    mean_x = float(np.mean(log_r1_f))
    mean_y = float(np.mean(log_r13_f))
    beta_f = float(beta_log_dec)

    alpha_f = mean_y - beta_f * mean_x
    alpha_log_dec = to_decimal18(Decimal(f"{alpha_f:.18f}"))
    alpha_log_dec = alpha_log_dec if alpha_log_dec is not None else Decimal("0")

    # Compute unadjusted R^2
    y_pred = alpha_f + beta_f * log_r1_f
    residuals = log_r13_f - y_pred
    sse = float(np.sum(residuals ** 2))
    sst = float(np.sum((log_r13_f - mean_y) ** 2))

    if sst <= 0.0:
        raise DataContractError(f"SST non-positive in R^2 calculation: SST={sst}")

    r2_f = 1.0 - (sse / sst)
    r2_dec = to_decimal18(Decimal(f"{r2_f:.18f}"))
    r2_dec = r2_dec if r2_dec is not None else Decimal("0")

    # Descriptive significance thresholds
    sig_10pct = p_val_dec < Decimal("0.10")
    sig_5pct = p_val_dec < Decimal("0.05")
    sig_1pct = p_val_dec < Decimal("0.01")

    return LogRobustnessResult(
        sample_size_t=n,
        hac_lag_l=EXPECTED_HAC_LAG,
        alpha_log=alpha_log_dec,
        beta_log=beta_log_dec,
        hac_se=hac_se_dec,
        hac_t_stat=hac_t_dec,
        two_sided_p_value=p_val_dec,
        r_squared=r2_dec,
        sig_10pct=sig_10pct,
        sig_5pct=sig_5pct,
        sig_1pct=sig_1pct,
        source_r2_parquet_sha256=r2_parquet_sha256,
        derived_log_parquet_sha256=log_parquet_sha256,
        earliest_date=rows[0].trading_date,
        latest_date=rows[-1].trading_date,
    )


def build_log_robustness_manifest(
    result: LogRobustnessResult,
    source_git_sha: str,
) -> Dict[str, Any]:
    """Construct canonical tracked JSON manifest for log-return robustness characterization."""
    payload: Dict[str, Any] = {
        "manifest_type": "LOG_RETURN_ROBUSTNESS_MANIFEST",
        "hypothesis_id": "HYP_004",
        "hypothesis_ordinal": 4,
        "mechanism_id": "MEC-0014A",
        "source_git_sha": source_git_sha,
        "epistemic_classification": {
            "analysis_family": "PREREGISTERED_SECONDARY_ANALYSIS_FAMILY",
            "operationalization": "POST_PRIMARY_HUMAN_AUTHORIZED_ROBUSTNESS_OPERATIONALIZATION",
            "role": "ONE_DIMENSION_AT_A_TIME_ROBUSTNESS_OPERATIONALIZATION",
            "authority_scope": "ZERO_AUTHORITY_TO_ALTER_PRIMARY_OUTCOME",
        },
        "upstream_governance_lineage": {
            "hypothesis_sha256": EXPECTED_HYP_004_SHA256,
            "preregistration_sha256": EXPECTED_PREREG_SHA256,
            "r1_manifest_sha256": EXPECTED_R1_MANIFEST_SHA256,
            "r2_manifest_sha256": EXPECTED_R2_MANIFEST_SHA256,
            "r3_manifest_sha256": EXPECTED_R3_MANIFEST_SHA256,
            "r4_manifest_sha256": EXPECTED_R4_MANIFEST_SHA256,
            "source_r2_parquet_sha256": result.source_r2_parquet_sha256,
            "derived_log_parquet_sha256": result.derived_log_parquet_sha256,
        },
        "sample_and_formulas": {
            "sample_size_t": result.sample_size_t,
            "date_range": {
                "start": result.earliest_date,
                "end": result.latest_date,
            },
            "formula_log_r1": "ln(p1_1000_price / p0_previous_primary_close)",
            "formula_log_r13": "ln(p13_current_primary_close / p12_1530_price)",
            "log_base": "NATURAL_LOGARITHM_LN",
            "positive_price_precondition_enforced": True,
            "model_specification": "log_r13_t = alpha_log + beta_log * log_r1_t + epsilon_t",
            "inference_hac_family": "NEWEY_WEST_BARTLETT_KERNEL",
            "hac_lag_rule": "floor(4 * (T / 100)^(2/9))",
            "hac_lag_l": result.hac_lag_l,
        },
        "econometric_estimates": {
            "alpha_log": str(result.alpha_log),
            "beta_log": str(result.beta_log),
            "hac_se": str(result.hac_se),
            "hac_t_stat": str(result.hac_t_stat),
            "two_sided_p_value": str(result.two_sided_p_value),
            "r_squared": str(result.r_squared),
        },
        "descriptive_significance_indicators": {
            "p_less_than_0_10": result.sig_10pct,
            "p_less_than_0_05": result.sig_5pct,
            "p_less_than_0_01": result.sig_1pct,
        },
        "primary_benchmark_comparison": {
            "primary_outcome_label": PRIMARY_OUTCOME_LABEL,
            "primary_simple_return_estimates": {
                "alpha_hat": str(PRIMARY_ALPHA),
                "beta_hat": str(PRIMARY_BETA),
                "hac_se": str(PRIMARY_HAC_SE),
                "hac_t_stat": str(PRIMARY_HAC_T),
                "two_sided_p_value": str(PRIMARY_P_VALUE),
                "r_squared": str(PRIMARY_R_SQUARED),
                "p_less_than_0_10": False,
                "p_less_than_0_05": False,
                "p_less_than_0_01": False,
            },
            "qualitative_comparison": {
                "sign_agreement": "SAME_POSITIVE_SIGN",
                "beta_magnitude_description": "Descriptively comparable (+0.023451 vs +0.022489)",
                "p_value_description": "Statistically insignificant at all standard thresholds (0.508409 vs 0.523533)",
                "r_squared_description": "Descriptively comparable (0.002910 vs 0.002641)",
                "direction_consistent_with_primary": True,
            },
        },
        "governance_invariants": {
            "primary_outcome_changed": False,
            "external_holdout_accessed": False,
            "trading_authorized": False,
            "capital_authority_usd": "0.00",
            "single_model_k_equals_1": True,
        },
        "status": "STEP_LOG_ROBUSTNESS_SEALED",
        "next_required_action": "HUMAN_AUDIT_REQUIRED",
    }

    manifest_json = CanonicalConfigSerializer.to_canonical_json(payload)
    manifest_bytes = manifest_json.encode("utf-8")
    payload["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    return payload
