/**
 * ACASH Shadow Alpha Tournament — TypeScript Data Contract
 *
 * Governance Invariants (Non-Negotiable):
 * - SHADOW / SIMULATED ONLY — zero real capital, zero real orders.
 * - Read-only representation; zero mutation capability from the UI.
 * - NO strategy qualification implied by any tournament result.
 * - NOT Paper GO / NOT Live / NOT HYP_003 / NOT R1.
 * - CANONICAL_CAPITAL = $0.00  |  NO_REAL_ORDERS = true
 */

// ---------------------------------------------------------------------------
// Governance constants embedded in type contract
// ---------------------------------------------------------------------------

export const SHADOW_GOVERNANCE = {
  CANONICAL_CAPITAL_USD: 0.00,
  REAL_ORDERS: 0,
  NO_REAL_ORDERS: true,
  IS_PAPER_AUTHORIZED: false,
  IS_LIVE_AUTHORIZED: false,
  IS_BACKTEST_AUTHORIZED: false,
  HYP_003_EXISTS: false,
  R1_STARTED: false,
  MODE: 'SHADOW_SIMULATED_RESEARCH_INFRA_ONLY',
  BADGE: 'SHADOW / SIMULATED ONLY',
} as const;

// ---------------------------------------------------------------------------
// Slot and strategy types
// ---------------------------------------------------------------------------

export type SlotId = 'A' | 'B' | 'C';
export type SlotStatus =
  | 'RUNNING'
  | 'HALTED'
  | 'UNASSIGNED'
  | 'ERROR'
  | 'INITIALIZING';

export type FeedHealth = 'HEALTHY' | 'STALE' | 'HALTED' | 'DISCONNECTED' | 'UNKNOWN';

export type SimulatedOrderStatus = 'OPEN' | 'FILLED' | 'CANCELLED';
export type SimulatedPositionSide = 'LONG' | 'SHORT';

// ---------------------------------------------------------------------------
// Per-slot state
// ---------------------------------------------------------------------------

export interface SimulatedPosition {
  positionId: string;
  symbol: string;
  side: SimulatedPositionSide;
  entryPrice: number;
  quantity: number;
  unrealizedPnlUsd: number;
  unrealizedPnlPct: number;
  openedAtUtc: string;
}

export interface SimulatedFill {
  fillId: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  price: number;
  quantity: number;
  filledAtUtc: string;
  pnlUsd: number | null; // null for opening fills
}

export interface EquityPoint {
  timestampUtc: string;
  navUsd: number;
  drawdownPct: number;
}

export interface SlotMetrics {
  initialNavUsd: number;
  currentNavUsd: number;
  pnlUsd: number;
  pnlPct: number;
  realizedPnlUsd: number;
  unrealizedPnlUsd: number;
  maxDrawdownPct: number;
  currentDrawdownPct: number;
  exposurePct: number;
  riskUtilizationPct: number;
  openPositionCount: number;
  simulatedOrderCount: number;
  simulatedFillCount: number;
  winCount: number;
  lossCount: number;
  winRatePct: number | null; // null if < 2 closed trades
  signalCount: number;
  lastSignalUtc: string | null;
  lastFillUtc: string | null;
  durationSeconds: number;
}

export interface StrategySlot {
  slotId: SlotId;
  strategyId: string;           // 'UNASSIGNED' if no candidate assigned
  strategyName: string;
  strategyVersion: string;
  governanceLabel: string;      // Always 'INFRASTRUCTURE_TEST_STRATEGY_ONLY' or 'UNASSIGNED'
  status: SlotStatus;
  metrics: SlotMetrics;
  openPositions: SimulatedPosition[];
  recentFills: SimulatedFill[];  // Last 10 fills
  equityCurve: EquityPoint[];    // Sampled at poll interval
  lastBarUtc: string | null;
  sessionId: string;
  configHash: string;
  acashCommitSha: string;
  haltReason: string | null;     // Populated when HALTED
}

// ---------------------------------------------------------------------------
// Global tournament state
// ---------------------------------------------------------------------------

export interface TournamentGlobalStatus {
  tournamentId: string;
  label: string;                  // 'Shadow Alpha Tournament'
  governanceBadge: string;        // 'SHADOW / SIMULATED ONLY'
  canonicalCapitalUsd: number;    // Always 0.00
  realOrderCount: number;         // Always 0
  noRealOrders: boolean;          // Always true
  feedHealth: FeedHealth;
  runtimeUptimeSeconds: number;
  acashCommitSha: string;
  deploymentImageId: string;      // Container image digest or 'NOT_DEPLOYED'
  tournamentStartUtc: string | null;
  lastDataTimestampUtc: string | null;
  lastSuccessfulUpdateUtc: string | null;
  overallStatus: 'RUNNING' | 'HALTED' | 'NOT_STARTED' | 'PARTIAL';
  haltReason: string | null;
}

export interface TournamentLeaderboard {
  rankedSlots: Array<{
    rank: number;
    slotId: SlotId;
    strategyName: string;
    pnlPct: number;
    maxDrawdownPct: number;
    navUsd: number;
  }>;
  comparisonAvailability: 'INSUFFICIENT_SAMPLE' | 'INDICATIVE_ONLY' | 'AVAILABLE';
  comparisonNote: string;
}

export interface TournamentState {
  global: TournamentGlobalStatus;
  slots: Record<SlotId, StrategySlot>;
  leaderboard: TournamentLeaderboard;
  /** Polling metadata for the read-only data plane */
  _meta: {
    fetchedAtUtc: string;
    dataSource: 'MOCK_DEMO' | 'LIVE_API';
    isMockData: boolean;
    mockNotice: string;
  };
}

// ---------------------------------------------------------------------------
// API response contracts (read-only)
// ---------------------------------------------------------------------------

export interface ShadowApiResponse<T> {
  ok: boolean;
  data: T | null;
  error: string | null;
  fetchedAtUtc: string;
}
