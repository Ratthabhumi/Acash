import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { AUTHORED_EVENTS, EVENT_FIELDS, TXN_ENDPOINT, newTransactionId, txnTh } from '../src/services/transactions.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf-8');

test('authored events and routes mirror the Python transaction service', () => {
  const py = read('../src/acash/dashboard_api/private_transactions.py');
  const events = [...py.match(/AUTHORED_EVENTS = \(([^)]*)\)/)[1].matchAll(/"([A-Z_]+)"/g)].map((m) => m[1]);
  assert.deepEqual([...AUTHORED_EVENTS], events);
  assert.equal(TXN_ENDPOINT, 'http://127.0.0.1:8765/api/upi/transactions/');
  for (const e of AUTHORED_EVENTS) assert.ok(EVENT_FIELDS[e].includes('net_cash'));
});

test('client transaction ids satisfy the server pattern and are not reused', () => {
  const ids = new Set(Array.from({ length: 50 }, () => newTransactionId()));
  assert.equal(ids.size, 50);
  for (const id of ids) assert.match(id, /^TX_[A-Z]{8,28}$/);
  assert.match(txnTh('TXN_BEFORE_BASELINE_CUTOFF'), /ไม่นับซ้ำ/);
});

test('journal client never computes money, stores credentials or reaches a broker', () => {
  const src = read('src/services/transactions.ts') + read('src/components/portfolio/TransactionJournalPanel.tsx');
  for (const banned of ['localStorage', 'sessionStorage', 'api_key', 'secret', 'Authorization', 'parseFloat', 'Number(', 'toFixed']) {
    assert.ok(!src.includes(banned), banned);
  }
  assert.ok(!/\borders?\b/i.test(src), 'broker order wording');
  assert.ok(!/[\w)\]]\s[*/]\s[\w(]/.test(src.replace(/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, '')), 'arithmetic in journal client');
});