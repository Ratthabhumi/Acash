"""Phase 14 Step R4: HYP_007 Post-M1 Governance Freeze & Partition Rules.

Authority:
- Zarattini, Aziz, Barbon (2024), SSRN 4824172 / Concretum Group Reference Implementation
- MEC-0015 Strategy Contract Audit & Profitability-First Intake
- MEC-0017 / HYP_007 Preregistration & Additive Governance Amendments
- Phase 14 Stage A Human Authorization: AUTHORIZE_HYP_007_POST_M1_FREEZE_AND_CONDITIONAL_R4_M2_EXECUTION
- Starting Canonical Head: 01345a2a98ddee1729045d366d9c9406448530ac

Strictly Enforces:
- Freeze of M2 interval (2024-05-01 through 2026-08-14) as PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE (NOT_PRISTINE_OOS).
- Quarantine of historical gap [2026-08-15 to instant before prospective M3 start).
- Prospective M3 start rule: first NYSE standard regular session whose 09:30 ET open occurs strictly after Stage-A governance commit timestamp.
- M2 simulated starting AUM normalization ($100,000.00).
- M2 state warm-up from sealed prior M1 history with zero performance contribution.
- Exact four R4 continuation gates (G1: Return > 0, G2: Sharpe >= 0.50, G3: MDD <= 0.35, G4: 2x Friction Return >= 0).
- Strict fail-closed boundary and firewall guards.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar, SessionType

# ---------------------------------------------------------------------------
# Upstream Lineage & Pinned Canonical Authority
# ---------------------------------------------------------------------------

CANONICAL_STARTING_HEAD_SHA: str = "01345a2a98ddee1729045d366d9c9406448530ac"
EXPECTED_M1_R3_CORRECTED_PACKAGE_SHA256: str = "d4bf18bb80ec650e4c4c0600a8cb5aebb762a7169b8b89111e604adf91293a25"
EXPECTED_M1_R2_DATASET_SHA256: str = "4dcf8546b8583bc214684228e29b329226ece904404768bc921f55991f1777aa"
EFFECTIVE_M1_VERDICT: str = "ACCEPTED_SUPPORTED_ON_REGISTERED_M1"
M1_SAMPLE_ROLE: str = "PUBLICATION_EXPOSED_DIRECT_SIP_REPLICATION_SAMPLE"

# ---------------------------------------------------------------------------
# Global Execution & Capital State
# ---------------------------------------------------------------------------

REAL_CAPITAL_AUTHORITY_USD: Decimal = Decimal("0.00")
NO_REAL_ORDERS: bool = True
PAPER_AUTHORIZED: bool = False
LIVE_AUTHORIZED: bool = False

# ---------------------------------------------------------------------------
# Partition Boundaries & Roles
# ---------------------------------------------------------------------------

M2_START_DATE_STR: str = "2024-05-01"
M2_END_DATE_STR: str = "2026-08-14"
M2_START_DATE: date = date(2024, 5, 1)
M2_END_DATE: date = date(2026, 8, 14)
M2_ROLE: str = "PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE"
M2_CLASSIFICATION: str = "NOT_PRISTINE_OOS"

QUARANTINE_START_DATE_STR: str = "2026-08-15"
QUARANTINE_START_DATE: date = date(2026, 8, 15)
GAP_ROLE: str = "QUARANTINED_HISTORICAL_GAP"

M3_ROLE: str = "PROSPECTIVE_ONLY"
M3_ACCESS_STATUS: str = "LOCKED_ZERO_ACCESS"

# ---------------------------------------------------------------------------
# M2 Accounting & Warm-Up Invariants
# ---------------------------------------------------------------------------

M2_SIMULATED_STARTING_AUM_USD: Decimal = Decimal("100000.00")
M2_AUM_CLASSIFICATION: str = "PRE_RESULT_SEGMENT_ACCOUNTING_NORMALIZATION"
M2_WARMUP_SOURCE: str = "SEALED_M1_R2_HISTORY"
M2_WARMUP_NOISE_AREA_SESSIONS: int = 14
M2_WARMUP_VOLATILITY_CLOSES: int = 16
M2_WARMUP_PERFORMANCE_CONTRIBUTION_USD: Decimal = Decimal("0.00")

# ---------------------------------------------------------------------------
# R4 Gate Thresholds
# ---------------------------------------------------------------------------

R4_G1_NET_TOTAL_RETURN_MIN: Decimal = Decimal("0.0")  # > 0.0
R4_G2_NET_ANNUALIZED_SHARPE_MIN: Decimal = Decimal("0.50")  # >= 0.50
R4_G3_MAX_DRAWDOWN_MAX: Decimal = Decimal("0.35")  # <= 0.35 (35%)
R4_G4_STRESS_TOTAL_RETURN_MIN: Decimal = Decimal("0.0")  # >= 0.0


class R4Verdict(str, Enum):
    """Authoritative Stage B R4 Verdict States."""
    PASS_RECENT_STRESS_SUPPORTED = "PASS_RECENT_STRESS_SUPPORTED"
    FAIL_CURRENT_EDGE_NOT_SUPPORTED = "FAIL_CURRENT_EDGE_NOT_SUPPORTED"
    BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT = "BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT"


@dataclass(frozen=True)
class R4GateEvaluationResult:
    """Evaluation result across all four frozen R4 gates."""
    g1_net_return: Decimal
    g1_pass: bool
    g2_sharpe: Decimal
    g2_pass: bool
    g3_max_drawdown: Decimal
    g3_pass: bool
    g4_stress_return: Decimal
    g4_pass: bool
    contract_valid: bool
    verdict: R4Verdict
    summary_message: str
    all_passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "r4_g1_net_total_return": {
                "observed": str(self.g1_net_return),
                "threshold": "> 0.0",
                "passed": self.g1_pass,
            },
            "r4_g2_net_annualized_sharpe": {
                "observed": str(self.g2_sharpe),
                "threshold": ">= 0.50",
                "passed": self.g2_pass,
            },
            "r4_g3_max_drawdown": {
                "observed": str(self.g3_max_drawdown),
                "threshold": "<= 0.35",
                "passed": self.g3_pass,
            },
            "r4_g4_2x_stress_total_return": {
                "observed": str(self.g4_stress_return),
                "threshold": ">= 0.0",
                "passed": self.g4_pass,
            },
            "contract_valid": self.contract_valid,
            "verdict": self.verdict.value,
            "summary_message": self.summary_message,
            "all_passed": self.all_passed,
        }


def evaluate_r4_gates(
    net_total_return: Decimal,
    annualized_sharpe: Decimal,
    max_drawdown: Decimal,
    stress_total_return: Decimal,
    contract_valid: bool = True,
    contract_failure_reason: Optional[str] = None,
) -> R4GateEvaluationResult:
    """Evaluate frozen R4 M2 continuation gates under strict fail-closed contract.

    Rule: ALL FOUR MUST PASS.
    If contract_valid is False -> BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT.
    """
    if not contract_valid:
        return R4GateEvaluationResult(
            g1_net_return=net_total_return,
            g1_pass=False,
            g2_sharpe=annualized_sharpe,
            g2_pass=False,
            g3_max_drawdown=max_drawdown,
            g3_pass=False,
            g4_stress_return=stress_total_return,
            g4_pass=False,
            contract_valid=False,
            verdict=R4Verdict.BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT,
            summary_message=contract_failure_reason or "Material data or execution contract failure.",
            all_passed=False,
        )

    g1_pass = net_total_return > R4_G1_NET_TOTAL_RETURN_MIN
    g2_pass = annualized_sharpe >= R4_G2_NET_ANNUALIZED_SHARPE_MIN
    g3_pass = max_drawdown <= R4_G3_MAX_DRAWDOWN_MAX
    g4_pass = stress_total_return >= R4_G4_STRESS_TOTAL_RETURN_MIN

    all_passed = g1_pass and g2_pass and g3_pass and g4_pass
    verdict = (
        R4Verdict.PASS_RECENT_STRESS_SUPPORTED
        if all_passed
        else R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    )
    summary = (
        "All four R4 M2 recent stress continuation gates passed."
        if all_passed
        else "One or more R4 M2 continuation gates failed; recent edge not supported."
    )

    return R4GateEvaluationResult(
        g1_net_return=net_total_return,
        g1_pass=g1_pass,
        g2_sharpe=annualized_sharpe,
        g2_pass=g2_pass,
        g3_max_drawdown=max_drawdown,
        g3_pass=g3_pass,
        g4_stress_return=stress_total_return,
        g4_pass=g4_pass,
        contract_valid=True,
        verdict=verdict,
        summary_message=summary,
        all_passed=all_passed,
    )


# ---------------------------------------------------------------------------
# Canonical Prospective M3 Start Calculation
# ---------------------------------------------------------------------------

def compute_prospective_m3_start_session(
    ratification_utc: datetime,
    calendar: Optional[NyseCa1Calendar] = None,
) -> Tuple[date, datetime]:
    """Compute exact prospective M3 start session using NyseCa1Calendar authority.

    Rule:
    M3_START = FIRST NYSE STANDARD REGULAR SESSION WHOSE 09:30 ET OPEN
    OCCURS STRICTLY AFTER STAGE-A GOVERNANCE COMMIT TIMESTAMP.

    Returns:
        (m3_start_date, m3_open_utc)
    """
    cal = calendar or NyseCa1Calendar()
    ny_tz = ZoneInfo("America/New_York")
    ratification_ny = ratification_utc.astimezone(ny_tz)

    candidate_date = ratification_ny.date()
    # Search forward up to 30 days
    for day_offset in range(30):
        check_date = candidate_date + date.resolution * day_offset
        if not cal.is_trading_session(check_date):
            continue
        if cal.is_early_close(check_date):
            # Non-standard regular sessions excluded by baseline contract
            continue

        sess = cal.get_session(check_date)
        if sess.session_type != SessionType.REGULAR:
            continue

        # Check if the 09:30 ET open occurs STRICTLY after ratification
        if sess.open_utc > ratification_utc:
            return check_date, sess.open_utc

    raise DataContractError(
        f"Unable to find eligible prospective NYSE regular session within 30 days of {ratification_utc}."
    )


# ---------------------------------------------------------------------------
# Strict Fail-Closed Firewalls & Request Guards
# ---------------------------------------------------------------------------

def enforce_m2_market_data_range_guard(session_date: Union[date, str, datetime]) -> None:
    """Enforce strict fail-closed boundary on M2 market data access.

    Authorized range: 2024-05-01 through 2026-08-14.
    Any attempt to request data for 2026-08-15 or later, or before 2024-05-01, raises DataContractError.
    """
    if isinstance(session_date, datetime):
        d = session_date.astimezone(ZoneInfo("America/New_York")).date()
    elif isinstance(session_date, str):
        d = date.fromisoformat(session_date[:10])
    else:
        d = session_date

    if d < M2_START_DATE:
        raise DataContractError(
            f"M2 range violation: Date {d.isoformat()} is before M2_START {M2_START_DATE_STR}."
        )
    if d > M2_END_DATE:
        raise DataContractError(
            f"M2 range violation: Date {d.isoformat()} is after M2_END {M2_END_DATE_STR}. "
            "Strict fail-closed: Access to 2026-08-15 or later is prohibited."
        )


def enforce_quarantine_firewall(session_date: Union[date, str, datetime], m3_start: Optional[date] = None) -> None:
    """Enforce strict firewall against reading prices, signals, or returns in the quarantined historical gap.

    Quarantine interval: [2026-08-15, M3_START).
    """
    if isinstance(session_date, datetime):
        d = session_date.astimezone(ZoneInfo("America/New_York")).date()
    elif isinstance(session_date, str):
        d = date.fromisoformat(session_date[:10])
    else:
        d = session_date

    if d >= QUARANTINE_START_DATE:
        if m3_start is None or d < m3_start:
            raise DataContractError(
                f"Quarantine gap violation: Date {d.isoformat()} lies within the strictly quarantined historical gap "
                f"[{QUARANTINE_START_DATE_STR}, {m3_start.isoformat() if m3_start else 'M3_START'}). "
                "Prices, signals, and returns in this interval are unreadable under HYP_007."
            )


def enforce_m3_firewall(session_date: Union[date, str, datetime], m3_start: date) -> None:
    """Enforce strict firewall against unauthorized M3 prospective access."""
    if isinstance(session_date, datetime):
        d = session_date.astimezone(ZoneInfo("America/New_York")).date()
    elif isinstance(session_date, str):
        d = date.fromisoformat(session_date[:10])
    else:
        d = session_date

    if d >= m3_start:
        raise DataContractError(
            f"M3 firewall violation: Date {d.isoformat()} is in prospective partition M3 (>= {m3_start.isoformat()}). "
            "M3 execution is strictly LOCKED."
        )
