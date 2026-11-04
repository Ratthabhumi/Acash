"""Qualify and reuse the D6 local research dataset (BIL/BND/GLD/VOO daily bars).

The data is a *price* series. Splits/dividends are reported separately and are not silently folded
into a total-return series: without a verified adjustment method the panel is labelled
``PRICE_RETURN``. Nothing is downloaded here and nothing is fabricated.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError

DEFAULT_DIR = Path("data/local_research")
PRICE_RETURN = "PRICE_RETURN"
TOTAL_RETURN = "TOTAL_RETURN_NOT_ESTABLISHED"


@dataclass(frozen=True)
class LocalDataset:
    bars: Mapping[str, Mapping[date, Decimal]]
    adjustment_basis: Tuple[str, ...]
    distributions: int
    splits: int
    manifest: Mapping[str, Any]
    sha256: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_d6(directory: Path = DEFAULT_DIR) -> LocalDataset:
    bars_path = directory / "bars_raw.csv"
    if not bars_path.is_file():
        raise DataContractError("LOCAL_BARS_MISSING: data/local_research/bars_raw.csv.")
    bars: Dict[str, Dict[date, Decimal]] = {}
    adjustments = set()
    with bars_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            symbol = str(row["symbol"]).strip()
            session = date.fromisoformat(str(row["session"]))
            close = Decimal(str(row["close"]))
            if close <= 0:
                raise DataContractError(f"LOCAL_BAR_INVALID: {symbol} {session}.")
            adjustments.add(str(row.get("adjustment") or "UNKNOWN"))
            symbol_bars = bars.setdefault(symbol, {})
            if session in symbol_bars and symbol_bars[session] != close:
                raise DataContractError(f"LOCAL_BAR_DUPLICATE_CONFLICT: {symbol} {session}.")
            symbol_bars[session] = close
    if not bars:
        raise DataContractError("LOCAL_BARS_EMPTY.")
    distributions = _count_rows(directory / "distributions.csv")
    splits = _count_rows(directory / "splits.csv")
    manifest = {}
    manifest_path = directory / "fetch_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return LocalDataset(bars={s: dict(sorted(v.items())) for s, v in bars.items()},
                        adjustment_basis=tuple(sorted(adjustments)), distributions=distributions,
                        splits=splits, manifest=manifest, sha256=_sha256(bars_path))


def _count_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def coverage(dataset: LocalDataset, symbols: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Per-symbol session coverage plus the gaps relative to the union calendar."""
    selected = sorted(symbols or dataset.bars)
    missing_symbols = [s for s in selected if s not in dataset.bars]
    union = sorted({d for s in selected if s in dataset.bars for d in dataset.bars[s]})
    per_symbol: Dict[str, Any] = {}
    for symbol in selected:
        sessions = sorted(dataset.bars.get(symbol, {}))
        if not sessions:
            per_symbol[symbol] = {"sessions": 0, "status": "MISSING"}
            continue
        gaps = [d.isoformat() for d in union if d not in dataset.bars[symbol]]
        per_symbol[symbol] = {"sessions": len(sessions), "first": sessions[0].isoformat(),
                              "last": sessions[-1].isoformat(), "gaps_vs_union": len(gaps),
                              "status": "COVERED" if not gaps else "PARTIAL"}
    return {
        "dataset": "D6_LOCAL_BARS",
        "sha256": dataset.sha256,
        "adjustment_basis": list(dataset.adjustment_basis),
        "price_basis": PRICE_RETURN if dataset.adjustment_basis != ("TOTAL_RETURN",) else TOTAL_RETURN,
        "distributions": dataset.distributions,
        "splits": dataset.splits,
        "manifest_asof": dataset.manifest.get("asof"),
        "manifest_counts": dataset.manifest.get("counts"),
        "symbols": per_symbol,
        "missing_symbols": missing_symbols,
        "union_sessions": len(union),
        "status": "QUALIFIED_FOR_PRICE_RETURN" if not missing_symbols else "PARTIAL_UNIVERSE",
        "note": "Price series only: dividends/splits are recorded separately and are not folded into "
                "returns without a verified adjustment method.",
    }


def aligned_returns(dataset: LocalDataset, symbols: Sequence[str]) -> Tuple[List[date], Dict[str, List[Decimal]]]:
    """Returns on the intersection of sessions so no value is forward-filled."""
    common = sorted(set.intersection(*(set(dataset.bars[s]) for s in symbols))) if symbols else []
    if len(common) < 2:
        raise DataContractError("LOCAL_PANEL_TOO_SHORT: fewer than two aligned sessions.")
    returns: Dict[str, List[Decimal]] = {}
    for symbol in symbols:
        series = dataset.bars[symbol]
        returns[symbol] = [(series[common[i]] / series[common[i - 1]]) - 1 for i in range(1, len(common))]
    return common[1:], returns


def proposal_inputs(dataset: LocalDataset, symbols: Sequence[str],
                    current_weights: Mapping[str, Decimal]) -> Dict[str, Any]:
    """Shape a qualified price-return panel for the existing research proposal engine."""
    from acash.invest import research_proposal as rp

    sessions, returns = aligned_returns(dataset, symbols)
    timestamps = [datetime.combine(s, datetime.min.time(), tzinfo=timezone.utc) for s in sessions]
    inputs = rp.ProposalInputs(returns=returns, timestamps=timestamps,
                               current_weights={s: Decimal(str(current_weights.get(s, 0))) for s in symbols})
    return {"inputs": inputs, "sessions": len(sessions), "price_basis": PRICE_RETURN}
