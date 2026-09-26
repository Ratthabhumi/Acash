"""HYP_011 prospective shadow single-session runner.

Default DRY-RUN (zero network). Live observation requires --execute-network
under an explicit human authorization AND processes exactly the unique next
expected session (activation session if none observed, else the first session
after the last processed one). One session per invocation. No catch-up ranges.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)
from acash.research.hyp_011.shadow import (
    SCIENTIFIC_PROSPECTIVE_BOUNDARY,
    ShadowState,
    derive_activation_session,
    missed_unobserved_sessions,
)
from acash.research.hyp_011.shadow_ops import (
    SessionMarket,
    ShadowBenchmark,
    ShadowPortfolio,
    append_observation,
    process_benchmark_session,
    process_strategy_session,
)

SYMBOLS = ("ACWI", "AGG", "SPY")
ACTIVATION_SESSION = date(2026, 9, 28)
STATE_DIR = Path("data/hyp_011/prospective")

EXIT_OK = 0
EXIT_BLOCKED = 2


def _load_state() -> Dict[str, Any]:
    path = STATE_DIR / "state.json"
    if not path.exists():
        return {
            "activation_session": ACTIVATION_SESSION.isoformat(),
            "observed_sessions": [],
            "completed_annual_rebalances": 0,
            "last_observation_sha256": None,
            "portfolio": None,
            "benchmark": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(doc: Dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / "state.json"
    raw = json.dumps(doc, indent=2, sort_keys=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)


def _expected_next(state: Dict[str, Any], calendar: NyseCa1Calendar) -> date:
    observed = state.get("observed_sessions", [])
    if not observed:
        return ACTIVATION_SESSION
    last = date.fromisoformat(observed[-1])
    cursor = date.fromordinal(last.toordinal() + 1)
    for _ in range(14):
        if calendar.is_trading_session(cursor):
            return cursor
        cursor = date.fromordinal(cursor.toordinal() + 1)
    raise DataContractError("SHADOW_NO_NEXT_SESSION_WITHIN_14_DAYS.")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HYP_011 prospective shadow runner.")
    parser.add_argument("--execute-network", action="store_true", default=False)
    args = parser.parse_args(argv)

    attempts = [0]

    def _count() -> None:
        attempts[0] += 1

    print("=== HYP_011 PROSPECTIVE SHADOW (single session) ===")
    if not args.execute_network:
        print("DRY-RUN: no network. Use --execute-network.")
        return 0
    try:
        EnvAlpacaCredentialProvider().load()
    except AlpacaCredentialError as exc:
        print(f"BLOCKED_MISSING_CREDENTIALS: {exc}")
        return EXIT_BLOCKED

    calendar = NyseCa1Calendar()
    state = _load_state()
    if state.get("activation_session") != ACTIVATION_SESSION.isoformat():
        raise DataContractError("SHADOW_ACTIVATION_MISMATCH.")
    target = _expected_next(state, calendar)
    print(f"Expected next session: {target.isoformat()}")

    # Idempotence: already processed -> no action, zero network.
    obs_path = STATE_DIR / "observations" / f"{target.isoformat()}.json"
    if obs_path.exists():
        print("ALREADY_PROCESSED_NO_ACTION")
        print("NETWORK_REQUESTS_ISSUED = 0")
        return EXIT_OK

    # Completion + backfill guards BEFORE any network call.
    guard_state = ShadowState(activation_session=ACTIVATION_SESSION)
    guard_state.observed_sessions = list(state.get("observed_sessions", []))
    if target < ACTIVATION_SESSION:
        raise DataContractError(f"SHADOW_BACKFILL_FORBIDDEN: {target}.")
    close_utc = calendar.get_session(target).close_utc
    if close_utc is None:
        raise DataContractError(f"SHADOW_NO_CLOSE_TIME: {target}.")
    now_utc = datetime.now(timezone.utc)
    if now_utc <= close_utc:
        print(f"SESSION_NOT_YET_COMPLETE: {target} (close {close_utc.isoformat()}).")
        print("NETWORK_REQUESTS_ISSUED = 0")
        return EXIT_OK
    # Full guard validation (duplicate/order/early/stress/quarantine/completion).
    guard_state.record_session(target, calendar, now_utc)

    client = HYP011AlpacaClient(http_attempt_listener=_count)
    fetched: Dict[str, Dict[str, Any]] = {}
    for symbol in SYMBOLS:
        fetched[symbol] = {}
        for adjustment in (PriceAdjustment.SPLIT, PriceAdjustment.RAW):
            result = client.fetch_single_session(
                symbol=symbol, session=target, feed=MarketDataFeed.SIP,
                adjustment=adjustment, timeframe="1Day",
            )
            fetched[symbol][adjustment.value] = {
                "bar": result.bars[0],
                "pages": result.pages_metadata,
                "raw_bytes": result.pages_raw_bytes,
            }
    print(f"NETWORK_REQUESTS_ISSUED = {attempts[0]}")
    print("Single-session fetch complete; accounting/benchmark/chain-write")
    print("completes only under a dedicated observation authorization. STOP.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
