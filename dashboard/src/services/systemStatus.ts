// Client for the read-only /api/upi/status/system endpoint.

const STATUS_ENDPOINT = 'http://127.0.0.1:8765/api/upi/status/system';

export interface FrameworkStatus {
  framework_id: string;
  adapter_present?: boolean;
  package_installed?: boolean;
  native_smoke_verified?: boolean;
  input_rights_qualified?: boolean;
  pit_validated?: boolean;
  result_reconciled?: boolean;
  dashboard_connected?: boolean;
  production_enabled?: boolean;
  blocked_reason?: string | null;
  execution_authority?: string;
  role?: string;
  license?: string;
}

export interface OpsReport {
  windows_sync?: { scheduled_sync_accepted?: boolean; status?: string; synced_at?: string | null };
  collector?: { latest_eligible_session?: string | null; next_run_ict?: string | null; storage_rights?: string };
  warehouse?: { partitions?: number; union_last?: string | null };
  shadow?: { signals?: number; outcomes?: number; state?: string };
  backup?: { status?: string; note?: string };
}

export interface SystemStatus {
  status: string;
  ops: OpsReport;
  frameworks: FrameworkStatus[];
  shadow: {
    protocol_hash?: string | null;
    registered_at?: string | null;
    qualified_universe?: unknown;
    first_eligible_session?: string | null;
    signals: number;
    outcomes: number;
    state: string;
  };
}

export async function fetchSystemStatus(signal?: AbortSignal): Promise<SystemStatus | null> {
  try {
    const r = await fetch(STATUS_ENDPOINT, { method: 'GET', credentials: 'include', referrerPolicy: 'no-referrer', signal });
    if (r.status !== 200) return null;
    return await r.json() as SystemStatus;
  } catch {
    return null;
  }
}

export const frameworkLabel: Record<string, string> = {
  NAUTILUS_TRADER: 'NautilusTrader',
  OPENBB: 'OpenBB',
  TRADINGAGENTS: 'TradingAgents',
  FREQTRADE: 'Freqtrade',
  QUANTDINGER: 'QuantDinger',
};
