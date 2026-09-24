"""CORE-001 / HYP_009 deterministic M1 research pipeline (frozen R1 contracts only).

No scientific decisions are made in this package. Every constant below is bound
to the sealed R1 manifest / preregistration / accounting clarification.
"""

from acash.research.hyp_009.partitions import (
    AUTHORIZED_MAX_DATE,
    AUTHORIZED_MIN_DATE,
    M1_END,
    M1_START,
    WARMUP_END,
    WARMUP_START,
)
from acash.research.hyp_009.signals import (
    LOOKBACK_MONTH_ENDS,
    compute_signal_states,
)
from acash.research.hyp_009.accounting import (
    SIMULATED_STARTING_AUM,
    run_portfolio,
)
from acash.research.hyp_009.gates import evaluate_gates

__all__ = [
    "AUTHORIZED_MAX_DATE",
    "AUTHORIZED_MIN_DATE",
    "M1_END",
    "M1_START",
    "WARMUP_END",
    "WARMUP_START",
    "LOOKBACK_MONTH_ENDS",
    "SIMULATED_STARTING_AUM",
    "compute_signal_states",
    "run_portfolio",
    "evaluate_gates",
]
