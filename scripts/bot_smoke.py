"""One authorized read-only BOT smoke test through the real adapters (no mock, no retry loop).

Prints only status/derived facts: no key, no header, no raw payload. Two requests total:

    uv run python scripts/bot_smoke.py --date 2026-11-03
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.invest import market_authority as ma  # noqa: E402
from acash.market_data import providers as mp  # noqa: E402

LIMIT = 200  # BOT publishes 200 calls/hour for this product family


def _allow() -> bool:
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="BOT read-only smoke test.")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    end = date.fromisoformat(args.date)
    store = ma.default_credential_store()
    out: dict = {"requested_date": end.isoformat(), "contract_verified": mp.BOT_CONTRACT_VERIFIED,
                 "live_response_verified": mp.BOT_LIVE_RESPONSE_VERIFIED}

    fx_cred = store.lookup("BOT_EXCHANGE_RATES")
    if fx_cred is None:
        out["fx"] = {"status": "CREDENTIAL_MISSING"}
    else:
        try:
            obs = mp.BOTReferenceFXProvider(fx_cred, mp.urllib_transport, _allow,
                                            lambda: datetime.now(timezone.utc)).reference_rates(end, 5)
            usd = [o for o in obs if o.from_currency == "USD"]
            out["fx"] = {"status": "OK", "observations": len(obs),
                         "dates": [o.market_date.isoformat() for o in usd],
                         "latest_usd_thb": str(usd[-1].rate) if usd else None,
                         "kind": "REFERENCE_FX_NOT_EXECUTABLE"}
        except Exception as error:  # evidence, not a crash: the code is the finding
            out["fx"] = {"status": type(error).__name__, "code": str(error)[:200]}

    hol_cred = store.lookup("BOT_OTHERS")
    if hol_cred is None:
        out["holidays"] = {"status": "CREDENTIAL_MISSING"}
    else:
        try:
            days = mp.BOTFinancialHolidaysProvider(hol_cred, mp.urllib_transport, _allow,
                                                   lambda: datetime.now(timezone.utc)).holidays(end.year)
            upcoming = [d for d in days if d.date >= end]
            out["holidays"] = {"status": "OK", "year": end.year, "count": len(days),
                               "next": [{"date": d.date.isoformat(), "name": d.name} for d in upcoming[:3]]}
        except Exception as error:
            out["holidays"] = {"status": type(error).__name__, "code": str(error)[:200]}

    print(json.dumps(out, indent=2, ensure_ascii=True))
    return 0 if out.get("fx", {}).get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
