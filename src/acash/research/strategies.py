"""Transparent Baseline Research Strategies (Phase 4).

Strictly enforces:
- Research evaluation vehicles ONLY (used to benchmark feature information value).
- Pure mathematical signal generation without execution, routing, or broker logic.
- Baseline 1: Microstructure Imbalance & Micro-Price Skew.
- Baseline 2: Session VWAP Mean Reversion (Band Rejection).
- Baseline 3: Multi-Horizon Time-Series Momentum (TSMOM).
"""

from decimal import Decimal
from typing import List, Optional, Sequence, Union
import numpy as np

from acash.data.features.engine import to_decimal18


class MicrostructureImbalanceStrategy:
    """Baseline Strategy 1: Microstructure Imbalance & Micro-Price Alpha.

    Signal = OBI_TopN + Skew(MicroPrice - MidPrice)
    """

    def __init__(self, obi_threshold: Decimal = Decimal("0.20")) -> None:
        self.obi_threshold = obi_threshold

    def generate_signals(
        self,
        obi_values: Sequence[Decimal],
        micro_prices: Sequence[Optional[Decimal]],
        mid_prices: Sequence[Decimal],
    ) -> List[Decimal]:
        """Generate continuous directional signals in range [-1.0, 1.0]."""
        n = len(obi_values)
        signals: List[Decimal] = []

        for i in range(n):
            obi = obi_values[i]
            mp = micro_prices[i]
            mid = mid_prices[i]

            sig = Decimal("0")
            if abs(obi) >= self.obi_threshold and mp is not None and mid > Decimal("0"):
                # Micro-price skew normalized by mid
                skew = (mp - mid) / mid
                sig = (obi * Decimal("0.5")) + (skew * Decimal("500.0"))
                # Clamp between -1.0 and 1.0
                sig = max(Decimal("-1.0"), min(Decimal("1.0"), sig))

            signals.append(to_decimal18(sig) or Decimal("0"))

        return signals



class SessionVwapMeanReversionStrategy:
    """Baseline Strategy 2: Session VWAP Mean Reversion.

    Signal = -1.0 if Close > VWAP + 2*Std (Overbought)
             +1.0 if Close < VWAP - 2*Std (Oversold)
              0.0 otherwise
    """

    def __init__(self, num_std: Decimal = Decimal("2.0")) -> None:
        self.num_std = num_std

    def generate_signals(
        self,
        closes: Sequence[Decimal],
        vwaps: Sequence[Optional[Decimal]],
        vwap_stds: Sequence[Optional[Decimal]],
    ) -> List[Decimal]:
        """Generate mean-reversion signals in range [-1.0, 1.0]."""
        n = len(closes)
        signals: List[Decimal] = []

        for i in range(n):
            c = closes[i]
            v = vwaps[i]
            s = vwap_stds[i]

            sig = Decimal("0")
            if v is not None and s is not None and s > Decimal("0"):
                upper_band = v + (self.num_std * s)
                lower_band = v - (self.num_std * s)

                if c >= upper_band:
                    sig = Decimal("-1.0")  # Expect downward reversion
                elif c <= lower_band:
                    sig = Decimal("1.0")   # Expect upward reversion

            signals.append(to_decimal18(sig) or Decimal("0"))

        return signals


class MultiHorizonMomentumStrategy:
    """Baseline Strategy 3: Multi-Horizon Time-Series Momentum (TSMOM).

    Signal = Sign(Return_lookback)
    """

    def __init__(self, lookback_bars: int = 5) -> None:
        self.lookback_bars = lookback_bars

    def generate_signals(
        self,
        closes: Sequence[Decimal],
    ) -> List[Decimal]:
        """Generate trend-following signals based on past return sign."""
        n = len(closes)
        signals: List[Decimal] = []

        for i in range(n):
            if i < self.lookback_bars:
                signals.append(Decimal("0"))
                continue

            c_now = closes[i]
            c_past = closes[i - self.lookback_bars]

            if c_past > Decimal("0"):
                ret = (c_now - c_past) / c_past
                if ret > Decimal("0.0001"):
                    sig = Decimal("1.0")
                elif ret < Decimal("-0.0001"):
                    sig = Decimal("-1.0")
                else:
                    sig = Decimal("0")
            else:
                sig = Decimal("0")

            signals.append(to_decimal18(sig) or Decimal("0"))

        return signals
