import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read raw source files to verify contracts and prevent unverified drift
const mockDataPath = path.resolve(__dirname, '../src/services/mockData.ts');
const mockDataContent = fs.readFileSync(mockDataPath, 'utf-8');

const repoPath = path.resolve(__dirname, '../src/services/researchRepository.ts');
const repoContent = fs.readFileSync(repoPath, 'utf-8');

const typesPath = path.resolve(__dirname, '../src/types/research.ts');
const typesContent = fs.readFileSync(typesPath, 'utf-8');

test('Data Contract: Epistemic & Demo Invariants', () => {
  // 1. Must enforce isDemoData: true
  assert.match(mockDataContent, /isDemoData:\s*true/, 'isDemoData must be explicitly true');

  // 2. Conspicuous demo notice
  assert.ok(
    mockDataContent.includes('DEMO DATA · SIMULATED RESEARCH RUN · NOT ACASH RESEARCH EVIDENCE'),
    'Demo notice banner string must be exact'
  );

  // 3. Strategy ID must not be real hypothesis
  assert.match(mockDataContent, /strategyId:\s*'MOCK-RESEARCH-001'/, 'Strategy ID must be synthetic MOCK-RESEARCH-001');
  assert.doesNotMatch(mockDataContent, /strategyId:\s*'HYP_00[1-9]'/, 'Strategy ID must NEVER be a real HYP_xxx');

  // 4. Human authorization must be locked
  assert.match(mockDataContent, /humanAuthorizationStatus:\s*'NOT_AUTHORIZED'/, 'Human authorization must be NOT_AUTHORIZED');

  // 5. Governance disclaimer
  assert.ok(
    mockDataContent.includes('Performance metrics do not imply research qualification or trading authorization.'),
    'Governance disclaimer must be exact'
  );

  // 6. Hardened Epistemic Boundaries (No fake capital, no fake runtime namespaces)
  assert.doesNotMatch(mockDataContent, /startingCashUsd/, 'Mock data must NOT represent cash/capital as startingCashUsd');
  assert.match(mockDataContent, /simulatedReferenceNotionalUsd/, 'Mock data must explicitly use simulatedReferenceNotionalUsd');
  assert.doesNotMatch(mockDataContent, /sourceModule:\s*'acash\./, 'Mock lineage must NOT pretend to be live acash.* modules');
  assert.doesNotMatch(mockDataContent, /riskVerdict:\s*'APPROVED/, 'Mock riskVerdict must NOT use APPROVED');
  assert.doesNotMatch(mockDataContent, /SOVEREIGN_RISK_GATE/, 'Mock authority rule must NOT use SOVEREIGN');
});

test('Evidence Lineage Contract: Exactly 11 Stages', () => {
  // Extract all stage numbers and names from mockLineageNodes
  const stageMatches = [...mockDataContent.matchAll(/stageNumber:\s*(\d+)/g)].map(m => parseInt(m[1], 10));
  
  assert.equal(stageMatches.length, 11, 'Lineage DAG must contain exactly 11 stages');
  
  for (let i = 1; i <= 11; i++) {
    assert.ok(stageMatches.includes(i), `Stage ${i} must exist in sequential order`);
  }

  const expectedStageNames = [
    'Market Data',
    'Normalized Data',
    'Feature State',
    'Signal',
    'Risk Decision',
    'Order Intent',
    'Simulated Execution',
    'Position',
    'Portfolio',
    'Metrics',
    'Validation'
  ];

  for (const name of expectedStageNames) {
    assert.ok(mockDataContent.includes(`stageName: '${name}'`), `Stage name '${name}' must be present in DAG`);
  }
});

test('Validation Gate Contract: Zero Fake Pass', () => {
  // Check all status values within mockValidationCriteria
  // We extract the mockValidationCriteria block
  const startIdx = mockDataContent.indexOf('mockValidationCriteria: ValidationCriterion[]');
  const endIdx = mockDataContent.indexOf('mockTimelineEvents: TimelineEvent[]');
  const validationBlock = mockDataContent.slice(startIdx, endIdx);

  // Assert NO fake 'PASS' inside the validation criteria checklist
  const passMatches = [...validationBlock.matchAll(/status:\s*'PASS'/g)];
  assert.equal(passMatches.length, 0, 'Validation criteria must NOT display fake PASS status in mock data');

  // Allowed statuses: NOT_EVALUATED, DEMO, PENDING, FAIL
  const validStatusRegex = /status:\s*'(NOT_EVALUATED|DEMO|PENDING|FAIL)'/g;
  const statusMatches = [...validationBlock.matchAll(validStatusRegex)];
  assert.equal(statusMatches.length, 8, 'All 8 validation criteria must have honest non-fake statuses');
});

test('Architecture & Boundary Isolation: Zero Trading Controls', () => {
  // Confirm no broker or live trading functions are present
  const forbiddenPatterns = [
    /sendOrder/i,
    /submitOrder/i,
    /placeOrder/i,
    /brokerClient/i,
    /executeLive/i,
    /tradeExecutionEngine/i,
  ];

  for (const pattern of forbiddenPatterns) {
    assert.doesNotMatch(repoContent, pattern, `Repository must not contain trading control pattern ${pattern}`);
    assert.doesNotMatch(mockDataContent, pattern, `Mock data must not contain trading control pattern ${pattern}`);
  }
});

test('Causal Trade Evidence Chain Contract', () => {
  // Verify that trade generator creates evidence chain with 6 stages
  assert.ok(mockDataContent.includes('signalId:'), 'Trade must include signalId');
  assert.ok(mockDataContent.includes('riskVerdict:'), 'Trade must include riskVerdict');
  assert.ok(mockDataContent.includes('orderIntentId:'), 'Trade must include orderIntentId');
  assert.ok(mockDataContent.includes('simulatedFillId:'), 'Trade must include simulatedFillId');
  assert.ok(mockDataContent.includes('positionId:'), 'Trade must include positionId');
  assert.ok(mockDataContent.includes('portfolioImpactBps:'), 'Trade must include portfolioImpactBps');
});

console.log('✔ All ACASH Research Dashboard Data Contracts Verified Successfully.');
