"""SETUP-MARKET-DATA.bat + credentials_setup: interactive, hidden input, Windows Credential Manager.

Synthetic only: no real Owner credential is touched and no test sends a byte to a provider.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import market_authority as ma
from acash.invest.capacity_plan import CAPACITY_SCHEMA
from acash.market_data import credentials_setup as cs
from acash.market_data import providers as mp
from acash.ppds import private_observation as po

SECRET = "SYNSECRETVALUENEVERPRINTED"
KEYID = "SYNKEYID"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A checkout whose ODR-004 scope is still empty: nothing here authorises egress."""
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(ma, "_repo_root", lambda: tmp_path)
    (tmp_path / po.AUTHORIZATION_RECORD).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / po.AUTHORIZATION_RECORD).write_text(json.dumps(
        {"capability": po.AUTHORIZED_CAPABILITY, "status": "RATIFIED", "ratified_by": "OWNER",
         "ratified_on": "2026-11-02", "scope_schemas": [po.SCHEMA_V1_2, CAPACITY_SCHEMA]}), encoding="utf-8")
    (tmp_path / ma.RECORD).write_text(json.dumps(
        {"decision_id": ma.DECISION_ID, "capability": ma.CAPABILITY, "status": "RATIFIED", "ratified_by": "OWNER",
         "ratified_on": "2026-11-03", "requires": list(ma.REQUIRES), "scope_providers": []}), encoding="utf-8")
    return tmp_path


class SharedStore:
    """Stand-in for the Windows Credential Manager: the writer and the reader are the same store."""

    def __init__(self) -> None:
        self.creds: Dict[str, Tuple[str, str]] = {}

    def lookup(self, provider_id: str) -> Optional[Tuple[str, str]]:
        return self.creds.get(provider_id)

    def store(self, provider_id: str, credential: Tuple[str, str]) -> str:
        self.creds[provider_id] = credential
        return ma.credential_target(provider_id)

    def remove(self, provider_id: str) -> bool:
        return self.creds.pop(provider_id, None) is not None


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> SharedStore:
    shared = SharedStore()
    monkeypatch.setattr(ma, "WindowsCredentialStore", lambda: shared)
    monkeypatch.setattr(ma, "WindowsCredentialWriter", lambda: shared)
    return shared


def test_setup_requires_a_real_terminal_and_never_falls_back_to_visible_input(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"{SECRET}\n"))
    assert not sys.stdin.isatty()
    with pytest.raises(DataContractError, match="INPUT_TERMINAL_UNAVAILABLE"):
        cs._hidden("API Secret Key")
    with pytest.raises(DataContractError, match="INPUT_TERMINAL_UNAVAILABLE"):
        cs._visible("API Key ID")


def test_configure_stores_and_reads_back_without_printing_the_secret(
        monkeypatch: pytest.MonkeyPatch, store: SharedStore, capsys: pytest.CaptureFixture[str]) -> None:
    answers = iter([KEYID, SECRET])
    monkeypatch.setattr(cs, "_visible", lambda prompt: next(answers))
    monkeypatch.setattr(cs, "_hidden", lambda prompt: next(answers))
    target = cs._configure(store, "ALPACA_BASIC", (("API Key ID", False), ("API Secret Key", True)))
    assert target == "ACASH/MARKET_DATA/ALPACA_BASIC"
    assert store.creds["ALPACA_BASIC"] == (KEYID, SECRET)
    assert SECRET not in capsys.readouterr().out


def test_configure_refuses_empty_values(monkeypatch: pytest.MonkeyPatch, store: SharedStore) -> None:
    monkeypatch.setattr(cs, "_visible", lambda prompt: KEYID)
    monkeypatch.setattr(cs, "_hidden", lambda prompt: "")
    with pytest.raises(DataContractError, match="CREDENTIAL_INVALID"):
        cs._configure(store, "ALPACA_BASIC", (("API Key ID", False), ("API Secret Key", True)))
    assert store.creds == {}


def test_status_rows_report_state_without_any_secret(root: Path, store: SharedStore) -> None:
    store.creds["ALPACA_BASIC"] = (KEYID, SECRET)
    rows = "\n".join(cs.status_rows(store))
    assert "ODR-004: RATIFIED" in rows and "ALPACA_BASIC" in rows
    assert SECRET not in rows and KEYID not in rows


