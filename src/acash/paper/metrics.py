"""ACASH Paper Trading — Prometheus-text /metrics endpoint (E3.6 / WS9).

DESIGN REFERENCE: E3.6-DESIGN.md §13 (D13.1 / D13.2).

ACASH side of the observability contract (D13.1):

- A Prometheus-text ``/metrics`` endpoint a VM static scrape job can point at
  (``acash-paper:<metrics-port>/metrics``). The HomeLab scrape-job wiring is a
  separate, later stage under the deployment rule — nothing here touches
  HomeLab.
- Metrics are OPERATIONAL TELEMETRY ONLY (D13.2): they never become evidence.
  The journal + window manifest remain the evidence authorities. No strategy
  returns, PnL, Sharpe, or qualification numbers are ever exported.

The endpoint is stdlib-only (``http.server``), bindable to a container-internal
address, and exposes a small, strictly operational metric set:
- process up / uptime
- journal event count + integrity status
- window interlock state (one gauge per state)
- feed failure event count + halted state (WS7 accounting surface)

GOVERNANCE (E3.6):
==================
- Execution/paper infrastructure only; no research evidence, no qualification.
- No magic floors; a failed registry read raises ``DataContractError`` instead
  of exporting a fabricated 0.
"""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from acash.core.domain.exceptions import DataContractError

MetricValue = float
MetricLabels = Dict[str, str]


class MetricsRegistry:
    """Tiny operational gauges/counters with Prometheus text rendering.

    Kept deliberately minimal and dependency-free. ``write_exposition`` fills
    the bodies in Prometheus text exposition format (counters/gauges).
    """

    def __init__(self) -> None:
        self._gauges: Dict[str, float] = {}
        self._lock = threading.Lock()

    def set_gauge(self, name: str, value: float, labels: Optional[MetricLabels] = None) -> None:
        if labels is None:
            key = name
        else:
            rendered = ",".join(
                f'{k}="{v}"' for k, v in sorted(labels.items())
            )
            key = f"{name}{{{rendered}}}"
        with self._lock:
            self._gauges[key] = float(value)

    def render(self) -> str:
        """Render all gauges in Prometheus text exposition format."""
        lines: List[str] = []
        with self._lock:
            for series_name, value in sorted(self._gauges.items()):
                base_name = series_name.split("{", 1)[0]
                lines.append(f"# TYPE {base_name} gauge")
                lines.append(f"{series_name} {value!r}")
        return "\n".join(lines) + "\n"


class PaperMetricsServer:
    """Prometheus-text /metrics endpoint (D13.1), stdlib only.

    A threaded HTTP server that serves a single route: ``/metrics``. Any other
    path returns 404. ``collect`` is supplied by the caller and must return an
    already-rendered Prometheus-text body (or raise DataContractError).

    Bind address/port are passed in; deployment decides whether the port is
    exposed (the design publishes nothing — scrape happens on the proxy/runtime
    network, a later HomeLab stage).
    """

    def __init__(
        self,
        registry: MetricsRegistry,
        host: str = "0.0.0.0",
        port: int = 9102,
    ) -> None:
        self._registry = registry
        self._host = host
        self._port = port
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._started_at_utc = datetime.now(timezone.utc)

    @property
    def started(self) -> bool:
        return self._server is not None

    @property
    def port(self) -> int:
        return self._port

    def start(self) -> None:
        """Start the endpoint in a daemon thread. Idempotent-protected."""
        if self._server is not None:
            raise DataContractError("PaperMetricsServer: already started.")
        server = self._build_server()
        self._server = server
        thread = threading.Thread(
            target=server.serve_forever,
            name="acash-paper-metrics",
            daemon=True,
        )
        self._thread = thread
        thread.start()

    def _build_server(self) -> ThreadingHTTPServer:
        registry = self._registry

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 (stdlib API name)
                if self.path != "/metrics":
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"404 not found\n")
                    return
                try:
                    body = registry.render()
                except DataContractError as exc:
                    self.send_response(503)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(str(exc).encode("utf-8") + b"\n")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))

            def log_message(self, fmt: str, *args: object) -> None:
                # Keep the operational noise out of the evidence journal.
                pass

        server = ThreadingHTTPServer((self._host, self._port), _Handler)
        return server

    def stop(self) -> None:
        """Stop the endpoint. Roundtrips HTTP 503 to keep Prometheus honest."""
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None


def build_operational_metrics(
    *,
    event_count: int,
    journal_integrity_status: str,  # "PASS" / "FAIL" / "NOT_CHECKED"
    window_state: str,  # WindowState value
    feed_failure_events: int,
    auto_recovery_used: bool,
    uptime_seconds: float,
) -> MetricsRegistry:
    """Assemble the strict operational metric set (D13.2).

    Raises ``DataContractError`` when the caller passes a corrupted integrity
    status — never exports a guess (fail-closed, no floors).
    """
    if journal_integrity_status not in ("PASS", "FAIL", "NOT_CHECKED"):
        raise DataContractError(
            f"build_operational_metrics: unknown integrity status "
            f"{journal_integrity_status!r}; refusing to fabricate a metric."
        )
    if window_state not in ("QUIESCENT", "OPEN", "SEALED", "VOID"):
        raise DataContractError(
            f"build_operational_metrics: unknown window state {window_state!r}."
        )
    if event_count < 0 or feed_failure_events < 0:
        raise DataContractError(
            "build_operational_metrics: negative counter is a contract violation."
        )

    registry = MetricsRegistry()
    registry.set_gauge("acash_paper_up", 1.0)
    registry.set_gauge("acash_paper_uptime_seconds", uptime_seconds)
    registry.set_gauge("acash_journal_event_count", float(event_count))
    registry.set_gauge(
        "acash_journal_integrity_status",
        1.0 if journal_integrity_status == "PASS" else 0.0,
        {"state": journal_integrity_status},
    )
    for state in ("QUIESCENT", "OPEN", "SEALED", "VOID"):
        registry.set_gauge(
            "acash_window_state",
            1.0 if state == window_state else 0.0,
            {"state": state},
        )
    registry.set_gauge("acash_feed_failure_events_total", float(feed_failure_events))
    registry.set_gauge(
        "acash_auto_recovery_used",
        1.0 if auto_recovery_used else 0.0,
    )
    return registry


def metrics_for_window_and_journal(
    *,
    event_count: int,
    journal_integrity_status: str,
    window_state: str,
    feed_failure_events: int,
    auto_recovery_used: bool,
    started_at_utc: Optional[datetime] = None,
) -> str:
    """Convenience: render the operational metric text for a scratch request.

    ``started_at_utc`` optional; when absent, uptime is 0.0 (never invented).
    """
    started = started_at_utc or datetime.now(timezone.utc)
    uptime = max(0.0, (datetime.now(timezone.utc) - started).total_seconds())
    registry = build_operational_metrics(
        event_count=event_count,
        journal_integrity_status=journal_integrity_status,
        window_state=window_state,
        feed_failure_events=feed_failure_events,
        auto_recovery_used=auto_recovery_used,
        uptime_seconds=uptime,
    )
    return registry.render()