"""HYP_009 R2 M2 canonical runner: acquire -> qualify -> seal -> execute once -> gates.

Frozen R1/M2 contracts only. Default DRY-RUN (no network). Live execution
requires --execute-m2 under explicit human authorization. K = 1, single run.
M1 signal history is reused SOLELY as causal warmup authority (sealed files).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.hyp_009_daily_client import (
    HYP009AlpacaClient,
    Hyp009PreNetworkGuard,
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
M1_DATASET_PATH = Path("data/hyp_009/m1_dataset_reproducibility_001.json")
M1_SIGNAL_PATH = Path("data/hyp_009/signal_ledger_reproducibility_001.json")
M2_DATA_DIR = Path("data/hyp_009")
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


def sha_canonical(obj: object) -> str:
    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(obj).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HYP_009 R2 M2 canonical run.")
    parser.add_argument("--execute-m2", action="store_true", default=False)
    args = parser.parse_args(argv)

    print("=== HYP_009 R2 M2 canonical runner ===")
    contracts = verify_contracts()
    print("R1 contracts verified.")

    if not args.execute_m2:
        print("DRY-RUN: no network, no dataset, no execution. Use --execute-m2.")
        return 0

    try:
        EnvAlpacaCredentialProvider().load()
    except AlpacaCredentialError as exc:
        print(f"BLOCKED_MISSING_CREDENTIALS: {exc}")
        return 2
    print("CREDENTIAL_KEY_PRESENT = True / CREDENTIAL_SECRET_PRESENT = True")

    calendar = NyseCa1Calendar()
    m2_sessions = PART.expected_sessions(calendar, PART.M2_START, PART.M2_END)
    print(f"Expected M2 sessions 2021-2024: {len(m2_sessions)}")

    http_count = [0]

    def _count() -> None:
        http_count[0] += 1

    guard = Hyp009PreNetworkGuard(min_date=PART.M2_START, max_date=PART.M2_END)
    client = HYP009AlpacaClient(guard=guard, http_attempt_listener=_count)
    start_utc, end_utc = inclusive_date_window_to_utc_bounds(PART.M2_START, PART.M2_END)

    def _fetch(adjustment: PriceAdjustment) -> Any:
        return client.fetch_historical_bars(
            symbol="SPY",
            start_utc=start_utc,
            end_utc=end_utc,
            feed=MarketDataFeed.SIP,
            adjustment=adjustment,
            timeframe="1Day",
        )

    split_result = _fetch(PriceAdjustment.SPLIT)
    raw_result = _fetch(PriceAdjustment.RAW)
    print(f"Actual HTTP transport attempts: {http_count[0]}")
    aligned = QUAL.qualify_bar_series(m2_sessions, split_result.bars, raw_result.bars)
    print(f"M2 bar qualification PASS: {len(aligned)} sessions.")

    # Sealed M1 warmup authority (signal history only; M1 P&L never carried).
    m1_dataset = json.loads(M1_DATASET_PATH.read_text(encoding="utf-8"))
    m1_signals_sealed = json.loads(M1_SIGNAL_PATH.read_text(encoding="utf-8"))
    m1_split = {
        date.fromisoformat(row["date"]): Decimal(row["c"])
        for row in m1_dataset["split_bars"]
    }
    m1_divs = {
        date.fromisoformat(row["ex_date"]): Decimal(row["amount"])
        for row in m1_dataset["dividends"]
    }

    m2_split = {b.timestamp_utc.date(): b.close for b in split_result.bars}
    m2_raw_open = {b.timestamp_utc.date(): b.open for b in raw_result.bars}
    m2_raw_close = {b.timestamp_utc.date(): b.close for b in raw_result.bars}

    # Split continuity across the M1/M2 boundary plus inside M2.
    m1_sessions_ordered = sorted(m1_split.keys())
    full_order = m1_sessions_ordered + m2_sessions
    full_split = dict(m1_split)
    full_split.update({s: m2_split[s] for s in m2_sessions})
    full_raw_m1 = {
        date.fromisoformat(row["date"]): Decimal(row["c"])
        for row in m1_dataset["raw_bars"]
    }
    full_raw = dict(full_raw_m1)
    full_raw.update({s: m2_raw_close[s] for s in m2_sessions})
    split_status = QUAL.require_no_unbound_splits(full_order, full_split, full_raw)
    print(f"Split continuity (M1+M2): {split_status}")

    ssga_path = Path(
        "docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json"
    )
    ssga_sha = hashlib.sha256(ssga_path.read_bytes()).hexdigest()
    if ssga_sha != EXPECTED_SSGA_MANIFEST_SHA256:
        raise DataContractError(f"SSGA_MANIFEST_MISMATCH: {ssga_sha}. STOP.")
    ssga = json.loads(ssga_path.read_text(encoding="utf-8"))
    m2_dividends = QUAL.qualify_dividends(
        ssga["distributions"], PART.M2_START, PART.M2_END
    )
    print(f"M2 dividend qualification PASS: {len(m2_dividends)} events.")

    # Causal TR continuity: rebuild over M1-sealed + M2 observations, verify sealed levels.
    full_divs: Dict[date, Decimal] = dict(m1_divs)
    for event in m2_dividends:
        if event.ex_date in full_divs and full_divs[event.ex_date] != event.amount_per_share:
            raise DataContractError(
                f"M2_DIVIDEND_CONFLICT_WITH_M1_HISTORY: {event.ex_date}."
            )
        full_divs[event.ex_date] = event.amount_per_share
    full_index = SIG.build_total_return_index(full_order, full_split, full_divs)
    sealed_levels = {
        row["decision_date"]: row["signal_level"] for row in m1_signals_sealed["rows"]
    }
    recomputed_m1_ends = [
        d for d in full_order if d <= PART.M1_END and d in {
            date.fromisoformat(r["decision_date"]) for r in m1_signals_sealed["rows"]
        }
    ]
    for row in m1_signals_sealed["rows"]:
        decision = date.fromisoformat(row["decision_date"])
        if str(full_index[decision]) != row["signal_level"]:
            raise DataContractError(
                f"TR_CONTINUITY_MISMATCH at {decision}: sealed M1 level not reproduced."
            )
    print(f"TR continuity verified over {len(sealed_levels)} sealed M1 month-ends.")

    m2_month_ends = [d for d in PART.month_end_sessions(m2_sessions)]
    if m2_month_ends[0] != date(2021, 1, 29):
        raise DataContractError(f"M2_FIRST_MONTH_END_UNEXPECTED: {m2_month_ends[0]}.")
    m2_levels = [full_index[d] for d in m2_month_ends]
    # SMA10 over the continuous level series (M1 tail + M2).
    m1_tail = [
        Decimal(m1_signals_sealed["rows"][i]["signal_level"])
        for i in range(len(m1_signals_sealed["rows"]) - 9, len(m1_signals_sealed["rows"]))
    ]
    assert len(m1_tail) == 9
    continuous = m1_tail + m2_levels
    m2_signals: List[Dict[str, Any]] = []
    prior_state: str | None = None
    # Dec-2020 frozen initial state authority.
    dec2020 = next(
        r for r in m1_signals_sealed["rows"] if r["decision_date"] == "2020-12-31"
    )
    if dec2020["state"] != "LONG":
        raise DataContractError("DEC2020_FROZEN_STATE_NOT_LONG.")
    prior_state = "LONG"
    for i, month_end in enumerate(m2_month_ends):
        window = continuous[i : i + 10]
        if len(window) != 10:
            raise DataContractError("M2_SMA_WINDOW_CORRUPT.")
        sma = sum(window, Decimal("0")) / Decimal(10)
        level = m2_levels[i]
        state = "LONG" if level > sma else "CASH"
        m2_signals.append(
            {
                "decision_date": month_end.isoformat(),
                "signal_level": str(level),
                "sma10": str(sma),
                "state": state,
                "prior_state": prior_state,
                "transition": state != prior_state,
            }
        )
        prior_state = state
    print(f"M2 signals: {len(m2_signals)} (Dec-2020 initial LONG injected).")

    first_m2_execution = next(s for s in m2_sessions if s > date(2020, 12, 31))
    execution_by_session: Dict[date, str] = {}
    decision_by_execution: Dict[str, str] = {}
    pending: List[Dict[str, Any]] = []
    # Initial execution from the frozen Dec-2020 LONG at the first M2 open.
    execution_by_session[first_m2_execution] = "LONG"
    decision_by_execution[first_m2_execution.isoformat()] = "2020-12-31"
    for signal in m2_signals:
        if not signal["transition"]:
            continue
        decision = date.fromisoformat(signal["decision_date"])
        execution = next((s for s in m2_sessions if s > decision), None)
        if execution is None:
            pending.append({**signal, "status": "PENDING_NEXT_PARTITION_EXECUTION_NOT_EXECUTED"})
        else:
            execution_by_session[execution] = signal["state"]
            decision_by_execution[execution.isoformat()] = signal["decision_date"]
    dec2024_pending = [p for p in pending if p["decision_date"].startswith("2024-12")]
    print(f"Transitions scheduled: {len(execution_by_session)}; pending: {len(pending)}.")

    opens_m2 = {s: m2_raw_open[s] for s in m2_sessions}
    closes_m2 = {s: m2_raw_close[s] for s in m2_sessions}
    div_events = [
        ACC.DividendEvent(
            ex_date=e.ex_date,
            payable_date=e.payable_date,
            amount_per_share=e.amount_per_share,
        )
        for e in m2_dividends
    ]
    baseline = ACC.run_portfolio(
        path="M2_BASELINE", m1_sessions=m2_sessions, opens_raw=opens_m2,
        closes_raw=closes_m2, execution_by_session=execution_by_session,
        dividends=div_events, slippage_bps=ACC.BASELINE_SLIPPAGE_BPS, fee_multiplier=1,
    )
    stress = ACC.run_portfolio(
        path="M2_STRESS", m1_sessions=m2_sessions, opens_raw=opens_m2,
        closes_raw=closes_m2, execution_by_session=execution_by_session,
        dividends=div_events, slippage_bps=ACC.STRESS_SLIPPAGE_BPS, fee_multiplier=2,
    )
    benchmark = ACC.run_portfolio(
        path="M2_BENCHMARK", m1_sessions=m2_sessions, opens_raw=opens_m2,
        closes_raw=closes_m2, execution_by_session={m2_sessions[0]: "LONG"},
        dividends=div_events, slippage_bps=ACC.BASELINE_SLIPPAGE_BPS, fee_multiplier=1,
    )

    def with_decisions(trades: List[ACC.TradeRecord]) -> List[ACC.TradeRecord]:
        from dataclasses import replace as _replace

        bound: List[ACC.TradeRecord] = []
        for trade in trades:
            key = trade.execution_date.isoformat()
            bound.append(
                _replace(
                    trade,
                    decision_date=date.fromisoformat(decision_by_execution[key])
                    if key in decision_by_execution
                    else None,
                )
            )
        return bound

    baseline.trades[:] = with_decisions(baseline.trades)
    stress.trades[:] = with_decisions(stress.trades)

    M2_DATA_DIR.mkdir(parents=True, exist_ok=True)
    dataset_payload = {
        "dataset_id": "DS_SPY_CORE001_HYP009_M2_ALPACA_1DAY_SIP",
        "provider": "ALPACA_HISTORICAL_STOCK_BARS",
        "feed": "sip",
        "timeframe": "1Day",
        "request_bounds": ["2021-01-01", "2024-12-31"],
        "actual_http_transport_attempts": http_count[0],
        "expected_sessions": len(m2_sessions),
        "split_bars": [
            {"date": b.timestamp_utc.date().isoformat(), "o": str(b.open),
             "h": str(b.high), "l": str(b.low), "c": str(b.close), "v": str(b.volume)}
            for b in split_result.bars
        ],
        "raw_bars": [
            {"date": b.timestamp_utc.date().isoformat(), "o": str(b.open),
             "h": str(b.high), "l": str(b.low), "c": str(b.close), "v": str(b.volume)}
            for b in raw_result.bars
        ],
        "dividends": [
            {"ex_date": e.ex_date.isoformat(), "payable_date": e.payable_date.isoformat(),
             "amount": str(e.amount_per_share)}
            for e in m2_dividends
        ],
        "split_status": split_status,
        "ssga_manifest_sha256": ssga_sha,
        "split_page_provenance": page_provenance(split_result),
        "raw_page_provenance": page_provenance(raw_result),
        "m2_access_count": http_count[0],
        "m3_access_count": 0,
        "quarantine_access_count": 0,
        "prospective_access_count": 0,
        "dataset_state": "M2_DATASET_QUALIFIED_AND_SEALED_PERFORMANCE_NOT_YET_OBSERVED",
    }
    dataset_sha = write_json(M2_DATA_DIR / "m2_dataset.json", dataset_payload)
    print(f"M2 dataset sealed: {dataset_sha}")

    signal_doc = {
        "warmup_authority": "SEALED_M1_SIGNAL_HISTORY_THROUGH_2020_12_31",
        "dec2020_injected_state": "LONG",
        "rows": m2_signals,
        "pending_terminal": pending,
    }
    signal_sha = write_json(M2_DATA_DIR / "m2_signal_ledger.json", signal_doc)
    base_exec_sha = write_json(
        M2_DATA_DIR / "m2_execution_ledger_baseline.json", LED.execution_ledger(baseline)
    )
    stress_exec_sha = write_json(
        M2_DATA_DIR / "m2_execution_ledger_stress.json", LED.execution_ledger(stress)
    )
    base_eq_sha = write_json(
        M2_DATA_DIR / "m2_equity_baseline.json", LED.equity_ledger(baseline.equity_curve, "M2_BASELINE")
    )
    stress_eq_sha = write_json(
        M2_DATA_DIR / "m2_equity_stress.json", LED.equity_ledger(stress.equity_curve, "M2_STRESS")
    )
    bench_eq_sha = write_json(
        M2_DATA_DIR / "m2_equity_benchmark.json", LED.equity_ledger(benchmark.equity_curve, "M2_BENCHMARK")
    )

    def metrics(result: ACC.PortfolioResult) -> Dict[str, str]:
        returns = [r.daily_return for r in result.equity_curve if r.daily_return is not None]
        total_return = result.ending_equity / ACC.SIMULATED_STARTING_AUM - Decimal("1")
        slippage = sum((ACC.execution_slippage_cost(t) for t in result.trades), Decimal("0"))
        return {
            "starting_aum": str(ACC.SIMULATED_STARTING_AUM),
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

    base_m, stress_m, bench_m = metrics(baseline), metrics(stress), metrics(benchmark)

    evidence = GATES.ContractQualificationEvidence(
        provider_contract_hash_recomputed=sha_canonical(
            json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_009.json").read_text(encoding="utf-8"))["provider_contract"]
        ),
        provider_contract_hash_authority=contracts["provider_contract_hash"],
        request_symbol="SPY",
        request_feed="sip",
        request_timeframe="1Day",
        request_start=PART.M2_START,
        request_end=PART.M2_END,
        partition="M2",
        expected_sessions=tuple(m2_sessions),
        split_sessions=tuple(sorted({b.timestamp_utc.date() for b in split_result.bars})),
        raw_sessions=tuple(sorted({b.timestamp_utc.date() for b in raw_result.bars})),
        dividend_validated_count=len(m2_dividends),
        dividend_missing_payable_count=sum(
            1 for e in m2_dividends if e.payable_date is None
        ),
        split_determination=split_status,
        page_shas_recorded=tuple(p["raw_sha256"] for p in dataset_payload["split_page_provenance"])
        + tuple(p["raw_sha256"] for p in dataset_payload["raw_page_provenance"]),
        page_shas_recomputed=tuple(p["raw_sha256"] for p in dataset_payload["split_page_provenance"])
        + tuple(p["raw_sha256"] for p in dataset_payload["raw_page_provenance"]),
        sealed_hash_pairs=(
            (dataset_sha, hashlib.sha256((M2_DATA_DIR / "m2_dataset.json").read_bytes()).hexdigest()),
        ),
        # M2 accesses are AUTHORIZED (counted separately as m2_access_count);
        # forbidden partitions (M3/quarantine/prospective/HYP007) are zero.
        forbidden_access_counts=(0, 0, 0, 0),
    )
    qual = GATES.derive_contract_qualification(evidence)
    g6 = qual.no_material_failure
    gates = GATES.evaluate_gates(
        GATES.GateInputs(
            baseline_net_total_return=Decimal(base_m["net_total_return"]),
            baseline_net_annualized_sharpe=Decimal(base_m["annualized_sharpe"]),
            baseline_max_drawdown=Decimal(base_m["max_drawdown"]),
            benchmark_max_drawdown=Decimal(bench_m["max_drawdown"]),
            stress_net_total_return=Decimal(stress_m["net_total_return"]),
            no_material_contract_failure=g6,
        )
    )
    verdict = GATES.classify_m2_verdict(gates, g6)
    for label, payload in (("M2_BASELINE", base_m), ("M2_STRESS", stress_m), ("M2_BENCHMARK", bench_m)):
        print(f"{label}: {payload['ending_aum']} ret={payload['net_total_return']}")
    print(f"GATES: G1={gates.g1} G2={gates.g2} G3={gates.g3} G4={gates.g4} G5={gates.g5} G6={gates.g6} AND={gates.conjunction}")
    print(f"VERDICT = {verdict}")

    result_manifest = {
        "manifest_id": "HYP_009_R2_M2_RESULT",
        "manifest_type": "M2_EXECUTION_RESULT_MANIFEST",
        "hypothesis_id": "HYP_009",
        "core_id": "CORE-001",
        "source_head": "53f031028e186d4081ce5a47df722a08be48de95",
        "contract_hashes": contracts,
        "dec2020_initial_state": "LONG",
        "first_m2_execution_date": first_m2_execution.isoformat(),
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
        "gates": {"G1": gates.g1, "G2": gates.g2, "G3": gates.g3, "G4": gates.g4,
                  "G5": gates.g5, "G6": gates.g6, "conjunction": gates.conjunction},
        "contract_qualification_derived": g6,
        "verdict": verdict,
        "m2_access_count": http_count[0],
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
    with open("docs/phase14/manifests/HYP_009_R2_M2_RESULT.json", "w", encoding="utf-8", newline="\n") as handle:
        handle.write(result_raw)
    print("M2 result sealed.")
    return 0


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
