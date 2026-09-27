import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const typesPath = path.resolve(__dirname, '../src/types/core001.ts');
const typesContent = fs.readFileSync(typesPath, 'utf-8');
const repoPath = path.resolve(__dirname, '../src/services/core001Repository.ts');
const repoContent = fs.readFileSync(repoPath, 'utf-8');
const pagePath = path.resolve(__dirname, '../src/pages/Core001Page.tsx');
const pageContent = fs.readFileSync(pagePath, 'utf-8');
const fixturePath = path.resolve(__dirname, './fixtures/core001-snapshot-one-obs.json');
const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf-8'));

test('CORE-001 Contract: Governance constants mirror ratified framework', () => {
  assert.match(typesContent, /S1_REQUIRED:\s*20/, 'S1 = 20');
  assert.match(typesContent, /S2_REQUIRED:\s*60/, 'S2 = 60');
  assert.match(typesContent, /LONG_HORIZON_REQUIRED:\s*504/, 'Long horizon = 504');
  assert.match(typesContent, /S2_MDD_LIMIT:\s*0\.25/, 'MDD limit 0.25');
  assert.match(typesContent, /S2_CUMRET_FLOOR:\s*-0\.2/, 'Cumret floor -0.20');
  assert.match(typesContent, /S2_DAILY_FLOOR:\s*-0\.1/, 'Daily floor -0.10');
  assert.match(typesContent, /CANONICAL_CAPITAL_USD:\s*0(\.0)?/, 'Capital structurally 0');
  assert.match(typesContent, /NO_REAL_ORDERS:\s*true/, 'NO_REAL_ORDERS structurally true');
  assert.match(typesContent, /PAPER_AUTHORIZED:\s*false/, 'Paper structurally unauthorized');
  assert.match(typesContent, /LIVE_AUTHORIZED:\s*false/, 'Live structurally unauthorized');
});

test('CORE-001 Contract: Read-only repository and page (zero mutation)', () => {
  assert.doesNotMatch(repoContent, /post\(|put\(|delete\(|patch\(/i, 'Repository must not implement mutation HTTP methods');
  assert.match(repoContent, /getState\(\)/, 'Repository must expose getState()');
  assert.match(repoContent, /subscribe\(/, 'Repository must expose subscribe()');
  assert.doesNotMatch(pageContent, /<button[^>]*>\s*(?:Buy|Sell|Run Observation|Start Paper|Authorize|Backfill|Start Live)\s*<\//i, 'Page must not contain mutation buttons');
  assert.ok(pageContent.includes('READ-ONLY OBSERVABILITY'), 'Page must declare read-only posture');
  assert.ok(pageContent.includes('NO_REAL_ORDERS') || pageContent.includes('NO\u005fREAL\u005fORDERS'), 'Page must show NO_REAL_ORDERS');
});

test('CORE-001 Fixture: one sealed observation derives honestly', () => {
  assert.equal(fixture.document, 'CORE_001_DASHBOARD_SNAPSHOT_V1');
  assert.equal(fixture.network_requests_issued, 0);
  assert.equal(fixture.read_only_derivation, true);
  const view = fixture.view;
  assert.equal(view.identity.hypothesis_id, 'HYP_011');
  assert.equal(view.governance.stage, 'S1_OPERATIONAL_SANITY_IN_PROGRESS');
  assert.equal(view.governance.paper_eligible, false);
  assert.equal(view.governance.paper_authorized, false);
  assert.equal(view.governance.live_authorized, false);
  assert.equal(view.governance.real_capital_authority_usd, '0.00');
  assert.equal(view.progress.observed_sessions, 1);
  assert.equal(view.evidence.latest_observation_ordinal, 1);
  assert.equal(view.evidence.latest_observation_session, '2026-09-28');
  assert.equal(view.s2.evaluation_state, 'INSUFFICIENT_OBSERVATIONS');
  assert.equal(view.equity_series.length, 1);
  assert.equal(view.runtime.timer_status, 'UNAVAILABLE_FROM_DASHBOARD');
  assert.equal(view.incident.category, 'NONE');
});

test('CORE-001 Fixture: snapshot carries chain linkage', () => {
  const view = fixture.view;
  assert.ok(typeof view.evidence.latest_artifact_sha256 === 'string' && view.evidence.latest_artifact_sha256.length === 64, 'Latest SHA present');
  assert.equal(view.evidence.previous_artifact_sha256, null);
  assert.equal(view.evidence.state_chain_health, 'READY');
});

test('CORE-001 Parser: rejects authority violations and wrong documents', () => {
  // Static enforcement: parser must check hypothesis, paper/live, capital.
  const mockContent = fs.readFileSync(path.resolve(__dirname, '../src/services/core001MockData.ts'), 'utf-8');
  assert.match(mockContent, /CORE001_SNAPSHOT_HYPOTHESIS_MISMATCH/, 'Parser must enforce hypothesis binding');
  assert.match(mockContent, /CORE001_SNAPSHOT_AUTHORITY_VIOLATION/, 'Parser must enforce paper/live false');
  assert.match(mockContent, /CORE001_SNAPSHOT_CAPITAL_VIOLATION/, 'Parser must enforce $0 capital');
  assert.match(mockContent, /EMPTY_PRE_S1/, 'Fallback must be explicit EMPTY PRE-S1');
});
