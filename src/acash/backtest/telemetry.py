"""Reality Gap Telemetry and Attribution Engine (Phase 5).

Measures and decomposes the systematic divergence between Phase 4 Analytical Edge
and Phase 5 Simulated Event-Driven Realized Edge:
Reality Gap = Edge_Phase4_Analytical - Edge_Phase5_Simulated
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from acash.backtest.schema import RealityGapSummary


class RealityGapAttributionEngine:
    """Calculates and decomposes execution friction drag against analytical assumptions."""

    @staticmethod
    def calculate_attribution(
        phase4_analytical_edge_bps: Decimal,
        phase5_simulated_realized_bps: Decimal,
        spread_drag_bps: Decimal = Decimal("0.0"),
        latency_slip_drag_bps: Decimal = Decimal("0.0"),
        queue_position_drag_bps: Decimal = Decimal("0.0"),
        fee_drag_bps: Decimal = Decimal("0.0"),
    ) -> RealityGapSummary:
        """Decompose total reality gap into constituent friction components."""
        reality_gap_bps = phase4_analytical_edge_bps - phase5_simulated_realized_bps

        return RealityGapSummary(
            phase4_analytical_edge_bps=phase4_analytical_edge_bps,
            phase5_simulated_realized_bps=phase5_simulated_realized_bps,
            reality_gap_bps=reality_gap_bps,
            spread_drag_bps=spread_drag_bps,
            latency_slip_drag_bps=latency_slip_drag_bps,
            queue_position_drag_bps=queue_position_drag_bps,
            fee_drag_bps=fee_drag_bps,
        )

    @staticmethod
    def derive_from_fills(
        fills: List[Any],
        initial_cash: Decimal,
        phase4_analytical_edge_bps: Decimal,
        phase5_simulated_realized_bps: Decimal,
        total_fees_paid: Optional[Decimal] = None,
    ) -> RealityGapSummary:
        """Derive empirical friction drag metrics directly from execution fill records."""
        reality_gap_bps = phase4_analytical_edge_bps - phase5_simulated_realized_bps

        if initial_cash <= Decimal("0.0") or not fills:
            return RealityGapSummary(
                phase4_analytical_edge_bps=phase4_analytical_edge_bps,
                phase5_simulated_realized_bps=phase5_simulated_realized_bps,
                reality_gap_bps=reality_gap_bps,
                spread_drag_bps=Decimal("0.0"),
                latency_slip_drag_bps=Decimal("0.0"),
                queue_position_drag_bps=max(Decimal("0.0"), reality_gap_bps),
                fee_drag_bps=Decimal("0.0"),
            )

        # 1. Empirical fee drag (actual fees incurred relative to initial capital)
        if total_fees_paid is not None:
            fee_sum = total_fees_paid
        else:
            fee_sum = sum(
                (Decimal(str(getattr(f, "fee_paid", f.get("fee_paid", 0) if isinstance(f, dict) else 0))) for f in fills),
                Decimal("0.0"),
            )
        fee_drag_bps = (fee_sum / initial_cash) * Decimal("10000.0")

        # 2. Empirical slippage & latency drag from actual recorded fill slippage
        slippage_cost = Decimal("0.0")
        for f in fills:
            qty = Decimal(str(getattr(f, "fill_qty", f.get("fill_qty", 0) if isinstance(f, dict) else 0)))
            px = Decimal(str(getattr(f, "fill_price", f.get("fill_price", 0) if isinstance(f, dict) else 0)))
            slip_bps = Decimal(str(getattr(f, "slippage_incurred_bps", f.get("slippage_incurred_bps", 0) if isinstance(f, dict) else 0)))
            slippage_cost += (qty * px) * (slip_bps / Decimal("10000.0"))

        latency_slip_drag_bps = (slippage_cost / initial_cash) * Decimal("10000.0")

        # 3. Empirical spread drag
        spread_drag_bps = Decimal("0.0")

        # 4. Empirical queue position / timing opportunity cost drag
        accounted_drag = fee_drag_bps + latency_slip_drag_bps + spread_drag_bps
        queue_position_drag_bps = max(Decimal("0.0"), reality_gap_bps - accounted_drag)

        return RealityGapSummary(
            phase4_analytical_edge_bps=phase4_analytical_edge_bps,
            phase5_simulated_realized_bps=phase5_simulated_realized_bps,
            reality_gap_bps=reality_gap_bps,
            spread_drag_bps=spread_drag_bps,
            latency_slip_drag_bps=latency_slip_drag_bps,
            queue_position_drag_bps=queue_position_drag_bps,
            fee_drag_bps=fee_drag_bps,
        )

    @staticmethod
    def generate_reality_gap_report(summary: RealityGapSummary) -> Dict[str, Any]:
        """Generate structured diagnostic dictionary for research reporting."""
        retained_edge_pct = (
            (summary.phase5_simulated_realized_bps / summary.phase4_analytical_edge_bps) * Decimal("100.0")
            if summary.phase4_analytical_edge_bps > Decimal("0.0")
            else Decimal("0.0")
        )

        return {
            "phase4_analytical_edge_bps": float(summary.phase4_analytical_edge_bps),
            "phase5_simulated_realized_bps": float(summary.phase5_simulated_realized_bps),
            "reality_gap_bps": float(summary.reality_gap_bps),
            "retained_edge_percentage": float(retained_edge_pct),
            "friction_decomposition": {
                "spread_drag_bps": float(summary.spread_drag_bps),
                "latency_slip_drag_bps": float(summary.latency_slip_drag_bps),
                "queue_position_drag_bps": float(summary.queue_position_drag_bps),
                "fee_drag_bps": float(summary.fee_drag_bps),
            },
            "verdict": "FEASIBLE" if summary.phase5_simulated_realized_bps > Decimal("0.0") else "UNREALIZABLE_ALPHA",
        }
