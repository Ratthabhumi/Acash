import { ResearchRun, TradeRecord, TimelineEvent, EquityPoint, LineageNode, ValidationCriterion } from '../types/research';

// Helper to generate 90-day daily equity series
function generateMockEquityCurve(): EquityPoint[] {
  const points: EquityPoint[] = [];
  const baseDate = new Date('2026-05-15T00:00:00Z');
  let currentEquity = 100000;
  let peakEquity = 100000;
  let grossEquity = 100000;
  let tradeCount = 0;

  for (let i = 0; i <= 90; i++) {
    const d = new Date(baseDate);
    d.setUTCDate(d.getUTCDate() + i);
    const dateStr = d.toISOString().split('T')[0];

    if (i > 0) {
      // Simulate realistic quantitative drift with modest volatility and friction
      const dailyTrades = (i % 2 === 0 || i % 3 === 0) ? Math.floor(1 + Math.sin(i) * 1.5 + 1) : 0;
      tradeCount += dailyTrades;

      // Drift + random normal-ish step
      const rawShock = (Math.sin(i * 0.22) * 0.004) + (Math.cos(i * 0.15) * 0.003) + 0.002;
      const frictionDrift = dailyTrades * 0.00015; // 1.5 bps friction drag

      const grossDelta = currentEquity * rawShock;
      const netDelta = grossDelta - (currentEquity * frictionDrift);

      grossEquity += grossDelta;
      currentEquity += netDelta;

      if (currentEquity > peakEquity) {
        peakEquity = currentEquity;
      }
    }

    const drawdownPct = peakEquity > 0 ? -((peakEquity - currentEquity) / peakEquity) * 100 : 0;

    points.push({
      index: i,
      date: dateStr,
      timestamp: d.toISOString(),
      equity: Math.round(currentEquity * 100) / 100,
      drawdownPct: Math.round(drawdownPct * 100) / 100,
      grossEquity: Math.round(grossEquity * 100) / 100,
      netEquity: Math.round(currentEquity * 100) / 100,
      cash: Math.round(currentEquity * 0.85 * 100) / 100,
      tradeCount,
    });
  }

  return points;
}

// Helper to generate 127 mock trades with evidence chain
function generateMockTrades(): TradeRecord[] {
  const trades: TradeRecord[] = [];
  const baseDate = new Date('2026-05-15T08:00:00Z');
  const symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD'];

  for (let i = 1; i <= 127; i++) {
    const date = new Date(baseDate.getTime() + i * 16.5 * 3600 * 1000);
    const isWin = (i * 17 + 5) % 100 < 57; // ~56.7% win rate
    const symbol = symbols[i % symbols.length];
    const side: 'LONG' | 'SHORT' = i % 3 === 0 ? 'SHORT' : 'LONG';
    const basePrice = symbol === 'USDJPY' ? 154.20 : 1.0850;
    const entryPrice = basePrice + (i % 20) * 0.0005;
    const pnlBps = isWin ? +(15 + (i % 25) * 1.8) : -(12 + (i % 15) * 1.2);
    const exitPrice = side === 'LONG' 
      ? entryPrice * (1 + pnlBps / 10000)
      : entryPrice * (1 - pnlBps / 10000);
    const rMultiple = isWin ? Math.round((pnlBps / 14) * 100) / 100 : -1.0;
    const pnlUsd = Math.round((pnlBps * 12.5) * 100) / 100;

    trades.push({
      id: `TRD-DEMO-${String(i).padStart(4, '0')}`,
      sequence: i,
      timestamp: date.toISOString(),
      symbol,
      side,
      entryPrice: Math.round(entryPrice * 100000) / 100000,
      exitPrice: Math.round(exitPrice * 100000) / 100000,
      size: 100000,
      pnlUsd,
      pnlBps: Math.round(pnlBps * 10) / 10,
      rMultiple,
      durationBars: (i % 12) + 2,
      status: isWin ? 'CLOSED_WIN' : 'CLOSED_LOSS',
      evidenceChain: {
        signalId: `SIG-DEMO-${String(i).padStart(4, '0')}`,
        signalValue: side === 'LONG' ? +1.0 : -1.0,
        featureHash: `sha256:feat_${(i * 1337).toString(16).padStart(16, '0')}`,
        riskDecisionId: `RISK-EVAL-${String(i).padStart(4, '0')}`,
        riskVerdict: 'SIMULATED_RISK_BOUNDED',
        orderIntentId: `INTENT-${String(i).padStart(4, '0')}`,
        simulatedFillId: `FILL-SIM-${String(i).padStart(4, '0')}`,
        slippageDeductedBps: 0.3,
        positionId: `POS-MOCK-${String(i).padStart(4, '0')}`,
        portfolioImpactBps: Math.round(pnlBps * 0.12 * 10) / 10,
      },
    });
  }

  return trades;
}

