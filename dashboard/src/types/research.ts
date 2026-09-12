/**
 * ACASH Research Dashboard — Canonical TypeScript Data Contract
 * 
 * Strict Governance Invariants:
 * - Read-only research observability representation.
 * - Decoupled from execution; zero order submission capability.
 * - Clear demarcation between real artifacts and mock/demo states.
 */

export type RunStatus = 'COMPLETED' | 'RUNNING' | 'HALTED' | 'TERMINATED';
export type HumanAuthStatus = 'NOT_AUTHORIZED' | 'PENDING_REVIEW' | 'REJECTED';

export type ValidationCriterionStatus = 
  | 'NOT_EVALUATED' 
  | 'DEMO' 
  | 'PENDING' 
  | 'FAIL' 
  | 'NOT_APPLICABLE';

export type TimelineEventCategory =
  | 'RUN_STARTED'
  | 'DATA_INGESTED'
  | 'SIGNAL_GENERATED'
  | 'TRADE_EXECUTED'
  | 'POSITION_CHANGED'
  | 'DRAWDOWN_EVENT'
  | 'VALIDATION_EVENT'
  | 'RUN_COMPLETED';

export interface RunMetadata {
  sessionId: string;
  strategyId: string;           // E.g. "MOCK-RESEARCH-001" (Never HYP_001/HYP_002)
  strategyVersion: string;      // E.g. "1.0.0-DEMO"
  isDemoData: boolean;          // Always true for Phase A mock runs
  demoNotice: string;           // "DEMO DATA · SIMULATED RESEARCH RUN · NOT ACASH RESEARCH EVIDENCE"
  gitCommit: string;
  configHash: string;
  manifestHash: string;
  environment: string;
  dataSource: string;
  marketDomain: string;
  startTimeUtc: string;
  endTimeUtc: string;
  totalEventCount: number;
  totalTradeCount: number;
  finalState: RunStatus;
  humanAuthorizationStatus: HumanAuthStatus; // Explicitly NOT_AUTHORIZED
  governanceDisclaimer: string;
}

export interface DatasetMetadata {
  datasetId: string;
  version: string;
  symbols: string[];
  timeframe: string;
  startUtc: string;
  endUtc: string;
  barCount: number;
  canonicalBatchSha256: string;
  rawSourceSha256: string;
  storageEngine: string;
}

export interface ConfigMetadata {
  configId: string;
  configHash: string;
  parameters: Record<string, string | number | boolean>;
  frictionModel: {
    quotedSpreadBps: number;
    roundtripFeeBps: number;
    fixedSlippageBps: number;
    totalFrictionBps: number;
    status: string;
  };
  executionModel: {
    type: string;
    horizon: number;
    fillTiming: string;
  };
}

export interface EquityPoint {
  index: number;
  date: string;
  timestamp: string;
  equity: number;
  drawdownPct: number;
  grossEquity: number;
  netEquity: number;
  cash: number;
  tradeCount: number;
}

export interface PerformanceMetrics {
  durationDays: number;
  totalReturnPct: number;
  annualizedReturnPct: number;
  maxDrawdownPct: number;
  sharpeRatio: number;
  sortinoRatio: number;
  profitFactor: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRatePct: number;
  avgWinBps: number;
  avgLossBps: number;
  expectancyR: number;
  // Friction decomposition
  grossReturnPct: number;
  totalFrictionCostPct: number;
  feesPaidPct: number;
  slippageIncurredPct: number;
  netReturnPct: number;
}

export interface TradeRecord {
  id: string;
  sequence: number;
  timestamp: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  exitPrice: number;
  size: number;
  pnlUsd: number;
  pnlBps: number;
  rMultiple: number;
  durationBars: number;
  status: 'CLOSED_WIN' | 'CLOSED_LOSS' | 'OPEN';
  // Full Causal Evidence Chain
  evidenceChain: {
    signalId: string;
    signalValue: number;
    featureHash: string;
    riskDecisionId: string;
    riskVerdict: string;
    orderIntentId: string;
    simulatedFillId: string;
    slippageDeductedBps: number;
    positionId: string;
    portfolioImpactBps: number;
  };
}

export interface TimelineEvent {
  id: string;
  sequence: number;
  timestamp: string;
  category: TimelineEventCategory;
  title: string;
  summary: string;
  sourceModule: string;
  relatedTradeId?: string;
  relatedPositionId?: string;
  evidenceRef?: string;
  payload: Record<string, unknown>;
}

export interface ValidationCriterion {
  id: string;
  name: string;
  ruleSpecification: string;
  observedMetric: string;
  status: ValidationCriterionStatus; // In mock data: NOT_EVALUATED, DEMO, or PENDING
  category: 'STATISTICAL' | 'FRICTION' | 'OUT_OF_SAMPLE' | 'ROBUSTNESS' | 'GOVERNANCE';
  notes: string;
}

export interface LineageNode {
  id: string;
  stageNumber: number; // 1 to 11
  stageName: string;
  shortTitle: string;
  description: string;
  artifactName: string;
  hashOrDigest: string;
  authorityRule: string;
  sourceModule: string;
  timestamp: string;
  inputLineage: string[];
  outputLineage: string[];
  mockEvidencePayload: Record<string, unknown>;
}

export interface OutOfSampleComparison {
  metricName: string;
  inSampleValue: string;
  outOfSampleValue: string;
  delta: string;
  status: 'NOT_EVALUATED' | 'DEMO';
}

export interface ResearchRun {
  metadata: RunMetadata;
  dataset: DatasetMetadata;
  config: ConfigMetadata;
  metrics: PerformanceMetrics;
  equityCurve: EquityPoint[];
  trades: TradeRecord[];
  timelineEvents: TimelineEvent[];
  validationCriteria: ValidationCriterion[];
  lineage: LineageNode[]; // Exactly 11 stages
  oosComparison: OutOfSampleComparison[];
}

export interface TradeFilterOptions {
  searchQuery?: string;
  symbol?: string;
  side?: 'ALL' | 'LONG' | 'SHORT';
  status?: 'ALL' | 'WIN' | 'LOSS';
  outcome?: 'ALL' | 'WIN' | 'LOSS';
  sortBy?: 'timestamp' | 'pnlBps' | 'rMultiple';
  sortDirection?: 'asc' | 'desc';
  page?: number;
  pageSize?: number;
}

