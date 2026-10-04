"""RI-01 provider probe R1 harness (CODE PREPARATION ONLY).

Bounded zero-outcome network probe design. THIS MODULE MUST NOT BE EXECUTED
against live endpoints without a future single explicit network authority
(after HYP_011 Observation #1 forensic check), and NEVER from /home/mew/Acash
while HYP_011 V2 is armed.

Scope, frozen:
- Symbol: SPY only (hardcoded; any other symbol is rejected).
- Sessions: allowlisted already-consumed / pre-holdout dates only.
  The sealed 2023-2026 holdout (>= 2023-01-01) is rejected before any network.
- Capabilities: 1Min SIP raw bars (paginated to exhaustion), narrow
  historical-trades windows around open/close (exchange + conditions
  preserved), credential-entitlement signal, rate-limit headers, raw-bytes +
  SHA-256 envelopes, deterministic re-fetch stability comparison.

Computes NOTHING predictive: no returns, no PnL, no Sharpe, no hit-rate, no
thresholds, no signal. Missing data is DATA_UNAVAILABLE, never imputed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)
from acash.research.ri01.feasibility import (
    evidence_digest,
    parse_utc_timestamp,
    require_complete_rth_grid,
    validate_provider_bar,
)

DATA_HOST = "https://data.alpaca.markets"
PROBE_SYMBOL = "SPY"
PROBE_FEED = "sip"
PROBE_TIMEFRAME = "1Min"
PROBE_ADJUSTMENT = "raw"
HOLDOUT_START: date = date(2023, 1, 1)

# Already-consumed (MEC-0015 probes) or pre-holdout sessions ONLY:
# - 2018-06-01: early-depth regular session (390 min expected)
# - 2021-06-01: normal later in-sample regular session (390 min expected)
# - 2021-11-26: historical half-day (210 min expected)
ALLOWLISTED_SESSIONS: tuple[date, ...] = (
    date(2018, 6, 1),
    date(2021, 6, 1),
    date(2021, 11, 26),
)

CAPABILITIES: tuple[str, ...] = ("bars", "trades")


@dataclass(frozen=True)
class ProbeTrade:
    """One historical trade with venue + condition provenance preserved."""

    timestamp_utc: datetime
    exchange: str
    price: Decimal
    size: Decimal
    conditions: Tuple[str, ...]

    @classmethod
    def from_dict(cls, doc: Mapping[str, Any], context: str) -> "ProbeTrade":
        if not isinstance(doc, Mapping):
            raise DataContractError(f"RI01_TRADE_NOT_A_MAPPING: {context}.")
        timestamp = parse_utc_timestamp(doc.get("t"), f"{context}.t")
        exchange = doc.get("x")
        if not isinstance(exchange, str) or not exchange.strip():
            raise DataContractError(f"RI01_TRADE_BAD_EXCHANGE: {context}.")
        try:
            price = Decimal(str(doc.get("p")))
            size = Decimal(str(doc.get("s")))
        except (InvalidOperation, ValueError, TypeError, ArithmeticError) as exc:
            raise DataContractError(f"RI01_TRADE_BAD_NUMERIC: {context}.") from exc
        if not price.is_finite() or price <= 0:
            raise DataContractError(f"RI01_TRADE_NONPOSITIVE_PRICE: {context}.")
        if not size.is_finite() or size <= 0:
            raise DataContractError(f"RI01_TRADE_NONPOSITIVE_SIZE: {context}.")
        raw_conditions = doc.get("c", [])
        if not isinstance(raw_conditions, list) or not all(
            isinstance(item, str) for item in raw_conditions
        ):
            raise DataContractError(f"RI01_TRADE_BAD_CONDITIONS: {context}.")
        return cls(
            timestamp_utc=timestamp,
            exchange=exchange.strip(),
            price=price,
            size=size,
            conditions=tuple(raw_conditions),
        )


def compare_stability(first_sha256: str, second_sha256: str) -> str:
    """Compare two evidence digests (pure; used by scheduled revisits)."""
    if not first_sha256 or not second_sha256:
        raise DataContractError("RI01_STABILITY_EMPTY_DIGEST.")
    return "STABLE" if first_sha256 == second_sha256 else "DIFFERENT"


def write_envelope(
    out_dir: Path,
    name: str,
    raw_bytes: bytes,
    metadata: Mapping[str, Any],
    retrieved_at_utc: datetime,
) -> str:
    """Persist raw payload bytes plus a JSON envelope; return content SHA-256.

    Crash-safe ordering (bytes first, envelope second). Creates NOTHING else.
    """
    if not name or "/" in name or "\\" in name:
        raise DataContractError("RI01_ENVELOPE_BAD_NAME.")
    digest = evidence_digest(raw_bytes)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload_path = out_dir / f"{name}.bin"
    tmp_payload = payload_path.with_suffix(".bin.tmp")
    tmp_payload.write_bytes(raw_bytes)
    tmp_payload.replace(payload_path)
    envelope = dict(metadata)
    envelope.update(
        {
            "content_sha256": digest,
            "retrieved_at_utc": retrieved_at_utc.isoformat(),
        }
    )
    envelope_path = out_dir / f"{name}.envelope.json"
    tmp_envelope = envelope_path.with_suffix(".json.tmp")
    tmp_envelope.write_text(
        json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8"
    )
    tmp_envelope.replace(envelope_path)
    return digest


def _auth_headers(credential_provider: EnvAlpacaCredentialProvider) -> Dict[str, str]:
    try:
        creds = credential_provider.load()
    except AlpacaCredentialError as exc:
        raise DataContractError(f"RI01_PROBE_CREDENTIALS_UNAVAILABLE: {exc}.") from exc
    return {
        "APCA-API-KEY-ID": creds.api_key_id,
        "APCA-API-SECRET-KEY": creds.api_secret_ref,
    }


class RI01ProbeClient:
    """Minimal read-only Alpaca client for the R1 probe (injectable transport)."""

    def __init__(
        self,
        credential_provider: Optional[EnvAlpacaCredentialProvider] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._credential_provider = credential_provider or EnvAlpacaCredentialProvider()
        self._http = httpx.Client(transport=transport, timeout=30.0)
        self.requests_issued = 0

    def fetch_bars(
        self, session: date, calendar: NyseCa1Calendar
    ) -> Tuple[bytes, List[Dict[str, Any]], Dict[str, str]]:
        """Fetch one session of 1Min SIP raw bars, paginated to exhaustion.

        Returns (concatenated raw page bytes, validated bar mappings,
        rate-limit headers). Any 401/403 fails closed as an entitlement
        signal with NOTHING recorded.
        """
        bounds_session = calendar.get_session(session)
        if bounds_session.open_utc is None or bounds_session.close_utc is None:
            raise DataContractError(f"RI01_SESSION_BOUNDS_MISSING: {session.isoformat()}.")
        params: Dict[str, Any] = {
            "symbols": PROBE_SYMBOL,
            "timeframe": PROBE_TIMEFRAME,
            "start": bounds_session.open_utc.isoformat(),
            "end": bounds_session.close_utc.isoformat(),
            "feed": PROBE_FEED,
            "adjustment": PROBE_ADJUSTMENT,
            "sort": "asc",
            "limit": 1000,
        }
        raw_pages: List[bytes] = []
        bars: List[Dict[str, Any]] = []
        rate_limits: Dict[str, str] = {}
        page_token: Optional[str] = None
        while True:
            if page_token is not None:
                params["page_token"] = page_token
            self.requests_issued += 1
            response = self._http.get(
                f"{DATA_HOST}/v2/stocks/bars",
                params=params,
                headers=_auth_headers(self._credential_provider),
            )
            if response.status_code in (401, 403):
                raise DataContractError(
                    "RI01_PROBE_ENTITLEMENT_DENIED: credentials lack historical "
                    f"SIP access (HTTP {response.status_code})."
                )
            if response.status_code != 200:
                raise DataContractError(
                    f"RI01_PROBE_BARS_HTTP_{response.status_code}."
                )
            raw_pages.append(response.content)
            for header in ("ratelimit_limit", "ratelimit_remaining", "ratelimit_reset"):
                if header in response.headers and header not in rate_limits:
                    rate_limits[header] = response.headers[header]
            try:
                doc = response.json()
            except ValueError as exc:
                raise DataContractError(f"RI01_PROBE_BARS_CORRUPT: {exc}.") from exc
            entries = doc.get("bars", {}).get(PROBE_SYMBOL, [])
            if not isinstance(entries, list):
                raise DataContractError("RI01_PROBE_BARS_MALFORMED.")
            for position, entry in enumerate(entries):
                if not isinstance(entry, Mapping):
                    raise DataContractError("RI01_PROBE_BAR_NOT_A_MAPPING.")
                bars.append(
                    validate_provider_bar(
                        {
                            "timestamp": entry.get("t"),
                            "open": entry.get("o"),
                            "high": entry.get("h"),
                            "low": entry.get("l"),
                            "close": entry.get("c"),
                            "volume": entry.get("v"),
                        },
                        f"{session.isoformat()}[{position}]",
                    )
                )
            page_token = doc.get("next_page_token")
            if not page_token:
                break
        return b"".join(raw_pages), bars, rate_limits

    def fetch_trades_window(
        self, window_start_utc: datetime, window_end_utc: datetime
    ) -> Tuple[bytes, List[ProbeTrade]]:
        """Fetch historical SIP trades in a narrow window, provenance intact.

        Returns (raw bytes, parsed trades). Empty windows are valid data
        (zero trades recorded), never an error.
        """
        if window_start_utc.tzinfo is None or window_end_utc.tzinfo is None:
            raise DataContractError("RI01_PROBE_WINDOW_NAIVE_TIME.")
        if not window_start_utc < window_end_utc:
            raise DataContractError("RI01_PROBE_WINDOW_INVERTED.")
        params: Dict[str, Any] = {
            "symbols": PROBE_SYMBOL,
            "start": window_start_utc.isoformat(),
            "end": window_end_utc.isoformat(),
            "feed": PROBE_FEED,
            "sort": "asc",
            "limit": 1000,
        }
        self.requests_issued += 1
        response = self._http.get(
            f"{DATA_HOST}/v2/stocks/trades",
            params=params,
            headers=_auth_headers(self._credential_provider),
        )
        if response.status_code in (401, 403):
            raise DataContractError(
                "RI01_PROBE_ENTITLEMENT_DENIED: credentials lack historical "
                f"SIP access (HTTP {response.status_code})."
            )
        if response.status_code != 200:
            raise DataContractError(f"RI01_PROBE_TRADES_HTTP_{response.status_code}.")
        try:
            doc = response.json()
        except ValueError as exc:
            raise DataContractError(f"RI01_PROBE_TRADES_CORRUPT: {exc}.") from exc
        entries = doc.get("trades", {}).get(PROBE_SYMBOL, [])
        if not isinstance(entries, list):
            raise DataContractError("RI01_PROBE_TRADES_MALFORMED.")
        trades = [
            ProbeTrade.from_dict(entry, f"trades[{position}]")
            for position, entry in enumerate(entries)
        ]
        return response.content, trades


def _validate_scope(
    sessions: List[date], capabilities: List[str], calendar: NyseCa1Calendar
) -> None:
    if not sessions:
        raise DataContractError("RI01_PROBE_NO_SESSIONS.")
    for session in sessions:
        if session >= HOLDOUT_START:
            raise DataContractError(
                f"RI01_PROBE_HOLDOUT_FORBIDDEN: {session.isoformat()} is in the "
                "sealed 2023-2026 holdout."
            )
        if session not in ALLOWLISTED_SESSIONS:
            raise DataContractError(
                f"RI01_PROBE_SESSION_NOT_ALLOWLISTED: {session.isoformat()}."
            )
        if not calendar.is_trading_session(session):
            raise DataContractError(
                f"RI01_PROBE_NON_SESSION: {session.isoformat()}."
            )
    for capability in capabilities:
        if capability not in CAPABILITIES:
            raise DataContractError(
                f"RI01_PROBE_UNKNOWN_CAPABILITY: {capability}."
            )


def main(
    argv: List[str] | None = None,
    _transport: Optional[httpx.BaseTransport] = None,
    _now_utc: Optional[datetime] = None,
    _out_dir: Optional[Path] = None,
    _credential_provider: Optional[EnvAlpacaCredentialProvider] = None,
) -> int:
    parser = argparse.ArgumentParser(description="RI-01 provider probe R1 (bounded, zero-outcome).")
    parser.add_argument("--execute-network", action="store_true", default=False)
    parser.add_argument("--authorization", default="")
    parser.add_argument("--session", action="append", default=[])
    parser.add_argument("--capability", action="append", default=[])
    args = parser.parse_args(argv)

    calendar = NyseCa1Calendar()
    try:
        sessions = [date.fromisoformat(str(raw)) for raw in args.session]
    except (ValueError, TypeError) as exc:
        raise DataContractError(f"RI01_PROBE_BAD_SESSION: {exc}.") from exc
    capabilities = list(args.capability) or ["bars"]

    # Scope is validated BEFORE any network, in every mode.
    _validate_scope(sessions, capabilities, calendar)

    if not args.execute_network:
        print("RI01-PROBE-DRY-RUN: zero network. Scope validated.")
        print(f"SYMBOL = {PROBE_SYMBOL}")
        for session in sessions:
            print(f"SESSION = {session.isoformat()}")
        for capability in capabilities:
            print(f"CAPABILITY = {capability}")
        print("NETWORK_REQUESTS = 0")
        return 0

    if not args.authorization or not args.authorization.startswith(
        "AUTHORIZE_RI01_PROBE_R1_"
    ):
        raise DataContractError(
            "RI01_PROBE_AUTHORIZATION_REQUIRED: live probe needs an explicit "
            "AUTHORIZE_RI01_PROBE_R1_* authority."
        )
    out_dir = _out_dir if _out_dir is not None else Path("data/ri01/probe_r1")
    now_utc = _now_utc if _now_utc is not None else datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        raise DataContractError("RI01_PROBE_NOW_NAIVE_TIME.")
    client = RI01ProbeClient(
        credential_provider=_credential_provider, transport=_transport
    )
    for session in sessions:
        if "bars" in capabilities:
            raw, bars, rate_limits = client.fetch_bars(session, calendar)
            digest = write_envelope(
                out_dir / session.isoformat(),
                "bars_1min_sip_raw",
                raw,
                {
                    "symbol": PROBE_SYMBOL,
                    "session": session.isoformat(),
                    "timeframe": PROBE_TIMEFRAME,
                    "feed": PROBE_FEED,
                    "adjustment": PROBE_ADJUSTMENT,
                    "rate_limits": rate_limits,
                    "authorization": args.authorization,
                },
                now_utc,
            )
            require_complete_rth_grid(
                bars, session, calendar, f"{session.isoformat()}/bars"
            )
            print(f"BARS {session.isoformat()}: {len(bars)} bars, sha256={digest}")
        if "trades" in capabilities:
            bounds = calendar.get_session(session)
            if bounds.open_utc is None or bounds.close_utc is None:
                raise DataContractError(
                    f"RI01_SESSION_BOUNDS_MISSING: {session.isoformat()}."
                )
            # Narrow ±5-minute probe windows around open/close. Widths are
            # probe-bounding choices (limit bytes transferred), NOT research
            # parameters and NOT preregistered signal windows.
            for label, anchor in (
                ("open", bounds.open_utc),
                ("close", bounds.close_utc),
            ):
                window_start = anchor - timedelta(minutes=5)
                window_end = anchor + timedelta(minutes=5)
                raw_trades, trades = client.fetch_trades_window(
                    window_start, window_end
                )
                digest = write_envelope(
                    out_dir / session.isoformat(),
                    f"trades_sip_window_{label}",
                    raw_trades,
                    {
                        "symbol": PROBE_SYMBOL,
                        "session": session.isoformat(),
                        "window": label,
                        "window_start_utc": window_start.isoformat(),
                        "window_end_utc": window_end.isoformat(),
                        "feed": PROBE_FEED,
                        "trade_count": len(trades),
                        "authorization": args.authorization,
                    },
                    now_utc,
                )
                print(
                    f"TRADES {session.isoformat()}/{label}: {len(trades)} trades, "
                    f"sha256={digest}"
                )
    print(f"NETWORK_REQUESTS_ISSUED = {client.requests_issued}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
