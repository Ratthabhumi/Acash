"""ACASH Phase 11: Forward Tracking, Online Drift Detection & Execution Reality Attribution.

This module provides an independent observational and evidence-generating plane
to evaluate forward strategy health and attribute empirical execution friction
without claiming operational execution or historical research authority.
"""

from acash.monitoring.attribution import (
    ExecutionAttributionEngine,
    aggregate_execution_cost_evidence,
    decompose_execution_drag,
)
from acash.monitoring.metrics import (
    DEFAULT_ANNUALIZATION_FACTOR,
    ForwardMetricsCalculator,
    calculate_forward_window_metrics,
)
from acash.monitoring.schema import (
    USD_SCALE,
    ExecutionAttributionPolicy,
    ExecutionCostEvidence,
    ExecutionObservation,
    ExecutionSide,
    ForwardGovernanceRecommendation,
    ForwardHealthPolicy,
    ForwardHealthState,
    ForwardObservation,
    ForwardWindowMetrics,
    LiquidityRole,
    RealizedExecutionDrag,
    StrategyForwardDriftEvidence,
)
from acash.monitoring.state_machine import (
    ForwardHealthStateMachine,
    StateTransitionResult,
)

__all__ = [
    "USD_SCALE",
    "DEFAULT_ANNUALIZATION_FACTOR",
    "ExecutionSide",
    "LiquidityRole",
    "ForwardHealthState",
    "ForwardGovernanceRecommendation",
    "ForwardObservation",
    "ForwardHealthPolicy",
    "ForwardWindowMetrics",
    "StrategyForwardDriftEvidence",
    "ExecutionObservation",
    "RealizedExecutionDrag",
    "ExecutionAttributionPolicy",
    "ExecutionCostEvidence",
    "ForwardMetricsCalculator",
    "calculate_forward_window_metrics",
    "ForwardHealthStateMachine",
    "StateTransitionResult",
    "ExecutionAttributionEngine",
    "decompose_execution_drag",
    "aggregate_execution_cost_evidence",
]
