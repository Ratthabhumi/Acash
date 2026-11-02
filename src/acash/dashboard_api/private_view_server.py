"""Loopback-only, read-only server for the owner-private dashboard view.

One GET route, no parameters, no write or order endpoints. Every request re-checks the
Host, the Origin allowlist, a per-start session token and the ODR-001 state before the
view file is read; localhost alone is never treated as authentication. Responses are
``no-store`` and the server never logs paths or values.
"""

from __future__ import annotations

import argparse
import hmac
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.invest.upi_view import VIEW_SCHEMA
from acash.ppds.private_observation import (
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

Response = Tuple[int, Dict[str, str], bytes]


def _json(status: int, headers: Dict[str, str], body: Mapping[str, Any]) -> Response:
    return status, headers, json.dumps(body, sort_keys=True).encode("utf-8")


def respond(method: str, target: str, headers: Mapping[str, str], token: str, view_path: Path, port: int) -> Response:
    base = {"Cache-Control": "no-store", "Pragma": "no-cache", "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff", "Vary": "Origin"}
    if headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
        return _json(421, base, {"status": "HOST_NOT_ALLOWED"})
    origin = headers.get("Origin")
    if origin not in ALLOWED_ORIGINS:
        return _json(403, base, {"status": "ORIGIN_NOT_ALLOWED"})
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
    state = odr_state(None, SCHEMA_V1_2)
    if state != "RATIFIED":
        return _json(403, cors, {"status": "AUTHORIZATION_REQUIRED", "odr_state": state})
    status, code, doc = load_view(view_path)
    if status == "NO_REPORT":
        return _json(404, cors, {"status": status})
    if status == "INVALID_REPORT":
        return _json(422, cors, {"status": status, "code": code})
    return _json(200, cors, doc)


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


def make_handler(token: str, view_path: Path, port: int) -> type:
    class Handler(BaseHTTPRequestHandler):
        server_version = "acash-private-view"
        sys_version = ""

        def _send(self) -> None:
            status, headers, body = respond(self.command, self.path, dict(self.headers.items()), token, view_path, port)
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
    server = ThreadingHTTPServer((HOST, port), make_handler(session, path, port))
    return server


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Serve the owner-private dashboard view on 127.0.0.1 (read-only).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    token = secrets.token_urlsafe(32)
    server = serve(args.port, token=token)
    print(f"Serving {ROUTE} on http://{HOST}:{args.port} (read-only, loopback only). Ctrl+C stops it.", flush=True)
    print(f"Session token (paste into the dashboard; valid until this process stops): {token}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
