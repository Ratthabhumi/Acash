"""Browser E2E harness: the private-view server on a throwaway synthetic root with mocked providers.

Run ``uv run python tests/integration/market_refresh_e2e_harness.py`` next to ``npm run dev`` and
open the printed one-time link. Nothing here is reachable from the launcher: the root, the ODR
records (including a synthetic ODR-004 scope) and the provider transport exist only inside this
process. The mocked transport answers with response-shaped synthetic payloads; the first refresh
returns an Alpaca quote for SYNIDX, a Massive previous close for SYNBOND and a BOT reference
rate, and ``FAIL_AFTER`` refreshes later every provider fails with HTTP 503.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from acash.dashboard_api import market_service as ms  # noqa: E402
from acash.dashboard_api import private_input as pi  # noqa: E402
from acash.dashboard_api import private_view_server as srv  # noqa: E402
from acash.invest import market_authority as ma  # noqa: E402
from acash.invest import market_refresh as mr  # noqa: E402
from acash.market_data import providers as mp  # noqa: E402
from acash.invest.capacity_plan import CAPACITY_SCHEMA  # noqa: E402
from acash.ppds import private_observation as po  # noqa: E402

FAIL_AFTER = 1


class Store:
    def lookup(self, provider_id: str) -> Optional[Tuple[str, str]]:
        return ("SYNKEY", "SYNTHETIC_SECRET") if provider_id in ma.ADAPTED_PROVIDERS else None


class MockTransport:
    def __init__(self) -> None:
        self.refreshes = 0

    def __call__(self, request: mp.HttpRequest) -> Tuple[int, bytes]:
        mp.assert_allowed(request)
        if request.provider_id == "ALPACA_BASIC":
            self.refreshes += 1
        if self.refreshes > FAIL_AFTER:
            return 503, b""
        now = datetime.now(timezone.utc)
        session_ms = int(datetime(now.year, now.month, now.day, tzinfo=mr.NEW_YORK).timestamp() * 1000) - 86_400_000
        body: Dict[str, Any]
        if request.provider_id == "ALPACA_BASIC":
            stamp = (now - timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%S.000000001Z")
            body = {"trades": {"SYNIDX": {"t": stamp, "x": "V", "p": 52.5, "s": 10}}}
        elif request.provider_id == "MASSIVE_BASIC":
            ticker = request.url.split("/ticker/")[1].split("/")[0]
            body = {"ticker": ticker, "adjusted": False, "results": [{"T": ticker, "c": 99.1, "t": session_ms}]}
        else:
            day = now.astimezone(mr.NEW_YORK).date().isoformat()
            body = {"result": {"data": {"data_detail": [{"period": day, "rate": "33.10"}]}}}
        return 200, json.dumps(body).encode("utf-8")


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="acash_e2e_market_"))
    setattr(po, "_repo_root", lambda: root)
    setattr(ma, "_repo_root", lambda: root)
    governance = root / "docs" / "governance"
    governance.mkdir(parents=True)
    (root / po.AUTHORIZATION_RECORD).write_text(json.dumps({
        "capability": po.AUTHORIZED_CAPABILITY, "status": "RATIFIED", "ratified_by": "OWNER", "ratified_on": "2026-11-03",
        "scope_schemas": [po.SCHEMA_V1_2, CAPACITY_SCHEMA]}), encoding="utf-8")
    (root / pi.AUTHORING_RECORD).write_text(json.dumps({
        "decision_id": pi.AUTHORING_DECISION_ID, "capability": pi.AUTHORING_CAPABILITY, "status": "RATIFIED",
        "ratified_by": "OWNER", "ratified_on": "2026-11-03", "requires": [pi.OBSERVATION_DECISION_ID],
        "scope_schemas": [po.SCHEMA_V1_2, CAPACITY_SCHEMA], "scope_files": pi.SCOPE_FILES}), encoding="utf-8")
    (root / ma.RECORD).write_text(json.dumps({
        "decision_id": ma.DECISION_ID, "capability": ma.CAPABILITY, "status": "RATIFIED", "ratified_by": "OWNER",
        "ratified_on": "2026-11-03", "requires": ma.REQUIRES,
        "scope_providers": [{"provider_id": p, "entitlement_verified": True, "display_permitted": True,
                             "cache_permitted": False, "evidence": "SYNTHETIC_E2E"} for p in ma.ADAPTED_PROVIDERS]}),
        encoding="utf-8")
    private = root / "data" / "private"
    private.mkdir(parents=True)
    for name, source in (("snapshot.json", "upi_v1_2_synthetic_snapshot.json"), ("capacity.json", "upi_v1_synthetic_capacity.json")):
        doc = json.loads((REPO / "docs/research/evidence" / source).read_text(encoding="utf-8"))
        doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
        (private / name).write_text(json.dumps(doc), encoding="utf-8")
    print("initial report:", pi.generate()[1]["status"], flush=True)

    session = srv.Session("e2e-" + "x" * 40, float("inf"), "E2E_LAUNCH_KEY_" + "0" * 40)
    market = ms.MarketService(Store(), MockTransport())
    handler = srv.make_handler(session.token, private / "out" / pi.VIEW_FILE, srv.DEFAULT_PORT,
                               pi.InputService(), None, session, market)
    server = ThreadingHTTPServer((srv.HOST, srv.DEFAULT_PORT), handler)
    print(f"root: {root}", flush=True)
    print(f"sign in: POST {srv.LAUNCH_ROUTE} with {srv.LAUNCH_HEADER}: {session.launch_key}, then open "
          f"http://{srv.HOST}:{srv.DEFAULT_PORT}{srv.SESSION_ROUTE}?nonce=<nonce> within {srv.NONCE_SECONDS} s", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