// 11-Stage Evidence Lineage DAG
const mockLineageNodes: LineageNode[] = [
  {
    id: 'stage-1-market-data',
    stageNumber: 1,
    stageName: 'Market Data',
    shortTitle: 'Raw Ingestion',
    description: 'Bi-temporal immutable Parquet part files verified with raw source SHA-256.',
    artifactName: 'part-EURUSD-H4-2026.parquet',
    hashOrDigest: 'sha256:8f4c2e9b110a...',
    authorityRule: 'PIT_TIMESTAMP_ASCENDING',
    sourceModule: 'demo.data.parquet_provider',
    timestamp: '2026-05-15T00:00:00Z',
    inputLineage: ['External Raw Feed'],
    outputLineage: ['stage-2-normalized-data'],
    mockEvidencePayload: {
      recordsIngested: 3739,
      parquetPartHash: '8f4c2e9b110a19d45e43a9f0298a728b',
      vintageIsoUtc: '2026-05-15T00:00:00Z',
    },
  },
  {
    id: 'stage-2-normalized-data',
    stageNumber: 2,
    stageName: 'Normalized Data',
    shortTitle: 'Canonical Bars',
    description: 'Canonical OHLCV bar panel validation with exact Decimal128 arithmetic.',
    artifactName: 'panel_canonical_h4.arrow',
    hashOrDigest: 'sha256:4d7a812e99bf...',
    authorityRule: 'CANONICAL_ARROW_SCHEMA_V1',
    sourceModule: 'demo.data.schema',
    timestamp: '2026-05-15T00:05:00Z',
    inputLineage: ['stage-1-market-data'],
    outputLineage: ['stage-3-feature-state'],
    mockEvidencePayload: {
      canonicalBatchDigest: '4d7a812e99bf88c031d274e5088fbc21',
      zeroVarianceChecked: true,
      timeContinuityVerified: true,
    },
  },
  {
    id: 'stage-3-feature-state',
    stageNumber: 3,
    stageName: 'Feature State',
    shortTitle: 'Causal Features',
    description: 'Lagged lookback returns and volatility estimators strictly preserving zero look-ahead bias.',
    artifactName: 'features_lookback_tsmom.parquet',
    hashOrDigest: 'sha256:721a9900c14b...',
    authorityRule: 'STRICT_CAUSALITY_T_MINUS_1',
    sourceModule: 'demo.data.features.engine',
    timestamp: '2026-05-15T00:10:00Z',
    inputLineage: ['stage-2-normalized-data'],
    outputLineage: ['stage-4-signal'],
    mockEvidencePayload: {
      featureGrid: 'lookback=[3,6,12,24,48,120]',
      lookaheadLeakageCheck: 'PASS_ZERO_LEAKAGE',
    },
  },
  {
    id: 'stage-4-signal',
    stageNumber: 4,
    stageName: 'Signal',
    shortTitle: 'Ternary Signal',
    description: 'Ternary directional hypothesis evaluation with deadband friction boundary filter.',
    artifactName: 'signals_ternary_stream.jsonl',
    hashOrDigest: 'sha256:1a84f33190ab...',
    authorityRule: 'DEADBAND_FILTER_RULE',
    sourceModule: 'mock.research.evaluation',
    timestamp: '2026-05-15T00:15:00Z',
    inputLineage: ['stage-3-feature-state'],
    outputLineage: ['stage-5-risk-decision'],
    mockEvidencePayload: {
      signalType: 'TERNARY_DIRECTIONAL',
      activeSignalRatio: 0.62,
      deadbandThresholdBps: 3.0,
    },
  },
  {
    id: 'stage-5-risk-decision',
    stageNumber: 5,
    stageName: 'Risk Decision',
    shortTitle: 'Pre-Trade Risk',
    description: 'Kill-switch validation, max position checks, and drawdown circuit breaker gating.',
    artifactName: 'risk_gate_eval_ledger.jsonl',
    hashOrDigest: 'sha256:3381df68122c...',
    authorityRule: 'DEMO_RISK_GATE_RULE',
    sourceModule: 'mock.risk.guard',
    timestamp: '2026-05-15T00:16:00Z',
    inputLineage: ['stage-4-signal'],
    outputLineage: ['stage-6-order-intent'],
    mockEvidencePayload: {
      killSwitchState: 'SIMULATED_NORMAL',
      maxPositionExposureBps: 2000,
      riskRejectionCount: 0,
    },
  },
  {
    id: 'stage-6-order-intent',
    stageNumber: 6,
    stageName: 'Order Intent',
    shortTitle: 'Intent Manifest',
    description: 'Cryptographically sealed order intent created with correlation ID lineage.',
    artifactName: 'order_intents_journal.jsonl',
    hashOrDigest: 'sha256:59bb8a719cde...',
    authorityRule: 'DEMO_INTENT_SPEC',
    sourceModule: 'mock.paper.simulation',
    timestamp: '2026-05-15T00:17:00Z',
    inputLineage: ['stage-5-risk-decision'],
    outputLineage: ['stage-7-simulated-execution'],
    mockEvidencePayload: {
      totalIntentsSealed: 127,
      correlationChainVerified: true,
    },
  },
  {
    id: 'stage-7-simulated-execution',
    stageNumber: 7,
    stageName: 'Simulated Execution',
    shortTitle: 'Fill Simulation',
    description: 'Next-bar open fill simulation with 3-tier friction (spread + fee + slippage).',
    artifactName: 'simulated_fills_record.jsonl',
    hashOrDigest: 'sha256:9981ca2901ee...',
    authorityRule: 'DEMO_FRICTION_MODEL',
    sourceModule: 'mock.paper.simulation',
    timestamp: '2026-05-15T00:18:00Z',
    inputLineage: ['stage-6-order-intent'],
    outputLineage: ['stage-8-position'],
    mockEvidencePayload: {
      frictionDeductedTotalBps: 1.2,
      fillTimingPolicy: 'NEXT_BAR_OPEN',
      brokerOrdersSubmitted: 0, // Strict zero broker orders
    },
  },
  {
    id: 'stage-8-position',
    stageNumber: 8,
    stageName: 'Position',
    shortTitle: 'Position Ledger',
    description: 'Bi-temporal position accounting and lot-level cost basis maintenance.',
    artifactName: 'position_history_ledger.jsonl',
    hashOrDigest: 'sha256:2219bcde88fa...',
    authorityRule: 'DEMO_LOT_ACCOUNTING',
    sourceModule: 'mock.portfolio.allocation',
    timestamp: '2026-05-15T00:19:00Z',
    inputLineage: ['stage-7-simulated-execution'],
    outputLineage: ['stage-9-portfolio'],
    mockEvidencePayload: {
      maxSimultaneousPositions: 2,
      holdingTimeAverageHours: 28.5,
    },
  },
  {
    id: 'stage-9-portfolio',
    stageNumber: 9,
    stageName: 'Portfolio',
    shortTitle: 'Simulated Valuation',
    description: 'Simulated mark-to-market valuation series and reference notional tracking.',
    artifactName: 'portfolio_equity_curve.arrow',
    hashOrDigest: 'sha256:6631adbf90aa...',
    authorityRule: 'DEMO_NOTIONAL_VALUATION',
    sourceModule: 'mock.portfolio.mtm',
    timestamp: '2026-05-15T00:20:00Z',
    inputLineage: ['stage-8-position'],
    outputLineage: ['stage-10-metrics'],
    mockEvidencePayload: {
      simulatedReferenceNotionalUsd: 100000,
      simulatedEndingNotionalUsd: 118420,
      unrealizedPnlAccounting: 'SIMULATED_MTM',
    },
  },
  {
    id: 'stage-10-metrics',
    stageNumber: 10,
    stageName: 'Metrics',
    shortTitle: 'Empirical Stats',
    description: 'Observed Sharpe, Sortino, max drawdown, and empirical distribution calculation.',
    artifactName: 'metrics_summary_report.json',
    hashOrDigest: 'sha256:7710cba190ee...',
    authorityRule: 'DEMO_H4_BAR_STATS',
    sourceModule: 'mock.analytics.engine',
    timestamp: '2026-08-15T00:00:00Z',
    inputLineage: ['stage-9-portfolio'],
    outputLineage: ['stage-11-validation'],
    mockEvidencePayload: {
      observedSharpeAnnualized: 1.82,
      observedMaxDrawdownPct: 4.2,
      totalFrictionDecayBps: 152.4,
    },
  },
  {
    id: 'stage-11-validation',
    stageNumber: 11,
    stageName: 'Validation',
    shortTitle: 'Gate Evaluation',
    description: 'Multi-gate statistical audit, DSR multiple-testing adjustment, and governance sealing.',
    artifactName: 'search_trial_ledger_manifest.json',
    hashOrDigest: 'sha256:88301fa9b201...',
    authorityRule: 'DEMO_STATISTICAL_GATE_SPEC',
    sourceModule: 'mock.validation.evaluator',
    timestamp: '2026-08-15T00:05:00Z',
    inputLineage: ['stage-10-metrics'],
    outputLineage: [],
    mockEvidencePayload: {
      gateVerdictStatus: 'NOT_EVALUATED_DEMO',
      multipleTestingAdjustmentK: 12,
      humanSignatoryAuthority: 'NOT_AUTHORIZED',
    },
  },
];

