"""POSIX-host credential lookup (the Homelab collector) without a secrets file."""

from __future__ import annotations

import sys

import pytest

from acash.invest import market_authority as ma


def test_environment_store_reads_the_provider_variable() -> None:
    store = ma.EnvironmentCredentialStore({"ACASH_MARKET_DATA_MASSIVE_BASIC": "abc123"})
    assert store.lookup("MASSIVE_BASIC") == ("", "abc123")
    assert store.lookup("ALPACA_BASIC") is None


def test_environment_store_honours_vendor_aliases_only_for_the_secret() -> None:
    store = ma.EnvironmentCredentialStore({"ACASH_MARKET_DATA_BOT_EXCHANGE_RATES": "bot-key"})
    assert store.lookup("BOT_REFERENCE_FX") == ("", "bot-key")
    store = ma.EnvironmentCredentialStore({"ACASH_MARKET_DATA_BOT_OTHERS": "others-key"})
    assert store.lookup("BOT_HOLIDAYS") == ("", "others-key")


def test_environment_store_refuses_unknown_providers_and_empty_values() -> None:
    store = ma.EnvironmentCredentialStore({"ACASH_MARKET_DATA_NOT_A_PROVIDER": "x",
                                          "ACASH_MARKET_DATA_ALPACA_BASIC": ""})
    assert store.lookup("NOT_A_PROVIDER") is None
    assert store.lookup("ALPACA_BASIC") is None


def test_default_store_matches_the_host() -> None:
    store = ma.default_credential_store()
    expected = ma.WindowsCredentialStore if sys.platform == "win32" else ma.EnvironmentCredentialStore
    assert isinstance(store, expected)
