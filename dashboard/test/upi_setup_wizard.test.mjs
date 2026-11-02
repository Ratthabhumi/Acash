import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ACCOUNT_ROLES, CAPACITY_FIELDS, CASH_KINDS, CLASSIFICATIONS, INSTRUMENT_TYPES, MESSAGES_TH, capacityForSave, clearPlaceholders,
  compact, emptyCapacity, emptySnapshot, messageTh,
} from '../src/services/privateInput.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf-8');
const pyTuple = (src, name) => [...src.match(new RegExp(`${name} = \\(([^)]*)\\)`, 's'))[1].matchAll(/"([A-Z_]+)"/g)].map((m) => m[1]);

test('wizard enumerations and capacity fields mirror the Python contracts', () => {
  const po = read('../src/acash/ppds/private_observation.py');
  assert.deepEqual([...ACCOUNT_ROLES], pyTuple(po, 'ACCOUNT_ROLES'));
  assert.deepEqual([...CASH_KINDS], pyTuple(po, 'CASH_KINDS'));
  assert.deepEqual(INSTRUMENT_TYPES.filter(Boolean), pyTuple(po, 'INSTRUMENT_TYPES'));
  assert.deepEqual(new Set(CLASSIFICATIONS), new Set(pyTuple(po, 'TAXONOMY').filter((c) => c !== 'CASH')));
  const cap = read('../src/acash/invest/capacity_plan.py');
  const fields = [...cap.match(/_FIELDS = \{([^}]*)\}/s)[1].matchAll(/"([a-z0-9_]+)"/g)].map((m) => m[1]);
  assert.deepEqual(new Set([...CAPACITY_FIELDS, 'schema', 'data_class', 'horizon_years']), new Set(fields));
  assert.deepEqual(Object.keys(emptyCapacity()).sort(), [...fields].sort());
});

test('placeholders are cleared, never replaced by a value', () => {
  const doc = { a: 'REPLACE_WITH_THB', b: ['replace_me', 'X'], c: { d: 'KEEP' }, n: 7 };
  assert.deepEqual(clearPlaceholders(doc), { a: '', b: ['', 'X'], c: { d: 'KEEP' }, n: 7 });
});

test('compact drops only empty optional values and never invents amounts', () => {
  const snap = emptySnapshot();
  snap.accounts.push({ account_ref: 'A_ONE', broker: 'DIME', role: 'LONG_TERM', base_currency: 'USD',
    reported_total: { amount: '', currency: 'USD' }, cash: [], positions: [{ security_id: 'SYN', sub_portfolio: 'Core', quantity: '' }] });
  const out = compact(snap);
  assert.deepEqual(out.accounts[0], { account_ref: 'A_ONE', broker: 'DIME', role: 'LONG_TERM', base_currency: 'USD',
    positions: [{ security_id: 'SYN', sub_portfolio: 'Core' }] });
  assert.deepEqual([out.fx_rates, out.prices, out.securities], [[], [], []]);
  assert.equal(out.observed_at, undefined, 'missing dates stay missing so Python rejects them');
  const cap = capacityForSave({ ...emptyCapacity(), horizon_years: '7', monthly_income_thb: '0012.50' });
  assert.equal(cap.horizon_years, 7);
  assert.equal(cap.monthly_income_thb, '0012.50', 'amount strings pass through unchanged');
  assert.equal(capacityForSave({ ...emptyCapacity(), horizon_years: '7.5' }).horizon_years, '7.5');
});

test('Python error codes the wizard can hit have Thai messages; unknown codes keep the raw code', () => {
  const po = read('../src/acash/ppds/private_observation.py');
  const codes = new Set([...po.matchAll(/DataContractError\(f?"(PRIVATE_[A-Z_]+)/g)].map((m) => m[1]));
  const parserCodes = [...codes].filter((c) => !/NAV|CONSERVATION|REPORT_CURRENCY_NOT_BUILT|DUPLICATE_SNAPSHOT|LOCATION|OBSERVATION_NOT_AUTHORIZED|NOT_A_MAPPING|SCHEMA_MISMATCH|DATA_CLASS|EVIDENCE_SOURCE|REPORT_CURRENCIES|PUBLISHED_AFTER|CLASSIFICATION_INVALID|WITHOUT_METHODOLOGY|INSTRUMENT_TYPE|EXCHANGE_MIC|ISIN|FIGI|IDENTITY_CURRENCY|NONFINITE/.test(c));
  for (const code of parserCodes) assert.ok(MESSAGES_TH[code], `${code} has no Thai message`);
  for (const code of ['PRIVATE_FX_RATE_MISSING', 'PRIVATE_DUPLICATE_CASH_LINE', 'PRIVATE_POSITION_EVIDENCE_MISSING',
    'POSSIBLE_DUPLICATE_CASH_ACROSS_ACCOUNTS', 'REVISION_CONFLICT', 'AUTHORING_AUTHORIZATION_REQUIRED', 'SESSION_EXPIRED']) {
    assert.match(MESSAGES_TH[code], /[\u0E00-\u0E7F]/, `${code} is Thai`);
  }
  assert.equal(messageTh('NEW_CODE_Z'), 'ข้อมูลไม่ผ่านการตรวจ (NEW_CODE_Z)');
});

test('wizard sources do not compute, persist, log or download private figures', () => {
  const sources = ['src/components/portfolio/SetupWizard.tsx', 'src/services/privateInput.ts'].map(read);
  for (const src of sources) {
    for (const banned of ['toFixed(', 'toLocaleString(', 'parseFloat(', 'localStorage', 'sessionStorage', 'indexedDB', 'console.',
      'navigator.sendBeacon', 'createObjectURL', 'download=', 'eval(', 'new Function']) {
      assert.ok(!src.includes(banned), `${banned} must not appear`);
    }
    assert.ok(!/fetch\(/.test(src), 'requests go through upiRepository only');
  }
  const wizard = sources[0];
  assert.match(wizard, /ACASH ได้รับอนุญาตให้อ่านและวิเคราะห์ข้อมูลพอร์ตส่วนตัวในเครื่องนี้เท่านั้น ไม่มีสิทธิ์ซื้อขายหรือโอนเงิน/);
  assert.match(wizard, /confirm_replace: true/);
  assert.match(wizard, /callInput\('PUT', 'inputs', \{\s*snapshot: compact\(snap\), capacity: capacityForSave\(cap\), base_revisions: revisions/);
  assert.doesNotMatch(wizard, /'PUT', kind/);
  assert.match(wizard, /disabled=\{busy \|\| !canSave \|\| !confirm\}/);
  const repo = read('src/services/upiRepository.ts');
  assert.match(repo, /INPUT_ENDPOINT \+ route/);
  assert.match(repo, /credentials: 'include'/);
});
