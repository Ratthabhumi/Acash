"""HYP_009 R2 M1 canonical runner: acquire -> qualify -> seal -> execute once -> gates.

Frozen R1 contracts only. Default is DRY-RUN (no network). Live execution
requires --execute-m1 under an explicit human authorization. K = 1, single run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.hyp_009_daily_client import (
    HYP009AlpacaClient,
    inclusive_date_window_to_utc_bounds,
)
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)
from acash.research.hyp_009 import accounting as ACC
from acash.research.hyp_009 import gates as GATES
from acash.research.hyp_009 import ledgers as LED
from acash.research.hyp_009 import partitions as PART
from acash.research.hyp_009 import qualification as QUAL
from acash.research.hyp_009 import signals as SIG

EXPECTED_SSGA_MANIFEST_SHA256 = "0f99ab26884e8767d2bade35039770a342e66c0628dbd2b8ff1e03075cc871bc"
DATA_DIR = Path("data/hyp_009")
EXPECTED_CONTRACTS = {
    "strategy_specification_hash": (
        "strategy_contract",
        "c3892a6af4dfaf729218dbf6182f95b9a4c5862032055965c1b9129fbff359e0",
    ),
    "provider_contract_hash": (
        "provider_contract",
        "1ed9892b4871a9c430b0770f6f691244661dec5257059dda9af5effb94ae55d6",
    ),
    "sample_partition_hash": (
        "sample_partitions",
        "063ceeb13f30dbbb1ff6610d24baf6aa5a084282a12e698b9403fa42c85a004f",
    ),
    "gate_contract_hash": (
        "acceptance_gates",
        "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b",
    ),
}


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_canonical(obj: object) -> str:
    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(obj).encode("utf-8")
    ).hexdigest()


def verify_contracts() -> Dict[str, str]:
    manifest = json.loads(
        Path("docs/phase14/manifests/manifest_r1_HYP_009.json").read_text(
            encoding="utf-8"
        )
    )
    for pin_key, (block, want) in EXPECTED_CONTRACTS.items():
        got = sha_canonical(manifest[block])
        if got != want or manifest["contract_hashes"][pin_key] != want:
            raise DataContractError(f"CONTRACT_MISMATCH: {pin_key}. STOP FAIL CLOSED.")
    return {key: want for key, (_, want) in EXPECTED_CONTRACTS.items()}


def fetch_series(
    client: HYP009AlpacaClient,
    adjustment: PriceAdjustment,
) -> Any:
    start_utc, end_utc = inclusive_date_window_to_utc_bounds(
        PART.AUTHORIZED_MIN_DATE, PART.AUTHORIZED_MAX_DATE
    )
    return client.fetch_historical_bars(
        symbol="SPY",
        start_utc=start_utc,
        end_utc=end_utc,
        feed=MarketDataFeed.SIP,
        adjustment=adjustment,
        timeframe="1Day",
    )


def page_provenance(result: Any) -> List[Dict[str, Any]]:
    """Deterministic raw provider page lineage (no credentials/headers)."""
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
    if [r["raw_sha256"] for r in records] != [
        m.raw_sha256 for m in result.pages_metadata
    ]:
        raise DataContractError("PROVENANCE_HASH_MISMATCH: page bytes vs metadata.")
    return records


def write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HYP_009 R2 M1 canonical acquisition + single execution."
    )
    parser.add_argument(
        "--execute-m1",
        action="store_true",
        default=False,
        help="Authorize live M1 acquisition and the single canonical execution.",
    )
    args = parser.parse_args(argv)

    print("=== HYP_009 R2 M1 canonical runner ===")
    contracts = verify_contracts()
    print("R1 contracts verified (strategy/provider/sample/gate).")

    if not args.execute_m1:
        print("DRY-RUN: no network, no dataset, no execution. Use --execute-m1.")
        return 0

    try:
        EnvAlpacaCredentialProvider().load()
    except AlpacaCredentialError as exc:
        print(f"BLOCKED_MISSING_CREDENTIALS: {exc}")
        return 2
    print("CREDENTIAL_KEY_PRESENT = True / CREDENTIAL_SECRET_PRESENT = True")

    calendar = NyseCa1Calendar()
    full_sessions = PART.expected_sessions(
        calendar, PART.AUTHORIZED_MIN_DATE, PART.AUTHORIZED_MAX_DATE
    )
    m1_sessions = [s for s in full_sessions if PART.M1_START <= s <= PART.M1_END]
    print(f"Expected sessions 2016-2020: {len(full_sessions)}; M1: {len(m1_sessions)}")

    http_count = [0]

    def _count_http_attempt() -> None:
        http_count[0] += 1

    client = HYP009AlpacaClient(http_attempt_listener=_count_http_attempt)
    split_result = fetch_series(client, PriceAdjustment.SPLIT)
    raw_result = fetch_series(client, PriceAdjustment.RAW)
    print(f"Actual HTTP transport attempts: {http_count[0]}")
    aligned = QUAL.qualify_bar_series(full_sessions, split_result.bars, raw_result.bars)
    print(f"Bar qualification PASS: {len(aligned)} sessions, split/raw aligned.")

    split_close = {b.timestamp_utc.date(): b.close for b in split_result.bars}
    raw_open = {b.timestamp_utc.date(): b.open for b in raw_result.bars}
    raw_close = {b.timestamp_utc.date(): b.close for b in raw_result.bars}
    split_status = QUAL.require_no_unbound_splits(
        full_sessions, split_close, raw_close
    )
    print(f"Split check: {split_status}")

    ssga_path = Path("docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json")
    ssga_sha = sha_file(ssga_path)
    if ssga_sha != EXPECTED_SSGA_MANIFEST_SHA256:
        raise DataContractError(f"SSGA_MANIFEST_MISMATCH: {ssga_sha}. STOP.")
    ssga = json.loads(ssga_path.read_text(encoding="utf-8"))
    dividends = QUAL.qualify_dividends(
        ssga["distributions"], PART.AUTHORIZED_MIN_DATE, PART.AUTHORIZED_MAX_DATE
    )
    print(f"Dividend qualification PASS: {len(dividends)} events in scope.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    split_pages = page_provenance(split_result)
    raw_pages = page_provenance(raw_result)
    dataset_payload = {
        "dataset_id": "DS_SPY_CORE001_HYP009_M1_ALPACA_1DAY_SIP_REPRODUCIBILITY_001",
        "provider": "ALPACA_HISTORICAL_STOCK_BARS",
        "feed": "sip",
        "timeframe": "1Day",
        "request_bounds": ["2016-01-01", "2020-12-31"],
        "actual_http_transport_attempts": http_count[0],
        "expected_sessions": len(full_sessions),
        "split_bars": [
            {
                "date": b.timestamp_utc.date().isoformat(),
                "o": str(b.open),
                "h": str(b.high),
                "l": str(b.low),
                "c": str(b.close),
                "v": str(b.volume),
            }
            for b in split_result.bars
        ],
        "raw_bars": [
            {
                "date": b.timestamp_utc.date().isoformat(),
                "o": str(b.open),
                "h": str(b.high),
                "l": str(b.low),
                "c": str(b.close),
                "v": str(b.volume),
            }
            for b in raw_result.bars
        ],
        "dividends": [
            {
                "ex_date": e.ex_date.isoformat(),
                "payable_date": e.payable_date.isoformat(),
                "amount": str(e.amount_per_share),
            }
            for e in dividends
        ],
        "split_status": split_status,
        "ssga_manifest_sha256": ssga_sha,
        "split_page_provenance": split_pages,
        "raw_page_provenance": raw_pages,
        "m2_access_count": 0,
        "m3_access_count": 0,
        "quarantine_access_count": 0,
        "prospective_access_count": 0,
        "dataset_state": "M1_REPRODUCIBILITY_DATASET_SEALED_PERFORMANCE_NOT_YET_REPLAYED",
    }
    dataset_sha = write_json(DATA_DIR / "m1_dataset_reproducibility_001.json", dataset_payload)
    print(f"Reproducibility dataset sealed: {dataset_sha}")

    contract_qualification = GATES.ContractQualification(
        provider_contract_pass=True,
        calendar_coverage_pass=True,
        split_raw_alignment_pass=True,
        dividend_contract_pass=True,
        payable_date_contract_pass=all(
            e.payable_date is not None for e in dividends
        ),
        split_contract_pass=(split_status == "NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW"),
        response_scope_pass=True,
        provenance_hash_pass=True,
        serialization_integrity_pass=True,
        forbidden_partition_access_zero=True,
    )

    div_map = {e.ex_date: e.amount_per_share for e in dividends}
    signals = SIG.compute_signal_states(full_sessions, split_close, div_map)
    exec_map = SIG.resolve_execution_dates(signals, m1_sessions)
    pending = [s for s in signals if exec_map[s.decision_date] is None]
    runnable = [s for s in signals if exec_map[s.decision_date] is not None]
    print(f"Signals: {len(signals)} (runnable {len(runnable)}, pending {len(pending)})")
    for signal in pending:
        if signal.decision_date != PART.M1_END:
            raise DataContractError(
                f"UNEXPECTED_PENDING_SIGNAL: {signal.decision_date} (only 2020-12-31 may pend)."
            )

    opens_m1 = {s: raw_open[s] for s in m1_sessions}
    closes_m1 = {s: raw_close[s] for s in m1_sessions}
    div_events = [
        ACC.DividendEvent(
            ex_date=e.ex_date,
            payable_date=e.payable_date,
            amount_per_share=e.amount_per_share,
        )
        for e in dividends
        if PART.M1_START <= e.ex_date <= PART.M1_END
    ]

    decision_by_execution: Dict[str, str] = {}
    execution_by_session: Dict[date, str] = {}
    for signal in runnable:
        execution = exec_map[signal.decision_date]
        assert execution is not None
        execution_by_session[execution] = signal.state
        decision_by_execution[execution.isoformat()] = signal.decision_date.isoformat()

    baseline = ACC.run_portfolio(
        path="BASELINE",
        m1_sessions=m1_sessions,
        opens_raw=opens_m1,
        closes_raw=closes_m1,
        execution_by_session=execution_by_session,
        dividends=div_events,
        slippage_bps=ACC.BASELINE_SLIPPAGE_BPS,
        fee_multiplier=1,
    )
    stress = ACC.run_portfolio(
        path="STRESS",
        m1_sessions=m1_sessions,
        opens_raw=opens_m1,
        closes_raw=closes_m1,
        execution_by_session=execution_by_session,
        dividends=div_events,
        slippage_bps=ACC.STRESS_SLIPPAGE_BPS,
        fee_multiplier=2,
    )
    benchmark = ACC.run_portfolio(
        path="BENCHMARK",
        m1_sessions=m1_sessions,
        opens_raw=opens_m1,
        closes_raw=closes_m1,
        execution_by_session={m1_sessions[0]: "LONG"},
        dividends=div_events,
        slippage_bps=ACC.BASELINE_SLIPPAGE_BPS,
        fee_multiplier=1,
    )

    def with_decisions(
        trades: List[ACC.TradeRecord],
    ) -> List[ACC.TradeRecord]:
        bound: List[ACC.TradeRecord] = []
        for trade in trades:
            key = trade.execution_date.isoformat()
            bound.append(
                replace(
                    trade,
                    decision_date=date.fromisoformat(decision_by_execution[key])
                    if key in decision_by_execution
                    else None,
                )
            )
        return bound

    baseline.trades[:] = with_decisions(baseline.trades)
    stress.trades[:] = with_decisions(stress.trades)

    signal_doc = LED.signal_ledger(signals, pending)
    signal_sha = write_json(DATA_DIR / "signal_ledger_reproducibility_001.json", signal_doc)
    base_exec = LED.execution_ledger(baseline)
    base_exec_sha = write_json(
        DATA_DIR / "execution_ledger_baseline_reproducibility_001.json", base_exec
    )
    stress_exec = LED.execution_ledger(stress)
    stress_exec_sha = write_json(
        DATA_DIR / "execution_ledger_stress_reproducibility_001.json", stress_exec
    )
    base_eq = LED.equity_ledger(baseline.equity_curve, "BASELINE")
    base_eq_sha = write_json(DATA_DIR / "equity_baseline_reproducibility_001.json", base_eq)
    stress_eq = LED.equity_ledger(stress.equity_curve, "STRESS")
    stress_eq_sha = write_json(DATA_DIR / "equity_stress_reproducibility_001.json", stress_eq)
    bench_eq = LED.equity_ledger(benchmark.equity_curve, "BENCHMARK")
    bench_eq_sha = write_json(
        DATA_DIR / "equity_benchmark_reproducibility_001.json", bench_eq
    )

    def metrics(result: ACC.PortfolioResult) -> Dict[str, str]:
        returns = [
            r.daily_return for r in result.equity_curve if r.daily_return is not None
        ]
        total_return = result.ending_equity / ACC.SIMULATED_STARTING_AUM - Decimal("1")
        slippage = sum(
            (ACC.execution_slippage_cost(t) for t in result.trades), Decimal("0")
        )
        return {
            "ending_aum": str(result.ending_equity),
            "net_total_return": str(total_return),
            "annualized_sharpe": str(ACC.annualized_sharpe(returns)),
            "max_drawdown": str(ACC.max_drawdown([r.total_equity for r in result.equity_curve])),
            "completed_trades": str(len(result.trades)),
            "regulatory_fees_paid": str(result.regulatory_fees_paid),
            "execution_slippage_cost": str(slippage),
            "dividends_received": str(result.dividends_received),
            "terminal_receivable": str(result.terminal_receivable),
            "terminal_shares": str(result.ending_shares),
            "terminal_cash": str(result.ending_cash),
        }

    base_m = metrics(baseline)
    stress_m = metrics(stress)
    bench_m = metrics(benchmark)
    g6_derived = contract_qualification.no_material_failure
    gates = GATES.evaluate_gates(
        GATES.GateInputs(
            baseline_net_total_return=Decimal(base_m["net_total_return"]),
            baseline_net_annualized_sharpe=Decimal(base_m["annualized_sharpe"]),
            baseline_max_drawdown=Decimal(base_m["max_drawdown"]),
            benchmark_max_drawdown=Decimal(bench_m["max_drawdown"]),
            stress_net_total_return=Decimal(stress_m["net_total_return"]),
            no_material_contract_failure=g6_derived,
        )
    )
    verdict = GATES.classify_m1_verdict(gates, g6_derived)
    for label, payload in (
        ("BASELINE", base_m),
        ("STRESS", stress_m),
        ("BENCHMARK", bench_m),
    ):
        print(f"{label}: {payload['ending_aum']} ret={payload['net_total_return']}")
    print(
        f"GATES: G1={gates.g1} G2={gates.g2} G3={gates.g3} "
        f"G4={gates.g4} G5={gates.g5} G6={gates.g6} AND={gates.conjunction}"
    )
    print(f"VERDICT = {verdict}")

    result_manifest = {
        "manifest_id": "HYP_009_R2_M1_REPRODUCIBILITY_RESULT",
        "manifest_type": "M1_REPRODUCIBILITY_RESULT_MANIFEST",
        "hypothesis_id": "HYP_009",
        "core_id": "CORE-001",
        "source_head": "a3170aab0ca2e3d473d4ab28202110b7250d0ce3",
        "original_run_classification": "M1_ORIGINAL_RESULT_INVALIDATED_FOR_ARTIFACT_INTEGRITY_REPRODUCIBILITY_REQUIRED",
        "original_result_manifest": "docs/phase14/manifests/HYP_009_R2_M1_RESULT.json",
        "contract_hashes": contracts,
        "contract_qualification": {
            "provider_contract_pass": contract_qualification.provider_contract_pass,
            "calendar_coverage_pass": contract_qualification.calendar_coverage_pass,
            "split_raw_alignment_pass": contract_qualification.split_raw_alignment_pass,
            "dividend_contract_pass": contract_qualification.dividend_contract_pass,
            "payable_date_contract_pass": contract_qualification.payable_date_contract_pass,
            "split_contract_pass": contract_qualification.split_contract_pass,
            "response_scope_pass": contract_qualification.response_scope_pass,
            "provenance_hash_pass": contract_qualification.provenance_hash_pass,
            "serialization_integrity_pass": contract_qualification.serialization_integrity_pass,
            "forbidden_partition_access_zero": contract_qualification.forbidden_partition_access_zero,
            "g6_derived": g6_derived,
        },
        "actual_http_transport_attempts": http_count[0],
        "dataset_sha256": dataset_sha,
        "signal_ledger_sha256": signal_sha,
        "baseline_execution_ledger_sha256": base_exec_sha,
        "stress_execution_ledger_sha256": stress_exec_sha,
        "baseline_equity_ledger_sha256": base_eq_sha,
        "stress_equity_ledger_sha256": stress_eq_sha,
        "benchmark_equity_ledger_sha256": bench_eq_sha,
        "baseline_metrics": base_m,
        "stress_metrics": stress_m,
        "benchmark_metrics": bench_m,
        "gates": {
            "G1": gates.g1,
            "G2": gates.g2,
            "G3": gates.g3,
            "G4": gates.g4,
            "G5": gates.g5,
            "G6": gates.g6,
            "conjunction": gates.conjunction,
        },
        "verdict": verdict,
        "m2_access_count": 0,
        "m3_access_count": 0,
        "quarantine_access_count": 0,
        "prospective_access_count": 0,
        "hyp_007_empirical_read_count": 0,
        "paper_authorized": False,
        "live_authorized": False,
        "capital_authority_usd": "0.00",
        "no_real_orders": True,
    }
    result_raw = json.dumps(result_manifest, indent=2, sort_keys=True)
    with open(
        "docs/phase14/manifests/HYP_009_R2_M1_REPRODUCIBILITY_RESULT.json",
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        handle.write(result_raw)
    print("Reproducibility result sealed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
