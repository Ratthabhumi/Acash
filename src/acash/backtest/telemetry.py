"""Reality Gap Telemetry and Attribution Engine (Phase 5).

Measures and decomposes the systematic divergence between Phase 4 Analytical Edge
and Phase 5 Simulated Event-Driven Realized Edge:
Reality Gap = Edge_Phase4_Analytical - Edge_Phase5_Simulated = Spread Drag + Slippage Drag + Latency Drag + Fee Drag + Queue Drag + Unmodelled Residual
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
        slippage_drag_bps: Decimal = Decimal("0.0"),
        latency_drag_bps: Decimal = Decimal("0.0"),
        fee_drag_bps: Decimal = Decimal("0.0"),
        queue_drag_bps: Decimal = Decimal("0.0"),
        latency_slip_drag_bps: Optional[Decimal] = None,
        queue_position_drag_bps: Optional[Decimal] = None,
    ) -> RealityGapSummary:
        """Decompose total reality gap into constituent friction components."""
        reality_gap_bps = phase4_analytical_edge_bps - phase5_simulated_realized_bps

        eff_latency_slip = (
            latency_slip_drag_bps
            if latency_slip_drag_bps is not None
            else (latency_drag_bps + slippage_drag_bps)
        )
        eff_queue = queue_position_drag_bps if queue_position_drag_bps is not None else queue_drag_bps

        accounted = spread_drag_bps + slippage_drag_bps + latency_drag_bps + fee_drag_bps + eff_queue
        unmodelled_residual = reality_gap_bps - accounted

        return RealityGapSummary(
            phase4_analytical_edge_bps=phase4_analytical_edge_bps,
            phase5_simulated_realized_bps=phase5_simulated_realized_bps,
            reality_gap_bps=reality_gap_bps,
            spread_drag_bps=spread_drag_bps,
            slippage_drag_bps=slippage_drag_bps,
            latency_drag_bps=latency_drag_bps,
            fee_drag_bps=fee_drag_bps,
            queue_drag_bps=eff_queue,
            unmodelled_residual_bps=unmodelled_residual,
            latency_slip_drag_bps=eff_latency_slip,
            queue_position_drag_bps=eff_queue,
        )

    @staticmethod
    def derive_from_fills(
        fills: List[Any],
        initial_cash: Decimal,
        phase4_analytical_edge_bps: Decimal,
        phase5_simulated_realized_bps: Decimal,
        total_fees_paid: Optional[Decimal] = None,
    ) -> RealityGapSummary:
        """Derive empirical friction drag metrics directly from execution fill records and reference prices."""
        reality_gap_bps = phase4_analytical_edge_bps - phase5_simulated_realized_bps

        if initial_cash <= Decimal("0.0") or not fills:
            return RealityGapSummary(
                phase4_analytical_edge_bps=phase4_analytical_edge_bps,
                phase5_simulated_realized_bps=phase5_simulated_realized_bps,
                reality_gap_bps=reality_gap_bps,
                spread_drag_bps=Decimal("0.0"),
                slippage_drag_bps=Decimal("0.0"),
                latency_drag_bps=Decimal("0.0"),
                fee_drag_bps=Decimal("0.0"),
                queue_drag_bps=Decimal("0.0"),
                unmodelled_residual_bps=reality_gap_bps,
                latency_slip_drag_bps=Decimal("0.0"),
                queue_position_drag_bps=Decimal("0.0"),
            )

        # 1. Empirical fee drag
        if total_fees_paid is not None:
            fee_sum = total_fees_paid
        else:
            fee_sum = sum(
                (Decimal(str(getattr(f, "fee_paid", f.get("fee_paid", 0) if isinstance(f, dict) else 0))) for f in fills),
                Decimal("0.0"),
            )
        fee_drag_bps = (fee_sum / initial_cash) * Decimal("10000.0")

        # 2. Empirical slippage drag (pure depth impact / price degradation)
        slippage_cost = Decimal("0.0")
        for f in fills:
            qty = Decimal(str(getattr(f, "fill_qty", f.get("fill_qty", 0) if isinstance(f, dict) else 0)))
            px = Decimal(str(getattr(f, "fill_price", f.get("fill_price", 0) if isinstance(f, dict) else 0)))
            slip_bps = Decimal(str(getattr(f, "slippage_incurred_bps", f.get("slippage_incurred_bps", 0) if isinstance(f, dict) else 0)))
            slippage_cost += (qty * px) * (slip_bps / Decimal("10000.0"))
        slippage_drag_bps = (slippage_cost / initial_cash) * Decimal("10000.0")

        # 3. Empirical latency drift drag (price drift during transmission window)
        latency_cost = Decimal("0.0")
        for f in fills:
            qty = Decimal(str(getattr(f, "fill_qty", f.get("fill_qty", 0) if isinstance(f, dict) else 0)))
            px = Decimal(str(getattr(f, "fill_price", f.get("fill_price", 0) if isinstance(f, dict) else 0)))
            drift_bps = Decimal(str(getattr(f, "latency_drift_bps", f.get("latency_drift_bps", 0) if isinstance(f, dict) else 0)))
            latency_cost += (qty * px) * (drift_bps / Decimal("10000.0"))
        latency_drag_bps = (latency_cost / initial_cash) * Decimal("10000.0")

        # 4. Empirical spread drag (half-spread crossing cost for taker fills)
        spread_cost = Decimal("0.0")
        for f in fills:
            liq_type = str(getattr(f, "liquidity_type", f.get("liquidity_type", "") if isinstance(f, dict) else ""))
            if "TAKER" in liq_type.upper():
                qty = Decimal(str(getattr(f, "fill_qty", f.get("fill_qty", 0) if isinstance(f, dict) else 0)))
                bid_val = getattr(f, "bid_at_fill", f.get("bid_at_fill", None) if isinstance(f, dict) else None)
                ask_val = getattr(f, "ask_at_fill", f.get("ask_at_fill", None) if isinstance(f, dict) else None)
                if bid_val is not None and ask_val is not None:
                    bid = Decimal(str(bid_val))
                    ask = Decimal(str(ask_val))
                    if ask > bid:
                        half_spread = (ask - bid) / Decimal("2.0")
                        spread_cost += qty * half_spread
        spread_drag_bps = (spread_cost / initial_cash) * Decimal("10000.0")

        # 5. Empirical queue drag (maker adverse selection drift)
        queue_cost = Decimal("0.0")
        for f in fills:
            liq_type = str(getattr(f, "liquidity_type", f.get("liquidity_type", "") if isinstance(f, dict) else ""))
            if "MAKER" in liq_type.upper():
                arr_val = getattr(f, "arrival_price", f.get("arrival_price", None) if isinstance(f, dict) else None)
                if arr_val is not None:
                    arr_px = Decimal(str(arr_val))
                    fill_px = Decimal(str(getattr(f, "fill_price", f.get("fill_price", 0) if isinstance(f, dict) else 0)))
                    side = str(getattr(f, "side", f.get("side", "") if isinstance(f, dict) else "")).upper()
                    qty = Decimal(str(getattr(f, "fill_qty", f.get("fill_qty", 0) if isinstance(f, dict) else 0)))
                    # Maker buy filled lower than arrival mid is positive; filled higher is negative
                    adverse_drift = (fill_px - arr_px) if side == "BUY" else (arr_px - fill_px)
                    if adverse_drift > Decimal("0.0"):
                        queue_cost += qty * adverse_drift
        queue_drag_bps = (queue_cost / initial_cash) * Decimal("10000.0")

        # 6. Unmodelled residual gap (model mismatch / timing discrepancy)
        accounted = fee_drag_bps + slippage_drag_bps + latency_drag_bps + spread_drag_bps + queue_drag_bps
        unmodelled_residual_bps = reality_gap_bps - accounted

        return RealityGapSummary(
            phase4_analytical_edge_bps=phase4_analytical_edge_bps,
            phase5_simulated_realized_bps=phase5_simulated_realized_bps,
            reality_gap_bps=reality_gap_bps,
            spread_drag_bps=spread_drag_bps,
            slippage_drag_bps=slippage_drag_bps,
            latency_drag_bps=latency_drag_bps,
            fee_drag_bps=fee_drag_bps,
            queue_drag_bps=queue_drag_bps,
            unmodelled_residual_bps=unmodelled_residual_bps,
            latency_slip_drag_bps=latency_drag_bps + slippage_drag_bps,
            queue_position_drag_bps=queue_drag_bps,
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
                "slippage_drag_bps": float(summary.slippage_drag_bps),
                "latency_drag_bps": float(summary.latency_drag_bps),
                "fee_drag_bps": float(summary.fee_drag_bps),
                "queue_drag_bps": float(summary.queue_drag_bps),
                "unmodelled_residual_bps": float(summary.unmodelled_residual_bps),
                "latency_slip_drag_bps": float(summary.latency_slip_drag_bps),
                "queue_position_drag_bps": float(summary.queue_position_drag_bps),
            },
            "verdict": "FEASIBLE" if summary.phase5_simulated_realized_bps > Decimal("0.0") else "UNREALIZABLE_ALPHA",
        }
