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

test('Shadow Alpha Tournament Contract: Mobile Responsiveness and Fail-Closed Indicators', () => {
  // Page must have responsive grid classes (grid-cols-1 for mobile, md:grid-cols-3 for desktop)
  assert.match(pageContent, /grid-cols-1 md:grid-cols-3/, 'Slot cards must adapt from 1 col on mobile to 3 cols on desktop');

  // Page must indicate mock/stale data status
  assert.ok(pageContent.includes('MOCK DEMO DATA'), 'Mock data warning banner must be implemented');
});
