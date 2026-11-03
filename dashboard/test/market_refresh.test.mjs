import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MARKET_ENDPOINT, MARKET_TH, PRICE_PROVIDERS, PROVIDER_INFO, marketTh, refreshBlocker } from '../src/services/marketRefresh.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf-8');
const pyTuple = (src, name) => [...src.match(new RegExp(`${name} = (?:[A-Z_]+ \\+ )?\\(([^)]*)\\)`))[1].matchAll(/"([A-Z_]+)"/g)].map((m) => m[1]);

test('provider ids and activation statuses mirror the Python authority', () => {
  const ma = read('../src/acash/invest/market_authority.py');
  assert.deepEqual(new Set(Object.keys(PROVIDER_INFO)), new Set([...pyTuple(ma, 'ADAPTED_PROVIDERS'), ...pyTuple(ma, 'KNOWN_PROVIDERS')]));
  for (const s of pyTuple(ma, 'STATUSES').filter((s) => s !== 'RATE_LIMITED' && s !== 'SERVICE_UNAVAILABLE')) {
    assert.ok(MARKET_TH[s], `missing Thai text for ${s}`);
  }
  assert.equal(MARKET_ENDPOINT, 'http://127.0.0.1:8765/api/upi/market/');
});

test('refresh stays disabled unless ODR-004 is ratified and a price provider is READY', () => {
  const ok = { status: 'OK', odr_004: 'RATIFIED', providers: [{ provider_id: 'ALPACA_BASIC', status: 'READY' }] };
  assert.equal(refreshBlocker(ok), null);
  assert.equal(refreshBlocker(null), 'SERVICE_UNAVAILABLE');
  assert.equal(refreshBlocker({ ...ok, odr_004: 'PROPOSED_NOT_RATIFIED' }), 'MARKET_DATA_AUTHORIZATION_REQUIRED');
  assert.equal(refreshBlocker({ ...ok, providers: [{ provider_id: 'BOT_REFERENCE_FX', status: 'READY' }] }), 'NO_READY_PRICE_PROVIDER');
  assert.equal(refreshBlocker({ ...ok, providers: [{ provider_id: 'ALPACA_BASIC', status: 'CREDENTIALS_REQUIRED' }] }), 'NO_READY_PRICE_PROVIDER');
  assert.deepEqual([...PRICE_PROVIDERS], ['ALPACA_BASIC', 'ALPACA_HISTORICAL', 'MARKETDATA_APP_FREE', 'MASSIVE_BASIC']);
});

test('partial valuation is never described as the whole portfolio and the client holds no secrets', () => {
  assert.match(marketTh('PARTIAL_INDICATIVE_VALUATION'), /ไม่ใช่มูลค่าพอร์ตทั้งหมด/);
  assert.match(marketTh('PRICES_ONLY_PPDS_CONSOLIDATION_FX_MISSING'), /คงรายงานเดิม/);
  const src = read('src/services/marketRefresh.ts') + read('src/components/portfolio/MarketRefreshPanel.tsx');
  for (const banned of ['APCA-API', 'Authorization', 'localStorage', 'sessionStorage', 'api_key', 'secret']) {
    assert.ok(!src.includes(banned), banned);
  }
});
