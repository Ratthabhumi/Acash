import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const typesPath = path.resolve(__dirname, '../src/types/shadow.ts');
const typesContent = fs.readFileSync(typesPath, 'utf-8');

const mockPath = path.resolve(__dirname, '../src/services/shadowMockData.ts');
const mockContent = fs.readFileSync(mockPath, 'utf-8');

const repoPath = path.resolve(__dirname, '../src/services/shadowRepository.ts');
const repoContent = fs.readFileSync(repoPath, 'utf-8');

const pagePath = path.resolve(__dirname, '../src/pages/ShadowTournamentPage.tsx');
const pageContent = fs.readFileSync(pagePath, 'utf-8');

const distHtmlPath = path.resolve(__dirname, '../dist/index.html');
const distHtmlContent = fs.existsSync(distHtmlPath) ? fs.readFileSync(distHtmlPath, 'utf-8') : '';

test('Shadow Alpha Tournament Contract: Zero Real Orders and Simulated Only', () => {
  // 1. Mandatory governance constants in types
  assert.match(typesContent, /CANONICAL_CAPITAL_USD:\s*0\.00/, 'Canonical capital must be structurally 0.00');
  assert.match(typesContent, /NO_REAL_ORDERS:\s*true/, 'NO_REAL_ORDERS must be structurally true');
  assert.match(typesContent, /MODE:\s*'SHADOW_SIMULATED_RESEARCH_INFRA_ONLY'/, 'Governance mode must be SHADOW_SIMULATED_RESEARCH_INFRA_ONLY');

  // 2. Mock data enforcement
  assert.match(mockContent, /isMockData:\s*true/, 'Mock data must explicitly set isMockData: true');
  assert.match(mockContent, /canonicalCapitalUsd:\s*SHADOW_GOVERNANCE\.CANONICAL_CAPITAL_USD/, 'Mock data must bind to CANONICAL_CAPITAL_USD');
  assert.match(mockContent, /noRealOrders:\s*SHADOW_GOVERNANCE\.NO_REAL_ORDERS/, 'Mock data must bind to NO_REAL_ORDERS');

  // 3. Page governance banners
  assert.ok(pageContent.includes('CANONICAL CAPITAL = $0.00'), 'Page must conspicuously display canonical capital $0.00');
  assert.ok(pageContent.includes('REAL ORDERS = 0'), 'Page must conspicuously display REAL ORDERS = 0');
  assert.ok(pageContent.includes('SHADOW / SIMULATED ONLY'), 'Page must conspicuously display SHADOW / SIMULATED ONLY');
});

test('Shadow Alpha Tournament Contract: Read-Only Architecture (Zero Mutation)', () => {
  // Page must NOT contain any order placement, buy, sell, start, stop, deploy controls
  assert.doesNotMatch(pageContent, /<button[^>]*>\s*(?:Buy|Sell|Place Order|Submit Order|Deploy|Start Tournament|Execute)\s*<\/button>/i, 'Page must not contain mutation buttons');
  
  // Repository must only expose read-only methods
  assert.doesNotMatch(repoContent, /post\(|put\(|delete\(|patch\(/i, 'Repository must not implement mutation HTTP methods');
  assert.match(repoContent, /getState\(\)/, 'Repository must expose getState()');
  assert.match(repoContent, /subscribe\(/, 'Repository must expose subscribe()');
});

test('Shadow Alpha Tournament Contract: 3 Strategy Slots with Honest Unassigned State', () => {
  // Verify 3 slots are instantiated in mock
  assert.match(mockContent, /A:\s*makeInfraSlot\('A'\)/, 'Slot A must exist');
  assert.match(mockContent, /B:\s*makeInfraSlot\('B'\)/, 'Slot B must exist');
  assert.match(mockContent, /C:\s*makeInfraSlot\('C'\)/, 'Slot C must exist');

  // Verify status is honest about unassigned state (zero alpha candidates exist in repo)
  assert.match(mockContent, /status:\s*'UNASSIGNED'/, 'Slots without approved candidates must be UNASSIGNED');
});

test('Shadow Alpha Tournament Contract: Fail-Closed Production Repository Defaults', () => {
  // 1. Must check VITE_SHADOW_ALLOW_MOCK explicitly
  assert.match(repoContent, /VITE_SHADOW_ALLOW_MOCK === 'true'/, 'Must require explicit dev-only flag VITE_SHADOW_ALLOW_MOCK');

  // 2. Default factory must return LiveShadowRepository when allowMock is false
  assert.match(repoContent, /if \(allowMock\) \{\s*return new MockShadowRepository\(\);\s*\}\s*return new LiveShadowRepository/, 'Must default to LiveShadowRepository and never silently fall back to mock');

  // 3. Live repository must return error state on failure, never mock data
  assert.match(repoContent, /return \{\s*ok:\s*false,\s*data:\s*null,\s*error:/, 'Live repository failure must yield ok: false, data: null');
});

test('Shadow Alpha Tournament Contract: UNASSIGNED N/A Metrics Are Null-Safe', () => {
  // Backend serializes exposurePct / riskUtilizationPct / durationSeconds as null
  // for UNASSIGNED slots. The frontend contract must declare them nullable and the
  // page must guard before calling toFixed / formatDuration. Null means N/A — never
  // faked to zero on the client, and never silently fabricated on the backend.
  assert.match(typesContent, /exposurePct:\s*number \| null/, 'exposurePct must be declared number | null');
  assert.match(typesContent, /riskUtilizationPct:\s*number \| null/, 'riskUtilizationPct must be declared number | null');
  assert.match(typesContent, /durationSeconds:\s*number \| null/, 'durationSeconds must be declared number | null');

  assert.match(
    pageContent,
    /metrics\.riskUtilizationPct !== null \? `\$\{metrics\.riskUtilizationPct\.toFixed\(1\)\}%` : '—'/,
    'Risk Util. must guard null and render em dash'
  );
  assert.match(
    pageContent,
    /metrics\.exposurePct !== null \? `\$\{metrics\.exposurePct\.toFixed\(1\)\}%` : '—'/,
    'Exposure must guard null and render em dash'
  );
  assert.match(
    pageContent,
    /metrics\.durationSeconds !== null \? formatDuration\(metrics\.durationSeconds\) : '—'/,
    'Runtime must guard null and render em dash'
  );
});

test('Shadow Alpha Tournament Contract: Relative Base and Path Routing Compatibility', () => {
  if (distHtmlContent) {
    // Assets must be relative (./assets/...) to support both / and /acash/ path prefixes
    assert.match(distHtmlContent, /src="\.\/assets\//, 'Built scripts must use relative ./assets/ path for path-prefix compatibility');
    assert.match(distHtmlContent, /href="\.\/assets\//, 'Built styles must use relative ./assets/ path for path-prefix compatibility');
  }

  // Verify getShadowApiEndpoint is exported and handles path prefix
  assert.match(repoContent, /export function getShadowApiEndpoint/, 'Must export getShadowApiEndpoint');
  assert.match(repoContent, /pathname\.startsWith\('\/acash'\)/, 'Must detect /acash prefix dynamically from window.location');
  assert.match(repoContent, /\$\{prefix\}\/api\/shadow\/status/, 'Must resolve API to prefix-safe path');
});
