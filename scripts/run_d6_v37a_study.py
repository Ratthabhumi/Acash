"""Frozen V37A offline study; no network, no admission, immutable new output dirs."""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import date
from decimal import Decimal as D
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.runtime_identity import get_current_runtime_sha
from acash.evidence import canonical_manifest_sha256, content_sha256, write_immutable_json
from acash.research.d6.accounting import D6_INITIAL_NAV, D6_REGISTERED_PORTFOLIOS, D6CostModel
from acash.research.d6.attribution import broker_attribution, household_attribution
from acash.research.d6.contributions import h10_rate, parse_h10_rates
from acash.research.d6.funding import FundingScenario, plan_funding_thb, reconcile_funding
from acash.research.d6.local_exploratory import load_local_inputs, official_sessions
from scripts.run_d6_contribution_study import _metrics
from scripts.run_d6_v36_study import AUDIT_ROWS, R2_COST, _household, _run, _write

SPEC = Path('docs/research/evidence/v37a_frozen_study_20261027.json')
Case = Tuple[str, str, D, FundingScenario, D6CostModel, bool]


def cases(config: Mapping[str, Any]) -> List[Case]:
    base = config['base']
    def scenario(label: str, cadence: int, overrides: Mapping[str, Any]) -> FundingScenario:
        values = {**base, **overrides}
        return FundingScenario(label, cadence, D(values['sender_fee_thb']), D(values['fx_spread']),
                               D(values['intermediary_fee_usd']), int(values['delay_sessions']))
    result: List[Case] = []
    for raw in config['monthly_thb']:
        amount = D(raw)
        for cadence in config['cadence_events']:
            label = f'THB{raw}_E{cadence}'
            result.append((label, 'PRIMARY', amount, scenario(label, cadence, {}), R2_COST, False))
        label = f'THB{raw}_CTRL'
        result.append((label, 'PRIMARY', amount, FundingScenario(label, cadence=1), R2_COST, False))
    sensitivity = config['sensitivities']
    for field, values in sensitivity['one_at_a_time'].items():
        for value in values:
            label = f'SENS_{field}_{value}'
            cost = next(c for name, c, _ in AUDIT_ROWS if name == value) if field == 'cost_row' else R2_COST
            overrides = {} if field in ('cost_row', 'whole_shares') else {field: value}
            result.append((label, 'SENSITIVITY', D(sensitivity['monthly_thb']),
                           scenario(label, sensitivity['cadence_events'], overrides), cost,
                           bool(value) if field == 'whole_shares' else False))
    if len(result) != 27 or sum(c[1] == 'PRIMARY' for c in result) != 20 or len({c[0] for c in result}) != 27:
        raise DataContractError('V37A_FROZEN_GRID_MISMATCH.')
    return result


