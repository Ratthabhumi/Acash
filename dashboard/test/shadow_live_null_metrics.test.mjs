import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import esbuild from 'esbuild';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

/**
 * Regression: Shadow Tournament production crash — "Cannot read properties of
 * null (reading 'toFixed')" on live runtime payloads.
 *
 * The backend serializes UNASSIGNED slots with exposurePct / riskUtilizationPct /
 * durationSeconds = null (meanings: N/A). The live repository casts JSON to
 * TournamentState with zero runtime validation, so these nulls reach the React
 * renderer untouched. Before the fix, SlotCard called `.toFixed()` / formatDuration()
 * directly on those fields and crashed.
 *
 * This test bundles the CURRENT page source at test time and renders the real
 * SlotCard component against a LIVE-SHAPED payload (Slot A RUNNING with numeric
 * metrics; Slots B/C UNASSIGNED with the three N/A fields null) — mirroring the
 * exact bytes the browser receives from `resp.json()`.
 */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const entry = path.resolve(__dirname, '../src/pages/ShadowTournamentPage.tsx');

let outFile = '';
let SlotCard;

test('bundle current ShadowTournamentPage.tsx at test time', async () => {
  const bundle = await esbuild.build({
    entryPoints: [entry],
    bundle: true,
    format: 'esm',
    platform: 'node',
    jsx: 'automatic',
    jsxDev: false,
    external: ['react', 'react-dom', 'react/jsx-runtime', 'react-dom/*', 'lucide-react'],
    logLevel: 'silent',
    write: false,
  });

  const code = bundle.outputFiles[0].text;
  // The bundle must come from the freshly transpiled page (not a stale artifact).
  assert.match(code, /riskUtilizationPct !== null/, 'bundle must contain the null guard');
  assert.match(code, /exposurePct !== null/, 'bundle must contain the exposure null guard');
  assert.match(code, /durationSeconds !== null/, 'bundle must contain the duration null guard');

  const outDir = path.resolve(__dirname, '..', 'node_modules', '.acash-shadow-test');
  fs.mkdirSync(outDir, { recursive: true });
  outFile = path.join(outDir, 'ShadowTournamentPage.mjs');
  fs.writeFileSync(outFile, code);
  ({ SlotCard } = await import(pathToFileURL(outFile).href));

  assert.equal(typeof SlotCard, 'function', 'SlotCard must be exported by the page module');
});

test.after(() => {
  if (outFile) {
    try {
      fs.rmSync(path.dirname(outFile), { recursive: true, force: true });
    } catch {
      // best-effort cleanup
    }
  }
});

const acashSha = 'bb6d49c41fefef42c288ebdfce597572433423f9';

function runningSlot(slotId) {
  return {
    slotId,
    strategyId: 'INFRA-TEST-MOMENTUM-SYNTHETIC-001',
    strategyName: 'Infrastructure Test Strategy',
    strategyVersion: '1.0.0',
    governanceLabel: 'INFRASTRUCTURE_TEST_STRATEGY_ONLY',
    status: 'RUNNING',
    sessionId: `SHADOW-LIVE-${slotId}-RUNNING`,
    configHash: 'a'.repeat(64),
    acashCommitSha: acashSha,
    haltReason: null,
    lastBarUtc: '2026-09-14T12:00:00Z',
    openPositions: [],
    recentFills: [],
    equityCurve: [],
    metrics: {
      initialNavUsd: 1000.0,
      currentNavUsd: 1012.5,
      pnlUsd: 12.5,
      pnlPct: 1.25,
      realizedPnlUsd: 12.5,
      unrealizedPnlUsd: 0.0,
      maxDrawdownPct: 1.1,
      currentDrawdownPct: 0.4,
      exposurePct: 80.25,
      riskUtilizationPct: 42.5,
      openPositionCount: 1,
      simulatedOrderCount: 3,
      simulatedFillCount: 2,
      winCount: 1,
      lossCount: 1,
      winRatePct: 50.0,
      signalCount: 4,
      lastSignalUtc: '2026-09-14T12:00:00Z',
      lastFillUtc: '2026-09-14T12:00:00Z',
      durationSeconds: 3661,
    },
  };
}

function unassignedSlot(slotId) {
  return {
    slotId,
    strategyId: 'UNASSIGNED',
    strategyName: 'UNASSIGNED',
    strategyVersion: 'N/A',
    governanceLabel: 'UNASSIGNED_SLOT',
    status: 'UNASSIGNED',
    sessionId: `SHADOW-LIVE-${slotId}-UNASSIGNED`,
    configHash: '0'.repeat(64),
    acashCommitSha: acashSha,
    haltReason: null,
    lastBarUtc: null,
    openPositions: [],
    recentFills: [],
    equityCurve: [],
    metrics: {
      initialNavUsd: 1000.0,
      currentNavUsd: 1000.0,
      pnlUsd: 0.0,
      pnlPct: 0.0,
      realizedPnlUsd: 0.0,
      unrealizedPnlUsd: 0.0,
      maxDrawdownPct: 0.0,
      currentDrawdownPct: 0.0,
      exposurePct: null,
      riskUtilizationPct: null,
      openPositionCount: 0,
      simulatedOrderCount: 0,
      simulatedFillCount: 0,
      winCount: 0,
      lossCount: 0,
      winRatePct: null,
      signalCount: 0,
      lastSignalUtc: null,
      lastFillUtc: null,
      durationSeconds: null,
    },
  };
}

