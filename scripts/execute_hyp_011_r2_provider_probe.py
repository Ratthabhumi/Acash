"""HYP_011 R2 tiny provider probe: ACWI/AGG/SPY 1Day SIP split+raw, 2016-01-04..07.

Default DRY-RUN (no network). Live execution requires --execute-network under
explicit human authorization. Counts every actual HTTP attempt; persists safe
per-page provenance (no credentials).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from acash.data.qualification.hyp_009_daily_client import (
    inclusive_date_window_to_utc_bounds,
)
from acash.data.qualification.hyp_011_qual_client import (
    HYP011AlpacaClient,
    assert_probe_sessions,
)
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)

SYMBOLS = ("ACWI", "AGG", "SPY")
PROBE_START, PROBE_END = inclusive_date_window_to_utc_bounds(
    date(2016, 1, 4), date(2016, 1, 7)
)

EXIT_OK = 0
EXIT_BLOCKED = 2


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HYP_011 tiny provider probe.")
    parser.add_argument("--execute-network", action="store_true", default=False)
    parser.add_argument("--out", default="data/hyp_011/probe_evidence.json")
    args = parser.parse_args(argv)

    attempts = [0]

    def _count() -> None:
        attempts[0] += 1

    print("=== HYP_011 R2 TINY PROVIDER PROBE ===")
    key_present = bool(os.environ.get("ACASH_ALPACA_API_KEY_ID"))
    secret_present = bool(os.environ.get("ACASH_ALPACA_API_SECRET"))
    print(f"CREDENTIAL_KEY_PRESENT = {key_present}")
    print(f"CREDENTIAL_SECRET_PRESENT = {secret_present}")
    if not args.execute_network:
        print("DRY-RUN: no network. Use --execute-network.")
        return 0
    try:
        EnvAlpacaCredentialProvider().load()
    except AlpacaCredentialError as exc:
        print(f"VERDICT = BLOCKED_MISSING_CREDENTIALS ({exc})")
        return EXIT_BLOCKED

    client = HYP011AlpacaClient(http_attempt_listener=_count)
    evidence: Dict[str, Any] = {"symbols": {}, "http_attempts": 0, "verdict": "PENDING"}
    failed = False
    for symbol in SYMBOLS:
        record: Dict[str, Any] = {"adjustments": {}}
        for adjustment in (PriceAdjustment.SPLIT, PriceAdjustment.RAW):
            try:
                result = client.fetch_tiny_probe(
                    symbol=symbol,
                    start_utc=PROBE_START,
                    end_utc=PROBE_END,
                    feed=MarketDataFeed.SIP,
                    adjustment=adjustment,
                    timeframe="1Day",
                )
                sessions = assert_probe_sessions(result.bars, symbol)
                record["adjustments"][adjustment.value] = {
                    "status": "PASS",
                    "rows": len(result.bars),
                    "sessions": [d.isoformat() for d in sessions],
                    "pages": [
                        {
                            "page_index": m.page_index,
                            "byte_length": m.byte_length,
                            "bar_count": m.bar_count,
                            "page_token": m.page_token,
                            "next_page_token": m.next_page_token,
                            "raw_sha256": m.raw_sha256,
                        }
                        for m in result.pages_metadata
                    ],
                }
            except (AlpacaCredentialError, Exception) as exc:
                from acash.core.domain.exceptions import DataContractError as _DCE

                record["adjustments"][adjustment.value] = {
                    "status": type(exc).__name__,
                    "detail": str(exc)[:300],
                }
                failed = True
        adj = record["adjustments"]
        if adj.get("split", {}).get("status") == "PASS" and adj.get("raw", {}).get(
            "status"
        ) == "PASS":
            record["alignment"] = (
                "PASS" if adj["split"]["sessions"] == adj["raw"]["sessions"] else "FAIL"
            )
            if record["alignment"] != "PASS":
                failed = True
        evidence["symbols"][symbol] = record
    evidence["http_attempts"] = attempts[0]
    evidence["verdict"] = "PROVIDER_PROBE_PASS" if not failed else "PROVIDER_PROBE_BLOCKED"
    print(f"HTTP_ATTEMPTS = {attempts[0]}")
    print(f"VERDICT = {evidence['verdict']}")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(evidence, indent=2, sort_keys=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    print(f"Evidence: {out_path} sha={hashlib.sha256(raw.encode()).hexdigest()}")
    return EXIT_OK if not failed else EXIT_BLOCKED


if __name__ == "__main__":
    sys.exit(main())
