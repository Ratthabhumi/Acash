"""Execution Script: HYP_009 R2 Provider Qualification (daily SIP, SPY 1Day, split+raw).

Frozen probe scope (CORE-001 / HYP_009 R1 + pre-R2 clarification):

- symbol = SPY, timeframe = 1Day, feed = SIP
- window = 2016-11-01 .. 2016-11-04 inclusive (Tue-Fri, no holiday, no early close)
- Request A: adjustment = split (signal prices)
- Request B: adjustment = raw (execution/valuation)

Runner behavior when live execution is explicitly authorized:

    credential presence
    -> split request
    -> raw request
    -> scope validation (window + expected sessions)
    -> OHLCV validation (inherent in HYP009AlpacaClient parsing)
    -> split/raw date-set alignment
    -> concise verdict

STRICT INVARIANTS:

1. Secrets: never prints or logs API keys/secrets (presence booleans only).
2. Fail-closed credentials: missing credentials abort BEFORE any network call.
3. Explicit live gate: live network requests require --execute-network. The
   default is a dry-run/blocked verdict with NETWORK_REQUESTS_ISSUED = 0.
4. Live provider qualification requires separate human authorization
   (AUTHORIZE_CORE_001_HYP_009_R2_LIVE_PROVIDER_QUALIFICATION). Executing this
   script without that authorization is out of scope.
5. No returns, no regressions, no trades, no Sharpe. Qualification only.

Usage (dry-run / blocked verdict, zero network):

    uv run python scripts/execute_hyp_009_r2_provider_qualification.py

Usage (authorized live qualification only):

    uv run python scripts/execute_hyp_009_r2_provider_qualification.py --execute-network
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date
from typing import List

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.client import SipContractViolationError
from acash.data.qualification.hyp_009_daily_client import (
    HYP009_MAX_DATE,
    HYP009_MIN_DATE,
    HYP009AlpacaClient,
    Hyp009RetrievalResult,
    assert_split_raw_alignment,
    inclusive_date_window_to_utc_bounds,
)
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)

PROBE_START_DATE: date = date(2016, 11, 1)
PROBE_END_DATE: date = date(2016, 11, 4)

EXIT_OK = 0
EXIT_QUALIFICATION_FAIL = 1
EXIT_BLOCKED = 2


class HttpAttemptCounter:
    """Counts ACTUAL provider HTTP executions (attempts, retries, pages).

    Wired into the client as its http_attempt_listener, so the count reflects
    real transport executions - including failed responses - rather than
    successful fetch returns. Carries no credentials.
    """

    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> None:
        self.count += 1


def get_git_head_sha() -> str:
    """Retrieve current Git HEAD SHA."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception as e:
        raise DataContractError(f"Failed to retrieve git HEAD: {e}") from e


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="execute_hyp_009_r2_provider_qualification.py",
        description="HYP_009 R2 provider qualification probe (SPY 1Day SIP, split+raw).",
    )
    parser.add_argument(
        "--execute-network",
        action="store_true",
        default=False,
        help="Explicit human operator flag required to issue live Alpaca requests. "
        "Default is FALSE (no network calls).",
    )
    return parser.parse_args(argv)


