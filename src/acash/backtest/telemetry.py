"""Reality Gap Telemetry and Attribution Engine (Phase 5).

Measures and decomposes the systematic divergence between Phase 4 Analytical Edge
and Phase 5 Simulated Event-Driven Realized Edge:
Reality Gap = Edge_Phase4_Analytical - Edge_Phase5_Simulated
"""

from decimal import Decimal
from typing import Any, Dict, List
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
            },
            "verdict": "FEASIBLE" if summary.phase5_simulated_realized_bps > Decimal("0.0") else "UNREALIZABLE_ALPHA",
        }
