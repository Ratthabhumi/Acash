/**
 * ACASH CORE-001 / HYP_011 — Read-Only Dashboard Types
 *
 * Mirrors the Python view model (src/acash/observability/core001_dashboard.py).
 * Presentation only — never authority.
 *
 * SHADOW / SIMULATED ONLY — NOT Paper — NOT Live — NOT a trading surface.
 */

// ---------------------------------------------------------------------------
// Governance constants (mirror ratified framework; dashboard never changes them)
// ---------------------------------------------------------------------------

export const CORE001_GOVERNANCE = {
  CORE_ID: 'CORE-001',
  HYPOTHESIS_ID: 'HYP_011',
  STRATEGY_NAME: 'Global 80/20 Strategic Allocation Core',
  S1_REQUIRED: 20,
  S2_REQUIRED: 60,
  LONG_HORIZON_REQUIRED: 504,
  REQUIRED_ANNUAL_REBALANCES: 2,
  S2_MDD_LIMIT: 0.25,
  S2_CUMRET_FLOOR: -0.2,
  S2_DAILY_FLOOR: -0.1,
  CANONICAL_CAPITAL_USD: 0.0,
  NO_REAL_ORDERS: true,
  PAPER_AUTHORIZED: false,
  LIVE_AUTHORIZED: false,
  MODE: 'SHADOW_SIMULATED_OBSERVABILITY_ONLY',
} as const;

// ---------------------------------------------------------------------------
// View-model interfaces
// ---------------------------------------------------------------------------

export interface Core001Identity {
  core_id: string;
  hypothesis_id: string;
  strategy_name: string;
}

export interface Core001Governance {
  stage: string;
  paper_eligible: boolean;
  paper_eligible_basis: string;
  paper_authorized: boolean;
  live_authorized: boolean;
  live_locked: boolean;
  real_capital_authority_usd: string;
  no_real_orders: boolean;
}

export interface Core001Progress {
  observed_sessions: number;
  s1_required: number;
  s2_required: number;
  s4_checkpoints: number[];
  long_horizon_required: number;
  completed_annual_rebalances: number;
  required_annual_rebalances: number;
}

export interface Core001Portfolio {
  total_equity: string;
  cash: string;
  receivable: string;
  holdings: Record<string, number>;
  market_value?: string;
  basis: string;
}

export interface Core001Benchmark {
  equity: string | null;
  shares: number;
  return_since_entry?: string;
  status: string;
}

export interface Core001Performance {
  latest_daily_return: string | null;
  cumulative_return: string | null;
  current_drawdown: string | null;
  max_drawdown: string | null;
  annualized_sharpe: string | null;
  annualized_volatility: string | null;
  status: string;
}

export interface Core001S2 {
  mdd_limit: string;
  cumulative_return_floor: string;
  daily_return_floor: string;
  current_mdd: string | null;
  current_cumulative_return: string | null;
  worst_daily_return: string | null;
  evaluation_state: string;
  note: string;
}

export interface Core001Evidence {
  status: string;
  reason: string;
  latest_observation_ordinal: number | null;
  latest_observation_session: string | null;
  latest_artifact_sha256?: string | null;
  previous_artifact_sha256?: string | null;
  provider_attempts?: number | null;
  corporate_action_status?: string;
  state_chain_health?: string;
  observation_count?: number;
}

export interface Core001Runtime {
  runtime_status: string;
  timer_status: string;
  service_status: string;
  note: string;
}

export interface Core001Incident {
  category: string;
  basis: string;
}

export interface Core001EquityPoint {
  session: string;
  ordinal: number;
  strategy_equity: string;
  benchmark_equity: string;
  strategy_drawdown: string;
}

export interface Core001DashboardState {
  identity: Core001Identity;
  governance: Core001Governance;
  progress: Core001Progress;
  portfolio: Core001Portfolio;
  benchmark: Core001Benchmark;
  performance: Core001Performance;
  s2: Core001S2;
  evidence: Core001Evidence;
  runtime: Core001Runtime;
  incident: Core001Incident;
  equity_series: Core001EquityPoint[];
  dataSource: 'SNAPSHOT' | 'EMPTY_PRE_S1';
  fetchedAtUtc: string;
}

export interface Core001ApiResponse {
  ok: boolean;
  data: Core001DashboardState | null;
  error: string | null;
  fetchedAtUtc: string;
}
