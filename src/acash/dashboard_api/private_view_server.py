"""Loopback-only server for the owner-private dashboard view and the Setup Wizard inputs.

The view route is one parameterless GET. The input routes (``private_input``) can replace
only the two fixed input files and only while ODR-003 is also RATIFIED; there are no order,
broker or arbitrary-path endpoints. Every request re-checks the Host, the Origin allowlist,
a per-start session token that expires, and the ODR state before any file is read;
localhost alone is never treated as authentication. Responses are ``no-store`` and the
server never logs paths, payloads or values.
"""

from __future__ import annotations

import argparse
import hmac
import json
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.dashboard_api import private_input
from acash.invest.upi_view import VIEW_SCHEMA
from acash.ppds.private_observation import (
    MAX_INPUT_BYTES,
    SCHEMA_V1_2,
    _repo_root,
    assert_private_location,
    odr_state,
    read_gated_json,
)

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
ROUTE = "/api/upi/view"
TOKEN_HEADER = "X-ACASH-Session"
ALLOWED_ORIGINS = ("http://127.0.0.1:3002", "http://localhost:3002")
DEFAULT_VIEW = Path("data/private/out/upi_view.json")
SESSION_SECONDS = 4 * 60 * 60

Response = Tuple[int, Dict[str, str], bytes]


def _json(status: int, headers: Dict[str, str], body: Mapping[str, Any]) -> Response:
    return status, headers, json.dumps(body, sort_keys=True).encode("utf-8")


def respond(method: str, target: str, headers: Mapping[str, str], token: str, view_path: Path, port: int,
            body: bytes = b"", service: Optional[private_input.InputService] = None,
            session_expired: bool = False) -> Response:
    base = {"Cache-Control": "no-store", "Pragma": "no-cache", "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff", "Vary": "Origin"}
    if headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
        return _json(421, base, {"status": "HOST_NOT_ALLOWED"})
    origin = headers.get("Origin")
    if origin not in ALLOWED_ORIGINS:
        return _json(403, base, {"status": "ORIGIN_NOT_ALLOWED"})
    name = target[len(private_input.PREFIX):] if target.startswith(private_input.PREFIX) else None
    if service is not None and name in private_input.ROUTES:
        return _input_route(method, name, headers, token, body, service, session_expired,
                            {**base, "Access-Control-Allow-Origin": str(origin),
                             "Access-Control-Allow-Headers": f"{TOKEN_HEADER}, Content-Type",
                             "Access-Control-Allow-Methods": ", ".join(private_input.ROUTES[name])})
    cors = {**base, "Access-Control-Allow-Origin": str(origin), "Access-Control-Allow-Headers": TOKEN_HEADER,
            "Access-Control-Allow-Methods": "GET"}
    if target != ROUTE:
        return _json(404, cors, {"status": "NOT_FOUND"})
    if method == "OPTIONS":
        return 204, cors, b""
    if method != "GET":
        return _json(405, cors, {"status": "METHOD_NOT_ALLOWED"})
    if not hmac.compare_digest(headers.get(TOKEN_HEADER, "").encode("utf-8"), token.encode("utf-8")):
        return _json(401, cors, {"status": "SESSION_TOKEN_REQUIRED"})
    if session_expired:
        return _json(401, cors, {"status": "SESSION_EXPIRED"})
    state = odr_state(None, SCHEMA_V1_2)
    if state != "RATIFIED":
        return _json(403, cors, {"status": "AUTHORIZATION_REQUIRED", "odr_state": state})
    status, code, doc = load_view(view_path)
    if status == "NO_REPORT":
        return _json(404, cors, {"status": status})
    if status == "INVALID_REPORT":
        return _json(422, cors, {"status": status, "code": code})
    return _json(200, cors, doc)


