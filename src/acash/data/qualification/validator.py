"""Data integrity and microstructure sanity validator for historical equity minute bars."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Sequence

from acash.data.qualification.models import (
    HistoricalSipBar,
    QualityFinding,
    QualityRuleCode,
    QualitySeverity,
)
from acash.data.qualification.session import (
    RthSessionBounds,
    VerifiedSessionSchedule,
)


class HistoricalBarValidator:
    """Validates temporal monotonicity, OHLC invariants, volume, and session alignment."""

    def __init__(self, check_rth_hours: bool = True) -> None:
        self.check_rth_hours = check_rth_hours

    def validate_bars(
        self,
        bars: Sequence[HistoricalSipBar],
        verified_schedules: Optional[Dict[date, VerifiedSessionSchedule]] = None,
    ) -> List[QualityFinding]:
        """Validate a sequence of historical bars and collect quality findings.

        Args:
            bars: Sequence of historical bars sorted by timestamp.
            verified_schedules: Optional mapping of date -> VerifiedSessionSchedule.
                                If None or missing for a date, CALENDAR_AUTHORITY_UNVERIFIED
                                is recorded instead of falsely flagging missing bars.

        Returns:
            List of QualityFinding records.
        """
        findings: List[QualityFinding] = []
        if not bars:
            return findings

        seen_timestamps: set[datetime] = set()
        bars_by_date: Dict[date, List[HistoricalSipBar]] = {}

        prev_bar: Optional[HistoricalSipBar] = None
        for idx, bar in enumerate(bars):
            t = bar.timestamp_utc
            d = RthSessionBounds.to_ny_time(t).date()
            bars_by_date.setdefault(d, []).append(bar)

            # 1. Monotonicity & Duplicates
            if t in seen_timestamps:
                findings.append(
                    QualityFinding(
                        rule=QualityRuleCode.DUPLICATE_TIMESTAMP,
                        severity=QualitySeverity.ERROR,
                        message=f"Duplicate bar timestamp observed at row {idx}: {t.isoformat()}.",
                        timestamp_utc=t,
                        details={"row_index": idx},
                    )
                )
            seen_timestamps.add(t)

            if prev_bar is not None:
                if t < prev_bar.timestamp_utc:
                    findings.append(
                        QualityFinding(
                            rule=QualityRuleCode.NON_MONOTONIC_TIMESTAMP,
                            severity=QualitySeverity.ERROR,
                            message=(
                                f"Non-monotonic timestamp at row {idx}: {t.isoformat()} preceded by "
                                f"{prev_bar.timestamp_utc.isoformat()}."
                            ),
                            timestamp_utc=t,
                            details={"row_index": idx},
                        )
                    )

            # 2. Structural OHLC invariants
            max_body = max(bar.open, bar.close)
            min_body = min(bar.open, bar.close)
            if bar.high < max_body or bar.low > min_body or bar.high < bar.low:
                findings.append(
                    QualityFinding(
                        rule=QualityRuleCode.INVALID_OHLC_BOUNDS,
                        severity=QualitySeverity.ERROR,
                        message=(
                            f"Invalid OHLC bounds at {t.isoformat()}: open={bar.open}, "
                            f"high={bar.high}, low={bar.low}, close={bar.close}."
                        ),
                        timestamp_utc=t,
                        details={"open": str(bar.open), "high": str(bar.high), "low": str(bar.low), "close": str(bar.close)},
                    )
                )

            # 3. Prices and Volume validity
            if bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0:
                findings.append(
                    QualityFinding(
                        rule=QualityRuleCode.INVALID_PRICE,
                        severity=QualitySeverity.ERROR,
                        message=f"Non-positive price observed at {t.isoformat()}.",
                        timestamp_utc=t,
                    )
                )
            if bar.volume < 0:
                findings.append(
                    QualityFinding(
                        rule=QualityRuleCode.NEGATIVE_VOLUME,
                        severity=QualitySeverity.ERROR,
                        message=f"Negative volume ({bar.volume}) observed at {t.isoformat()}.",
                        timestamp_utc=t,
                    )
                )

            # 4. RTH hours check
            if self.check_rth_hours:
                rth_finding = RthSessionBounds.validate_bar_intraday_hours(bar)
                if rth_finding is not None:
                    findings.append(rth_finding)

            prev_bar = bar

        # 5. Session completeness checks per trading date
        schedules = verified_schedules or {}
        for session_date, session_bars in sorted(bars_by_date.items()):
            sched = schedules.get(session_date)
            completeness_findings = RthSessionBounds.evaluate_session_completeness(
                session_date=session_date,
                bars=session_bars,
                verified_schedule=sched,
            )
            findings.extend(completeness_findings)

        return findings

    @staticmethod
    def has_blocking_errors(findings: Sequence[QualityFinding]) -> bool:
        """Return True if any finding has ERROR severity."""
        return any(f.severity == QualitySeverity.ERROR for f in findings)
