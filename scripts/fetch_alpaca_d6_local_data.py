"""Fetch D6 LOCAL_EXPLORATORY inputs from the owner's Alpaca account (market data only).

Read-only GETs to data.alpaca.markets: daily raw bars (one fixed feed) and corporate
actions for VOO, BND, GLD and BIL. No trading endpoint is called. No retries, no feed
fallback. Raw pages and CSVs are written under the git-ignored data/ tree; the files
are for personal research and must not be redistributed. Credential values are never
printed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.local_alpaca import bar_rows, corporate_action_rows
from acash.research.step_r2_hyp_003 import resolve_alpaca_credentials

BASE_URL = "https://data.alpaca.markets"
SYMBOLS = ("BIL", "BND", "GLD", "VOO")
MAX_PAGES = 20


def _pages(client: httpx.Client, path: str, params: Dict[str, str], raw_dir: Path, tag: str) -> List[Any]:
    pages: List[Any] = []
    token = None
    while True:
        if len(pages) >= MAX_PAGES:
            raise DataContractError(f"PAGE_BUDGET_EXCEEDED: {tag}.")
        query = dict(params, **({"page_token": token} if token else {}))
        response = client.get(f"{BASE_URL}{path}", params=query)
        if response.status_code != 200:
            raise DataContractError(f"ALPACA_HTTP_{response.status_code}: {tag} {response.text[:200]}")
        (raw_dir / f"{tag}_page_{len(pages) + 1:02d}.json").write_bytes(response.content)
        page = response.json()
        pages.append(page)
        token = page.get("next_page_token")
        if not token:
            return pages


def _write_csv(path: Path, columns: Sequence[str], rows: Sequence[Mapping[str, str]]) -> str:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--feed", choices=("sip", "iex"), required=True)
    parser.add_argument("--out", type=Path, default=Path("data/local_research"))
    parser.add_argument(
        "--impute-missing-payable",
        action="store_true",
        help="label-and-impute missing payable dates as ex-date + largest observed lag for the symbol",
    )
    parser.add_argument("--from-raw", action="store_true", help="re-convert saved raw pages; no network")
    args = parser.parse_args()

    raw_dir = args.out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    bar_params = {
        "symbols": ",".join(SYMBOLS),
        "timeframe": "1Day",
        "start": f"{args.start}T00:00:00Z",
        "end": f"{args.end}T23:59:59Z",
        "adjustment": "raw",
        "feed": args.feed,
        "limit": "10000",
        "sort": "asc",
    }
    action_params = {
        "symbols": ",".join(SYMBOLS),
        "types": "cash_dividend,forward_split,reverse_split",
        "start": args.start,
        "end": args.end,
        "limit": "1000",
    }
    if args.from_raw:
        bar_pages = [json.loads(p.read_bytes()) for p in sorted(raw_dir.glob("bars_page_*.json"))]
        action_pages = [json.loads(p.read_bytes()) for p in sorted(raw_dir.glob("corporate_actions_page_*.json"))]
        if not bar_pages or not action_pages:
            raise DataContractError(f"RAW_PAGES_MISSING: {raw_dir}.")
    else:
        if any(raw_dir.glob("*.json")):
            raise DataContractError(f"RAW_DIR_NOT_EMPTY: {raw_dir}; use --from-raw or move previous pages.")
        creds = resolve_alpaca_credentials()
        if creds is None or not creds.resolved or not creds.api_key_id:
            raise DataContractError("ALPACA_CREDENTIALS_UNRESOLVED.")
        headers = {
            "APCA-API-KEY-ID": creds.api_key_id,
            "APCA-API-SECRET-KEY": creds.api_secret_ref,
            "Accept": "application/json",
        }
        with httpx.Client(headers=headers, timeout=30.0, follow_redirects=False) as client:
            bar_pages = _pages(client, "/v2/stocks/bars", bar_params, raw_dir, "bars")
            action_pages = _pages(client, "/v1/corporate-actions", action_params, raw_dir, "corporate_actions")

    bars = bar_rows(bar_pages, SYMBOLS)
    distributions, splits = corporate_action_rows(
        action_pages, SYMBOLS, impute_missing_payable=args.impute_missing_payable
    )
    manifest = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bars_request": bar_params,
        "corporate_actions_request": action_params,
        "asof": "provider default (not pinned)",
        "converted_from_saved_raw_pages": args.from_raw,
        "pages": len(bar_pages) + len(action_pages),
        "imputed_payable_dates": sum(r["payable_date_source"] != "PROVIDER" for r in distributions),
        "raw_bytes": sum(p.stat().st_size for p in raw_dir.glob("*.json")),
        "files_sha256": {
            "bars_raw.csv": _write_csv(args.out / "bars_raw.csv", ("symbol", "session", "open", "close", "adjustment"), bars),
            "distributions.csv": _write_csv(
                args.out / "distributions.csv",
                ("symbol", "ex_date", "payable_date", "gross_amount", "distribution_type", "payable_date_source"),
                distributions,
            ),
            "splits.csv": _write_csv(args.out / "splits.csv", ("symbol", "session", "ratio"), splits),
        },
        "counts": {"bars": len(bars), "distributions": len(distributions), "splits": len(splits)},
    }
    (args.out / "fetch_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("pages", "raw_bytes", "counts", "imputed_payable_dates")}, indent=2))


if __name__ == "__main__":
    main()
