"""CORE-001 / HYP_011 deterministic historical pipeline (frozen R1 contracts only)."""

from acash.research.hyp_011.accounting import (
    SIMULATED_STARTING_AUM,
    run_allocation,
    run_single_asset_buy_hold,
)
from acash.research.hyp_011.gates import (
    HYP011ContractQualificationEvidence,
    derive_contract_qualification,
)
from acash.research.hyp_011.partitions import (
    HISTORICAL_END,
    HISTORICAL_START,
    expected_rebalance_sessions,
    expected_sessions,
)

__all__ = [
    "SIMULATED_STARTING_AUM",
    "HISTORICAL_START",
    "HISTORICAL_END",
    "run_allocation",
    "run_single_asset_buy_hold",
    "HYP011ContractQualificationEvidence",
    "derive_contract_qualification",
    "expected_sessions",
    "expected_rebalance_sessions",
]
