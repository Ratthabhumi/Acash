"""Phase 11 Realized Execution Drag Attribution Engine.

Deterministic, policy-defined execution-cost attribution categories:
- Spread Drag: cost of crossing the quoted bid-ask spread at arrival.
- Timing Drag: signed drag/benefit from decision midpoint to arrival midpoint.
- Slippage Drag: signed drag/benefit from arrival quoted price to executed fill price.
- Commission Fee Drag: exchange/broker fees normalized by filled notional.
- Rebate Benefit: liquidity provider rebates normalized by filled notional.
- Gross Drag: non-negative floor of execution frictions.
- Net Realized Execution Cost: signed net cost (legitimately negative if rebate exceeds gross drag).

Attribution Invariant:
The components are attribution categories under the declared benchmark convention;
they are not required to algebraically reconcile to a single implementation-shortfall
measurement because categories use distinct benchmark denominators
(arrival_mid_price, decision_mid_price, arrival_quoted, and filled_notional_usd).

Coverage & Reliability Philosophy:
Incomplete execution evidence is a coverage/sample-reliability issue,
never an automatic negative performance penalty (No Evidence != Negative Evidence).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_CEILING
import math
from typing import Optional, Sequence
import uuid

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.schema import (
    ExecutionAttributionPolicy,
    ExecutionCostEvidence,
    ExecutionObservation,
    ExecutionSide,
    RealizedExecutionDrag,
)

BPS_SCALER = Decimal("10000.0")
NORMAL_95_CRITICAL_VALUE = Decimal("1.959963984540054")


class ExecutionAttributionEngine:
    """Deterministic execution drag decomposition and sample aggregation engine."""

    @staticmethod
    def decompose_execution_drag(
        observation: ExecutionObservation,
        expected_drag_bps: Optional[Decimal] = None,
    ) -> RealizedExecutionDrag:
        """Decompose atomic fill observation into discrete execution drag categories.

        Args:
            observation: Validated atomic ExecutionObservation.
            expected_drag_bps: Optional ex-ante expected execution cost benchmark.

        Returns:
            RealizedExecutionDrag containing exact basis point attribution categories.
        """
        side_sign = observation.side.side_sign  # +1.0 for BUY, -1.0 for SELL

        # 1. Spread Drag (bps)
        # Half-spread cost at arrival relative to arrival midpoint
        spread = observation.arrival_ask_price - observation.arrival_bid_price
        two_mid = Decimal("2.0") * observation.arrival_mid_price
        spread_drag_bps = (spread / two_mid) * BPS_SCALER

        # 2. Timing Drag (bps)
        # Signed price drift between decision midpoint and arrival midpoint
        timing_drift = observation.arrival_mid_price - observation.decision_mid_price
        timing_drag_bps = side_sign * (timing_drift / observation.decision_mid_price) * BPS_SCALER

        # 3. Slippage Drag (bps)
        # Signed price difference between executed fill and arrival quoted price
        # For BUY: quoted price is arrival ask; for SELL: quoted price is arrival bid
        arrival_quoted = (
            observation.arrival_ask_price
            if observation.side == ExecutionSide.BUY
            else observation.arrival_bid_price
        )
        slippage_diff = observation.executed_fill_price - arrival_quoted
        slippage_drag_bps = side_sign * (slippage_diff / arrival_quoted) * BPS_SCALER

        # 4. Fee & Rebate Drag (bps)
        # Normalized by filled notional value in USD
        commission_fee_bps = (observation.commission_fee_usd / observation.filled_notional_usd) * BPS_SCALER
        rebate_benefit_bps = (observation.rebate_usd / observation.filled_notional_usd) * BPS_SCALER

        # 5. Gross Execution Drag (bps)
        # Non-negative baseline: adverse timing and slippage are penalized, favorable timing/slippage do not subsidize gross drag
        gross_execution_drag_bps = (
            spread_drag_bps
            + max(Decimal("0.0"), timing_drag_bps)
            + max(Decimal("0.0"), slippage_drag_bps)
            + commission_fee_bps
        )

        # 6. Net Realized Execution Cost (bps)
        # Signed: can legitimately be negative if liquidity provider rebate exceeds gross drag
        net_realized_execution_cost_bps = gross_execution_drag_bps - rebate_benefit_bps

        # 7. Expected vs Realized Divergence (bps)
        if expected_drag_bps is not None:
            expected_vs_realized_drag_bps = net_realized_execution_cost_bps - expected_drag_bps
        else:
            expected_vs_realized_drag_bps = Decimal("0.0")

        return RealizedExecutionDrag(
            observation_id=observation.observation_id,
            symbol=observation.symbol,
            spread_drag_bps=spread_drag_bps,
            timing_drag_bps=timing_drag_bps,
            slippage_drag_bps=slippage_drag_bps,
            commission_fee_bps=commission_fee_bps,
            rebate_benefit_bps=rebate_benefit_bps,
            gross_execution_drag_bps=gross_execution_drag_bps,
            net_realized_execution_cost_bps=net_realized_execution_cost_bps,
            expected_vs_realized_drag_bps=expected_vs_realized_drag_bps,
        )

    def aggregate_execution_cost_evidence(
        self,
        observations: Sequence[ExecutionObservation],
        policy: ExecutionAttributionPolicy,
        venue: str,
        symbol: str,
        as_of_utc: datetime,
        coverage_start_utc: datetime,
        coverage_end_utc: datetime,
        expected_fill_count: Optional[int] = None,
        evidence_id: Optional[str] = None,
    ) -> ExecutionCostEvidence:
        """Aggregate sample execution observations into forensic empirical cost evidence.

        Args:
            observations: Sequence of discrete ExecutionObservation DTOs.
            policy: ExecutionAttributionPolicy defining sample thresholds.
            venue: Target execution venue.
            symbol: Target financial instrument symbol.
            as_of_utc: Timestamp of evidence aggregation.
            coverage_start_utc: Inception timestamp of attribution window.
            coverage_end_utc: Final timestamp of attribution window.
            expected_fill_count: Optional total intended fills for coverage ratio calculation.
            evidence_id: Optional custom evidence ID.

        Returns:
            ExecutionCostEvidence with complete statistical uncertainty metadata.

        Raises:
            DataContractError: On 0 fills, temporal inversion, or critical coverage breach (< 80%).
        """
        if coverage_start_utc > coverage_end_utc:
            raise DataContractError(
                f"coverage_start_utc ({coverage_start_utc}) cannot exceed coverage_end_utc ({coverage_end_utc})."
            )

        # Filter observations matching venue, symbol, and temporal coverage
        matching_obs = [
            obs
            for obs in observations
            if obs.venue == venue
            and obs.symbol == symbol
            and coverage_start_utc <= obs.fill_timestamp_utc <= coverage_end_utc
        ]

        fill_count = len(matching_obs)
        if fill_count == 0:
            raise DataContractError(
                f"Cannot aggregate execution cost evidence: 0 fills observed for {symbol} on {venue} "
                f"between {coverage_start_utc.isoformat()} and {coverage_end_utc.isoformat()}."
            )

        # Calculate coverage ratio
        if expected_fill_count is not None:
            if expected_fill_count <= 0:
                raise DataContractError(f"expected_fill_count must be positive, got {expected_fill_count}.")
            coverage_ratio = Decimal(str(fill_count)) / Decimal(str(expected_fill_count))

            # Critical Fail-Closed Coverage Guard
            if coverage_ratio < policy.critical_fail_closed_coverage_ratio:
                raise DataContractError(
                    f"CRITICAL_COVERAGE_BREACH: Execution telemetry coverage ratio ({coverage_ratio:.4f}) "
                    f"breached critical fail-closed threshold ({policy.critical_fail_closed_coverage_ratio}). "
                    "Cannot emit unverified execution cost evidence."
                )
        else:
            coverage_ratio = Decimal("1.0")

        # Decompose drag for each atomic observation
        drags = [self.decompose_execution_drag(obs) for obs in matching_obs]

        n_dec = Decimal(str(fill_count))
        gross_drags = [d.gross_execution_drag_bps for d in drags]
        net_costs = [d.net_realized_execution_cost_bps for d in drags]

        # 1. Means
        mean_gross_drag_bps = sum(gross_drags, Decimal("0.0")) / n_dec
        mean_net_cost_bps = sum(net_costs, Decimal("0.0")) / n_dec

        # 2. Median Net Cost (Deterministic tie policy)
        sorted_net = sorted(net_costs)
        mid_idx = fill_count // 2
        if fill_count % 2 == 1:
            median_net_cost_bps = sorted_net[mid_idx]
        else:
            median_net_cost_bps = (sorted_net[mid_idx - 1] + sorted_net[mid_idx]) / Decimal("2.0")

        # 3. P95 Gross Drag (Deterministic nearest-rank percentile)
        sorted_gross = sorted(gross_drags)
        p95_rank = int(math.ceil(float(policy.tail_percentile) * fill_count))
        p95_idx = max(0, min(fill_count - 1, p95_rank - 1))
        p95_gross_drag_bps = sorted_gross[p95_idx]

        # 4. Standard Error & 95% Confidence Interval Half-Width
        if fill_count >= 2:
            n_minus_one_dec = Decimal(str(fill_count - 1))
            sum_sq_dev = sum(((c - mean_net_cost_bps) ** 2 for c in net_costs), Decimal("0.0"))
            sample_variance = sum_sq_dev / n_minus_one_dec
            sample_stdev = sample_variance.sqrt()
            standard_error_bps = sample_stdev / n_dec.sqrt()
            confidence_interval_95_half_width_bps = NORMAL_95_CRITICAL_VALUE * standard_error_bps
        else:
            standard_error_bps = Decimal("0.0")
            confidence_interval_95_half_width_bps = Decimal("0.0")

        # 5. Statistical Reliability Gating
        is_statistically_reliable = (
            fill_count >= policy.min_reliable_sample_count
            and coverage_ratio >= policy.min_reliable_coverage_ratio
        )

        eid = evidence_id if evidence_id is not None else f"CEVID_{symbol}_{venue}_{uuid.uuid4().hex[:12]}"

        return ExecutionCostEvidence(
            evidence_id=eid,
            venue=venue,
            symbol=symbol,
            as_of_utc=as_of_utc,
            coverage_start_utc=coverage_start_utc,
            coverage_end_utc=coverage_end_utc,
            fill_count=fill_count,
            effective_sample_count=fill_count,
            coverage_ratio=coverage_ratio,
            mean_gross_drag_bps=mean_gross_drag_bps,
            mean_net_cost_bps=mean_net_cost_bps,
            median_net_cost_bps=median_net_cost_bps,
            p95_gross_drag_bps=p95_gross_drag_bps,
            standard_error_bps=standard_error_bps,
            confidence_interval_95_half_width_bps=confidence_interval_95_half_width_bps,
            is_statistically_reliable=is_statistically_reliable,
            policy_digest=policy.policy_digest,
        )


def decompose_execution_drag(
    observation: ExecutionObservation,
    expected_drag_bps: Optional[Decimal] = None,
) -> RealizedExecutionDrag:
    """Convenience function decomposing an ExecutionObservation into RealizedExecutionDrag."""
    return ExecutionAttributionEngine.decompose_execution_drag(
        observation=observation,
        expected_drag_bps=expected_drag_bps,
    )


def aggregate_execution_cost_evidence(
    observations: Sequence[ExecutionObservation],
    policy: ExecutionAttributionPolicy,
    venue: str,
    symbol: str,
    as_of_utc: datetime,
    coverage_start_utc: datetime,
    coverage_end_utc: datetime,
    expected_fill_count: Optional[int] = None,
    evidence_id: Optional[str] = None,
) -> ExecutionCostEvidence:
    """Convenience function aggregating observations into ExecutionCostEvidence."""
    engine = ExecutionAttributionEngine()
    return engine.aggregate_execution_cost_evidence(
        observations=observations,
        policy=policy,
        venue=venue,
        symbol=symbol,
        as_of_utc=as_of_utc,
        coverage_start_utc=coverage_start_utc,
        coverage_end_utc=coverage_end_utc,
        expected_fill_count=expected_fill_count,
        evidence_id=evidence_id,
    )
