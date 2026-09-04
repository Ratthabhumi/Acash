"""Test Phase 17 Market State Vector, Price Structure, and Regime Uncertainty Invariants."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.strategy.schema import (
    ClassificationStatus,
    ConfidenceAssessment,
    DataProvenance,
    MarketDynamicsMeasurements,
    MarketStateVector,
    MicrostructureMeasurements,
    ParameterProvenance,
    PriceStructureMeasurements,
    RegimeClassificationEstimate,
    VolumeType,
)


def _build_valid_provenance(volume_type: VolumeType = VolumeType.TICK_VOLUME) -> DataProvenance:
    return DataProvenance(
        data_source="MT5_DEMO",
        symbol="EURUSD",
        timeframe="H1",
        timestamp_utc=datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc),
        lookback_bars=100,
        volume_type=volume_type,
    )


class TestMarketStateAndRegime:
    """Verify MarketStateVector continuous measurements and RegimeClassificationEstimate uncertainty."""

    def test_invariant_7_measurement_only_vector(self) -> None:
        """MarketStateVector strictly stores continuous numerical measurements and zero regime tags."""
        prov = _build_valid_provenance()
        price_struct = PriceStructureMeasurements(
            normalized_returns=(Decimal("0.0012"), Decimal("-0.0005"), Decimal("0.0034")),
            range_atr_ratio=Decimal("1.25"),
            body_range_ratio=Decimal("0.65"),
            wick_asymmetry=Decimal("0.10"),
            close_location=Decimal("0.75"),
            gap_ratio=Decimal("0.02"),
            is_range_expansion=False,
        )
        dynamics = MarketDynamicsMeasurements(
            trend_intensity=Decimal("0.82"),
            momentum_velocity=Decimal("0.45"),
            realized_volatility=Decimal("0.0075"),
            volume_zscore=Decimal("1.20"),
            benchmark_correlation=Decimal("0.65"),
        )
        micro = MicrostructureMeasurements(
            spread_bps=Decimal("1.5"),
            effective_spread_bps=Decimal("1.8"),
            execution_latency_ms=Decimal("45.0"),
        )
        state_vector = MarketStateVector(
            provenance=prov,
            price_structure=price_struct,
            market_dynamics=dynamics,
            microstructure=micro,
        )
        # Vector contains measurements only; no discrete regime labels embedded
        assert hasattr(state_vector, "price_structure")
        assert hasattr(state_vector, "market_dynamics")
        assert not hasattr(state_vector, "regime_label")

    def test_invariant_8_price_structure_geometry_bounds(self) -> None:
        """Body/range, wick asymmetry, and close location must obey strict mathematical bounds."""
        # body_range_ratio must be in [0.0, 1.0]
        with pytest.raises(DataContractError, match="body_range_ratio must be in"):
            PriceStructureMeasurements(
                normalized_returns=(Decimal("0.001"),),
                range_atr_ratio=Decimal("1.0"),
                body_range_ratio=Decimal("1.10"),
                wick_asymmetry=Decimal("0.0"),
                close_location=Decimal("0.5"),
                gap_ratio=Decimal("0.0"),
                is_range_expansion=False,
            )

        # wick_asymmetry must be in [-1.0, 1.0]
        with pytest.raises(DataContractError, match="wick_asymmetry must be in"):
            PriceStructureMeasurements(
                normalized_returns=(Decimal("0.001"),),
                range_atr_ratio=Decimal("1.0"),
                body_range_ratio=Decimal("0.5"),
                wick_asymmetry=Decimal("-1.50"),
                close_location=Decimal("0.5"),
                gap_ratio=Decimal("0.0"),
                is_range_expansion=False,
            )

        # close_location must be in [0.0, 1.0]
        with pytest.raises(DataContractError, match="close_location must be in"):
            PriceStructureMeasurements(
                normalized_returns=(Decimal("0.001"),),
                range_atr_ratio=Decimal("1.0"),
                body_range_ratio=Decimal("0.5"),
                wick_asymmetry=Decimal("0.0"),
                close_location=Decimal("-0.05"),
                gap_ratio=Decimal("0.0"),
                is_range_expansion=False,
            )

    def test_invariant_9_volume_provenance_distinct(self) -> None:
        """VolumeType distinguishes TICK_VOLUME vs REAL_VOLUME without conflation."""
        prov_tick = _build_valid_provenance(VolumeType.TICK_VOLUME)
        prov_real = _build_valid_provenance(VolumeType.REAL_VOLUME)
        assert prov_tick.volume_type == VolumeType.TICK_VOLUME
        assert prov_real.volume_type == VolumeType.REAL_VOLUME
        assert prov_tick.volume_type.value != prov_real.volume_type.value

    def test_invariant_10_confidence_assessment_provenance(self) -> None:
        """Confidence assessment requires explicit ThresholdProvenance (no ungrounded magic numbers)."""
        estimate = RegimeClassificationEstimate(
            status=ClassificationStatus.CLASSIFIED,
            confidence_score=Decimal("0.85"),
            confidence_assessment=ConfidenceAssessment.ACCEPTABLE,
            provisional_label="TREND_HIGH_VOL",
            threshold_provenance=ParameterProvenance.RESEARCH_DERIVED,
        )
        assert estimate.confidence_score == Decimal("0.85")
        assert estimate.confidence_assessment == ConfidenceAssessment.ACCEPTABLE
        assert estimate.threshold_provenance == ParameterProvenance.RESEARCH_DERIVED

    def test_invariant_11_uncertainty_fail_closed(self) -> None:
        """UNCLASSIFIED or INSUFFICIENT_EVIDENCE cannot carry an active provisional label."""
        with pytest.raises(DataContractError, match="Unclassified/insufficient regime status cannot carry active label"):
            RegimeClassificationEstimate(
                status=ClassificationStatus.INSUFFICIENT_EVIDENCE,
                confidence_score=Decimal("0.10"),
                confidence_assessment=ConfidenceAssessment.LOW,
                provisional_label="BULL_TREND",  # Invalid: cannot claim BULL_TREND when evidence is insufficient
                threshold_provenance=ParameterProvenance.PROVISIONAL,
            )
