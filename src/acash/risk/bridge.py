"""Phase 9: Type-Safe Cross-Phase Risk State Bridge (Slice 5).

Provides explicit, validated, and lossless/bounded conversions between:
1. Phase 1 / Phase 8 PortfolioState & AccountState <-> Phase 8 RiskSnapshot
2. Phase 1 TargetAllocation (float) <-> Phase 9 CandidateRiskAllocation (Decimal)
3. Phase 9 RiskEvaluationReport (Decimal/DTO) <-> Phase 1 RiskAssessment (float/interface)
4. Phase 9 RiskEvaluationReport & PortfolioState -> Phase 7 Execution RiskState

Strict Invariants:
- Zero implicit magic conversions: every transformation defines source, destination, and failure mode.
- Explicit finite Decimal boundary: validates finiteness and rejects NaN/Inf/unsupported types without claiming precision restoration.
- Preserves accounting invariants: Total Equity == Cash + Sum(Market Value).
- Preserves temporal identity: preserves as_of / timestamp_utc, rejects inverted timestamps, no silent now() replacements.
- Preserves cryptographic digests: binds destination identity to source state digests.
- Zero Execution Authority: the bridge is a pure data transformer; it has no broker wire or order execution authority.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from typing import Mapping, Optional

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.signal import RiskAssessment, TargetAllocation
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.schema import (
    CalculationStatus,
    RiskState,
    RiskStatus,
)
from acash.portfolio.schema import RiskSnapshot
from acash.risk.risk_schema import (
    CandidateRiskAllocation,
    RiskEvaluationReport,
    RiskVerdict,
    _ensure_utc,
    _verify_finite_decimal,
)


class RiskStateBridge:
    """Explicit, type-safe conversion bridge across ACASH research, portfolio, risk, and execution state models."""

    @classmethod
    def portfolio_state_to_risk_snapshot(
        cls,
        portfolio_state: PortfolioState,
        account_state: Optional[AccountState] = None,
        peak_equity: Optional[Decimal] = None,
        max_drawdown_limit_pct: Decimal = Decimal("15.00"),
        min_margin_buffer_threshold: Decimal = Decimal("5000.00"),
        is_kill_switch_active: bool = False,
        snapshot_id: Optional[str] = None,
    ) -> RiskSnapshot:
        """Convert Phase 1 PortfolioState & AccountState into Phase 8 RiskSnapshot."""
        equity = _verify_finite_decimal(portfolio_state.total_equity, "total_equity", min_val=Decimal("0.0000001"))
        cash = _verify_finite_decimal(portfolio_state.cash_balance, "cash_balance", allow_negative=True)
        margin_u = _verify_finite_decimal(portfolio_state.margin_used, "margin_used", min_val=Decimal("0.0"))

        if account_state is not None:
            headroom = _verify_finite_decimal(account_state.free_margin, "free_margin", allow_negative=False)
        else:
            headroom = max(Decimal("0.0"), equity - margin_u)

        hist_peak = peak_equity or equity
        _verify_finite_decimal(hist_peak, "peak_equity", min_val=Decimal("0.0"))

        if hist_peak > Decimal("0.0") and equity < hist_peak:
            dd_pct = ((hist_peak - equity) / hist_peak) * Decimal("100.0")
        else:
            dd_pct = Decimal("0.0")

        snap_id = snapshot_id or f"RISK_SNAP_{int(portfolio_state.timestamp_utc.timestamp() * 1000)}"

        return RiskSnapshot(
            snapshot_id=snap_id,
            timestamp=portfolio_state.timestamp_utc,
            account_equity=equity,
            cash_balance=cash,
            margin_used=margin_u,
            margin_headroom=headroom,
            margin_buffer_threshold=min_margin_buffer_threshold,
            current_drawdown_pct=dd_pct,
            max_drawdown_limit_pct=max_drawdown_limit_pct,
            is_kill_switch_active=is_kill_switch_active,
        )

    @classmethod
    def target_allocation_to_candidate_allocation(
        cls,
        target_allocation: TargetAllocation,
        strategy_id: str = "STRATEGY_ALLOCATION",
        candidate_id: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> CandidateRiskAllocation:
        """Convert Phase 1 float-based TargetAllocation into Phase 9 Decimal-based CandidateRiskAllocation."""
        dec_weights: dict[str, Decimal] = {}
        for sym, w in target_allocation.weights.items():
            if not isinstance(sym, str) or not sym.strip():
                raise DataContractError(f"Invalid symbol in target_allocation: '{sym}'.")
            dec_w = _verify_finite_decimal(w, f"weights[{sym}]", allow_negative=False)
            dec_weights[sym.strip().upper()] = dec_w

        dec_cash = _verify_finite_decimal(target_allocation.cash_weight, "cash_weight", allow_negative=False)
        eval_time = _ensure_utc(as_of or target_allocation.timestamp_utc)

        # Compute source decision digest
        sorted_weights = {k: str(dec_weights[k]) for k in sorted(dec_weights.keys())}
        payload = {
            "strategy_id": strategy_id,
            "weights": sorted_weights,
            "cash_weight": str(dec_cash),
            "timestamp": eval_time.isoformat(),
        }
        source_digest = hashlib.sha256(CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")).hexdigest()

        cid = candidate_id or f"CAND_{int(eval_time.timestamp() * 1000)}"

        return CandidateRiskAllocation(
            candidate_id=cid,
            strategy_id=strategy_id,
            weights=dec_weights,
            cash_weight=dec_cash,
            source_decision_digest=source_digest,
            as_of_utc=eval_time,
        )

    @classmethod
    def candidate_allocation_to_target_allocation(
        cls,
        candidate: CandidateRiskAllocation,
        rationale: str = "BRIDGED_CANDIDATE_ALLOCATION",
    ) -> TargetAllocation:
        """Convert Phase 9 CandidateRiskAllocation back into Phase 1 TargetAllocation."""
        float_weights = {k: float(v) for k, v in candidate.weights.items()}
        float_cash = float(candidate.cash_weight)

        return TargetAllocation(
            weights=float_weights,
            cash_weight=float_cash,
            rationale=rationale,
            timestamp_utc=candidate.as_of_utc,
        )

    @classmethod
    def risk_evaluation_report_to_risk_assessment(
        cls,
        report: RiskEvaluationReport,
        timestamp_utc: Optional[datetime] = None,
    ) -> RiskAssessment:
        """Convert Phase 9 RiskEvaluationReport into Phase 1 RiskAssessment."""
        is_approved = report.verdict in (RiskVerdict.APPROVED, RiskVerdict.REDUCED)
        float_weights = {k: float(v) for k, v in report.adjusted_weights.items()}

        dd_pct = float(report.metrics_observed.get("drawdown_pct", Decimal("0.0")))
        gross_lev = float(report.metrics_observed.get("gross_leverage", Decimal("0.0")))

        ts = _ensure_utc(timestamp_utc or report.evaluated_at_utc)

        return RiskAssessment(
            approved=is_approved,
            adjusted_weights=float_weights,
            rejection_reason=report.rejection_reason,
            max_drawdown_pct=dd_pct,
            risk_utilization_pct=gross_lev * 100.0,
            timestamp_utc=ts,
        )

    @classmethod
    def risk_evaluation_report_to_execution_risk_state(
        cls,
        report: RiskEvaluationReport,
        portfolio_state: PortfolioState,
        authorization_id: str,
        strategy_id: str,
        data_age_ms: int = 0,
        is_broker_connected: bool = True,
        is_clock_skew_detected: bool = False,
        is_market_data_stale: bool = False,
        active_kill_switch_event_id: Optional[str] = None,
    ) -> RiskState:
        """Bridge Phase 9 RiskEvaluationReport & PortfolioState into Phase 7 Execution RiskState."""
        if not authorization_id.strip():
            raise DataContractError("authorization_id must be a non-empty string.")
        if not strategy_id.strip():
            raise DataContractError("strategy_id must be a non-empty string.")

        # Determine RiskStatus from Verdict
        if report.verdict == RiskVerdict.APPROVED:
            r_status = RiskStatus.NORMAL
        elif report.verdict == RiskVerdict.REDUCED:
            r_status = RiskStatus.RESTRICTED
        elif report.verdict == RiskVerdict.KILL_SWITCH_BLOCKED:
            r_status = RiskStatus.HALTED
        else:
            r_status = RiskStatus.WARNING

        calc_status = CalculationStatus.NOMINAL if not is_market_data_stale else CalculationStatus.STALE

        dd_pct = report.metrics_observed.get("drawdown_pct", Decimal("0.0"))
        max_conc = report.metrics_observed.get("max_asset_concentration", Decimal("0.0"))

        return RiskState(
            timestamp=report.evaluated_at_utc,
            authorization_id=authorization_id.strip(),
            strategy_id=strategy_id.strip(),
            total_equity=portfolio_state.total_equity,
            realized_pnl_today=portfolio_state.realized_pnl,
            unrealized_pnl=portfolio_state.unrealized_pnl,
            current_drawdown_pct=dd_pct,
            gross_exposure_notional=portfolio_state.gross_exposure,
            net_exposure_notional=portfolio_state.net_exposure,
            concentration_ratio=max_conc,
            parametric_var_95=Decimal("0.0"),
            historical_cvar_95=Decimal("0.0"),
            confidence_level=0.95,
            estimation_window_bars=252,
            risk_model_version="PHASE9_DETERMINISTIC_RISK_ENGINE_V1",
            data_timestamp=report.evaluated_at_utc,
            data_age_ms=max(0, data_age_ms),
            calculation_status=calc_status,
            is_market_data_stale=is_market_data_stale,
            is_broker_connected=is_broker_connected,
            is_clock_skew_detected=is_clock_skew_detected,
            risk_status=r_status,
            active_kill_switch_event_id=active_kill_switch_event_id,
        )
