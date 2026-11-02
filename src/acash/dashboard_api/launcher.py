"""One-click launcher for the owner-private dashboard (``START-DASHBOARD.bat`` default mode).

Starts the loopback private-view service in this process, then the Vite dashboard, then opens
the browser on a one-time sign-in link. The link carries a nonce that expires after
``NONCE_SECONDS`` and works once; the service answers it with an HttpOnly, SameSite=Strict
session cookie and redirects to Portfolio Intelligence, so no token is shown or copied.

A second launch asks the running service for a new nonce with the launch key kept in
``data/private/.launch_key`` while the first launcher runs; nothing else is trusted to own the
ports. Read-only: no git operations, no broker access, no orders.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from typing import Callable, Mapping, Optional, Sequence, Tuple

from acash.dashboard_api import private_input
from acash.dashboard_api import private_view_server as srv
from acash.ppds import private_observation as po

DASHBOARD_PORT = 3002
DASHBOARD_MARKER = "<title>ACASH Research Dashboard"
KEY_NAME = ".launch_key"
EXIT_NOT_AUTHORIZED, EXIT_PORT_BUSY, EXIT_START_FAILED = 3, 4, 5


def _loopback(port: int, method: str, path: str, headers: Mapping[str, str], timeout: float) -> Tuple[int, bytes]:
    """The launcher's only network access: plain HTTP to 127.0.0.1, never a proxy or another host."""
    connection = http.client.HTTPConnection(srv.HOST, port, timeout=timeout)
    try:
        connection.request(method, path, headers=dict(headers))
        response = connection.getresponse()
        return response.status, response.read(65536)
    finally:
        connection.close()


def port_open(port: int) -> bool:
    connection = http.client.HTTPConnection(srv.HOST, port, timeout=0.5)
    try:
        connection.connect()
        return True
    except OSError:
        return False
    finally:
        connection.close()


def request_nonce(port: int, key: str) -> Optional[str]:
    """A nonce from an already running ACASH service, or None if the port belongs to anything else."""
    try:
        status, body = _loopback(port, "POST", srv.LAUNCH_ROUTE, {srv.LAUNCH_HEADER: key}, 3)
        doc = json.loads(body) if status == 200 else None
    except (OSError, ValueError, http.client.HTTPException):
        return None
    nonce = doc.get("nonce") if isinstance(doc, dict) else None
    return nonce if isinstance(nonce, str) and nonce else None


def dashboard_is_acash() -> bool:
    try:
        status, body = _loopback(DASHBOARD_PORT, "GET", "/", {}, 2)
    except (OSError, http.client.HTTPException):
        return False
    return status == 200 and DASHBOARD_MARKER in body.decode("utf-8", "replace")


def wait_for(check: Callable[[], bool], seconds: float, alive: Callable[[], bool] = lambda: True) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and alive():
        if check():
            return True
        time.sleep(0.5)
    return False


def sign_in_url(port: int, nonce: str) -> str:
    return f"http://{srv.HOST}:{port}{srv.SESSION_ROUTE}?nonce={nonce}"


def _open(port: int, nonce: str, browser: bool) -> None:
    url = sign_in_url(port, nonce)
    if browser:
        webbrowser.open(url)
    else:
        print(f"Sign-in link (one-time, expires in {srv.NONCE_SECONDS} s): {url}", flush=True)


def _stop(process: "subprocess.Popen[bytes]") -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True, check=False)
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Start ACASH with the owner-private dashboard signed in.")
    parser.add_argument("--no-browser", action="store_true", help="print the one-time sign-in link instead")
    parser.add_argument("--port", type=int, default=srv.DEFAULT_PORT)
    args = parser.parse_args(argv)
    browser = not args.no_browser

    auth = private_input.authority()
    print(f"ODR-001 {auth['odr_001']} · ODR-003 {auth['odr_003']} (saving "
          f"{'enabled' if private_input.write_authorized() else 'disabled'})", flush=True)
    if auth["odr_001"] != "RATIFIED":
        print("[BLOCKED] Owner-private mode needs ODR-001 RATIFIED; nothing was started.", flush=True)
        return EXIT_NOT_AUTHORIZED
    key_path = private_input._private_dir() / KEY_NAME

    if port_open(args.port):
        key = key_path.read_text(encoding="utf-8").strip() if key_path.is_file() else ""
        nonce = request_nonce(args.port, key) if key else None
        if nonce is None:
            print(f"[ERROR] Port {args.port} is used by a program that is not this ACASH launcher. "
                  "Close it (or the old \"ACASH Private View\" window) and double-click START-DASHBOARD.bat again.",
                  flush=True)
            return EXIT_PORT_BUSY
        if not dashboard_is_acash():
            print(f"[ERROR] ACASH is running but its dashboard on port {DASHBOARD_PORT} does not answer. "
                  "Close the other ACASH window and start again.", flush=True)
            return EXIT_START_FAILED
        _open(args.port, nonce, browser)
        print("ACASH is already running in its other window; opened a new signed-in browser tab.", flush=True)
        return 0
    if port_open(DASHBOARD_PORT):
        print(f"[ERROR] Port {DASHBOARD_PORT} is already in use, possibly by an older dashboard window. "
              "Its owner cannot be verified, so private mode does not use it. Close it and start again.", flush=True)
        return EXIT_PORT_BUSY
    npm = shutil.which("npm")
    if npm is None:
        print("[ERROR] npm was not found on PATH. Run SETUP.bat, then start again.", flush=True)
        return EXIT_START_FAILED

    key = secrets.token_hex(32)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(key, encoding="utf-8")
    server = srv.serve(args.port, launch_key=key)
    session: srv.Session = getattr(server, "acash_session")
    threading.Thread(target=server.serve_forever, name="acash-private-view", daemon=True).start()
    flags: int = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    vite = subprocess.Popen([npm, "run", "dev"], cwd=po._repo_root() / "dashboard", creationflags=flags)
    try:
        if not wait_for(dashboard_is_acash, 90, lambda: vite.poll() is None):
            print("[ERROR] The dashboard did not start; see the messages above.", flush=True)
            return EXIT_START_FAILED
        _open(args.port, session.mint(), browser)
        print("ACASH is running: Portfolio Intelligence opens signed in. Keep this window open; "
              f"close it or press Ctrl+C to stop. The session ends after {srv.SESSION_SECONDS // 3600} hours.",
              flush=True)
        while vite.poll() is None:
            time.sleep(0.5)
        print("The dashboard process ended.", flush=True)
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        server.shutdown()
        server.server_close()
        _stop(vite)
        if key_path.is_file() and key_path.read_text(encoding="utf-8").strip() == key:
            key_path.unlink()


if __name__ == "__main__":
    sys.exit(main())
