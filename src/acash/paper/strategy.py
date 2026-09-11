"""ACASH Paper Trading — Infrastructure Test Strategy.

WARNING — GOVERNANCE NOTICE:
==============================
This strategy is an INFRASTRUCTURE TEST STRATEGY ONLY.

It is NOT:
    - HYP_003
    - A new hypothesis under MACRO-001
    - Research evidence
    - Statistical qualification evidence
    - A candidate for backtesting
    - Authorization for paper trading any research hypothesis

Its SOLE purpose is to exercise the Execution Track infrastructure:
    Signal → Risk → Order → Fill → Portfolio → Journal → Replay

Any trading results produced by this strategy are:
    - SIMULATED ONLY
    - LABELED "INFRASTRUCTURE_TEST" in all journal events
    - NOT admissible as ACASH research evidence
    - NOT a basis for any live trading decision

Strategy ID: INFRA-TEST-MOMENTUM-SYNTHETIC-001
Classification: INFRASTRUCTURE_TEST_STRATEGY_ONLY
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Signal types
# ---------------------------------------------------------------------------


class SignalDirection(str, Enum):
    """Signal direction emitted by a strategy."""

    FLAT = "FLAT"
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class StrategySignal:
    """Structured signal output from a strategy evaluation.

    INFRASTRUCTURE_TEST signals are clearly labeled and MUST NOT be used
    as ACASH research evidence.
    """

    strategy_id: str
    strategy_version: str
    evaluation_timestamp_utc: datetime
    symbol: str
    direction: SignalDirection
    target_quantity: Decimal
    signal_strength: Decimal  # [0.0, 1.0]
    decision_reason: str
    feature_snapshot: Dict[str, Any]
    market_event_reference: str  # e.g., bar timestamp ISO string
    config_hash: str
    is_infrastructure_test: bool = True  # Always True for this strategy

    def to_journal_payload(self) -> Dict[str, Any]:
        """Serialize to journal payload format."""
        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "evaluation_timestamp_utc": self.evaluation_timestamp_utc.isoformat(),
            "symbol": self.symbol,
            "direction": self.direction.value,
            "target_quantity": str(self.target_quantity),
            "signal_strength": str(self.signal_strength),
            "decision_reason": self.decision_reason,
            "feature_snapshot": self.feature_snapshot,
            "market_event_reference": self.market_event_reference,
            "config_hash": self.config_hash,
            "is_infrastructure_test": self.is_infrastructure_test,
            "GOVERNANCE_LABEL": "INFRASTRUCTURE_TEST_STRATEGY_ONLY",
        }


# ---------------------------------------------------------------------------
# InfrastructureTestStrategy
# ---------------------------------------------------------------------------


class InfrastructureTestStrategy:
    """Deterministic infrastructure test strategy.

    GOVERNANCE: INFRASTRUCTURE_TEST_STRATEGY_ONLY — NOT HYP_003, NOT research.

    Algorithm (purely for infrastructure exercise):
    - Uses a simple moving-average crossover on simulated price data.
    - SMA_FAST > SMA_SLOW → LONG (buy 1 unit)
    - SMA_FAST < SMA_SLOW → SHORT (sell 1 unit)
    - Indeterminate → FLAT

    Parameters are fixed and deterministic for replay consistency.

    The strategy is STATELESS between evaluations (no hidden accumulation).
    Input is a list of closing prices (most recent last).
    """

    STRATEGY_ID = "INFRA-TEST-MOMENTUM-SYNTHETIC-001"
    STRATEGY_VERSION = "1.0.0"
    GOVERNANCE_LABEL = "INFRASTRUCTURE_TEST_STRATEGY_ONLY"

    def __init__(
        self,
        fast_period: int = 3,
        slow_period: int = 5,
        trade_quantity: Decimal = Decimal("1.0"),
        symbol: str = "SYNTH-USD",
        config_hash: str = "0" * 64,
    ) -> None:
        if fast_period >= slow_period:
            raise ValueError(
                f"fast_period ({fast_period}) must be < slow_period ({slow_period})"
            )
        if fast_period < 2:
            raise ValueError("fast_period must be >= 2")
        if trade_quantity <= Decimal("0"):
            raise ValueError("trade_quantity must be > 0")

        self._fast = fast_period
        self._slow = slow_period
        self._quantity = trade_quantity
        self._symbol = symbol
        self._config_hash = config_hash

    @property
    def strategy_id(self) -> str:
        return self.STRATEGY_ID

    @property
    def strategy_version(self) -> str:
        return self.STRATEGY_VERSION

    def evaluate(
        self,
        closes: Sequence[Decimal],
        evaluation_time_utc: datetime,
        market_event_reference: str,
    ) -> Optional[StrategySignal]:
        """Evaluate the strategy on recent close prices.

        Args:
            closes: Recent closing prices, most recent LAST.
                    Must have len >= slow_period.
            evaluation_time_utc: UTC timestamp of evaluation.
            market_event_reference: Reference string for the triggering market event.

        Returns:
            StrategySignal if enough data, None if insufficient history.
        """
        if len(closes) < self._slow:
            return None

        recent = list(closes[-self._slow:])
        sma_fast = sum(recent[-self._fast:], Decimal("0")) / Decimal(self._fast)
        sma_slow = sum(recent, Decimal("0")) / Decimal(self._slow)

        features = {
            "sma_fast": str(sma_fast),
            "sma_slow": str(sma_slow),
            "fast_period": self._fast,
            "slow_period": self._slow,
            "input_bars": len(closes),
            "last_close": str(recent[-1]),
            "GOVERNANCE_LABEL": self.GOVERNANCE_LABEL,
        }

        if sma_fast > sma_slow:
            direction = SignalDirection.LONG
            strength = min(
                Decimal("1.0"),
                abs(sma_fast - sma_slow) / sma_slow if sma_slow != Decimal("0") else Decimal("0"),
            )
            reason = f"SMA({self._fast})={sma_fast:.6f} > SMA({self._slow})={sma_slow:.6f}"
        elif sma_fast < sma_slow:
            direction = SignalDirection.SHORT
            strength = min(
                Decimal("1.0"),
                abs(sma_fast - sma_slow) / sma_slow if sma_slow != Decimal("0") else Decimal("0"),
            )
            reason = f"SMA({self._fast})={sma_fast:.6f} < SMA({self._slow})={sma_slow:.6f}"
        else:
            direction = SignalDirection.FLAT
            strength = Decimal("0.0")
            reason = "SMA crossover indeterminate"

        return StrategySignal(
            strategy_id=self.STRATEGY_ID,
            strategy_version=self.STRATEGY_VERSION,
            evaluation_timestamp_utc=evaluation_time_utc,
            symbol=self._symbol,
            direction=direction,
            target_quantity=self._quantity if direction != SignalDirection.FLAT else Decimal("0"),
            signal_strength=strength,
            decision_reason=f"[INFRA-TEST] {reason}",
            feature_snapshot=features,
            market_event_reference=market_event_reference,
            config_hash=self._config_hash,
            is_infrastructure_test=True,
        )