def verify_baseline(directory: Path, config: Mapping[str, Any]) -> Dict[str, object]:
    for original, digest in config['v36_output_sha256'].items():
        if content_sha256((directory / Path(original).name).read_bytes()) != digest:
            raise DataContractError(f'V37A_V36_REGRESSION: {Path(original).name}.')
    with (directory / 'v36_cost_audit.csv').open(encoding='utf-8', newline='') as f:
        current = {(r['scenario'], r['row'], r['portfolio']): r for r in csv.DictReader(f)}
    with Path('data/local_research/v35/v35_grid.csv').open(encoding='utf-8', newline='') as f:
        old = [r for r in csv.DictReader(f) if r['dataset'] == 'max' and r['row'] in ('R2', 'R3', 'R4', 'R5')]
    if len(old) != 80:
        raise DataContractError('V37A_V35_REGRESSION_CELL_COUNT.')
    for row in old:
        key = (row['scenario'], row['row'], row['portfolio'])
        found = current.get(key)
        if row['status'] != 'RUN':
            if found is not None:
                raise DataContractError(f'V37A_V35_STATUS_CHANGED: {key}.')
        elif found is None or any(row[k] != v for k, v in found.items() if k in row):
            raise DataContractError(f'V37A_V35_METRIC_CHANGED: {key}.')
    return {'v36_files_byte_identical': 5, 'v35_cells_identical': 80}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline-rerun', type=Path, required=True)
    args = parser.parse_args()
    if subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip():
        raise DataContractError('V37A_REQUIRES_CLEAN_COMMITTED_SOURCE.')
    config = json.loads(SPEC.read_text(encoding='utf-8'))
    for name, digest in config['input_sha256'].items():
        if content_sha256(Path(name).read_bytes()) != digest:
            raise DataContractError(f'V37A_INPUT_HASH_MISMATCH: {name}.')
    baseline = verify_baseline(args.baseline_rerun, config)
    root = Path('data/local_research/v37a').resolve()
    out = args.out.resolve()
    if root not in out.parents:
        raise DataContractError('V37A_OUTPUT_MUST_BE_WITHIN_IGNORED_V37A_ROOT.')
    out.mkdir(parents=True, exist_ok=False)
    data = Path('data/local_research/v36/reconciled_max')
    inputs = load_local_inputs(data / 'bars_raw.csv', data / 'distributions.csv', data / 'splits.csv')
    rates = parse_h10_rates(Path('data/local_research/fx/h10_dat00_th_20261025.txt').read_text(encoding='utf-8'))
    window = list(official_sessions(date.fromisoformat(config['start']), date.fromisoformat(config['end'])))
    portfolio = next(p for p in D6_REGISTERED_PORTFOLIOS if p.name == config['portfolio'])
    if D(config['initial_usd']) != D6_INITIAL_NAV:
        raise DataContractError('V37A_INITIAL_NAV_MISMATCH.')
    rows: List[Dict[str, object]] = []
    attributes: List[Dict[str, object]] = []
    for label, group, amount, funding, cost, whole in cases(config):
        plan = plan_funding_thb(window, amount, rates, funding)
        if len(plan.savings) != config['expected_savings_events']:
            raise DataContractError('V37A_SAVINGS_EVENT_COUNT.')
        ledger = reconcile_funding(plan)
        result = _run(inputs, window, portfolio, cost, whole, plan.contributions)
        if result is None:
            raise DataContractError(f'V37A_UNEXPECTED_NOT_RUN: {label}.')
        metrics = _metrics(result)  # canonical TWR/XIRR and independent broker cash identity
        broker = broker_attribution(result, D6_INITIAL_NAV, {s: inputs.closes[s][window[-1]] for s in portfolio.weights})
        household = household_attribution(plan, broker, result.terminal_nav, h10_rate(rates, window[-1])[0])
        rows.append({'case': label, 'group': group, 'monthly_thb': amount, 'cadence_events': funding.cadence,
                     'whole_shares': whole, 'cost': cost.label, 'savings_events': len(plan.savings),
                     **metrics, **_household(plan, result, rates, window), **ledger})
        attributes.append({'case': label, **{f'broker_{k}': v for k, v in broker.items()},
                           **{f'household_{k}': v for k, v in household.items()}})
    _write(out / 'v37a_grid.csv', rows)
    _write(out / 'v37a_attribution.csv', attributes)
    manifest = {
        'label': config['label'], 'runtime_sha': get_current_runtime_sha(),
        'frozen_config_sha256': canonical_manifest_sha256(config), 'input_sha256': config['input_sha256'],
        'primary_cells': 20, 'sensitivity_cells': 7, 'baseline_regression': baseline,
        'funding_broker_household_identities': 'PASS_ALL_27',
        'output_sha256': {p.name: content_sha256(p.read_bytes()) for p in sorted(out.glob('*.csv'))},
    }
    digest = write_immutable_json(out / 'run_manifest.json', manifest)
    print(json.dumps({'manifest_sha256': digest, **manifest}, indent=2))


if __name__ == '__main__':
    main()
