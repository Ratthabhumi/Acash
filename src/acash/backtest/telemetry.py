"""Reality Gap Telemetry and Attribution Engine (Phase 5).

Measures and decomposes the systematic divergence between Phase 4 Analytical Edge
and Phase 5 Simulated Event-Driven Realized Edge:
Reality Gap = Edge_Phase4_Analytical - Edge_Phase5_Simulated = Spread Drag + Slippage Drag + Latency Drag + Fee Drag + Maker Adverse Selection Drag + Unmodelled Residual

Implements a disjoint non-overlapping reference-price decomposition:
- Latency Drag: Mid-to-mid price drift during transmission (Decision Mid -> Match Arrival Mid)
- Spread Drag: Half-spread crossing cost (Match Arrival Mid -> Touch Price for Taker)
- Slippage Drag: Book depth consumption / price impact beyond touch (Touch Price -> Fill Price for Taker)
- Fee Drag: Exchange, broker, and clearing transaction fees
- Maker Adverse Selection Drag: Post-arrival market drift conditional on maker fill (Arrival Mid -> Fill Mid for Maker)
- Unmodelled Residual: Mathematical residual gap (Alpha analytical formula assumption mismatch)
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
        maker_adverse_selection_drag_bps: Optional[Decimal] = None,
        queue_drag_bps: Optional[Decimal] = None,
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
        
        eff_maker_adverse = Decimal("0.0")
        if maker_adverse_selection_drag_bps is not None:
            eff_maker_adverse = maker_adverse_selection_drag_bps
        elif queue_drag_bps is not None:
            eff_maker_adverse = queue_drag_bps
        elif queue_position_drag_bps is not None:
            eff_maker_adverse = queue_position_drag_bps

        accounted = spread_drag_bps + slippage_drag_bps + latency_drag_bps + fee_drag_bps + eff_maker_adverse
        unmodelled_residual = reality_gap_bps - accounted

        return RealityGapSummary(
            phase4_analytical_edge_bps=phase4_analytical_edge_bps,
            phase5_simulated_realized_bps=phase5_simulated_realized_bps,
            reality_gap_bps=reality_gap_bps,
            spread_drag_bps=spread_drag_bps,
            slippage_drag_bps=slippage_drag_bps,
            latency_drag_bps=latency_drag_bps,
            fee_drag_bps=fee_drag_bps,
            maker_adverse_selection_drag_bps=eff_maker_adverse,
            unmodelled_residual_bps=unmodelled_residual,
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
                maker_adverse_selection_drag_bps=Decimal("0.0"),
                unmodelled_residual_bps=reality_gap_bps,
            )

        # 1. Empirical Fee Drag (actual fees incurred relative to initial capital)
        if total_fees_paid is not None:
            fee_sum = total_fees_paid
        else:
            fee_sum = sum(
                (Decimal(str(getattr(f, "fee_paid", f.get("fee_paid", 0) if isinstance(f, dict) else 0))) for f in fills),
                Decimal("0.0"),
            )
        fee_drag_bps = (fee_sum / initial_cash) * Decimal("10000.0")

        # 2. Empirical Latency Drag (transmission adverse mid-price drift: Decision Mid -> Match Mid)
        latency_cost = Decimal("0.0")
        for f in fills:
            qty = Decimal(str(getattr(f, "fill_qty", f.get("fill_qty", 0) if isinstance(f, dict) else 0)))
            side = str(getattr(f, "side", f.get("side", "") if isinstance(f, dict) else "")).upper()
            side_sign = Decimal("1.0") if side == "BUY" else Decimal("-1.0")

            arr_mid = getattr(f, "arrival_mid_price", f.get("arrival_mid_price", None) if isinstance(f, dict) else None)
            match_mid = getattr(f, "match_mid_price", f.get("match_mid_price", None) if isinstance(f, dict) else None)

            if arr_mid is not None and match_mid is not None:
                # Adverse mid drift: BUY suffers when mid rises; SELL suffers when mid falls
                adverse_drift = side_sign * (Decimal(str(match_mid)) - Decimal(str(arr_mid)))
                if adverse_drift > Decimal("0.0"):
                    latency_cost += qty * adverse_drift
            else:
                # Fallback to pre-calculated latency_drift_bps if explicit mid benchmarks not attached
                drift_bps = Decimal(str(getattr(f, "latency_drift_bps", f.get("latency_drift_bps", 0) if isinstance(f, dict) else 0)))
                px = Decimal(str(getattr(f, "fill_price", f.get("fill_price", 0) if isinstance(f, dict) else 0)))
                if drift_bps > Decimal("0.0"):
                    latency_cost += (qty * px) * (drift_bps / Decimal("10000.0"))

        latency_drag_bps = (latency_cost / initial_cash) * Decimal("10000.0")

        # 3. Empirical Spread Drag (half-spread crossing cost for taker fills: Match Mid -> Touch Price)
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

        # 4. Empirical Slippage Drag (depth sweep / price impact beyond touch: Touch Price -> Fill Price)
        slippage_cost = Decimal("0.0")
        for f in fills:
            qty = Decimal(str(getattr(f, "fill_qty", f.get("fill_qty", 0) if isinstance(f, dict) else 0)))
            fill_px = Decimal(str(getattr(f, "fill_price", f.get("fill_price", 0) if isinstance(f, dict) else 0)))
            touch_val = getattr(f, "touch_price", f.get("touch_price", None) if isinstance(f, dict) else None)
            side = str(getattr(f, "side", f.get("side", "") if isinstance(f, dict) else "")).upper()

            if touch_val is not None:
                touch_px = Decimal(str(touch_val))
                # Depth slippage beyond touch: BUY pays fill > touch; SELL receives fill < touch
                excess_slip = (fill_px - touch_px) if side == "BUY" else (touch_px - fill_px)
                if excess_slip > Decimal("0.0"):
                    slippage_cost += qty * excess_slip
            else:
                # Fallback to slippage_incurred_bps
                slip_bps = Decimal(str(getattr(f, "slippage_incurred_bps", f.get("slippage_incurred_bps", 0) if isinstance(f, dict) else 0)))
                if slip_bps > Decimal("0.0"):
                    slippage_cost += (qty * fill_px) * (slip_bps / Decimal("10000.0"))

        slippage_drag_bps = (slippage_cost / initial_cash) * Decimal("10000.0")

        # 5. Empirical Maker Adverse Selection Drag (post-arrival market drift: Arrival Mid -> Fill Mid while resting)
        maker_adverse_cost = Decimal("0.0")
        for f in fills:
            liq_type = str(getattr(f, "liquidity_type", f.get("liquidity_type", "") if isinstance(f, dict) else ""))
            if "MAKER" in liq_type.upper():
                qty = Decimal(str(getattr(f, "fill_qty", f.get("fill_qty", 0) if isinstance(f, dict) else 0)))
                side = str(getattr(f, "side", f.get("side", "") if isinstance(f, dict) else "")).upper()
                side_sign = Decimal("1.0") if side == "BUY" else Decimal("-1.0")

                arr_mid = getattr(f, "arrival_mid_price", f.get("arrival_mid_price", None) if isinstance(f, dict) else None)
                if arr_mid is None:
                    arr_mid = getattr(f, "arrival_price", f.get("arrival_price", None) if isinstance(f, dict) else None)

                bid_val = getattr(f, "bid_at_fill", f.get("bid_at_fill", None) if isinstance(f, dict) else None)
                ask_val = getattr(f, "ask_at_fill", f.get("ask_at_fill", None) if isinstance(f, dict) else None)

                fill_mid: Optional[Decimal] = None
                if bid_val is not None and ask_val is not None:
                    fill_mid = (Decimal(str(bid_val)) + Decimal(str(ask_val))) / Decimal("2.0")

                if arr_mid is not None and fill_mid is not None:
                    # Normalized adverse move:
                    # BUY maker suffers when mid drops (M_arrival - M_fill > 0)
                    # SELL maker suffers when mid rises (M_fill - M_arrival > 0)
                    adverse_queue_move = -side_sign * (fill_mid - Decimal(str(arr_mid)))
                    if adverse_queue_move > Decimal("0.0"):
                        maker_adverse_cost += qty * adverse_queue_move
                elif arr_mid is not None:
                    # Fallback using fill_price if quotes at fill are not available
                    fill_px = Decimal(str(getattr(f, "fill_price", f.get("fill_price", 0) if isinstance(f, dict) else 0)))
                    adverse_drift = -side_sign * (fill_px - Decimal(str(arr_mid)))
                    if adverse_drift > Decimal("0.0"):
                        maker_adverse_cost += qty * adverse_drift

        maker_adverse_selection_drag_bps = (maker_adverse_cost / initial_cash) * Decimal("10000.0")

        # 6. Unmodelled Residual Gap (pure model mismatch / alpha assumption divergence)
        accounted = fee_drag_bps + slippage_drag_bps + latency_drag_bps + spread_drag_bps + maker_adverse_selection_drag_bps
        unmodelled_residual_bps = reality_gap_bps - accounted

        return RealityGapSummary(
            phase4_analytical_edge_bps=phase4_analytical_edge_bps,
            phase5_simulated_realized_bps=phase5_simulated_realized_bps,
            reality_gap_bps=reality_gap_bps,
            spread_drag_bps=spread_drag_bps,
            slippage_drag_bps=slippage_drag_bps,
            latency_drag_bps=latency_drag_bps,
            fee_drag_bps=fee_drag_bps,
            maker_adverse_selection_drag_bps=maker_adverse_selection_drag_bps,
            unmodelled_residual_bps=unmodelled_residual_bps,
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
                "maker_adverse_selection_drag_bps": float(summary.maker_adverse_selection_drag_bps),
                "unmodelled_residual_bps": float(summary.unmodelled_residual_bps),
            },
            "verdict": "FEASIBLE" if summary.phase5_simulated_realized_bps > Decimal("0.0") else "UNREALIZABLE_ALPHA",
        }