def expected_probe_sessions(calendar: NyseCa1Calendar) -> List[date]:
    """Derive expected trading sessions for the probe window from CA-1 authority."""
    sessions: List[date] = []
    cursor = PROBE_START_DATE
    while cursor <= PROBE_END_DATE:
        if calendar.is_trading_session(cursor):
            sessions.append(cursor)
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return sessions


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    http_attempts = HttpAttemptCounter()

    # Provider timestamp bounds for the INCLUSIVE scientific session window.
    # End-of-day bound keeps daily bars timestamped after 00:00Z for the end
    # session (e.g. Alpaca 1Day bars near 04:00:00Z) inside the provider query;
    # response spill validation still rejects any Nov-5 session.
    provider_start_utc, provider_end_utc = inclusive_date_window_to_utc_bounds(
        PROBE_START_DATE, PROBE_END_DATE
    )

    print("================================================================================")
    print("ACASH HYP_009 R2 PROVIDER QUALIFICATION (SPY 1Day SIP, split + raw)")
    print(f"Probe sessions: {PROBE_START_DATE} .. {PROBE_END_DATE} inclusive")
    print(f"Provider start UTC: {provider_start_utc.isoformat()}")
    print(f"Provider end UTC:   {provider_end_utc.isoformat()}")
    print(f"Authorized window: {HYP009_MIN_DATE} .. {HYP009_MAX_DATE}")
    print(f"Network Execution Flag: {args.execute_network}")
    print(f"Git HEAD: {get_git_head_sha()}")
    print("================================================================================")

    # 1. Credential presence (booleans only - never print secret values).
    key_present = bool(os.environ.get("ACASH_ALPACA_API_KEY_ID"))
    secret_present = bool(os.environ.get("ACASH_ALPACA_API_SECRET"))
    print(f"CREDENTIAL_KEY_PRESENT = {key_present}")
    print(f"CREDENTIAL_SECRET_PRESENT = {secret_present}")

    # 2. Explicit live gate: default is no network.
    if not args.execute_network:
        print("VERDICT = NOT_EXECUTED_DRY_RUN_DEFAULT")
        print(f"NETWORK_REQUESTS_ISSUED = {http_attempts.count}")
        print("Live provider qualification requires separate human authorization:")
        print("AUTHORIZE_CORE_001_HYP_009_R2_LIVE_PROVIDER_QUALIFICATION")
        return EXIT_BLOCKED

    # 3. Fail closed on missing credentials BEFORE any network call.
    try:
        EnvAlpacaCredentialProvider().load()
    except AlpacaCredentialError as e:
        print(f"VERDICT = BLOCKED_MISSING_CREDENTIALS ({e})")
        print(f"NETWORK_REQUESTS_ISSUED = {http_attempts.count}")
        return EXIT_BLOCKED

    calendar = NyseCa1Calendar()
    expected_sessions = expected_probe_sessions(calendar)
    print(f"EXPECTED_SESSIONS = {[d.isoformat() for d in expected_sessions]}")

    client = HYP009AlpacaClient(http_attempt_listener=http_attempts)
    start_utc = provider_start_utc
    end_utc = provider_end_utc

    try:
        # Request A: adjustment = split (signal prices).
        split_result: Hyp009RetrievalResult = client.fetch_historical_bars(
            symbol="SPY",
            start_utc=start_utc,
            end_utc=end_utc,
            feed=MarketDataFeed.SIP,
            adjustment=PriceAdjustment.SPLIT,
            timeframe="1Day",
        )

        # Request B: adjustment = raw (execution/valuation).
        raw_result: Hyp009RetrievalResult = client.fetch_historical_bars(
            symbol="SPY",
            start_utc=start_utc,
            end_utc=end_utc,
            feed=MarketDataFeed.SIP,
            adjustment=PriceAdjustment.RAW,
            timeframe="1Day",
        )

        split_dates = sorted({bar.timestamp_utc.date() for bar in split_result.bars})
        raw_dates = sorted({bar.timestamp_utc.date() for bar in raw_result.bars})
        print(f"SPLIT_ROWS = {len(split_result.bars)}")
        print(f"RAW_ROWS = {len(raw_result.bars)}")

        # Scope validation: exact expected sessions, nothing more, nothing less.
        if split_dates != expected_sessions or raw_dates != expected_sessions:
            print("VERDICT = FAIL_SCOPE_MISMATCH")
            print(f"SPLIT_DATES = {[d.isoformat() for d in split_dates]}")
            print(f"RAW_DATES = {[d.isoformat() for d in raw_dates]}")
            print(f"NETWORK_REQUESTS_ISSUED = {http_attempts.count}")
            return EXIT_QUALIFICATION_FAIL

        # Split/raw date-set alignment (fail closed on mismatch).
        aligned = assert_split_raw_alignment(split_result.bars, raw_result.bars)
        print(f"ALIGNED_SESSIONS = {[d.isoformat() for d in aligned]}")
        print("VERDICT = PASS_PROVIDER_QUALIFICATION_PROBE")
        print(f"NETWORK_REQUESTS_ISSUED = {http_attempts.count}")
        return EXIT_OK
    except (SipContractViolationError, DataContractError, AlpacaCredentialError) as e:
        print(f"VERDICT = FAIL_CONTRACT_VIOLATION ({e})")
        print(f"NETWORK_REQUESTS_ISSUED = {http_attempts.count}")
        return EXIT_QUALIFICATION_FAIL


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"PROBE_ERROR = {e}")
        sys.exit(1)
