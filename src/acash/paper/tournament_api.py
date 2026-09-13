"""ACASH Paper Trading — Read-Only Shadow Tournament HTTP API Server.

GOVERNANCE:
- Strictly READ-ONLY. Zero mutation endpoints (POST/PUT/PATCH/DELETE rejected with 405).
- No trading credentials required.
- Serves /api/shadow/status, /healthz, and Prometheus /metrics.
"""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from acash.paper.metrics import MetricsRegistry
from acash.paper.tournament import ShadowTournamentSupervisor

logger = logging.getLogger(__name__)


class ShadowApiHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Shadow Tournament read-only API."""

    supervisor: ShadowTournamentSupervisor
    metrics_registry: Optional[MetricsRegistry] = None

    def log_message(self, format: str, *args: object) -> None:
        """Suppress standard stderr request logging unless error."""
        if args and len(args) > 1:
            try:
                status_code = int(str(args[1]))
                if status_code >= 400:
                    super().log_message(format, *args)
            except (ValueError, TypeError):
                super().log_message(format, *args)

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests strictly."""
        path = self.path.split("?")[0].rstrip("/")
        if not path:
            path = "/"

        if path == "/api/shadow/status":
            self._handle_status()
        elif path == "/healthz":
            self._handle_healthz()
        elif path == "/metrics":
            self._handle_metrics()
        else:
            self._send_response(404, {"error": "Not Found", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802
        """Reject all mutation attempts with 405 Method Not Allowed."""
        self._send_response(
            405,
            {
                "error": "Method Not Allowed",
                "message": "ACASH Shadow Tournament API is strictly read-only.",
                "NO_REAL_ORDERS": True,
            },
        )

    def do_PUT(self) -> None:  # noqa: N802
        self.do_POST()

    def do_DELETE(self) -> None:  # noqa: N802
        self.do_POST()

    def do_PATCH(self) -> None:  # noqa: N802
        self.do_POST()

    def _handle_status(self) -> None:
        try:
            status_data = self.supervisor.to_dict()
            body = json.dumps(status_data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            logger.error("Error generating tournament status JSON: %s", exc)
            self._send_response(500, {"error": "Internal Server Error", "details": str(exc)})

    def _handle_healthz(self) -> None:
        health_data = {
            "status": "ok",
            "overall_status": self.supervisor.overall_status,
            "feed_health": self.supervisor.feed_health,
            "tournament_id": self.supervisor.tournament_id,
            "NO_REAL_ORDERS": True,
            "CANONICAL_CAPITAL": "0.00",
        }
        self._send_response(200, health_data)

    def _handle_metrics(self) -> None:
        if self.metrics_registry is not None:
            exposition = self.metrics_registry.render().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(exposition)))
            self.end_headers()
            self.wfile.write(exposition)
        else:
            self._send_response(503, {"error": "Metrics registry not configured"})

    def _send_response(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


class ShadowApiServer:
    """Threaded read-only HTTP server for Shadow Tournament status."""

    def __init__(
        self,
        supervisor: ShadowTournamentSupervisor,
        host: str = "0.0.0.0",
        port: int = 9103,
        metrics_registry: Optional[MetricsRegistry] = None,
    ) -> None:
        self._supervisor = supervisor
        self._host = host
        self._port = port
        self._metrics_registry = metrics_registry
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        return self._port

    def start(self) -> None:
        """Start server in background thread."""
        if self._server is not None:
            return

        handler_class = type(
            "BoundShadowApiHandler",
            (ShadowApiHandler,),
            {
                "supervisor": self._supervisor,
                "metrics_registry": self._metrics_registry,
            },
        )

        self._server = ThreadingHTTPServer((self._host, self._port), handler_class)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name=f"ShadowApiServer-{self._port}",
        )
        self._thread.start()
        logger.info("ShadowApiServer started on %s:%d", self._host, self._port)

    def stop(self) -> None:
        """Stop server cleanly."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            if self._thread is not None:
                self._thread.join(timeout=2.0)
                self._thread = None
            logger.info("ShadowApiServer stopped")
