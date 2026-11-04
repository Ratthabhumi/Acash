import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { barFraction, classifyView } from '../src/services/upiView.ts';
import { FINDINGS, findingsFor } from '../src/services/upiFindings.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf-8');
const fixture = (name) => JSON.parse(read(`src/fixtures/${name}`));
const AUTHORITY = ['PRIVATE_OBSERVATION_AUTHORIZATION_NOT_REQUIRED', 'OWNER_PRIVATE_OBSERVATION_AUTHORIZED'];

test('every reason code the wealth pack can emit has a finding with a valid severity', () => {
  const pack = read('../src/acash/invest/wealth_pack.py');
  const codes = [...pack.matchAll(/reasons\.append\(f?"([A-Z0-9_]+):/g)].map((m) => m[1]);
  assert.ok(codes.length >= 12, `parsed ${codes.length} codes`);
  for (const code of codes) {
    assert.ok(FINDINGS[code], `${code} has no finding entry`);
    assert.ok(['CRITICAL', 'IMPORTANT', 'INFO'].includes(FINDINGS[code].severity));
  }
  for (const code of AUTHORITY) assert.equal(FINDINGS[code], undefined, 'authority codes are not findings');
});

test('findings follow classifyView warnings, sort by severity and keep the exact detail', () => {
  for (const name of ['upi_synthetic_view.json', 'upi_synthetic_evidence_only_view.json']) {
    const state = classifyView(fixture(name), 'SYNTHETIC_DEMO');
    const findings = findingsFor(state.warnings, state.view.decision_status.reasons);
    assert.equal(findings.length, state.warnings.length);
    assert.ok(findings.every((f) => !AUTHORITY.includes(f.code)));
    const order = findings.map((f) => ['CRITICAL', 'IMPORTANT', 'INFO'].indexOf(f.severity));
    assert.deepEqual(order, [...order].sort((a, b) => a - b));
    for (const f of findings) assert.ok(f.detail.startsWith(f.code));
  }
  const full = classifyView(fixture('upi_synthetic_view.json'), 'SYNTHETIC_DEMO');
  assert.equal(findingsFor(full.warnings, full.view.decision_status.reasons)[0].code, 'ACCOUNT_TOTALS_NOT_FULLY_RECONCILED');
});

test('unknown codes stay visible as IMPORTANT with the raw code', () => {
  const [f] = findingsFor(['NEW_CODE_X'], ['NEW_CODE_X: something new.']);
  assert.deepEqual([f.code, f.severity, f.title, f.detail], ['NEW_CODE_X', 'IMPORTANT', 'NEW_CODE_X', 'NEW_CODE_X: something new.']);
});

test('barFraction is bounded geometry and fails to zero on missing or invalid input', () => {
  assert.equal(barFraction('0.4136'), 0.4136);
  assert.equal(barFraction('8250.00', '95750.00'), 8250 / 95750);
  assert.equal(barFraction('2', '1'), 1);
  for (const [p, w] of [[null, '1'], [undefined, '1'], ['-1', '1'], ['1', '0'], ['1', '-5'], ['abc', '1'], ['1e3', '1'], ['NaN', '1'], ['1', null]]) {
    assert.equal(barFraction(p, w), 0, `${p}/${w}`);
  }
});

test('portfolio UI does not compute or persist figures and keeps the A-E structure', () => {
  const page = read('src/pages/PortfolioPage.tsx');
  const charts = read('src/components/charts/PortfolioCharts.tsx');
  for (const src of [page, charts, read('src/services/upiFindings.ts')]) {
    for (const banned of ['toFixed(', 'toLocaleString(', 'parseFloat(', 'localStorage', 'sessionStorage', 'console.', 'fetch(', 'navigator.sendBeacon']) {
      assert.ok(!src.includes(banned), `${banned} must not appear`);
    }
  }
  for (const id of ['sec-a', 'sec-b', 'sec-c', 'sec-d', 'sec-e']) assert.match(page, new RegExp(`id="${id}"`));
  // V89: the headline is the broker-displayed observation; the ACASH computed valuation is separate.
  assert.match(page, /broker_observation\?\.displayed_total/);
  assert.match(page, /ACASH คำนวณ \(statement\)/);
  assert.match(page, /evidenceOnly \? NOT_ESTABLISHED : formatDec\(ov\.computed_nav_ppds\)/);
  assert.ok(!/label="Total best evidence"/.test(page), 'best evidence must not be the portfolio headline');
  assert.ok(!/NAV history|drawdown|projection/i.test(page), 'no time-series charts from a single snapshot');
});
