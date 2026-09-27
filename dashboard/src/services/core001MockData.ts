/**
 * ACASH CORE-001 — Empty PRE-S1 fallback + snapshot parser (read-only).
 *
 * When no generated snapshot exists (observed count 0, normal pre-first
 * observation), the repository serves this explicit PRE-S1 state — never
 * ERROR, never fake observations.
 */

import {
  CORE001_GOVERNANCE,
  Core001ApiResponse,
  Core001DashboardState,
} from '../types/core001';

export function buildEmptyPreS1State(fetchedAtUtc: string): Core001DashboardState {
  return {
    identity: {
      core_id: CORE001_GOVERNANCE.CORE_ID,
      hypothesis_id: CORE001_GOVERNANCE.HYPOTHESIS_ID,
      strategy_name: CORE001_GOVERNANCE.STRATEGY_NAME,
    },
    governance: {
      stage: 'PRE-S1',
      paper_eligible: false,
      paper_eligible_basis: 'NO_QUALIFICATION_EVIDENCE_IN_V1',
      paper_authorized: CORE001_GOVERNANCE.PAPER_AUTHORIZED,
      live_authorized: CORE001_GOVERNANCE.LIVE_AUTHORIZED,
      live_locked: true,
      real_capital_authority_usd: '0.00',
      no_real_orders: CORE001_GOVERNANCE.NO_REAL_ORDERS,
    },
    progress: {
      observed_sessions: 0,
      s1_required: CORE001_GOVERNANCE.S1_REQUIRED,
      s2_required: CORE001_GOVERNANCE.S2_REQUIRED,
      s4_checkpoints: [126, 252],
      long_horizon_required: CORE001_GOVERNANCE.LONG_HORIZON_REQUIRED,
      completed_annual_rebalances: 0,
      required_annual_rebalances: 2,
    },
    portfolio: {
      total_equity: '100000.00',
      cash: '100000.00',
      receivable: '0',
      holdings: { ACWI: 0, AGG: 0 },
      basis: 'CANONICAL_INITIAL_ALL_CASH',
    },
    benchmark: { equity: null, shares: 0, status: 'NOT YET OBSERVED' },
    performance: {
      latest_daily_return: null,
      cumulative_return: null,
      current_drawdown: null,
      max_drawdown: null,
      annualized_sharpe: null,
      annualized_volatility: null,
      status: 'INSUFFICIENT_OBSERVATIONS',
    },
    s2: {
      mdd_limit: String(CORE001_GOVERNANCE.S2_MDD_LIMIT),
      cumulative_return_floor: String(CORE001_GOVERNANCE.S2_CUMRET_FLOOR),
      daily_return_floor: String(CORE001_GOVERNANCE.S2_DAILY_FLOOR),
      current_mdd: null,
      current_cumulative_return: null,
      worst_daily_return: null,
      evaluation_state: 'INSUFFICIENT_OBSERVATIONS',
      note: 'Diagnostic only until Observation 60.',
    },
    evidence: {
      status: 'AWAITING_OBSERVATION',
      reason: 'NO_SNAPSHOT_YET',
      latest_observation_ordinal: null,
      latest_observation_session: null,
    },
    runtime: {
      runtime_status: 'UNAVAILABLE_FROM_DASHBOARD',
      timer_status: 'UNAVAILABLE_FROM_DASHBOARD',
      service_status: 'UNAVAILABLE_FROM_DASHBOARD',
      note: 'Dashboard v1 performs no remote access.',
    },
    incident: { category: 'NONE', basis: 'NO_INCIDENCE_EVIDENCE' },
    equity_series: [],
    dataSource: 'EMPTY_PRE_S1',
    fetchedAtUtc,
  };
}

/** Validate + normalize a parsed snapshot payload into a view state. */
export function parseCore001Snapshot(payload: unknown, fetchedAtUtc: string): Core001DashboardState {
  if (typeof payload !== 'object' || payload === null) {
    throw new Error('CORE001_SNAPSHOT_NOT_AN_OBJECT');
  }
  const doc = payload as Record<string, unknown>;
  if (doc['document'] !== 'CORE_001_DASHBOARD_SNAPSHOT_V1') {
    throw new Error('CORE001_SNAPSHOT_UNKNOWN_DOCUMENT');
  }
  const view = doc['view'] as Core001DashboardState | null;
  if (typeof view !== 'object' || view === null) {
    throw new Error('CORE001_SNAPSHOT_MISSING_VIEW');
  }
  if (view.identity?.hypothesis_id !== CORE001_GOVERNANCE.HYPOTHESIS_ID) {
    throw new Error('CORE001_SNAPSHOT_HYPOTHESIS_MISMATCH');
  }
  if (view.governance?.paper_authorized !== false || view.governance?.live_authorized !== false) {
    throw new Error('CORE001_SNAPSHOT_AUTHORITY_VIOLATION');
  }
  if (view.governance?.real_capital_authority_usd !== '0.00' || view.governance?.no_real_orders !== true) {
    throw new Error('CORE001_SNAPSHOT_CAPITAL_VIOLATION');
  }
  return { ...view, dataSource: 'SNAPSHOT', fetchedAtUtc };
}

export function emptyPreS1Response(fetchedAtUtc: string): Core001ApiResponse {
  return { ok: true, data: buildEmptyPreS1State(fetchedAtUtc), error: null, fetchedAtUtc };
}

/**
 * Fail-closed blocked state. Used ONLY when a snapshot exists (or may
 * exist) but cannot be trusted: malformed JSON, wrong document, hypothesis
 * mismatch, authority/capital violation, or unreadable source. NEVER used
 * for a genuinely absent snapshot (that is EMPTY PRE-S1). Authority
 * boundaries are preserved structurally even in the blocked state.
 */
export function buildBlockedState(reason: string, fetchedAtUtc: string): Core001DashboardState {
  const base = buildEmptyPreS1State(fetchedAtUtc);
  return {
    ...base,
    governance: { ...base.governance, stage: 'EVIDENCE_INVALID_OR_BLOCKED' },
    portfolio: { ...base.portfolio, basis: 'BLOCKED_EVIDENCE_NOT_SHOWN' },
    evidence: {
      status: 'EVIDENCE_INVALID_OR_BLOCKED',
      reason,
      latest_observation_ordinal: null,
      latest_observation_session: null,
    },
    incident: { category: 'UNKNOWN', basis: 'BLOCKED_EVIDENCE_UNREADABLE' },
    dataSource: 'SNAPSHOT',
    fetchedAtUtc,
  };
}

export function blockedResponse(reason: string, fetchedAtUtc: string): Core001ApiResponse {
  return { ok: false, data: buildBlockedState(reason, fetchedAtUtc), error: reason, fetchedAtUtc };
}