def test_connection_test_is_refused_before_any_egress_when_scope_is_empty(
        root: Path, store: SharedStore, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[Any] = []

    def fake_transport(request: Any) -> Tuple[int, bytes]:
        calls.append(request)
        return 200, b"{}"

    monkeypatch.setattr(mp, "urllib_transport", fake_transport)
    store.creds["ALPACA_BASIC"] = (KEYID, SECRET)
    result = cs._test_connection("ALPACA_BASIC")
    assert result.startswith("REFUSED")
    assert calls == []


def test_connection_test_refuses_keyless_and_unknown_providers(root: Path, store: SharedStore) -> None:
    assert cs._test_connection("MASSIVE_BASIC").startswith("REFUSED")


def test_launcher_starts_the_module_without_secrets_on_the_command_line() -> None:
    text = Path("SETUP-MARKET-DATA.bat").read_text(encoding="utf-8")
    assert "acash.market_data.credentials_setup" in text
    executable = "\n".join(line for line in text.splitlines() if not line.strip().startswith("rem"))
    for banned in ("cmdkey", "/user:", "/password:", ".env", "set APCA", "set ACASH_TOKEN"):
        assert banned not in executable


def test_setup_module_holds_no_trading_surface() -> None:
    text = Path(str(cs.__file__)).read_text(encoding="utf-8")
    for banned in ("/v2/orders", "/v2/account", "/v2/positions", "paper-api", "api.alpaca.markets",
                   "import socket", "import subprocess"):
        assert banned not in text


def test_openfigi_is_a_separate_identity_provider_with_its_own_target(
        monkeypatch: pytest.MonkeyPatch, store: SharedStore, capsys: pytest.CaptureFixture[str]) -> None:
    ids = [row[0] for row in cs.KEYED_PROVIDERS]
    assert "OPENFIGI_IDENTITY" in ids and "ALPACA_BASIC" in ids
    monkeypatch.setattr(ma, "identity_credential", lambda provider_id="OPENFIGI_IDENTITY": store.lookup(provider_id))
    monkeypatch.setattr(cs, "_hidden", lambda prompt: "SYNTHETIC_OPENFIGI_KEY_NEVER_REAL")
    target = cs._configure(store, "OPENFIGI_IDENTITY", (("OpenFIGI API Key", True),))
    assert target == "ACASH/IDENTITY/OPENFIGI_IDENTITY"
    assert store.creds["OPENFIGI_IDENTITY"] == ("OPENFIGI_IDENTITY", "SYNTHETIC_OPENFIGI_KEY_NEVER_REAL")
    assert "SYNTHETIC_OPENFIGI_KEY_NEVER_REAL" not in capsys.readouterr().out
    rows = "\n".join(cs.status_rows(store))
    assert "OPENFIGI_IDENTITY" in rows


def test_replace_and_remove_ask_for_the_provider_instead_of_defaulting_to_alpaca(
        monkeypatch: pytest.MonkeyPatch, store: SharedStore) -> None:
    monkeypatch.setattr(cs, "_visible", lambda prompt: "2")
    provider_id, fields = cs._choose_provider("Provider to replace")
    assert provider_id == "MARKETDATA_APP_FREE"  # explicit selection, never a hidden Alpaca default
    assert fields
    monkeypatch.setattr(cs, "_visible", lambda prompt: "not-a-number")
    with pytest.raises(DataContractError, match="PROVIDER_CHOICE_INVALID"):
        cs._choose_provider("Provider to remove")


def test_massive_and_bot_are_configurable_and_bot_refuses_the_legacy_contract() -> None:
    ids = [row[0] for row in cs.KEYED_PROVIDERS]
    assert "MASSIVE_BASIC" in ids and "BOT_EXCHANGE_RATES" in ids and "BOT_OTHERS" in ids
    result = cs._test_connection("BOT_EXCHANGE_RATES")
    assert result.startswith(("REFUSED_NOT_READY", "REFUSED_CONTRACT_UNVERIFIED"))


def test_menu_lists_every_keyed_provider_and_a_stable_exit() -> None:
    items = cs.menu_items()
    labels = " ".join(items.values())
    for provider_id in ("ALPACA_BASIC", "MARKETDATA_APP_FREE", "OPENFIGI_IDENTITY",
                        "MASSIVE_BASIC", "BOT_EXCHANGE_RATES", "BOT_INTEREST_RATES", "BOT_STATISTICS",
                        "BOT_DEBT_AUCTION", "BOT_LICENSE_CHECK", "BOT_OTHERS"):
        assert provider_id in labels
    base = len(cs.KEYED_PROVIDERS)
    assert items[str(base + 1)] == "Check Credential Status"
    assert items[str(base + 5)] == "Exit"
    assert str(base + 5) == "15"


def test_bot_product_credentials_are_retrievable_for_setup_readback(monkeypatch: pytest.MonkeyPatch) -> None:
    """A BOT product has no adapter yet, but setup must still read back what it just stored."""
    import acash.invest.market_authority as auth

    seen = {}

    def fake_read(target: str):
        seen["target"] = target
        return ("BOT_OTHERS", "SYNTHETIC_BOT_KEY") if target.endswith("BOT_OTHERS") else None

    monkeypatch.setattr(auth, "_cred_read", fake_read)
    assert auth.WindowsCredentialStore().lookup("BOT_OTHERS") == ("BOT_OTHERS", "SYNTHETIC_BOT_KEY")
    assert seen["target"] == "ACASH/MARKET_DATA/BOT_OTHERS"
    assert auth.WindowsCredentialStore().lookup("NOT_A_PROVIDER") is None
