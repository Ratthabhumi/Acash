"""Fetch / seal / convert D6 LOCAL_EXPLORATORY inputs from the owner's Alpaca account.

Read-only GETs to data.alpaca.markets (market data only; no trading endpoint), one
fixed feed, no retries, no fallback. Raw pages live under the git-ignored data/ tree,
are for personal research and must not be redistributed. Credential values and
response bodies are never printed.

Subcommands:
  fetch        one request series into a NEW raw directory with a page manifest
               (bars require an explicit --asof; caps on requests and observed bytes)
  seal-legacy  record SHA-256 of raw pages fetched before manifests existed, keeping
               their original request and unpinned-asof status (sealed after fetch)
  convert      verify raw pages against manifests, then write CSVs to a NEW directory;
               never opens a network connection
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.local_alpaca import (
    DISTRIBUTION_COLUMNS,
    PAYABLE_LAG_POLICIES,
    SPLIT_COLUMNS,
    bar_rows,
    corporate_action_rows,
    page_record,
    verify_page_bytes,
    verify_page_chain,
)

BASE_URL = "https://data.alpaca.markets"
SYMBOLS = ("BIL", "BND", "GLD", "VOO")
MANIFEST = "raw_manifest.json"
MAX_REQUESTS = 32
MAX_RESPONSE_BYTES = 8_388_608
SCHEMA = "acash.local_alpaca.raw.v1"


def _new_dir(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise DataContractError(f"OUTPUT_DIR_NOT_EMPTY: {path}; use a new versioned path.")
    path.mkdir(parents=True, exist_ok=True)


def _fetch(args: argparse.Namespace) -> None:
    import httpx

    from acash.research.step_r2_hyp_003 import resolve_alpaca_credentials

    if args.kind == "bars":
        if not args.asof:
            raise DataContractError("ASOF_REQUIRED: bars fetch needs an explicit --asof YYYY-MM-DD.")
        path = "/v2/stocks/bars"
        params = {
            "symbols": ",".join(SYMBOLS),
            "timeframe": "1Day",
            "start": f"{args.start}T00:00:00Z",
            "end": f"{args.end}T23:59:59Z",
            "adjustment": "raw",
            "feed": args.feed,
            "asof": date.fromisoformat(args.asof).isoformat(),
            "limit": "10000",
            "sort": "asc",
        }
        asof_status = f"PINNED:{params['asof']}"
    else:
        path = "/v1/corporate-actions"
        params = {
            "symbols": ",".join(SYMBOLS),
            "types": args.types,
            "start": args.start,
            "end": args.end,
            "limit": "1000",
        }
        asof_status = "NOT_APPLICABLE"
    _new_dir(args.raw_dir)
    creds = resolve_alpaca_credentials()
    if creds is None or not creds.resolved or not creds.api_key_id:
        raise DataContractError("ALPACA_CREDENTIALS_UNRESOLVED.")
    headers = {
        "APCA-API-KEY-ID": creds.api_key_id,
        "APCA-API-SECRET-KEY": creds.api_secret_ref,
        "Accept": "application/json",
    }
    records: List[Dict[str, Any]] = []
    observed = 0
    token: Optional[str] = None
    with httpx.Client(headers=headers, timeout=30.0, follow_redirects=False) as client:
        while True:
            if len(records) >= MAX_REQUESTS:
                raise DataContractError(f"REQUEST_BUDGET_EXCEEDED: {args.kind}.")
            query = dict(params, **({"page_token": token} if token else {}))
            response = client.get(f"{BASE_URL}{path}", params=query)
            if response.status_code != 200:
                raise DataContractError(f"ALPACA_HTTP_{response.status_code}: {args.kind} (body not shown).")
            payload = response.content
            observed += len(payload)
            if observed > MAX_RESPONSE_BYTES:
                raise DataContractError(f"BYTE_BUDGET_EXCEEDED: {args.kind} {observed}.")
            record = page_record(args.kind, len(records) + 1, token, payload)
            (args.raw_dir / record["file"]).write_bytes(payload)
            records.append(record)
            verify_page_chain(records[:-1])
            token = record["next_page_token"]
            if token is None:
                break
    verify_page_chain(records)
    manifest = {
        "schema": SCHEMA,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sealed_after_fetch": False,
        "requests": {args.kind: {"path": path, "params": params, "asof_status": asof_status}},
        "budget": {"max_requests": MAX_REQUESTS, "max_response_bytes": MAX_RESPONSE_BYTES},
        "observed_response_bytes": observed,
        "pages": records,
    }
    (args.raw_dir / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"pages": len(records), "observed_response_bytes": observed}, indent=2))


def _seal_legacy(args: argparse.Namespace) -> None:
    target = args.raw_dir / MANIFEST
    if target.exists():
        raise DataContractError(f"MANIFEST_EXISTS: {target}.")
    legacy = json.loads((args.raw_dir.parent / "fetch_manifest.json").read_text(encoding="utf-8"))
    records: List[Dict[str, Any]] = []
    for tag in ("bars", "corporate_actions"):
        token: Optional[str] = None
        for index, page in enumerate(sorted(args.raw_dir.glob(f"{tag}_page_*.json")), start=1):
            record = page_record(tag, index, token, page.read_bytes())
            if record["file"] != page.name:
                raise DataContractError(f"RAW_PAGE_NAME_UNEXPECTED: {page.name}.")
            records.append(record)
            token = record["next_page_token"]
    verify_page_chain(records)
    manifest = {
        "schema": SCHEMA,
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sealed_after_fetch": True,
        "original_fetch_manifest_fetched_at_utc": legacy.get("fetched_at_utc"),
        "requests": {
            "bars": {"path": "/v2/stocks/bars", "params": legacy["bars_request"], "asof_status": "UNPINNED_PROVIDER_DEFAULT"},
            "corporate_actions": {
                "path": "/v1/corporate-actions",
                "params": legacy["corporate_actions_request"],
                "asof_status": "NOT_APPLICABLE",
            },
        },
        "request_page_tokens": "INFERRED_FROM_SAVED_PAGES",
        "observed_response_bytes": sum(r["bytes"] for r in records),
        "pages": records,
    }
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"pages": len(records), "bytes": manifest["observed_response_bytes"]}, indent=2))


def load_verified_pages(raw_dir: Path, tag: str) -> tuple[List[Any], Dict[str, Any]]:
    manifest: Dict[str, Any] = json.loads((raw_dir / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        raise DataContractError(f"RAW_MANIFEST_SCHEMA: {raw_dir}.")
    records = [r for r in manifest["pages"] if r["tag"] == tag]
    if not records:
        raise DataContractError(f"RAW_PAGES_MISSING: {raw_dir} {tag}.")
    verify_page_chain(records)
    listed = {r["file"] for r in records}
    on_disk = {p.name for p in raw_dir.glob(f"{tag}_page_*.json")}
    if listed != on_disk:
        raise DataContractError(f"RAW_PAGE_SET_MISMATCH: {raw_dir} {sorted(listed ^ on_disk)}.")
    pages = [verify_page_bytes(r, (raw_dir / r["file"]).read_bytes()) for r in records]
    return pages, {"dir": raw_dir.as_posix(), "request": manifest["requests"][tag], "pages": records}


def _write_csv(path: Path, columns: Sequence[str], rows: Sequence[Mapping[str, str]]) -> str:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convert(
    bars_raw: Path, action_raws: Sequence[tuple[Path, str]], out: Path, start: date, end: date, policy: Optional[str]
) -> Dict[str, Any]:
    bar_pages, bar_source = load_verified_pages(bars_raw, "bars")
    action_pages: List[Any] = []
    action_sources = []
    for raw_dir, tag in action_raws:
        pages, source = load_verified_pages(raw_dir, tag)
        action_pages += pages
        action_sources.append(source)
    bars = bar_rows(bar_pages, SYMBOLS)
    actions = corporate_action_rows(action_pages, SYMBOLS, window=(start, end), payable_lag_policy=policy)
    _new_dir(out)
    sources = [r["payable_date_source"] for r in actions.distributions]
    manifest = {
        "converted_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "network": "NONE",
        "window_by_ex_date": [start.isoformat(), end.isoformat()],
        "payable_lag_policy": policy,
        "sources": {"bars": bar_source, "corporate_actions": action_sources},
        "counts": {
            "bars": len(bars),
            "distributions": len(actions.distributions),
            "by_type": {t: sum(r["distribution_type"] == t for r in actions.distributions)
                        for t in sorted({r["distribution_type"] for r in actions.distributions})},
            "provider_payable_dates": sources.count("PROVIDER"),
            "imputed_payable_dates": len(sources) - sources.count("PROVIDER"),
            "splits": len(actions.splits),
            "excluded_outside_window": len(actions.excluded_outside_window),
            "cross_page_duplicates_identical": actions.cross_page_duplicates,
        },
        "excluded_outside_window": actions.excluded_outside_window,
        "observed_payable_lags_days": actions.observed_payable_lags,
        "files_sha256": {
            "bars_raw.csv": _write_csv(out / "bars_raw.csv", ("symbol", "session", "open", "close", "adjustment"), bars),
            "distributions.csv": _write_csv(out / "distributions.csv", DISTRIBUTION_COLUMNS, actions.distributions),
            "splits.csv": _write_csv(out / "splits.csv", SPLIT_COLUMNS, actions.splits),
        },
    }
    (out / "conversion_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _convert(args: argparse.Namespace) -> None:
    action_raws = [(Path(item.split("=", 1)[1]), item.split("=", 1)[0]) for item in args.actions]
    manifest = convert(args.bars_raw, action_raws, args.out, args.start, args.end, args.payable_lag_policy)
    print(json.dumps({"counts": manifest["counts"], "files_sha256": manifest["files_sha256"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--kind", choices=("bars", "corporate_actions"), required=True)
    fetch.add_argument("--raw-dir", type=Path, required=True)
    fetch.add_argument("--start", default="2016-01-01")
    fetch.add_argument("--end", default="2025-12-31")
    fetch.add_argument("--feed", choices=("sip", "iex"), default="sip")
    fetch.add_argument("--asof")
    fetch.add_argument("--types", default="cash_dividend,capital_gains_distribution,forward_split,reverse_split")
    seal = sub.add_parser("seal-legacy")
    seal.add_argument("--raw-dir", type=Path, required=True)
    conv = sub.add_parser("convert")
    conv.add_argument("--bars-raw", type=Path, required=True)
    conv.add_argument("--actions", nargs="+", required=True, help="TAG=DIR, e.g. corporate_actions=data/.../raw")
    conv.add_argument("--out", type=Path, required=True)
    conv.add_argument("--start", type=date.fromisoformat, default=date(2016, 1, 1))
    conv.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    conv.add_argument("--payable-lag-policy", choices=PAYABLE_LAG_POLICIES)
    args = parser.parse_args()
    {"fetch": _fetch, "seal-legacy": _seal_legacy, "convert": _convert}[args.command](args)


if __name__ == "__main__":
    main()