// Validation Checklist (Reflecting NOT_EVALUATED / DEMO / PENDING states - NO FAKE PASS)
const mockValidationCriteria: ValidationCriterion[] = [
  {
    id: 'VAL-CRIT-01',
    name: 'Sample Size Adequacy (N ≥ 500)',
    ruleSpecification: 'T_eff must exceed 500 independent effective bar observations after causal lag.',
    observedMetric: 'N = 3,739 observations (Simulated in-sample partition)',
    status: 'DEMO',
    category: 'STATISTICAL',
    notes: 'Observed count satisfies sample geometry in mock harness; pending formal production run audit.',
  },
  {
    id: 'VAL-CRIT-02',
    name: 'HAC Robust t-Statistic (t > 2.00)',
    ruleSpecification: 'Newey-West automatic plug-in bandwidth OLS HAC t-stat must exceed 2.00.',
    observedMetric: 't = 3.42 (Unverified Mock Data)',
    status: 'NOT_EVALUATED',
    category: 'STATISTICAL',
    notes: 'Mock t-stat generated for UI telemetry testing. Formal R1 statistical validation not yet executed.',
  },
  {
    id: 'VAL-CRIT-03',
    name: 'Friction Stress Deduction',
    ruleSpecification: 'Minimum 1.2 bps roundtrip friction (0.4 spread + 0.5 fee + 0.3 slippage) deducted per trade.',
    observedMetric: '1.2 bps total friction model enforced in mock engine',
    status: 'DEMO',
    category: 'FRICTION',
    notes: 'Friction drag successfully reduces gross performance from +24.1% to +18.4% in demo dataset.',
  },
  {
    id: 'VAL-CRIT-04',
    name: 'Demo Out-of-Sample Partition Isolation',
    ruleSpecification: 'Demo OOS partition (Bars 5,009..6,230) marked as unexposed in prototype harness.',
    observedMetric: 'DEMO PARTITION · UNEXPOSED IN PROTOTYPE (Not real ACASH research evidence)',
    status: 'NOT_EVALUATED',
    category: 'OUT_OF_SAMPLE',
    notes: 'Mock demonstration structure only. Real ACASH out-of-sample data is protected and never accessible to research prototypes.',
  },
  {
    id: 'VAL-CRIT-05',
    name: 'Parameter Perturbation Stability',
    ruleSpecification: 'Performance delta across ±20% parameter grid variation must not exceed 15% decay.',
    observedMetric: 'Grid perturbation sensitivity not computed',
    status: 'NOT_EVALUATED',
    category: 'ROBUSTNESS',
    notes: 'Perturbation matrix evaluation deferred to Phase 6 validation runner.',
  },
  {
    id: 'VAL-CRIT-06',
    name: 'Market Capacity & Headroom',
    ruleSpecification: 'Simulated order size must not exceed 1.0% of 20-day Average Daily Volume (ADV).',
    observedMetric: 'ADV headroom assessment pending',
    status: 'NOT_EVALUATED',
    category: 'ROBUSTNESS',
    notes: 'Pending execution against real market volume profiles.',
  },
  {
    id: 'VAL-CRIT-07',
    name: 'Independent Hash Ledger Review',
    ruleSpecification: 'Cryptographic hash-chain linking genesis block to final manifest must be verified.',
    observedMetric: 'Verification pending independent auditor run',
    status: 'PENDING',
    category: 'GOVERNANCE',
    notes: 'Awaiting independent CLI verification on dedicated audit runner.',
  },
  {
    id: 'VAL-CRIT-08',
    name: 'Human Research Signatory Authorization',
    ruleSpecification: 'Formal cryptographic signature from designated research director approving strategy transition.',
    observedMetric: 'STATUS: NOT AUTHORIZED (Hard Locked by Governance)',
    status: 'FAIL', // Explicit FAIL to communicate non-authorized state
    category: 'GOVERNANCE',
    notes: 'Trading authority remains strictly LOCKED ($0.00 capital). No operational authorization granted.',
  },
];

