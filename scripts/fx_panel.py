"""Build the BOT USD/THB reference series and the THB return decomposition for the held universe.

Reads the *stored* daily bars (so this only works once the warehouse is permitted to persist), fetches
the reference FX series from BOT in bounded chunks, and writes two private research artifacts:

    data/private/market_warehouse/fx/usd_thb_series.json
    data/private/market_warehouse/fx/decomposition.json

No price is fabricated, no missing FX date is forward-filled, and the BOT rate is a reference rate —
never an executable brokerage conversion.

    uv run python scripts/fx_panel.py --start 2025-03-28 --end 2026-11-03
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.dashboard_api.private_input import RateLimiter  # noqa: E402
from acash.invest import fx_series as fx  # noqa: E402
from acash.invest import market_authority as ma  # noqa: E402
from acash.market_data import providers as mp  # noqa: E402
from acash.market_data import warehouse as wh  # noqa: E402

PRIVATE = ROOT / "data" / "private"
WAREHOUSE = PRIVATE / "market_warehouse"
NON_US = {"SCBSET50", "MTS-GOLD"}


def held_symbols() -> List[str]:
    snapshot = json.loads((PRIVATE / "snapshot.json").read_text(encoding="utf-8"))
    return sorted({str(sec["security_id"]) for sec in snapshot["securities"]
                   if sec.get("figi") and str(sec["security_id"]) not in NON_US})


def weights(symbols: List[str]) -> Dict[str, Decimal]:
    snapshot = json.loads((PRIVATE / "snapshot.json").read_text(encoding="utf-8"))
    values: Dict[str, Decimal] = {}
    for account in snapshot["accounts"]:
        for position in account.get("positions") or []:
            symbol = str(position["security_id"])
            if symbol in symbols and position.get("observed_market_value_currency") == "USD":
                values[symbol] = values.get(symbol, Decimal(0)) + Decimal(str(position["observed_market_value"]))
    total = sum(values.values(), Decimal(0))
    return {symbol: value / total for symbol, value in values.items() if total > 0}


def main() -> int:
    parser = argparse.ArgumentParser(description="BOT reference FX series and THB decomposition.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--chunk-days", type=int, default=31)
    args = parser.parse_args()

    store = wh.BarWarehouse(WAREHOUSE, record=ROOT / ma.RECORD)
    symbols = [s for s in held_symbols() if store.partition(s).is_file()]
    if not symbols:
        print(json.dumps({"status": "NO_STORED_BARS", "detail": "run the persistent backfill first"}))
        return 2
    closes: Dict[str, Dict[date, Decimal]] = {}
    for symbol in symbols:
        closes[symbol] = {day: bar.close for day, bar in store.read(symbol).items()}
    common = sorted(set.intersection(*(set(series) for series in closes.values())))
    end = date.fromisoformat(args.end) if args.end else common[-1]
    start = date.fromisoformat(args.start) if args.start else common[0]
    credential = ma.default_credential_store().lookup("BOT_EXCHANGE_RATES")
    if credential is None:
        print(json.dumps({"status": "FX_CREDENTIAL_MISSING", "provider_id": "BOT_EXCHANGE_RATES"}))
        return 2
    provider = mp.BOTReferenceFXProvider(credential, mp.urllib_transport,
                                         RateLimiter(200, time.monotonic, 3600).allow, lambda: datetime.now(timezone.utc))
    series = fx.collect_series(provider, start, end, chunk_days=args.chunk_days)
    weights_by_symbol = weights(symbols)
    excluded = sorted(s for s in symbols if s not in weights_by_symbol)
    usable = {symbol: closes[symbol] for symbol in symbols if symbol in weights_by_symbol}
    if not usable:
        print(json.dumps({"status": "INSUFFICIENT_EVIDENCE", "detail": "no established weight for any held symbol"}))
        return 2
    decomposition = fx.decompose(usable, series.rates(), [day for day in common if start <= day <= end])
    summary = decomposition.summary(weights_by_symbol)
    fx.write_series(series, summary)
    out: Dict[str, Any] = {
        "status": "OK",
        "series": {k: series.summary()[k] for k in ("source", "first", "last", "points", "weekday_gaps")},
        "decomposition": {"sessions": summary["sessions"], "first": summary["first"], "last": summary["last"],
                          "portfolio": summary["portfolio"]},
        "instruments": len(summary["instruments"]),
        "excluded_no_weight": excluded,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
