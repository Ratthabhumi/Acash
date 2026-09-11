"""ACASH Paper Trading — Bounded Graceful Shutdown Handler (E3.6 / WS5).

DESIGN REFERENCE: E3.6-DESIGN.md §16 (D16.1 / D16.2 / D16.3).

The run loop has no signal handling today; a default ``docker stop`` sends
SIGTERM and the process is killed with the session manifest unsealed. This
module installs a *bounded* handler:

- First SIGTERM/SIGINT requests a graceful stop (the run loop breaks, then
  ``disconnect()`` + ``stop()`` seal the manifest).
- A second signal forces an immediate non-zero exit (fail-closed escalation).
- If the graceful path exceeds ``grace_seconds`` (default 10s) the process
  forces a non-zero exit: an unsealed manifest after the grace bound is never
  silently accepted (D16.1).

GOVERNANCE (E3.6):
==================
- This is EXECUTION/PAPER INFRASTRUCTURE ONLY.
- Every ``docker stop`` during an OPEN window closes a runtime segment and is
  a runtime transition (D16.2); recording that transition is the window
  authoring step's job (see ``window.py``), not this handler's.
- No silent fallback: exceeding the grace bound exits non-zero rather than
  pretending the seal happened.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import FrameType
from typing import Any, List, Optional

from acash.core.domain.exceptions import DataContractError


@dataclass(frozen=True)
class GracefulStopOutcome:
    """Structured outcome of a bounded graceful stop (never a profitability claim)."""

    requested: bool
    completed_within_grace: bool
    forced_exit: bool
    shutdown_requested_at_utc: Optional[datetime]
    grace_deadline_utc: Optional[datetime]
    resolved_at_utc: Optional[datetime]


class BoundedGracefulShutdown:
    """Bounded SIGTERM/SIGINT handler with a hard fail-closed grace bound.

    Usage::

        ctrl = BoundedGracefulShutdown(grace_seconds=10.0)
        try:
            ctrl.install()
            while not ctrl.shutdown_requested:
                supervisor.step_once()
        finally:
            ctrl.restore()
        supervisor.disconnect()
        manifest = runner.stop()
        exit_code = ctrl.resolve()        # 0 if graceful within grace, 1 otherwise

    Thread-safe: signal handlers may fire on the main thread at any time, so
    the request state is guarded by a lock.
    """

    DEFAULT_GRACE_SECONDS = 10.0
    FORCED_EXIT_CODE = 1

    def __init__(
        self,
        grace_seconds: float = DEFAULT_GRACE_SECONDS,
        forced_exit_code: int = FORCED_EXIT_CODE,
        signals: Optional[List[int]] = None,
    ) -> None:
        if grace_seconds <= 0:
            raise DataContractError(
                "BoundedGracefulShutdown: grace_seconds must be > 0 "
                f"(got {grace_seconds!r}); no silent zero-grace fallback."
            )
        self._grace_seconds = float(grace_seconds)
        self._forced_exit_code = int(forced_exit_code)
        self._signals: List[int] = list(signals or [signal.SIGINT, signal.SIGTERM])
        self._lock = threading.Lock()
        self._shutdown_requested_at_utc: Optional[datetime] = None
        self._saved_dispositions: List[Any] = []
        self._installed = False

    # ------------------------------------------------------------------
    # Install / restore
    # ------------------------------------------------------------------

    @property
    def installed(self) -> bool:
        return self._installed

    @property
    def grace_seconds(self) -> float:
        return self._grace_seconds

    def install(self) -> None:
        """Register signal handlers. Safe to call at most once per instance."""
        with self._lock:
            if self._installed:
                raise DataContractError(
                    "BoundedGracefulShutdown: handler already installed."
                )
            dispositions: List[Any] = []
            for signum in self._signals:
                previous = signal.getsignal(signum)
                if previous == signal.SIG_IGN:
                    dispositions.append(previous)
                    continue
                handler = self._make_handler(signum)
                signal.signal(signum, handler)
                dispositions.append(handler)
            self._saved_dispositions = dispositions
            self._installed = True

    def restore(self) -> None:
        """Restore previous signal dispositions."""
        with self._lock:
            if not self._installed:
                return
            for signum, dispo in zip(self._signals, self._saved_dispositions):
                try:
                    signal.signal(signum, dispo)
                except (ValueError, OSError):
                    pass
            self._installed = False

    def _make_handler(self, signum: int) -> Any:
        def _handle(_signum: int, _frame: Optional[FrameType]) -> None:
            self.request_shutdown(signum)
        return _handle

    # ------------------------------------------------------------------
    # Request state
    # ------------------------------------------------------------------

    @property
    def shutdown_requested(self) -> bool:
        with self._lock:
            return self._shutdown_requested_at_utc is not None

    @property
    def shutdown_requested_at_utc(self) -> Optional[datetime]:
        with self._lock:
            return self._shutdown_requested_at_utc

    @property
    def grace_deadline_utc(self) -> Optional[datetime]:
        requested = self.shutdown_requested_at_utc
        if requested is None:
            return None
        return requested + timedelta(seconds=self._grace_seconds)

    def request_shutdown(self, signum: Optional[int] = None) -> None:
        """Request a graceful stop.

        First invocation records the request time. A *second* invocation
        escalates immediately: the graceful window is non-renegotiable, so a
        repeated signal forces a fail-closed non-zero exit.
        """
        with self._lock:
            if self._shutdown_requested_at_utc is None:
                self._shutdown_requested_at_utc = datetime.now(timezone.utc)
                return
            # Second signal → forced escalation (fail-closed).
            print(
                "BoundedGracefulShutdown: second signal during graceful stop; "
                f"forcibly exiting with code {self._forced_exit_code}.",
                file=sys.stderr,
            )
            os._exit(self._forced_exit_code)

    def forced(self) -> bool:
        """True when the graceful window has been exhausted (fail-closed)."""
        deadline = self.grace_deadline_utc
        if deadline is None:
            return False
        return datetime.now(timezone.utc) >= deadline

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(self) -> int:
        """Return the exit code for the completed run.

        0  — no shutdown was requested, or the graceful path completed within
             the grace window with the manifest sealed.
        1  — a shutdown was requested but the grace window was exceeded
             before the caller finished (journal may be unsealed) — fail-closed.

        Resolution returns 1 when ``forced()`` is true at call time. The caller
        must have sealed the manifest *before* calling ``resolve()``; this
        handler never pretends a seal happened.
        """
        if not self.shutdown_requested and not self.forced():
            return 0
        if self.forced():
            print(
                "BoundedGracefulShutdown: graceful window exceeded; "
                "run loop did not seal within the grace bound. "
                "Exiting non-zero (fail-closed).",
                file=sys.stderr,
            )
            return self._forced_exit_code
        return 0

    def outcome(self, resolved_at_utc: Optional[datetime] = None) -> GracefulStopOutcome:
        requested = self.shutdown_requested_at_utc
        deadline = self.grace_deadline_utc
        res_at = resolved_at_utc or datetime.now(timezone.utc)
        return GracefulStopOutcome(
            requested=requested is not None,
            completed_within_grace=(
                requested is not None and deadline is not None and res_at < deadline
            ),
            forced_exit=(requested is not None and self.forced()),
            shutdown_requested_at_utc=requested,
            grace_deadline_utc=deadline,
            resolved_at_utc=res_at,
        )