// Timeline Events (Sample milestones along the 90 days)
const mockTimelineEvents: TimelineEvent[] = [
  {
    id: 'EVT-001',
    sequence: 1,
    timestamp: '2026-05-15T08:00:00Z',
    category: 'RUN_STARTED',
    title: 'Research Session Initialized',
    summary: 'Session SES-DEMO-2026-001 started under mock research harness with strategy MOCK-RESEARCH-001.',
    sourceModule: 'demo.paper.runner',
    payload: {
      sessionId: 'SES-DEMO-2026-001',
      mode: 'RESEARCH_VIEW_ONLY',
      simulatedReferenceNotional: '$100,000 (Reference Only)',
      capitalAuthority: '$0.00',
    },
  },
  {
    id: 'EVT-015',
    sequence: 15,
    timestamp: '2026-05-28T12:00:00Z',
    category: 'SIGNAL_GENERATED',
    title: 'First Cluster of Directional Signals',
    summary: 'Ternary momentum filter generated 8 qualifying entry signals exceeding 3.0 bps deadband.',
    sourceModule: 'demo.research.evaluation',
    relatedTradeId: 'TRD-DEMO-0001',
    payload: {
      signalsCount: 8,
      symbols: ['EURUSD', 'GBPUSD'],
      deadbandThresholdBps: 3.0,
    },
  },
  {
    id: 'EVT-042',
    sequence: 42,
    timestamp: '2026-06-18T16:00:00Z',
    category: 'TRADE_EXECUTED',
    title: 'Milestone: 50 Simulated Trades Filled',
    summary: 'Simulated execution reached 50 trades with cumulative friction drag of 60.0 bps.',
    sourceModule: 'demo.paper.runner',
    relatedTradeId: 'TRD-DEMO-0050',
    payload: {
      tradesFilled: 50,
      cumulativePnlUsd: '+6,420.50',
      totalFrictionDeductedBps: 60.0,
    },
  },
  {
    id: 'EVT-068',
    sequence: 68,
    timestamp: '2026-07-08T04:00:00Z',
    category: 'DRAWDOWN_EVENT',
    title: 'Peak-to-Trough Drawdown Window (-4.2%)',
    summary: 'Consecutive adverse price movements triggered max observed drawdown of -4.2%. Risk controls held.',
    sourceModule: 'demo.risk.guard',
    payload: {
      drawdownDepthPct: -4.2,
      peakEquity: 112400,
      troughEquity: 107679,
      killSwitchTriggered: false,
    },
  },
  {
    id: 'EVT-095',
    sequence: 95,
    timestamp: '2026-07-28T20:00:00Z',
    category: 'POSITION_CHANGED',
    title: 'Portfolio Simulated De-Risk Transition',
    summary: 'Simulated rebalance planner executed planned derisking to 85% defensive buffer prior to volatile macro release.',
    sourceModule: 'demo.portfolio.planner',
    payload: {
      targetDefensiveRatio: 0.85,
      positionsClosed: 2,
      rebalanceFrictionBps: 2.4,
    },
  },
  {
    id: 'EVT-120',
    sequence: 120,
    timestamp: '2026-08-15T00:00:00Z',
    category: 'RUN_COMPLETED',
    title: '90-Day Simulation Window Concluded',
    summary: 'Simulation concluded after 90 days, 127 trades, and 3,739 observations. Synthetic manifest sealed with demo digest.',
    sourceModule: 'demo.paper.manifest',
    evidenceRef: 'sha256:8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
    payload: {
      totalTrades: 127,
      finalEquityUsd: 118420,
      manifestHash: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
    },
  },
];