/**
 * LIVE-SHAPED TournamentState: Slot A RUNNING (numeric metrics),
 * Slots B & C UNASSIGNED with the three N/A fields null.
 * Round-trips through JSON to reproduce the exact payload shape the browser
 * receives from the live endpoint (`resp.json()`) before casting.
 */
function buildLiveShapedTournament() {
  const tournament = {
    global: {
      tournamentId: 'SHADOW-LIVE-RUNNING',
      label: 'Shadow Alpha Tournament',
      governanceBadge: 'SHADOW / SIMULATED ONLY',
      canonicalCapitalUsd: 0.0,
      realOrderCount: 0,
      noRealOrders: true,
      feedHealth: 'HEALTHY',
      runtimeUptimeSeconds: 3660,
      acashCommitSha: acashSha,
      deploymentImageId: 'acash:shadow-tournament-bb6d49c',
      tournamentStartUtc: '2026-09-14T10:59:00Z',
      lastDataTimestampUtc: '2026-09-14T12:00:00Z',
      lastSuccessfulUpdateUtc: '2026-09-14T12:00:01Z',
      overallStatus: 'RUNNING',
      haltReason: null,
    },
    slots: {
      A: runningSlot('A'),
      B: unassignedSlot('B'),
      C: unassignedSlot('C'),
    },
    leaderboard: {
      rankedSlots: [
        {
          rank: 1,
          slotId: 'A',
          strategyName: 'Infrastructure Test Strategy',
          pnlPct: 1.25,
          maxDrawdownPct: 1.1,
          navUsd: 1012.5,
        },
      ],
      comparisonAvailability: 'INSUFFICIENT_SAMPLE',
      comparisonNote:
        'Tournament awaiting sufficient fill sample across active strategies.',
    },
    _meta: {
      fetchedAtUtc: '2026-09-14T12:00:01Z',
      dataSource: 'LIVE_API',
      isMockData: false,
      mockNotice: '',
    },
  };

  // Mirror the live path: JSON over the wire -> JSON.parse -> cast to TournamentState.
  const raw = JSON.stringify(tournament);
  assert.match(raw, /"exposurePct":null/, 'live payload must carry exposurePct:null for UNASSIGNED');
  assert.match(raw, /"riskUtilizationPct":null/, 'live payload must carry riskUtilizationPct:null for UNASSIGNED');
  assert.match(raw, /"durationSeconds":null/, 'live payload must carry durationSeconds:null for UNASSIGNED');
  assert.match(raw, /"exposurePct":80\.25/, 'live payload must carry numeric exposurePct for RUNNING');
  return JSON.parse(raw);
}

function renderSlotCard(slot, rank) {
  return renderToStaticMarkup(React.createElement(SlotCard, { slot, rank }));
}

test('SlotCard renders RUNNING slot with numeric metrics unchanged', () => {
  const live = buildLiveShapedTournament();
  const markup = renderSlotCard(live.slots.A, 1);

  assert.doesNotThrow(() => renderSlotCard(live.slots.A, 1), 'RUNNING slot must render without throwing');

  // Numeric behavior must not change: Risk Util. and Exposure keep their toFixed(1) formatting.
  assert.match(markup, /42\.5%/g, 'RUNNING slot must render Risk Util. 42.5%');
  assert.match(markup, /80\.3%/g, 'RUNNING slot must render Exposure 80.3% (toFixed(1))');
  assert.match(markup, /1h 1m/, 'RUNNING slot must render Runtime via formatDuration');
  assert.match(markup, /RUNNING/, 'RUNNING slot must render RUNNING status');
});

test('SlotCard renders UNASSIGNED slots with em dash for N/A metrics — no throw', () => {
  const live = buildLiveShapedTournament();

  for (const id of ['B', 'C']) {
    assert.doesNotThrow(
      () => renderSlotCard(live.slots[id], null),
      `UNASSIGNED slot ${id} with null metrics must render without throwing`
    );

    const markup = renderSlotCard(live.slots[id], null);

    assert.match(markup, /UNASSIGNED — Awaiting Human Strategy Selection/, `slot ${id} must render UNASSIGNED`);
    assert.match(markup, /UNASSIGNED/, `slot ${id} must render UNASSIGNED badge`);

    // N/A metrics must render the em dash — never "null%", "NaN%", or a crash.
    assert.match(markup, /Risk Util\.<\/span><span[^>]*>—<\/span>/, `slot ${id} Risk Util. must render em dash`);
    assert.match(markup, /Exposure<\/span><span[^>]*>—<\/span>/, `slot ${id} Exposure must render em dash`);
    assert.match(markup, /Runtime<\/span><span[^>]*>—<\/span>/, `slot ${id} Runtime must render em dash`);
    assert.doesNotMatch(markup, /null|NaN/, `slot ${id} must not render null or NaN`);
  }
});

test('Mixed grid of all three slots renders without throwing (full live shape)', () => {
  const live = buildLiveShapedTournament();
  const slots = ['A', 'B', 'C'];

  assert.doesNotThrow(() => {
    for (const id of slots) {
      const rank = id === 'A' ? 1 : null;
      renderSlotCard(live.slots[id], rank);
    }
  }, 'rendering Slot A/B/C together must not throw');
});