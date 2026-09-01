"""Phase 9: Sovereign Risk Engine & Kill Switch for ACASH.

Provides:
- Domain Contracts & Enums:
  - RiskVerdict, DeriskPolicy, KillSwitchState, EmergencyFlattenStatus
  - RiskPolicyConfig, CandidateRiskAllocation, RiskEvaluationReport
  - KillSwitchResetEvent, EmergencyFlattenIntent
- Deterministic Evaluation & Verification Utilities:
  - _verify_finite_decimal, _validate_sha256
"""

from acash.risk.bridge import RiskStateBridge
from acash.risk.emergency import (
    EmergencyFlattenGenerator,
    EmergencyFlattenTracker,
)
from acash.risk.kill_switch import (
    ALLOWED_KILL_SWITCH_TRANSITIONS,
    KillSwitchEvent,
    SovereignKillSwitchController,
)
from acash.risk.risk_engine import (
    DeriskEngine,
    DeterministicRiskEngine,
    calculate_exact_scale_down_factor,
)
from acash.risk.risk_schema import (
    CandidateRiskAllocation,
    DeriskPolicy,
    EmergencyFlattenIntent,
    EmergencyFlattenStatus,
    KillSwitchResetEvent,
    KillSwitchState,
    RiskEvaluationReport,
    RiskPolicyConfig,
    RiskVerdict,
    _validate_sha256,
    _verify_finite_decimal,
)

__all__ = [
    "RiskVerdict",
    "DeriskPolicy",
    "KillSwitchState",
    "EmergencyFlattenStatus",
    "RiskPolicyConfig",
    "CandidateRiskAllocation",
    "RiskEvaluationReport",
    "KillSwitchResetEvent",
    "EmergencyFlattenIntent",
    "_verify_finite_decimal",
    "_validate_sha256",
    "calculate_exact_scale_down_factor",
    "DeriskEngine",
    "DeterministicRiskEngine",
    "KillSwitchEvent",
    "ALLOWED_KILL_SWITCH_TRANSITIONS",
    "SovereignKillSwitchController",
    "EmergencyFlattenGenerator",
    "EmergencyFlattenTracker",
    "RiskStateBridge",
]
