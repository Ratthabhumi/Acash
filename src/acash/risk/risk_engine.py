"""Phase 9: Deterministic Risk Engine & Derisking Engine (Slice 2).

Implements:
1. DeterministicRiskEngine realizing the IRiskEngine interface contract.
2. DeriskEngine implementing EXACT_SCALE_DOWN and BINARY_REJECT sizing policies.
3. Sovereign risk gate evaluation:
   - Gross leverage ceiling (sum of risky weights <= max_gross_leverage)
   - Single-asset concentration bound (w_i <= max_asset_concentration)
   - Mandatory minimum cash buffer floor (w_cash >= min_cash_buffer)
   - Peak-to-trough equity drawdown limit (drawdown < max_drawdown_limit_pct)
   - Cumulative daily loss limit (daily_loss < max_daily_loss_usd)
   - Free margin headroom buffer (free_margin >= min_margin_buffer_usd)
   - Market data staleness bound (data_age_ms <= max_market_data_age_ms)
   - Broker connection state check (is_broker_connected == True)
4. Emits authoritative RiskEvaluationReport with 60s TTL and SHA-256 lineage digests.

Strict Invariants:
- Research (8.5) != Allocation (8) != Risk (9) != Execution (7).
- Risk Rejection => Execution Blocked (Fail-Closed, 0 Orders Transmitted).
- Phase 9 has ZERO direct broker wire transmission authority.
- Derisking monotonicity: w_i' <= w_i, no short creation, cash buffer preserved, idempotent.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from typing import Mapping, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.signal import RiskAssessment, TargetAllocation
from acash.core.domain.types import freeze_mapping
from acash.core.interfaces.risk import IRiskEngine
from acash.core.serialization import CanonicalConfigSerializer
from acash.risk.risk_schema import (
    CandidateRiskAllocation,
    DeriskPolicy,
    RiskEvaluationReport,
    RiskPolicyConfig,
    RiskVerdict,
    _ensure_utc,
    _verify_finite_decimal,
)


def calculate_exact_scale_down_factor(
    weights: Mapping[str, Decimal],
    max_gross_leverage: Decimal,
    max_asset_concentration: Decimal,
    min_cash_buffer: Decimal,
) -> Decimal:
    """Calculate the uniform scale-down factor alpha under EXACT_SCALE_DOWN policy.

    Mathematical Formulation:
        alpha = min(
            1.0,
            max_gross_leverage / sum(w_i),
            min_{w_i > 0}(max_asset_concentration / w_i),
            (1.0 - min_cash_buffer) / sum(w_i)
        )

    Properties Mathematically Proven:
    1. Monotonic: alpha <= 1.0 => w_i' = alpha * w_i <= w_i for all w_i >= 0.
    2. No Short Creation: alpha >= 0 and w_i >= 0 => w_i' >= 0.
    3. Leverage Bounded: sum(w_i') = alpha * sum(w_i) <= max_gross_leverage.
    4. Concentration Bounded: for all i, w_i' = alpha * w_i <= max_asset_concentration.
    5. Cash Buffer Preserved: w_cash' = 1.0 - sum(w_i') >= min_cash_buffer.
    6. Idempotent: re-scaling w' yields alpha' = 1.0 and w'' == w'.
    """
    _verify_finite_decimal(max_gross_leverage, "max_gross_leverage", min_val=Decimal("0.0"))
    _verify_finite_decimal(max_asset_concentration, "max_asset_concentration", min_val=Decimal("0.0"), max_val=Decimal("1.0"))
    _verify_finite_decimal(min_cash_buffer, "min_cash_buffer", min_val=Decimal("0.0"), max_val=Decimal("1.0"))

    if min_cash_buffer > Decimal("1.0") or max_gross_leverage <= Decimal("0.0"):
        return Decimal("0.0")

    sum_risky = Decimal("0.0")
    for sym, w in weights.items():
        dec_w = _verify_finite_decimal(w, f"weights[{sym}]", allow_negative=False)
        sum_risky += dec_w

    if sum_risky == Decimal("0.0"):
        return Decimal("1.0")

    # 1. Gross Leverage constraint factor
    alpha_lev = max_gross_leverage / sum_risky

    # 2. Maximum Asset Concentration constraint factor
    alpha_conc = Decimal("1.0")
    for sym, w in weights.items():
        if w > Decimal("0.0"):
            conc_factor = max_asset_concentration / w
            if conc_factor < alpha_conc:
                alpha_conc = conc_factor

    # 3. Minimum Cash Buffer constraint factor
    avail_for_risky = Decimal("1.0") - min_cash_buffer
    if avail_for_risky < Decimal("0.0"):
        return Decimal("0.0")
    alpha_cash = avail_for_risky / sum_risky

    alpha = min(Decimal("1.0"), alpha_lev, alpha_conc, alpha_cash)
    return max(Decimal("0.0"), alpha)


class DeriskEngine:
    """Engine executing deterministic portfolio derisking and weight sizing."""

    @classmethod
    def evaluate_and_derisk(
        cls,
        weights: Mapping[str, Decimal],
        policy: RiskPolicyConfig,
    ) -> Tuple[Mapping[str, Decimal], Decimal, RiskVerdict, Optional[str]]:
        """Evaluate candidate weights against leverage and concentration bounds and apply derisking.

        Returns:
            (adjusted_weights, cash_weight, verdict, rejection_reason)
        """
        # Validate all inputs
        cleaned_weights: dict[str, Decimal] = {}
        sum_risky = Decimal("0.0")
        max_conc_observed = Decimal("0.0")

        for sym, w in weights.items():
            dec_w = _verify_finite_decimal(w, f"weights[{sym}]", allow_negative=False)
            cleaned_weights[sym.strip().upper()] = dec_w
            sum_risky += dec_w
            if dec_w > max_conc_observed:
                max_conc_observed = dec_w

        cash_from_weights = Decimal("1.0") - sum_risky

        # Check if already fully safe
        is_leverage_safe = sum_risky <= policy.max_gross_leverage
        is_concentration_safe = max_conc_observed <= policy.max_asset_concentration
        is_cash_safe = cash_from_weights >= policy.min_cash_buffer

        if is_leverage_safe and is_concentration_safe and is_cash_safe:
            return (
                freeze_mapping(cleaned_weights),
                cash_from_weights,
                RiskVerdict.APPROVED,
                None,
            )

        # Limits breached: apply configured DeriskPolicy
        if policy.derisk_policy == DeriskPolicy.BINARY_REJECT:
            reasons = []
            if not is_leverage_safe:
                reasons.append(f"Gross leverage ({sum_risky}) exceeds limit ({policy.max_gross_leverage})")
            if not is_concentration_safe:
                reasons.append(f"Concentration ({max_conc_observed}) exceeds limit ({policy.max_asset_concentration})")
            if not is_cash_safe:
                reasons.append(f"Cash buffer ({cash_from_weights}) below minimum ({policy.min_cash_buffer})")
            return (
                freeze_mapping({}),
                Decimal("1.0"),
                RiskVerdict.REJECTED,
                "BINARY_REJECT: " + "; ".join(reasons),
            )

        elif policy.derisk_policy == DeriskPolicy.EXACT_SCALE_DOWN:
            alpha = calculate_exact_scale_down_factor(
                weights=cleaned_weights,
                max_gross_leverage=policy.max_gross_leverage,
                max_asset_concentration=policy.max_asset_concentration,
                min_cash_buffer=policy.min_cash_buffer,
            )

            if alpha == Decimal("0.0"):
                return (
                    freeze_mapping({}),
                    Decimal("1.0"),
                    RiskVerdict.REJECTED,
                    "EXACT_SCALE_DOWN_FAILED: Infeasible constraints produced zero scale factor.",
                )

            scaled_weights: dict[str, Decimal] = {}
            sum_scaled = Decimal("0.0")
            for sym, w in cleaned_weights.items():
                scaled_w = alpha * w
                scaled_weights[sym] = scaled_w
                sum_scaled += scaled_w

            scaled_cash = Decimal("1.0") - sum_scaled
            return (
                freeze_mapping(scaled_weights),
                scaled_cash,
                RiskVerdict.REDUCED,
                None,
            )

        raise DataContractError(f"Unsupported DeriskPolicy: '{policy.derisk_policy}'")


class DeterministicRiskEngine(IRiskEngine):
    """Authoritative Sovereign Risk Engine implementing deterministic runtime evaluation and kill switch gates."""

    def __init__(self, policy_config: Optional[RiskPolicyConfig] = None) -> None:
        self.policy = policy_config or RiskPolicyConfig()

    def evaluate_candidate_allocation(
        self,
        candidate_allocation: CandidateRiskAllocation,
        portfolio_state: PortfolioState,
        account_state: Optional[AccountState] = None,
        peak_equity: Optional[Decimal] = None,
        realized_pnl_today: Optional[Decimal] = None,
        data_age_ms: Optional[int] = None,
        clock_drift_ms: Optional[int] = None,
        is_broker_connected: bool = True,
        as_of: Optional[datetime] = None,
    ) -> RiskEvaluationReport:
        """Evaluate candidate allocation against all sovereign risk gates and emit an authoritative RiskEvaluationReport."""
        eval_time = _ensure_utc(as_of or datetime.now(timezone.utc))
        exp_time = eval_time + timedelta(seconds=self.policy.evaluation_ttl_seconds)

        # 1. Telemetry & Connection Invariant Checks
        if not is_broker_connected:
            return self._build_rejection_report(
                candidate=candidate_allocation,
                portfolio_state=portfolio_state,
                account_state=account_state,
                reason="BROKER_DISCONNECTED: Broker connection is inactive.",
                eval_time=eval_time,
                exp_time=exp_time,
                verdict=RiskVerdict.KILL_SWITCH_BLOCKED,
            )

        if data_age_ms is not None and data_age_ms > self.policy.max_market_data_age_ms:
            return self._build_rejection_report(
                candidate=candidate_allocation,
                portfolio_state=portfolio_state,
                account_state=account_state,
                reason=f"STALE_MARKET_DATA: Data age ({data_age_ms}ms) exceeds limit ({self.policy.max_market_data_age_ms}ms).",
                eval_time=eval_time,
                exp_time=exp_time,
                verdict=RiskVerdict.KILL_SWITCH_BLOCKED,
            )

        if clock_drift_ms is not None and clock_drift_ms > self.policy.max_clock_drift_ms:
            return self._build_rejection_report(
                candidate=candidate_allocation,
                portfolio_state=portfolio_state,
                account_state=account_state,
                reason=f"CLOCK_SKEW_DETECTED: Clock drift ({clock_drift_ms}ms) exceeds limit ({self.policy.max_clock_drift_ms}ms).",
                eval_time=eval_time,
                exp_time=exp_time,
                verdict=RiskVerdict.KILL_SWITCH_BLOCKED,
            )

        # 2. Portfolio Equity & Double-Entry Sanity Checks
        curr_equity = portfolio_state.total_equity
        if not curr_equity.is_finite() or curr_equity <= Decimal("0.0"):
            return self._build_rejection_report(
                candidate=candidate_allocation,
                portfolio_state=portfolio_state,
                account_state=account_state,
                reason=f"INVALID_EQUITY: Portfolio total_equity ({curr_equity}) is non-positive or non-finite.",
                eval_time=eval_time,
                exp_time=exp_time,
                verdict=RiskVerdict.REJECTED,
            )

        # 3. Peak-to-Trough Equity Drawdown Gate
        historical_peak = peak_equity or curr_equity
        _verify_finite_decimal(historical_peak, "peak_equity", min_val=Decimal("0.0"))
        if historical_peak > Decimal("0.0") and curr_equity < historical_peak:
            drawdown_pct = ((historical_peak - curr_equity) / historical_peak) * Decimal("100.0")
            if drawdown_pct >= self.policy.max_drawdown_limit_pct:
                return self._build_rejection_report(
                    candidate=candidate_allocation,
                    portfolio_state=portfolio_state,
                    account_state=account_state,
                    reason=f"MAX_DRAWDOWN_BREACHED: Portfolio drawdown ({drawdown_pct:.2f}%) exceeds limit ({self.policy.max_drawdown_limit_pct}%).",
                    eval_time=eval_time,
                    exp_time=exp_time,
                    verdict=RiskVerdict.KILL_SWITCH_BLOCKED,
                    metrics={"drawdown_pct": drawdown_pct, "peak_equity": historical_peak},
                )
        else:
            drawdown_pct = Decimal("0.0")

        # 4. Intraday Daily Loss Gate
        today_loss = realized_pnl_today if realized_pnl_today is not None else portfolio_state.realized_pnl
        total_daily_pnl = today_loss + portfolio_state.unrealized_pnl
        if total_daily_pnl < -self.policy.max_daily_loss_usd:
            return self._build_rejection_report(
                candidate=candidate_allocation,
                portfolio_state=portfolio_state,
                account_state=account_state,
                reason=f"MAX_DAILY_LOSS_BREACHED: Daily P&L ({total_daily_pnl}) breaches max loss limit (-{self.policy.max_daily_loss_usd}).",
                eval_time=eval_time,
                exp_time=exp_time,
                verdict=RiskVerdict.KILL_SWITCH_BLOCKED,
                metrics={"total_daily_pnl": total_daily_pnl, "daily_loss_limit": self.policy.max_daily_loss_usd},
            )

        # 5. Account Margin Buffer Gate (if AccountState supplied)
        if account_state is not None:
            free_margin = account_state.free_margin
            if free_margin < self.policy.min_margin_buffer_usd:
                return self._build_rejection_report(
                    candidate=candidate_allocation,
                    portfolio_state=portfolio_state,
                    account_state=account_state,
                    reason=f"MARGIN_BUFFER_BREACHED: Free margin ({free_margin}) below buffer threshold ({self.policy.min_margin_buffer_usd}).",
                    eval_time=eval_time,
                    exp_time=exp_time,
                    verdict=RiskVerdict.REJECTED,
                    metrics={"free_margin": free_margin, "min_margin_buffer": self.policy.min_margin_buffer_usd},
                )

        # 6. Evaluate Candidate Weights via DeriskEngine
        adj_weights, cash_w, verdict, reason = DeriskEngine.evaluate_and_derisk(
            weights=candidate_allocation.weights,
            policy=self.policy,
        )

        # Calculate observed metrics
        gross_lev = sum(adj_weights.values(), Decimal("0.0"))
        max_conc = max(adj_weights.values(), default=Decimal("0.0"))
        metrics_obs = {
            "gross_leverage": gross_lev,
            "max_asset_concentration": max_conc,
            "cash_weight": cash_w,
            "drawdown_pct": drawdown_pct,
            "total_daily_pnl": total_daily_pnl,
        }

        # Build digests
        port_digest = self._compute_portfolio_digest(portfolio_state)
        acc_digest = self._compute_account_digest(account_state)

        eval_id = f"RISK_EVAL_{int(eval_time.timestamp() * 1000)}"

        return RiskEvaluationReport(
            evaluation_id=eval_id,
            verdict=verdict,
            original_allocation_digest=candidate_allocation.candidate_digest,
            portfolio_state_digest=port_digest,
            account_state_digest=acc_digest,
            risk_policy_digest=self.policy.policy_digest,
            adjusted_weights=adj_weights,
            cash_weight=cash_w,
            metrics_observed=metrics_obs,
            rejection_reason=reason,
            evaluated_at_utc=eval_time,
            expires_at_utc=exp_time,
        )

    def evaluate_allocation(
        self,
        target_allocation: TargetAllocation,
        portfolio_state: PortfolioState,
        account_state: Optional[AccountState],
        timestamp_utc: datetime,
    ) -> RiskAssessment:
        """IRiskEngine interface compliance method converting TargetAllocation into RiskAssessment."""
        # Convert TargetAllocation (float) into CandidateRiskAllocation (Decimal)
        dec_weights = {k: _verify_finite_decimal(w, f"target_allocation.weights[{k}]", allow_negative=False) for k, w in target_allocation.weights.items()}
        dec_cash = _verify_finite_decimal(target_allocation.cash_weight, "target_allocation.cash_weight", allow_negative=False)

        source_digest = hashlib.sha256(
            CanonicalConfigSerializer.to_canonical_json({
                "weights": {k: str(dec_weights[k]) for k in sorted(dec_weights.keys())},
                "cash_weight": str(dec_cash),
                "timestamp": target_allocation.timestamp_utc.isoformat(),
            }).encode("utf-8")
        ).hexdigest()

        candidate = CandidateRiskAllocation(
            candidate_id=f"CAND_{int(timestamp_utc.timestamp())}",
            strategy_id="LEGACY_INTERFACE_ADAPTER",
            weights=dec_weights,
            cash_weight=dec_cash,
            source_decision_digest=source_digest,
            as_of_utc=timestamp_utc,
        )

        report = self.evaluate_candidate_allocation(
            candidate_allocation=candidate,
            portfolio_state=portfolio_state,
            account_state=account_state,
            as_of=timestamp_utc,
        )

        is_approved = report.verdict in (RiskVerdict.APPROVED, RiskVerdict.REDUCED)
        float_adjusted = {k: float(w) for k, w in report.adjusted_weights.items()}

        drawdown_pct = float(report.metrics_observed.get("drawdown_pct", Decimal("0.0")))
        gross_lev = float(report.metrics_observed.get("gross_leverage", Decimal("0.0")))

        return RiskAssessment(
            approved=is_approved,
            adjusted_weights=float_adjusted,
            rejection_reason=report.rejection_reason,
            max_drawdown_pct=drawdown_pct,
            risk_utilization_pct=gross_lev * 100.0,
            timestamp_utc=timestamp_utc,
        )

    def _build_rejection_report(
        self,
        candidate: CandidateRiskAllocation,
        portfolio_state: PortfolioState,
        account_state: Optional[AccountState],
        reason: str,
        eval_time: datetime,
        exp_time: datetime,
        verdict: RiskVerdict = RiskVerdict.REJECTED,
        metrics: Optional[Mapping[str, Decimal]] = None,
    ) -> RiskEvaluationReport:
        """Construct fail-closed 100% Cash rejection report."""
        port_digest = self._compute_portfolio_digest(portfolio_state)
        acc_digest = self._compute_account_digest(account_state)
        eval_id = f"RISK_EVAL_REJ_{int(eval_time.timestamp() * 1000)}"

        return RiskEvaluationReport(
            evaluation_id=eval_id,
            verdict=verdict,
            original_allocation_digest=candidate.candidate_digest,
            portfolio_state_digest=port_digest,
            account_state_digest=acc_digest,
            risk_policy_digest=self.policy.policy_digest,
            adjusted_weights={},
            cash_weight=Decimal("1.0"),
            metrics_observed=metrics or {},
            rejection_reason=reason,
            evaluated_at_utc=eval_time,
            expires_at_utc=exp_time,
        )

    def _compute_portfolio_digest(self, portfolio_state: PortfolioState) -> str:
        payload = {
            "timestamp_utc": portfolio_state.timestamp_utc.isoformat(),
            "total_equity": str(portfolio_state.total_equity),
            "cash_balance": str(portfolio_state.cash_balance),
            "gross_exposure": str(portfolio_state.gross_exposure),
            "unrealized_pnl": str(portfolio_state.unrealized_pnl),
            "realized_pnl": str(portfolio_state.realized_pnl),
        }
        return hashlib.sha256(CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")).hexdigest()

    def _compute_account_digest(self, account_state: Optional[AccountState]) -> str:
        if account_state is None:
            return hashlib.sha256(b"ACCOUNT_STATE_NOT_SUPPLIED").hexdigest()
        payload = {
            "account_id": account_state.account_id,
            "balance": str(account_state.balance),
            "equity": str(account_state.equity),
            "free_margin": str(account_state.free_margin),
            "timestamp_utc": account_state.timestamp_utc.isoformat(),
        }
        return hashlib.sha256(CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")).hexdigest()
