"""Guard preventing access to the protected recent window for Alpaca historical SIP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from acash.core.domain.exceptions import DataContractError


class ProtectedWindowViolationError(DataContractError):
    """Raised when historical SIP query end timestamp falls within the protected recent window."""


class FifteenMinuteAccessGuard:
    """Enforces the 15-minute delay boundary for historical Alpaca Basic plan SIP queries.

    Alpaca Basic plan ($0) permits historical SIP data access only when the requested
    interval's end timestamp is at least 15 minutes old relative to current wall-clock time.
    Fails closed if the boundary is violated; never silently clamps the window.
    """

    DEFAULT_MINIMUM_AGE_MINUTES: int = 15

    def __init__(
        self,
        minimum_age_minutes: int = DEFAULT_MINIMUM_AGE_MINUTES,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        if minimum_age_minutes < 0:
            raise DataContractError(f"minimum_age_minutes must be non-negative, got {minimum_age_minutes}")
        self.minimum_age = timedelta(minutes=minimum_age_minutes)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def validate_requested_end(self, end_utc: datetime) -> None:
        """Validate that requested end_utc is safely older than qualification_now - 15 minutes.

        Args:
            end_utc: Requested upper timestamp boundary in UTC.

        Raises:
            DataContractError: If end_utc is not timezone-aware.
            ProtectedWindowViolationError: If end_utc is newer than now - 15 minutes.
        """
        if end_utc.tzinfo is None:
            raise DataContractError("Requested end_utc must be timezone-aware UTC.")
        normalized_end = end_utc.astimezone(timezone.utc)
        now_utc = self._clock().astimezone(timezone.utc)
        allowed_boundary = now_utc - self.minimum_age

        if normalized_end > allowed_boundary:
            raise ProtectedWindowViolationError(
                f"Requested end_utc ({normalized_end.isoformat()}) violates the 15-minute free SIP "
                f"access guard. Current time: {now_utc.isoformat()}, latest allowed end: "
                f"{allowed_boundary.isoformat()} (delta required >= {self.minimum_age})."
            )
