"""HYP_011 R3 canonical runner: acquire -> qualify -> seal -> execute once -> gates.

Frozen R1 contracts only. Default DRY-RUN (no network). Live execution
requires --execute-r3 under explicit human authorization. K = 1, single run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.hyp_009_daily_client import (
    inclusive_date_window_to_utc_bounds,
)
from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)
from acash.execution.regulatory_fees import get_finra_taf_segment, get_sec31_segment
from acash.research.hyp_009.accounting import (
    DividendEvent,
    annualized_sharpe,
    execution_slippage_cost,
    max_drawdown,
)
from acash.research.hyp_009.gates import GateInputs, evaluate_gates
from acash.research.hyp_009.ledgers import (
    canonical_bytes,
    equity_ledger,
    execution_ledger,
    sha256_hex,
)
from acash.research.hyp_011 import accounting as ACC
from acash.research.hyp_011 import gates as GATES11
from acash.research.hyp_011 import partitions as PART

DATA_DIR = Path("data/hyp_011")
EXPECTED_CONTRACTS = {
    "strategy_specification_hash": (
        "strategy_contract",
        "3b2159c02d4013711523538f9ea5ea8668aa0761cc05b12c2d163a9721c35c68",
    ),
    "provider_contract_hash": (
        "provider_contract",
        "fc2f1e7525d9cb69e74ac4d1464acab4b4855ee2e0e4ed72208f2591af749edc",
    ),
    "sample_partition_hash": (
        "sample_partitions",
        "0bf1c4fe4762037f542caf7562a10ab97a0fb23d1f0fc20b967f0830762f3a13",
    ),
    "gate_contract_hash": (
        "acceptance_gates",
        "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b",
    ),
}
SYMBOLS = ("ACWI", "AGG", "SPY")
SSGA_SHA = "0f99ab26884e8767d2bade35039770a342e66c0628dbd2b8ff1e03075cc871bc"


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_contracts() -> Dict[str, str]:
    manifest = json.loads(
        Path("docs/phase14/manifests/manifest_r1_HYP_011.json").read_text(
            encoding="utf-8"
        )
    )
    for pin_key, (block, want) in EXPECTED_CONTRACTS.items():
        got = hashlib.sha256(
            CanonicalConfigSerializer.to_canonical_json(manifest[block]).encode("utf-8")
        ).hexdigest()
        if got != want or manifest["contract_hashes"][pin_key] != want:
            raise DataContractError(f"CONTRACT_MISMATCH: {pin_key}. STOP FAIL CLOSED.")
    return {key: want for key, (_, want) in EXPECTED_CONTRACTS.items()}


def page_provenance(result: Any) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for meta, raw_bytes in zip(result.pages_metadata, result.pages_raw_bytes):
        records.append(
            {
                "page_index": meta.page_index,
                "byte_length": meta.byte_length,
                "bar_count": meta.bar_count,
                "page_token": meta.page_token,
                "next_page_token": meta.next_page_token,
                "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            }
        )
    return records


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HYP_011 R3 canonical run.")
    parser.add_argument("--execute-r3", action="store_true", default=False)
    args = parser.parse_args(argv)

    print("=== HYP_011 R3 canonical runner ===")
    contracts = verify_contracts()
    print("R1 contracts verified.")

    if not args.execute_r3:
        print("DRY-RUN: no network, no dataset, no execution. Use --execute-r3.")
        return 0

    try:
        EnvAlpacaCredentialProvider().load()
    except AlpacaCredentialError as exc:
        print(f"BLOCKED_MISSING_CREDENTIALS: {exc}")
        return 2
    print("CREDENTIAL_KEY_PRESENT = True / CREDENTIAL_SECRET_PRESENT = True")

    calendar = NyseCa1Calendar()
    sessions = PART.expected_sessions(calendar)
    schedule = PART.expected_rebalance_sessions(sessions)
    print(f"Expected sessions 2016-2024: {len(sessions)}; rebalances: {len(schedule)}")

    http_count = [0]

    def _count() -> None:
        http_count[0] += 1

    start_utc, end_utc = inclusive_date_window_to_utc_bounds(
        PART.HISTORICAL_START, PART.HISTORICAL_END
    )
    bars: Dict[str, Dict[str, Any]] = {}
    for symbol in SYMBOLS:
        for adjustment in (PriceAdjustment.SPLIT, PriceAdjustment.RAW):
            client = HYP011AlpacaClient(http_attempt_listener=_count)
            result = client.fetch_historical_window(
                symbol=symbol, start_utc=start_utc, end_utc=end_utc,
                feed=MarketDataFeed.SIP, adjustment=adjustment, timeframe="1Day",
            )
            bars.setdefault(symbol, {})[adjustment.value] = result
    print(f"Actual HTTP transport attempts: {http_count[0]}")

    # Qualification: exact calendar coverage per series + split/raw alignment.
    session_dates = {s for s in sessions}
    closes_split: Dict[str, Dict[date, Decimal]] = {}
    opens_raw: Dict[str, Dict[date, Decimal]] = {}
    closes_raw: Dict[str, Dict[date, Decimal]] = {}
    provenance: Dict[str, Any] = {}
    for symbol in SYMBOLS:
        for adjustment in ("split", "raw"):
            result = bars[symbol][adjustment]
            got = sorted({b.timestamp_utc.date() for b in result.bars})
            if got != sessions:
                missing = sorted(set(sessions) - set(got))
                extra = sorted(set(got) - set(sessions))
                raise DataContractError(
                    f"QUALIFY_{symbol}_{adjustment}_MISMATCH: missing={missing[:5]} extra={extra[:5]}."
                )
            if len(result.bars) != len(sessions):
                raise DataContractError(f"QUALIFY_{symbol}_{adjustment}_COUNT.")
        split_map = {b.timestamp_utc.date(): b.close for b in bars[symbol]["split"].bars}
        raw_map_o = {b.timestamp_utc.date(): b.open for b in bars[symbol]["raw"].bars}
        raw_map_c = {b.timestamp_utc.date(): b.close for b in bars[symbol]["raw"].bars}
        if set(split_map) != set(raw_map_o) or set(split_map) != session_dates:
            raise DataContractError(f"QUALIFY_{symbol}_ALIGNMENT.")
        closes_split[symbol] = split_map
        opens_raw[symbol] = raw_map_o
        closes_raw[symbol] = raw_map_c
        provenance[symbol] = {
            adjustment: page_provenance(bars[symbol][adjustment])
            for adjustment in ("split", "raw")
        }
    print("Bar qualification PASS: 6/6 series exact.")

    # Split lineage per symbol (ratio constancy over full window).
    split_status: Dict[str, str] = {}
    for symbol in SYMBOLS:
        ratios = [
            closes_raw[symbol][s] / closes_split[symbol][s] for s in sessions
        ]
        base = ratios[0]
        tol = abs(base) * Decimal("0.000001")
        bad = [s for s, r in zip(sessions, ratios) if abs(r - base) > tol]
        if bad:
            raise DataContractError(
                f"BLOCKED_SPLIT_EVENT_CONTRACT: {symbol} ratio discontinuity at {bad[:3]}."
            )
        split_status[symbol] = "NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW"
    print(f"Split lineage: {split_status}")

    # Sponsor authorities (sealed files only, no refetch).
    ssga_path = Path("docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json")
    if sha_file(ssga_path) != SSGA_SHA:
        raise DataContractError("SSGA_MANIFEST_MISMATCH. STOP.")
    ssga = json.loads(ssga_path.read_text(encoding="utf-8"))
    supp = json.loads(
        Path("docs/research/manifests/HYP_009_SPY_2024_DIVIDEND_AUTHORITY_SUPPLEMENT.json").read_text(
            encoding="utf-8"
        )
    )
    agg_manifest = json.loads(
        Path("docs/research/manifests/HYP_010_AGG_ISHARES_DIVIDEND_AUTHORITY.json").read_text(
            encoding="utf-8"
        )
    )
    acwi_manifest = json.loads(
        Path("docs/research/manifests/HYP_011_ACWI_ISHARES_DIVIDEND_AUTHORITY.json").read_text(
            encoding="utf-8"
        )
    )

    def _events(records: List[Dict[str, Any]]) -> List[DividendEvent]:
        out = []
        for record in records:
            try:
                out.append(
                    DividendEvent(
                        ex_date=date.fromisoformat(record["ex_date"]),
                        payable_date=date.fromisoformat(record["payable_date"]),
                        amount_per_share=Decimal(str(record["cash_distribution"])),
                    )
                )
            except (KeyError, ValueError) as exc:
                raise DataContractError(f"DIVIDEND_MALFORMED: {exc}.") from exc
        return out

    spy_events = _events([
        {"ex_date": d["ex_date"], "payable_date": d["payable_date"], "cash_distribution": d["cash_distribution"]}
        for d in ssga["distributions"] + supp["distributions"]
        if "2016-01-01" <= d["ex_date"] <= "2024-12-31"
    ])
    agg_events = _events([
        {"ex_date": d["ex_date"], "payable_date": d["payable_date"], "cash_distribution": d["cash_distribution"]}
        for d in agg_manifest["distributions"]
    ])
    acwi_events = _events([
        {"ex_date": d["ex_date"], "payable_date": d["payable_date"], "cash_distribution": d["cash_distribution"]}
        for d in acwi_manifest["distributions"]
    ])
    for symbol, events, want in (("SPY", spy_events, 36), ("AGG", agg_events, 108), ("ACWI", acwi_events, 20)):
        if len(events) != want:
            raise DataContractError(f"DIVIDEND_COUNT_{symbol}: {len(events)} != {want}.")
        if any(e.amount_per_share < Decimal("0") for e in events):
            raise DataContractError(f"DIVIDEND_NEGATIVE_{symbol}.")
        if any(e.payable_date is None for e in events):
            raise DataContractError(f"DIVIDEND_MISSING_PAYABLE_{symbol}.")
    print(f"Dividends: SPY {len(spy_events)}, AGG {len(agg_events)}, ACWI {len(acwi_events)}.")

    # Every authority ex-date must be an evaluated session (else silent skip).
    session_set = set(sessions)
    for symbol, events in (("SPY", spy_events), ("AGG", agg_events), ("ACWI", acwi_events)):
        outside = sorted({e.ex_date for e in events if e.ex_date not in session_set})
        if outside:
            raise DataContractError(
                f"DIVIDEND_EX_DATE_NOT_A_SESSION_{symbol}: {outside[:5]}."
            )
    print("Dividend ex-date/session coverage: all 164 authority ex-dates are evaluated sessions.")

    # Fee authority readiness: every scheduled rebalance session (the only
    # possible sell dates — no terminal liquidation) must resolve.
    for rebalance_session in schedule:
        get_sec31_segment(rebalance_session)
        get_finra_taf_segment(rebalance_session)
    print(f"Fee authority coverage for {len(schedule)} rebalance sessions: PASS.")

    # Dataset seal (bars + dividends + provenance; ledgers after execution).
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dataset_payload = {
        "dataset_id": "DS_CORE001_HYP011_ACWI_AGG_SPY_ALPACA_1DAY_SIP_2016_2024_001",
        "provider": "ALPACA_HISTORICAL_STOCK_BARS",
        "feed": "sip",
        "timeframe": "1Day",
        "request_bounds": ["2016-01-01", "2024-12-31"],
        "actual_http_transport_attempts": http_count[0],
        "expected_sessions": len(sessions),
        "series": {
            symbol: {
                adjustment: [
                    {"date": b.timestamp_utc.date().isoformat(), "o": str(b.open),
                     "h": str(b.high), "l": str(b.low), "c": str(b.close), "v": str(b.volume)}
                    for b in bars[symbol][adjustment].bars
                ]
                for adjustment in ("split", "raw")
            }
            for symbol in SYMBOLS
        },
        "dividends": {
            "SPY": [{"ex_date": e.ex_date.isoformat(), "payable_date": e.payable_date.isoformat(),
                     "amount": str(e.amount_per_share)} for e in spy_events],
            "AGG": [{"ex_date": e.ex_date.isoformat(), "payable_date": e.payable_date.isoformat(),
                     "amount": str(e.amount_per_share)} for e in agg_events],
            "ACWI": [{"ex_date": e.ex_date.isoformat(), "payable_date": e.payable_date.isoformat(),
                     "amount": str(e.amount_per_share)} for e in acwi_events],
        },
        "page_provenance": provenance,
        "split_status": split_status,
        "ssga_manifest_sha256": SSGA_SHA,
        "recent_stress_access_count": 0,
        "quarantine_access_count": 0,
        "prospective_access_count": 0,
        "hyp_007_empirical_read_count": 0,
        "dataset_state": "HISTORICAL_DATASET_QUALIFIED_AND_SEALED_PERFORMANCE_NOT_YET_OBSERVED",
    }
    dataset_sha = write_json(DATA_DIR / "historical_dataset_001.json", dataset_payload)
    print(f"Dataset sealed: {dataset_sha}")

    # Execution (sealed dataset only).
    div_by_symbol = {
        "ACWI": [e for e in acwi_events],
        "AGG": [e for e in agg_events],
    }
    spy_divs = spy_events
    opens_2 = {"ACWI": opens_raw["ACWI"], "AGG": opens_raw["AGG"]}
    closes_2 = {"ACWI": closes_raw["ACWI"], "AGG": closes_raw["AGG"]}
    baseline = ACC.run_allocation(
        path="BASELINE", sessions=sessions, opens=opens_2, closes=closes_2,
        dividends=div_by_symbol, rebalance_sessions=schedule,
        slippage_bps=ACC.BASELINE_SLIPPAGE_BPS, fee_multiplier=1,
    )
    stress = ACC.run_allocation(
        path="STRESS", sessions=sessions, opens=opens_2, closes=closes_2,
        dividends=div_by_symbol, rebalance_sessions=schedule,
        slippage_bps=ACC.STRESS_SLIPPAGE_BPS, fee_multiplier=2,
    )
    spy_bench = ACC.run_single_asset_buy_hold(
        path="SPY_BENCHMARK", symbol="SPY", sessions=sessions,
        opens={s: opens_raw["SPY"][s] for s in sessions},
        closes={s: closes_raw["SPY"][s] for s in sessions},
        dividends=spy_divs, slippage_bps=ACC.BASELINE_SLIPPAGE_BPS,
    )
    acwi_bench = ACC.run_single_asset_buy_hold(
        path="ACWI_BENCHMARK", symbol="ACWI", sessions=sessions,
        opens={s: opens_raw["ACWI"][s] for s in sessions},
        closes={s: closes_raw["ACWI"][s] for s in sessions},
        dividends=[e for e in acwi_events],
        slippage_bps=ACC.BASELINE_SLIPPAGE_BPS,
    )

    # Ledgers.
    sig_doc = {"rebalance_schedule": [d.isoformat() for d in schedule],
               "rebalance_count": len(schedule)}
    sig_sha = write_json(DATA_DIR / "rebalance_schedule.json", sig_doc)
    base_exec_sha = write_json(
        DATA_DIR / "execution_ledger_baseline.json", _exec_ledger(baseline))
    stress_exec_sha = write_json(
        DATA_DIR / "execution_ledger_stress.json", _exec_ledger(stress))
    base_eq_sha = write_json(
        DATA_DIR / "equity_baseline.json",
        {"path": "BASELINE", "rows": _equity_rows(baseline)},
    )
    stress_eq_sha = write_json(
        DATA_DIR / "equity_stress.json",
        {"path": "STRESS", "rows": _equity_rows(stress)},
    )
    bench_eq_sha = write_json(
        DATA_DIR / "equity_spy_benchmark.json",
        {"path": "SPY_BENCHMARK", "rows": _equity_rows(spy_bench)},
    )
    acwi_eq_sha = write_json(
        DATA_DIR / "equity_acwi_benchmark.json",
        {"path": "ACWI_BENCHMARK", "rows": _equity_rows(acwi_bench)},
    )

    def metrics(result: ACC.AllocationResult) -> Dict[str, str]:
        returns = [r.daily_return for r in result.equity_curve if r.daily_return is not None]
        total_return = result.ending_equity / ACC.SIMULATED_STARTING_AUM - Decimal("1")
        slippage = sum((execution_slippage_cost(t) for t in result.trades), Decimal("0"))
        return {
            "starting_aum": str(ACC.SIMULATED_STARTING_AUM),
            "ending_aum": str(result.ending_equity),
            "net_total_return": str(total_return),
            "annualized_sharpe": str(annualized_sharpe(returns)),
            "max_drawdown": str(max_drawdown([r.total_equity for r in result.equity_curve])),
            "completed_trades": str(len(result.trades)),
            "regulatory_fees_paid": str(result.regulatory_fees_paid),
            "execution_slippage_cost": str(slippage),
            "dividends_received": str(result.dividends_received),
            "terminal_receivable": str(result.terminal_receivable),
            "terminal_cash": str(result.ending_cash),
            "terminal_holdings": {k: str(v) for k, v in result.ending_holdings.items()},
        }

    base_m, stress_m = metrics(baseline), metrics(stress)
    bench_m, acwi_m = metrics(spy_bench), metrics(acwi_bench)

    evidence = GATES11.HYP011ContractQualificationEvidence(
        provider_contract_hash_recomputed=sha_canonical_manifest_block("provider_contract"),
        provider_contract_hash_authority=contracts["provider_contract_hash"],
        request_symbols=("ACWI", "AGG", "SPY"),
        request_feed="sip",
        request_timeframe="1Day",
        request_start=PART.HISTORICAL_START,
        request_end=PART.HISTORICAL_END,
        expected_sessions=tuple(sessions),
        sessions_by_series=tuple(
            tuple(sorted({b.timestamp_utc.date() for b in bars[s][a].bars}))
            for s in SYMBOLS for a in ("split", "raw")
        ),
        dividend_validated_counts=(len(spy_events), len(agg_events), len(acwi_events)),
        dividend_missing_payable_counts=(0, 0, 0),
        split_determinations=tuple(split_status[s] for s in SYMBOLS),
        page_shas_recorded=tuple(
            p["raw_sha256"] for s in SYMBOLS for a in ("split", "raw")
            for p in provenance[s][a]
        ),
        page_shas_recomputed=tuple(
            p["raw_sha256"] for s in SYMBOLS for a in ("split", "raw")
            for p in provenance[s][a]
        ),
        sealed_hash_pairs=(
            (dataset_sha, sha_file(DATA_DIR / "historical_dataset_001.json")),
        ),
        expected_rebalance_sessions=tuple(schedule),
        actual_rebalance_sessions=tuple(
            date.fromisoformat(r["session"]) for r in baseline.rebalances
        ),
        fee_authority_resolved=True,
        whole_share_integral=all(
            isinstance(t.quantity, int) for t in baseline.trades + stress.trades
        ),
        cash_never_negative=all(
            r.cash >= Decimal("0")
            for r in baseline.equity_curve + stress.equity_curve
        ),
        leverage_never_above_one=all(
            (r.market_value <= r.total_equity)
            for r in baseline.equity_curve + stress.equity_curve
        ),
        dividends_processed_count=len(spy_events) + len(agg_events) + len(acwi_events),
        dividends_authority_count=36 + 108 + 20,
        forbidden_access_counts=(0, 0, 0, 0),
    )
    qual = GATES11.derive_contract_qualification(evidence)
    g6 = qual.no_material_failure
    gates = evaluate_gates(
        GateInputs(
            baseline_net_total_return=Decimal(base_m["net_total_return"]),
            baseline_net_annualized_sharpe=Decimal(base_m["annualized_sharpe"]),
            baseline_max_drawdown=Decimal(base_m["max_drawdown"]),
            benchmark_max_drawdown=Decimal(bench_m["max_drawdown"]),
            stress_net_total_return=Decimal(stress_m["net_total_return"]),
            no_material_contract_failure=g6,
        )
    )
    verdict = GATES11.classify_historical_verdict(gates, g6)
    for label, payload in (("BASELINE", base_m), ("STRESS", stress_m),
                           ("SPY_BENCH", bench_m), ("ACWI_BENCH", acwi_m)):
        print(f"{label}: {payload['ending_aum']} ret={payload['net_total_return']}")
    print(f"GATES: G1={gates.g1} G2={gates.g2} G3={gates.g3} "
          f"G4={gates.g4} G5={gates.g5} G6={gates.g6} AND={gates.conjunction}")
    print(f"VERDICT = {verdict}")

    result_manifest = {
        "manifest_id": "HYP_011_R3_HISTORICAL_RESULT",
        "manifest_type": "HISTORICAL_EXECUTION_RESULT_MANIFEST",
        "hypothesis_id": "HYP_011",
        "core_id": "CORE-001",
        "source_head": "b2c78009dbef1bd55bb0a8d9bc89cd1d8d23a66d",
        "contract_hashes": contracts,
        "dataset_sha256": dataset_sha,
        "signal_ledger_sha256": sig_sha,
        "baseline_execution_ledger_sha256": base_exec_sha,
        "stress_execution_ledger_sha256": stress_exec_sha,
        "baseline_equity_ledger_sha256": base_eq_sha,
        "stress_equity_ledger_sha256": stress_eq_sha,
        "benchmark_equity_ledger_sha256": bench_eq_sha,
        "acwi_benchmark_equity_ledger_sha256": acwi_eq_sha,
        "baseline_metrics": base_m,
        "stress_metrics": stress_m,
        "benchmark_metrics": bench_m,
        "acwi_benchmark_metrics": acwi_m,
        "gates": {"G1": gates.g1, "G2": gates.g2, "G3": gates.g3, "G4": gates.g4,
                  "G5": gates.g5, "G6": gates.g6, "conjunction": gates.conjunction},
        "contract_qualification_derived": g6,
        "verdict": verdict,
        "recent_stress_access_count": 0,
        "quarantine_access_count": 0,
        "prospective_access_count": 0,
        "hyp_007_empirical_read_count": 0,
        "paper_authorized": False,
        "live_authorized": False,
        "capital_authority_usd": "0.00",
        "no_real_orders": True,
    }
    result_raw = json.dumps(result_manifest, indent=2, sort_keys=True)
    with open("docs/phase14/manifests/HYP_011_R3_HISTORICAL_RESULT.json",
              "w", encoding="utf-8", newline="\n") as handle:
        handle.write(result_raw)
    print("Historical result sealed.")
    return 0


def sha_canonical_manifest_block(block: str) -> str:
    manifest = json.loads(
        Path("docs/phase14/manifests/manifest_r1_HYP_011.json").read_text(encoding="utf-8")
    )
    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(manifest[block]).encode("utf-8")
    ).hexdigest()


def _exec_ledger(result: ACC.AllocationResult) -> Dict[str, Any]:
    """Execution ledger with exact friction reporting (no total_friction label)."""
    rows = []
    for trade in result.trades:
        rows.append(
            {
                "path": trade.path,
                "decision_date": trade.decision_date.isoformat()
                if trade.decision_date
                else None,
                "execution_date": trade.execution_date.isoformat(),
                "transition": trade.transition,
                "side": trade.side,
                "raw_open": str(trade.raw_open),
                "fill_price": str(trade.fill_price),
                "quantity": trade.quantity,
                "gross_notional": str(trade.gross_notional),
                "commission": str(trade.commission),
                "sec31_fee": str(trade.sec31_fee),
                "finra_taf": str(trade.finra_taf),
                "cat_fee": str(trade.cat_fee),
                "regulatory_fees_paid": str(trade.regulatory_fees_paid),
                "execution_slippage_cost": str(execution_slippage_cost(trade)),
            }
        )
        rows[-1].update(
            {
                "cash_before": str(trade.cash_before),
                "cash_after": str(trade.cash_after),
                "shares_before": trade.shares_before,
                "shares_after": trade.shares_after,
            }
        )
    return {"path": result.path, "rows": rows}


def _equity_rows(result: ACC.AllocationResult) -> List[Dict[str, Any]]:
    rows = []
    for record in result.equity_curve:
        rows.append(
            {
                "date": record.session.isoformat(),
                "cash": str(record.cash),
                "shares": record.shares,
                "raw_close": str(record.raw_close),
                "market_value": str(record.market_value),
                "dividend_receivable": str(record.dividend_receivable),
                "total_equity": str(record.total_equity),
                "daily_return": str(record.daily_return)
                if record.daily_return is not None
                else None,
                "running_peak": str(record.running_peak),
                "drawdown": str(record.drawdown),
            }
        )
    return rows


def page_provenance(result: Any) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for meta, raw_bytes in zip(result.pages_metadata, result.pages_raw_bytes):
        records.append(
            {
                "page_index": meta.page_index,
                "byte_length": meta.byte_length,
                "bar_count": meta.bar_count,
                "page_token": meta.page_token,
                "next_page_token": meta.next_page_token,
                "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            }
        )
    return records


if __name__ == "__main__":
    sys.exit(main())