def _input_route(method: str, name: str, headers: Mapping[str, str], token: str, body: bytes,
                 service: private_input.InputService, session_expired: bool, cors: Dict[str, str]) -> Response:
    if method == "OPTIONS":
        return 204, cors, b""
    if method not in private_input.ROUTES[name]:
        return _json(405, cors, {"status": "METHOD_NOT_ALLOWED"})
    if not hmac.compare_digest(headers.get(TOKEN_HEADER, "").encode("utf-8"), token.encode("utf-8")):
        return _json(401, cors, {"status": "SESSION_TOKEN_REQUIRED"})
    if session_expired:
        return _json(401, cors, {"status": "SESSION_EXPIRED"})
    rejected, payload = private_input.parse_body(method, headers, body)
    status, doc = rejected or private_input.handle(method, name, payload, service)
    return _json(status, cors, doc)


def load_view(view_path: Path) -> Tuple[str, Optional[str], Any]:
    """Single authority for the private view contract: (READY | NO_REPORT | INVALID_REPORT, code, doc).

    Callers must check ODR-001 first; ``read_gated_json`` refuses the read otherwise.
    """
    if not view_path.is_file():
        return "NO_REPORT", None, None
    try:
        doc = read_gated_json(view_path, "UPI_VIEW")
    except DataContractError as exc:
        return "INVALID_REPORT", str(exc).split(":")[0].rstrip("."), None
    if not isinstance(doc, dict) or doc.get("view_schema") != VIEW_SCHEMA or doc.get("data_mode") != "OWNER_PRIVATE_READ_ONLY":
        return "INVALID_REPORT", "VIEW_CONTRACT_MISMATCH", None
    return "READY", None, doc


def _read_body(handler: BaseHTTPRequestHandler) -> Optional[bytes]:
    """Bounded request body; None means it was refused without reading."""
    if handler.headers.get("Transfer-Encoding"):
        return None
    try:
        length = int(handler.headers.get("Content-Length") or "0")
    except ValueError:
        return None
    if length < 0 or length > MAX_INPUT_BYTES:
        return None
    return handler.rfile.read(length) if length else b""


def make_handler(token: str, view_path: Path, port: int, service: Optional[private_input.InputService] = None,
                 expires_at: Optional[float] = None) -> type:
    class Handler(BaseHTTPRequestHandler):
        server_version = "acash-private-view"
        sys_version = ""

        def _send(self) -> None:
            body = _read_body(self)
            if body is None:
                self.close_connection = True
                status, headers, out = _json(413, {"Cache-Control": "no-store", "Content-Type": "application/json"},
                                             {"status": "PAYLOAD_TOO_LARGE_OR_UNBOUNDED"})
            else:
                expired = expires_at is not None and time.monotonic() > expires_at
                status, headers, out = respond(self.command, self.path, dict(self.headers.items()), token,
                                               view_path, port, body, service, expired)
            self._write(status, headers, out)

        def _write(self, status: int, headers: Dict[str, str], body: bytes) -> None:
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        do_GET = do_OPTIONS = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _send

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def serve(port: int = DEFAULT_PORT, view_path: Optional[Path] = None, token: Optional[str] = None) -> ThreadingHTTPServer:
    path = view_path or (_repo_root() / DEFAULT_VIEW)
    assert_private_location(path)
    session = token or secrets.token_urlsafe(32)
    handler = make_handler(session, path, port, private_input.InputService(), time.monotonic() + SESSION_SECONDS)
    return ThreadingHTTPServer((HOST, port), handler)


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Serve the owner-private dashboard view on 127.0.0.1 (loopback only).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    token = secrets.token_urlsafe(32)
    server = serve(args.port, token=token)
    auth = private_input.authority()
    print(f"Serving {ROUTE} and the Setup Wizard on http://{HOST}:{args.port} (loopback only). Ctrl+C stops it.",
          flush=True)
    print(f"Input saving: {'ENABLED' if auth['odr_003'] == 'RATIFIED' else 'DISABLED'} (ODR-003 {auth['odr_003']})",
          flush=True)
    print(f"Session token (paste into the dashboard; expires after {SESSION_SECONDS // 3600} hours "
          f"or when this window closes): {token}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
