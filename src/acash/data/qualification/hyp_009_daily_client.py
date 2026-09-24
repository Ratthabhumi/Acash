# src/acash/data/qualification/hyp_009_daily_client.py
"""HYP 009‑specific Alpaca client for daily SIP bars.

This client mirrors :class:`AlpacaHistoricalSipClient` but:
- enforces ``timeframe='1Day'`` (daily bars)
- returns a list of :class:`DailyBar` DTOs defined in ``daily_models.py``
- preserves the strict request contract (feed=SIP, adjustment=RAW)
- raises the same contract‑violation errors for any deviation.

No changes are made to the existing ``AlpacaHistoricalSipClient`` – this
implementation lives in a separate module so that HYP 003 codepaths are
completely untouched.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

import httpx
import time

from acash.core.domain.exceptions import DataContractError
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    AlpacaCredentialProvider,
    EnvAlpacaCredentialProvider,
    AlpacaCredentials,
)
from acash.data.qualification.guard import FifteenMinuteAccessGuard
from acash.data.qualification.manifest import compute_page_sha256
from acash.data.qualification.models import (
    MarketDataFeed,
    PriceAdjustment,
    SipPageMetadata,
)
from acash.data.qualification.client import SipRetrievalResult
from acash.data.qualification.client import SipContractViolationError
from acash.data.qualification.daily_models import DailyBar


class HYP009AlpacaClient:
    """Client for fetching **daily** SIP bars via Alpaca.

    The semantics are identical to :class:`AlpacaHistoricalSipClient` except
    that the ``timeframe`` is fixed to ``'1Day'`` and the returned bar objects
    are instances of :class:`DailyBar`.
    """

    def __init__(
        self,
        credential_provider: Optional[AlpacaCredentialProvider] = None,
        guard: Optional[FifteenMinuteAccessGuard] = None,
        base_url: str = "https://data.alpaca.markets",
        transport: Optional[httpx.BaseTransport] = None,
        max_pages: int = 50,
        max_retries_429: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self._credentials_provider = credential_provider or EnvAlpacaCredentialProvider()
        self._guard = guard or FifteenMinuteAccessGuard()
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._max_pages = max_pages
        self._max_retries_429 = max_retries_429
        self._retry_delay_seconds = retry_delay_seconds

    def _get_auth_headers(self) -> Dict[str, str]:
        creds: AlpacaCredentials = self._credentials_provider.load()
        if not creds.resolved or not creds.api_key_id:
            raise AlpacaCredentialError(
                "Alpaca API credentials are not resolved; refusing request (fail-closed)."
            )
        return {
            "APCA-API-KEY-ID": creds.api_key_id,
            "APCA-API-SECRET-KEY": creds.api_secret_ref,
            "Accept": "application/json",
        }

    def fetch_historical_bars(
        self,
        symbol: str,
        start_utc: datetime,
        end_utc: datetime,
        feed: MarketDataFeed = MarketDataFeed.SIP,
        adjustment: PriceAdjustment = PriceAdjustment.RAW,
        timeframe: str = "1Day",
        limit: int = 10000,
        asof: Optional[str] = None,
    ) -> SipRetrievalResult:
        """Fetch daily SIP bars with *strict* contract enforcement.
        """
        if feed != MarketDataFeed.SIP:
            raise SipContractViolationError(
                f"Daily SIP client requires feed='sip', got '{feed}'."
            )
        if adjustment != PriceAdjustment.RAW:
            raise SipContractViolationError(
                f"Daily SIP client requires adjustment='raw', got '{adjustment}'."
            )
        if timeframe != "1Day":
            raise SipContractViolationError(
                f"Daily SIP client requires timeframe='1Day', got '{timeframe}'."
            )

        self._guard.validate_requested_end(end_utc)

        sym = symbol.strip().upper()
        if not sym:
            raise DataContractError("Symbol must be a non‑empty string.")

        start_str = start_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        url = f"{self._base_url}/v2/stocks/{sym}/bars"
        headers = self._get_auth_headers()

        pages_raw_bytes: List[bytes] = []
        pages_metadata: List[SipPageMetadata] = []
        all_bars: List[DailyBar] = []
        next_page_token: Optional[str] = None
        page_index = 0
        last_status_code = 0
        last_headers: Dict[str, str] = {}

        with httpx.Client(transport=self._transport) as client:
            while True:
                page_index += 1
                if page_index > self._max_pages:
                    raise DataContractError(
                        f"Pagination exceeded maximum allowed pages ({self._max_pages}); aborting."
                    )

                params: Dict[str, Any] = {
                    "timeframe": timeframe,
                    "feed": feed.value,
                    "adjustment": adjustment.value,
                    "start": start_str,
                    "end": end_str,
                    "limit": limit,
                    "sort": "asc",
                }
                if asof:
                    params["asof"] = asof.strip()
                if next_page_token:
                    params["page_token"] = next_page_token

                response = self._execute_request_with_retry(client, url, headers, params)
                last_status_code = response.status_code
                last_headers = dict(response.headers)

                if response.status_code == 401:
                    raise AlpacaCredentialError("Alpaca authentication failed (HTTP 401).")
                if response.status_code == 403:
                    raise DataContractError("Alpaca access forbidden (HTTP 403). SIP feed denied.")
                if response.status_code != 200:
                    raise DataContractError(
                        f"Alpaca historical data query failed with HTTP status {response.status_code}."
                    )

                raw_bytes = response.content
                page_sha256 = compute_page_sha256(raw_bytes)
                pages_raw_bytes.append(raw_bytes)

                try:
                    payload = response.json()
                except Exception as e:
                    raise DataContractError(f"Failed to parse Alpaca response as JSON: {e}") from e

                raw_bars = payload.get("bars") or []
                if isinstance(raw_bars, dict):
                    raw_bars = raw_bars.get(sym, [])

                parsed_page = self._parse_daily_bars(raw_bars)
                all_bars.extend(parsed_page)

                token = payload.get("next_page_token")
                pages_metadata.append(
                    SipPageMetadata(
                        page_index=page_index,
                        bar_count=len(parsed_page),
                        raw_sha256=page_sha256,
                        byte_length=len(raw_bytes),
                        relative_artifact_path=f"page-{page_index:04d}.raw.json",
                        page_token=next_page_token,
                        next_page_token=token,
                    )
                )

                if not token or token == next_page_token:
                    break
                next_page_token = str(token)

        feed_provenance = "UNVERIFIED"
        for k, v in last_headers.items():
            if "feed" in k.lower() and "sip" in v.lower():
                feed_provenance = "FEED_CONFIRMED_IN_HEADER"
                break

        return SipRetrievalResult(
            bars=all_bars,
            pages_raw_bytes=pages_raw_bytes,
            pages_metadata=pages_metadata,
            http_status_code=last_status_code,
            response_headers=last_headers,
            feed_requested=feed.value,
            feed_response_provenance=feed_provenance,
            asof=asof,
        )

    def _execute_request_with_retry(
        self, client: httpx.Client, url: str, headers: Dict[str, str], params: Dict[str, Any]
    ) -> httpx.Response:
        retries = 0
        while True:
            try:
                resp = client.get(url, headers=headers, params=params, timeout=30.0)
                if resp.status_code == 429:
                    retries += 1
                    if retries > self._max_retries_429:
                        raise DataContractError(
                            f"Alpaca rate limit exceeded (HTTP 429). Retry budget ({self._max_retries_429}) exhausted."
                        )
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else self._retry_delay_seconds * (2 ** (retries - 1))
                    time.sleep(delay)
                    continue
                return resp
            except httpx.RequestError as e:
                raise DataContractError(f"HTTP request to Alpaca failed: {e}") from e

    def _parse_daily_bars(self, raw_bars: Sequence[Mapping[str, Any]]) -> List[DailyBar]:
        result: List[DailyBar] = []
        for item in raw_bars:
            t_str = str(item["t"])
            if t_str.endswith("Z"):
                t_str = t_str[:-1] + "+00:00"
            t_utc = datetime.fromisoformat(t_str).astimezone(timezone.utc)

            open_val = Decimal(str(item["o"]))
            high_val = Decimal(str(item["h"]))
            low_val = Decimal(str(item["l"]))
            close_val = Decimal(str(item["c"]))
            volume_val = Decimal(str(item["v"]))

            result.append(
                DailyBar(
                    timestamp_utc=t_utc,
                    open=open_val,
                    high=high_val,
                    low=low_val,
                    close=close_val,
                    volume=volume_val,
                )
            )
        return result
