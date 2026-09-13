/**
 * ACASH Shadow Alpha Tournament — Mock Data Service
 *
 * GOVERNANCE:
 * - This is MOCK / DEMO data only. No real runtime is connected.
 * - isMockData: true is mandatory — never remove this flag.
 * - The mock shows the HALTED + UNASSIGNED state to be honest
 *   about the current operational status.
 *
 * SHADOW / SIMULATED ONLY — NOT Paper — NOT Live — NOT HYP_003
 * CANONICAL CAPITAL = $0.00 | REAL ORDERS = 0
 */

import {
  TournamentState,
  StrategySlot,
  SlotId,
  SHADOW_GOVERNANCE,
} from '../types/shadow';

const NOW_UTC = new Date().toISOString();
const BASE_COMMIT = '638388e38f721b49cab2621532b04757d6d85586';

/**
 * Produces a single unassigned/infrastructure-test slot record.
 * The mock honestly reflects that zero alpha candidates exist.
 */
function makeInfraSlot(slotId: SlotId): StrategySlot {
  const isInfra = true; // only InfrastructureTestStrategy exists
  return {
    slotId,
    strategyId: isInfra ? 'INFRA-TEST-MOMENTUM-SYNTHETIC-001' : 'UNASSIGNED',
    strategyName: isInfra
      ? 'Infrastructure Test Strategy'
      : 'UNASSIGNED — Awaiting Human Strategy Selection',
    strategyVersion: isInfra ? '1.0.0' : 'N/A',
    governanceLabel: 'INFRASTRUCTURE_TEST_STRATEGY_ONLY',
    status: 'UNASSIGNED',
    sessionId: `SHADOW-MOCK-${slotId}-NOT-STARTED`,
    configHash: '0'.repeat(64),
    acashCommitSha: BASE_COMMIT,
    haltReason: null,
    lastBarUtc: null,
    openPositions: [],
    recentFills: [],
    equityCurve: [],
    metrics: {
      initialNavUsd: 1000.00,
      currentNavUsd: 1000.00,
      pnlUsd: 0.00,
      pnlPct: 0.00,
      realizedPnlUsd: 0.00,
      unrealizedPnlUsd: 0.00,
      maxDrawdownPct: 0.00,
      currentDrawdownPct: 0.00,
      exposurePct: 0.00,
      riskUtilizationPct: 0.00,
      openPositionCount: 0,
      simulatedOrderCount: 0,
      simulatedFillCount: 0,
      winCount: 0,
      lossCount: 0,
      winRatePct: null,
      signalCount: 0,
      lastSignalUtc: null,
      lastFillUtc: null,
      durationSeconds: 0,
    },
  };
}

export const mockTournamentState: TournamentState = {
  global: {
    tournamentId: 'SHADOW-MOCK-NOT-STARTED',
    label: 'Shadow Alpha Tournament',
    governanceBadge: SHADOW_GOVERNANCE.BADGE,
    canonicalCapitalUsd: SHADOW_GOVERNANCE.CANONICAL_CAPITAL_USD,
    realOrderCount: SHADOW_GOVERNANCE.REAL_ORDERS,
    noRealOrders: SHADOW_GOVERNANCE.NO_REAL_ORDERS,
    feedHealth: 'UNKNOWN',
    runtimeUptimeSeconds: 0,
    acashCommitSha: BASE_COMMIT,
    deploymentImageId: 'NOT_DEPLOYED',
    tournamentStartUtc: null,
    lastDataTimestampUtc: null,
    lastSuccessfulUpdateUtc: NOW_UTC,
    overallStatus: 'NOT_STARTED',
    haltReason: 'Tournament has not been started. Awaiting Human authorization (H01) and strategy candidate selection (H02).',
  },
  slots: {
    A: makeInfraSlot('A'),
    B: makeInfraSlot('B'),
    C: makeInfraSlot('C'),
  },
  leaderboard: {
    rankedSlots: [],
    comparisonAvailability: 'INSUFFICIENT_SAMPLE',
    comparisonNote:
      'Tournament not started. Zero runtime data available. ' +
      'Sample size insufficient for any statistical comparison.',
  },
  _meta: {
    fetchedAtUtc: NOW_UTC,
    dataSource: 'MOCK_DEMO',
    isMockData: true,
    mockNotice:
      'MOCK DEMO DATA · Shadow Tournament not running · NOT ACASH research evidence · ' +
      'CANONICAL CAPITAL = $0.00 · REAL ORDERS = 0 · NO_REAL_ORDERS = true',
  },
};
