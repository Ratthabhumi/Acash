/**
 * CORE-001 executable fail-closed tests.
 *
 * Compiles the real TypeScript repository (tsc, no bundler) and exercises
 * getState() with a stubbed global fetch:
 * - HTTP 404 alone -> EMPTY_PRE_S1
 * - every other failure class -> EVIDENCE_INVALID_OR_BLOCKED
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dashboardRoot = path.resolve(__dirname, '..');
const outDir = path.resolve(__dirname, './.tmp-core001-failclosed');

function compileOnce() {
  const entry = path.join(outDir, 'services', 'core001Repository.js');
  if (fs.existsSync(entry)) return entry;
  fs.mkdirSync(outDir, { recursive: true });
  const tsc = path.resolve(dashboardRoot, 'node_modules', 'typescript', 'bin', 'tsc');
  execFileSync(process.execPath, [
    tsc,
    'src/services/core001MockData.ts',
    'src/services/core001Repository.ts',
    'src/types/core001.ts',
    '--outDir', outDir,
    '--module', 'commonjs',
    '--target', 'es2020',
    '--strict', 'false',
    '--esModuleInterop', 'true',
    '--skipLibCheck', 'true',
    '--rootDir', 'src',
  ], { cwd: dashboardRoot, stdio: 'pipe' });
  // The dashboard package is "type": "module"; force CommonJS scope here
  // so the compiled repository loads via createRequire.
  fs.writeFileSync(path.join(outDir, 'package.json'), '{"type":"commonjs"}\n');
  return entry;
}

const entry = compileOnce();
const require = createRequire(__filename);
const repoModule = require(entry);

const realFetch = globalThis.fetch;

function stubFetch(handler) {
  globalThis.fetch = handler;
}

function restoreFetch() {
  globalThis.fetch = realFetch;
}

function okJson(payload) {
  return { ok: true, status: 200, json: async () => payload };
}

test('404 alone maps to EMPTY_PRE_S1', async () => {
  stubFetch(async () => ({ ok: false, status: 404 }));
  try {
    const res = await repoModule.core001Repository.getState();
    assert.equal(res.ok, true);
    assert.equal(res.data.dataSource, 'EMPTY_PRE_S1');
    assert.equal(res.data.governance.stage, 'PRE-S1');
    assert.equal(res.data.progress.observed_sessions, 0);
  } finally {
    restoreFetch();
  }
});

test('HTTP 500 maps to blocked', async () => {
  stubFetch(async () => ({ ok: false, status: 500 }));
  try {
    const res = await repoModule.core001Repository.getState();
    assert.equal(res.ok, false);
    assert.equal(res.data.evidence.status, 'EVIDENCE_INVALID_OR_BLOCKED');
    assert.equal(res.data.governance.paper_authorized, false);
    assert.equal(res.data.governance.live_authorized, false);
    assert.equal(res.data.governance.real_capital_authority_usd, '0.00');
    assert.equal(res.data.governance.no_real_orders, true);
  } finally {
    restoreFetch();
  }
});

test('unreachable snapshot maps to blocked, not PRE-S1', async () => {
  stubFetch(async () => { throw new Error('socket hang up'); });
  try {
    const res = await repoModule.core001Repository.getState();
    assert.equal(res.ok, false);
    assert.equal(res.data.evidence.status, 'EVIDENCE_INVALID_OR_BLOCKED');
    assert.match(res.data.evidence.reason, /SNAPSHOT_UNREACHABLE/);
  } finally {
    restoreFetch();
  }
});

test('malformed JSON maps to blocked', async () => {
  stubFetch(async () => ({
    ok: true, status: 200, json: async () => { throw new SyntaxError('bad json'); },
  }));
  try {
    const res = await repoModule.core001Repository.getState();
    assert.equal(res.ok, false);
    assert.equal(res.data.evidence.reason, 'SNAPSHOT_MALFORMED_JSON');
  } finally {
    restoreFetch();
  }
});

test('wrong document maps to blocked', async () => {
  stubFetch(async () => okJson({ document: 'SOMETHING_ELSE', view: {} }));
  try {
    const res = await repoModule.core001Repository.getState();
    assert.equal(res.ok, false);
    assert.match(res.data.evidence.reason, /UNKNOWN_DOCUMENT/);
  } finally {
    restoreFetch();
  }
});

test('authority violation maps to blocked', async () => {
  const fixture = JSON.parse(fs.readFileSync(
    path.resolve(__dirname, './fixtures/core001-snapshot-one-obs.json'), 'utf-8'));
  fixture.view.governance.paper_authorized = true;
  stubFetch(async () => okJson(fixture));
  try {
    const res = await repoModule.core001Repository.getState();
    assert.equal(res.ok, false);
    assert.match(res.data.evidence.reason, /AUTHORITY_VIOLATION/);
  } finally {
    restoreFetch();
  }
});

test('capital violation maps to blocked', async () => {
  const fixture = JSON.parse(fs.readFileSync(
    path.resolve(__dirname, './fixtures/core001-snapshot-one-obs.json'), 'utf-8'));
  fixture.view.governance.real_capital_authority_usd = '1000.00';
  stubFetch(async () => okJson(fixture));
  try {
    const res = await repoModule.core001Repository.getState();
    assert.equal(res.ok, false);
    assert.match(res.data.evidence.reason, /CAPITAL_VIOLATION/);
  } finally {
    restoreFetch();
  }
});

test('valid snapshot still maps to SNAPSHOT state', async () => {
  const fixture = JSON.parse(fs.readFileSync(
    path.resolve(__dirname, './fixtures/core001-snapshot-one-obs.json'), 'utf-8'));
  stubFetch(async () => okJson(fixture));
  try {
    const res = await repoModule.core001Repository.getState();
    assert.equal(res.ok, true);
    assert.equal(res.data.dataSource, 'SNAPSHOT');
    assert.equal(res.data.governance.stage, 'S1_OPERATIONAL_SANITY_IN_PROGRESS');
  } finally {
    restoreFetch();
  }
});
