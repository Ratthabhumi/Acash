"""Read-only research proposals built from the existing portfolio evaluator.

This module is an *orchestrator*, not a second valuation or optimisation engine: weights come from
the repository's own allocators, scoring and friction estimation come from
``acash.portfolio.evaluation``, and the proposal is a plain data contract with no execution path.

A proposal is a research artefact. It never carries an order, never claims a mandate, and is only
emitted when a return panel qualifies; otherwise the status is ``INSUFFICIENT_EVIDENCE``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.baselines import CashAllocator, EqualWeightAllocator
from acash.portfolio.evaluation import AllocationEvaluator, EvaluationConfig
from acash.portfolio.schema import AllocationCandidate, AssetReturnPanel, PortfolioConstraints

RESEARCH_ONLY = "RESEARCH_ONLY_NOT_AUTHORIZED_FOR_EXECUTION"
TEST_FIXTURE = "TEST_FIXTURE"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
ACTION_EPSILON = Decimal("0.01")


@dataclass(frozen=True)
class ProposalInputs:
    returns: Mapping[str, Sequence[Decimal]]   # symbol -> periodic returns, same order
    timestamps: Sequence[datetime]
    current_weights: Mapping[str, Decimal]
    cash_weight: Decimal = Decimal("0")
    frequency: str = "1D"


def build_panel(inputs: ProposalInputs, universe_id: str = "RESEARCH_PANEL") -> AssetReturnPanel:
    symbols = tuple(sorted(inputs.returns))
    if not symbols:
        raise DataContractError("RESEARCH_PANEL_EMPTY: no instruments.")
    lengths = {len(inputs.returns[s]) for s in symbols}
    if len(lengths) != 1:
        raise DataContractError("RESEARCH_PANEL_RAgged: instruments have different histories.")
    length = lengths.pop()
    if length != len(inputs.timestamps):
        raise DataContractError("RESEARCH_PANEL_TIMESTAMP_MISMATCH: timestamps must align with returns.")
    matrix = tuple(tuple(inputs.returns[s][i] for s in symbols) for i in range(length))
    return AssetReturnPanel(universe_id=universe_id, timestamps=tuple(inputs.timestamps), symbols=symbols,
                            returns_matrix=matrix, frequency=inputs.frequency)


def _expected_returns(panel: AssetReturnPanel, periods_per_year: Decimal) -> Dict[str, Decimal]:
    out: Dict[str, Decimal] = {}
    for index, symbol in enumerate(panel.symbols):
        values = [row[index] for row in panel.returns_matrix]
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        out[symbol] = mean * periods_per_year
    return out


def _candidate(panel: AssetReturnPanel, constraints: PortfolioConstraints,
               current_weights: Mapping[str, Decimal], strategy: str) -> AllocationCandidate:
    if strategy == "CASH":
        return CashAllocator().compute_candidate(panel, constraints, current_weights)
    if strategy == "EQUAL_WEIGHT":
        return EqualWeightAllocator().compute_candidate(panel, constraints, current_weights)
    if strategy == "BUY_AND_HOLD":
        weights = {s: Decimal(str(current_weights.get(s, 0))) for s in panel.symbols}
        if sum(weights.values(), Decimal(0)) <= 0:
            raise DataContractError("RESEARCH_PROPOSAL_NO_CURRENT_WEIGHTS.")
        return AllocationCandidate(candidate_id=f"CAND_HOLD_{panel.universe_id}", allocator_name="BUY_AND_HOLD",
                                   asset_weights=weights)
    raise DataContractError(f"RESEARCH_STRATEGY_UNKNOWN: {strategy}.")


def _actions(current: Mapping[str, Decimal], target: Mapping[str, Decimal]) -> List[Dict[str, str]]:
    actions: List[Dict[str, str]] = []
    for symbol in sorted(set(current) | set(target)):
        now, want = Decimal(str(current.get(symbol, 0))), Decimal(str(target.get(symbol, 0)))
        delta = want - now
        if want == 0 and now > 0:
            action = "EXIT"
        elif delta > ACTION_EPSILON:
            action = "ADD"
        elif delta < -ACTION_EPSILON:
            action = "REDUCE"
        else:
            action = "HOLD"
        actions.append({"symbol": symbol, "action": action,
                        "current_weight": format(now, "f"), "target_weight": format(want, "f"),
                        "change": format(delta, "f")})
    return actions


def build_proposal(inputs: ProposalInputs, *, generated_at: Optional[datetime] = None,
                   periods_per_year: Decimal = Decimal("252"),
                   max_drawdown_limit: Optional[Decimal] = None) -> Dict[str, Any]:
    """Evaluate CASH / BUY_AND_HOLD / EQUAL_WEIGHT out of sample and emit a research proposal."""
    panel = build_panel(inputs)
    if panel.T < 2:
        return {"status": INSUFFICIENT, "missing_evidence": ["return panel needs at least two periods"],
                "governance_status": RESEARCH_ONLY}
    split = max(1, int(panel.T * 0.7))
    from acash.portfolio.tournament import slice_panel
    train, test = slice_panel(panel, 0, split), slice_panel(panel, split, panel.T)
    if test.T < 1:
        return {"status": INSUFFICIENT, "missing_evidence": ["out-of-sample window is empty"],
                "governance_status": RESEARCH_ONLY}

    constraints = PortfolioConstraints()
    evaluator = AllocationEvaluator(EvaluationConfig())
    expected = _expected_returns(train, periods_per_year)
    current = {s: Decimal(str(inputs.current_weights.get(s, 0))) for s in panel.symbols}
    results: Dict[str, Any] = {}
    for strategy in ("CASH", "BUY_AND_HOLD", "EQUAL_WEIGHT"):
        candidate = _candidate(test, constraints, current, strategy)
        evaluation = evaluator.evaluate_candidate(candidate, test, constraints, current, expected)
        results[strategy] = {"evaluation": evaluation, "candidate": candidate}

    def score(name: str) -> Decimal:
        value: Decimal = results[name]["evaluation"].rank_score
        return value

    eligible = [name for name in results
                if results[name]["evaluation"].constraints_satisfied
                and (results[name]["evaluation"].hurdle_rate_cleared or name == "CASH")]
    chosen = max(eligible, key=score) if eligible else "CASH"
    chosen_eval = results[chosen]["evaluation"]
    if max_drawdown_limit is not None and chosen_eval.oos_cvar_95 is not None \
            and chosen_eval.oos_cvar_95 > max_drawdown_limit:
        chosen, chosen_eval = "CASH", results["CASH"]["evaluation"]

    target = {s: Decimal(str(chosen_eval.normalized_weights.get(s, 0))) for s in panel.symbols}
    payload = {
        "proposal_schema": "ACASH_RESEARCH_PROPOSAL_V1",
        "strategy_id": chosen,
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "input_hash": hashlib.sha256(json.dumps(
            [[str(v) for v in inputs.returns[s]] for s in panel.symbols], sort_keys=True).encode()).hexdigest(),
        "universe_id": panel.universe_id,
        "in_sample_period": {"periods": train.T},
        "out_of_sample_period": {"periods": test.T},
        "current_weights": {s: format(current[s], "f") for s in panel.symbols},
        "target_weights": {s: format(target[s], "f") for s in panel.symbols},
        "cash_weight": format(chosen_eval.normalized_cash_weight, "f"),
        "proposed_actions": _actions(current, target),
        "modeled_risk": {"oos_sharpe": None if chosen_eval.oos_sharpe_ratio is None else
                         format(chosen_eval.oos_sharpe_ratio, "f"),
                         "oos_cvar_95": None if chosen_eval.oos_cvar_95 is None else
                         format(chosen_eval.oos_cvar_95, "f"),
                         "constraints_satisfied": chosen_eval.constraints_satisfied,
                         "hurdle_rate_cleared": chosen_eval.hurdle_rate_cleared},
        "transaction_cost_status": "MODELED_ESTIMATE",
        "modeled_transaction_cost": format(chosen_eval.estimated_transaction_cost, "f"),
        "turnover_required": format(chosen_eval.turnover_required, "f"),
        "rank_scores": {name: format(score(name), "f") for name in results},
        "evaluated_strategies": [
            {"strategy": name,
             "rank_score": format(score(name), "f"),
             "constraints_satisfied": bool(results[name]["evaluation"].constraints_satisfied),
             "hurdle_rate_cleared": bool(results[name]["evaluation"].hurdle_rate_cleared)} for name in results
        ],
        "limitations": ["Historical evaluation does not predict future returns.",
                        "Broker fee schedule is not established; costs are modelled estimates.",
                        "No dividend or corporate-action evidence is included."],
        "missing_evidence": ["broker fee schedule", "dividend/corporate-action series"],
        "recommendation_status": RESEARCH_ONLY,
        "governance_status": "RANKING_IS_NOT_APPROVAL",
        "execution_authority": "NONE",
        "disclaimer": "Research-only output. Not an order, not a mandate, not investment advice.",
    }
    return payload
