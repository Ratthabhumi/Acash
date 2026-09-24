# tests/unit/data/qualification/test_hyp_009_daily_client.py
"""Tests for the HYP009AlpacaClient (daily SIP qualification)."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock

import pytest

from acash.data.qualification.hyp_009_daily_client import HYP009AlpacaClient
from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider, AlpacaCredentials
from acash.data.qualification.models import SipContractViolationError, SipRetrievalResult
from acash.data.qualification.daily_models import DailyBar


# Helper mock response
class MockResponse:
    def __init__(self, json_data, status_code=200, headers=None):
        self._json = json_data
        self.status_code = status_code
        self.headers = headers or {}
        self.content = json.dumps(json_data).encode()

    def json(self):
        return self._json


def make_dummy_credentials():
    creds = AlpacaCredentials()
    creds.resolved = True
    creds.api_key_id = "dummy_key"
    creds.api_secret_ref = "dummy_secret"
    return creds


def test_fetch_historical_bars_success(monkeypatch):
    # Arrange
    client = HYP009AlpacaClient()
    start = datetime(2016, 1, 1, tzinfo=timezone.utc)
    end = datetime(2016, 1, 2, tzinfo=timezone.utc)

    # Mock credential provider
    dummy_creds = make_dummy_credentials()
    monkeypatch.setattr(EnvAlpacaCredentialProvider, "load", lambda self: dummy_creds)

    # Mock HTTP response
    bar_timestamp = "2016-01-01T00:00:00Z"
    mock_payload = {
        "bars": [
            {"t": bar_timestamp, "o": "200.0", "h": "210.0", "l": "190.0", "c": "205.0", "v": "1000000"}
        ]
    }
    mock_resp = MockResponse(mock_payload)
    mock_client = mock.Mock()
    mock_client.get.return_value = mock_resp
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: mock_client)

    # Act
    result: SipRetrievalResult = client.fetch_historical_bars(
        symbol="SPY",
        start_utc=start,
        end_utc=end,
    )

    # Assert
    assert isinstance(result, SipRetrievalResult)
    assert len(result.bars) == 1
    bar: DailyBar = result.bars[0]
    assert isinstance(bar, DailyBar)
    assert bar.timestamp_utc == datetime.fromisoformat(bar_timestamp.replace("Z", "+00:00"))
    assert bar.open == Decimal("200.0")
    assert bar.high == Decimal("210.0")
    assert bar.low == Decimal("190.0")
    assert bar.close == Decimal("205.0")
    assert bar.volume == Decimal("1000000")


def test_invalid_timeframe_raises():
    client = HYP009AlpacaClient()
    start = datetime(2016, 1, 1, tzinfo=timezone.utc)
    end = datetime(2016, 1, 2, tzinfo=timezone.utc)
    with pytest.raises(SipContractViolationError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=start,
            end_utc=end,
            timeframe="1Min",  # wrong timeframe
        )
