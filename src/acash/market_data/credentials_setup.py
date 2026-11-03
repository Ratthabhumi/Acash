"""Double-clickable market-data credential setup (``SETUP-MARKET-DATA.bat`` launches this).

Secrets are read with hidden terminal input and written straight into the current Windows user's
Credential Manager through ``market_authority`` — never into a command-line argument, a ``.env``
file, plaintext JSON, a log, or Git. Storing a credential only proves it is retrievable: it does
not prove entitlement, a working API key, or any data-use right, so this tool reports
``CREDENTIAL_CONFIGURED`` and never ``PROVIDER_READY``.

The authorized connection test refuses to send a single byte unless ODR-004 reports the provider
READY (ratified scope, verified contract, credential present, and every Owner attestation true)
and asks only for the public sample symbols AAPL, VOO and BIL.
"""

from __future__ import annotations

import getpass
import sys
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.invest import market_authority as ma
from acash.market_data import providers as mp

SAMPLE_SYMBOLS = ("AAPL", "VOO", "BIL")
KEYED_PROVIDERS: Tuple[Tuple[str, str, Tuple[Tuple[str, bool], ...]], ...] = (
    ("ALPACA_BASIC", "Alpaca market data (Key ID + Secret; shared read-only alias for historical)",
     (("API Key ID", False), ("API Secret Key", True))),
    ("MARKETDATA_APP_FREE", "MarketData.app Free Forever (API token, sent as a Bearer header only)",
     (("API Token", True),)),
)
PROVIDER_LABELS = {provider_id: label for provider_id, label, _ in KEYED_PROVIDERS}


def _line(char: str = "=", width: int = 60) -> str:
    return char * width


def _visible(prompt: str) -> str:
    if not sys.stdin.isatty():
        raise DataContractError("INPUT_TERMINAL_UNAVAILABLE: interactive terminal required.")
    return input(f"  {prompt}: ").strip()


def _hidden(prompt: str) -> str:
    """Hidden entry only. If the terminal cannot hide echo, refuse instead of showing the secret."""
    if not sys.stdin.isatty():
        raise DataContractError("INPUT_TERMINAL_UNAVAILABLE: interactive terminal required.")
    try:
        value = getpass.getpass(f"  {prompt} (input is hidden): ")
    except (EOFError, KeyboardInterrupt):
        raise DataContractError("INPUT_CANCELLED.") from None
    except Exception:  # no hidden echo support on this terminal: fail closed rather than echo
        raise DataContractError("INPUT_HIDDEN_UNAVAILABLE: terminal cannot mask input.") from None
    return value.strip()


def status_rows(store: Optional[ma.CredentialStore] = None) -> List[str]:
    store = store or ma.WindowsCredentialStore()
    state, statuses = ma.provider_statuses(store)
    out = [f"  ODR-004: {state}"]
    for entry in statuses:
        credentials = entry["capabilities"].get("credentials_configured", "UNKNOWN")
        out.append(f"  {entry['provider_id']:<20} {entry['status']:<24} credentials={credentials}")
    return out


def _configure(writer: Any, provider_id: str,
               fields: Tuple[Tuple[str, bool], ...]) -> str:
    """Read each field (hidden for secrets), store it, then verify only that it reads back."""
    values = [(_hidden if hidden else _visible)(label) for label, hidden in fields]
    if any(not v for v in values):
        raise DataContractError("CREDENTIAL_INVALID: empty value.")
    username, secret = (values[0], values[1]) if len(values) == 2 else (provider_id, values[0])
    target = writer.store(provider_id, (username, secret))
    back = ma.WindowsCredentialStore().lookup(provider_id)
    if back is None or back != (username, secret):
        raise DataContractError("CREDENTIAL_READBACK_FAILED.")
    return str(target)


def _test_connection(provider_id: str) -> str:
    """Authorized sample request. Every gate is checked before a byte leaves the machine."""
    store = ma.WindowsCredentialStore()
    state, statuses = ma.provider_statuses(store)
    entry = next((s for s in statuses if s["provider_id"] == provider_id), None)
    if entry is None:
        return "PROVIDER_NOT_REGISTERED"
    blockers = [k for k, v in entry["capabilities"].items() if v in ("MISSING", "DENIED", "UNKNOWN")]
    if state != "RATIFIED" or entry["status"] != "READY":
        return "REFUSED_NOT_READY: " + ", ".join(
            (["ODR_004_" + state] if state != "RATIFIED" else []) + blockers)
    credential = store.lookup(provider_id)
    if credential is None and provider_id not in ma.KEYLESS_PROVIDERS:
        return "REFUSED_NO_CREDENTIAL"
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    allow: Callable[[], bool] = lambda: True
    if provider_id == "ALPACA_BASIC":
        observations = mp.AlpacaIEXMarketDataProvider(credential or ("", ""), mp.urllib_transport, allow,
                                                     clock).latest_prices(list(SAMPLE_SYMBOLS),
                                                                          date.today())
    elif provider_id == "ALPACA_HISTORICAL":
        observations = mp.AlpacaHistoricalSIPProvider(credential or ("", ""), mp.urllib_transport, allow,
                                                     clock).latest_prices(list(SAMPLE_SYMBOLS), date.today())
    elif provider_id == "MARKETDATA_APP_FREE":
        observations = mp.MarketDataAppFreeProvider(credential or ("", ""), mp.urllib_transport, allow,
                                                    clock).latest_prices(list(SAMPLE_SYMBOLS), date.today())
    else:
        return "REFUSED_NO_SAMPLE_TEST_FOR_PROVIDER"
    return f"REAL_RESPONSE_OBSERVED: {len(observations)} observation(s); schema valid, timestamps preserved"


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    writer = ma.WindowsCredentialWriter()
    print(_line())
    print("ACASH — SECURE MARKET DATA SETUP")
    print(_line())
    print("  Frankfurter ECB FX: KEYLESS_PROVIDER (no key required; ODR-004 and data-use gates still apply)")
    print("  Secrets are never displayed, logged, or written to a file.")
    menu = {
        "1": "Configure Alpaca API",
        "2": "Configure MarketData.app API",
        "3": "Check Credential Status",
        "4": "Test Authorized Provider Connection",
        "5": "Replace Existing Credentials",
        "6": "Remove Credentials",
        "7": "Exit",
    }
    while True:
        print()
        for key, label in menu.items():
            print(f"  {key}. {label}")
        try:
            choice = _visible("Choice")
        except DataContractError as exc:
            print(f"  {exc}")
            return 2
        if choice == "7":
            return 0
        try:
            if choice in ("1", "2", "5"):
                provider_id, _, fields = KEYED_PROVIDERS[0 if choice in ("1", "5") else 1]
                target = _configure(writer, provider_id, fields)
                print(f"  CREDENTIAL_CONFIGURED at {target} (this does not mean PROVIDER_READY)")
            elif choice == "3":
                for row in status_rows():
                    print(row)
            elif choice == "4":
                provider_id = _visible("Provider id")
                print("  " + _test_connection(provider_id))
            elif choice == "6":
                provider_id = _visible("Provider id to remove")
                print("  REMOVED" if writer.remove(provider_id) else "  NOT_FOUND")
            else:
                print("  Unknown choice.")
        except DataContractError as exc:
            print(f"  REFUSED: {str(exc).split(':')[0]} (no secret is shown)")
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