// Complete Mock Research Run Object
export const mockResearchRun: ResearchRun = {
  metadata: {
    sessionId: 'SES-DEMO-2026-001',
    strategyId: 'MOCK-RESEARCH-001',
    strategyVersion: '1.0.0-DEMO',
    isDemoData: true,
    demoNotice: 'DEMO DATA · SIMULATED RESEARCH RUN · NOT ACASH RESEARCH EVIDENCE',
    gitCommit: 'demo9a1b2c',
    configHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    manifestHash: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
    environment: 'RESEARCH_SIMULATION_SANDBOX',
    dataSource: 'SYNTHETIC_CANONICAL_EURUSD_H4',
    marketDomain: 'FX_G10_OVERNIGHT',
    startTimeUtc: '2026-05-15T00:00:00Z',
    endTimeUtc: '2026-08-15T00:00:00Z',
    totalEventCount: 120,
    totalTradeCount: 127,
    finalState: 'COMPLETED',
    humanAuthorizationStatus: 'NOT_AUTHORIZED',
    governanceDisclaimer: 'Performance metrics do not imply research qualification or trading authorization.',
  },
  dataset: {
    datasetId: 'DS-EURUSD-H4-2026-MOCK',
    version: '1.0.0-DEMO',
    symbols: ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD'],
    timeframe: 'H4 (4-Hour Bars)',
    startUtc: '2026-05-15T00:00:00Z',
    endUtc: '2026-08-15T00:00:00Z',
    barCount: 3739,
    canonicalBatchSha256: '4d7a812e99bf88c031d274e5088fbc2100a918f0c33d82a170b42c121e78bb29',
    rawSourceSha256: '8f4c2e9b110a19d45e43a9f0298a728b9918aa0921bbcf10984a1e944b9101ff',
    storageEngine: 'DuckDB_PIT_Parquet',
  },
  config: {
    configId: 'CFG-TSMOM-H4-MOCK',
    configHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    parameters: {
      lookbackBars: 24,
      deadbandBps: 3.0,
      horizonBars: 1,
      signalTransform: 'SIGN',
      rebalanceFrequency: 'H4',
      maxPositionExposureBps: 2000,
    },
    frictionModel: {
      quotedSpreadBps: 0.4,
      roundtripFeeBps: 0.5,
      fixedSlippageBps: 0.3,
      totalFrictionBps: 1.2,
      status: 'PROPOSED_RESEARCH_ASSUMPTION',
    },
    executionModel: {
      type: 'NEXT_BAR_OPEN_FILL',
      horizon: 1,
      fillTiming: 'BAR_OPEN_T_PLUS_1',
    },
  },
  metrics: {
    durationDays: 90,
    totalReturnPct: 18.42,
    annualizedReturnPct: 54.3,
    maxDrawdownPct: 4.20,
    sharpeRatio: 1.82,
    sortinoRatio: 2.45,
    profitFactor: 1.68,
    totalTrades: 127,
    winningTrades: 72,
    losingTrades: 55,
    winRatePct: 56.69,
    avgWinBps: 34.2,
    avgLossBps: -22.8,
    expectancyR: 0.42,
    grossReturnPct: 24.12,
    totalFrictionCostPct: 5.70,
    feesPaidPct: 2.38,
    slippageIncurredPct: 1.42,
    netReturnPct: 18.42,
  },
  equityCurve: generateMockEquityCurve(),
  trades: generateMockTrades(),
  timelineEvents: mockTimelineEvents,
  validationCriteria: mockValidationCriteria,
  lineage: mockLineageNodes,
  oosComparison: [
    {
      metricName: 'Annualized Sharpe Ratio',
      inSampleValue: '1.82',
      outOfSampleValue: 'UNEXPOSED (Pristine)',
      delta: 'N/A',
      status: 'NOT_EVALUATED',
    },
    {
      metricName: 'Maximum Drawdown',
      inSampleValue: '-4.20%',
      outOfSampleValue: 'UNEXPOSED (Pristine)',
      delta: 'N/A',
      status: 'NOT_EVALUATED',
    },
    {
      metricName: 'Win Rate (%)',
      inSampleValue: '56.7%',
      outOfSampleValue: 'UNEXPOSED (Pristine)',
      delta: 'N/A',
      status: 'NOT_EVALUATED',
    },
    {
      metricName: 'Trade Expectancy (R)',
      inSampleValue: '0.42R',
      outOfSampleValue: 'UNEXPOSED (Pristine)',
      delta: 'N/A',
      status: 'NOT_EVALUATED',
    },
  ],
};
