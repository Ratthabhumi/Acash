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
from acash.market_data import openfigi as of
from acash.market_data import providers as mp

SAMPLE_SYMBOLS = ("AAPL", "VOO", "BIL")
KEYED_PROVIDERS: Tuple[Tuple[str, str, Tuple[Tuple[str, bool], ...]], ...] = (
    ("ALPACA_BASIC", "Alpaca market data (Key ID + Secret; shared read-only alias for historical)",
     (("API Key ID", False), ("API Secret Key", True))),
    ("MARKETDATA_APP_FREE", "MarketData.app Free Forever (API token, sent as a Bearer header only)",
     (("API Token", True),)),
    ("OPENFIGI_IDENTITY", "OpenFIGI identity API (candidate FIGI mapping; key sent as a header only)",
     (("OpenFIGI API Key", True),)),
    ("MASSIVE_BASIC", "Massive Stocks Basic (EOD and historical research; key sent as a header only)",
     (("Massive API Key", True),)),
    ("BOT_EXCHANGE_RATES", "BOT Exchange Rates (THB reference FX; header auth, 200 calls/hour)",
     (("BOT API Key", True),)),
    ("BOT_INTEREST_RATES", "BOT Interest Rates (policy/deposit/BIBOR; 200 calls/hour)",
     (("BOT API Key", True),)),
    ("BOT_STATISTICS", "BOT Statistics (Thai macro series; 2000 calls/hour)",
     (("BOT API Key", True),)),
    ("BOT_DEBT_AUCTION", "BOT Debt Securities Auction (bond auction results; 200 calls/hour)",
     (("BOT API Key", True),)),
    ("BOT_LICENSE_CHECK", "BOT License Check (financial-institution due diligence; 100 calls/hour)",
     (("BOT API Key", True),)),
    ("BOT_OTHERS", "BOT Others (financial institutions' holidays; 100 calls/hour)",
     (("BOT API Key", True),)),
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
    out.append(f"  {'OPENFIGI_IDENTITY':<20} {'CONFIGURED' if ma.identity_credential() is not None else 'NOT_CONFIGURED':<24} "
               "credentials=" + ("ESTABLISHED" if ma.identity_credential() is not None else "MISSING"))
    for product, state in ma.bot_product_credentials().items():
        out.append(f"  {product:<20} {'CREDENTIAL_CONFIGURED' if state == 'CONFIGURED' else 'NOT_CONFIGURED':<24} "
                   "adapter=CONTRACT_UNVERIFIED")
    return out


def _test_identity() -> str:
    """One bounded mapping request with the public demonstration ticker IBM; never Owner holdings."""
    key = ma.identity_credential()
    if key is None:
        return "REFUSED_NO_CREDENTIAL"
    provider = of.OpenFIGIIdentityProvider(key, of.urllib_post, lambda: True,
                                           lambda: datetime.now(timezone.utc))
    results = provider.map_identifiers("TICKER", ["IBM"], exchCode="US")
    if not results:
        return "NO_CANDIDATE"
    first = results[0]
    return (f"REAL_RESPONSE_OBSERVED candidates={len(first.candidates)} "
            f"state={first.status} (candidate only; Owner confirmation still required)")


def _configure(writer: Any, provider_id: str,
               fields: Tuple[Tuple[str, bool], ...]) -> str:
    """Read each field (hidden for secrets), store it, then verify only that it reads back."""
    values = [(_hidden if hidden else _visible)(label) for label, hidden in fields]
    if any(not v for v in values):
        raise DataContractError("CREDENTIAL_INVALID: empty value.")
    username, secret = (values[0], values[1]) if len(values) == 2 else (provider_id, values[0])
    target = writer.store(provider_id, (username, secret))
    back = (ma.identity_credential(provider_id) if provider_id in ma.IDENTITY_PROVIDERS
            else ma.WindowsCredentialStore().lookup(provider_id))
    if back is None or back != (username, secret):
        raise DataContractError("CREDENTIAL_READBACK_FAILED.")
    return str(target)


def _choose_provider(prompt: str) -> Tuple[str, Tuple[Tuple[str, bool], ...]]:
    """Explicit provider selection for replace/remove/test; never defaults to Alpaca."""
    for index, (provider_id, label, _) in enumerate(KEYED_PROVIDERS, start=1):
        print(f"    {index}. {provider_id} — {label}")
    choice = _visible(prompt)
    if not choice.isdigit() or not 1 <= int(choice) <= len(KEYED_PROVIDERS):
        raise DataContractError("PROVIDER_CHOICE_INVALID.")
    return KEYED_PROVIDERS[int(choice) - 1][0], KEYED_PROVIDERS[int(choice) - 1][2]


def _test_connection(provider_id: str) -> str:
    """Authorized sample request. Every gate is checked before a byte leaves the machine."""
    if provider_id in ma.BOT_PRODUCTS:
        return ("REFUSED_CONTRACT_UNVERIFIED: no verified adapter exists for this BOT product yet; "
                "the credential is stored but no live request is made")
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
    elif provider_id == "MASSIVE_BASIC":
        observations = mp.MassiveEODMarketDataProvider(credential or ("", ""), mp.urllib_transport, allow,
                                                       clock).latest_prices(["AAPL"], date.today())
    elif provider_id == "BOT_REFERENCE_FX" or provider_id in ma.BOT_PRODUCTS:
        return ("REFUSED_CONTRACT_UNVERIFIED: the BOT endpoint contract for this product has not been "
                "verified against the official schema; no live request is made")
    else:
        return "REFUSED_NO_SAMPLE_TEST_FOR_PROVIDER"
    return f"REAL_RESPONSE_OBSERVED: {len(observations)} observation(s); schema valid, timestamps preserved"


def menu_items() -> Dict[str, str]:
    """Menu grows with the provider list; every provider is configurable, never silently omitted."""
    items = {str(index): f"Configure {provider_id} — {label}"
             for index, (provider_id, label, _) in enumerate(KEYED_PROVIDERS, start=1)}
    base = len(KEYED_PROVIDERS)
    items[str(base + 1)] = "Check Credential Status"
    items[str(base + 2)] = "Test Authorized Provider Connection"
    items[str(base + 3)] = "Replace Existing Credentials"
    items[str(base + 4)] = "Remove Credentials"
    items[str(base + 5)] = "Exit"
    return items


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    writer = ma.WindowsCredentialWriter()
    print(_line())
    print("ACASH — SECURE MARKET DATA SETUP")
    print(_line())
    print("  Frankfurter ECB FX: KEYLESS_PROVIDER (no key required; ODR-004 and data-use gates still apply)")
    print("  Secrets are never displayed, logged, or written to a file.")
    menu = menu_items()
    while True:
        print()
        for key, label in menu.items():
            print(f"  {key}. {label}")
        try:
            choice = _visible("Choice")
        except DataContractError as exc:
            print(f"  {exc}")
            return 2
        count = len(KEYED_PROVIDERS)
        if choice == str(count + 5):
            return 0
        try:
            if choice.isdigit() and 1 <= int(choice) <= count:
                provider_id, _, fields = KEYED_PROVIDERS[int(choice) - 1]
                target = _configure(writer, provider_id, fields)
                print(f"  CREDENTIAL_CONFIGURED at {target} (this does not mean PROVIDER_READY)")
            elif choice == str(count + 1):
                for row in status_rows():
                    print(row)
            elif choice == str(count + 2):
                test_id, _fields = _choose_provider("Provider to test")
                print("  " + (_test_identity() if test_id in ma.IDENTITY_PROVIDERS
                              else _test_connection(test_id)))
            elif choice == str(count + 3):
                provider_id, fields = _choose_provider("Provider to replace")
                target = _configure(writer, provider_id, fields)
                print(f"  CREDENTIAL_CONFIGURED at {target} (replaced)")
            elif choice == str(count + 4):
                provider_id, _ = _choose_provider("Provider to remove")
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
